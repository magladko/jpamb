from jpamb import jvm


def test_singletons():

    assert jvm.Boolean() is jvm.Boolean()
    assert jvm.Int() is jvm.Int()
    assert jvm.Char() is jvm.Char()
    assert jvm.Int() is not jvm.Boolean()

    assert jvm.Array(jvm.Boolean()) is jvm.Array(jvm.Boolean())
    assert jvm.Array(jvm.Boolean()) is not jvm.Array(jvm.Int())


def test_value_parser():

    assert jvm.ValueParser.parse("1, 's', [I:10, 32]") == [
        jvm.Value.int(1),
        jvm.Value.char("s"),
        jvm.Value.array(jvm.Int(), [10, 32]),
    ]
