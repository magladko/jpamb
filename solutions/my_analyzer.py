#!/usr/bin/env python3
import sys
import logging
import tree_sitter
import tree_sitter_java

import jpamb

class JavaAnalyzer:
    """A Java program analysis tool that predicts method outcomes."""
    
    def __init__(self):
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
            ["syntatic", "python"],
            for_science=True,
        )
        
        # Optional debugging setup
        # self._setup_debugger()
    
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
    
    def analyze_method_body(self, method_node: tree_sitter.Node) -> dict:
        """Analyze the method body and return prediction results for all outcomes."""
        body = method_node.child_by_field_name("body")
        if not body or not body.text:
            self.log.warning("Could not find method body")
            return self._get_default_predictions()
        
        # Debug: print method body lines
        for line in body.text.splitlines():
            self.log.debug("line: %s", line.decode())
        
        # Analyze different types of potential issues
        predictions = {}
        
        # Check for assertions
        assertion_result = self._analyze_assertions(body)
        predictions.update(assertion_result)
        
        # Check for divide by zero
        divide_by_zero_result = self._analyze_divide_by_zero(body)
        predictions.update(divide_by_zero_result)
        
        # Check for array access (out of bounds)
        array_bounds_result = self._analyze_array_bounds(body)
        predictions.update(array_bounds_result)
        
        # Check for null pointer access
        null_pointer_result = self._analyze_null_pointer(body)
        predictions.update(null_pointer_result)
        
        # Check for infinite loops
        infinite_loop_result = self._analyze_infinite_loops(body)
        predictions.update(infinite_loop_result)
        
        # Fill in any missing predictions with defaults
        return self._complete_predictions(predictions)
    
    def _get_default_predictions(self) -> dict:
        """Return default predictions when analysis fails."""
        return {
            "ok": "50%",
            "divide by zero": "50%",
            "assertion error": "50%",
            "out of bounds": "50%",
            "null pointer": "50%",
            "*": "0%"
        }
    
    def _complete_predictions(self, predictions: dict) -> dict:
        """Fill in missing predictions with defaults and ensure they sum appropriately."""
        defaults = self._get_default_predictions()
        
        # Fill in missing outcomes
        for outcome in defaults:
            if outcome not in predictions:
                predictions[outcome] = "0%"
        
        # If we have high confidence in a specific outcome, reduce others
        high_confidence_outcomes = [k for k, v in predictions.items() 
                                   if v.endswith('%') and int(v[:-1]) >= 80]
        
        if high_confidence_outcomes:
            # Reduce other outcomes when we have high confidence
            for outcome in predictions:
                if outcome not in high_confidence_outcomes:
                    predictions[outcome] = "5%"
        
        return predictions
    
    def _analyze_assertions(self, body_node: tree_sitter.Node) -> dict:
        """Analyze assertions in the method body."""
        assert_query = tree_sitter.Query(self.java_language, """(assert_statement) @assert""")
        captures = tree_sitter.QueryCursor(assert_query).captures(body_node)
        assert_nodes = captures.get("assert", [])
        
        if not assert_nodes:
            self.log.debug("Did not find any assertions")
            return {}
        
        # Check if any assertion is "assert false"
        for assert_node in assert_nodes:
            assertion_text = assert_node.text.decode() if assert_node.text else ""
            self.log.debug("Found assertion: %s", assertion_text)
            
            if "false" in assertion_text:
                self.log.debug("Found 'assert false' statement")
                return {"assertion error": "90%"}
        
        self.log.debug("Found assertion but not 'assert false'")
        return {"assertion error": "80%"}
    
    def _analyze_divide_by_zero(self, body_node: tree_sitter.Node) -> dict:
        """Analyze potential divide by zero operations."""
        # Look for division operations
        div_query = tree_sitter.Query(self.java_language, 
            """(binary_expression operator: "/" @div)""")
        
        captures = tree_sitter.QueryCursor(div_query).captures(body_node)
        div_nodes = captures.get("div", [])
        
        if not div_nodes:
            return {}
        
        # Simple check: look for literal "0" or "(expression - same_expression)"
        body_text = body_node.text.decode() if body_node.text else ""
        
        # if "/ 0" in body_text or "1/0" in body_text:
        #     self.log.debug("Found explicit divide by zero")
        #     return {"divide by zero": "95%"}
        
        self.log.debug("Found division operations - potential divide by zero")
        return {"divide by zero": "50%"}
    
    def _analyze_array_bounds(self, body_node: tree_sitter.Node) -> dict:
        """Analyze potential array out of bounds access."""
        # Look for array access expressions
        array_query = tree_sitter.Query(self.java_language,
            """(array_access) @array_access""")
        
        captures = tree_sitter.QueryCursor(array_query).captures(body_node)
        array_nodes = captures.get("array_access", [])
        
        if not array_nodes:
            return {}
        
        # TODO: Add more sophisticated analysis for bounds checking
        self.log.debug("Found array access operations")
        return {"out of bounds": "20%"}
    
    def _analyze_null_pointer(self, body_node: tree_sitter.Node) -> dict:
        """Analyze potential null pointer dereferences."""
        body_text = body_node.text.decode() if body_node.text else ""
        
        # Simple check for null assignments followed by usage
        if "= null" in body_text:
            self.log.debug("Found null assignment - potential null pointer")
            return {"null pointer": "40%"}
        
        return {}
    
    def _analyze_infinite_loops(self, body_node: tree_sitter.Node) -> dict:
        """Analyze potential infinite loops."""
        # Look for while loops
        while_query = tree_sitter.Query(self.java_language,
            """(while_statement condition: (_) @condition)""")
        
        captures = tree_sitter.QueryCursor(while_query).captures(body_node)
        condition_nodes = captures.get("condition", [])
        
        for condition in condition_nodes:
            condition_text = condition.text.decode() if condition.text else ""
            self.log.debug("Found while loop condition: %s", condition_text)
            
            if "true" in condition_text.lower():
                self.log.debug("Found while(true) - potential infinite loop")
                return {"*": "80%"}
        
        return {}
    
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
        analyzer = JavaAnalyzer()
        predictions = analyzer.analyze_method()
        formatted_output = analyzer.format_predictions(predictions)
        print(formatted_output)


if __name__ == "__main__":
    main()
