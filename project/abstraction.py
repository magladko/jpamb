from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Literal

type Sign = Literal["+", "-", "0"]


class Arithmetic:
    """Abstract arithmetic operations for various abstract domains."""

    # Map signs to representative values for comparison
    _SIGN_VALUES: ClassVar[dict[str, int]] = {"+": 1, "-": -1, "0": 0}

    # Comparison operators
    _COMPARISONS: ClassVar[dict[str, Callable[[int, int], bool]]] = {
        "le": lambda a, b: a <= b,
        "lt": lambda a, b: a < b,
        "ge": lambda a, b: a >= b,
        "gt": lambda a, b: a > b,
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
    }

    @classmethod
    def compare(
        cls,
        op: Literal["le", "eq", "lt", "gt", "ge", "ne"],
        s1: "SignSet",
        s2: "SignSet",
    ) -> set[bool]:
        """
        Compare abstract values and return possible boolean results.

        For sign abstraction: compares all possible concrete values
        represented by the signs. We need to consider all possible
        combinations within each sign category.
        """
        if op not in cls._COMPARISONS:
            raise NotImplementedError(f"Op {op} not implemented")

        results = set()
        comp_fn = cls._COMPARISONS[op]

        # For each pair of signs, we need to consider all possible outcomes
        # For example: + compared with + can give both True and False
        for sign1 in s1.signs:
            for sign2 in s2.signs:
                # Use representative extreme values to capture all possibilities
                if sign1 == "+":
                    vals1 = [1, 100]  # Different positive values
                elif sign1 == "-":
                    vals1 = [-1, -100]  # Different negative values
                else:  # "0"
                    vals1 = [0]

                if sign2 == "+":
                    vals2 = [1, 100]
                elif sign2 == "-":
                    vals2 = [-1, -100]
                else:  # "0"
                    vals2 = [0]

                # Check all combinations
                for val1 in vals1:
                    for val2 in vals2:
                        results.add(comp_fn(val1, val2))

        return results

@dataclass
class SignSet:
    signs: set[Sign]

    @classmethod
    def abstract(cls, items: set[int]) -> "SignSet":
        signset = set()
        if 0 in items:
            signset.add("0")
        if any(x for x in items if x > 0):
            signset.add("+")
        if any(x for x in items if x < 0):
            signset.add("-")
        return cls(signset)

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

    def __contains__(self, member: int) -> bool:
        if member == 0 and "0" in self.signs:
            return True
        if member > 0 and "+" in self.signs:
            return True
        return bool(member < 0 and "-" in self.signs)

    def __add__(self, other: "SignSet") -> "SignSet":
        """Abstract addition of two sign sets."""
        assert isinstance(other, SignSet)
        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._add_signs(s1, s2))
        return SignSet(new_signs)

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

    def __sub__(self, other: "SignSet") -> "SignSet":
        """Abstract subtraction of two sign sets."""
        assert isinstance(other, SignSet)
        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._sub_signs(s1, s2))
        return SignSet(new_signs)

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

    def __mul__(self, other: "SignSet") -> "SignSet":
        """Abstract multiplication of two sign sets."""
        assert isinstance(other, SignSet)
        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                new_signs.update(self._mul_signs(s1, s2))
        return SignSet(new_signs)

    def __le__(self, other: "SignSet") -> bool:
        assert isinstance(other, SignSet)
        return self.signs <= other.signs

    def __eq__(self, other: "SignSet") -> bool:
        assert isinstance(other, SignSet)
        return self.signs == other.signs

    def __and__(self, other: "SignSet") -> "SignSet":
        assert isinstance(other, SignSet)
        return SignSet(self.signs & other.signs)

    def __or__(self, other: "SignSet") -> "SignSet":
        assert isinstance(other, SignSet)
        return SignSet(self.signs | other.signs)
