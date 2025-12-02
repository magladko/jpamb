import os
import re
import json
import javalang
import javalang.tree

COMMENT_KEYWORDS = [
    "DO NOT DELETE", "FIXME", "TODO", "IMPORTANT", "TEMP", "DEBUG", "HACK"
]


def extract_comments(source_code):
    """Extracts // and /* ... */ comments."""
    pattern = r"(//[^\n]*|/\*[\s\S]*?\*/)"
    comments = re.findall(pattern, source_code)
    return [c.strip() for c in comments]


def find_keyword_comments(comments):
    """Finds comments with important keywords."""
    hits = []
    for c in comments:
        for kw in COMMENT_KEYWORDS:
            if kw.lower() in c.lower():
                hits.append(c)
                break
    return hits

def clean_annotations(source):
    cleaned_lines = []
    for line in source.splitlines():
        if line.strip().startswith("@"):
            cleaned_lines.append("") 
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def find_method_start_line(source_lines, decl_line):
    for i in range(decl_line - 1, len(source_lines)):
        if '{' in source_lines[i]:
            return i + 1
    return decl_line


def find_method_end_line(source_lines, start_line):
    open_braces = 0
    for i in range(start_line - 1, len(source_lines)):
        line = source_lines[i]
        open_braces += line.count('{')
        open_braces -= line.count('}')
        if open_braces == 0 and i > start_line:
            return i + 1 
    return len(source_lines)



def find_redundant_blocks(method):
    """Detect useless code blocks, constant conditions, and unreachable or meaningless syntax."""
    redundant = []

    # Empty blocks
    for _, block in method.filter(javalang.tree.BlockStatement):
        statements = getattr(block, "statements", None)
        if statements is None or len(statements) == 0:
            redundant.append("Empty block {}")

    # Constant while-loops
    for _, loop in method.filter(javalang.tree.WhileStatement):
        cond = getattr(loop, "condition", None)
        if isinstance(cond, javalang.tree.Literal):
            cond_val = getattr(cond, "value", None) or getattr(cond, "member", None)
            if cond_val == "true":
                redundant.append("Infinite while(true) loop – may cause unreachable code after it")
            elif cond_val == "false":
                redundant.append("Unreachable while(false) loop")

    # Constant if-statements
    for _, ifstmt in method.filter(javalang.tree.IfStatement):
        cond = getattr(ifstmt, "condition", None)
        if isinstance(cond, javalang.tree.Literal):
            cond_val = getattr(cond, "value", None) or getattr(cond, "member", None)
            if cond_val == "true":
                redundant.append("If(true) – else branch never executes")
            elif cond_val == "false":
                redundant.append("If(false) – main branch never executes")

    # return; after while(true)
    for _, loop in method.filter(javalang.tree.WhileStatement):
        cond = getattr(loop, "condition", None)
        cond_val = getattr(cond, "value", None) if isinstance(cond, javalang.tree.Literal) else None
        if cond_val == "true":
            parent_block = getattr(loop, "body", None)
            if parent_block and hasattr(parent_block, "statements"):
                stmts = parent_block.statements
                if stmts and isinstance(stmts[-1], javalang.tree.ReturnStatement):
                    redundant.append("Return after while(true) – code after this is dead")

    # break / continue outside loops
    for _, br in method.filter(javalang.tree.BreakStatement):
        redundant.append("Break used outside of any loop – meaningless")
    for _, cont in method.filter(javalang.tree.ContinueStatement):
        redundant.append("Continue used outside of any loop – meaningless")

    statements = list(method.body or [])
    found_return = False
    for stmt in statements:
        if isinstance(stmt, javalang.tree.ReturnStatement):
            found_return = True
        elif found_return and isinstance(stmt, javalang.tree.LocalVariableDeclaration):
            for decl in getattr(stmt, "declarators", []):
                redundant.append(f"Variable '{decl.name}' declared after return – dead code")

    return redundant


