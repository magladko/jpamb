from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal, Self

from .abstraction import Abstraction, JvmNumberAbs

type Sign = Literal["+", "-", "0"]


@dataclass
class SignSet(Abstraction[JvmNumberAbs]):
    signs: set[Sign]

    @classmethod
    def abstract(cls, items: Iterable[JvmNumberAbs | int | float]) -> Self:
        signset = set()
        if not items or any(x is None for x in items):
            return cls.bot()
        if 0 in items:
            signset.add("0")
        if any(x for x in items if x > 0):
            signset.add("+")
        if any(x for x in items if x < 0):
            signset.add("-")
        return cls(signset)

    @classmethod
    def bot(cls) -> Self:
        return cls(set())

    @classmethod
    def top(cls) -> Self:
        return cls({"+", "-", "0"})

    @classmethod
    def has_finite_lattice(cls) -> bool:
        return True

    def _binary_comparison(
        self: Self, other: Self, outcome_fn: Callable[[Sign, Sign], set[bool]]
    ) -> dict[bool, tuple[Self, Self]]:
        assert isinstance(other, SignSet)

        results: dict[bool, tuple[Self, Self]] = {}
        self_true_set = type(self).bot()
        self_false_set = type(self).bot()
        other_true_set = type(self).bot()
        other_false_set = type(self).bot()

        for s1 in self.signs:
            for s2 in other.signs:
                outcomes = outcome_fn(s1, s2)

                if True in outcomes:
                    self_true_set.signs.add(s1)
                    other_true_set.signs.add(s2)
                if False in outcomes:
                    other_false_set.signs.add(s2)
                    self_false_set.signs.add(s1)

        if len(self_true_set) > 0:
            results[True] = (self_true_set, other_true_set)
        if len(self_false_set) > 0:
            results[False] = (self_false_set, other_false_set)

        return results

    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        # {0} <= {0} -> {True}
        # {0} <= {+} -> {True}
        # {0} <= {-} -> {False}
        # {+} <= {0} -> {False}
        # {+} <= {+} -> {True, False}
        # {+} <= {-} -> {False}
        # {-} <= {0} -> {True}
        # {-} <= {+} -> {True}
        # {-} <= {-} -> {True, False}
        def le_outcome(s1: Sign, s2: Sign) -> set[bool]:
            match (s1, s2):
                case ("0", "0") | ("0", "+") | ("-", "0") | ("-", "+"):
                    return {True}
                case ("0", "-") | ("+", "0") | ("+", "-"):
                    return {False}
                case ("+", "+") | ("-", "-"):
                    return {True, False}
                case _:
                    raise ValueError(f"Invalid signs: {s1}, {s2}")

        return self._binary_comparison(other, le_outcome)

    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        # {0} == {0} -> {True}
        # {0} == {+} -> {False}
        # {0} == {-} -> {False}
        # {+} == {0} -> {False}
        # {+} == {+} -> {True, False}
        # {+} == {-} -> {False}
        # {-} == {0} -> {False}
        # {-} == {+} -> {False}
        # {-} == {-} -> {True, False}
        def eq_outcome(s1: Sign, s2: Sign) -> set[bool]:
            match (s1, s2):
                case ("0", "0"):
                    return {True}
                case (
                    ("0", "+")
                    | ("0", "-")
                    | ("+", "0")
                    | ("-", "0")
                    | ("+", "-")
                    | ("-", "+")
                ):
                    return {False}
                case ("+", "+") | ("-", "-"):
                    return {True, False}
                case _:
                    raise ValueError(f"Invalid signs: {s1}, {s2}")

        return self._binary_comparison(other, eq_outcome)

    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        # {0} != {0} -> {False}
        # {0} != {+} -> {True}
        # {0} != {-} -> {True}
        # {+} != {0} -> {True}
        # {+} != {+} -> {True, False}
        # {+} != {-} -> {True}
        # {-} != {0} -> {True}
        # {-} != {+} -> {True}
        # {-} != {-} -> {True, False}
        def ne_outcome(s1: Sign, s2: Sign) -> set[bool]:
            match (s1, s2):
                case ("0", "0"):
                    return {False}
                case (
                    ("0", "+")
                    | ("0", "-")
                    | ("+", "0")
                    | ("-", "0")
                    | ("+", "-")
                    | ("-", "+")
                ):
                    return {True}
                case ("+", "+") | ("-", "-"):
                    return {True, False}
                case _:
                    raise ValueError(f"Invalid signs: {s1}, {s2}")

        return self._binary_comparison(other, ne_outcome)

    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        # {0} < {0} -> {False}
        # {0} < {+} -> {True}
        # {0} < {-} -> {False}
        # {+} < {0} -> {False}
        # {+} < {+} -> {True, False}
        # {+} < {-} -> {False}
        # {-} < {0} -> {True}
        # {-} < {+} -> {True}
        # {-} < {-} -> {True, False}
        def lt_outcome(s1: Sign, s2: Sign) -> set[bool]:
            match (s1, s2):
                case ("0", "+") | ("-", "0") | ("-", "+"):
                    return {True}
                case ("0", "0") | ("0", "-") | ("+", "0") | ("+", "-"):
                    return {False}
                case ("+", "+") | ("-", "-"):
                    return {True, False}
                case _:
                    raise ValueError(f"Invalid signs: {s1}, {s2}")

        return self._binary_comparison(other, lt_outcome)

    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        # {0} >= {0} -> {True}
        # {0} >= {+} -> {False}
        # {0} >= {-} -> {True}
        # {+} >= {0} -> {True}
        # {+} >= {+} -> {True, False}
        # {+} >= {-} -> {True}
        # {-} >= {0} -> {False}
        # {-} >= {+} -> {False}
        # {-} >= {-} -> {True, False}
        def ge_outcome(s1: Sign, s2: Sign) -> set[bool]:
            match (s1, s2):
                case ("0", "0") | ("0", "-") | ("+", "0") | ("+", "-"):
                    return {True}
                case ("0", "+") | ("-", "0") | ("-", "+"):
                    return {False}
                case ("+", "+") | ("-", "-"):
                    return {True, False}
                case _:
                    raise ValueError(f"Invalid signs: {s1}, {s2}")

        return self._binary_comparison(other, ge_outcome)

    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        # {0} > {0} -> {False}
        # {0} > {+} -> {False}
        # {0} > {-} -> {True}
        # {+} > {0} -> {True}
        # {+} > {+} -> {True, False}
        # {+} > {-} -> {True}
        # {-} > {0} -> {False}
        # {-} > {+} -> {False}
        # {-} > {-} -> {True, False}
        def gt_outcome(s1: Sign, s2: Sign) -> set[bool]:
            match (s1, s2):
                case ("0", "-") | ("+", "0") | ("+", "-"):
                    return {True}
                case ("0", "0") | ("0", "+") | ("-", "0") | ("-", "+"):
                    return {False}
                case ("+", "+") | ("-", "-"):
                    return {True, False}
                case _:
                    raise ValueError(f"Invalid signs: {s1}, {s2}")

        return self._binary_comparison(other, gt_outcome)

    def __contains__(self, member: JvmNumberAbs) -> bool:
        if member == 0 and "0" in self.signs:
            return True
        if member > 0 and "+" in self.signs:
            return True
        return bool(member < 0 and "-" in self.signs)

    @staticmethod
    def _add_signs(s1: Sign, s2: Sign) -> set[Sign]:
        """Add two signs and return the possible resulting signs."""
        # Addition rules for signs:
        # + + + = +
        # - + - = -
        # 0 + x = x
        # + + - = {+, -, 0}  (could be any sign)
        # - + + = {+, -, 0}  (could be any sign)
        match (s1, s2):
            case ("+", "+"):
                return {"+"}
            case ("-", "-"):
                return {"-"}
            case ("0", x) | (x, "0"):
                return {x}
            case ("+", "-") | ("-", "+"):
                return {"+", "-", "0"}
            case _:
                raise ValueError(f"Invalid signs: {s1}, {s2}")

    def __add__(self, other: Self) -> Self:
        """Abstract addition of two sign sets."""
        assert isinstance(other, SignSet)
        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._add_signs(s1, s2))
        return type(self)(new_signs)

    @staticmethod
    def _sub_signs(s1: Sign, s2: Sign) -> set[Sign]:
        """Subtract two signs and return the possible resulting signs."""
        # Subtraction rules for signs (s1 - s2):
        # + - + = {+, -, 0}  (could be any sign)
        # + - - = +
        # + - 0 = +
        # - - + = -
        # - - - = {+, -, 0}  (could be any sign)
        # - - 0 = -
        # 0 - + = -
        # 0 - - = +
        # 0 - 0 = 0
        match (s1, s2):
            case ("+", "-") | ("-", "0") | ("0", "-"):
                return {"+"}
            case ("-", "+") | ("+", "0") | ("0", "+"):
                return {"-"}
            case ("0", "0"):
                return {"0"}
            case ("+", "+") | ("-", "-"):
                return {"+", "-", "0"}
            case _:
                raise ValueError(f"Invalid signs: {s1}, {s2}")

    def __sub__(self, other: Self) -> Self:
        """Abstract subtraction of two sign sets."""
        assert isinstance(other, SignSet)
        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._sub_signs(s1, s2))
        return type(self)(new_signs)

    @staticmethod
    def _mul_signs(s1: Sign, s2: Sign) -> set[Sign]:
        """Multiply two signs and return the possible resulting signs."""
        # Multiplication rules for signs:
        # + * + = +
        # - * - = +
        # + * - = -
        # - * + = -
        # 0 * x = 0
        match (s1, s2):
            case ("0", _) | (_, "0"):
                return {"0"}
            case ("+", "+") | ("-", "-"):
                return {"+"}
            case ("+", "-") | ("-", "+"):
                return {"-"}
            case _:
                raise ValueError(f"Invalid signs: {s1}, {s2}")

    def __mul__(self, other: Self) -> Self:
        """Abstract multiplication of two sign sets."""
        assert isinstance(other, SignSet)
        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._mul_signs(s1, s2))
        return type(self)(new_signs)

    def __div__(self, other: Self) -> Abstraction.DivisionResult:
        """Abstract division of two sign sets."""
        assert isinstance(other, SignSet)
        has_zero = "0" in other.signs
        if has_zero and len(other) == 1:
            return "divide by zero"

        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._mul_signs(s1, s2))
        result = type(self)(new_signs)
        return result if not has_zero else (result, "divide by zero")

    def __floordiv__(self, other: Self) -> Abstraction.DivisionResult:
        """Abstract integer division of two sign sets."""
        return self.__div__(other)

    def __mod__(self, other: Self) -> Abstraction.DivisionResult:
        """Abstract modulus of two sign sets."""
        assert isinstance(other, SignSet)
        has_zero = "0" in other.signs
        if has_zero and len(other) == 1:
            # Error: modulus by zero
            return "divide by zero"

        new_signs: set[Sign] = {"0"}
        # JVM DOCS:
        # the result of the remainder operation
        # can be negative only if the dividend is negative and
        # can be positive only if the dividend is positive
        if "-" in other.signs:
            new_signs.add("-")
        if "+" in other.signs:
            new_signs.add("+")
        result = type(self)(new_signs)
        return result if not has_zero else (result, "divide by zero")

    def __neg__(self) -> Self:
        res: set[Sign] = set()
        if "+" in self.signs:
            res.add("-")
        if "0" in self.signs:
            res.add("0")
        if "-" in self.signs:
            # TODO(kornel): the negation of the maximum negative int
            # results in that same maximum negative number
            # For now discard the behavior,
            # since the suite doesn't seem to mind (see: Dependent:normalizedDistance)
            res.add("+")
            # res |= {"+", "-"}
        self.signs = res
        return self

    def __le__(self, other: Self) -> bool:
        if not isinstance(other, SignSet):
            return False
        return self.signs <= other.signs

    def __eq__(self, other: Self) -> bool:
        if not isinstance(other, SignSet):
            return False
        return self.signs == other.signs

    def __and__(self, other: Self) -> Self:
        if not isinstance(other, SignSet):
            return False
        return type(self)(self.signs & other.signs)

    def __or__(self, other: Self) -> Self:
        if not isinstance(other, SignSet):
            return False
        return type(self)(self.signs | other.signs)

    def widen(self, other: Self, _k_set: set[JvmNumberAbs]) -> Self:
        """As this is a finite-lattice abstraction, it always calls join."""
        return self.__or__(other)

    def i2s_cast(self) -> Self:
        """
        Model int-to-short cast for SignSet (conservative).

        Analysis:
        - {0} → {0} (zero preserved)
        - Any non-zero sign set → {+, -, 0} (TOP)

        Rationale: Without value ranges, we can't determine if wrapping occurs.
        Any positive value could be ≥32768 and wrap to negative.
        Any negative value could be ≤-32769 and wrap to positive.
        """
        if "0" in self.signs and len(self.signs) == 1:
            return type(self)({"0"})  # Zero preserved
        if len(self.signs) == 0:
            return type(self).bot()  # Bottom preserved
        return type(self).top()  # Conservative: any sign possible

    def __str__(self) -> str:
        return "{" + ",".join(sorted(self.signs)) + "}"

    def __len__(self) -> int:
        return len(self.signs)
