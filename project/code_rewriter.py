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


@dataclass
class StatementInfo:
    """Information about a statement in the AST."""

    node: tree_sitter.Node
    start_line: int
    end_line: int
    source_text: str


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
        # Read source file
        source_file = self.suite.sourcefile(methodid.classname)
        with Path.open(source_file, "r") as f:
            original_source = f.read()

        # Parse with tree-sitter
        tree = self.syntactic_helper.parse_source_file(
            self.syntactic_helper.parser, methodid
        )

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
            )

        # Extract statements from method body
        all_statements = self._get_method_statements(method_node, original_source)

        # Filter: keep only executed statements
        kept_statements = [
            stmt for stmt in all_statements if self._is_executed(stmt, lines_executed)
        ]

        # Build transformations report
        transformations = [
            f"Removed {len(all_statements) - len(kept_statements)} dead statements",
            f"Kept {len(kept_statements)}/{len(all_statements)} statements",
        ]

        # Build new method body
        if kept_statements:
            debloated_source = self._replace_method_body(
                original_source, method_node, kept_statements
            )
        else:
            # Empty body - insert minimal return
            return_type = methodid.extension.return_type
            minimal_return = self._get_minimal_return(return_type)
            debloated_source = self._replace_method_body_with_text(
                original_source, method_node, minimal_return
            )
            transformations.append("Method body empty - inserted minimal return")

        # Calculate metrics
        lines_removed = len(all_statements) - len(kept_statements)
        bytes_saved = len(original_source) - len(debloated_source)

        return RewriteResult(
            original_source=original_source,
            debloated_source=debloated_source,
            lines_removed=lines_removed,
            bytes_saved=bytes_saved,
            transformations=transformations,
        )

    def _get_method_statements(
        self, method_node: tree_sitter.Node, source: str
    ) -> list[StatementInfo]:
        """
        Extract all statements from method body with their line ranges.

        Args:
            method_node: The method declaration node
            source: Original source code

        Returns:
            List of StatementInfo objects

        """
        body_node = method_node.child_by_field_name("body")
        if not body_node:
            return []

        statements = []
        source_bytes = source.encode("utf-8")

        # Query for all direct children of the method body block
        # We want top-level statements, not nested ones
        for child in body_node.children:
            # Skip braces and whitespace
            if child.type in ("{", "}", "comment", "line_comment", "block_comment"):
                continue

            # Get line numbers (tree-sitter uses 0-based, but we use 1-based)
            start_line = child.start_point[0] + 1
            end_line = child.end_point[0] + 1

            # Extract source text
            source_text = source_bytes[child.start_byte : child.end_byte].decode(
                "utf-8"
            )

            statements.append(
                StatementInfo(
                    node=child,
                    start_line=start_line,
                    end_line=end_line,
                    source_text=source_text,
                )
            )

        return statements

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

    def _replace_method_body(
        self,
        source: str,
        method_node: tree_sitter.Node,
        kept_statements: list[StatementInfo],
    ) -> str:
        """
        Replace method body with only the kept statements.

        Args:
            source: Original source code
            method_node: The method declaration node
            kept_statements: Statements to keep

        Returns:
            Modified source code

        """
        body_node = method_node.child_by_field_name("body")
        if not body_node:
            return source

        # Build new body content
        new_body_lines = [stmt.source_text for stmt in kept_statements]

        new_body_content = "\n".join(new_body_lines)

        # Get the content of the body block (between the braces)
        # We need to find the opening and closing braces
        source_bytes = source.encode("utf-8")

        # Find opening brace
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

        # Add proper indentation and newlines
        if new_body_content:
            new_source = f"{before_body}\n{new_body_content}\n    {after_body}"
        else:
            new_source = f"{before_body}\n    {after_body}"

        return new_source

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
