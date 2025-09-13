#!/usr/bin/env python3
import logging
import re
import sys

import tree_sitter
import tree_sitter_java

import jpamb


class Prediction:

    def __init__(self, title: str, probability: int):
        self.title = title
        self.probability = probability
    
    def __str__(self) -> str:
        return f"{self.title};{self.probability}%"
    
    def __repr__(self) -> str:
        return f"Prediction({self.title}, {self.probability}%)"
    
    def set(self, probability: int):
        self.probability = probability
    
    def adjust(self, delta: int, relative=True):
        if relative:
            self.probability = max(
                0,
                min(100, int(self.probability * (1 + delta / 100)))
            )
        else:
            self.probability = max(0, min(100, self.probability + delta))
    
    def get(self) -> int:
        return self.probability
    
    def as_tuple(self) -> tuple:
        return (self.title, f"{self.probability}%")

    def as_dict(self) -> dict:
        return dict(self.as_tuple())


class Result:
    ok              = Prediction("ok",              60)
    assertion_error = Prediction("assertion error", 0)
    divide_by_zero  = Prediction("divide by zero",  0)
    out_of_bounds   = Prediction("out of bounds",   0)
    null_pointer    = Prediction("null pointer",    0)
    infinite_loop   = Prediction("*",               0)

    def __init__(self):
        self.set_defaults()

    @staticmethod
    def get_defaults() -> dict:
        return {
            "ok": "60%",
            "assertion error": "0%",
            "divide by zero": "0%",
            "out of bounds": "0%",
            "null pointer": "0%",
            "*": "0%"
        }

    def set_defaults(self) -> None:
        defaults = self.get_defaults()
        self.ok.set(int(defaults["ok"][:-1]))
        self.assertion_error.set(int(defaults["assertion error"][:-1]))
        self.divide_by_zero.set(int(defaults["divide by zero"][:-1]))
        self.out_of_bounds.set(int(defaults["out of bounds"][:-1]))
        self.null_pointer.set(int(defaults["null pointer"][:-1]))
        self.infinite_loop.set(int(defaults["*"][:-1]))

    def as_dict(self) -> dict:
        return {
            "ok": f"{self.ok.get()}%",
            "assertion error": f"{self.assertion_error.get()}%",
            "divide by zero": f"{self.divide_by_zero.get()}%",
            "out of bounds": f"{self.out_of_bounds.get()}%",
            "null pointer": f"{self.null_pointer.get()}%",
            "*": f"{self.infinite_loop.get()}%"
        }
    
    def __iter__(self):
        yield from [
            self.ok,
            self.assertion_error,
            self.divide_by_zero,
            self.out_of_bounds,
            self.null_pointer,
            self.infinite_loop
        ]
        # for outcome in self.as_dict().items():
        #     yield outcome


