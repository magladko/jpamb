"""Tests for i2s (int-to-short) cast operation."""

from hypothesis import given
from hypothesis import strategies as st

from project.abstractions.interval import Interval
from project.abstractions.signset import SignSet

# ============================================================================
# SIGNSET TESTS
# ============================================================================


def test_signset_i2s_zero() -> None:
    """Zero remains zero."""
    s = SignSet({"0"})
    result = s.i2s_cast()
    assert result == SignSet({"0"})


def test_signset_i2s_positive() -> None:
    """Positive could wrap to any sign."""
    s = SignSet({"+"})
    result = s.i2s_cast()
    assert result == SignSet({"+", "-", "0"})


def test_signset_i2s_negative() -> None:
    """Negative could wrap to any sign."""
    s = SignSet({"-"})
    result = s.i2s_cast()
    assert result == SignSet({"+", "-", "0"})


def test_signset_i2s_mixed() -> None:
    """Mixed signs result in top."""
    s = SignSet({"+", "-", "0"})
    result = s.i2s_cast()
    assert result == SignSet({"+", "-", "0"})


def test_signset_i2s_positive_zero() -> None:
    """Positive and zero result in top."""
    s = SignSet({"+", "0"})
    result = s.i2s_cast()
    assert result == SignSet({"+", "-", "0"})


def test_signset_i2s_negative_zero() -> None:
    """Negative and zero result in top."""
    s = SignSet({"-", "0"})
    result = s.i2s_cast()
    assert result == SignSet({"+", "-", "0"})


def test_signset_i2s_bot() -> None:
    """Bottom remains bottom."""
    s = SignSet.bot()
    result = s.i2s_cast()
    assert result == SignSet.bot()


# ============================================================================
# INTERVAL TESTS
# ============================================================================


def test_interval_i2s_in_range() -> None:
    """Values in short range remain unchanged."""
    i = Interval(100, 200)
    result = i.i2s_cast()
    assert result == Interval(100, 200)


def test_interval_i2s_boundary_max() -> None:
    """Maximum short value."""
    i = Interval(32767, 32767)
    result = i.i2s_cast()
    assert result == Interval(32767, 32767)


def test_interval_i2s_boundary_min() -> None:
    """Minimum short value."""
    i = Interval(-32768, -32768)
    result = i.i2s_cast()
    assert result == Interval(-32768, -32768)


def test_interval_i2s_single_wrap_positive() -> None:
    """Single value just over max wraps to min."""
    i = Interval(32768, 32768)
    result = i.i2s_cast()
    assert result == Interval(-32768, -32768)


def test_interval_i2s_single_wrap_negative() -> None:
    """Single value just under min wraps to max."""
    i = Interval(-32769, -32769)
    result = i.i2s_cast()
    assert result == Interval(32767, 32767)


def test_interval_i2s_large_interval() -> None:
    """Large interval returns full short range."""
    i = Interval(0, 100000)
    result = i.i2s_cast()
    assert result == Interval(-32768, 32767)


def test_interval_i2s_full_cycle() -> None:
    """Interval spanning 65536 returns full range."""
    i = Interval(0, 65536)
    result = i.i2s_cast()
    assert result == Interval(-32768, 32767)


def test_interval_i2s_negative_to_positive() -> None:
    """Large negative interval."""
    i = Interval(-100000, -50000)
    result = i.i2s_cast()
    # Should return full range due to multiple wraps
    assert result == Interval(-32768, 32767)


def test_interval_i2s_bot() -> None:
    """Bottom remains bottom."""
    i = Interval.bot()
    result = i.i2s_cast()
    assert result.is_bot()


def test_interval_i2s_top() -> None:
    """Top returns full short range."""
    i = Interval.top()
    result = i.i2s_cast()
    assert result == Interval(-32768, 32767)


def test_interval_i2s_partial_overlap_low() -> None:
    """Interval partially below short range."""
    i = Interval(-32800, -32700)
    result = i.i2s_cast()
    # -32800 wraps to 32736, -32700 wraps to 32836 (then to -31700)
    # This should handle wrapping correctly
    assert result.lower >= -32768  # noqa: PLR2004
    assert result.upper <= 32767  # noqa: PLR2004


