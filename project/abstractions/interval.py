
from dataclasses import dataclass
from typing import Self

from .abstraction import Abstraction


@dataclass
class Interval(Abstraction[int]):
    lower: int | float
    upper: int | float

    def is_bot(self) -> bool:
        """Check if this is the bottom element (empty interval)."""
        return self.lower > self.upper

    @classmethod
    def abstract(cls, items: set[int]) -> Self:
        """Create interval from a set of concrete integers."""
        if not items:
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
        can_be_false = True  # Can always be false unless singleton intervals that match

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
        can_be_true = True

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

        # Consider all four corner products
        products = [
            self.lower * other.lower,
            self.lower * other.upper,
            self.upper * other.lower,
            self.upper * other.upper
        ]
        return type(self)(min(products), max(products))

    def __div__(self, other: Self) -> Self:
        """Interval division (true division)."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        # Check for division by zero
        if other.lower <= 0 <= other.upper:
            # Interval contains zero - return bot (error state)
            return type(self).bot()

        # Consider all four corner divisions
        divisions = [
            self.lower / other.lower,
            self.lower / other.upper,
            self.upper / other.lower,
            self.upper / other.upper
        ]

        # Convert to integers
        return type(self)(int(min(divisions)), int(max(divisions)))

    def __floordiv__(self, other: Self) -> Self:
        """Interval floor division."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        # Check for division by zero
        if other.lower <= 0 <= other.upper:
            # Interval contains zero - return bot (error state)
            return type(self).bot()

        # Consider all four corner divisions
        divisions = [
            self.lower // other.lower,
            self.lower // other.upper,
            self.upper // other.lower,
            self.upper // other.upper
        ]
        return type(self)(min(divisions), max(divisions))

    def __mod__(self, other: Self) -> Self:
        """Interval modulus operation."""
        if self.is_bot() or other.is_bot():
            return type(self).bot()

        # Check for modulus by zero
        if other.lower <= 0 <= other.upper:
            # Interval contains zero - return bot (error state)
            return type(self).bot()

        # Conservative approximation based on JVM semantics:
        # Result sign matches dividend sign
        # Result magnitude is less than divisor magnitude

        # Find the maximum absolute value in the divisor
        max_divisor = max(abs(other.lower), abs(other.upper))

        # Conservative bounds
        if self.lower >= 0:
            # Positive dividend: result in [0, max_divisor - 1]
            return type(self)(0, max_divisor - 1)
        if self.upper <= 0:
            # Negative dividend: result in [-(max_divisor - 1), 0]
            return type(self)(-(max_divisor - 1), 0)
        # Mixed signs: result in [-(max_divisor - 1), max_divisor - 1]
        return type(self)(-(max_divisor - 1), max_divisor - 1)

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
