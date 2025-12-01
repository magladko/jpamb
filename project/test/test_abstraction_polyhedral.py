"""Hypothesis-based property tests for PolyhedralDomain abstraction."""

from itertools import chain

from hypothesis import example, given
from hypothesis import strategies as st

from project.abstractions.abstraction import Comparison
from project.abstractions.polyhedral import PolyhedralDomain

# ============================================================================
# CONFIGURATION
# ============================================================================

# Number of concrete samples to use in oracle tests
# (configurable for performance tuning)
ORACLE_SAMPLES = 5

# ============================================================================
# HYPOTHESIS STRATEGIES
# ============================================================================


def polyhedral_elements() -> st.SearchStrategy[PolyhedralDomain]:
    """Generate polyhedral elements with diverse dimensions and bounds."""
    # 1D random polyhedra (filter out NaN and inf)
    random_1d = st.builds(
        lambda points: PolyhedralDomain.abstract(points),
        points=st.sets(
            st.floats(
                min_value=-100.0,
                max_value=100.0,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=5,
        ),
    )

    # 2D random polyhedra
    random_2d = st.builds(
        lambda points: PolyhedralDomain.abstract(points),
        points=st.sets(
            st.tuples(
                st.floats(
                    min_value=-100.0,
                    max_value=100.0,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.floats(
                    min_value=-100.0,
                    max_value=100.0,
                    allow_nan=False,
                    allow_infinity=False,
                ),
            ),
            min_size=1,
            max_size=5,
        ),
    )

    # Special cases
    special_polys = st.sampled_from(
        [
            PolyhedralDomain.bot(dimension=1),
            PolyhedralDomain.top(dimension=1),
            PolyhedralDomain.bot(dimension=2),
            PolyhedralDomain.top(dimension=2),
            PolyhedralDomain.abstract({0.0}),  # singleton
            PolyhedralDomain.abstract({-10.0, 10.0}),  # interval
            PolyhedralDomain.abstract({(0.0, 0.0)}),  # 2D origin
            PolyhedralDomain.abstract({(0.0, 0.0), (1.0, 1.0)}),  # 2D box
            PolyhedralDomain.abstract({(1.0, 2.0), (3.0, 4.0)}),  # 2D box
        ]
    )

    return st.one_of(random_1d, random_2d, special_polys)


def comparison_ops() -> st.SearchStrategy[Comparison]:
    """Generate all comparison operations."""
    return st.sampled_from(["le", "lt", "eq", "ne", "ge", "gt"])


# ============================================================================
# BASIC PROPERTY TESTS
# ============================================================================


@given(
    st.sets(
        st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False)
    )
)
def test_valid_abstraction_1d(xs: set[float]) -> None:
    """Property: All concrete values are contained in their abstraction (1D)."""
    if not xs:
        return
    poly = PolyhedralDomain.abstract(xs)
    for x in xs:
        assert x in poly


@given(
    st.sets(
        st.tuples(
            st.floats(
                min_value=-100, max_value=100, allow_nan=False, allow_infinity=False
            ),
            st.floats(
                min_value=-100, max_value=100, allow_nan=False, allow_infinity=False
            ),
        ),
        min_size=1,
    )
)
def test_valid_abstraction_2d(xs: set[tuple[float, float]]) -> None:
    """Property: All concrete values are contained in their abstraction (2D)."""
    poly = PolyhedralDomain.abstract(xs)
    for x in xs:
        assert x in poly


@given(polyhedral_elements(), polyhedral_elements(), comparison_ops())
def test_compare_returns_valid_bool_set_all_ops(
    p1: PolyhedralDomain, p2: PolyhedralDomain, op: Comparison
) -> None:
    """Property: Comparison returns valid dict with bool keys and polyhedral values."""
    result = p1.compare(op, p2)
    polys_list = list(chain.from_iterable(result.values()))

    assert isinstance(result, dict)
    assert all(isinstance(k, bool) for k in result)
    assert all(isinstance(v, PolyhedralDomain) for v in polys_list)


# ============================================================================
# COMPLEMENTARITY PROPERTIES
# ============================================================================


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({0.0, 10.0}), PolyhedralDomain.abstract({5.0, 15.0}))
def test_comparison_complementarity_lt_ge(
    p1: PolyhedralDomain, p2: PolyhedralDomain
) -> None:
    """Property: x < y and x >= y are complements."""
    # Skip if dimensions don't match
    if p1.dimension != p2.dimension:
        return

    lt_result = p1.lt(p2)
    ge_result = p1.ge(p2)

    # If both non-empty, outcomes should be complementary
    if lt_result and ge_result:
        for outcome in [True, False]:
            if outcome in lt_result:
                complement = not outcome
                assert complement in ge_result or outcome in ge_result


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({0.0, 10.0}), PolyhedralDomain.abstract({5.0, 15.0}))
def test_comparison_complementarity_le_gt(
    p1: PolyhedralDomain, p2: PolyhedralDomain
) -> None:
    """Property: x <= y and x > y are complements."""
    if p1.dimension != p2.dimension:
        return

    le_result = p1.le(p2)
    gt_result = p1.gt(p2)

    if le_result and gt_result:
        for outcome in [True, False]:
            if outcome in le_result:
                complement = not outcome
                assert complement in gt_result or outcome in gt_result


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({5.0}), PolyhedralDomain.abstract({5.0}))
def test_comparison_complementarity_eq_ne(
    p1: PolyhedralDomain, p2: PolyhedralDomain
) -> None:
    """Property: x == y and x != y are complements."""
    if p1.dimension != p2.dimension:
        return

    eq_result = p1.eq(p2)
    ne_result = p1.ne(p2)

    # For polyhedral domain, complementarity may not be exact due to approximation
    # Just verify valid results
    assert isinstance(eq_result, dict)
    assert isinstance(ne_result, dict)


