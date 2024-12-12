from jpamb import jvm, model

from pathlib import Path


def skip_test_bytecode():

    suite = model.Suite(Path("../").absolute())

    for c in suite.cases:
        methods = suite.decompile(c.methodid.classname)["methods"]
        for method in methods:
            if method["name"] == c.methodid.extension.name:
                break
        else:
            assert False, f"Could not find {c.methodid}"

        for opcode in method["code"]["bytecode"]:
            print(opcode)
            result = jvm.Opcode.from_json(opcode)
            print(result, "/", result.real())
            assert not isinstance(result, dict), opcode

        break

    assert False
