"""Code rewriter for dead code removal."""

from dataclasses import dataclass
from pathlib import Path

import tree_sitter
import tree_sitter_java
from syntactic_helper import SyntacticHelper

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
    lines_removed_set: set[int]  # Which specific lines were removed


@dataclass
class StatementInfo:
    """Information about a statement in the AST."""

    node: tree_sitter.Node
    start_line: int
    end_line: int


class CodeRewriter:
    """Remove dead code based on coverage analysis using AST manipulation."""

    JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())

    def __init__(self, suite: jpamb.Suite) -> None:
        self.suite = suite
        self.syntactic_helper = SyntacticHelper()

    def rewrite(
        self, methodid: jvm.AbsMethodID, lines_executed: set[int]
    ) -> RewriteResult:
        """
        Rewrite Java source to remove dead code using AST-based analysis.

        Args:
            methodid: Method to debloat
            lines_executed: Set of line numbers that were executed

        Returns:
            RewriteResult with original and debloated source

        """
        return self.rewrite_incremental(methodid, lines_executed, current_source=None)

    def rewrite_incremental(
        self,
        methodid: jvm.AbsMethodID,
        lines_executed: set[int],
        current_source: str | None = None,
    ) -> RewriteResult:
        """
        Rewrite Java source incrementally, using provided source state.

        This method supports incremental rewrites by accepting the current source
        state. This allows multiple methods in the same file to be debloated
        sequentially without overwriting previous changes.

        Args:
            methodid: Method to debloat
            lines_executed: Set of line numbers that were executed
            current_source: Current source state (or None to read from disk)

        Returns:
            RewriteResult with original and debloated source

        """
        # Read source file only if not provided
        if current_source is None:
            source_file = self.suite.sourcefile(methodid.classname)
            with Path.open(source_file, "r") as f:
                original_source = f.read()
        else:
            original_source = current_source

        # Parse with tree-sitter (parse the provided source, not from disk)
        tree = self.syntactic_helper.parser.parse(original_source.encode("utf-8"))

        # Find method node
        class_name = str(methodid.classname.name)
        class_node = self.syntactic_helper.find_class_node(tree, class_name)
        if not class_node:
            # Can't find class - return original source
            return RewriteResult(
                original_source=original_source,
                debloated_source=original_source,
                lines_removed=0,
                bytes_saved=0,
                transformations=["Could not find class in AST"],
                lines_removed_set=set(),
            )

        method_node = self.syntactic_helper.find_method_node(class_node, methodid)
        if not method_node:
            # Can't find method - return original source
            return RewriteResult(
                original_source=original_source,
                debloated_source=original_source,
                lines_removed=0,
                bytes_saved=0,
                transformations=["Could not find method in AST"],
                lines_removed_set=set(),
            )

        # Extract statements from method body
        all_statements = self._get_method_statements(method_node)

        # Mark dead lines for removal
        lines_to_remove = self._mark_dead_lines(all_statements, lines_executed)

        # Count kept vs removed statements
        kept_statements = [
            stmt for stmt in all_statements if self._is_executed(stmt, lines_executed)
        ]

        # Build transformations report
        transformations = [
            f"Removed {len(all_statements) - len(kept_statements)} dead statements",
            f"Kept {len(kept_statements)}/{len(all_statements)} statements",
            f"Removed {len(lines_to_remove)} lines from source",
        ]

        # Build new source by omitting dead lines
        if kept_statements:
            debloated_source = self.apply_line_removals(
                original_source, lines_to_remove
            )
        else:
            # Empty body - insert minimal return
            return_type = methodid.extension.return_type
            minimal_return = self._get_minimal_return(return_type)
            debloated_source = self._replace_method_body_with_text(
                original_source, method_node, minimal_return
            )
            transformations.append("Method body empty - inserted minimal return")
            # When body is empty, we replaced all method body lines
            # lines_to_remove already contains all statement lines

        # Calculate metrics
        lines_removed = len(lines_to_remove)
        bytes_saved = len(original_source) - len(debloated_source)

        return RewriteResult(
            original_source=original_source,
            debloated_source=debloated_source,
            lines_removed=lines_removed,
            bytes_saved=bytes_saved,
            transformations=transformations,
            lines_removed_set=lines_to_remove,
        )

    def _get_method_statements(
        self, method_node: tree_sitter.Node
    ) -> list[StatementInfo]:
        """
        Extract all statements from method body recursively.

        This includes nested statements inside control flow blocks.

        Args:
            method_node: The method declaration node
        Returns:
            List of StatementInfo objects

        """
        body_node = method_node.child_by_field_name("body")
        if not body_node:
            return []

        statements = []
        self._extract_statements_recursive(body_node, statements)
        return statements

    def _extract_statements_recursive(
        self, parent_node: tree_sitter.Node, statements: list[StatementInfo]
    ) -> None:
        """
        Recursively extract statements, descending into control flow bodies.

        Args:
            parent_node: The parent node to extract statements from
            statements: List to append extracted statements to

        """
        for child in parent_node.children:
            # Skip braces and whitespace
            if child.type in ("{", "}", "comment", "line_comment", "block_comment"):
                continue

            # Get line numbers (tree-sitter uses 0-based, but we use 1-based)
            start_line = child.start_point[0] + 1
            end_line = child.end_point[0] + 1

            statements.append(
                StatementInfo(
                    node=child,
                    start_line=start_line,
                    end_line=end_line,
                )
            )

            # Recurse into control flow bodies
            if child.type in ("if_statement", "while_statement", "for_statement"):
                # Extract statements from body
                body_node = child.child_by_field_name(
                    "consequence"
                ) or child.child_by_field_name("body")
                if body_node and body_node.type == "block":
                    self._extract_statements_recursive(body_node, statements)

                # For if-statements, also handle else/else-if
                if child.type == "if_statement":
                    alternative = child.child_by_field_name("alternative")
                    if alternative:
                        if alternative.type == "block":
                            self._extract_statements_recursive(alternative, statements)
                        elif alternative.type == "if_statement":
                            # else-if case: the alternative is itself an if_statement
                            # It will be processed in the main loop,
                            # so no need to recurse
                            pass
            # Recurse into bare/anonymous blocks
            elif child.type == "block":
                self._extract_statements_recursive(child, statements)

    def _is_executed(self, stmt: StatementInfo, lines_executed: set[int]) -> bool:
        """
        Check if a statement was executed.

        A statement is considered executed if ANY of its lines were executed.

        Args:
            stmt: Statement information
            lines_executed: Set of executed line numbers

        Returns:
            True if the statement was executed, False otherwise

        """
        return any(
            line in lines_executed for line in range(stmt.start_line, stmt.end_line + 1)
        )

    def _mark_dead_lines(
        self, all_statements: list[StatementInfo], lines_executed: set[int]
    ) -> set[int]:
        """
        Mark which lines should be removed based on statement execution.

        Args:
            all_statements: All statements in the method body
            lines_executed: Set of line numbers that were executed

        Returns:
            Set of line numbers to remove (1-indexed)

        """
        lines_to_remove = set()

        for stmt in all_statements:
            if not self._is_executed(stmt, lines_executed):
                # Mark all lines in this dead statement for removal
                for line in range(stmt.start_line, stmt.end_line + 1):
                    lines_to_remove.add(line)

        return lines_to_remove

    def _get_minimal_return(self, return_type: jvm.Type | None) -> str:
        """
        Generate a minimal return statement based on return type.

        Args:
            return_type: The method's return type

        Returns:
            A minimal return statement

        """
        if return_type is None:  # void
            return "        return;"
        if isinstance(return_type, jvm.Boolean):
            return "        return false;"
        if isinstance(return_type, jvm.Int):
            return "        return 0;"
        if isinstance(return_type, jvm.Long):
            return "        return 0L;"
        if isinstance(return_type, jvm.Short):
            return "        return (short) 0;"
        if isinstance(return_type, jvm.Byte):
            return "        return (byte) 0;"
        if isinstance(return_type, jvm.Char):
            return "        return '\\0';"
        if isinstance(return_type, jvm.Float):
            return "        return 0.0f;"
        if isinstance(return_type, jvm.Double):
            return "        return 0.0;"
        return "        return null;"

    def apply_line_removals(
        self,
        source: str,
        lines_to_remove: set[int],
    ) -> str:
        """
        Reconstruct source by omitting specified lines.

        Args:
            source: Original source code
            lines_to_remove: Set of line numbers to omit (1-indexed)

        Returns:
            Modified source with specified lines removed

        """
        # Split source into lines
        lines = source.split("\n")

        # Filter out dead lines (using 1-based indexing)
        kept_lines = [
            line for i, line in enumerate(lines, start=1) if i not in lines_to_remove
        ]

        # Rejoin
        return "\n".join(kept_lines)

    def _replace_method_body_with_text(
        self, source: str, method_node: tree_sitter.Node, body_text: str
    ) -> str:
        """
        Replace method body with custom text.

        Args:
            source: Original source code
            method_node: The method declaration node
            body_text: New body text

        Returns:
            Modified source code

        """
        body_node = method_node.child_by_field_name("body")
        if not body_node:
            return source

        source_bytes = source.encode("utf-8")

        # Find opening and closing braces
        opening_brace_pos = None
        closing_brace_pos = None

        for child in body_node.children:
            if child.type == "{":
                opening_brace_pos = child.end_byte
            elif child.type == "}":
                closing_brace_pos = child.start_byte

        if opening_brace_pos is None or closing_brace_pos is None:
            return source

        # Reconstruct source
        before_body = source_bytes[:opening_brace_pos].decode("utf-8")
        after_body = source_bytes[closing_brace_pos:].decode("utf-8")

        new_source = f"{before_body}\n{body_text}\n    {after_body}"
        return new_source  # noqa: RET504
