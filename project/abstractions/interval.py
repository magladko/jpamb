from dataclasses import dataclass
from numbers import Number
from typing import Self

from .abstraction import Abstraction, JvmNumberAbs


@dataclass
class Interval(Abstraction[JvmNumberAbs]):
    lower: int | float
    upper: int | float

    def is_bot(self) -> bool:
        """Check if this is the bottom element (empty interval)."""
        return self.lower > self.upper

    @classmethod
    def abstract(cls, items: set[int] | set[float] | set[int | float]) -> Self:
        """Create interval from a set of concrete integers."""
        if not items or any(i is None for i in items):
            return cls.bot()
        return cls(min(items), max(items))

    @classmethod
    def bot(cls) -> Self:
        """Return the bottom element (empty interval)."""
        return cls(float("inf"), float("-inf"))

    @classmethod
    def top(cls) -> Self:
        """Return the top element (all integers)."""
        return cls(float("-inf"), float("inf"))

    @classmethod
    def has_finite_lattice(cls) -> bool:
        return False

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        """Less than or equal comparison with refinement."""
        # self <= other
        # If self.upper <= other.lower, always True
        # If self.lower > other.upper, always False
        # Otherwise, both outcomes possible

        if self.is_bot() or other.is_bot():
            return {}

        results: dict[bool, tuple[Self, Self]] = {}

        # Determine possible outcomes
        can_be_true = self.lower <= other.upper
        can_be_false = self.upper > other.lower

        if can_be_true:
            # When True: self <= other
            # Refine: self.upper <= other.upper and other.lower <= self.upper
            self_true = type(self)(self.lower, min(self.upper, other.upper))
            other_true = type(self)(max(other.lower, self.lower), other.upper)
            results[True] = (self_true, other_true)

        if can_be_false:
            # When False: self > other
            # Refine: self.lower > other.lower and other.upper < self.upper
            self_false = type(self)(max(self.lower, other.lower + 1), self.upper)
            other_false = type(self)(other.lower, min(other.upper, self.upper - 1))
            results[False] = (self_false, other_false)

        return results

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        """Less than comparison with refinement."""
        # self < other
        if self.is_bot() or other.is_bot():
            return {}

        results: dict[bool, tuple[Self, Self]] = {}

        # Determine possible outcomes
        can_be_true = self.lower < other.upper
        can_be_false = self.upper >= other.lower

        if can_be_true:
            # When True: self < other
            # Refine: self.upper < other.upper and other.lower > self.lower
            self_true = type(self)(self.lower, min(self.upper, other.upper - 1))
            other_true = type(self)(max(other.lower, self.lower + 1), other.upper)
            results[True] = (self_true, other_true)

        if can_be_false:
            # When False: self >= other
            # Refine: self.lower >= other.lower and other.upper <= self.upper
            self_false = type(self)(max(self.lower, other.lower), self.upper)
            other_false = type(self)(other.lower, min(other.upper, self.upper))
            results[False] = (self_false, other_false)

        return results

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        """Equality comparison with refinement."""
        if self.is_bot() or other.is_bot():
            return {}

        results: dict[bool, tuple[Self, Self]] = {}

        # Check if intervals overlap
        overlap_lower = max(self.lower, other.lower)
        overlap_upper = min(self.upper, other.upper)

        can_be_true = overlap_lower <= overlap_upper
        can_be_false = self != other

        if can_be_true:
            # When True: both must be in the intersection
            intersection = type(self)(overlap_lower, overlap_upper)
            results[True] = (intersection, intersection)

        if can_be_false:
            # When False: keep original intervals (no refinement possible in general)
            results[False] = (self, other)

        return results

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        """Not equal comparison with refinement."""
        if self.is_bot() or other.is_bot():
            return {}

        results: dict[bool, tuple[Self, Self]] = {}

        # Check if intervals overlap
        overlap_lower = max(self.lower, other.lower)
        overlap_upper = min(self.upper, other.upper)

        # Can be false (equal) if intervals overlap
        can_be_false = overlap_lower <= overlap_upper
        # Can always be true unless both are singletons with same value
        can_be_true = self != other

        if can_be_true:
            # When True: keep original intervals (no refinement in general)
            results[True] = (self, other)

        if can_be_false:
            # When False: both must be in the intersection
            intersection = type(self)(overlap_lower, overlap_upper)
            results[False] = (intersection, intersection)

        return results

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        """Greater than or equal comparison with refinement."""
        # self >= other is equivalent to other <= self
        result = other.le(self)
        # Swap the tuple order
        return {k: (v[1], v[0]) for k, v in result.items()}

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        """Greater than comparison with refinement."""
        # self > other is equivalent to other < self
        result = other.lt(self)
        # Swap the tuple order
        return {k: (v[1], v[0]) for k, v in result.items()}

    def __contains__(self, member: int) -> bool:
        """Check if integer is in the interval."""
        if self.is_bot():
            return False
        return self.lower <= member <= self.upper

    def __add__(self, other: Self) -> Self:
        """Interval addition: [a,b] + [c,d] = [a+c, b+d]."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()
        return type(self)(self.lower + other.lower, self.upper + other.upper)

    def __sub__(self, other: Self) -> Self:
        """Interval subtraction: [a,b] - [c,d] = [a-d, b-c]."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()
        return type(self)(self.lower - other.upper, self.upper - other.lower)

    def __mul__(self, other: Self) -> Self:
        """Interval multiplication."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        if self == 0 or other == 0:
            return type(self)(0, 0)

        # Consider all four corner products
        products = [
            self.lower * other.lower,
            self.lower * other.upper,
            self.upper * other.lower,
            self.upper * other.upper,
        ]
        return type(self)(min(products), max(products))

    def __div__(self, other: Self) -> Abstraction.DivisionResult:
        """Interval division (true division)."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        # Check for division by zero
        has_zero = other.lower <= 0 <= other.upper
        if other == 0:
            return "divide by zero"

        if any(float("inf") in map(abs, (x.lower, x.upper)) for x in [self, other]):
            top = type(self).top()
            return top if not has_zero else (top, "divide by zero")

        # Consider all four corner divisions
        divisions = [
            self.lower / other.lower,
            self.lower / other.upper,
            self.upper / other.lower,
            self.upper / other.upper,
        ]
        # Convert to integers
        result = type(self)(int(min(divisions)), int(max(divisions)))
        return result if not has_zero else (result, "divide by zero")

    def __floordiv__(self, other: Self) -> Abstraction.DivisionResult:
        """Interval floor division."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        # Check for division by zero
        has_zero = other.lower <= 0 <= other.upper
        if other == 0:
            return "divide by zero"

        if any(float("inf") in map(abs, (x.lower, x.upper)) for x in [self, other]):
            top = type(self).top()
            return top if not has_zero else (top, "divide by zero")

        # Consider all four corner divisions
        divisions = [
            self.lower // other.lower,
            self.lower // other.upper,
            self.upper // other.lower,
            self.upper // other.upper,
        ]

        result = type(self)(min(divisions), max(divisions))
        return result if not has_zero else (result, "divide by zero")

    def __mod__(self, other: Self) -> Abstraction.DivisionResult:
        """
        Interval modulus operation (JVM behavior).

        Semantics:
        - Result has the sign of the dividend (self).
        - |Result| < |divisor|.
        - Division by zero logic matches __div__.
        """
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        # 1. Check for division by zero
        # If other spans 0 (e.g., [-1, 1]), 0 is a possible divisor.
        has_zero = other.lower <= 0 <= other.upper

        # If the interval is exactly [0, 0], it's purely an error
        if other == 0:
            return "divide by zero"

        # 2. Determine Divisor Magnitude Constraints
        # The remainder is bounded by the largest absolute value in the divisor - 1.
        # We calculate max(|other|)
        max_div_abs = max(abs(other.lower), abs(other.upper))

        # limit is the maximum possible magnitude of the result (exclusive of divisor)
        # effectively: result <= limit.
        # Note: inf - 1 is still inf, which correctly models uncertainty.
        limit = max_div_abs - 1

        # We also need the minimum absolute value of the divisor (excluding 0)
        # to detect "no-op" cases (e.g. 2 % [10, 20] == 2).
        if other.lower > 0:
            min_div_abs = other.lower
        elif other.upper < 0:
            min_div_abs = abs(other.upper)
        else:
            # If divisor spans 0, we can't guarantee a "no-op" because
            # dividend could be larger than the small numbers near 0 in divisor.
            min_div_abs = 0

        results = []

        # 3. Handle Positive Part of Dividend (Result must be >= 0)
        if self.upper >= 0:
            # Restrict dividend to non-negative part
            pos_lower = max(0, self.lower)
            pos_upper = self.upper

            if pos_lower > pos_upper:
                pass  # self was strictly negative, handled below
            else:
                # Calculate bounds
                # Lower bound is always 0 for modulo
                new_lower = 0

                # Upper bound:
                # If dividend < min_divisor, the operation is identity: returns dividend
                # Otherwise, it is bounded by min(dividend_max, limit).
                if pos_upper < min_div_abs:
                    new_upper = pos_upper
                    new_lower = pos_lower  # Keep original lower if it's identity
                else:
                    new_upper = min(pos_upper, limit)

                results.append(type(self)(new_lower, new_upper))

        # 4. Handle Negative Part of Dividend (Result must be <= 0)
        if self.lower <= 0:
            # Restrict dividend to non-positive part
            neg_lower = self.lower
            neg_upper = min(0, self.upper)

            if neg_lower > neg_upper:
                pass  # self was strictly positive, handled above
            else:
                # Calculate bounds
                # Upper bound is always 0
                new_upper = 0

                # Lower bound:
                # If |dividend| < min_divisor, operation is identity.
                # Otherwise, it is bounded by max(dividend_min, -limit).
                if abs(neg_lower) < min_div_abs:
                    new_lower = neg_lower
                    new_upper = neg_upper  # Keep original upper if it's identity
                else:
                    new_lower = max(neg_lower, -limit)

                results.append(type(self)(new_lower, new_upper))

        # 5. Combine Results
        if not results:
            result = type(self).bot()
        elif len(results) == 1:
            result = results[0]
        else:
            # Join the positive and negative results
            result = results[0] | results[1]

        # 6. Return with Error State if necessary
        # Handle the infinite case explicitly if needed, but float('inf') logic
        # in min/max usually handles this correctly.
        if any(float("inf") in map(abs, (x.lower, x.upper)) for x in [self, other]):
            # If inputs are infinite, we double check bounds.
            # But the logic above (min/max) propagates inf correctly for bounds.
            pass

        return result if not has_zero else (result, "divide by zero")

    def __neg__(self) -> Self:
        # TODO(kornel): Negation overflow for smallest numbers
        tmp = self.lower
        self.lower = -self.upper
        self.upper = -tmp
        return self

    def __le__(self, other: Self) -> bool:
        """Return result of poset ordering (self ⊑ other)."""
        # [i,j] ⊑ [k,h] ≡ k ≤ i ∧ j ≤ h
        # This means self is contained in other
        if self.is_bot():
            return True  # Bot is less than or equal to everything
        if other.is_bot():
            return False  # Nothing (except bot) is less than or equal to bot
        return other.lower <= self.lower and self.upper <= other.upper

    def __eq__(self, other: object) -> bool:
        """Structural equality of intervals."""
        if not isinstance(other, Interval):
            if isinstance(other, Number):
                return self.lower == other and self.upper == other
            return False
        # Handle bot specially
        if self.is_bot() and other.is_bot():
            return True
        if self.is_bot() or other.is_bot():
            return False
        return self.lower == other.lower and self.upper == other.upper

    def __and__(self, other: Self) -> Self:
        """Return result of meet operator (self ⊓ other)."""
        # [i,j] ⊓ [k,h] ≡ [max{i,k}, min{j,h}]
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        new_lower = max(self.lower, other.lower)
        new_upper = min(self.upper, other.upper)

        # If result is invalid (empty interval), return bot
        return type(self)(new_lower, new_upper)

    def __or__(self, other: Self) -> Self:
        """Return result of join operator (self ⊔ other)."""
        # [i,j] ⊔ [k,h] ≡ [min{i,k}, max{j,h}]
        if self.is_bot():
            return other
        if other.is_bot():
            return self

        new_lower = min(self.lower, other.lower)
        new_upper = max(self.upper, other.upper)
        return type(self)(new_lower, new_upper)

    def widen(self, other: "Interval", k_set: set[int | float]) -> "Interval":
        # Standard join first to find the bounds
        joined = self | other

        new_min = joined.lower
        new_max = joined.upper

        # If the lower bound is UNSTABLE (it changed/dropped), widen to next K threshold
        if other.lower < self.lower:
            # Find largest k in K such that k <= new_min. If none, -infinity.
            k_candidates = [k for k in k_set if k <= new_min]
            new_min = max(k_candidates) if k_candidates else -float("inf")

        # If the upper bound is UNSTABLE (it grew), widen to next K threshold
        if other.upper > self.upper:
            # Find smallest k in K such that k >= new_max. If none, infinity.
            k_candidates = [k for k in k_set if k >= new_max]
            new_max = min(k_candidates) if k_candidates else float("inf")

        return Interval(new_min, new_max)

    def i2s_cast(self) -> Self:
        """
        Model int-to-short cast for Interval (precise wrapping).

        The i2s instruction truncates to 16 bits and sign-extends:
        - Range: -32768 to 32767
        - Values outside this range wrap around (modulo 2^16)

        Algorithm:
        1. If interval entirely within [-32768, 32767] → no change
        2. If interval spans ≥65536 → return full short range
        3. Otherwise, compute wrapped bounds with modulo arithmetic
        4. Handle wraparound discontinuity (return full range)
        """
        short_min, short_max, modulo = -32768, 32767, 65536

        if self.is_bot():
            return self

        # Handle infinite bounds
        if self.lower == float("-inf") or self.upper == float("inf"):
            return type(self)(short_min, short_max)

        lower, upper = int(self.lower), int(self.upper)

        # Case 1: Fully in range
        if short_min <= lower <= upper <= short_max:
            return self

        # Case 2: Spans multiple cycles
        if upper - lower >= modulo:
            return type(self)(short_min, short_max)

        # Case 3: Compute wrapped bounds
        def to_short(v: int) -> int:
            """Convert int to short with wrapping."""
            normalized = v % modulo
            return normalized - modulo if normalized > short_max else normalized

        wrapped_lower = to_short(lower)
        wrapped_upper = to_short(upper)

        # If wraparound boundary crossed, return full range
        if wrapped_lower <= wrapped_upper:
            return type(self)(wrapped_lower, wrapped_upper)
        return type(self)(short_min, short_max)

    def __str__(self) -> str:
        """Return string representation of the interval."""
        if self.is_bot():
            return "⊥"
        if self.lower == float("-inf") and self.upper == float("inf"):
            return "⊤"  # noqa: RUF001

        # Format bounds nicely
        if self.lower not in [float("-inf"), float("inf")]:
            lower_str = str(int(self.lower))
        else:
            lower_str = "-∞" if self.lower == float("-inf") else "∞"

        if self.upper not in [float("-inf"), float("inf")]:
            upper_str = str(int(self.upper))
        else:
            upper_str = "-∞" if self.upper == float("-inf") else "∞"

        return f"[{lower_str}, {upper_str}]"