def test_interval_i2s_partial_overlap_high() -> None:
    """Interval partially above short range."""
    i = Interval(32700, 32800)
    result = i.i2s_cast()
    # 32700 is in range, 32800 wraps
    assert result.lower >= -32768  # noqa: PLR2004
    assert result.upper <= 32767  # noqa: PLR2004


def test_interval_i2s_small_positive() -> None:
    """Small positive values stay unchanged."""
    i = Interval(1, 10)
    result = i.i2s_cast()
    assert result == Interval(1, 10)


def test_interval_i2s_small_negative() -> None:
    """Small negative values stay unchanged."""
    i = Interval(-10, -1)
    result = i.i2s_cast()
    assert result == Interval(-10, -1)


def test_interval_i2s_zero() -> None:
    """Zero remains zero."""
    i = Interval(0, 0)
    result = i.i2s_cast()
    assert result == Interval(0, 0)


def test_interval_i2s_around_zero() -> None:
    """Interval around zero."""
    i = Interval(-100, 100)
    result = i.i2s_cast()
    assert result == Interval(-100, 100)


# ============================================================================
# PROPERTY-BASED TESTS (SOUNDNESS)
# ============================================================================


def i2s_concrete(value: int) -> int:
    """Concrete implementation of i2s for testing."""
    # Truncate to 16 bits
    truncated = value & 0xFFFF
    # Sign-extend
    if truncated >= 32768:  # noqa: PLR2004
        return truncated - 65536
    return truncated


@given(st.integers(min_value=-1000000, max_value=1000000))
def test_interval_i2s_soundness_single(value: int) -> None:
    """Property: For any concrete value, i2s(value) is in i2s_cast([value, value])."""
    concrete_result = i2s_concrete(value)
    abstract_input = Interval(value, value)
    abstract_result = abstract_input.i2s_cast()

    # Check soundness: concrete result must be in abstract result
    assert abstract_result.lower <= concrete_result <= abstract_result.upper


@given(
    st.integers(min_value=-10000, max_value=100000),
    st.integers(min_value=0, max_value=1000),
)
def test_interval_i2s_soundness_range(start: int, width: int) -> None:
    """Property: For any interval, all concrete results are in abstract result."""
    end = start + width
    abstract_input = Interval(start, end)
    abstract_result = abstract_input.i2s_cast()

    # Sample some concrete values from the interval
    samples = [start, end, (start + end) // 2]
    for value in samples:
        if start <= value <= end:
            concrete_result = i2s_concrete(value)
            assert abstract_result.lower <= concrete_result <= abstract_result.upper, (
                f"Soundness violation: {concrete_result} not in {abstract_result}"
                f"(input: [{start}, {end}])"
            )


@given(st.integers(min_value=-100000, max_value=100000))
def test_signset_i2s_soundness(value: int) -> None:
    """For any concrete value, sign(i2s(value)) is in i2s_cast(sign(value))."""
    concrete_result = i2s_concrete(value)

    abstract_input = SignSet.abstract({value})
    abstract_result = abstract_input.i2s_cast()

    # Determine sign of result
    if concrete_result > 0:
        result_sign = "+"
    elif concrete_result < 0:
        result_sign = "-"
    else:
        result_sign = "0"

    # Check soundness: result sign must be in abstract result
    assert result_sign in abstract_result.signs


# ============================================================================
# MONOTONICITY TESTS
# ============================================================================


def test_interval_i2s_monotonicity() -> None:
    """Property: A ⊑ B ⟹ i2s_cast(A) ⊑ i2s_cast(B)."""
    # [100, 200] ⊑ [50, 300]
    a = Interval(100, 200)
    b = Interval(50, 300)

    result_a = a.i2s_cast()
    result_b = b.i2s_cast()

    # Check monotonicity: result_a ⊑ result_b
    # This means result_a.lower >= result_b.lower and result_a.upper <= result_b.upper
    assert result_b.lower <= result_a.lower
    assert result_a.upper <= result_b.upper


def test_signset_i2s_monotonicity() -> None:
    """Property: A ⊑ B ⟹ i2s_cast(A) ⊑ i2s_cast(B)."""
    # {+} ⊑ {+, -}
    a = SignSet({"+"})
    b = SignSet({"+", "-"})

    result_a = a.i2s_cast()
    result_b = b.i2s_cast()

    # Check monotonicity: result_a ⊑ result_b
    # This means result_a.signs ⊆ result_b.signs
    assert result_a.signs.issubset(result_b.signs)
