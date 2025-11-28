import operator as op
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from .abstraction import Abstraction


@dataclass
class MachineWordDomain(Abstraction[int]):

    residues: set[int] | None
    is_bottom: bool = False

    WIDTH = 32
    MAX_TRACKED = 16

    @classmethod
    def has_finite_lattice(cls) -> bool:
        # Machine words are finite (2**WIDTH possibilities)
        return True

    def widen(self, other: Self) -> Self:
        """
        Widening operator.

        Since the lattice is finite and height is bounded,
        simple join is enough to ensure convergence.
        """
        return self | other

    @classmethod
    def i2s_cast(cls, value: int) -> Self:
        return cls.abstract({value})

    # -----------------------------------------

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
    ) -> Self:
        if self.is_bottom or other.is_bottom:
            return self.bot()
        if self.residues is None or other.residues is None:
            return self.top()
        mask = self._mask()
        acc = {fn(a, b) & mask for a in self.residues for b in other.residues}
        if len(acc) > self.MAX_TRACKED:
            return self.top()
        return self.__class__(acc)

    def __add__(self, other: Self) -> Self:
        return self._binary_op(other, lambda a, b: a + b)

    def __sub__(self, other: Self) -> Self:
        return self._binary_op(other, lambda a, b: a - b)

    def __mul__(self, other: Self) -> Self:
        return self._binary_op(other, lambda a, b: a * b)

    def __div__(self, other: Self) -> Self:
        if other.is_bottom:
            return self.bot()
        if other.residues is None:
            return self.top()
        if 0 in other.residues:
            return self.top()
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
            return self.bot()
        if self.residues is None:
            return other
        if other.residues is None:
            return self
        return self.__class__(self.residues & other.residues)

    def __or__(self, other: Self) -> Self:
        if self.is_bottom:
            return other
        if other.is_bottom:
            return self
        if self.residues is None or other.residues is None:
            return self.top()
        merged = self.residues | other.residues
        if len(merged) > self.MAX_TRACKED:
            return self.top()
        return self.__class__(merged)

    def __neg__(self) -> Self:
        if self.is_bottom:
            return self.bot()
        if self.residues is None:
            return self.top()
        mask = self._mask()
        negated = {(-v) & mask for v in self.residues}
        return self.__class__(negated)

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
    ) -> dict[bool, tuple[Self, Self]]:
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
        translated: dict[bool, tuple[Self, Self]] = {}
        for truth, (lhs_vals, rhs_vals) in results.items():
            translated[truth] = (
                self.__class__(lhs_vals),
                self.__class__(rhs_vals),
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
