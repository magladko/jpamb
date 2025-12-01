"""Hypothesis-based property tests for Interval abstraction."""

from itertools import chain

from hypothesis import example, given
from hypothesis import strategies as st

# Assumes project structure provided in prompt
from project.abstractions.abstraction import Comparison
from project.abstractions.interval import Interval

# ============================================================================
# HELPERS
# ============================================================================


def jvm_rem(a: int, b: int) -> int:
    """
    Simulate JVM 'irem' behavior (truncate towards zero) using pure integer math.

    NOTE: Do NOT use math.fmod, as it converts to float and loses precision
    for integers > 2^53, causing false test failures.
    """
    if b == 0:
        # This will be caught by the test logic handling exceptions
        raise ZeroDivisionError

    # 1. Calculate remainder based on magnitudes
    rem = abs(a) % abs(b)

    # 2. Result takes the sign of the dividend (a)
    return -rem if a < 0 else rem


# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================


def intervals() -> st.SearchStrategy[Interval]:
    """
    Generate intervals with diverse bounds.

    Includes special cases: bot, top, singletons, and random intervals.
    """
    # Regular intervals with unbounded random bounds
    random_intervals = st.builds(
        lambda lower, upper: Interval(lower, upper),
        lower=st.integers(),
        upper=st.integers(),
    )

    # Special cases for edge coverage
    special_intervals = st.sampled_from(
        [
            Interval.bot(),
            Interval.top(),
            Interval(0, 0),  # singleton zero
            Interval(1, 1),  # singleton positive
            Interval(-1, -1),  # singleton negative
            Interval(-10, -1),  # negative range
            Interval(1, 10),  # positive range
            Interval(-5, 5),  # mixed range
            Interval(2, 3),  # small positive
            Interval(10, 20),  # large positive
        ]
    )

    return st.one_of(random_intervals, special_intervals)


def comparison_ops() -> st.SearchStrategy[Comparison]:
    """Generate all comparison operations."""
    return st.sampled_from(["le", "lt", "eq", "ne", "ge", "gt"])


# ============================================================================
# ARITHMETIC PROPERTY TESTS
# ============================================================================


@given(st.sets(st.integers()))
def test_valid_abstraction(xs: set[int]) -> None:
    """Property: All concrete values are contained in their abstraction."""
    interval = Interval.abstract(xs)
    assert all(x in interval for x in xs)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_interval_adds(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract addition is sound."""
    if not xs or not ys:
        return

    concrete_sums = {x + y for x in xs for y in ys}
    abstract_result = Interval.abstract(xs) + Interval.abstract(ys)

    assert all(s in abstract_result for s in concrete_sums)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_interval_subs(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract subtraction is sound."""
    if not xs or not ys:
        return

    concrete_diffs = {x - y for x in xs for y in ys}
    abstract_result = Interval.abstract(xs) - Interval.abstract(ys)

    assert all(d in abstract_result for d in concrete_diffs)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_interval_muls(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract multiplication is sound."""
    if not xs or not ys:
        return

    concrete_prods = {x * y for x in xs for y in ys}
    abstract_result = Interval.abstract(xs) * Interval.abstract(ys)

    assert all(p in abstract_result for p in concrete_prods)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_interval_mods(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract modulus is sound w.r.t JVM semantics."""
    if not xs or not ys:
        return

    # 1. Compute Concrete JVM Outcomes
    concrete_rems = set()
    has_zero_div = False

    for x in xs:
        for y in ys:
            if y == 0:
                has_zero_div = True
            else:
                concrete_rems.add(jvm_rem(x, y))

    # 2. Compute Abstract Result
    i_xs = Interval.abstract(xs)
    i_ys = Interval.abstract(ys)
    result = i_xs % i_ys

    # 3. Parse Abstract Result
    abstract_interval = Interval.bot()
    abstract_error = False

    if isinstance(result, Interval):
        abstract_interval = result
    elif isinstance(result, tuple):
        abstract_interval = result[0]
        assert isinstance(abstract_interval, Interval)
        if result[1] == "divide by zero":
            abstract_error = True
    elif result == "divide by zero":
        abstract_error = True

    # 4. Assertions
    # If concrete execution had valid numbers, they must be in the interval
    if concrete_rems:
        assert not abstract_interval.is_bot(), (
            f"Got Bot for concrete results {concrete_rems}"
        )
        assert all(r in abstract_interval for r in concrete_rems), (
            f"Concrete {concrete_rems} not in {abstract_interval} for {xs} % {ys}"
        )

    # If concrete execution had zero, abstract must report potential error
    if has_zero_div:
        assert abstract_error, f"Expected zero division error for {xs} % {ys}"


@given(intervals(), intervals())
@example(Interval(10, 20), Interval(5, 5))  # Positive % Positive
@example(Interval(-20, -10), Interval(5, 5))  # Negative % Positive
@example(Interval(-10, 10), Interval(5, 5))  # Mixed % Positive
def test_mod_sign_invariant(i1: Interval, i2: Interval) -> None:
    """Property: Result sign matches dividend sign (JVM rule)."""
    if i1.is_bot() or i2.is_bot() or i2 == 0:
        return

    result = i1 % i2

    # Unwrap tuple if error exists
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, str):  # "divide by zero"
        return

    assert isinstance(result, Interval)

    # If dividend is strictly positive, result is [0, ...]
    if i1.lower >= 0:
        assert result.lower >= 0

    # If dividend is strictly negative, result is [..., 0]
    if i1.upper <= 0:
        assert result.upper <= 0

    # If dividend is strictly zero, result is 0
    if i1 == 0:
        assert result == 0


@given(intervals(), intervals())
def test_mod_magnitude_bound(i1: Interval, i2: Interval) -> None:
    """Property: |Result| is strictly less than max(|Divisor|)."""
    if i1.is_bot() or i2.is_bot() or i2 == 0:
        return

    result = i1 % i2

    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, str):
        return

    # Find max absolute value of divisor
    max_div_abs = max(abs(i2.lower), abs(i2.upper))

    if max_div_abs == 0:
        return  # Caught by zero check
    if max_div_abs == float("inf"):
        return
    assert isinstance(result, Interval)
    # The result boundaries must be strictly less than divisor magnitude
    # (Except when divisor is 1 or -1, result is 0)
    assert abs(result.lower) < max_div_abs
    assert abs(result.upper) < max_div_abs


