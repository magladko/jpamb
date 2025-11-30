"""Configuration for debloating workflow."""

from jpamb import jvm


def generate_k_set(interesting_values: set[jvm.Value]) -> set[int | float]:
    """
    Generate K-set thresholds from syntactic interesting values.

    The K-set contains threshold values used for widening in abstract interpretation.
    We include default thresholds plus values derived from the code.

    Args:
        interesting_values: Set of values found in the source code

    Returns:
        Set of threshold values for widening

    """
    # Default thresholds
    k_set: set[int | float] = {-100, -10, -1, 0, 1, 10, 100}

    # Add interesting values from code
    for val in interesting_values:
        if isinstance(val.value, (int, float)):
            # Add the value itself and neighbors for more precision
            k_set.add(val.value)
            k_set.add(val.value - 1)
            k_set.add(val.value + 1)

    return k_set


# TODO (kornel): Abstraction selection
# def select_abstraction(code_insights: dict) -> type[Abstraction]:
#     """Choose abstraction based on code complexity."""
#     if code_insights['is_trivial']:
#         return SignSet  # Simpler, faster
#     else:
#         return Interval  # More precise for complex cases
