"""Hypothesis-based property tests for Interval abstraction."""

from itertools import chain

from hypothesis import example, given
from hypothesis import strategies as st

from project.abstractions.abstraction import Comparison
from project.abstractions.interval import Interval

# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================


def intervals() -> st.SearchStrategy[Interval]:
    """
    Generate intervals with diverse bounds.

    Includes special cases: bot, top, singletons, and random intervals.
    Let Hypothesis explore the space naturally without artificial limits.
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
        ]
    )

    return st.one_of(random_intervals, special_intervals)


def comparison_ops() -> st.SearchStrategy[Comparison]:
    """Generate all comparison operations."""
    return st.sampled_from(["le", "lt", "eq", "ne", "ge", "gt"])


# ============================================================================
# BASIC PROPERTY TESTS
# ============================================================================


@given(st.sets(st.integers()))
def test_valid_abstraction(xs: set[int]) -> None:
    """Property: All concrete values are contained in their abstraction."""
    interval = Interval.abstract(xs)
    assert all(x in interval for x in xs)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_interval_adds(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract addition is sound (overapproximates concrete)."""
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


# ============================================================================
# COMPLEMENTARITY PROPERTIES
# ============================================================================


@given(intervals(), intervals())
@example(Interval(0, 10), Interval(5, 15))
@example(Interval(1, 5), Interval(6, 10))
def test_comparison_complementarity_lt_ge(i1: Interval, i2: Interval) -> None:
    """Property: x < y and x >= y are complements."""
    lt_result = i1.lt(i2)
    ge_result = i1.ge(i2)

    # If both non-empty, they should have complementary outcomes
    if lt_result and ge_result:
        # At least one outcome should be shared or complementary
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


# ============================================================================
# SYMMETRY PROPERTIES
# ============================================================================


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


# ============================================================================
# IDENTITY PROPERTIES
# ============================================================================


@given(intervals())
@example(Interval(5, 5))
@example(Interval(1, 10))
def test_comparison_identity_eq(i: Interval) -> None:
    """Property: x == x should always include True outcome for non-bot."""
    eq_result = i.eq(i)

    if not i.is_bot():
        assert True in eq_result
        # For identity comparison, refined intervals should equal the original
        assert eq_result[True] == (i, i)
    else:
        assert eq_result == {}


@given(intervals())
@example(Interval(1, 10))
def test_comparison_identity_le(i: Interval) -> None:
    """Property: x <= x should always include True."""
    le_result = i.le(i)

    if not i.is_bot():
        assert True in le_result


@given(intervals())
@example(Interval(1, 10))
def test_comparison_identity_ge(i: Interval) -> None:
    """Property: x >= x should always include True."""
    ge_result = i.ge(i)

    if not i.is_bot():
        assert True in ge_result


# ============================================================================
# LOGICAL RELATIONSHIP PROPERTIES
# ============================================================================


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
# SOUNDNESS (ORACLE-BASED)
# ============================================================================


