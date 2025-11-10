from itertools import chain
from typing import get_args

from hypothesis import given
from hypothesis.strategies import integers, sampled_from, sets

from project.abstraction import Comparison, SignSet


@given(sets(integers()))
def test_valid_abstraction(xs: set[int]) -> None:
    s = SignSet.abstract(xs)
    assert all(x in s for x in xs)


@given(sets(integers()), sets(integers()))
def test_sign_adds(xs: set[int], ys: set[int]) -> None:
    assert (
        SignSet.abstract({x + y for x in xs for y in ys})
        <= SignSet.abstract(xs) + SignSet.abstract(ys)
    )


@given(sets(integers()), sets(integers()))
def test_sign_compare_le(xs: set[int], ys: set[int]) -> None:
    assert ({x <= y for x in xs for y in ys}
            <= SignSet.abstract(xs).compare("le", SignSet.abstract(ys)).keys()
            )

@given(
    sets(integers()),
    sets(integers()),
    sampled_from(get_args(Comparison.__value__))
)
def test_compare_returns_valid_bool_set_all_ops(
    xs: set[int], ys: set[int], op: Comparison
) -> None:
    s1 = SignSet.abstract(xs)
    s2 = SignSet.abstract(ys)

    result = s1.compare(op, s2)
    sign_sets = list(chain.from_iterable(result.values()))

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)
    assert all(isinstance(v, SignSet) for v in sign_sets)

    if len(xs) > 0 and len(ys) > 0:
        assert True in result or False in result

def test_singset_binary_comparison() -> None:
    s1 = SignSet({"0", "-"})
    s2 = SignSet({"0", "+"})

    # {0, -} < {0, +}
    # True  -> {0, -}, {0, +}
    # False -> {0}, {0}
    lt_result = s1.lt(s2)
    assert lt_result == {
        True: (SignSet({"0", "-"}), SignSet({"0", "+"})),
        False: (SignSet({"0"}), SignSet({"0"}))
    }

    s1 = SignSet({"0"})
    s2 = SignSet({"0", "+"})
    # {0} < {0, +}
    # True  -> {0}, {+}
    # False -> {0}, {0}
    lt_result = s1.lt(s2)
    assert lt_result == {
        True: (SignSet({"0"}), SignSet({"+"})),
        False: (SignSet({"0"}), SignSet({"0"}))
    }
