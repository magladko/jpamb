import operator as op
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from .abstraction import Abstraction


@dataclass
class StringDomain(Abstraction[str]):
    """Finite-set abstraction for string values."""

    values: set[str] | None
    MAX_TRACKED = 5

    @classmethod
    def has_finite_lattice(cls) -> bool:
        return True

    def widen(self, other: Self) -> Self:
        return self | other

    @classmethod
    def i2s_cast(cls, value: int) -> Self:
        return cls.abstract({value})

    @classmethod
    def abstract(cls, items: set[str] | set[int] | set[str | int]) -> Self:
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
            return self.bot()
        if self.values is None or other.values is None:
            return self.top()
        acc = {str(a) + str(b) for a in self.values for b in other.values}
        if len(acc) > self.MAX_TRACKED:
            return self.top()
        return self.__class__(acc)

    def __sub__(self, other: Self) -> Self:
        return self.top()

    def __neg__(self) -> Self:
        return self

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
            return self.bot()
        if self.values is None:
            return other
        if other.values is None:
            return self
        return self.__class__(self.values & other.values)

    def __or__(self, other: Self) -> Self:
        if self.values is None or other.values is None:
            return self.top()
        if self.values == set():
            return other
        if other.values == set():
            return self
        merged = self.values | other.values
        if len(merged) > self.MAX_TRACKED:
            return self.top()
        return self.__class__(merged)

    def __str__(self) -> str:
        if self.values is None:
            return "⊤str"  # noqa: RUF001
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
    ) -> dict[bool, tuple[Self, Self]]:
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
        translated: dict[bool, tuple[Self, Self]] = {}
        for truth, (lhs_vals, rhs_vals) in results.items():
            translated[truth] = (self.__class__(lhs_vals), self.__class__(rhs_vals))
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
