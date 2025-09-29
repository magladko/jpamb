from typing import Optional

import tree_sitter
import tree_sitter_java

import jpamb
from jpamb import jvm


class SyntacticHelper:
    
    JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
    parser = tree_sitter.Parser(JAVA_LANGUAGE)

    def find_interesting_values(self, methodid: jvm.AbsMethodID) -> set[jvm.Value]:
        self.tree = self.parse_source_file(self.parser, methodid)
        self.simple_classname = str(methodid.classname.name)

        class_node = self.find_class_node(self.tree, self.simple_classname)
        assert class_node, f"Class {self.simple_classname} not found in source file."
        method_node = self.find_method_node(class_node, methodid)
        assert method_node, f"Method {methodid.extension.name} not found in class {self.simple_classname}."

        return self._gather_numeric_values(method_node)

    def _gather_numeric_values(self, method_node: tree_sitter.Node, include_oposite: bool = True) -> set[jvm.Value]:
        """Gather all numeric values from the method node using tree_sitter."""
        numeric_values = set()

        numeric_query = tree_sitter.Query(self.JAVA_LANGUAGE, """
            [
                (decimal_integer_literal) @number
                (hex_integer_literal) @number
                (octal_integer_literal) @number
                (binary_integer_literal) @number
                (decimal_floating_point_literal) @number
                (hex_floating_point_literal) @number
            ]
        """)

        captures = tree_sitter.QueryCursor(numeric_query).captures(method_node)
        number_nodes = captures.get("number", [])

        for node in number_nodes:
            if node.text is None:
                continue
            text = node.text.decode('utf-8')
            try:
                if '.' in text or 'e' in text.lower() or 'f' in text.lower() or 'd' in text.lower():
                    value = float(text.rstrip('fFdD'))
                    if 'f' in text.lower():
                        v = jvm.Value(jvm.Float(), value)
                        # numeric_values.add(jvm.Value(jvm.Float(), value))
                    else:
                        v = jvm.Value(jvm.Double(), value)
                        # numeric_values.add(jvm.Value(jvm.Double(), value))
                else:
                    text_clean = text.rstrip('lL')
                    if text_clean.startswith('0x') or text_clean.startswith('0X'):
                        value = int(text_clean, 16)
                    elif text_clean.startswith('0b') or text_clean.startswith('0B'):
                        value = int(text_clean, 2)
                    elif text_clean.startswith('0') and len(text_clean) > 1:
                        value = int(text_clean, 8)
                    else:
                        value = int(text_clean)
                    v = jvm.Value.int(value)
                
                numeric_values.add(v)
                numeric_values.add(jvm.Value(v.type, -value))

            except ValueError:
                continue

        return numeric_values

    def parse_source_file(self, parser: tree_sitter.Parser, methodid: jvm.AbsMethodID) -> tree_sitter.Tree:
        """Parse the Java source file for the given method."""
        srcfile = jpamb.Suite().sourcefile(methodid.classname)

        with open(srcfile, "rb") as f:
            return parser.parse(f.read())
        
    def find_class_node(self, tree: tree_sitter.Tree, class_name: str) -> Optional[tree_sitter.Node]:
        """Find the class node in the parsed tree."""

        class_query = tree_sitter.Query(self.JAVA_LANGUAGE,
            f"""
            (class_declaration
                name: ((identifier) @class-name
                        (#eq? @class-name "{class_name}"))) @class
            """)

        captures = tree_sitter.QueryCursor(class_query).captures(tree.root_node)
        class_nodes = captures.get("class", [])

        if class_nodes:
            return class_nodes[0]
        return None

    def find_method_node(self, class_node: tree_sitter.Node, methodid) -> Optional[tree_sitter.Node]:
        """Find the specific method node within the class."""
        method_name = methodid.extension.name

        method_query = tree_sitter.Query(self.JAVA_LANGUAGE,
            f"""
            (method_declaration name:
              ((identifier) @method-name (#eq? @method-name "{method_name}"))
            ) @method
        """)

        captures = tree_sitter.QueryCursor(method_query).captures(class_node)
        method_nodes = captures.get("method", [])

        # Find method with matching parameters
        for method_node in method_nodes:
            if self._method_matches_signature(method_node, methodid):
                return method_node

        return None

    def _method_matches_signature(self, method_node: tree_sitter.Node, methodid) -> bool:
        """Check if method node matches the expected signature."""
        parameters_node = method_node.child_by_field_name("parameters")
        if not parameters_node:
            return False

        params = [c for c in parameters_node.children 
                  if c.type == "formal_parameter"]

        if len(params) != len(methodid.extension.params):
            return False

        # Basic parameter count match (could be extended for type checking)
        for actual_param in params:
            param_type = actual_param.child_by_field_name("type")
            if not param_type or not param_type.text:
                return False
            # TODO: Add more sophisticated type checking here

        return True

