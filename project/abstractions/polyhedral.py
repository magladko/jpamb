from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Self

from .abstraction import Abstraction


@dataclass
class PolyhedralDomain(Abstraction[tuple[float, ...]]):
    dimension: int
    bounds: list[tuple[float, float]] | None  # None = top, [] = bot

    DEFAULT_DIMENSION = 1

    # Basic lattice helpers
    def is_bot(self) -> bool:
        """Bottom is represented by an empty bounds list."""
        return self.bounds == []

    @classmethod
    def has_finite_lattice(cls) -> bool:
        return False

    def widen(self, other: Self) -> Self:
        """Very simple widening: use the join (bounding box / hull)."""
        return self | other

    @classmethod
    def i2s_cast(cls, value: int) -> Self:
        """Cast an int to a 1D polyhedral point interval [v, v]."""
        point = float(value)
        return cls.abstract({point})

    # Internal helpers
    @classmethod
    def _as_point(cls, value: tuple[float, ...] | float | int) -> tuple[float, ...]:
        if isinstance(value, tuple):
            return tuple(float(v) for v in value)
        if isinstance(value, list):
            return tuple(float(v) for v in value)
        if isinstance(value, (int, float)):
            return (float(value),)
        raise TypeError(f"Unsupported value for PolyhedralDomain: {value!r}")

    @classmethod
    def abstract(cls, items: Iterable[tuple[float, ...] | float | int]) -> Self:
        items = list(items)
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
        return cls(dim, [])

    @classmethod
    def top(cls, dimension: int | None = None) -> Self:
        """Identity top (for comparisons, join, etc.)."""
        dim = cls.DEFAULT_DIMENSION if dimension is None else dimension
        return cls(dim, None)

    def _is_absorbing_top(self) -> bool:
        """Special top created by meet on mismatched dimensions."""
        return self.bounds is None and self.dimension < 0

    def _is_identity_top(self) -> bool:
        """Normal top, e.g. from top() or join on mismatched dimensions."""
        return self.bounds is None and self.dimension >= 0

    def __contains__(self, member: tuple[float, ...] | float | int) -> bool:
        if self.is_bot():
            return False
        if self.bounds is None:
            return True
        point = self._as_point(member)
        if len(point) != self.dimension:
            return False
        return all(
            lo <= value <= hi
            for value, (lo, hi) in zip(point, self.bounds, strict=True)
        )


    # Binary arithmetic

    def _preferself_dimension(self, other: Self) -> int:
        """Best-effort dimension choice when collapsing to top/bot."""
        if self.bounds not in (None, []):
            return self.dimension
        if other.bounds not in (None, []):
            return other.dimension
        return max(self.dimension, other.dimension)

    def _apply_pairwise(
        self,
        other: Self,
        fn: Callable[[tuple[float, float], tuple[float, float]], tuple[float, float]],
    ) -> Self:
        if self.is_bot() or other.is_bot():
            dim = self._preferself_dimension(other)
            return self.bot(dim)
        if self.bounds is None or other.bounds is None:
            dim = self._preferself_dimension(other)
            return self.top(dim)
        if self.dimension != other.dimension:
            dim = max(self.dimension, other.dimension)
            return self.top(dim)
        merged = [fn(a, b) for a, b in zip(self.bounds, other.bounds, strict=True)]
        return type(self)(self.dimension, merged)

    def __add__(self, other: Self) -> Self:
        return self._apply_pairwise(other, lambda a, b: (a[0] + b[0], a[1] + b[1]))

    def __sub__(self, other: Self) -> Self:
        return self._apply_pairwise(other, lambda a, b: (a[0] - b[1], a[1] - b[0]))

    __mul__ = __div__ = __floordiv__ = __mod__ = __sub__

    def __le__(self, other: Self) -> bool:
        if self.is_bot():
            return True
        if other.bounds is None:
            return True
        if self.bounds is None:
            return other.bounds is None
        if self.dimension != other.dimension:
            return False
        return all(
            other_lo <= lo and hi <= other_hi
            for (lo, hi), (other_lo, other_hi) in zip(
                self.bounds, other.bounds, strict=True
            )
        )

    def __neg__(self) -> Self:
        if self.is_bot():
            return self.bot(self.dimension)
        if self.bounds is None:
            return self.top(self.dimension)
        neg_bounds = [(-hi, -lo) for (lo, hi) in self.bounds]
        return type(self)(self.dimension, neg_bounds)

    # Equality
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PolyhedralDomain):
            return False
        # Both bottom: equal regardless of dimension
        if self.is_bot() and other.is_bot():
            return True

        # Both top (any flavour): equal regardless of dimension
        if self.bounds is None and other.bounds is None:
            return True

        # One bot, one not
        if self.is_bot() != other.is_bot():
            return False

        # One top, one not
        if (self.bounds is None) != (other.bounds is None):
            return False

        # Both proper boxes: require same dimension and bounds
        return self.dimension == other.dimension and self.bounds == other.bounds

    # Meet and Join

    def __and__(self, other: Self) -> Self:
        """Lattice meet (intersection) with cross-dimension handling."""

        dim1, dim2 = self.dimension, other.dimension
        maxdim = max(dim1, dim2)

        # 1. ⊥ is absorbing
        if self.is_bot() and other.is_bot():
            return type(self).bot(dimension=maxdim)
        if self.is_bot():
            return type(self).bot(dimension=maxdim)
        if other.is_bot():
            return type(self).bot(dimension=maxdim)

        # 2. ⊤ handling
        if self.bounds is None and other.bounds is None:
            # top ∧ top = top (with max dimension)
            return type(self).top(dimension=maxdim)
        if self.bounds is None:
            # top ∧ x = x
            return other
        if other.bounds is None:
            # x ∧ top = x
            return self

        # 3. Both are proper boxes (non-top, non-bot)
        if dim1 == dim2:
            # Same dimension: coordinate-wise intersection
            intersected: list[tuple[float, float]] = []
            for (lo1, hi1), (lo2, hi2) in zip(self.bounds, other.bounds, strict=True):
                lo = max(lo1, lo2)
                hi = min(hi1, hi2)
                if lo > hi:
                    return type(self).bot(dimension=dim1)
                intersected.append((lo, hi))
            return type(self)(dim1, intersected)

        # 4. Different dimensions, both proper boxes
        #    Work on the overlapping coordinates, then decide:
        #    - if intersection empty -> ⊥(maxdim)
        #    - if intersection equals the smaller box on those coords -> smaller box
        #    - else -> ⊤(maxdim) (lose precision)
        common_dim = min(dim1, dim2)

        intersection: list[tuple[float, float]] = []
        for i in range(common_dim):
            lo = max(self.bounds[i][0], other.bounds[i][0])
            hi = min(self.bounds[i][1], other.bounds[i][1])
            if lo > hi:
                # Empty intersection in projected space -> bottom
                return type(self).bot(dimension=maxdim)
            intersection.append((lo, hi))

        # Decide which is the "smaller" (lower-dimensional) box
        small = self if dim1 < dim2 else other

        # Check if the intersection exactly matches the smaller box
        same_as_small = all(
            intersection[i] == small.bounds[i] for i in range(common_dim)
        )

        if same_as_small:
            # Return the smaller box (keeps its dimension)
            return type(self)(small.dimension, list(small.bounds))

        # Otherwise, we lose precision and go to top in the larger dimension
        return type(self).top(dimension=maxdim)

    def __or__(self, other: Self) -> Self:
        """Lattice join (hull).

        Bottom is neutral and dimension-agnostic.
        Dimension mismatches between non-bottom elements yield top.
        """
        # Bottom is neutral for join
        if self.is_bot():
            return other

        if other.is_bot():
            return self

        # Neither is bottom - check dimension compatibility
        if self.dimension != other.dimension:
            # Incompatible dimensions -> top (with the higher dimension)
            return PolyhedralDomain.top(dimension=max(self.dimension, other.dimension))

        # Any top is absorbing for join
        if self.bounds is None or other.bounds is None:
            return PolyhedralDomain.top(dimension=self.dimension)

        # Same-dimension boxes: coordinate-wise hull
        hull: list[tuple[float, float]] = []
        for (lo1, hi1), (lo2, hi2) in zip(self.bounds, other.bounds, strict=True):
            hull.append((min(lo1, lo2), max(hi1, hi2)))
        return PolyhedralDomain(self.dimension, hull)

    def __str__(self) -> str:
        if self.is_bot():
            return "⊥poly"
        if self.bounds is None:
            return "⊤poly"  # absorbing or identity top look the same externally
        parts = [f"{lo}≤x{idx}≤{hi}" for idx, (lo, hi) in enumerate(self.bounds)]
        return "{" + ", ".join(parts) + "}"

    # Comparison helpers
    def _unknown(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        return {True: (self, other), False: (self, other)}

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        if self <= other:
            return {True: (self, other)}
        return self._unknown(other)

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        # Very conservative: we generally don't know
        return self._unknown(other)

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return other.le(self)

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        return other.lt(self)

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        if self.is_bot() or other.is_bot():
            return {}
        if self == other:
            return {True: (self, other)}
        return self._unknown(other)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        result = self.eq(other)
        if True in result and len(result) == 1:
            return {False: result[True]}
        return self._unknown(other)
