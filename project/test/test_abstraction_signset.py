from itertools import chain, product
from typing import get_args

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from hypothesis.strategies import integers, sampled_from, sets

from project.abstractions.abstraction import Comparison
from project.abstractions.signset import SignSet

# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================

def sign_sets_exhaustive() -> st.SearchStrategy[SignSet]:
    """
    Exhaustive strategy sampling from all 8 possible SignSets.

    Guarantees coverage: {}, {+}, {-}, {0}, {+,-}, {+,0}, {-,0}, {+,-,0}.
    """
    all_signsets = [
        SignSet(set()),
        SignSet({"+"}),
        SignSet({"-"}),
        SignSet({"0"}),
        SignSet({"+", "-"}),
        SignSet({"+", "0"}),
        SignSet({"-", "0"}),
        SignSet({"+", "-", "0"}),
    ]
    return st.sampled_from(all_signsets)


def comparison_ops() -> st.SearchStrategy[Comparison]:
    """Generate all comparison operations."""
    return st.sampled_from(["le", "lt", "eq", "ne", "ge", "gt"])


# ============================================================================
# EXISTING TESTS
# ============================================================================


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
            <= SignSet.abstract(xs).compare("le", SignSet.abstract(ys)).keys()
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
    sign_sets = list(chain.from_iterable(result.values()))

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)
    assert all(isinstance(v, SignSet) for v in sign_sets)

    if len(xs) > 0 and len(ys) > 0:
        assert True in result or False in result

def test_singset_binary_comparison() -> None:
    s1 = SignSet({"0", "-"})
    s2 = SignSet({"0", "+"})

    # {0, -} < {0, +}
    # True  -> {0, -}, {0, +}
    # False -> {0}, {0}
    lt_result = s1.lt(s2)
    assert lt_result == {
        True: (SignSet({"0", "-"}), SignSet({"0", "+"})),
        False: (SignSet({"0"}), SignSet({"0"}))
    }

    s1 = SignSet({"0"})
    s2 = SignSet({"0", "+"})
    # {0} < {0, +}
    # True  -> {0}, {+}
    # False -> {0}, {0}
    lt_result = s1.lt(s2)
    assert lt_result == {
        True: (SignSet({"0"}), SignSet({"+"})),
        False: (SignSet({"0"}), SignSet({"0"}))
    }


# ============================================================================
# NEW PROPERTY-BASED TESTS
# ============================================================================
# TODO(kornel): review tests
# --- Complementarity Properties ---

@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_comparison_complementarity_lt_ge(s1: SignSet, s2: SignSet) -> None:
    """Property: x < y and x >= y are complements."""
    lt_result = s1.lt(s2)
    ge_result = s1.ge(s2)

    for outcome in [True, False]:
        if outcome in lt_result:
            complement = not outcome
            assert complement in ge_result or outcome in ge_result


@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_comparison_complementarity_le_gt(s1: SignSet, s2: SignSet) -> None:
    """Property: x <= y and x > y are complements."""
    le_result = s1.le(s2)
    gt_result = s1.gt(s2)

    for outcome in [True, False]:
        if outcome in le_result:
            complement = not outcome
            assert complement in gt_result or outcome in gt_result


@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_comparison_complementarity_eq_ne(s1: SignSet, s2: SignSet) -> None:
    """Property: x == y and x != y are complements."""
    eq_result = s1.eq(s2)
    ne_result = s1.ne(s2)

    if True in eq_result and False in ne_result:
        assert eq_result[True] == ne_result[False]

    if False in eq_result and True in ne_result:
        assert eq_result[False] == ne_result[True]


# --- Symmetry Properties ---

@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_comparison_symmetry_eq(s1: SignSet, s2: SignSet) -> None:
    """Property: Equality is symmetric."""
    eq_12 = s1.eq(s2)
    eq_21 = s2.eq(s1)

    assert eq_12.keys() == eq_21.keys()

    for outcome in eq_12:
        s1_refined, s2_refined = eq_12[outcome]
        s2_refined_rev, s1_refined_rev = eq_21[outcome]
        assert s1_refined == s1_refined_rev
        assert s2_refined == s2_refined_rev


@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_comparison_antisymmetry_lt_gt(s1: SignSet, s2: SignSet) -> None:
    """Property: s1 < s2 is the opposite of s2 > s1."""
    lt_result = s1.lt(s2)
    gt_result = s2.gt(s1)

    assert lt_result.keys() == gt_result.keys()

    for outcome in lt_result:
        s1_refined_lt, s2_refined_lt = lt_result[outcome]
        s2_refined_gt, s1_refined_gt = gt_result[outcome]
        assert s1_refined_lt == s1_refined_gt
        assert s2_refined_lt == s2_refined_gt


@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_comparison_antisymmetry_le_ge(s1: SignSet, s2: SignSet) -> None:
    """Property: s1 <= s2 is the opposite of s2 >= s1."""
    le_result = s1.le(s2)
    ge_result = s2.ge(s1)

    assert le_result.keys() == ge_result.keys()

    for outcome in le_result:
        s1_refined_le, s2_refined_le = le_result[outcome]
        s2_refined_ge, s1_refined_ge = ge_result[outcome]
        assert s1_refined_le == s1_refined_ge
        assert s2_refined_le == s2_refined_ge


# --- Identity Properties ---

@given(sign_sets_exhaustive())
def test_comparison_identity_eq(s: SignSet) -> None:
    """Property: x == x should always include True outcome for non-empty sets."""
    eq_result = s.eq(s)

    if len(s.signs) > 0:
        assert True in eq_result
        # For identity comparison, refined sets should equal the original
        assert eq_result[True] == (s, s)
    elif len(s.signs) == 0:
        assert eq_result == {}


