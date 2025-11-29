from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from .abstraction import Abstraction


@dataclass
class DoubleDomain(Abstraction[float]):
    """Interval abstraction for floating-point values."""

    lower: float
    upper: float

    def is_bot(self) -> bool:
        """Check if this is the bottom element (empty interval)."""
        return self.lower > self.upper

    # --- New required lattice/utility methods ---

    @classmethod
    def has_finite_lattice(cls) -> bool:
        """Intervals over floats form an infinite-height lattice."""
        return False

    def widen(self, other: Self) -> Self:
        """
        Classic interval widening.

        If the new interval grows beyond current bounds, we jump to ±∞
        in that direction to ensure convergence.
        """
        if self.is_bot():
            return other
        if other.is_bot():
            return self

        lower = self.lower
        upper = self.upper

        if other.lower < self.lower:
            lower = float("-inf")
        if other.upper > self.upper:
            upper = float("inf")

        return self.__class__(lower, upper)

    @classmethod
    def i2s_cast(cls, value: int) -> Self:
        """
        Cast an integer into this abstraction.

        Represent it as a singleton interval [v, v].
        """
        return cls(float(value), float(value))

    # ------------------------------------------------------------------

    @classmethod
    def abstract(cls, items: set[float]) -> Self:
        """Return the tightest interval covering the items."""
        if not items:
            return cls.bot()
        return cls(min(items), max(items))

    @classmethod
    def bot(cls) -> Self:
        return cls(float("inf"), float("-inf"))

    @classmethod
    def top(cls) -> Self:
        return cls(float("-inf"), float("inf"))

    def __contains__(self, member: float) -> bool:
        if self.is_bot():
            return False
        return self.lower <= member <= self.upper

    def _combine(
        self,
        other: Self,
        fn: Callable[[float, float], float],
    ) -> Self:
        if self.is_bot() or other.is_bot():
            return self.bot()
        lows = [fn(self.lower, other.lower), fn(self.lower, other.upper)]
        highs = [fn(self.upper, other.lower), fn(self.upper, other.upper)]
        return self.__class__(min(lows + highs), max(lows + highs))

    def __add__(self, other: Self) -> Self:
        return self._combine(other, lambda a, b: a + b)

    def __sub__(self, other: Self) -> Self:
        return self._combine(other, lambda a, b: a - b)

    def __mul__(self, other: Self) -> Self:
        return self._combine(other, lambda a, b: a * b)

    def __neg__(self) -> Self:
        """Unary minus: -[a, b] = [-b, -a]."""
        if self.is_bot():
            return self.bot()
        return self.__class__(-self.upper, -self.lower)

    def __div__(self, other: Self) -> Self:
        if self.is_bot() or other.is_bot():
            return self.bot()
        if other.lower <= 0 <= other.upper:
            return self.top()
        return self._combine(other, lambda a, b: a / b)

    __truediv__ = __div__

    def __floordiv__(self, other: Self) -> Self:
        return self.__div__(other)

    def __mod__(self, other: Self) -> Self:
        if self.is_bot() or other.is_bot():
            return self.bot()
        return self.top()

    def __le__(self, other: Self) -> bool:
        if self.is_bot():
            return True
        if other.lower == float("-inf") and other.upper == float("inf"):
            return True
        if self.lower == float("-inf") and self.upper == float("inf"):
            return other.lower == float("-inf") and other.upper == float("inf")
        return self.lower >= other.lower and self.upper <= other.upper

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DoubleDomain):
            return False
        if self.is_bot() and other.is_bot():
            return True
        if self.is_bot() or other.is_bot():
            return False
        return self.lower == other.lower and self.upper == other.upper

    def __and__(self, other: Self) -> Self:
        if self.is_bot() or other.is_bot():
            return self.bot()
        lower = max(self.lower, other.lower)
        upper = min(self.upper, other.upper)
        if lower > upper:
            return self.bot()
        return self.__class__(lower, upper)

    def __or__(self, other: Self) -> Self:
        if self.is_bot():
            return other
        if other.is_bot():
            return self
        lower = min(self.lower, other.lower)
        upper = max(self.upper, other.upper)
        return self.__class__(lower, upper)

    def __str__(self) -> str:
        if self.is_bot():
            return "⊥dbl"
        if self.lower == float("-inf") and self.upper == float("inf"):
            return "⊤dbl"  # noqa: RUF001
        return f"[{self.lower}, {self.upper}]"

    # Helpers

    def _unknown(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        return {True: (self, other), False: (self, other)}

    def _truths_to_dict(
        self,
        other: Self,
        truths: set[bool],
    ) -> dict[bool, tuple[Self, Self]]:
        if not truths:
            truths = {True, False}
        if self.is_bot() or other.is_bot():
            return {}
        return dict.fromkeys(truths, (self, other))

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}

        results: dict[bool, tuple[Self, Self]] = {}

        can_be_true = self.lower <= other.upper
        can_be_false = self.upper > other.lower

        if can_be_true:
            self_true = type(self)(self.lower, min(self.upper, other.upper))
            other_true = type(self)(max(other.lower, self.lower), other.upper)
            results[True] = (self_true, other_true)

        if can_be_false:
            self_false = type(self)(max(self.lower, other.lower), self.upper)
            other_false = type(self)(other.lower, min(other.upper, self.upper))
            results[False] = (self_false, other_false)

        return results

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}

        results: dict[bool, tuple[Self, Self]] = {}

        can_be_true = self.lower < other.upper
        can_be_false = self.upper >= other.lower

        if can_be_true:
            self_true = type(self)(self.lower, min(self.upper, other.upper))
            other_true = type(self)(max(other.lower, self.lower), other.upper)
            results[True] = (self_true, other_true)

        if can_be_false:
            self_false = type(self)(max(self.lower, other.lower), self.upper)
            other_false = type(self)(other.lower, min(other.upper, self.upper))
            results[False] = (self_false, other_false)

        return results

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {
            truth: (self_refined, other_refined)
            for truth, (other_refined, self_refined) in other.le(self).items()
        }

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {
            truth: (self_refined, other_refined)
            for truth, (other_refined, self_refined) in other.lt(self).items()
        }

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        result: dict[bool, tuple[Self, Self]] = {}
        overlap_low = max(self.lower, other.lower)
        overlap_high = min(self.upper, other.upper)
        if overlap_low <= overlap_high:
            overlap = self.__class__(overlap_low, overlap_high)
            result[True] = (overlap, overlap)
        only_true = self.lower == self.upper == other.lower == other.upper
        if not only_true:
            result[False] = (self, other)
        return result or self._unknown(other)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        eq_result = self.eq(other)
        truths = set(eq_result.keys())
        if truths == {True}:
            return {False: eq_result[True]}
        if truths == {False}:
            return {True: eq_result[False]}
        return {True: (self, other), False: (self, other)}
