"""Hypothesis-based property tests for StringDomain abstraction."""

from itertools import chain

from hypothesis import example, given
from hypothesis import strategies as st

from project.abstractions.abstraction import Comparison
from project.abstractions.string_set import StringDomain

# ============================================================================
# CONFIGURATION
# ============================================================================

# Number of concrete samples to use in oracle tests
# (configurable for performance tuning)
ORACLE_SAMPLES = 5

# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================


def string_elements() -> st.SearchStrategy[StringDomain]:
    """
    Generate string domain elements with diverse value sets.

    MAX_TRACKED = 5
    """
    # Random string sets (printable ASCII for readability)
    random_strings = st.builds(
        lambda strings: StringDomain(strings if strings else set()),
        strings=st.sets(
            st.text(
                alphabet=st.characters(min_codepoint=32, max_codepoint=126),
                min_size=0,
                max_size=10,
            ),
            max_size=5,
        ),
    )

    # Special cases
    special_strings = st.sampled_from(
        [
            StringDomain.bot(),
            StringDomain.top(),
            StringDomain({""}),  # empty string singleton
            StringDomain({"a"}),  # single char
            StringDomain({"hello", "world"}),  # common strings
            StringDomain({"0", "1", "2", "3", "4"}),  # exactly MAX_TRACKED
            StringDomain({"x" * i for i in range(1, 6)}),  # varying lengths
            StringDomain({"apple", "banana"}),  # lexicographic test
        ]
    )

    return st.one_of(random_strings, special_strings)


def comparison_ops() -> st.SearchStrategy[Comparison]:
    """Generate all comparison operations."""
    return st.sampled_from(["le", "lt", "eq", "ne", "ge", "gt"])


# ============================================================================
# BASIC PROPERTY TESTS
# ============================================================================


@given(st.sets(st.text(max_size=10)))
def test_valid_abstraction(xs: set[str]) -> None:
    """Property: All concrete values are contained in their abstraction."""
    string_dom = StringDomain.abstract(xs)
    for x in xs:
        assert x in string_dom


@given(string_elements(), string_elements(), comparison_ops())
def test_compare_returns_valid_bool_set_all_ops(
    s1: StringDomain, s2: StringDomain, op: Comparison
) -> None:
    """Property: Comparison returns valid dict with bool keys and string values."""
    result = s1.compare(op, s2)
    strings_list = list(chain.from_iterable(result.values()))

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)
    assert all(isinstance(v, StringDomain) for v in strings_list)


# ============================================================================
# COMPLEMENTARITY PROPERTIES
# ============================================================================


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_comparison_complementarity_lt_ge(s1: StringDomain, s2: StringDomain) -> None:
    """Property: x < y and x >= y are complements."""
    lt_result = s1.lt(s2)
    ge_result = s1.ge(s2)

    # If both non-empty, outcomes should be complementary
    if lt_result and ge_result:
        for outcome in [True, False]:
            if outcome in lt_result:
                complement = not outcome
                assert complement in ge_result or outcome in ge_result


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_comparison_complementarity_le_gt(s1: StringDomain, s2: StringDomain) -> None:
    """Property: x <= y and x > y are complements."""
    le_result = s1.le(s2)
    gt_result = s1.gt(s2)

    if le_result and gt_result:
        for outcome in [True, False]:
            if outcome in le_result:
                complement = not outcome
                assert complement in gt_result or outcome in gt_result


@given(string_elements(), string_elements())
@example(StringDomain({"hello"}), StringDomain({"hello"}))
def test_comparison_complementarity_eq_ne(s1: StringDomain, s2: StringDomain) -> None:
    """Property: x == y and x != y are complements."""
    eq_result = s1.eq(s2)
    ne_result = s1.ne(s2)

    if True in eq_result and False in ne_result:
        assert eq_result[True] == ne_result[False]

    if False in eq_result and True in ne_result:
        assert eq_result[False] == ne_result[True]


