
from hypothesis import given
from hypothesis.strategies import integers, sets
from abstraction import SignSet

@given(sets(integers()))
def test_valid_abstraction(xs):
  s = SignSet.abstract(xs) 
  assert all(x in s for x in xs)