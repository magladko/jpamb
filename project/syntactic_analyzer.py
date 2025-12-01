import ast
import json
import os
import re
from pathlib import Path
from typing import cast
import javalang
import javalang.tree
import jpamb
from jpamb import jvm


COMMENT_KEYWORDS = [
    "DO NOT DELETE", "FIXME", "TODO", "IMPORTANT", "TEMP", "DEBUG", "HACK"
]


def determine_analysis_type(info: dict) -> str:
    # 1. Recursion → abstract
    if info["isRecursive"]:
        return "abstract"

    # 2. Method calls → abstract
    if len(info["methodCalls"]) > 0:
        return "abstract"

    # 3. Complex loops → abstract
    if len(info["whileLoops"]) > 0:
        return "abstract"
    if any("for" in loop for loop in info["forLoops"]):
        return "abstract"

    # 4. Parameters → abstract
    if len(info["parameters"]) > 0:
        return "abstract"

    # 5. Variable dependencies → abstract
    if len(info["dependencies"]) > 0:
        return "abstract"

    # Otherwise → concrete
    return "dynamic"


def extract_comments(source_code: str) -> list[str]:
    pattern = r"(//[^\n]*|/\*[\s\S]*?\*/)"
    comments = re.findall(pattern, source_code)
    return [c.strip() for c in comments]


def find_keyword_comments(comments: list[str]) -> list[str]:
    hits = []
    for c in comments:
        for kw in COMMENT_KEYWORDS:
            if kw.lower() in c.lower():
                hits.append(c)
                break
    return hits

def clean_annotations(source: str) -> str:
    cleaned_lines = []
    for line in source.splitlines():
        if line.strip().startswith("@"):
            cleaned_lines.append("")
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def find_method_start_line(source_lines: list[str], decl_line: int) -> int:
    for i in range(decl_line - 1, len(source_lines)):
        if "{" in source_lines[i]:
            return i + 1
    return decl_line


def find_method_end_line(source_lines: list[str], start_line: int) -> int:
    open_braces = 0
    for i in range(start_line - 1, len(source_lines)):
        line = source_lines[i]
        open_braces += line.count("{")
        open_braces -= line.count("}")
        if open_braces == 0 and i > start_line:
            return i + 1
    return len(source_lines)



def find_redundant_blocks(method: javalang.tree.MethodDeclaration) -> list[str]:
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
                redundant.append("Infinite while(true) loop may cause unreachable code")
            elif cond_val == "false":
                redundant.append("Unreachable while(false) loop")

    # Constant if-statements
    for _, ifstmt in method.filter(javalang.tree.IfStatement):
        cond = getattr(ifstmt, "condition", None)
        if isinstance(cond, javalang.tree.Literal):
            cond_val = getattr(cond, "value", None) or getattr(cond, "member", None)
            if cond_val == "true":
                redundant.append("If(true) else branch never executes")
            elif cond_val == "false":
                redundant.append("If(false) main branch never executes")

    # return; after while(true)
    for _, loop in method.filter(javalang.tree.WhileStatement):
        cond = getattr(loop, "condition", None)
        cond_val = getattr(cond, "value", None) \
            if isinstance(cond, javalang.tree.Literal) else None
        if cond_val == "true":
            parent_block = getattr(loop, "body", None)
            if parent_block and hasattr(parent_block, "statements"):
                stmts = parent_block.statements
                if stmts and isinstance(stmts[-1], javalang.tree.ReturnStatement):
                    redundant.append("Return after while(true) code after this is dead")

    # break / continue outside loops
    for _, _br in method.filter(javalang.tree.BreakStatement):
        redundant.append("Break used outside of any loop meaningless")
    for _, _cont in method.filter(javalang.tree.ContinueStatement):
        redundant.append("Continue used outside of any loop meaningless")

    statements = list(getattr(method, "body", []) or [])
    found_return = False
    for stmt in statements:
        if isinstance(stmt, javalang.tree.ReturnStatement):
            found_return = True
        elif found_return and isinstance(stmt, javalang.tree.LocalVariableDeclaration):
            redundant.extend([
                f"Variable '{decl.name}' declared after return - dead code"
                for decl in getattr(stmt, "declarators", [])
            ])


    return redundant