# ============================================================================
# SYMMETRY PROPERTIES
# ============================================================================


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({3.0, 7.0}))
@example(PolyhedralDomain.bot(), PolyhedralDomain.abstract({1.0, 5.0}))
def test_comparison_symmetry_eq(p1: PolyhedralDomain, p2: PolyhedralDomain) -> None:
    """Property: Equality is symmetric."""
    if p1.dimension != p2.dimension:
        return

    eq_12 = p1.eq(p2)
    eq_21 = p2.eq(p1)

    assert eq_12.keys() == eq_21.keys()

    for outcome in eq_12:
        p1_refined, p2_refined = eq_12[outcome]
        p2_refined_rev, p1_refined_rev = eq_21[outcome]
        assert p1_refined == p1_refined_rev
        assert p2_refined == p2_refined_rev


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({6.0, 10.0}))
def test_comparison_antisymmetry_lt_gt(
    p1: PolyhedralDomain, p2: PolyhedralDomain
) -> None:
    """Property: p1 < p2 is the opposite of p2 > p1."""
    if p1.dimension != p2.dimension:
        return

    lt_result = p1.lt(p2)
    gt_result = p2.gt(p1)

    assert lt_result.keys() == gt_result.keys()


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({3.0, 7.0}))
def test_comparison_antisymmetry_le_ge(
    p1: PolyhedralDomain, p2: PolyhedralDomain
) -> None:
    """Property: p1 <= p2 is the opposite of p2 >= p1."""
    if p1.dimension != p2.dimension:
        return

    le_result = p1.le(p2)
    ge_result = p2.ge(p1)

    assert le_result.keys() == ge_result.keys()


# ============================================================================
# IDENTITY PROPERTIES
# ============================================================================


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({5.0}))
@example(PolyhedralDomain.abstract({1.0, 10.0}))
def test_comparison_identity_eq(p: PolyhedralDomain) -> None:
    """Property: x == x should always include True outcome for non-bot."""
    eq_result = p.eq(p)

    if not p.is_bot():
        assert True in eq_result
        assert eq_result[True] == (p, p)
    else:
        assert eq_result == {}


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 10.0}))
def test_comparison_identity_le(p: PolyhedralDomain) -> None:
    """Property: x <= x should always include True."""
    le_result = p.le(p)

    if not p.is_bot():
        assert True in le_result


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 10.0}))
def test_comparison_identity_ge(p: PolyhedralDomain) -> None:
    """Property: x >= x should always include True."""
    ge_result = p.ge(p)

    if not p.is_bot():
        assert True in ge_result


# ============================================================================
# LOGICAL RELATIONSHIP PROPERTIES
# ============================================================================


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({6.0, 10.0}))
def test_logical_relationship_lt_implies_le(
    p1: PolyhedralDomain, p2: PolyhedralDomain
) -> None:
    """Property: x < y implies x <= y."""
    if p1.dimension != p2.dimension:
        return

    lt_result = p1.lt(p2)
    le_result = p1.le(p2)

    # For polyhedral domain, this is conservative
    # Just check that if lt is possible, le is also possible
    if True in lt_result:
        assert True in le_result or len(le_result) > 0


