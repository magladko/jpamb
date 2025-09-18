from jpamb import jvm, model

from pathlib import Path


def test_bytecode():
    suite = model.Suite()
    for c in suite.cases:
        methods = suite.findclass(c.methodid.classname)["methods"]
        for method in methods:
            if method["name"] == c.methodid.extension.name:
                break
        else:
            assert False, f"Could not find {c.methodid}"

        opcode_count = 0
        for opcode in method["code"]["bytecode"]:
            print(opcode)
            result = jvm.Opcode.from_json(opcode)
            print(result, "/", result.real())
            assert not isinstance(result, dict), opcode
            opcode_count += 1

        assert opcode_count > 0, "No opcodes were processed"

        break