class JavaAnalyzer:
    """A Java program analysis tool that predicts method outcomes."""
    
    def __init__(self, debug=False):
        self.java_language = tree_sitter.Language(tree_sitter_java.language())
        self.parser = tree_sitter.Parser(self.java_language)
        self.log = logging
        # self.log.basicConfig(level=logging.DEBUG)
        self.log.basicConfig(level=logging.ERROR)
        
        # Get method ID from jpamb
        self.methodid = jpamb.getmethodid(
            "My First Analyzer",
            "1.0",
            "Garbage Spillers",
            ["syntactic", "python"],
            for_science=True,
        )
        
        # Optional debugging setup
        if debug:
            self.log.basicConfig(level=logging.DEBUG)
            self._setup_debugger()
    
    def _setup_debugger(self):
        """Setup debugger if available."""
        try:
            import debugpy
            debugpy.listen(5678)
            debugpy.wait_for_client()
        except ImportError:
            pass
    
    def parse_source_file(self, methodid) -> tree_sitter.Tree:
        """Parse the Java source file for the given method."""
        srcfile = jpamb.Suite().sourcefile(methodid.classname)
        
        with open(srcfile, "rb") as f:
            self.log.debug("parse sourcefile %s", srcfile)
            return self.parser.parse(f.read())
    
    def find_class_node(self, tree: tree_sitter.Tree, class_name: str) -> tree_sitter.Node:
        """Find the class node in the parsed tree."""
        self.log.debug(f"Looking for class: {class_name}")
        
        class_query = tree_sitter.Query(self.java_language,
            f"""
            (class_declaration 
                name: ((identifier) @class-name 
                       (#eq? @class-name "{class_name}"))) @class
            """)
        
        captures = tree_sitter.QueryCursor(class_query).captures(tree.root_node)
        class_nodes = captures.get("class", [])
        
        if not class_nodes:
            self.log.error(f"Could not find class '{class_name}'")
            sys.exit(-1)
        
        class_node = class_nodes[0]
        self.log.debug("Found class %s", class_node.range)
        return class_node
    
    def find_method_node(self, class_node: tree_sitter.Node, methodid) -> tree_sitter.Node:
        """Find the specific method node within the class."""
        method_name = methodid.extension.name
        
        method_query = tree_sitter.Query(self.java_language,
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
                self.log.debug("Found method %s %s", method_name, method_node.range)
                return method_node
        
        self.log.warning(f"Could not find method '{method_name}' with matching signature")
        sys.exit(-1)
    
    def _method_matches_signature(self, method_node: tree_sitter.Node, methodid) -> bool:
        """Check if method node matches the expected signature."""
        parameters_node = method_node.child_by_field_name("parameters")
        if not parameters_node:
            self.log.debug(f"Could not find parameters for method")
            return False
        
        params = [c for c in parameters_node.children if c.type == "formal_parameter"]
        
        if len(params) != len(methodid.extension.params):
            return False
        
        self.log.debug("Method parameters: %s", methodid.extension.params)
        self.log.debug("Found parameters: %s", params)
        
        # Basic parameter count match (could be extended for type checking)
        for actual_param in params:
            param_type = actual_param.child_by_field_name("type")
            if not param_type or not param_type.text:
                return False
            # TODO: Add more sophisticated type checking here
        
        return True
    
    def _get_called_method_bodies(self, body_node):
        called_bodies = []
        # Find all method invocations in the body
        call_query = tree_sitter.Query(self.java_language,
            """(method_invocation name: (identifier) @called_name) @call""")
        captures = tree_sitter.QueryCursor(call_query).captures(body_node)
        call_nodes = captures.get("call", [])
        for call_node in call_nodes:
            called_name_node = call_node.child_by_field_name("name")
            called_name = called_name_node.text.decode() if called_name_node and called_name_node.text else ""
            # Find method node in the same class
            method_query = tree_sitter.Query(self.java_language,
                f"""(method_declaration name: ((identifier) @method-name (#eq? @method-name "{called_name}"))) @method""")
            class_node = body_node.parent
            method_captures = tree_sitter.QueryCursor(method_query).captures(class_node)
            method_nodes = method_captures.get("method", [])
            for method_node in method_nodes:
                called_body = method_node.child_by_field_name("body")
                if called_body and called_body.text:
                    called_bodies.append(called_body)
                    # Recursively get bodies of methods called within this method
                    called_bodies.extend(self._get_called_method_bodies(called_body))
        return called_bodies

    def analyze_method_body(self, method_node: tree_sitter.Node) -> dict:
        """Analyze the method body and return prediction results for all outcomes."""
        body = method_node.child_by_field_name("body")

        self.predictions = Result()
        if not body or not body.text:
            self.log.warning("Could not find method body")
            return self.predictions.as_dict()

        # assert body
        # Append all called methods' bodies to the current body
        # all_bodies = [body] + self._get_called_method_bodies(body)
        
        # Debug: print method body lines
        # for body in all_bodies:
        #     if body and body.text:
        for line in body.text.splitlines():
            self.log.debug("line: %s", line.decode())
        
        # Check for assertions
        self._analyze_assertions(body)
        
        # Check for divide by zero
        self._analyze_divide_by_zero(body)
        
        # Check for array access (out of bounds)
        self._analyze_array_bounds(body)
        
        # Check for null pointer access
        self._analyze_null_pointer(body)
        
        # Check for infinite loops
        self._analyze_infinite_loops(body)

        self.predictions.ok.set(100 - max(
            [p.get() for p in self.predictions if p.title != "ok"]
        ))

        # Adjust not to get -inf points for method calls
        # TODO: improve
        for p in self.predictions:
            if p.get() == 0:
                p.set(5)

        # Fill in any missing predictions with defaults
        return self.predictions.as_dict()
    
    def _complete_predictions(self):
        """Fill in missing predictions with defaults and ensure they sum appropriately."""
        # defaults = Result.get_defaults()
        
        # # Fill in missing outcomes
        # for outcome in defaults:
        #     if outcome not in predictions:
        #         predictions[outcome] = "0%"
        
        # If we have high confidence in a specific outcome, reduce others
        # high_confidence_outcomes = [k for k, v in predictions.items() 
        #                            if v.endswith('%') and int(v[:-1]) >= 80]
        
        # if high_confidence_outcomes:
        #     # Reduce other outcomes when we have high confidence
        #     for outcome in predictions:
        #         if outcome not in high_confidence_outcomes:
        #             predictions[outcome] = "5%"
        
        # return predictions
        pass
    
    def _analyze_assertions(self, body_node: tree_sitter.Node) -> None:
        """Analyze assertions in the method body."""
        assert_query = tree_sitter.Query(
            self.java_language, 
            """(assert_statement) @assert"""
        )
        captures = tree_sitter.QueryCursor(assert_query).captures(body_node)
        assert_nodes = captures.get("assert", [])
        
        if not assert_nodes:
            self.log.debug("Did not find any assertions")
            self.predictions.assertion_error.set(0)
            return 
        
        # Check if any assertion is "assert false"
        for assert_node in assert_nodes:
            assertion_text = assert_node.text.decode() if assert_node.text else ""
            self.log.debug("Found assertion: %s", assertion_text)
            
            if "false" in assertion_text:
                self.log.debug("Found 'assert false' statement")
                self.predictions.assertion_error.set(90)
                return
        
        self.log.debug("Found assertion but not 'assert false'")
        self.predictions.assertion_error.set(60)
    
    def _analyze_divide_by_zero(self, body_node: tree_sitter.Node) -> None:
        """Analyze potential divide by zero operations."""
        # Look for division operations
        div_query = tree_sitter.Query(self.java_language, 
            """(binary_expression operator: "/" @div)""")
        
        captures = tree_sitter.QueryCursor(div_query).captures(body_node)
        div_nodes = captures.get("div", [])
        
        if not div_nodes:
            self.predictions.divide_by_zero.set(0)
            return
        
        # Simple check: look for literal "0" or "(expression - same_expression)"
        body_text = body_node.text.decode() if body_node.text else ""
        
        # Regex to match division by zero (e.g., "/ 0", "/0", "1/0", "x / 0")
        if re.search(r'/\s*0\b', body_text):
            self.log.debug("Found explicit divide by zero")
            self.predictions.divide_by_zero.set(95)
            return
        
        self.log.debug("Found division operations - potential divide by zero")
        self.predictions.divide_by_zero.set(60)
    
    def _analyze_array_bounds(self, body_node: tree_sitter.Node) -> None:
        """Analyze potential array out of bounds access."""
        # Look for array access expressions
        array_query = tree_sitter.Query(self.java_language,
            """(array_access) @array_access""")
        
        captures = tree_sitter.QueryCursor(array_query).captures(body_node)
        array_nodes = captures.get("array_access", [])
        
        if not array_nodes:
            return self.predictions.out_of_bounds.set(0)
        
        # TODO: Add more sophisticated analysis for bounds checking
        self.log.debug("Found array access operations")
        self.predictions.out_of_bounds.set(30)
    
    def _analyze_null_pointer(self, body_node: tree_sitter.Node) -> None:
        """Analyze potential null pointer dereferences."""
        # Look for explicit 'null' usage in the AST
        null_query = tree_sitter.Query(self.java_language,
            """(null_literal) @null""")
        captures = tree_sitter.QueryCursor(null_query).captures(body_node)
        null_nodes = captures.get("null", [])

        if null_nodes:
            self.log.debug("Found 'null' literal - potential null pointer dereference")
            self.predictions.null_pointer.set(40)
            return
        
        self.predictions.null_pointer.set(20)
    
    def _analyze_infinite_loops(self, body_node: tree_sitter.Node) -> None:
        """Analyze potential infinite loops."""
        # Look for while loops
        while_query = tree_sitter.Query(self.java_language,
            """(while_statement condition: (_) @condition)""")
        
        captures = tree_sitter.QueryCursor(while_query).captures(body_node)

        if not captures:
            self.predictions.infinite_loop.set(0)
            return

        condition_nodes = captures.get("condition", [])

        for condition in condition_nodes:
            condition_text = condition.text.decode() if condition.text else ""
            self.log.debug("Found while loop condition: %s", condition_text)
            
            if "true" in condition_text.lower():
                self.log.debug("Found while(true) - potential infinite loop")
                self.predictions.infinite_loop.set(70)
                return

        self.predictions.infinite_loop.set(10)
    
    def analyze_method(self) -> dict:
        """Main method to analyze a Java method and return all predictions."""
        tree = self.parse_source_file(self.methodid)
        class_name = str(self.methodid.classname.name)
        class_node = self.find_class_node(tree, class_name)
        method_node = self.find_method_node(class_node, self.methodid)
        return self.analyze_method_body(method_node)
    
    def format_predictions(self, predictions: dict) -> str:
        """Format predictions in the required output format."""
        # Ensure all required outcomes are present in the correct order
        outcomes = ["ok", "divide by zero", "assertion error", "out of bounds", "null pointer", "*"]
        
        formatted_lines = []
        for outcome in outcomes:
            probability = predictions.get(outcome, "0%")
            formatted_lines.append(f"{outcome};{probability}")
        
        return "\n".join(formatted_lines)


def main():
    # Analyze the specified method
    analyzer = JavaAnalyzer(False)
    predictions = analyzer.analyze_method()
    formatted_output = analyzer.format_predictions(predictions)
    print(formatted_output)


if __name__ == "__main__":
    main()