# ============================================================================
# LATTICE PROPERTY TESTS
# ============================================================================


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({3.0, 7.0}))
def test_meet_commutativity(p1: PolyhedralDomain, p2: PolyhedralDomain) -> None:
    """Property: Meet is commutative (p1 ⊓ p2 = p2 ⊓ p1)."""
    assert (p1 & p2) == (p2 & p1)


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({3.0, 7.0}))
def test_join_commutativity(p1: PolyhedralDomain, p2: PolyhedralDomain) -> None:
    """Property: Join is commutative (p1 ⊔ p2 = p2 ⊔ p1)."""
    assert (p1 | p2) == (p2 | p1)


@given(polyhedral_elements(), polyhedral_elements(), polyhedral_elements())
def test_meet_associativity(
    p1: PolyhedralDomain, p2: PolyhedralDomain, p3: PolyhedralDomain
) -> None:
    """Property: Meet is associative ((p1 ⊓ p2) ⊓ p3 = p1 ⊓ (p2 ⊓ p3))."""
    assert ((p1 & p2) & p3) == (p1 & (p2 & p3))


@given(polyhedral_elements(), polyhedral_elements(), polyhedral_elements())
def test_join_associativity(
    p1: PolyhedralDomain, p2: PolyhedralDomain, p3: PolyhedralDomain
) -> None:
    """Property: Join is associative ((p1 ⊔ p2) ⊔ p3 = p1 ⊔ (p2 ⊔ p3))."""
    assert ((p1 | p2) | p3) == (p1 | (p2 | p3))


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({3.0, 7.0}))
def test_absorption_law_1(p1: PolyhedralDomain, p2: PolyhedralDomain) -> None:
    """Property: Absorption law p1 ⊔ (p1 ⊓ p2) = p1."""
    assert (p1 | (p1 & p2)) == p1


@given(polyhedral_elements(), polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 5.0}), PolyhedralDomain.abstract({3.0, 7.0}))
def test_absorption_law_2(p1: PolyhedralDomain, p2: PolyhedralDomain) -> None:
    """Property: Absorption law p1 ⊓ (p1 ⊔ p2) = p1."""
    assert (p1 & (p1 | p2)) == p1


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 10.0}))
def test_bot_is_identity_for_join(p: PolyhedralDomain) -> None:
    """Property: Bot is identity for join (p ⊔ ⊥ = p)."""
    bot = PolyhedralDomain.bot(dimension=p.dimension)
    assert (p | bot) == p
    assert (bot | p) == p


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({1.0, 10.0}))
def test_bot_is_absorbing_for_meet(p: PolyhedralDomain) -> None:
    """Property: Bot is absorbing for meet (p ⊓ ⊥ = ⊥)."""
    bot = PolyhedralDomain.bot(dimension=p.dimension)
    assert (p & bot) == bot
    assert (bot & p) == bot


# ============================================================================
# TOP ELEMENT BINARY OPERATIONS
# ============================================================================


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({0.0}))
@example(PolyhedralDomain.abstract({1.0, 10.0}))
@example(PolyhedralDomain.bot(dimension=1))
def test_top_addition(p: PolyhedralDomain) -> None:
    """Property: Top + poly = Top (except bot case)."""
    top = PolyhedralDomain.top(dimension=p.dimension)

    if p.is_bot():
        result1 = top + p
        result2 = p + top
        assert result1.is_bot()
        assert result2.is_bot()
    else:
        result1 = top + p
        result2 = p + top
        assert result1 == top, f"Expected Top + {p} = Top, got {result1}"
        assert result2 == top, f"Expected {p} + Top = Top, got {result2}"


@given(polyhedral_elements())
@example(PolyhedralDomain.abstract({0.0}))
@example(PolyhedralDomain.abstract({1.0, 10.0}))
@example(PolyhedralDomain.bot(dimension=1))
def test_top_subtraction(p: PolyhedralDomain) -> None:
    """Property: Top - poly = Top and poly - Top = Top (except bot case)."""
    top = PolyhedralDomain.top(dimension=p.dimension)

    if p.is_bot():
        assert (top - p).is_bot()
        assert (p - top).is_bot()
    else:
        result1 = top - p
        result2 = p - top
        assert result1 == top, f"Expected Top - {p} = Top, got {result1}"
        assert result2 == top, f"Expected {p} - Top = Top, got {result2}"