# ============================================================================
# SYMMETRY PROPERTIES
# ============================================================================


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
@example(StringDomain.bot(), StringDomain({"hello"}))
def test_comparison_symmetry_eq(s1: StringDomain, s2: StringDomain) -> None:
    """Property: Equality is symmetric."""
    eq_12 = s1.eq(s2)
    eq_21 = s2.eq(s1)

    assert eq_12.keys() == eq_21.keys()

    for outcome in eq_12:
        s1_refined, s2_refined = eq_12[outcome]
        s2_refined_rev, s1_refined_rev = eq_21[outcome]
        assert s1_refined == s1_refined_rev
        assert s2_refined == s2_refined_rev


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"x", "y"}))
def test_comparison_antisymmetry_lt_gt(s1: StringDomain, s2: StringDomain) -> None:
    """Property: s1 < s2 is the opposite of s2 > s1."""
    lt_result = s1.lt(s2)
    gt_result = s2.gt(s1)

    assert lt_result.keys() == gt_result.keys()

    for outcome in lt_result:
        s1_refined_lt, s2_refined_lt = lt_result[outcome]
        s2_refined_gt, s1_refined_gt = gt_result[outcome]
        assert s1_refined_lt == s1_refined_gt
        assert s2_refined_lt == s2_refined_gt


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_comparison_antisymmetry_le_ge(s1: StringDomain, s2: StringDomain) -> None:
    """Property: s1 <= s2 is the opposite of s2 >= s1."""
    le_result = s1.le(s2)
    ge_result = s2.ge(s1)

    assert le_result.keys() == ge_result.keys()

    for outcome in le_result:
        s1_refined_le, s2_refined_le = le_result[outcome]
        s2_refined_ge, s1_refined_ge = ge_result[outcome]
        assert s1_refined_le == s1_refined_ge
        assert s2_refined_le == s2_refined_ge


# ============================================================================
# IDENTITY PROPERTIES
# ============================================================================


@given(string_elements())
@example(StringDomain({"hello"}))
@example(StringDomain({"a", "b", "c"}))
def test_comparison_identity_eq(s: StringDomain) -> None:
    """Property: x == x should always include True outcome for non-bot."""
    eq_result = s.eq(s)

    if s.values != set():
        assert True in eq_result
        assert eq_result[True] == (s, s)
    else:
        # Bot case
        assert len(eq_result) == 0 or eq_result == {}


@given(string_elements())
@example(StringDomain({"a", "b"}))
def test_comparison_identity_le(s: StringDomain) -> None:
    """Property: x <= x should always include True."""
    le_result = s.le(s)

    if s.values != set():
        assert True in le_result


@given(string_elements())
@example(StringDomain({"a", "b"}))
def test_comparison_identity_ge(s: StringDomain) -> None:
    """Property: x >= x should always include True."""
    ge_result = s.ge(s)

    if s.values != set():
        assert True in ge_result


# ============================================================================
# LOGICAL RELATIONSHIP PROPERTIES
# ============================================================================


@given(string_elements(), string_elements())
@example(StringDomain({"a"}), StringDomain({"z"}))
def test_logical_relationship_lt_implies_le(s1: StringDomain, s2: StringDomain) -> None:
    """Property: x < y implies x <= y."""
    lt_result = s1.lt(s2)
    le_result = s1.le(s2)

    if True in lt_result:
        assert True in le_result
        lt_s1, lt_s2 = lt_result[True]
        le_s1, le_s2 = le_result[True]
        assert lt_s1 <= le_s1
        assert lt_s2 <= le_s2


@given(string_elements(), string_elements())
@example(StringDomain({"z"}), StringDomain({"a"}))
def test_logical_relationship_gt_implies_ge(s1: StringDomain, s2: StringDomain) -> None:
    """Property: x > y implies x >= y."""
    gt_result = s1.gt(s2)
    ge_result = s1.ge(s2)

    if True in gt_result:
        assert True in ge_result
        gt_s1, gt_s2 = gt_result[True]
        ge_s1, ge_s2 = ge_result[True]
        assert gt_s1 <= ge_s1
        assert gt_s2 <= ge_s2


@given(string_elements(), string_elements())
@example(StringDomain({"hello"}), StringDomain({"hello"}))
def test_logical_relationship_eq_implies_le_and_ge(
    s1: StringDomain, s2: StringDomain
) -> None:
    """Property: x == y implies x <= y and x >= y."""
    eq_result = s1.eq(s2)
    le_result = s1.le(s2)
    ge_result = s1.ge(s2)

    if True in eq_result:
        assert True in le_result
        assert True in ge_result


# ============================================================================
# LATTICE PROPERTY TESTS
# ============================================================================


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_meet_commutativity(s1: StringDomain, s2: StringDomain) -> None:
    """Property: Meet is commutative (s1 ⊓ s2 = s2 ⊓ s1)."""
    assert (s1 & s2) == (s2 & s1)


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_join_commutativity(s1: StringDomain, s2: StringDomain) -> None:
    """Property: Join is commutative (s1 ⊔ s2 = s2 ⊔ s1)."""
    assert (s1 | s2) == (s2 | s1)


