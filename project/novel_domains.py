from __future__ import annotations

import operator as op
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from project.abstractions.abstraction import Abstraction

if TYPE_CHECKING:
    from collections.abc import Callable

@dataclass
class StringDomain(Abstraction[str]):
    """Finite-set abstraction for string values."""

    values: set[str] | None
    MAX_TRACKED = 5

    @classmethod
    def abstract(cls, items: set[str | int]) -> Self:
        """Return an abstraction covering the items."""
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

    def __neg__(self) -> Self:
        raise NotImplementedError

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
            return "⊤str" # noqa: RUF001
        if self.values == set():
            return "⊥str"
        return "{" + ",".join(sorted(self.values)) + "}"

    # Helpers

    def _unknown(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {True: (self, other), False: (self, other)}

    def _compare_literals(
            self,
            other: Self,
            comparator: Callable[[str, str], bool],
    ) -> dict[bool, tuple[StringDomain, StringDomain]]:
        if self.values is None or other.values is None:
            return self._unknown(other)
        results: dict[bool, tuple[set[str], set[str]]] = {}
        for lhs in self.values:
            for rhs in other.values:
                truth = comparator(lhs, rhs)
                lhs_set, rhs_set = results.setdefault(truth, (set(), set()))
                lhs_set.add(lhs)
                rhs_set.add(rhs)
        if not results:
            return self._unknown(other)
        translated: dict[bool, tuple[StringDomain, StringDomain]] = {}
        for truth, (lhs_vals, rhs_vals) in results.items():
            translated[truth] = (StringDomain(lhs_vals), StringDomain(rhs_vals))
        return translated

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_literals(other, op.le)

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_literals(other, op.lt)

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {
            truth: (self_refined, other_refined)
            for truth, (other_refined, self_refined) in other.le(self).items()
        }

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_literals(other, op.gt)

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_literals(other, op.eq)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_literals(other, op.ne)


@dataclass
class DoubleDomain(Abstraction[float]):
    """Interval abstraction for floating-point values."""

    lower: float
    upper: float
    is_bottom: bool = False

    @classmethod
    def abstract(cls, items: set[float]) -> Self:
        """Return the tightest interval covering the items."""
        if not items:
            return cls.bot()
        return cls(min(items), max(items))

    @classmethod
    def bot(cls) -> Self:
        return cls(0.0, 0.0, True)

    @classmethod
    def top(cls) -> Self:
        return cls(float("-inf"), float("inf"))

    def __contains__(self, member: float) -> bool:
        if self.is_bottom:
            return False
        return self.lower <= member <= self.upper

    def _combine(
            self,
            other: Self,
            fn: Callable[[float, float], float],
    ) -> DoubleDomain:
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

    def __neg__(self) -> Self:
        raise NotImplementedError

    def __div__(self, other: Self) -> Self:
        if other.lower <= 0 <= other.upper:
            return DoubleDomain.top()
        return self._combine(other, lambda a, b: a / b)

    __truediv__ = __div__

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
            return "⊤dbl"  # noqa: RUF001
        return f"[{self.lower}, {self.upper}]"

    # Helpers

    def _unknown(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {True: (self, other), False: (self, other)}

    def _truths_to_dict(
        self,
        other: Self,
        truths: set[bool],
    ) -> dict[bool, tuple[Self, Self]]:
        if not truths:
            truths = {True, False}
        return dict.fromkeys(truths, (self, other))

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bottom or other.is_bottom:
            return self._unknown(other)
        truths: set[bool] = set()
        if self.upper <= other.lower:
            truths.add(True)
        if self.lower > other.upper:
            truths.add(False)
        return self._truths_to_dict(other, truths)

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bottom or other.is_bottom:
            return self._unknown(other)
        truths: set[bool] = set()
        if self.upper < other.lower:
            truths.add(True)
        if self.lower >= other.upper:
            truths.add(False)
        return self._truths_to_dict(other, truths)

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
        if self.is_bottom or other.is_bottom:
            return self._unknown(other)
        result: dict[bool, tuple[DoubleDomain, DoubleDomain]] = {}
        overlap_low = max(self.lower, other.lower)
        overlap_high = min(self.upper, other.upper)
        if overlap_low <= overlap_high:
            overlap = DoubleDomain(overlap_low, overlap_high)
            result[True] = (overlap, overlap)
        only_true = (
            self.lower == self.upper
            == other.lower
            == other.upper
        )
        if not only_true:
            result[False] = (self, other)
        return result or self._unknown(other)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        eq_result = self.eq(other)
        truths = set(eq_result.keys())
        if truths == {True}:
            return {False: eq_result[True]}
        if truths == {False}:
            return {True: eq_result[False]}
        return {True: (self, other), False: (self, other)}


@dataclass
class MachineWordDomain(Abstraction[int]):
    """Finite-set abstraction for machine word integers."""

    residues: set[int] | None
    is_bottom: bool = False

    WIDTH = 32
    MAX_TRACKED = 16

    @classmethod
    def _mask(cls) -> int:
        return (1 << cls.WIDTH) - 1

    @classmethod
    def _normalize_values(cls, items: set[int]) -> set[int]:
        mask = cls._mask()
        return {item & mask for item in items}

    @classmethod
    def abstract(cls, items: set[int]) -> Self:
        if not items:
            return cls.bot()
        normalized = cls._normalize_values(items)
        if len(normalized) > cls.MAX_TRACKED:
            return cls.top()
        return cls(normalized)

    @classmethod
    def bot(cls) -> Self:
        return cls(set(), True)

    @classmethod
    def top(cls) -> Self:
        return cls(None)

    def __contains__(self, member: int) -> bool:
        if self.is_bottom:
            return False
        if self.residues is None:
            return True
        return (member & self._mask()) in self.residues

    def _binary_op(
            self,
            other: Self,
            fn: Callable[[int, int], int],
    ) -> MachineWordDomain:
        if self.is_bottom or other.is_bottom:
            return MachineWordDomain.bot()
        if self.residues is None or other.residues is None:
            return MachineWordDomain.top()
        mask = self._mask()
        acc = {fn(a, b) & mask for a in self.residues for b in other.residues}
        if len(acc) > self.MAX_TRACKED:
            return MachineWordDomain.top()
        return MachineWordDomain(acc)

    def __add__(self, other: Self) -> Self:
        return self._binary_op(other, lambda a, b: a + b)

    def __sub__(self, other: Self) -> Self:
        return self._binary_op(other, lambda a, b: a - b)

    def __mul__(self, other: Self) -> Self:
        return self._binary_op(other, lambda a, b: a * b)

    def __div__(self, other: Self) -> Self:
        if other.is_bottom:
            return MachineWordDomain.bot()
        if other.residues is None:
            return MachineWordDomain.top()
        if 0 in other.residues:
            return MachineWordDomain.top()
        return self._binary_op(other, lambda a, b: a // b)

    __floordiv__ = __div__
    __mod__ = __div__

    def __le__(self, other: Self) -> bool:
        if self.is_bottom:
            return True
        if other.residues is None:
            return True
        if self.residues is None:
            return other.residues is None
        if other.is_bottom:
            return False
        return self.residues <= other.residues

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, MachineWordDomain)
            and self.residues == other.residues
            and self.is_bottom == other.is_bottom
        )

    def __and__(self, other: Self) -> Self:
        if self.is_bottom or other.is_bottom:
            return MachineWordDomain.bot()
        if self.residues is None:
            return other
        if other.residues is None:
            return self
        return MachineWordDomain(self.residues & other.residues)

    def __or__(self, other: Self) -> Self:
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        if self.residues is None or other.residues is None:
            return MachineWordDomain.top()
        merged = self.residues | other.residues
        if len(merged) > self.MAX_TRACKED:
            return MachineWordDomain.top()
        return MachineWordDomain(merged)

    def __neg__(self) -> Self:
        raise NotImplementedError

    def __str__(self) -> str:
        if self.is_bottom:
            return "⊥word"
        if self.residues is None:
            return "⊤word"  # noqa: RUF001
        return "{" + ",".join(str(v) for v in sorted(self.residues)) + "}"

    # Helpers

    def _unknown(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {True: (self, other), False: (self, other)}

    def _compare_values(
            self,
            other: Self,
            comparator: Callable[[int, int], bool],
    ) -> dict[bool, tuple[MachineWordDomain, MachineWordDomain]]:
        if self.is_bottom or other.is_bottom:
            return self._unknown(other)
        if self.residues is None or other.residues is None:
            return self._unknown(other)
        results: dict[bool, tuple[set[int], set[int]]] = {}
        for lhs in self.residues:
            for rhs in other.residues:
                truth = comparator(lhs, rhs)
                lhs_set, rhs_set = results.setdefault(truth, (set(), set()))
                lhs_set.add(lhs)
                rhs_set.add(rhs)
        if not results:
            return self._unknown(other)
        translated: dict[bool, tuple[MachineWordDomain, MachineWordDomain]] = {}
        for truth, (lhs_vals, rhs_vals) in results.items():
            translated[truth] = (
                MachineWordDomain(lhs_vals),
                MachineWordDomain(rhs_vals),
            )
        return translated

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_values(other, op.le)

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_values(other, op.lt)

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_values(other, op.ge)

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_values(other, op.gt)

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_values(other, op.eq)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._compare_values(other, op.ne)


@dataclass
class PolyhedralDomain(Abstraction[tuple[float, ...]]):

    dimension: int
    bounds: list[tuple[float, float]] | None
    is_bottom: bool = False

    DEFAULT_DIMENSION = 1

    @classmethod
    def _as_point(cls, value: tuple[float, ...] | float) -> tuple[float, ...]:
        if isinstance(value, tuple):
            return tuple(float(v) for v in value)
        if isinstance(value, list):
            return tuple(float(v) for v in value)
        if isinstance(value, (int, float)):
            return (float(value),)
        raise TypeError(f"Unsupported value for PolyhedralDomain: {value!r}")

    @classmethod
    def abstract(cls, items: set[tuple[float, ...] | float | int]) -> Self:
        if not items:
            return cls.bot()
        normalized = [cls._as_point(point) for point in items]
        dimension = len(normalized[0])
        mins = [float("inf")] * dimension
        maxs = [float("-inf")] * dimension
        for point in normalized:
            if len(point) != dimension:
                raise ValueError("points must share the same dimension")
            for idx, value in enumerate(point):
                mins[idx] = min(mins[idx], value)
                maxs[idx] = max(maxs[idx], value)
        bounds = list(zip(mins, maxs, strict=True))
        return cls(dimension, bounds)

    @classmethod
    def bot(cls, dimension: int | None = None) -> Self:
        dim = cls.DEFAULT_DIMENSION if dimension is None else dimension
        return cls(dim, None, True)

    @classmethod
    def top(cls, dimension: int | None = None) -> Self:
        dim = cls.DEFAULT_DIMENSION if dimension is None else dimension
        return cls(dim, None)

    def __contains__(self, member: tuple[float, ...] | float) -> bool:
        if self.is_bottom:
            return False
        if self.bounds is None:
            return True
        point = self._as_point(member)
        if len(point) != self.dimension:
            return False
        return all(lo <= value <= hi for value, (lo, hi)
                   in zip(point, self.bounds, strict=True))

    # Helpers

    def _preferself_dimension(self, other: Self) -> int:
        """Best-effort dimension choice when collapsing to top/bot."""
        if self.bounds is not None or self.is_bottom:
            return self.dimension
        if other.bounds is not None or other.is_bottom:
            return other.dimension
        return max(self.dimension, other.dimension)

    def _apply_pairwise(
            self,
            other: Self,
            fn: Callable[
                [tuple[float, float], tuple[float, float]],
                tuple[float, float]
            ],
    ) -> PolyhedralDomain:
        if self.is_bottom or other.is_bottom:
            dim = self._preferself_dimension(other)
            return PolyhedralDomain.bot(dim)
        if self.bounds is None or other.bounds is None:
            dim = self._preferself_dimension(other)
            return PolyhedralDomain.top(dim)
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return PolyhedralDomain.top(dim)
        merged = [fn(a, b) for a, b in zip(self.bounds, other.bounds,strict=True)]
        return PolyhedralDomain(self.dimension, merged)

    def __add__(self, other: Self) -> Self:
        return self._apply_pairwise(other, lambda a, b: (a[0] + b[0], a[1] + b[1]))

    def __sub__(self, other: Self) -> Self:
        return self._apply_pairwise(other, lambda a, b: (a[0] - b[1], a[1] - b[0]))

    __mul__ = __div__ = __floordiv__ = __mod__ = __sub__

    def __le__(self, other: Self) -> bool:
        if self.is_bottom:
            return True
        if other.bounds is None:
            return True
        if self.bounds is None:
            return other.bounds is None
        if self.dimension != other.dimension:
            return False
        return all(
            other_lo <= lo and hi <= other_hi
            for (lo, hi), (other_lo, other_hi) in zip(self.bounds, other.bounds,
                                                      strict=True)
        )

    def __neg__(self) -> Self:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, PolyhedralDomain)
            and self.dimension == other.dimension
            and self.bounds == other.bounds
            and self.is_bottom == other.is_bottom
        )

    def __and__(self, other: Self) -> Self:
        if self.is_bottom or other.is_bottom:
            dim = self._preferself_dimension(other)
            return PolyhedralDomain.bot(dim)
        if self.bounds is None:
            return other
        if other.bounds is None:
            return self
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return PolyhedralDomain.top(dim)
        intersected = []
        for (lo1, hi1), (lo2, hi2) in zip(self.bounds, other.bounds,strict=True):
            lo = max(lo1, lo2)
            hi = min(hi1, hi2)
            if lo > hi:
                return PolyhedralDomain.bot(self.dimension)
            intersected.append((lo, hi))
        return PolyhedralDomain(self.dimension, intersected)

    def __or__(self, other: Self) -> Self:
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        if self.bounds is None or other.bounds is None:
            dim = self._preferself_dimension(other)
            return PolyhedralDomain.top(dim)
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return PolyhedralDomain.top(dim)
        hull = []
        for (lo1, hi1), (lo2, hi2) in zip(self.bounds, other.bounds, strict=True):
            hull.append((min(lo1, lo2), max(hi1, hi2)))
        return PolyhedralDomain(self.dimension, hull)

    def __str__(self) -> str:
        if self.is_bottom:
            return "⊥poly"
        if self.bounds is None:
            return "⊤poly" # noqa: RUF001
        parts = [f"{lo}≤x{idx}≤{hi}" for idx, (lo, hi) in enumerate(self.bounds)]
        return "{" + ", ".join(parts) + "}"

    # Helpers

    def _unknown(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return {True: (self, other), False: (self, other)}

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self <= other:
            return {True: (self, other)}
        return self._unknown(other)

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return self._unknown(other)

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return other.le(self)

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return other.lt(self)

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self == other and not self.is_bottom:
            return {True: (self, other)}
        return self._unknown(other)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        result = self.eq(other)
        if True in result and len(result) == 1:
            return {False: result[True]}
        return self._unknown(other)


__all__ = [
    "DoubleDomain",
    "MachineWordDomain",
    "PolyhedralDomain",
    "StringDomain",
]



####### __neg__