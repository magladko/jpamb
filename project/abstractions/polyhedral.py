from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from .abstraction import Abstraction


@dataclass
class PolyhedralDomain(Abstraction[tuple[float, ...]]):

    dimension: int
    bounds: list[tuple[float, float]] | None
    is_bottom: bool = False

    DEFAULT_DIMENSION = 1

    @classmethod
    def has_finite_lattice(cls) -> bool:
        return False

    def widen(self, other: Self) -> Self:
        """Very simple widening: useing the join (bounding box / hull)."""
        return self | other

    @classmethod
    def i2s_cast(cls, value: int) -> Self:
        """Cast an int to a 1D polyhedral point interval [v, v]."""
        point = float(value)
        return cls.abstract({point})

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
    ) -> Self:
        if self.is_bottom or other.is_bottom:
            dim = self._preferself_dimension(other)
            return self.bot(dim)
        if self.bounds is None or other.bounds is None:
            dim = self._preferself_dimension(other)
            return self.top(dim)
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return self.top(dim)
        merged = [fn(a, b) for a, b in zip(self.bounds, other.bounds,strict=True)]
        return self.__class__(self.dimension, merged)

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
        if self.is_bottom:
            return self.bot(self.dimension)
        if self.bounds is None:
            return self.top(self.dimension)
        neg_bounds = [(-hi, -lo) for (lo, hi) in self.bounds]
        return self.__class__(self.dimension, neg_bounds, self.is_bottom)

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
            return self.bot(dim)
        if self.bounds is None:
            return other
        if other.bounds is None:
            return self
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return self.top(dim)
        intersected = []
        for (lo1, hi1), (lo2, hi2) in zip(self.bounds, other.bounds,strict=True):
            lo = max(lo1, lo2)
            hi = min(hi1, hi2)
            if lo > hi:
                return self.bot(self.dimension)
            intersected.append((lo, hi))
        return self.__class__(self.dimension, intersected)

    def __or__(self, other: Self) -> Self:
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        if self.bounds is None or other.bounds is None:
            dim = self._preferself_dimension(other)
            return self.top(dim)
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return self.top(dim)
        hull = []
        for (lo1, hi1), (lo2, hi2) in zip(self.bounds, other.bounds, strict=True):
            hull.append((min(lo1, lo2), max(hi1, hi2)))
        return self.__class__(self.dimension, hull)

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
