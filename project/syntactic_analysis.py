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
    """Completely strips Java annotations like @Case(...) or @Tag({...}) even across multiple lines."""
    # Remove anything that starts with @ and continues until the next line
    source = re.sub(
        r'@\w+[^\n]*(?:\n(?!\s*(public|private|protected|class|static|if|for|while|return)).*)*',
        '',
        source,
        flags=re.MULTILINE
    )
    return source



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

    # 🧹 Clean annotations before parsing
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
        info = {
            "fileName": os.path.basename(file_path),
            "className": class_name or "(anonymous)",
            "methodName": getattr(method, "name", "(unknown)"),
            "startLine": getattr(getattr(method, "position", None), "line", -1),
            "endLine": -1,
            "variables": [],
            "forLoops": [],
            "whileLoops": [],
            "constants": [],
            "comments": comments,
            "keywordComments": keyword_comments,
            "deadByConstant": [],
            "dependencies": []
        }

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
