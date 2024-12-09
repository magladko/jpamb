from jpamb import jvm


def test_roundtrip_cases():

    methods = []

    with open("../stats/cases.txt") as fp:
        for c in fp:
            input = c.split(" ")[0]
            absmethod = jvm.MethodID.decode_absolute(input)
            methods.append(methods)
            assert jvm.MethodID.encode_absolute(absmethod) == input, f"{absmethod}"

    # Make sure we can sort methods
    assert sorted(methods) == sorted(sorted(methods))