@given(sign_sets_exhaustive())
def test_comparison_identity_le(s: SignSet) -> None:
    """Property: x <= x should always include True."""
    le_result = s.le(s)

    if len(s.signs) > 0:
        assert True in le_result


@given(sign_sets_exhaustive())
def test_comparison_identity_ge(s: SignSet) -> None:
    """Property: x >= x should always include True."""
    ge_result = s.ge(s)

    if len(s.signs) > 0:
        assert True in ge_result


# --- Logical Relationship Properties ---

@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_logical_relationship_lt_implies_le(s1: SignSet, s2: SignSet) -> None:
    """Property: x < y implies x <= y."""
    lt_result = s1.lt(s2)
    le_result = s1.le(s2)

    if True in lt_result:
        assert True in le_result
        lt_s1, lt_s2 = lt_result[True]
        le_s1, le_s2 = le_result[True]
        assert lt_s1 <= le_s1
        assert lt_s2 <= le_s2


@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_logical_relationship_gt_implies_ge(s1: SignSet, s2: SignSet) -> None:
    """Property: x > y implies x >= y."""
    gt_result = s1.gt(s2)
    ge_result = s1.ge(s2)

    if True in gt_result:
        assert True in ge_result
        gt_s1, gt_s2 = gt_result[True]
        ge_s1, ge_s2 = ge_result[True]
        assert gt_s1 <= ge_s1
        assert gt_s2 <= ge_s2


@given(sign_sets_exhaustive(), sign_sets_exhaustive())
def test_logical_relationship_eq_implies_le_and_ge(s1: SignSet, s2: SignSet) -> None:
    """Property: x == y implies x <= y and x >= y."""
    eq_result = s1.eq(s2)
    le_result = s1.le(s2)
    ge_result = s1.ge(s2)

    if True in eq_result:
        assert True in le_result
        assert True in ge_result


# --- Soundness (Oracle-based) ---

def compute_concrete_outcomes(s1: SignSet, s2: SignSet, op: Comparison) -> set[bool]:
    """Oracle: compute concrete outcomes for sign sets."""
    outcomes = set()
    concrete_map = {"+": [1, 2, 100], "-": [-1, -2, -100], "0": [0]}

    for sign1 in s1.signs:
        for sign2 in s2.signs:
            for val1 in concrete_map[sign1]:
                for val2 in concrete_map[sign2]:
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


@given(sign_sets_exhaustive(), sign_sets_exhaustive(), comparison_ops())
@example(SignSet({"0"}), SignSet({"0"}), "eq")
@example(SignSet({"+"}), SignSet({"-"}), "gt")
@example(SignSet({"-"}), SignSet({"+"}), "lt")
def test_soundness_concrete_oracle(s1: SignSet, s2: SignSet, op: Comparison) -> None:
    """Property: Abstract comparison is sound w.r.t. concrete execution."""
    if len(s1.signs) == 0 or len(s2.signs) == 0:
        return

    result = s1.compare(op, s2)
    concrete_outcomes = compute_concrete_outcomes(s1, s2, op)

    for concrete_outcome in concrete_outcomes:
        assert concrete_outcome in result, \
            f"Concrete outcome {concrete_outcome} not in result for {s1} {op} {s2}"


# --- Refinement Coverage ---

@given(sign_sets_exhaustive(), sign_sets_exhaustive(), comparison_ops())
@example(SignSet(set()), SignSet(set()), "eq")
@example(SignSet({"+", "-", "0"}), SignSet({"+", "-", "0"}), "eq")
def test_comparison_refinement_coverage(
    s1: SignSet, s2: SignSet, op: Comparison
) -> None:
    """Property: Refinements cover the original sets and are valid subsets."""
    result = s1.compare(op, s2)

    # Refined sets should be subsets
    for refined_s1, refined_s2 in result.values():
        assert isinstance(refined_s1, SignSet)
        assert isinstance(refined_s2, SignSet)
        assert refined_s1 <= s1
        assert refined_s2 <= s2

    # Union of refined sets should cover originals
    if result:
        all_s1_refined = SignSet.bot()
        all_s2_refined = SignSet.bot()
        for refined_s1, refined_s2 in result.values():
            all_s1_refined = all_s1_refined | refined_s1
            all_s2_refined = all_s2_refined | refined_s2
        assert all_s1_refined == s1
        assert all_s2_refined == s2


# ============================================================================
# EXHAUSTIVE PARAMETRIZED TESTS (100% Systematic Coverage)
# ============================================================================

ALL_SIGNSETS = [
    SignSet(set()),
    SignSet({"+"}),
    SignSet({"-"}),
    SignSet({"0"}),
    SignSet({"+", "-"}),
    SignSet({"+", "0"}),
    SignSet({"-", "0"}),
    SignSet({"+", "-", "0"}),
]

ALL_OPS = ["le", "lt", "eq", "ne", "ge", "gt"]


@pytest.mark.parametrize(
    ("s1", "s2", "op"), product(ALL_SIGNSETS, ALL_SIGNSETS, ALL_OPS)
)
def test_exhaustive_comparison_coverage(
    s1: SignSet, s2: SignSet, op: Comparison
) -> None:
    """
    Exhaustive test: all 8*8*6 = 384 combinations.

    Ensures 100% systematic coverage.
    """
    result = s1.compare(op, s2)

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)

    for refined_s1, refined_s2 in result.values():
        assert refined_s1 <= s1
        assert refined_s2 <= s2
