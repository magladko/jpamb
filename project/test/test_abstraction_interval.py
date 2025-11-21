"""Tests for Interval abstraction."""

from project.abstractions.interval import Interval


def test_abstract() -> None:
    """Test abstract method."""
    # Empty set should give bot
    assert Interval.abstract(set()) == Interval.bot()

    # Single element
    assert Interval.abstract({5}) == Interval(5, 5)

    # Multiple elements
    assert Interval.abstract({1, 3, 5, 7}) == Interval(1, 7)
    assert Interval.abstract({-5, 0, 10}) == Interval(-5, 10)


def test_bot_and_top() -> None:
    """Test bot and top elements."""
    bot = Interval.bot()
    assert bot.is_bot()
    assert bot.lower > bot.upper

    top = Interval.top()
    assert not top.is_bot()
    assert top.lower == float("-inf")
    assert top.upper == float("inf")


def test_contains() -> None:
    """Test membership check."""
    interval = Interval(1, 10)
    assert 1 in interval
    assert 5 in interval  # noqa: PLR2004
    assert 10 in interval  # noqa: PLR2004
    assert 0 not in interval
    assert 11 not in interval  # noqa: PLR2004

    bot = Interval.bot()
    assert 5 not in bot  # noqa: PLR2004


def test_addition() -> None:
    """Test interval addition."""
    a = Interval(1, 3)
    b = Interval(2, 4)
    result = a + b
    assert result == Interval(3, 7)

    # With negative numbers
    a = Interval(-5, -1)
    b = Interval(2, 4)
    result = a + b
    assert result == Interval(-3, 3)


def test_subtraction() -> None:
    """Test interval subtraction."""
    a = Interval(5, 10)
    b = Interval(2, 3)
    result = a - b
    assert result == Interval(2, 8)


def test_multiplication() -> None:
    """Test interval multiplication."""
    a = Interval(2, 3)
    b = Interval(4, 5)
    result = a * b
    assert result == Interval(8, 15)

    # With negative numbers
    a = Interval(-2, 3)
    b = Interval(1, 4)
    result = a * b
    assert result == Interval(-8, 12)


def test_division() -> None:
    """Test interval division."""
    a = Interval(10, 20)
    b = Interval(2, 5)
    result = a // b
    # 10 // 5 = 2, 10 // 2 = 5, 20 // 5 = 4, 20 // 2 = 10
    assert result == Interval(2, 10)

    # Division by zero should return bot
    a = Interval(10, 20)
    b = Interval(-1, 1)
    result = a // b
    assert result.is_bot()


def test_modulus() -> None:
    """Test interval modulus."""
    a = Interval(10, 20)
    b = Interval(3, 7)
    result = a % b
    # Conservative: [0, 6] (max divisor - 1)
    assert result == Interval(0, 6)

    # Negative dividend
    a = Interval(-20, -10)
    b = Interval(3, 7)
    result = a % b
    assert result == Interval(-6, 0)


def test_lattice_ordering() -> None:
    """Test poset ordering (<=)."""
    a = Interval(3, 5)
    b = Interval(1, 7)
    assert a <= b  # a is contained in b
    assert not (b <= a)

    # Equal intervals
    a = Interval(3, 5)
    b = Interval(3, 5)
    assert a <= b
    assert b <= a

    # Bot is less than everything
    bot = Interval.bot()
    a = Interval(1, 5)
    assert bot <= a
    assert not (a <= bot)


def test_meet() -> None:
    """Test meet operator (intersection)."""
    a = Interval(1, 5)
    b = Interval(3, 7)
    result = a & b
    assert result == Interval(3, 5)

    # Non-overlapping intervals
    a = Interval(1, 3)
    b = Interval(5, 7)
    result = a & b
    assert result.is_bot()


def test_join() -> None:
    """Test join operator (convex hull)."""
    a = Interval(1, 3)
    b = Interval(5, 7)
    result = a | b
    assert result == Interval(1, 7)

    a = Interval(1, 5)
    b = Interval(3, 7)
    result = a | b
    assert result == Interval(1, 7)


def test_equality() -> None:
    """Test structural equality."""
    a = Interval(1, 5)
    b = Interval(1, 5)
    assert a == b

    a = Interval(1, 5)
    b = Interval(2, 5)
    assert a != b

    # Both bot should be equal
    bot1 = Interval.bot()
    bot2 = Interval.bot()
    assert bot1 == bot2


def test_comparison_le() -> None:
    """Test <= comparison with refinement."""
    a = Interval(0, 10)
    b = Interval(5, 15)
    result = a.le(b)

    # Both outcomes are possible
    assert True in result
    assert False in result

    # When true: a <= b, refine both intervals
    a_true, b_true = result[True]
    assert a_true == Interval(0, 10)
    assert b_true == Interval(5, 15)

    # When false: a > b
    a_false, b_false = result[False]
    assert a_false == Interval(6, 10)
    assert b_false == Interval(5, 9)


def test_comparison_eq() -> None:
    """Test == comparison with refinement."""
    a = Interval(0, 10)
    b = Interval(5, 15)
    result = a.eq(b)

    # Both outcomes are possible
    assert True in result
    assert False in result

    # When true: both must be in intersection
    a_true, b_true = result[True]
    assert a_true == Interval(5, 10)
    assert b_true == Interval(5, 10)


def test_string_representation() -> None:
    """Test string representation."""
    assert str(Interval(1, 5)) == "[1, 5]"
    assert str(Interval.bot()) == "⊥"
    assert str(Interval.top()) == "⊤"
