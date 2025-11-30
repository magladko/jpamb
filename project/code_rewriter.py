"""Code rewriter for dead code removal."""

from dataclasses import dataclass
from pathlib import Path

import jpamb
from jpamb import jvm


@dataclass
class RewriteResult:
    """Result of code rewriting operation."""

    original_source: str
    debloated_source: str
    lines_removed: int
    bytes_saved: int
    transformations: list[str]


class CodeRewriter:
    """Remove dead code based on coverage analysis."""

    def __init__(self, suite: jpamb.Suite):
        self.suite = suite

    def rewrite(
        self, methodid: jvm.AbsMethodID, lines_executed: set[int]
    ) -> RewriteResult:
        """
        Rewrite Java source to remove dead code.

        Phase 1: Simple line-based removal
        - Remove lines not in lines_executed
        - Preserve class structure and imports

        Args:
            methodid: Method to debloat
            lines_executed: Set of line numbers that were executed

        Returns:
            RewriteResult with original and debloated source

        """
        # Read source file
        source_file = self.suite.sourcefile(methodid.classname)
        with Path.open(source_file, "r") as f:
            original_source = f.read()

        # For Phase 1: Simple approach - just report what would be removed
        # In future phases, we'll use tree_sitter for AST manipulation
        original_lines = original_source.splitlines(keepends=True)
        transformations = []

        # Analyze which lines are dead code
        dead_lines = set()
        for line_num in range(1, len(original_lines) + 1):
            if line_num not in lines_executed:
                # Check if it's a code line (not comment, import, class declaration)
                line = original_lines[line_num - 1].strip()
                if line and not self._is_structural_line(line):
                    dead_lines.add(line_num)

        if dead_lines:
            transformations.append(
                f"Identified {len(dead_lines)} potentially dead code lines"
            )

        # For now, return original source
        # TODO: Implement actual AST-based removal in future phases
        debloated_source = original_source

        lines_removed = 0
        bytes_saved = len(original_source) - len(debloated_source)

        return RewriteResult(
            original_source=original_source,
            debloated_source=debloated_source,
            lines_removed=lines_removed,
            bytes_saved=bytes_saved,
            transformations=transformations,
        )

    def _is_structural_line(self, line: str) -> bool:
        """Check if line is structural (import, package, class declaration, etc.)."""
        structural_keywords = [
            "package ",
            "import ",
            "public class ",
            "private class ",
            "class ",
            "public static ",
            "private static ",
            "@",  # Annotations
            "{",
            "}",
            "//",
            "/*",
            "*/",
        ]
        # TODO(kornel): this should work 90% of the time,
        # but we should refine the check for non-trivial cases
        return any(line.startswith(kw) for kw in structural_keywords) or line == ""
