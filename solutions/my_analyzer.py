#!/usr/bin/env python3
import sys
import logging
import tree_sitter
import tree_sitter_java

import jpamb

methodid = jpamb.getmethodid(
    "My First Analyzer",
    "1.0",
    "Garbage Spillers",
    ["syntatic", "python"],
    for_science=True,
)

try:
    import debugpy
    debugpy.listen(5678)
    debugpy.wait_for_client()
except ImportError:
    pass

JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
parser = tree_sitter.Parser(JAVA_LANGUAGE)

log = logging
log.basicConfig(level=logging.DEBUG)


srcfile = jpamb.Suite().sourcefile(methodid.classname)

with open(srcfile, "rb") as f:
    log.debug("parse sourcefile %s", srcfile)
    tree = parser.parse(f.read())

simple_classname = str(methodid.classname.name)

log.debug(f"{simple_classname}")

# To figure out how to write these you can consult the
# https://tree-sitter.github.io/tree-sitter/playground
class_q = tree_sitter.Query(JAVA_LANGUAGE,
    f"""
    (class_declaration 
        name: ((identifier) @class-name 
               (#eq? @class-name "{simple_classname}"))) @class
    """)

for node in tree_sitter.QueryCursor(class_q).captures(tree.root_node)["class"]:
    break
else:
    log.error(f"could not find a class of name {simple_classname} in {srcfile}")

    sys.exit(-1)

log.debug("Found class %s", node.range)

method_name = methodid.extension.name

method_q = tree_sitter.Query(JAVA_LANGUAGE,
    f"""
    (method_declaration name: 
      ((identifier) @method-name (#eq? @method-name "{method_name}"))
    ) @method
"""
)

for node in tree_sitter.QueryCursor(method_q).captures(node)["method"]:

    if not (p := node.child_by_field_name("parameters")):
        log.debug(f"Could not find parameteres of {method_name}")
        continue

    params = [c for c in p.children if c.type == "formal_parameter"]

    if len(params) != len(methodid.extension.params):
        continue

    log.debug(methodid.extension.params)
    log.debug(params)

    for tn, t in zip(methodid.extension.params, params):
        if (tp := t.child_by_field_name("type")) is None:
            break

        if tp.text is None:
            break

        # todo check for type.
    else:
        break
else:
    log.warning(f"could not find a method of name {method_name} in {simple_classname}")
    sys.exit(-1)

log.debug("Found method %s %s", method_name, node.range)

body = node.child_by_field_name("body")
assert body and body.text
for t in body.text.splitlines():
    log.debug("line: %s", t.decode())

assert_q = tree_sitter.Query(JAVA_LANGUAGE, f"""(assert_statement) @assert""")

assert_found = False
assert_false_found = False

for node, t in tree_sitter.QueryCursor(assert_q).captures(body).items():
    if node == "assert":
        for assert_node in t:
            assert_found = True
            log.debug("Found assertion: %s", assert_node.text.decode() if assert_node.text else "")
            # Check if this is specifically "assert false"
            if assert_node.text and b"false" in assert_node.text:
                assert_false_found = True
        break

if not assert_found:
    log.debug("Did not find any assertions")
    print("assertion error;20%")
    sys.exit(0)

if assert_false_found:
    log.debug("Found 'assert false' statement")
    print("assertion error;90%")
else:
    log.debug("Found assertion but not 'assert false'")
    print("assertion error;80%")
sys.exit(0)