def analyze_dependencies(method):
    """Find relationships like 'a = b + 1' → a depends on b."""
    dependencies = []
    for _, assign in method.filter(javalang.tree.Assignment):
        left = getattr(assign.expressionl, "member", None) or getattr(assign.expressionl, "name", None)
        right = getattr(assign, "value", None)
        if left and right:
            dependencies.append(f"{left} depends on {right}")
    return dependencies


def analyze_java_file(file_path):
    """Analyze one .java file."""
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    source_lines = source.splitlines()

    #Clean annotations before parsing
    source = clean_annotations(source)

    try:
        tree = javalang.parse.parse(source)
    except Exception as e:
        print(f"Could not parse {file_path}: {e}")
        return []

    comments = extract_comments(source)
    keyword_comments = find_keyword_comments(comments)
    results = []

    class_name = None
    for _, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = getattr(node, "name", "(anonymous)")

    for _, method in tree.filter(javalang.tree.MethodDeclaration):

        start_line_decl = getattr(getattr(method, "position", None), "line", -1)
        start_line = find_method_start_line(source_lines, start_line_decl)
        end_line = find_method_end_line(source_lines, start_line)

        info = {
            "fileName": os.path.basename(file_path),
            "className": class_name or "(anonymous)",
            "methodName": getattr(method, "name", "(unknown)"),
            "parameters": [],
            "start_line": start_line,
            "end_line": end_line,
            "variables": [],
            "forLoops": [],
            "whileLoops": [],
            "constants": [],
            "comments": comments,
            "keywordComments": keyword_comments,
            "deadByConstant": [],
            "dependencies": [],
            "isRecursive": False,
            "removableCode": [],
            "typeOfAnalysis": "dynamic"
        }

        # Parameters
        params = []
        for param in getattr(method, "parameters", []):
            ptype = getattr(param.type, "name", None)
            pname = getattr(param, "name", None)
            if ptype and pname:
                params.append(f"{ptype} {pname}")
            elif pname:
                params.append(pname)
        info["parameters"] = params
        info["typeOfAnalysis"] = "abstract" if len(params) > 0 else "dynamic"


        # Variables
        for _, var in method.filter(javalang.tree.VariableDeclarator):
            var_name = getattr(var, "name", None)
            var_type = getattr(var, "type", None)
            if var_name:
                info["variables"].append(f"{var_name} : {var_type}" if var_type else var_name)

        # Loops
        for _, loop in method.filter(javalang.tree.ForStatement):
            info["forLoops"].append(str(loop))
        for _, loop in method.filter(javalang.tree.WhileStatement):
            info["whileLoops"].append(str(loop))

        # Constants
        for _, literal in method.filter(javalang.tree.Literal):
            val = getattr(literal, "value", "")
            if val.isdigit():
                info["constants"].append(val)

        # Dependencies
        info["dependencies"] = analyze_dependencies(method)
        info["removableCode"] = find_redundant_blocks(method)

        # Constant-based dead code
        for _, ifstmt in method.filter(javalang.tree.IfStatement):
            cond = getattr(ifstmt, "condition", None)
            if isinstance(cond, javalang.tree.BinaryOperation):
                left_node = getattr(cond, "operandl", None)
                right_node = getattr(cond, "operandr", None)
                left = getattr(left_node, "value", None)
                right = getattr(right_node, "value", None)
                op = getattr(cond, "operator", None)

                if left and right and left.isdigit() and right.isdigit() and op:
                    l, r = int(left), int(right)
                    try:
                        result = eval(f"{l}{op}{r}")
                        info["deadByConstant"].append(f"If condition '{left} {op} {right}' always {result}")
                    except Exception:
                        pass

        for _, call in method.filter(javalang.tree.MethodInvocation):
            call_name = getattr(call, "member", None)
            if call_name == info["methodName"]:
                info["isRecursive"] = True
                break

        results.append(info)

    return results


def analyze_project(root_dir):
    all_results = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java"):
                path = os.path.join(subdir, file)
                file_results = analyze_java_file(path)
                all_results.extend(file_results)

    with open("syntactic_output.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)

    print(f"Analysis complete. {len(all_results)} methods found.")
    print("Results saved to syntactic_output.json")


if __name__ == "__main__":
    analyze_project("src/main/java/jpamb/cases/")