def analyze_dependencies(method: javalang.tree.MethodDeclaration) -> list[str]:
    """Find relationships like 'a = b + 1' → a depends on b."""
    dependencies = []
    for _, assign in method.filter(javalang.tree.Assignment):
        left = getattr(assign.expressionl, "member", None) or \
            getattr(assign.expressionl, "name", None)
        right = getattr(assign, "value", None)
        if left and right:
            dependencies.append(f"{left} depends on {right}")
    return dependencies


def analyze_java_file(methodid: jvm.AbsMethodID) -> list[dict]:
    """Analyze one .java file."""
    srcfile = jpamb.Suite().sourcefile(methodid.classname)
    with Path(srcfile).open(encoding="utf-8") as f:
        source = f.read()
    source_lines = source.splitlines()

    #Clean annotations before parsing
    source = clean_annotations(source)

    try:
        tree = javalang.parse.parse(source)
    except javalang.parser.JavaSyntaxError as e:
        print(f"Could not parse {srcfile}: {e}")
        return []


    comments = extract_comments(source)
    keyword_comments = find_keyword_comments(comments)
    results = []

    class_name = None
    for _, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = getattr(node, "name", "(anonymous)")

    for _, method in tree.filter(javalang.tree.MethodDeclaration):
        method = cast("javalang.tree.MethodDeclaration", method)
        start_line_decl = getattr(getattr(method, "position", None), "line", -1)
        start_line = find_method_start_line(source_lines, start_line_decl)
        end_line = find_method_end_line(source_lines, start_line)

        info = {
            "fileName": Path(srcfile).name,
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
            "methodCalls": [],
            "isRecursive": False,
            "removableCode": [],
            "typeOfAnalysis": None
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

        # Method calls
        calls = []
        for _, call in method.filter(javalang.tree.MethodInvocation):
            call_name = getattr(call, "member", None)
            qualifier = getattr(call, "qualifier", None)
            args = getattr(call, "arguments", [])
            pos = getattr(call, "position", None)

            if call_name in ("println", "print"):
                continue

            calls.append({
                "name": call_name,
                "qualifier": qualifier,
                "arguments": len(args),
                "line": pos.line if pos else None
            })

        info["methodCalls"] = calls

        # Variables
        for _, var in method.filter(javalang.tree.VariableDeclarator):
            var_name = getattr(var, "name", None)
            var_type = getattr(var, "type", None)
            if var_name:
                info["variables"].append(
                    f"{var_name} : {var_type}" if var_type else var_name
                )


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
                right_node = getattr(cond, "operandr", None)
                left_expr = getattr(cond, "operandl", None)
                left = getattr(left_expr, "member", None) \
                or getattr(left_expr, "name", None)
                right = getattr(right_node, "value", None)
                op = getattr(cond, "operator", None)

                if left and right and left.isdigit() and right.isdigit() and op:
                    le, r = int(left), int(right)
                    result = ast.literal_eval(f"{le}{op}{r}")
                    msg = f"If condition '{left} {op} {right}' always {result}"
                    info["deadByConstant"].append(msg)

        for _, call in method.filter(javalang.tree.MethodInvocation):
            call_name = getattr(call, "member", None)
            if call_name == info["methodName"]:
                info["isRecursive"] = True
                break

        info["typeOfAnalysis"] = determine_analysis_type(info)


        results.append(info)

    return results


def analyze_project(root_dir: str) -> None:
    all_results = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".java"):
                path = Path(subdir) / file
                file_results = analyze_java_file(path)
                all_results.extend(file_results)

    with Path.open("syntactic_output.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)

    print(f"Analysis complete. {len(all_results)} methods found.")
    print("Results saved to syntactic_output.json")


if __name__ == "__main__":
    analyze_project("src/main/java/jpamb/cases/")