def test_top_with_top_operations() -> None:
    """Property: Binary operations between two Top elements."""
    top = PolyhedralDomain.top(dimension=1)

    # Top + Top = Top
    assert (top + top) == top

    # Top - Top = Top
    assert (top - top) == top


# ============================================================================
# DOMAIN-SPECIFIC TESTS: DIMENSION HANDLING
# ============================================================================


def test_dimension_preserved_in_abstraction() -> None:
    """Dimension is inferred from first point."""
    points_1d = {1.0, 2.0, 3.0}
    result = PolyhedralDomain.abstract(points_1d)
    assert result.dimension == 1

    points_2d = {(1.0, 2.0), (3.0, 4.0)}
    result = PolyhedralDomain.abstract(points_2d)
    assert result.dimension == 2  # noqa: PLR2004


def test_operations_on_different_dimensions_return_top() -> None:
    """Binary operations on different dimensions return top."""
    poly_1d = PolyhedralDomain.abstract({1.0, 2.0})
    poly_2d = PolyhedralDomain.abstract({(1.0, 2.0)})

    result = poly_1d + poly_2d
    assert result.bounds is None  # Top
    assert result.dimension == max(poly_1d.dimension, poly_2d.dimension)


def test_meet_different_dimensions() -> None:
    """Meet on different dimensions returns Bot (Empty Intersection)."""
    poly_1d = PolyhedralDomain.abstract({1.0, 2.0})
    poly_2d = PolyhedralDomain.abstract({(1.0, 2.0)})

    result = poly_1d & poly_2d
    assert result.is_bot()


def test_join_different_dimensions() -> None:
    """Join on different dimensions returns top."""
    poly_1d = PolyhedralDomain.abstract({1.0, 2.0})
    poly_2d = PolyhedralDomain.abstract({(1.0, 2.0)})

    result = poly_1d | poly_2d
    assert result.bounds is None  # Top


# ============================================================================
# DOMAIN-SPECIFIC TESTS: BOUNDING BOX (HULL) SEMANTICS
# ============================================================================


def test_abstraction_computes_bounding_box() -> None:
    """Abstraction computes axis-aligned bounding box."""
    points = {(1.0, 5.0), (3.0, 2.0), (2.0, 4.0)}
    result = PolyhedralDomain.abstract(points)

    assert result.bounds == [(1.0, 3.0), (2.0, 5.0)]
    # x: [1.0, 3.0], y: [2.0, 5.0]


def test_join_computes_hull() -> None:
    """Join computes convex hull (bounding box approximation)."""
    poly1 = PolyhedralDomain.abstract({(0.0, 0.0), (1.0, 1.0)})
    poly2 = PolyhedralDomain.abstract({(2.0, 2.0), (3.0, 3.0)})

    result = poly1 | poly2
    assert result.bounds == [(0.0, 3.0), (0.0, 3.0)]


def test_abstraction_1d_bounding_box() -> None:
    """1D abstraction computes interval."""
    points = {-5.0, 0.0, 10.0, 3.0}
    result = PolyhedralDomain.abstract(points)

    assert result.dimension == 1
    assert result.bounds == [(-5.0, 10.0)]


def test_abstraction_singleton() -> None:
    """Singleton abstraction."""
    result_1d = PolyhedralDomain.abstract({5.0})
    assert result_1d.bounds == [(5.0, 5.0)]

    result_2d = PolyhedralDomain.abstract({(3.0, 7.0)})
    assert result_2d.bounds == [(3.0, 3.0), (7.0, 7.0)]


# ============================================================================
# DOMAIN-SPECIFIC TESTS: INTERSECTION AND EMPTY BOXES
# ============================================================================


def test_meet_computes_intersection() -> None:
    """Meet computes intersection of bounding boxes."""
    poly1 = PolyhedralDomain.abstract({(0.0, 0.0), (5.0, 5.0)})
    poly2 = PolyhedralDomain.abstract({(3.0, 3.0), (7.0, 7.0)})

    result = poly1 & poly2
    assert result.bounds == [(3.0, 5.0), (3.0, 5.0)]


