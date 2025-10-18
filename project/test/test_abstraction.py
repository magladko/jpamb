
from hypothesis import given
from hypothesis.strategies import integers, sets

from project.abstraction import SignSet


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

# @given(sets(integers()), sets(integers()))
# def test_sign_adds(xs, ys):
#     assert (
#       {x <= y for x in xs for y in ys}
#       <= arithmetic.compare("le", SignSet.abstract(xs), SignSet.abstract(ys))
#     )
