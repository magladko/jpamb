from __future__ import annotations
from dataclasses import dataclass
from typing import Self
from project.abstraction import Abstraction, Comparison


@dataclass
class StringDomain(Abstraction[str]):
    "Finite-set abstraction for string values."

    values: set[str] | None
    MAX_TRACKED = 5

    @classmethod
    def abstract(cls, items: set[str | int]) -> Self:
        "Return an abstraction covering the items."
        if not items:
            return cls.bot()
        normalized = {str(item) for item in items}
        if len(normalized) > cls.MAX_TRACKED:
            return cls.top()
        return cls(normalized)

    @classmethod
    def bot(cls) -> Self:
        return cls(set())

    @classmethod
    def top(cls) -> Self:
        return cls(None)

    def compare(self, op: Comparison, other: Self) -> set[bool]:
        if (
            op in {"eq", "ne"}
            and self.values is not None
            and other.values is not None
            and self.values
            and other.values
        ):
            only_equal = len(self.values) == len(other.values) == 1
            same = next(iter(self.values)) == next(iter(other.values)) if only_equal else None
            if only_equal:
                return {same} if op == "eq" else {not same}
        return {True, False}

    def le(self, other: Self) -> set[bool]:
        return {True, False}

    def eq(self, other: Self) -> set[bool]:
        return self.compare("eq", other)

    def __contains__(self, member: str | int) -> bool:
        if self.values is None:
            return True
        if self.values == set():
            return False
        return str(member) in self.values

    def __add__(self, other: Self) -> Self:
        if self.values == set() or other.values == set():
            return StringDomain.bot()
        if self.values is None or other.values is None:
            return StringDomain.top()
        acc = {str(a) + str(b) for a in self.values for b in other.values}
        if len(acc) > self.MAX_TRACKED:
            return StringDomain.top()
        return StringDomain(acc)

    def __sub__(self, other: Self) -> Self:
        return StringDomain.top()

    __mul__ = __div__ = __floordiv__ = __mod__ = __sub__

    def __le__(self, other: Self) -> bool:
        if self.values == set():
            return True
        if other.values is None:
            return True
        if self.values is None:
            return other.values is None
        if other.values == set():
            return False
        return self.values <= other.values

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StringDomain) and self.values == other.values

    def __and__(self, other: Self) -> Self:
        if self.values == set() or other.values == set():
            return StringDomain.bot()
        if self.values is None:
            return other
        if other.values is None:
            return self
        return StringDomain(self.values & other.values)

    def __or__(self, other: Self) -> Self:
        if self.values is None or other.values is None:
            return StringDomain.top()
        if self.values == set():
            return other
        if other.values == set():
            return self
        merged = self.values | other.values
        if len(merged) > self.MAX_TRACKED:
            return StringDomain.top()
        return StringDomain(merged)

    def __str__(self) -> str:
        if self.values is None:
            return "⊤str"
        if self.values == set():
            return "⊥str"
        return "{" + ",".join(sorted(self.values)) + "}"


@dataclass
class DoubleDomain(Abstraction[float]):
    "Interval abstraction for floating-point values"

    lower: float
    upper: float
    is_bottom: bool = False

    @classmethod
    def abstract(cls, items: set[float]) -> Self:
        "Return the tightest interval covering the items"
        if not items:
            return cls.bot()
        return cls(min(items), max(items))

    @classmethod
    def bot(cls) -> Self:
        return cls(0.0, -0.0, True)

    @classmethod
    def top(cls) -> Self:
        return cls(float("-inf"), float("inf"))

    def compare(self, op: Comparison, other: Self) -> set[bool]:
        if self.is_bottom or other.is_bottom:
            return {True, False}
        match op:
            case "eq":
                if self.lower == self.upper == other.lower == other.upper:
                    return {True}
                if self.upper < other.lower or other.upper < self.lower:
                    return {False}
            case "ne":
                return {not r for r in self.compare("eq", other)}
            case "le":
                if self.upper <= other.lower:
                    return {True}
                if self.lower > other.upper:
                    return {False}
            case "lt":
                if self.upper < other.lower:
                    return {True}
                if self.lower >= other.upper:
                    return {False}
        return {True, False}

    def le(self, other: Self) -> set[bool]:
        return self.compare("le", other)

    def eq(self, other: Self) -> set[bool]:
        return self.compare("eq", other)

    def __contains__(self, member: float) -> bool:
        if self.is_bottom:
            return False
        return self.lower <= member <= self.upper

    def _combine(self, other: Self, fn) -> "DoubleDomain":
        if self.is_bottom or other.is_bottom:
            return DoubleDomain.bot()
        lows = [fn(self.lower, other.lower), fn(self.lower, other.upper)]
        highs = [fn(self.upper, other.lower), fn(self.upper, other.upper)]
        return DoubleDomain(min(lows + highs), max(lows + highs))

    def __add__(self, other: Self) -> Self:
        return self._combine(other, lambda a, b: a + b)

    def __sub__(self, other: Self) -> Self:
        return self._combine(other, lambda a, b: a - b)

    def __mul__(self, other: Self) -> Self:
        return self._combine(other, lambda a, b: a * b)

    def __div__(self, other: Self) -> Self:
        if other.lower <= 0 <= other.upper:
            return DoubleDomain.top()
        return self._combine(other, lambda a, b: a / b)

    def __floordiv__(self, other: Self) -> Self:
        return self.__div__(other)

    def __mod__(self, other: Self) -> Self:
        return DoubleDomain.top()

    def __le__(self, other: Self) -> bool:
        if self.is_bottom:
            return True
        if other.lower == float("-inf") and other.upper == float("inf"):
            return True
        if self.lower == float("-inf") and self.upper == float("inf"):
            return other.lower == float("-inf") and other.upper == float("inf")
        return self.lower >= other.lower and self.upper <= other.upper

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DoubleDomain)
            and self.lower == other.lower
            and self.upper == other.upper
            and self.is_bottom == other.is_bottom
        )

    def __and__(self, other: Self) -> Self:
        if self.is_bottom or other.is_bottom:
            return DoubleDomain.bot()
        lower = max(self.lower, other.lower)
        upper = min(self.upper, other.upper)
        if lower > upper:
            return DoubleDomain.bot()
        return DoubleDomain(lower, upper)

    def __or__(self, other: Self) -> Self:
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        lower = min(self.lower, other.lower)
        upper = max(self.upper, other.upper)
        return DoubleDomain(lower, upper)

    def __str__(self) -> str:
        if self.is_bottom:
            return "⊥dbl"
        if self.lower == float("-inf") and self.upper == float("inf"):
            return "⊤dbl"
        return f"[{self.lower}, {self.upper}]"


__all__ = [
    "StringDomain",
    "DoubleDomain",
]
