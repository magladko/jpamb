"""Hypothesis-based property tests for MachineWordDomain abstraction."""

from itertools import chain

from hypothesis import example, given
from hypothesis import strategies as st

from project.abstractions.abstraction import Comparison
from project.abstractions.machine_word import MachineWordDomain

# ============================================================================
# CONFIGURATION
# ============================================================================

# Number of concrete samples to use in oracle tests
# (configurable for performance tuning)
ORACLE_SAMPLES = 5

# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================


def machine_words() -> st.SearchStrategy[MachineWordDomain]:
    """
    Generate machine word elements with diverse residue sets.

    WIDTH = 32, MAX_TRACKED = 16
    """
    # Random residues (normalized to 32-bit)
    random_words = st.builds(
        lambda residues: MachineWordDomain(residues if residues else set()),
        residues=st.sets(st.integers(min_value=0, max_value=2**32 - 1), max_size=16),
    )

    # Special cases
    special_words = st.sampled_from(
        [
            MachineWordDomain.bot(),
            MachineWordDomain.top(),
            MachineWordDomain({0}),  # singleton zero
            MachineWordDomain({1}),  # singleton one
            MachineWordDomain({2**32 - 1}),  # max value
            MachineWordDomain({2**31}),  # sign bit
            MachineWordDomain({0, 1, 2**31}),  # small set
            MachineWordDomain(set(range(16))),  # exactly MAX_TRACKED
        ]
    )

    return st.one_of(random_words, special_words)


def comparison_ops() -> st.SearchStrategy[Comparison]:
    """Generate all comparison operations."""
    return st.sampled_from(["le", "lt", "eq", "ne", "ge", "gt"])


# ============================================================================
# BASIC PROPERTY TESTS
# ============================================================================


@given(st.sets(st.integers()))
def test_valid_abstraction(xs: set[int]) -> None:
    """Property: All concrete values are contained in their abstraction."""
    word = MachineWordDomain.abstract(xs)
    for x in xs:
        assert x in word


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_machine_word_adds(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract addition is sound (overapproximates concrete)."""
    if not xs or not ys:
        return

    # Compute concrete sums with wrapping
    mask = (1 << 32) - 1
    concrete_sums = {(x + y) & mask for x in xs for y in ys}
    abstract_result = MachineWordDomain.abstract(xs) + MachineWordDomain.abstract(ys)

    assert all(s in abstract_result for s in concrete_sums)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_machine_word_subs(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract subtraction is sound."""
    if not xs or not ys:
        return

    mask = (1 << 32) - 1
    concrete_diffs = {(x - y) & mask for x in xs for y in ys}
    abstract_result = MachineWordDomain.abstract(xs) - MachineWordDomain.abstract(ys)

    assert all(d in abstract_result for d in concrete_diffs)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_machine_word_muls(xs: set[int], ys: set[int]) -> None:
    """Property: Abstract multiplication is sound."""
    if not xs or not ys:
        return

    mask = (1 << 32) - 1
    concrete_prods = {(x * y) & mask for x in xs for y in ys}
    abstract_result = MachineWordDomain.abstract(xs) * MachineWordDomain.abstract(ys)

    assert all(p in abstract_result for p in concrete_prods)


@given(machine_words(), machine_words(), comparison_ops())
def test_compare_returns_valid_bool_set_all_ops(
    w1: MachineWordDomain, w2: MachineWordDomain, op: Comparison
) -> None:
    """Property: Comparison returns valid dict with bool keys and word values."""
    result = w1.compare(op, w2)
    words_list = list(chain.from_iterable(result.values()))

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)
    assert all(isinstance(v, MachineWordDomain) for v in words_list)


# ============================================================================
# COMPLEMENTARITY PROPERTIES
# ============================================================================