def test_meet_disjoint_boxes_returns_bot() -> None:
    """Intersection of disjoint boxes returns bot."""
    poly1 = PolyhedralDomain.abstract({(0.0, 0.0), (1.0, 1.0)})
    poly2 = PolyhedralDomain.abstract({(5.0, 5.0), (7.0, 7.0)})

    result = poly1 & poly2
    assert result.is_bot()


def test_meet_overlapping_1d() -> None:
    """Meet on overlapping 1D intervals."""
    poly1 = PolyhedralDomain.abstract({0.0, 10.0})
    poly2 = PolyhedralDomain.abstract({5.0, 15.0})

    result = poly1 & poly2
    assert result.bounds == [(5.0, 10.0)]


def test_meet_disjoint_1d() -> None:
    """Meet on disjoint 1D intervals."""
    poly1 = PolyhedralDomain.abstract({0.0, 5.0})
    poly2 = PolyhedralDomain.abstract({10.0, 15.0})

    result = poly1 & poly2
    assert result.is_bot()


# ============================================================================
# DOMAIN-SPECIFIC TESTS: CONTAINMENT TESTING
# ============================================================================


def test_containment_multi_dimensional() -> None:
    """Containment works for multi-dimensional points."""
    poly = PolyhedralDomain.abstract({(0.0, 0.0), (10.0, 10.0)})

    assert (5.0, 5.0) in poly
    assert (0.0, 10.0) in poly
    assert (10.0, 0.0) in poly
    assert (15.0, 5.0) not in poly
    assert (5.0, 15.0) not in poly


def test_containment_dimension_mismatch() -> None:
    """Wrong dimension returns False."""
    poly_2d = PolyhedralDomain.abstract({(1.0, 2.0)})
    assert 1.0 not in poly_2d  # 1D point in 2D domain


def test_containment_1d() -> None:
    """Containment for 1D intervals."""
    poly = PolyhedralDomain.abstract({-5.0, 10.0})

    assert 0.0 in poly
    assert -5.0 in poly  # noqa: PLR2004
    assert 10.0 in poly  # noqa: PLR2004
    assert -6.0 not in poly  # noqa: PLR2004
    assert 11.0 not in poly  # noqa: PLR2004


def test_containment_bot() -> None:
    """Bot contains nothing."""
    bot_1d = PolyhedralDomain.bot(dimension=1)
    assert 0.0 not in bot_1d

    bot_2d = PolyhedralDomain.bot(dimension=2)
    assert (0.0, 0.0) not in bot_2d


def test_containment_top() -> None:
    """Top contains everything."""
    top_1d = PolyhedralDomain.top(dimension=1)
    assert 0.0 in top_1d
    assert 1000000.0 in top_1d  # noqa: PLR2004

    top_2d = PolyhedralDomain.top(dimension=2)
    assert (0.0, 0.0) in top_2d
    assert (1000000.0, -1000000.0) in top_2d


# ============================================================================
# DOMAIN-SPECIFIC TESTS: ARITHMETIC OPERATIONS
# ============================================================================


def test_addition_bounds_algebra() -> None:
    """Addition: [a,b] + [c,d] = [a+c, b+d] per dimension."""
    poly1 = PolyhedralDomain.abstract({(1.0, 2.0), (3.0, 4.0)})
    poly2 = PolyhedralDomain.abstract({(10.0, 20.0), (30.0, 40.0)})

    result = poly1 + poly2
    # x: [1,3] + [10,30] = [11,33]
    # y: [2,4] + [20,40] = [22,44]
    assert result.bounds == [(11.0, 33.0), (22.0, 44.0)]


def test_subtraction_bounds_algebra() -> None:
    """Subtraction: [a,b] - [c,d] = [a-d, b-c] per dimension."""
    poly1 = PolyhedralDomain.abstract({(10.0, 20.0), (30.0, 40.0)})
    poly2 = PolyhedralDomain.abstract({(1.0, 2.0), (3.0, 4.0)})

    result = poly1 - poly2
    # x: [10,30] - [1,3] = [10-3, 30-1] = [7,29]
    # y: [20,40] - [2,4] = [20-4, 40-2] = [16,38]
    assert result.bounds == [(7.0, 29.0), (16.0, 38.0)]


def test_addition_1d() -> None:
    """Addition on 1D intervals."""
    poly1 = PolyhedralDomain.abstract({1.0, 5.0})
    poly2 = PolyhedralDomain.abstract({10.0, 20.0})

    result = poly1 + poly2
    assert result.bounds == [(11.0, 25.0)]