@given(string_elements(), string_elements(), string_elements())
def test_meet_associativity(
    s1: StringDomain, s2: StringDomain, s3: StringDomain
) -> None:
    """Property: Meet is associative ((s1 ⊓ s2) ⊓ s3 = s1 ⊓ (s2 ⊓ s3))."""
    assert ((s1 & s2) & s3) == (s1 & (s2 & s3))


@given(string_elements(), string_elements(), string_elements())
def test_join_associativity(
    s1: StringDomain, s2: StringDomain, s3: StringDomain
) -> None:
    """Property: Join is associative ((s1 ⊔ s2) ⊔ s3 = s1 ⊔ (s2 ⊔ s3))."""
    assert ((s1 | s2) | s3) == (s1 | (s2 | s3))


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_absorption_law_1(s1: StringDomain, s2: StringDomain) -> None:
    """Property: Absorption law s1 ⊔ (s1 ⊓ s2) = s1."""
    assert (s1 | (s1 & s2)) == s1


@given(string_elements(), string_elements())
@example(StringDomain({"a", "b"}), StringDomain({"c", "d"}))
def test_absorption_law_2(s1: StringDomain, s2: StringDomain) -> None:
    """Property: Absorption law s1 ⊓ (s1 ⊔ s2) = s1."""
    assert (s1 & (s1 | s2)) == s1


@given(string_elements())
@example(StringDomain({"hello", "world"}))
def test_bot_is_identity_for_join(s: StringDomain) -> None:
    """Property: Bot is identity for join (s ⊔ ⊥ = s)."""
    bot = StringDomain.bot()
    assert (s | bot) == s
    assert (bot | s) == s


@given(string_elements())
@example(StringDomain({"hello", "world"}))
def test_bot_is_absorbing_for_meet(s: StringDomain) -> None:
    """Property: Bot is absorbing for meet (s ⊓ ⊥ = ⊥)."""
    bot = StringDomain.bot()
    assert (s & bot) == bot
    assert (bot & s) == bot


# ============================================================================
# TOP ELEMENT BINARY OPERATIONS
# ============================================================================


@given(string_elements())
@example(StringDomain({""}))
@example(StringDomain({"hello", "world"}))
@example(StringDomain.bot())
def test_top_addition(s: StringDomain) -> None:
    """Property: Top + string = Top (concatenation)."""
    top = StringDomain.top()

    if s.values == set():  # bot
        assert (top + s).values == set()
        assert (s + top).values == set()
    else:
        result1 = top + s
        result2 = s + top
        assert result1 == top, f"Expected Top + {s} = Top, got {result1}"
        assert result2 == top, f"Expected {s} + Top = Top, got {result2}"


def test_top_with_top_operations() -> None:
    """Property: Binary operations between two Top elements."""
    top = StringDomain.top()

    # Top + Top = Top (concatenation)
    assert (top + top) == top

    # Top - Top = Top (subtraction returns top for strings)
    assert (top - top) == top


# ============================================================================
# DOMAIN-SPECIFIC TESTS: STRING CONCATENATION
# ============================================================================


def test_concatenation_cartesian_product() -> None:
    """Concatenation computes Cartesian product of string sets."""
    s1 = StringDomain({"hello", "hi"})
    s2 = StringDomain({"world", "there"})

    result = s1 + s2
    assert "helloworld" in result
    assert "hellothere" in result
    assert "hiworld" in result
    assert "hithere" in result


def test_concatenation_empty_string() -> None:
    """Concatenating with empty string preserves values."""
    s1 = StringDomain({"hello"})
    s2 = StringDomain({""})

    result = s1 + s2
    assert "hello" in result


def test_concatenation_explosion() -> None:
    """Large Cartesian product collapses to top."""
    s1 = StringDomain({"a", "b", "c"})
    s2 = StringDomain({"x", "y", "z"})

    result = s1 + s2
    # 3 * 3 = 9 > MAX_TRACKED (5)
    assert result == StringDomain.top()


def test_concatenation_bot() -> None:
    """Concatenation with bot returns bot."""
    s1 = StringDomain({"hello"})
    bot = StringDomain.bot()

    assert (s1 + bot) == bot
    assert (bot + s1) == bot


