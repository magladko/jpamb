from project.abstractions.string_set import (
    StringDomain,
)


def test_string_domain_concatenation() -> None:
    hello = StringDomain.abstract({"he"})
    world = StringDomain.abstract({"llo"})
    combined = hello + world
    assert "hello" in combined


def test_string_domain_collapses_to_top_when_exceeding_budget() -> None:
    strings = {"s0", "s1", "s2", "s3", "s4", "s5"}  # MAX_TRACKED is 5
    result = StringDomain.abstract(strings)
    assert result.values is None


def test_string_domain_accepts_non_string_literals() -> None:
    domain = StringDomain.abstract({1, "2"})
    assert "1" in domain
    assert "2" in domain


def test_string_domain_eq_ne_behavior() -> None:
    a = StringDomain.abstract({"foo"})
    b = StringDomain.abstract({"foo"})
    c = StringDomain.abstract({"bar", "baz"})
    assert a.compare("eq", b) == {True: (a, b)}
    assert set(a.compare("eq", c)) == {False}
    assert set(a.compare("ne", c)) == {True}
