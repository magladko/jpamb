from typing import get_args

from hypothesis import given
from hypothesis.strategies import integers, sampled_from, sets

from project.abstraction import Arithmetic, Comparison, SignSet


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
            <= Arithmetic.compare("le", SignSet.abstract(xs), SignSet.abstract(ys))
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

    assert isinstance(result, set)
    assert all(isinstance(x, bool) for x in result)
    if len(xs) > 0 and len(ys) > 0:
        assert True in result or False in result
