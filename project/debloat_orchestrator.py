"""Debloating pipeline orchestrator."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from code_rewriter import CodeRewriter, RewriteResult
from debloat_config import generate_k_set
from syntactic_helper import SyntacticHelper

import jpamb
import jpamb.model
from jpamb import jvm
from project import abstract_interpreter
from project.abstractions.signset import SignSet


@dataclass
class DebloatingResult:
    """Result of debloating a single test case."""

    case: jpamb.model.Case
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
    ):
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
        Run debloating pipeline on all cases.

        Args:
            filter_pattern: Optional regex to filter cases

        Returns:
            List of DebloatingResult for each case

        """
        cases = self._filter_cases(filter_pattern)
        results = []

        for case in cases:
            try:
                result = self.debloat_case(case)
                results.append(result)
            except Exception as e:
                # Log error and continue
                results.append(
                    DebloatingResult(
                        case=case,
                        success=False,
                        methodid=jpamb.parse_methodid(case.methodid.encode()),
                        triviality={},
                        lines_executed=set(),
                        rewrite_result=None,
                        error=str(e),
                    )
                )

        return results

    def debloat_case(self, case: jpamb.model.Case) -> DebloatingResult:
        """
        Debloat a single test case.

        Pipeline:
        1. Syntactic analysis (triviality check, K_SET generation)
        2. Coverage analysis (trivial → concrete, non-trivial → abstract)
        3. Code rewriting
        4. Persist
        """
        methodid = jpamb.parse_methodid(case.methodid.encode())
        try:
            # Stage 1: Syntactic analysis
            triviality = self.syntactic_helper.check_triviality(methodid)
            interesting_vals = self.syntactic_helper.find_interesting_values(
                methodid
            )
            # Stage 2: Coverage analysis
            if triviality["is_trivial"]:
                lines_executed = self._run_concrete(methodid, case.input)
            else:
                k_set = generate_k_set(interesting_vals)
                lines_executed = self._run_abstract(methodid, k_set)

            # Stage 3: Code rewriting
            rewrite_result = self.code_rewriter.rewrite(methodid, lines_executed)

            # Stage 4: Persist
            self._persist_code(methodid, rewrite_result.debloated_source)

            # Save intermediate artifacts
            self._save_intermediate_artifacts(
                case, triviality, lines_executed, rewrite_result
            )

            return DebloatingResult(
                case=case,
                success=True,
                methodid=methodid,
                triviality=triviality,
                lines_executed=lines_executed,
                rewrite_result=rewrite_result,
                error=None,
            )

        except Exception as e:
            return DebloatingResult(
                case=case,
                success=False,
                methodid=methodid,
                triviality={},
                lines_executed=set(),
                rewrite_result=None,
                error=str(e),
            )

    def _run_concrete(
        self, methodid: jvm.AbsMethodID, input: jpamb.model.Input
    ) -> set[int]:
        """
        Run concrete interpreter to get coverage.

        Uses interpreter.py which now tracks lines_executed.
        """
        from interpreter import Frame, Stack, State, lines_executed, step

        # Clear previous execution tracking
        lines_executed.clear()

        # Set up concrete execution
        frame = Frame.from_method(methodid)
        state = State({}, Stack.empty().push(frame))

        # Initialize parameters from input
        for i, val in enumerate(input.values):
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
        return abstract_interpreter.analyze_coverage(methodid, {SignSet}, k_set)

    def _persist_code(
        self, methodid: jvm.AbsMethodID, source: str
    ) -> None:
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
        case: jpamb.model.Case,
        triviality: dict,
        lines_executed: set[int],
        rewrite_result: RewriteResult,
    ) -> None:
        """Save all intermediate artifacts for debugging/analysis."""
        # Create case-specific directory
        case_dir = self.intermediate_dir / str(case.methodid).replace("/", "_")
        case_dir.mkdir(parents=True, exist_ok=True)

        # Save triviality check result
        with Path.open(case_dir / "triviality.json", "w") as f:
            json.dump(triviality, f, indent=2)

        # Save coverage information
        with Path.open(case_dir / "coverage.json", "w") as f:
            json.dump(
                {
                    "lines_executed": sorted(lines_executed),
                    "total_lines_executed": len(lines_executed),
                },
                f,
                indent=2,
            )

        # Save rewrite result
        with Path.open(case_dir / "original.java", "w") as f:
            f.write(rewrite_result.original_source)

        with Path.open(case_dir / "debloated.java", "w") as f:
            f.write(rewrite_result.debloated_source)

        with Path.open(case_dir / "rewrite_summary.json", "w") as f:
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