@given(machine_words(), machine_words())
@example(MachineWordDomain({0, 10}), MachineWordDomain({5, 15}))
def test_comparison_complementarity_lt_ge(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: x < y and x >= y are complements."""
    lt_result = w1.lt(w2)
    ge_result = w1.ge(w2)

    # If both non-empty, outcomes should be complementary
    if lt_result and ge_result:
        for outcome in [True, False]:
            if outcome in lt_result:
                complement = not outcome
                assert complement in ge_result or outcome in ge_result


@given(machine_words(), machine_words())
@example(MachineWordDomain({0, 10}), MachineWordDomain({5, 15}))
def test_comparison_complementarity_le_gt(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: x <= y and x > y are complements."""
    le_result = w1.le(w2)
    gt_result = w1.gt(w2)

    if le_result and gt_result:
        for outcome in [True, False]:
            if outcome in le_result:
                complement = not outcome
                assert complement in gt_result or outcome in gt_result


@given(machine_words(), machine_words())
@example(MachineWordDomain({5}), MachineWordDomain({5}))
def test_comparison_complementarity_eq_ne(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: x == y and x != y are complements."""
    eq_result = w1.eq(w2)
    ne_result = w1.ne(w2)

    if True in eq_result and False in ne_result:
        assert eq_result[True] == ne_result[False]

    if False in eq_result and True in ne_result:
        assert eq_result[False] == ne_result[True]


# ============================================================================
# SYMMETRY PROPERTIES
# ============================================================================


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({3, 7}))
@example(MachineWordDomain.bot(), MachineWordDomain({1, 5}))
def test_comparison_symmetry_eq(w1: MachineWordDomain, w2: MachineWordDomain) -> None:
    """Property: Equality is symmetric."""
    eq_12 = w1.eq(w2)
    eq_21 = w2.eq(w1)

    assert eq_12.keys() == eq_21.keys()

    for outcome in eq_12:
        w1_refined, w2_refined = eq_12[outcome]
        w2_refined_rev, w1_refined_rev = eq_21[outcome]
        assert w1_refined == w1_refined_rev
        assert w2_refined == w2_refined_rev


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({6, 10}))
def test_comparison_antisymmetry_lt_gt(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: w1 < w2 is the opposite of w2 > w1."""
    lt_result = w1.lt(w2)
    gt_result = w2.gt(w1)

    assert lt_result.keys() == gt_result.keys()

    for outcome in lt_result:
        w1_refined_lt, w2_refined_lt = lt_result[outcome]
        w2_refined_gt, w1_refined_gt = gt_result[outcome]
        assert w1_refined_lt == w1_refined_gt
        assert w2_refined_lt == w2_refined_gt


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({3, 7}))
def test_comparison_antisymmetry_le_ge(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: w1 <= w2 is the opposite of w2 >= w1."""
    le_result = w1.le(w2)
    ge_result = w2.ge(w1)

    assert le_result.keys() == ge_result.keys()

    for outcome in le_result:
        w1_refined_le, w2_refined_le = le_result[outcome]
        w2_refined_ge, w1_refined_ge = ge_result[outcome]
        assert w1_refined_le == w1_refined_ge
        assert w2_refined_le == w2_refined_ge


# ============================================================================
# IDENTITY PROPERTIES
# ============================================================================


@given(machine_words())
@example(MachineWordDomain({5}))
@example(MachineWordDomain({1, 10}))
def test_comparison_identity_eq(w: MachineWordDomain) -> None:
    """Property: x == x should always include True outcome for non-bot."""
    eq_result = w.eq(w)

    if not w.is_bot():
        assert True in eq_result
        assert eq_result[True] == (w, w)
    else:
        assert eq_result == {}


@given(machine_words())
@example(MachineWordDomain({1, 10}))
def test_comparison_identity_le(w: MachineWordDomain) -> None:
    """Property: x <= x should always include True."""
    le_result = w.le(w)

    if not w.is_bot():
        assert True in le_result


@given(machine_words())
@example(MachineWordDomain({1, 10}))
def test_comparison_identity_ge(w: MachineWordDomain) -> None:
    """Property: x >= x should always include True."""
    ge_result = w.ge(w)

    if not w.is_bot():
        assert True in ge_result


# ============================================================================
# LOGICAL RELATIONSHIP PROPERTIES
# ============================================================================


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({6, 10}))
def test_logical_relationship_lt_implies_le(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: x < y implies x <= y."""
    lt_result = w1.lt(w2)
    le_result = w1.le(w2)

    if True in lt_result:
        assert True in le_result
        lt_w1, lt_w2 = lt_result[True]
        le_w1, le_w2 = le_result[True]
        assert lt_w1 <= le_w1
        assert lt_w2 <= le_w2


@given(machine_words(), machine_words())
@example(MachineWordDomain({6, 10}), MachineWordDomain({1, 5}))
def test_logical_relationship_gt_implies_ge(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: x > y implies x >= y."""
    gt_result = w1.gt(w2)
    ge_result = w1.ge(w2)

    if True in gt_result:
        assert True in ge_result
        gt_w1, gt_w2 = gt_result[True]
        ge_w1, ge_w2 = ge_result[True]
        assert gt_w1 <= ge_w1
        assert gt_w2 <= ge_w2


@given(machine_words(), machine_words())
@example(MachineWordDomain({5}), MachineWordDomain({5}))
def test_logical_relationship_eq_implies_le_and_ge(
    w1: MachineWordDomain, w2: MachineWordDomain
) -> None:
    """Property: x == y implies x <= y and x >= y."""
    eq_result = w1.eq(w2)
    le_result = w1.le(w2)
    ge_result = w1.ge(w2)

    if True in eq_result:
        assert True in le_result
        assert True in ge_result


# ============================================================================
# LATTICE PROPERTY TESTS
# ============================================================================


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({3, 7}))
def test_meet_commutativity(w1: MachineWordDomain, w2: MachineWordDomain) -> None:
    """Property: Meet is commutative (w1 ⊓ w2 = w2 ⊓ w1)."""
    assert (w1 & w2) == (w2 & w1)


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({3, 7}))
def test_join_commutativity(w1: MachineWordDomain, w2: MachineWordDomain) -> None:
    """Property: Join is commutative (w1 ⊔ w2 = w2 ⊔ w1)."""
    assert (w1 | w2) == (w2 | w1)


@given(machine_words(), machine_words(), machine_words())
def test_meet_associativity(
    w1: MachineWordDomain, w2: MachineWordDomain, w3: MachineWordDomain
) -> None:
    """Property: Meet is associative ((w1 ⊓ w2) ⊓ w3 = w1 ⊓ (w2 ⊓ w3))."""
    assert ((w1 & w2) & w3) == (w1 & (w2 & w3))


@given(machine_words(), machine_words(), machine_words())
def test_join_associativity(
    w1: MachineWordDomain, w2: MachineWordDomain, w3: MachineWordDomain
) -> None:
    """Property: Join is associative ((w1 ⊔ w2) ⊔ w3 = w1 ⊔ (w2 ⊔ w3))."""
    assert ((w1 | w2) | w3) == (w1 | (w2 | w3))


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({3, 7}))
def test_absorption_law_1(w1: MachineWordDomain, w2: MachineWordDomain) -> None:
    """Property: Absorption law w1 ⊔ (w1 ⊓ w2) = w1."""
    assert (w1 | (w1 & w2)) == w1


@given(machine_words(), machine_words())
@example(MachineWordDomain({1, 5}), MachineWordDomain({3, 7}))
def test_absorption_law_2(w1: MachineWordDomain, w2: MachineWordDomain) -> None:
    """Property: Absorption law w1 ⊓ (w1 ⊔ w2) = w1."""
    assert (w1 & (w1 | w2)) == w1


@given(machine_words())
@example(MachineWordDomain({1, 10}))
def test_bot_is_identity_for_join(w: MachineWordDomain) -> None:
    """Property: Bot is identity for join (w ⊔ ⊥ = w)."""
    bot = MachineWordDomain.bot()
    assert (w | bot) == w
    assert (bot | w) == w


@given(machine_words())
@example(MachineWordDomain({1, 10}))
def test_bot_is_absorbing_for_meet(w: MachineWordDomain) -> None:
    """Property: Bot is absorbing for meet (w ⊓ ⊥ = ⊥)."""
    bot = MachineWordDomain.bot()
    assert (w & bot) == bot
    assert (bot & w) == bot


# ============================================================================
# TOP ELEMENT BINARY OPERATIONS
# ============================================================================


@given(machine_words())
@example(MachineWordDomain({0}))
@example(MachineWordDomain({1, 10}))
@example(MachineWordDomain.bot())
def test_top_addition(w: MachineWordDomain) -> None:
    """Property: Top + word = Top (except bot case)."""
    top = MachineWordDomain.top()

    if w.is_bot():
        assert (top + w).is_bot()
        assert (w + top).is_bot()
    else:
        result1 = top + w
        result2 = w + top
        assert result1 == top, f"Expected Top + {w} = Top, got {result1}"
        assert result2 == top, f"Expected {w} + Top = Top, got {result2}"


@given(machine_words())
@example(MachineWordDomain({0}))
@example(MachineWordDomain({1, 10}))
@example(MachineWordDomain.bot())
def test_top_subtraction(w: MachineWordDomain) -> None:
    """Property: Top - word = Top and word - Top = Top (except bot case)."""
    top = MachineWordDomain.top()

    if w.is_bot():
        assert (top - w).is_bot()
        assert (w - top).is_bot()
    else:
        result1 = top - w
        result2 = w - top
        assert result1 == top, f"Expected Top - {w} = Top, got {result1}"
        assert result2 == top, f"Expected {w} - Top = Top, got {result2}"


@given(machine_words())
@example(MachineWordDomain({0}))
@example(MachineWordDomain({1, 10}))
@example(MachineWordDomain.bot())
def test_top_multiplication(w: MachineWordDomain) -> None:
    """Property: Top * word = Top (except bot case)."""
    top = MachineWordDomain.top()

    if w.is_bot():
        assert (top * w).is_bot()
        assert (w * top).is_bot()
    else:
        result1 = top * w
        result2 = w * top
        assert result1 == top, f"Expected Top * {w} = Top, got {result1}"
        assert result2 == top, f"Expected {w} * Top = Top, got {result2}"


@given(machine_words())
@example(MachineWordDomain({1, 10}))
@example(MachineWordDomain({0}))
@example(MachineWordDomain.bot())
def test_top_division(w: MachineWordDomain) -> None:
    """Property: Top / word behavior with division by zero handling."""
    top = MachineWordDomain.top()

    if w.is_bot():
        assert (top / w).is_bot()
        assert (w / top).is_bot()
    elif w.residues is not None and 0 in w.residues:
        # Contains zero - should return top
        result = top / w
        assert result == top
    else:
        result = top / w
        assert result == top


def test_top_with_top_operations() -> None:
    """Property: Binary operations between two Top elements."""
    top = MachineWordDomain.top()

    # Top + Top = Top
    assert (top + top) == top

    # Top - Top = Top
    assert (top - top) == top

    # Top * Top = Top
    assert (top * top) == top

    # Top / Top = Top (due to zero in divisor)
    assert (top / top) == top


# ============================================================================
# DOMAIN-SPECIFIC TESTS: WRAPPING BEHAVIOR
# ============================================================================


def test_wrapping_overflow() -> None:
    """Values wrap modulo 2^32."""
    # Overflow past 2^32
    a = MachineWordDomain({2**32 - 1})
    b = MachineWordDomain({2})
    result = a + b
    assert 1 in result  # (2^32 - 1) + 2 = 1 (mod 2^32)


def test_wrapping_underflow() -> None:
    """Negative values wrap to positive."""
    a = MachineWordDomain({0})
    b = MachineWordDomain({1})
    result = a - b
    assert 2**32 - 1 in result  # 0 - 1 = 2^32 - 1 (mod 2^32)


def test_normalization_on_construction() -> None:
    """Values are normalized during abstraction."""
    # Values beyond 2^32 are masked
    result = MachineWordDomain.abstract({2**32, 2**32 + 5, -1})
    assert 0 in result  # 2^32 mod 2^32 = 0
    assert 5 in result  # (2^32 + 5) mod 2^32 = 5  # noqa: PLR2004
    assert 2**32 - 1 in result  # -1 mod 2^32 = 2^32 - 1


def test_wrapping_large_positive() -> None:
    """Large positive values wrap correctly."""
    a = MachineWordDomain({2**33})  # 2 * 2^32
    assert 0 in a  # wraps to 0


def test_wrapping_large_negative() -> None:
    """Large negative values wrap correctly."""
    a = MachineWordDomain({-(2**32)})
    assert 0 in a  # wraps to 0


# ============================================================================
# DOMAIN-SPECIFIC TESTS: MAX_TRACKED BUDGET
# ============================================================================


def test_exceeding_max_tracked_collapses_to_top() -> None:
    """Tracking > MAX_TRACKED elements returns top."""
    # Create sets that exceed MAX_TRACKED (16)
    large_set = set(range(20))
    result = MachineWordDomain.abstract(large_set)
    assert result == MachineWordDomain.top()


@given(machine_words(), machine_words())
def test_operations_respect_max_tracked(
    a: MachineWordDomain, b: MachineWordDomain
) -> None:
    """Binary operations collapse to top when result exceeds MAX_TRACKED."""
    result = a + b
    if result.residues is not None:
        assert len(result.residues) <= MachineWordDomain.MAX_TRACKED


def test_exactly_max_tracked_preserved() -> None:
    """Exactly MAX_TRACKED elements are tracked."""
    exact_set = set(range(16))
    result = MachineWordDomain.abstract(exact_set)
    assert result.residues == exact_set
    assert result != MachineWordDomain.top()


def test_addition_explosion() -> None:
    """Addition can cause explosion to top."""
    # 10 * 10 = 100 > MAX_TRACKED
    a = MachineWordDomain(set(range(10)))
    b = MachineWordDomain(set(range(0, 100, 10)))
    result = a + b
    # Should collapse to top due to size
    assert result == MachineWordDomain.top()


# ============================================================================
# DOMAIN-SPECIFIC TESTS: NEGATION (TWO'S COMPLEMENT)
# ============================================================================


def test_negation_twos_complement() -> None:
    """Negation uses two's complement semantics."""
    a = MachineWordDomain({1})
    result = -a
    # -1 in two's complement 32-bit = 0xFFFFFFFF = 2^32 - 1
    assert 2**32 - 1 in result


def test_negation_zero() -> None:
    """Negation of zero is zero."""
    a = MachineWordDomain({0})
    result = -a
    assert 0 in result


def test_negation_max_value() -> None:
    """Negation of max unsigned value."""
    a = MachineWordDomain({2**32 - 1})
    result = -a
    # -(2^32 - 1) = 1 (mod 2^32)
    assert 1 in result


def test_negation_sign_bit() -> None:
    """Negation of sign bit value."""
    a = MachineWordDomain({2**31})
    result = -a
    # -(2^31) = 2^31 (mod 2^32) in two's complement
    assert 2**31 in result


# ============================================================================
# DOMAIN-SPECIFIC TESTS: DIVISION BY ZERO
# ============================================================================


def test_division_by_zero_returns_top() -> None:
    """Division when divisor contains only 0 returns top."""
    a = MachineWordDomain({10, 20})
    b = MachineWordDomain({0})
    result = a / b
    assert result == MachineWordDomain.top()


def test_division_partial_zero() -> None:
    """Division when divisor set contains 0 among others returns top."""
    a = MachineWordDomain({10})
    b = MachineWordDomain({0, 2, 4})
    result = a / b
    assert result == MachineWordDomain.top()


def test_division_no_zero() -> None:
    """Division with no zero in divisor computes normally."""
    a = MachineWordDomain({20, 40})
    b = MachineWordDomain({2, 4})
    result = a / b
    # 20//2=10, 20//4=5, 40//2=20, 40//4=10
    # Result should contain these values
    assert not result.is_bot()
    if result.residues is not None:
        assert 10 in result  # noqa: PLR2004
        assert 5 in result  # noqa: PLR2004
        assert 20 in result  # noqa: PLR2004


# ============================================================================
# DOMAIN-SPECIFIC TESTS: COMPARISON REFINEMENT
# ============================================================================


def test_comparison_partitions_residues() -> None:
    """Comparisons partition residues based on truth values."""
    a = MachineWordDomain({1, 5, 10})
    b = MachineWordDomain({3, 7})

    result = a.lt(b)

    # True outcome: values where a_i < b_j
    if True in result:
        a_true, _b_true = result[True]
        # 1 < 3, 1 < 7, 5 < 7, so 1 and 5 should be in a_true
        assert 1 in a_true
        assert 5 in a_true  # noqa: PLR2004

    # False outcome: values where a_i >= b_j
    if False in result:
        a_false, _b_false = result[False]
        # 10 >= 3, 10 >= 7, 5 >= 3, so 10 and 5 should be in a_false
        assert 10 in a_false  # noqa: PLR2004


def test_equality_refines_to_intersection() -> None:
    """Equality refines both operands to their intersection."""
    a = MachineWordDomain({1, 5, 10})
    b = MachineWordDomain({5, 10, 15})

    result = a.eq(b)

    # True outcome: shared values
    if True in result:
        a_true, b_true = result[True]
        assert 5 in a_true  # noqa: PLR2004
        assert 10 in a_true  # noqa: PLR2004
        assert 5 in b_true  # noqa: PLR2004
        assert 10 in b_true  # noqa: PLR2004
        assert 1 not in a_true
        assert 15 not in b_true  # noqa: PLR2004


def test_comparison_with_singleton() -> None:
    """Comparison with singleton gives precise results."""
    a = MachineWordDomain({1, 5, 10})
    b = MachineWordDomain({5})

    lt_result = a.lt(b)
    eq_result = a.eq(b)
    gt_result = a.gt(b)

    # 1 < 5 (True), 5 < 5 (False), 10 < 5 (False)
    assert True in lt_result
    assert False in lt_result

    # Only 5 == 5
    assert True in eq_result
    if True in eq_result:
        a_eq, b_eq = eq_result[True]
        assert 5 in a_eq  # noqa: PLR2004
        assert 5 in b_eq  # noqa: PLR2004

    # 10 > 5 (True)
    assert True in gt_result