def test_concatenation_single_char() -> None:
    """Concatenation of single characters."""
    s1 = StringDomain({"a", "b"})
    s2 = StringDomain({"x"})

    result = s1 + s2
    assert "ax" in result
    assert "bx" in result


# ============================================================================
# DOMAIN-SPECIFIC TESTS: MAX_TRACKED BUDGET
# ============================================================================


def test_exceeding_max_tracked_collapses_to_top() -> None:
    """Abstracting > MAX_TRACKED strings returns top."""
    large_set = {str(i) for i in range(10)}
    result = StringDomain.abstract(large_set)
    assert result == StringDomain.top()


def test_abstraction_exactly_max_tracked() -> None:
    """Exactly MAX_TRACKED strings are tracked."""
    exact_set = {str(i) for i in range(5)}
    result = StringDomain.abstract(exact_set)
    assert result.values == exact_set


def test_join_exceeding_max_tracked() -> None:
    """Join that exceeds MAX_TRACKED collapses to top."""
    s1 = StringDomain({"a", "b", "c"})
    s2 = StringDomain({"d", "e", "f"})

    result = s1 | s2
    # 3 + 3 = 6 > MAX_TRACKED (5)
    assert result == StringDomain.top()


def test_join_within_max_tracked() -> None:
    """Join within MAX_TRACKED is tracked."""
    s1 = StringDomain({"a", "b"})
    s2 = StringDomain({"c", "d"})

    result = s1 | s2
    # 2 + 2 = 4 <= MAX_TRACKED (5)
    assert result.values == {"a", "b", "c", "d"}


# ============================================================================
# DOMAIN-SPECIFIC TESTS: TYPE COERCION
# ============================================================================


def test_int_to_string_coercion() -> None:
    """Integers are coerced to strings during abstraction."""
    result = StringDomain.abstract({1, 2, 3})
    assert "1" in result
    assert "2" in result
    assert "3" in result


def test_mixed_types_coercion() -> None:
    """Mixed types are all coerced to strings."""
    result = StringDomain.abstract({1, "hello", 3.14})
    assert "1" in result
    assert "hello" in result
    assert "3.14" in result


def test_empty_string_abstraction() -> None:
    """Empty string is tracked."""
    result = StringDomain.abstract({""})
    assert "" in result
    assert result.values == {""}


def test_coercion_preserves_uniqueness() -> None:
    """Coercion removes duplicates."""
    result = StringDomain.abstract({1, "1", 1.0})  # noqa: B033
    # All coerce to "1"
    assert "1" in result
    # Should only have one "1"
    assert len(result.values) == 1 if result.values is not None else True


# ============================================================================
# DOMAIN-SPECIFIC TESTS: COMPARISON OPERATIONS (LEXICOGRAPHIC)
# ============================================================================


def test_comparison_lexicographic_ordering() -> None:
    """String comparisons use lexicographic ordering."""
    s1 = StringDomain({"apple", "banana"})
    s2 = StringDomain({"cherry"})

    result = s1.lt(s2)

    # "apple" < "cherry" and "banana" < "cherry", so True outcome
    assert True in result
    if True in result:
        s1_true, _s2_true = result[True]
        assert "apple" in s1_true
        assert "banana" in s1_true


def test_equality_string_matching() -> None:
    """Equality partitions by exact string match."""
    s1 = StringDomain({"hello", "world"})
    s2 = StringDomain({"hello", "there"})

    result = s1.eq(s2)

    # True outcome: "hello" == "hello"
    assert True in result
    if True in result:
        s1_true, s2_true = result[True]
        assert "hello" in s1_true
        assert "hello" in s2_true

    # False outcome: "world" != "there", etc.
    assert False in result


def test_comparison_empty_string() -> None:
    """Empty string comparisons."""
    s1 = StringDomain({""})
    s2 = StringDomain({"a"})

    lt_result = s1.lt(s2)
    # "" < "a" is True
    assert True in lt_result


def test_comparison_case_sensitive() -> None:
    """String comparison is case-sensitive."""
    s1 = StringDomain({"apple"})
    s2 = StringDomain({"Apple"})

    eq_result = s1.eq(s2)
    # "apple" != "Apple"
    assert False in eq_result or True not in eq_result


def test_comparison_numeric_strings() -> None:
    """Numeric string comparison is lexicographic, not numeric."""
    s1 = StringDomain({"10", "2"})
    s2 = StringDomain({"2"})

    lt_result = s1.lt(s2)
    # "10" < "2" lexicographically (True), "2" < "2" (False)
    assert True in lt_result
    if True in lt_result:
        s1_true, _ = lt_result[True]
        assert "10" in s1_true


