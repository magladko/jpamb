from enum import Flag, auto
from pathlib import Path

import tree_sitter
import tree_sitter_java

import jpamb
from jpamb import jvm


class SyntacticHelper:
    JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
    parser = tree_sitter.Parser(JAVA_LANGUAGE)

    def find_interesting_values(
        self, methodid: jvm.AbsMethodID
    ) -> set[jvm.Value]:
        self.tree = self.parse_source_file(self.parser, methodid)
        self.simple_classname = str(methodid.classname.name)

        class_node = self.find_class_node(self.tree, self.simple_classname)
        assert class_node, f"Class {self.simple_classname} not found in source file."
        method_node = self.find_method_node(class_node, methodid)
        assert method_node, (
            f"Method {methodid.extension.name} not found in "
            f"class {self.simple_classname}."
        )

        return self._gather_numeric_values(method_node)

    class ExtraValues(Flag):
        OPOSITE = auto()
        ZERO = auto()
        ALL = OPOSITE | ZERO

    def _gather_numeric_values(
        self,
        method_node: tree_sitter.Node,
        include_extra: ExtraValues = ExtraValues.ALL,
    ) -> set[jvm.Value]:
        """Gather all numeric values from the method node using tree_sitter."""
        numeric_values = set()

        numeric_query = tree_sitter.Query(
            self.JAVA_LANGUAGE,
            """
            [
                (decimal_integer_literal) @number
                (hex_integer_literal) @number
                (octal_integer_literal) @number
                (binary_integer_literal) @number
                (decimal_floating_point_literal) @number
                (hex_floating_point_literal) @number
            ]
        """,
        )

        captures = tree_sitter.QueryCursor(numeric_query).captures(method_node)
        number_nodes = captures.get("number", [])

        for node in number_nodes:
            if node.text is None:
                continue
            text = node.text.decode("utf-8").lower()
            try:
                if any(c in text for c in ".efd"):
                    value = float(text.rstrip("fd"))
                    v = jvm.Value(jvm.Float() if "f" in text else jvm.Double(), value)
                else:
                    text_clean = text.rstrip("l")
                    if text_clean.startswith("0x"):
                        value = int(text_clean, 16)
                    elif text_clean.startswith("0b"):
                        value = int(text_clean, 2)
                    elif text_clean.startswith("0") and len(text_clean) > 1:
                        value = int(text_clean, 8)
                    else:
                        value = int(text_clean)
                    v = jvm.Value.int(value)

                numeric_values.add(v)
                if self.ExtraValues.OPOSITE in include_extra:
                    numeric_values.add(jvm.Value(v.type, -value))
                if self.ExtraValues.ZERO in include_extra:
                    numeric_values.add(jvm.Value(v.type, 0))

            except ValueError:
                continue

        return numeric_values

    def parse_source_file(
        self, parser: tree_sitter.Parser, methodid: jvm.AbsMethodID
    ) -> tree_sitter.Tree:
        """Parse the Java source file for the given method."""
        srcfile = jpamb.Suite().sourcefile(methodid.classname)

        with Path.open(srcfile, "rb") as f:
            return parser.parse(f.read())

    def find_class_node(
        self, tree: tree_sitter.Tree, class_name: str
    ) -> tree_sitter.Node | None:
        """Find the class node in the parsed tree."""
        class_query = tree_sitter.Query(
            self.JAVA_LANGUAGE,
            f"""
            (class_declaration
                name: ((identifier) @class-name
                        (#eq? @class-name "{class_name}"))) @class
            """,
        )

        captures = tree_sitter.QueryCursor(class_query).captures(tree.root_node)
        class_nodes = captures.get("class", [])

        if class_nodes:
            return class_nodes[0]
        return None

    def find_method_node(
        self, class_node: tree_sitter.Node, methodid: jvm.AbsMethodID
    ) -> tree_sitter.Node | None:
        """Find the specific method node within the class."""
        method_name = methodid.extension.name

        method_query = tree_sitter.Query(
            self.JAVA_LANGUAGE,
            f"""
            (method_declaration name:
              ((identifier) @method-name (#eq? @method-name "{method_name}"))
            ) @method
        """,
        )

        captures = tree_sitter.QueryCursor(method_query).captures(class_node)
        method_nodes = captures.get("method", [])

        # Find method with matching parameters
        for method_node in method_nodes:
            if self._method_matches_signature(method_node, methodid):
                return method_node

        return None

    def _method_matches_signature(
        self, method_node: tree_sitter.Node, methodid: jvm.AbsMethodID
    ) -> bool:
        """Check if method node matches the expected signature."""
        parameters_node = method_node.child_by_field_name("parameters")
        if not parameters_node:
            return False

        params = [c for c in parameters_node.children if c.type == "formal_parameter"]

        if len(params) != len(methodid.extension.params):
            return False

        # Basic parameter count match (could be extended for type checking)
        for actual_param in params:
            param_type = actual_param.child_by_field_name("type")
            if not param_type or not param_type.text:
                return False
            # TODO(kornel): Add more sophisticated type checking here

        return True

    def check_triviality(self, methodid: jvm.AbsMethodID) -> dict:
        """
        Check if a method is trivial (no parameters, loops, or recursion).

        A method is trivial if it has:
        - No method parameters
        - No loops (while, for, do-while)
        - No recursive calls

        Returns:
            dict with keys: 'is_trivial', 'has_parameters', 'has_loops',
                           'has_recursion', 'justification'

        """
        # Check for parameters
        has_parameters = len(methodid.extension.params) > 0

        # Check for loops (AST-based)
        has_loops = self._detect_loops(methodid)

        # Check for recursion
        has_recursion = self._detect_recursion(methodid)

        is_trivial = not (has_parameters or has_loops or has_recursion)

        # Build justification
        reasons = []
        if has_parameters:
            reasons.append("has parameters")
        if has_loops:
            reasons.append("contains loops")
        if has_recursion:
            reasons.append("has recursive calls")

        justification = (
            "Trivial: no parameters, loops, or recursion"
            if is_trivial
            else f"Non-trivial: {', '.join(reasons)}"
        )

        return {
            "is_trivial": is_trivial,
            "has_parameters": has_parameters,
            "has_loops": has_loops,
            "has_recursion": has_recursion,
            "justification": justification,
        }

    def _detect_loops(self, methodid: jvm.AbsMethodID) -> bool:
        """Detect loops in method using both bytecode and AST analysis."""
        # First, check bytecode for backward goto jumps
        suite = jpamb.Suite()
        try:
            opcodes = list(suite.method_opcodes(methodid))
            for i, op in enumerate(opcodes):
                if isinstance(op, jvm.Goto):
                    if op.target < i:  # Backward jump = loop
                        return True
        except Exception:
            pass  # If bytecode check fails, rely on AST

        # Also check AST for loop constructs
        tree = self.parse_source_file(self.parser, methodid)
        simple_classname = str(methodid.classname.name)
        class_node = self.find_class_node(tree, simple_classname)
        if not class_node:
            return False

        method_node = self.find_method_node(class_node, methodid)
        if not method_node:
            return False

        # Query for all loop types
        loop_query = tree_sitter.Query(
            self.JAVA_LANGUAGE,
            """
            [
                (while_statement) @loop
                (for_statement) @loop
                (do_statement) @loop
                (enhanced_for_statement) @loop
            ]
            """,
        )

        captures = tree_sitter.QueryCursor(loop_query).captures(method_node)
        return len(captures.get("loop", [])) > 0

    def _detect_recursion(self, methodid: jvm.AbsMethodID) -> bool:
        """Detect recursive method calls in the AST."""
        method_name = methodid.extension.name

        tree = self.parse_source_file(self.parser, methodid)
        simple_classname = str(methodid.classname.name)
        class_node = self.find_class_node(tree, simple_classname)
        if not class_node:
            return False

        method_node = self.find_method_node(class_node, methodid)
        if not method_node:
            return False

        # Query for method invocations
        call_query = tree_sitter.Query(
            self.JAVA_LANGUAGE,
            """
            (method_invocation
                name: (identifier) @method_name
            )
            """,
        )

        captures = tree_sitter.QueryCursor(call_query).captures(method_node)
        called_methods = captures.get("method_name", [])

        # Check if any call matches this method's name
        for call in called_methods:
            if call.text and call.text.decode() == method_name:
                return True

        return False
