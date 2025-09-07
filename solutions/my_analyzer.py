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
    
    def analyze_method_body(self, method_node: tree_sitter.Node) -> str:
        """Analyze the method body and return prediction result."""
        body = method_node.child_by_field_name("body")
        if not body or not body.text:
            self.log.warning("Could not find method body")
            return "assertion error;20%"
        
        # Debug: print method body lines
        for line in body.text.splitlines():
            self.log.debug("line: %s", line.decode())
        
        return self._analyze_assertions(body)
    
    def _analyze_assertions(self, body_node: tree_sitter.Node) -> str:
        """Analyze assertions in the method body."""
        assert_query = tree_sitter.Query(self.java_language, """(assert_statement) @assert""")
        captures = tree_sitter.QueryCursor(assert_query).captures(body_node)
        assert_nodes = captures.get("assert", [])
        
        if not assert_nodes:
            self.log.debug("Did not find any assertions")
            return "assertion error;20%"
        
        # Check if any assertion is "assert false"
        for assert_node in assert_nodes:
            assertion_text = assert_node.text.decode() if assert_node.text else ""
            self.log.debug("Found assertion: %s", assertion_text)
            
            if "false" in assertion_text:
                self.log.debug("Found 'assert false' statement")
                return "assertion error;90%"
        
        self.log.debug("Found assertion but not 'assert false'")
        return "assertion error;80%"
    
    def analyze_method(self) -> str:
        """Main method to analyze a Java method and return prediction."""
        tree = self.parse_source_file(self.methodid)
        class_name = str(self.methodid.classname.name)
        class_node = self.find_class_node(tree, class_name)
        method_node = self.find_method_node(class_node, self.methodid)
        return self.analyze_method_body(method_node)


def main():
    """Main entry point for the analyzer."""
    analyzer = JavaAnalyzer()
    
    # if len(sys.argv) == 2 and sys.argv[1] == "info":
    #     # Output analyzer information - using the original jpamb.getmethodid result format
    #     print("My First Analyzer")
    #     print("1.0")
    #     print("Garbage Spillers")
    #     print("syntatic,python")
    #     print("Linux-6.8.0-79-generic-x86_64-with-glibc2.39")
    # else:
        # Analyze the specified method
    result = analyzer.analyze_method()
    print(result)


if __name__ == "__main__":
    main()