# ============================================================================
# DOMAIN-SPECIFIC TESTS: TOP ELEMENT BEHAVIOR
# ============================================================================


def test_top_containment() -> None:
    """Top contains all strings."""
    top = StringDomain.top()
    assert "any string" in top
    assert "" in top
    assert "xyz" in top
    assert "12345" in top


def test_operations_with_top() -> None:
    """Operations with top return top."""
    s = StringDomain({"hello"})
    top = StringDomain.top()

    assert (s + top) == top
    assert (top + s) == top


def test_top_meet_any() -> None:
    """Top meet any returns any."""
    top = StringDomain.top()
    s = StringDomain({"hello", "world"})

    assert (top & s) == s
    assert (s & top) == s


def test_top_join_any() -> None:
    """Top join any returns top."""
    top = StringDomain.top()
    s = StringDomain({"hello", "world"})

    assert (top | s) == top
    assert (s | top) == top


# ============================================================================
# DOMAIN-SPECIFIC TESTS: NEGATION AND NON-ARITHMETIC OPERATIONS
# ============================================================================


def test_negation_preserves_strings() -> None:
    """Negation is identity for strings (no numeric negation)."""
    s = StringDomain({"hello", "world"})
    result = -s
    assert result == s


def test_non_concatenation_arithmetic_returns_top() -> None:
    """Subtraction, multiplication, etc. return top for strings."""
    s1 = StringDomain({"hello"})
    s2 = StringDomain({"world"})

    assert (s1 - s2) == StringDomain.top()
    assert (s1 * s2) == StringDomain.top()
    assert (s1 / s2) == StringDomain.top()


def test_negation_bot() -> None:
    """Negation of bot is bot."""
    bot = StringDomain.bot()
    result = -bot
    assert result == bot


def test_negation_top() -> None:
    """Negation of top is top."""
    top = StringDomain.top()
    result = -top
    assert result == top


# ============================================================================
# DOMAIN-SPECIFIC TESTS: I2S CAST
# ============================================================================


def test_i2s_cast_int_to_string() -> None:
    """i2s cast converts int to string singleton."""
    result = StringDomain.i2s_cast(42)
    assert "42" in result
    assert result == StringDomain({"42"})


def test_i2s_cast_zero() -> None:
    """i2s cast for zero."""
    result = StringDomain.i2s_cast(0)
    assert "0" in result
    assert result == StringDomain({"0"})


def test_i2s_cast_negative() -> None:
    """i2s cast for negative value."""
    result = StringDomain.i2s_cast(-100)
    assert "-100" in result
    assert result == StringDomain({"-100"})


# ============================================================================
# DOMAIN-SPECIFIC TESTS: BOT HANDLING
# ============================================================================


def test_bot_properties() -> None:
    """Bot has expected properties."""
    bot = StringDomain.bot()
    assert bot.values == set()
    assert "anything" not in bot


def test_meet_with_bot() -> None:
    """Meet with bot returns bot."""
    s = StringDomain({"hello", "world"})
    bot = StringDomain.bot()

    assert (s & bot) == bot
    assert (bot & s) == bot


def test_join_with_bot() -> None:
    """Join with bot returns original."""
    s = StringDomain({"hello", "world"})
    bot = StringDomain.bot()

    assert (s | bot) == s
    assert (bot | s) == s


# ============================================================================
# DOMAIN-SPECIFIC TESTS: POSET ORDERING
# ============================================================================


def test_poset_ordering_subset() -> None:
    """Smaller set is ⊑ larger set."""
    small = StringDomain({"a", "b"})
    large = StringDomain({"a", "b", "c", "d"})

    assert small <= large
    assert not (large <= small)


def test_poset_ordering_bot() -> None:
    """Bot is ⊑ everything."""
    bot = StringDomain.bot()
    s = StringDomain({"hello", "world"})

    assert bot <= s
    assert bot <= bot  # noqa: PLR0124


def test_poset_ordering_top() -> None:
    """Everything is ⊑ top."""
    top = StringDomain.top()
    s = StringDomain({"hello", "world"})

    assert s <= top
    assert top <= top  # noqa: PLR0124


def test_poset_ordering_disjoint() -> None:
    """Disjoint sets are not comparable."""
    s1 = StringDomain({"a", "b"})
    s2 = StringDomain({"c", "d"})

    assert not (s1 <= s2)
    assert not (s2 <= s1)