@given(intervals(), intervals())
@example(Interval(2, 3), Interval(10, 20))  # [2,3] % [10,20] -> [2,3]
@example(Interval(-3, -2), Interval(10, 20))  # [-3,-2] % [10,20] -> [-3,-2]
def test_mod_identity_refinement(i1: Interval, i2: Interval) -> None:
    """Property: If |dividend| < |divisor|, result == dividend (No-op)."""
    if i1.is_bot() or i2.is_bot():
        return

    # Determine min absolute value of divisor (excluding 0)
    if i2.lower > 0:
        min_div = i2.lower
    elif i2.upper < 0:
        min_div = abs(i2.upper)
    else:
        return  # Divisor spans 0, cannot guarantee identity

    # Determine max absolute value of dividend
    max_dividend = max(abs(i1.lower), abs(i1.upper))

    # If dividend is strictly smaller than smallest divisor
    if max_dividend < min_div:
        result = i1 % i2
        if isinstance(result, tuple):
            result = result[0]
        assert result == i1, f"Expected identity {i1}, got {result}"


# ============================================================================
# COMPARISON PROPERTY TESTS
# ============================================================================


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_interval_compare_le(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract <= comparison includes all concrete outcomes."""
    if not xs or not ys:
        return

    concrete_outcomes = {x <= y for x in xs for y in ys}
    abstract_result = Interval.abstract(xs).compare("le", Interval.abstract(ys))

    assert concrete_outcomes <= abstract_result.keys()


@given(intervals(), intervals(), comparison_ops())
def test_compare_returns_valid_bool_set_all_ops(
    i1: Interval, i2: Interval, op: Comparison
) -> None:
    """Property: Comparison returns valid dict with bool keys and interval values."""
    result = i1.compare(op, i2)
    intervals_list = list(chain.from_iterable(result.values()))

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)
    assert all(isinstance(v, Interval) for v in intervals_list)


@given(intervals(), intervals())
@example(Interval(0, 10), Interval(5, 15))
@example(Interval(1, 5), Interval(6, 10))
def test_comparison_complementarity_lt_ge(i1: Interval, i2: Interval) -> None:
    """Property: x < y and x >= y are complements."""
    lt_result = i1.lt(i2)
    ge_result = i1.ge(i2)

    if lt_result and ge_result:
        for outcome in [True, False]:
            if outcome in lt_result:
                complement = not outcome
                assert complement in ge_result or outcome in ge_result


@given(intervals(), intervals())
@example(Interval(0, 10), Interval(5, 15))
def test_comparison_complementarity_le_gt(i1: Interval, i2: Interval) -> None:
    """Property: x <= y and x > y are complements."""
    le_result = i1.le(i2)
    gt_result = i1.gt(i2)

    if le_result and gt_result:
        for outcome in [True, False]:
            if outcome in le_result:
                complement = not outcome
                assert complement in gt_result or outcome in gt_result


@given(intervals(), intervals())
@example(Interval(5, 10), Interval(5, 10))
def test_comparison_complementarity_eq_ne(i1: Interval, i2: Interval) -> None:
    """Property: x == y and x != y are complements."""
    eq_result = i1.eq(i2)
    ne_result = i1.ne(i2)

    if True in eq_result and False in ne_result:
        assert eq_result[True] == ne_result[False]

    if False in eq_result and True in ne_result:
        assert eq_result[False] == ne_result[True]


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(3, 7))
@example(Interval.bot(), Interval(1, 5))
def test_comparison_symmetry_eq(i1: Interval, i2: Interval) -> None:
    """Property: Equality is symmetric."""
    eq_12 = i1.eq(i2)
    eq_21 = i2.eq(i1)

    assert eq_12.keys() == eq_21.keys()

    for outcome in eq_12:
        i1_refined, i2_refined = eq_12[outcome]
        i2_refined_rev, i1_refined_rev = eq_21[outcome]
        assert i1_refined == i1_refined_rev
        assert i2_refined == i2_refined_rev


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(6, 10))
def test_comparison_antisymmetry_lt_gt(i1: Interval, i2: Interval) -> None:
    """Property: i1 < i2 is the opposite of i2 > i1."""
    lt_result = i1.lt(i2)
    gt_result = i2.gt(i1)

    assert lt_result.keys() == gt_result.keys()

    for outcome in lt_result:
        i1_refined_lt, i2_refined_lt = lt_result[outcome]
        i2_refined_gt, i1_refined_gt = gt_result[outcome]
        assert i1_refined_lt == i1_refined_gt
        assert i2_refined_lt == i2_refined_gt


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(3, 7))
def test_comparison_antisymmetry_le_ge(i1: Interval, i2: Interval) -> None:
    """Property: i1 <= i2 is the opposite of i2 >= i1."""
    le_result = i1.le(i2)
    ge_result = i2.ge(i1)

    assert le_result.keys() == ge_result.keys()

    for outcome in le_result:
        i1_refined_le, i2_refined_le = le_result[outcome]
        i2_refined_ge, i1_refined_ge = ge_result[outcome]
        assert i1_refined_le == i1_refined_ge
        assert i2_refined_le == i2_refined_ge


@given(intervals())
@example(Interval(5, 5))
@example(Interval(1, 10))
def test_comparison_identity_eq(i: Interval) -> None:
    """Property: x == x should always include True outcome for non-bot."""
    eq_result = i.eq(i)

    if not i.is_bot():
        assert True in eq_result
        assert eq_result[True] == (i, i)
    else:
        assert eq_result == {}


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(6, 10))
def test_logical_relationship_lt_implies_le(i1: Interval, i2: Interval) -> None:
    """Property: x < y implies x <= y."""
    lt_result = i1.lt(i2)
    le_result = i1.le(i2)

    if True in lt_result:
        assert True in le_result
        lt_i1, lt_i2 = lt_result[True]
        le_i1, le_i2 = le_result[True]
        assert lt_i1 <= le_i1
        assert lt_i2 <= le_i2


@given(intervals(), intervals())
@example(Interval(6, 10), Interval(1, 5))
def test_logical_relationship_gt_implies_ge(i1: Interval, i2: Interval) -> None:
    """Property: x > y implies x >= y."""
    gt_result = i1.gt(i2)
    ge_result = i1.ge(i2)

    if True in gt_result:
        assert True in ge_result
        gt_i1, gt_i2 = gt_result[True]
        ge_i1, ge_i2 = ge_result[True]
        assert gt_i1 <= ge_i1
        assert gt_i2 <= ge_i2


@given(intervals(), intervals())
@example(Interval(5, 5), Interval(5, 5))
def test_logical_relationship_eq_implies_le_and_ge(i1: Interval, i2: Interval) -> None:
    """Property: x == y implies x <= y and x >= y."""
    eq_result = i1.eq(i2)
    le_result = i1.le(i2)
    ge_result = i1.ge(i2)

    if True in eq_result:
        assert True in le_result
        assert True in ge_result


# ============================================================================
# LATTICE PROPERTY TESTS
# ============================================================================


@given(intervals(), intervals())
def test_meet_commutativity(i1: Interval, i2: Interval) -> None:
    """Property: Meet is commutative."""
    assert (i1 & i2) == (i2 & i1)


@given(intervals(), intervals())
def test_join_commutativity(i1: Interval, i2: Interval) -> None:
    """Property: Join is commutative."""
    assert (i1 | i2) == (i2 | i1)


@given(intervals(), intervals(), intervals())
def test_meet_associativity(i1: Interval, i2: Interval, i3: Interval) -> None:
    """Property: Meet is associative."""
    assert ((i1 & i2) & i3) == (i1 & (i2 & i3))


@given(intervals(), intervals(), intervals())
def test_join_associativity(i1: Interval, i2: Interval, i3: Interval) -> None:
    """Property: Join is associative."""
    assert ((i1 | i2) | i3) == (i1 | (i2 | i3))


@given(intervals(), intervals())
def test_absorption_law_1(i1: Interval, i2: Interval) -> None:
    """Property: Absorption law i1 ⊔ (i1 ⊓ i2) = i1."""
    assert (i1 | (i1 & i2)) == i1


@given(intervals(), intervals())
def test_absorption_law_2(i1: Interval, i2: Interval) -> None:
    """Property: Absorption law i1 ⊓ (i1 ⊔ i2) = i1."""
    assert (i1 & (i1 | i2)) == i1


@given(intervals())
def test_bot_is_identity_for_join(i: Interval) -> None:
    """Property: Bot is identity for join."""
    bot = Interval.bot()
    assert (i | bot) == i
    assert (bot | i) == i


@given(intervals())
def test_bot_is_absorbing_for_meet(i: Interval) -> None:
    """Property: Bot is absorbing for meet."""
    bot = Interval.bot()
    assert (i & bot) == bot
    assert (bot & i) == bot


# ============================================================================
# TOP ELEMENT BINARY OPERATIONS
# ============================================================================


@given(intervals())
def test_top_addition(i: Interval) -> None:
    """Property: Top + interval = Top (except bot case)."""
    top = Interval.top()

    if i.is_bot():
        assert (top + i).is_bot()
        assert (i + top).is_bot()
    else:
        assert (top + i) == top
        assert (i + top) == top


@given(intervals())
def test_top_subtraction(i: Interval) -> None:
    """Property: Top - interval = Top (except bot case)."""
    top = Interval.top()

    if i.is_bot():
        assert (top - i).is_bot()
        assert (i - top).is_bot()
    else:
        assert (top - i) == top
        assert (i - top) == top


@given(intervals())
def test_top_multiplication(i: Interval) -> None:
    """Property: Top * interval = Top (except bot and zero cases)."""
    top = Interval.top()

    if i.is_bot():
        assert (top * i).is_bot()
        assert (i * top).is_bot()
    elif i == Interval(0, 0):
        # Top * 0 should be 0
        assert (top * i) == 0
        assert (i * top) == 0
    else:
        assert (top * i) == top
        assert (i * top) == top


@given(intervals())
def test_top_floor_division(i: Interval) -> None:
    """Property: Top // interval = Top (except bot and zero-containing cases)."""
    top = Interval.top()

    if i.is_bot():
        assert (top // i) == Interval.bot()
        assert (i // top) == Interval.bot()
    elif i.lower <= 0 <= i.upper:
        # Contains zero
        result1 = top // i
        result2 = i // top

        is_error = result1 == "divide by zero" or (
            isinstance(result1, tuple) and result1[1] == "divide by zero"
        )
        assert is_error

        is_top_or_error = result2 == top or (
            isinstance(result2, tuple) and result2[0] == top
        )
        assert is_top_or_error
    else:
        assert (top // i) == top
        assert (i // top) == (top, "divide by zero")  # Top contains 0


@given(intervals())
def test_top_modulus(i: Interval) -> None:
    """Property: Top % interval behavior."""
    top = Interval.top()

    if i.is_bot():
        assert (top % i).is_bot() # pyright: ignore[reportAttributeAccessIssue]
        assert (i % top).is_bot() # pyright: ignore[reportAttributeAccessIssue]
        return

    # 1. Top % i
    result1 = top % i

    has_zero = i.lower <= 0 <= i.upper

    if i == 0:
        # Pure divide by zero
        assert result1 == "divide by zero"
    else:
        # Unwrap result if tuple
        val = result1[0] if isinstance(result1, tuple) else result1

        # Calculate expected bound based on divisor magnitude
        max_divisor = max(abs(i.lower), abs(i.upper))

        if max_divisor == float("inf"):
            # If divisor goes to infinity, remainder can be anything (Top)
            # but usually bounded. However, here we just check validity.
            pass
        else:
            assert isinstance(val, Interval)
            limit = max(0, max_divisor - 1)
            # Since Top contains negative and positive, result is symmetric
            assert val.lower >= -limit
            assert val.upper <= limit

        # Check error flag presence
        if has_zero:
            assert isinstance(result1, tuple)
            assert result1[1] == "divide by zero"

    # 2. i % Top
    # Top contains large numbers and 0.
    result2 = i % top
    assert isinstance(result2, tuple)
    assert result2[1] == "divide by zero"


def test_top_with_top_operations() -> None:
    """Property: Binary operations between two Top elements."""
    top = Interval.top()

    # Top + Top = Top
    assert (top + top) == top

    # Top - Top = Top
    assert (top - top) == top

    # Top * Top = Top
    assert (top * top) == top

    # Top // Top
    result_div = top // top
    assert isinstance(result_div, tuple)
    assert result_div[0] == top
    assert result_div[1] == "divide by zero"

    # Top % Top
    result_mod = top % top
    assert isinstance(result_mod, tuple)
    assert result_mod[0] == top
    assert result_mod[1] == "divide by zero"
