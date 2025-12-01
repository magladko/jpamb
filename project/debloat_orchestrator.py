"""Debloating pipeline orchestrator."""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import abstract_interpreter
from abstractions.interval import Interval
from abstractions.signset import SignSet
from code_rewriter import CodeRewriter, RewriteResult
from debloat_config import generate_k_set
from interpreter import Frame, Stack, State, lines_executed, step
from syntactic_helper import SyntacticHelper
import syntactic_analyzer

import jpamb
import jpamb.model
from jpamb import jvm


@dataclass
class DebloatingResult:
    """Result of debloating a single test case."""

    success: bool
    methodid: jvm.AbsMethodID
    triviality: dict
    lines_executed: set[int]
    rewrite_result: RewriteResult | None
    error: str | None


class DebloatOrchestrator:
    """Orchestrate the complete debloating pipeline."""

    def __init__(
        self,
        suite: jpamb.Suite,
        source_dir: Path,
        target_dir: Path,
        timeout: float = 5.0,
    ) -> None:
        self.suite = suite
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.timeout = timeout

        # Initialize components
        self.syntactic_helper = SyntacticHelper()
        self.code_rewriter = CodeRewriter(suite)

        # Create output directories
        self.intermediate_dir = target_dir / "intermediate"
        self.final_dir = target_dir / "final"
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        self.final_dir.mkdir(parents=True, exist_ok=True)

    def run(self, filter_pattern: re.Pattern | None = None) -> list[DebloatingResult]:
        """
        Run debloating pipeline on all methods.

        Args:
            filter_pattern: Optional regex to filter cases

        Returns:
            List of DebloatingResult for each method

        """
        # Apply filter FIRST to get subset of cases to debloat
        cases = self._filter_cases(filter_pattern)
        methodids = {jpamb.parse_methodid(case.methodid.encode()) for case in cases}

        # Group filtered methods by source file
        methods_by_file = self._group_methods_by_source_file(methodids)
        results = []
        for file_methods in methods_by_file.values():
            file_results = self._debloat_source_file(file_methods)
            results.extend(file_results)

        return results

    def debloat_method(self, absmethodid: jvm.AbsMethodID) -> DebloatingResult:
        """
        Debloat a single method.

        This method is preserved for backward compatibility and single-method use.
        For multiple methods, use run() which groups them by source file efficiently.

        Pipeline:
        1. Syntactic analysis (triviality check, K_SET generation)
        2. Coverage analysis (trivial → concrete, non-trivial → abstract)
        3. Code rewriting
        4. Persist
        """
        # Delegate to _debloat_source_file with a single method
        results = self._debloat_source_file([absmethodid])
        return results[0]

    def _run_concrete(
        self, methodid: jvm.AbsMethodID, m_input: jpamb.model.Input | None
    ) -> set[int]:
        """
        Run concrete interpreter to get coverage.

        Uses interpreter.py which now tracks lines_executed.
        """
        # Clear previous execution tracking
        lines_executed.clear()

        # Set up concrete execution
        frame = Frame.from_method(methodid)
        state = State({}, Stack.empty().push(frame))

        # Initialize parameters from input
        if m_input:
            for i, val in enumerate(m_input.values):
                frame.locals[i] = val

        # Execute up to max steps
        max_steps = 1000
        for _ in range(max_steps):
            result = step(state)
            if isinstance(result, str):
                break

        # Return executed lines for this method
        return lines_executed.get(methodid, set())

    def _run_abstract(
        self, methodid: jvm.AbsMethodID, k_set: set[int | float]
    ) -> set[int]:
        """Run abstract interpreter to get coverage."""
        return abstract_interpreter.AbsInterpreter(debloater=True).analyze_coverage(
            methodid, {Interval, SignSet}, k_set
        )

    def _persist_code(self, methodid: jvm.AbsMethodID, source: str) -> None:
        """Persist debloated code to final output directory."""
        source_file = self.suite.sourcefile(methodid.classname)

        # Compute relative path from source_dir
        try:
            relative_path = source_file.relative_to(self.source_dir)
        except ValueError:
            # If source file is not under source_dir, use simple filename
            relative_path = Path(source_file.name)

        output_path = self.final_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with Path.open(output_path, "w") as f:
            f.write(source)

    def _save_intermediate_artifacts(
        self,
        absmethodid: jvm.AbsMethodID,
        triviality: dict,
        lines_executed: set[int],
        rewrite_result: RewriteResult,
    ) -> None:
        """Save all intermediate artifacts for debugging/analysis."""
        # Create case-specific directory
        method_dir = self.intermediate_dir / str(absmethodid.methodid).replace("/", "_")
        method_dir.mkdir(parents=True, exist_ok=True)

        # Save triviality check result
        with Path.open(method_dir / "triviality.json", "w") as f:
            json.dump(triviality, f, indent=2)

        # Save coverage information
        with Path.open(method_dir / "coverage.json", "w") as f:
            json.dump(
                {
                    "lines_executed": sorted(lines_executed),
                    "total_lines_executed": len(lines_executed),
                },
                f,
                indent=2,
            )

        # Save rewrite result
        with Path.open(method_dir / "original.java", "w") as f:
            f.write(rewrite_result.original_source)

        with Path.open(method_dir / "debloated.java", "w") as f:
            f.write(rewrite_result.debloated_source)

        with Path.open(method_dir / "rewrite_summary.json", "w") as f:
            json.dump(
                {
                    "lines_removed": rewrite_result.lines_removed,
                    "bytes_saved": rewrite_result.bytes_saved,
                    "transformations": rewrite_result.transformations,
                },
                f,
                indent=2,
            )

    def _filter_cases(self, pattern: re.Pattern | None) -> list[jpamb.model.Case]:
        """Filter cases based on regex pattern."""
        if pattern:
            return [
                case for case in self.suite.cases if pattern.search(str(case.methodid))
            ]
        return list(self.suite.cases)

    def _group_methods_by_source_file(
        self, absmethodids: Iterable[jvm.AbsMethodID]
    ) -> dict[Path, list[jvm.AbsMethodID]]:
        """
        Group methods by their source file path.

        This ensures all methods from the same Java file are processed together,
        allowing incremental rewrites without overwriting previous changes.
        Only groups the filtered methods passed as input.
        """
        grouped = {}
        for methodid in absmethodids:
            source_file = self.suite.sourcefile(methodid.classname)
            if source_file not in grouped:
                grouped[source_file] = []
            grouped[source_file].append(methodid)
        return grouped

    def _debloat_source_file(
        self, absmethodids: Iterable[jvm.AbsMethodID]
    ) -> list[DebloatingResult]:
        """
        Debloat all methods in a single source file.

        This method processes all methods in two phases:
        1. Analysis phase: Analyze each method against the ORIGINAL source
        2. Rewrite phase: Apply all line removals at once to avoid line number shifts

        Args:
            absmethodids: Method IDs for methods to be analyzed

        Returns:
            List of DebloatingResult for each method

        """
        results = []

        # Phase 1: Analyze all methods against original source
        analysis_results = []
        for methodid in absmethodids:
            try:
                # Stage 1: Syntactic analysis
                triviality = self.syntactic_helper.check_triviality(methodid)
                interesting_vals = self.syntactic_helper.find_interesting_values(
                    methodid
                )

                # FULL syntactic analysis for the *entire file*
                infos = syntactic_analyzer.analyze_java_file(methodid)

                # Identify the correct method-name in AST
                method_name = methodid.extension.name

                param_count = len(methodid.extension.params)

                info = next(
                    i for i in infos
                    if i["methodName"] == method_name and len(i["parameters"]) == param_count
                )

                # Now use your determine_analysis_type
                analysis_type = syntactic_analyzer.determine_analysis_type(info)
                print(f'Min:{analysis_type} hans: {triviality}')

                # Stage 2: Coverage analysis
                if analysis_type == "dynamic":
                    lines_executed_set = self._run_concrete(methodid, None)
                else:
                    k_set = generate_k_set(interesting_vals)
                    lines_executed_set = self._run_abstract(methodid, k_set)

                analysis_results.append(
                    {
                        "methodid": methodid,
                        "triviality": triviality,
                        "lines_executed": lines_executed_set,
                    }
                )

            except Exception as e:  # noqa: BLE001
                results.append(
                    DebloatingResult(
                        success=False,
                        methodid=methodid,
                        triviality={},
                        lines_executed=set(),
                        rewrite_result=None,
                        error=str(e),
                    )
                )

        # Phase 2: Collect lines to remove from all methods
        accumulated_lines_to_remove = set()
        original_source = None

        for analysis in analysis_results:
            methodid = analysis["methodid"]
            triviality = analysis["triviality"]
            lines_executed_set = analysis["lines_executed"]

            try:
                # Analyze against original source to get lines to remove
                rewrite_result = self.code_rewriter.rewrite_incremental(
                    methodid, lines_executed_set, current_source=None
                )

                # Save the original source from first method
                if original_source is None:
                    original_source = rewrite_result.original_source

                # Accumulate lines to remove across all methods
                accumulated_lines_to_remove.update(rewrite_result.lines_removed_set)

                # Save intermediate artifacts (shows per-method analysis)
                self._save_intermediate_artifacts(
                    methodid, triviality, lines_executed_set, rewrite_result
                )

                results.append(
                    DebloatingResult(
                        success=True,
                        methodid=methodid,
                        triviality=triviality,
                        lines_executed=lines_executed_set,
                        rewrite_result=rewrite_result,
                        error=None,
                    )
                )

            except Exception as e:  # noqa: BLE001
                results.append(
                    DebloatingResult(
                        success=False,
                        methodid=methodid,
                        triviality={},
                        lines_executed=set(),
                        rewrite_result=None,
                        error=str(e),
                    )
                )

        # Phase 3: Apply all accumulated line removals at once
        current_source = None
        if original_source and accumulated_lines_to_remove:
            # Apply all line removals to original source
            current_source = self.code_rewriter.apply_line_removals(
                original_source, accumulated_lines_to_remove
            )
        elif original_source:
            # No lines to remove
            current_source = original_source

        # Stage 4: Persist once per file (after all methods processed)
        if current_source and any(r.success for r in results):
            # Use first successful method's methodid to get source file path
            successful_result = next(r for r in results if r.success)
            self._persist_code(successful_result.methodid, current_source)

        return results