def compute_concrete_outcomes(i1: Interval, i2: Interval, op: Comparison) -> set[bool]:
    """Oracle: compute concrete outcomes for intervals by sampling."""
    if i1.is_bot() or i2.is_bot():
        return set()

    outcomes = set()

    # Sample concrete values from intervals
    def sample_from_interval(interval: Interval, num_samples: int = 5) -> list[int]:
        """Sample concrete values from an interval."""
        if interval.lower == float("-inf") or interval.upper == float("inf"):
            # For infinite bounds, sample a fixed range
            lower = int(max(interval.lower, -100))
            upper = int(min(interval.upper, 100))
        else:
            lower = int(interval.lower)
            upper = int(interval.upper)

        if lower > upper:
            return []

        # Sample endpoints and some middle values
        samples = [lower, upper]
        if upper - lower >= 2:  # noqa: PLR2004
            samples.append((lower + upper) // 2)
        if upper - lower >= 4:  # noqa: PLR2004
            samples.append((lower + (lower + upper) // 2) // 2)
            samples.append(((lower + upper) // 2 + upper) // 2)

        return list(set(samples))[:num_samples]

    samples1 = sample_from_interval(i1)
    samples2 = sample_from_interval(i2)

    for val1 in samples1:
        for val2 in samples2:
            if op == "le":
                outcomes.add(val1 <= val2)
            elif op == "lt":
                outcomes.add(val1 < val2)
            elif op == "eq":
                outcomes.add(val1 == val2)
            elif op == "ne":
                outcomes.add(val1 != val2)
            elif op == "ge":
                outcomes.add(val1 >= val2)
            elif op == "gt":
                outcomes.add(val1 > val2)

    return outcomes


# @given(intervals(), intervals(), comparison_ops())
# @example(Interval(5, 5), Interval(5, 5), "eq")
# @example(Interval(1, 5), Interval(6, 10), "lt")
# @example(Interval(6, 10), Interval(1, 5), "gt")
# @example(Interval.bot(), Interval(1, 5), "le")
# def test_soundness_concrete_oracle(
#     i1: Interval, i2: Interval, op: Comparison
# ) -> None:
#     """Property: Abstract comparison is sound w.r.t. concrete execution."""
#     if i1.is_bot() or i2.is_bot():
#         return

#     result = i1.compare(op, i2)
#     concrete_outcomes = compute_concrete_outcomes(i1, i2, op)

#     for concrete_outcome in concrete_outcomes:
#         assert (
#             concrete_outcome in result
#         ), f"Concrete outcome {concrete_outcome} not in result for {i1} {op} {i2}"


# ============================================================================
# REFINEMENT COVERAGE
# ============================================================================


# @given(intervals(), intervals(), comparison_ops())
# @example(Interval.bot(), Interval.bot(), "eq")
# @example(Interval.top(), Interval.top(), "eq")
# @example(Interval(1, 10), Interval(5, 15), "le")
# def test_comparison_refinement_coverage(
#     i1: Interval, i2: Interval, op: Comparison
# ) -> None:
#     """Property: Refinements cover the original intervals and are valid subsets."""
#     result = i1.compare(op, i2)

#     # Refined intervals should be subsets
#     for refined_i1, refined_i2 in result.values():
#         assert isinstance(refined_i1, Interval)
#         assert isinstance(refined_i2, Interval)
#         assert refined_i1 <= i1
#         assert refined_i2 <= i2

#     # Union of refined intervals should cover originals (for non-bot)
#     if result and not i1.is_bot() and not i2.is_bot():
#         all_i1_refined = Interval.bot()
#         all_i2_refined = Interval.bot()
#         for refined_i1, refined_i2 in result.values():
#             all_i1_refined = all_i1_refined | refined_i1
#             all_i2_refined = all_i2_refined | refined_i2
#         assert all_i1_refined == i1
#         assert all_i2_refined == i2


# ============================================================================
# LATTICE PROPERTY TESTS
# ============================================================================


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(3, 7))
def test_meet_commutativity(i1: Interval, i2: Interval) -> None:
    """Property: Meet is commutative (i1 ⊓ i2 = i2 ⊓ i1)."""
    assert (i1 & i2) == (i2 & i1)


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(3, 7))
def test_join_commutativity(i1: Interval, i2: Interval) -> None:
    """Property: Join is commutative (i1 ⊔ i2 = i2 ⊔ i1)."""
    assert (i1 | i2) == (i2 | i1)


@given(intervals(), intervals(), intervals())
def test_meet_associativity(i1: Interval, i2: Interval, i3: Interval) -> None:
    """Property: Meet is associative ((i1 ⊓ i2) ⊓ i3 = i1 ⊓ (i2 ⊓ i3))."""
    assert ((i1 & i2) & i3) == (i1 & (i2 & i3))


@given(intervals(), intervals(), intervals())
def test_join_associativity(i1: Interval, i2: Interval, i3: Interval) -> None:
    """Property: Join is associative ((i1 ⊔ i2) ⊔ i3 = i1 ⊔ (i2 ⊔ i3))."""
    assert ((i1 | i2) | i3) == (i1 | (i2 | i3))


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(3, 7))
def test_absorption_law_1(i1: Interval, i2: Interval) -> None:
    """Property: Absorption law i1 ⊔ (i1 ⊓ i2) = i1."""
    assert (i1 | (i1 & i2)) == i1


@given(intervals(), intervals())
@example(Interval(1, 5), Interval(3, 7))
def test_absorption_law_2(i1: Interval, i2: Interval) -> None:
    """Property: Absorption law i1 ⊓ (i1 ⊔ i2) = i1."""
    assert (i1 & (i1 | i2)) == i1


@given(intervals())
@example(Interval(1, 10))
def test_bot_is_identity_for_join(i: Interval) -> None:
    """Property: Bot is identity for join (i ⊔ ⊥ = i)."""
    bot = Interval.bot()
    assert (i | bot) == i
    assert (bot | i) == i


@given(intervals())
@example(Interval(1, 10))
def test_bot_is_absorbing_for_meet(i: Interval) -> None:
    """Property: Bot is absorbing for meet (i ⊓ ⊥ = ⊥)."""
    bot = Interval.bot()
    assert (i & bot) == bot
    assert (bot & i) == bot


# ============================================================================
# TOP ELEMENT BINARY OPERATIONS
# ============================================================================


@given(intervals())
@example(Interval(0, 0))
@example(Interval(1, 10))
@example(Interval(-5, 5))
@example(Interval.bot())
def test_top_addition(i: Interval) -> None:
    """Property: Top + interval = Top (except bot case)."""
    top = Interval.top()

    if i.is_bot():
        assert (top + i).is_bot()
        assert (i + top).is_bot()
    else:
        result1 = top + i
        result2 = i + top
        assert result1 == top, f"Expected Top + {i} = Top, got {result1}"
        assert result2 == top, f"Expected {i} + Top = Top, got {result2}"


@given(intervals())
@example(Interval(0, 0))
@example(Interval(1, 10))
@example(Interval(-5, 5))
@example(Interval.bot())
def test_top_subtraction(i: Interval) -> None:
    """Property: Top - interval = Top and interval - Top = Top (except bot case)."""
    top = Interval.top()

    if i.is_bot():
        assert (top - i).is_bot()
        assert (i - top).is_bot()
    else:
        result1 = top - i
        result2 = i - top
        assert result1 == top, f"Expected Top - {i} = Top, got {result1}"
        assert result2 == top, f"Expected {i} - Top = Top, got {result2}"


@given(intervals())
@example(Interval(0, 0))
@example(Interval(1, 10))
@example(Interval(-5, 5))
@example(Interval.bot())
def test_top_multiplication(i: Interval) -> None:
    """Property: Top * interval = Top (except bot and zero cases)."""
    top = Interval.top()

    if i.is_bot():
        assert (top * i).is_bot()
        assert (i * top).is_bot()
    elif i == Interval(0, 0):
        # Top * 0 should still be Top due to -inf * 0 and inf * 0
        result1 = top * i
        result2 = i * top
        assert result1 == 0
        assert result2 == 0
    else:
        result1 = top * i
        result2 = i * top
        assert result1 == top, f"Expected Top * {i} = Top, got {result1}"
        assert result2 == top, f"Expected {i} * Top = Top, got {result2}"


@given(intervals())
@example(Interval(1, 10))
@example(Interval(-5, -1))
@example(Interval(5, 5))
@example(Interval.bot())
def test_top_floor_division(i: Interval) -> None:
    """Property: Top // interval = Top (except bot and zero-containing cases)."""
    top = Interval.top()

    if i.is_bot():
        assert (top // i) == Interval.bot()
        assert (i // top) == Interval.bot()
    elif i.lower <= 0 <= i.upper:
        # Contains zero - should return error or (top, error)
        result1 = top // i
        result2 = i // top
        # Should involve divide by zero error
        is_error = result1 == "divide by zero" or (
            isinstance(result1, tuple) and result1[1] == "divide by zero"
        )
        assert is_error
        is_top_or_error = result2 == top or (
            isinstance(result2, tuple) and result2[0] == top
        )
        assert is_top_or_error
    else:
        result1 = top // i
        result2 = i // top
        # Top // non-zero should be Top
        assert result1 == top, f"Expected Top // {i} = Top, got {result1}"
        # interval // Top should also be Top due to infinite bounds
        assert result2 == (top, "divide by zero")


@given(intervals())
@example(Interval(1, 10))
@example(Interval(-5, -1))
@example(Interval(5, 5))
@example(Interval.bot())
def test_top_modulus(i: Interval) -> None:
    """Property: Top % interval behavior with infinite bounds."""
    # top = Interval.top()

    # if i.is_bot():
    #     result1 = top % i
    #     result2 = i % top
    #     assert isinstance(result1, Interval)
    #     assert isinstance(result2, tuple)
    #     assert result1.is_bot()
    #     assert isinstance(result2[0], Interval)
    #     assert result2[0].is_bot()
    #     assert result2[1] == "divide by zero"
    # elif i.lower <= 0 <= i.upper:
    #     # Contains zero - should return bot (error state)
    #     result1 = top % i
    #     result2 = i % top
    #     # Should involve divide by zero error
    #     is_error = result1 == "divide by zero" or (
    #         isinstance(result1, tuple) and result1[1] == "divide by zero"
    #     )
    #     assert is_error
    #     is_top_or_error = result2 == top or (
    #         isinstance(result2, tuple) and result2[0] == top
    #     )
    #     assert is_top_or_error
    # else:
    #     # Top % non-zero-containing interval
    #     result1 = top % i
    #     # Result should be conservative approximation
    #     max_divisor = max(abs(i.lower), abs(i.upper))
    #     expected_bounds = Interval(-(max_divisor - 1), max_divisor - 1)
    #     assert result1 == expected_bounds, \
    #         f"Expected Top % {i} = {expected_bounds}, got {result1}"

    #     # i % Top (Top contains zero) should be bot
    #     result2 = i % top
    #     assert result2.is_bot(), \
    #         f"Expected {i} % Top (Top contains 0) = Bot, got {result2}"


def test_top_with_top_operations() -> None:
    """Property: Binary operations between two Top elements."""
    top = Interval.top()

    # Top + Top = Top
    assert (top + top) == top

    # Top - Top = Top (not refined to zero)
    assert (top - top) == top

    # Top * Top = Top
    assert (top * top) == top

    # Top // Top should return (Top, "divide by zero") or similar
    # due to zero in divisor
    result = top // top
    is_error = result == "divide by zero" or (
        isinstance(result, tuple) and result[1] == "divide by zero"
    )
    assert is_error

    # Top % Top should be bot due to zero in divisor
    # TODO(kornel): %
    # assert (top % top)
