from project.abstractions.interval_double import (
    DoubleDomain,
)


def test_double_interval_arithmetic() -> None:
    lo = DoubleDomain.abstract({1.0})
    hi = DoubleDomain.abstract({2.0})
    summed = lo + hi
    expected_sum = 3.0
    assert expected_sum in summed

def test_double_interval_intersection_and_ordering() -> None:
    a = DoubleDomain.abstract({-2.0, 0.0})
    b = DoubleDomain.abstract({-1.0, 1.0})
    intersection = a & b
    assert intersection.lower == -1.0
    assert intersection.upper == 0.0
    assert intersection <= a

def test_double_division_by_interval_crossing_zero_yields_top() -> None:
    numerator = DoubleDomain.abstract({5.0})
    denominator = DoubleDomain.abstract({-1.0, 1.0})
    result = numerator / denominator
    assert result == DoubleDomain.top()


def test_double_comparisons_respect_bounds() -> None:
    small = DoubleDomain.abstract({-2.0, 0.0})
    large = DoubleDomain.abstract({5.0, 6.0})
    assert small.compare("lt", large) == {True: (small, large)}
    assert large.compare("gt", small) == {True: (large, small)}