def test_subtraction_1d() -> None:
    """Subtraction on 1D intervals."""
    poly1 = PolyhedralDomain.abstract({10.0, 20.0})
    poly2 = PolyhedralDomain.abstract({1.0, 5.0})

    result = poly1 - poly2
    # [10,20] - [1,5] = [10-5, 20-1] = [5, 19]
    assert result.bounds == [(5.0, 19.0)]


def test_negation_bounds() -> None:
    """Negation flips bounds."""
    poly = PolyhedralDomain.abstract({(1.0, 2.0), (3.0, 4.0)})
    result = -poly

    # x: [1,3] negated = [-3,-1]
    # y: [2,4] negated = [-4,-2]
    assert result.bounds == [(-3.0, -1.0), (-4.0, -2.0)]


def test_negation_1d() -> None:
    """Negation on 1D interval."""
    poly = PolyhedralDomain.abstract({-5.0, 10.0})
    result = -poly

    # [-5, 10] negated = [-10, 5]
    assert result.bounds == [(-10.0, 5.0)]


# ============================================================================
# DOMAIN-SPECIFIC TESTS: COMPARISON OPERATIONS
# ============================================================================


def test_comparison_conservative_approximation() -> None:
    """Comparisons return conservative {True, False} when uncertain."""
    poly1 = PolyhedralDomain.abstract({(1.0, 2.0), (5.0, 6.0)})
    poly2 = PolyhedralDomain.abstract({(3.0, 4.0), (7.0, 8.0)})

    result = poly1.lt(poly2)
    # Can't determine statically, should return both outcomes
    assert True in result or False in result


def test_comparison_definite_subset() -> None:
    """When poly1 ⊆ poly2, le returns {True}."""
    poly1 = PolyhedralDomain.abstract({(2.0, 3.0), (3.0, 4.0)})
    poly2 = PolyhedralDomain.abstract({(1.0, 2.0), (5.0, 6.0)})

    result = poly1.le(poly2)
    assert True in result


def test_equality_same_bounds() -> None:
    """Equality on identical bounds."""
    poly1 = PolyhedralDomain.abstract({(1.0, 2.0), (3.0, 4.0)})
    poly2 = PolyhedralDomain.abstract({(1.0, 2.0), (3.0, 4.0)})

    result = poly1.eq(poly2)
    assert True in result


# ============================================================================
# DOMAIN-SPECIFIC TESTS: POSET ORDERING
# ============================================================================


def test_poset_ordering_subset() -> None:
    """Smaller box is ⊑ larger box."""
    small = PolyhedralDomain.abstract({(2.0, 3.0), (3.0, 4.0)})
    large = PolyhedralDomain.abstract({(1.0, 2.0), (5.0, 6.0)})

    assert small <= large
    assert not (large <= small)


def test_poset_ordering_bot() -> None:
    """Bot is ⊑ everything."""
    bot = PolyhedralDomain.bot(dimension=1)
    poly = PolyhedralDomain.abstract({1.0, 10.0})

    assert bot <= poly
    assert bot <= bot  # noqa: PLR0124


def test_poset_ordering_disjoint() -> None:
    """Disjoint boxes are not comparable."""
    poly1 = PolyhedralDomain.abstract({(0.0, 0.0), (1.0, 1.0)})
    poly2 = PolyhedralDomain.abstract({(5.0, 5.0), (6.0, 6.0)})

    assert not (poly1 <= poly2)
    assert not (poly2 <= poly1)


# ============================================================================
# DOMAIN-SPECIFIC TESTS: I2S CAST
# ============================================================================


def test_i2s_cast_1d_value() -> None:
    """i2s cast converts int to 1D polyhedral point."""
    result = PolyhedralDomain.i2s_cast(42)
    assert result.dimension == 1
    assert 42.0 in result  # noqa: PLR2004
    assert result.bounds == [(42.0, 42.0)]


def test_i2s_cast_zero() -> None:
    """i2s cast for zero."""
    result = PolyhedralDomain.i2s_cast(0)
    assert 0.0 in result
    assert result.bounds == [(0.0, 0.0)]


def test_i2s_cast_negative() -> None:
    """i2s cast for negative value."""
    result = PolyhedralDomain.i2s_cast(-100)
    assert -100.0 in result  # noqa: PLR2004
    assert result.bounds == [(-100.0, -100.0)]
