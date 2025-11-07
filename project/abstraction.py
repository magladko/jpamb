from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import get_original_bases
from typing import Literal, Self, get_args, get_origin

type Sign = Literal["+", "-", "0"]
type Comparison = Literal["le", "eq", "lt", "gt", "ge", "ne"]


class Abstraction[T](ABC):

    concrete_type: type[T]

    def __init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        super().__init_subclass__(**kwargs)
        # Extract T from the generic base
        for base in get_original_bases(cls):
            origin = get_origin(base)
            if origin is Abstraction:
                args = get_args(base)
                if args:
                    cls.concrete_type = args[0]
                break

    @classmethod
    @abstractmethod
    def abstract(cls, items: set[T]) -> Self:
        pass

    @classmethod
    @abstractmethod
    def bot(cls) -> Self:
        pass

    @classmethod
    @abstractmethod
    def top(cls) -> Self:
        pass

    @abstractmethod
    def compare(self, op: Comparison, other: Self) -> set[bool]:
        pass

    @abstractmethod
    def le(self, other: Self) -> set[bool]:
        pass

    @abstractmethod
    def eq(self, other: Self) -> set[bool]:
        pass

    @abstractmethod
    def __contains__(self, member: T) -> bool:
        pass

    @abstractmethod
    def __add__(self, other: Self) -> Self:
        pass

    @abstractmethod
    def __sub__(self, other: Self) -> Self:
        pass

    @abstractmethod
    def __mul__(self, other: Self) -> Self:
        pass

    @abstractmethod
    def __div__(self, other: Self) -> Self:
        pass

    @abstractmethod
    def __floordiv__(self, other: Self) -> Self:
        pass

    @abstractmethod
    def __mod__(self, other: Self) -> Self:
        pass

    @abstractmethod
    def __le__(self, other: Self) -> bool:
        """Return result of poset ordering (self ⊑ other)."""

    @abstractmethod
    def __eq__(self, other: Self) -> bool:
        pass

    @abstractmethod
    def __and__(self, other: Self) -> Self:
        """Return result of meet operator (self ⊓ other)."""

    @abstractmethod
    def __or__(self, other: Self) -> Self:
        """Return result of join operator (self ⊔ other)."""

    @abstractmethod
    def __str__(self) -> str:
        pass

class Arithmetic[AbstractionClass: Abstraction]:
    """Abstract arithmetic operations for various abstract domains."""

    @classmethod
    def compare(
        cls,
        op: Comparison,
        s1: AbstractionClass,
        s2: AbstractionClass,
    ) -> set[bool]:
        """Compare abstract values and return possible boolean results."""
        return s1.compare(op, s2)


@dataclass
class SignSet(Abstraction[int]):
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

    @classmethod
    def bot(cls) -> "SignSet":
        return cls(set())

    @classmethod
    def top(cls) -> "SignSet":
        return cls({"+", "-", "0"})

    def compare(self, op: Comparison, other: "SignSet") -> set[bool]:
        match op:
            case "le":
                return self.le(other)
            case "lt":
                return self.lt(other)
            case "eq":
                return self.eq(other)
            case "ne":
                return self.ne(other)
            case "ge":
                return self.ge(other)
            case "gt":
                return self.gt(other)
            case _:
                raise NotImplementedError(f"Op {op} not implemented")

    def le(self, other: "SignSet") -> set[bool]:
        # {0} <= {0} -> {True}
        # {0} <= {+} -> {True}
        # {0} <= {-} -> {False}
        # {+} <= {0} -> {False}
        # {+} <= {+} -> {True, False}
        # {+} <= {-} -> {False}
        # {-} <= {0} -> {True}
        # {-} <= {+} -> {True}
        # {-} <= {-} -> {True, False}
        results = set()
        for s1 in self.signs:
            for s2 in other.signs:
                match (s1, s2):
                    case (("0", "0") | ("0", "+") | ("-", "0") | ("-", "+")):
                        results.add(True)
                    case ("0", "-") | ("+", "0") | ("+", "-"):
                        results.add(False)
                    case ("+", "+") | ("-", "-"):
                        results.update({True, False})
                    case _:
                        raise ValueError(f"Invalid signs: {s1}, {s2}")
        return results

    def eq(self, other: "SignSet") -> set[bool]:
        # {0} == {0} -> {True}
        # {0} == {+} -> {False}
        # {0} == {-} -> {False}
        # {+} == {0} -> {False}
        # {+} == {+} -> {True, False}
        # {+} == {-} -> {False}
        # {-} == {0} -> {False}
        # {-} == {+} -> {False}
        # {-} == {-} -> {True, False}
        results = set()
        for s1 in self.signs:
            for s2 in other.signs:
                match (s1, s2):
                    case (("0", "0")):
                        results.add(True)
                    case (("0", "+") | ("0", "-") | ("+", "0") |
                          ("-", "0") | ("+", "-") | ("-", "+")):
                        results.add(False)
                    case ("+", "+") | ("-", "-"):
                        results.update({True, False})
                    case _:
                        raise ValueError(f"Invalid signs: {s1}, {s2}")
        return results

    def ne(self, other: "SignSet") -> set[bool]:
        return {not r for r in self.eq(other)}

    def lt(self, other: "SignSet") -> set[bool]:
        # {0} < {0} -> {False}
        # {0} < {+} -> {True}
        # {0} < {-} -> {False}
        # {+} < {0} -> {False}
        # {+} < {+} -> {True, False}
        # {+} < {-} -> {False}
        # {-} < {0} -> {True}
        # {-} < {+} -> {True}
        # {-} < {-} -> {True, False}
        results = set()
        for s1 in self.signs:
            for s2 in other.signs:
                match (s1, s2):
                    case ("0", "+") | ("-", "0") | ("-", "+"):
                        results.add(True)
                    case ("0", "0") | ("0", "-") | ("+", "0") | ("+", "-"):
                        results.add(False)
                    case ("+", "+") | ("-", "-"):
                        results.update({True, False})
                    case _:
                        raise ValueError(f"Invalid signs: {s1}, {s2}")
        return results

    def ge(self, other: "SignSet") -> set[bool]:
        # {0} >= {0} -> {True}
        # {0} >= {+} -> {False}
        # {0} >= {-} -> {True}
        # {+} >= {0} -> {True}
        # {+} >= {+} -> {True, False}
        # {+} >= {-} -> {True}
        # {-} >= {0} -> {False}
        # {-} >= {+} -> {False}
        # {-} >= {-} -> {True, False}
        results = set()
        for s1 in self.signs:
            for s2 in other.signs:
                match (s1, s2):
                    case ("0", "0") | ("0", "-") | ("+", "0") | ("+", "-"):
                        results.add(True)
                    case ("0", "+") | ("-", "0") | ("-", "+"):
                        results.add(False)
                    case ("+", "+") | ("-", "-"):
                        results.update({True, False})
                    case _:
                        raise ValueError(f"Invalid signs: {s1}, {s2}")
        return results

    def gt(self, other: "SignSet") -> set[bool]:
        # {0} > {0} -> {False}
        # {0} > {+} -> {False}
        # {0} > {-} -> {True}
        # {+} > {0} -> {True}
        # {+} > {+} -> {True, False}
        # {+} > {-} -> {True}
        # {-} > {0} -> {False}
        # {-} > {+} -> {False}
        # {-} > {-} -> {True, False}
        results = set()
        for s1 in self.signs:
            for s2 in other.signs:
                match (s1, s2):
                    case ("0", "-") | ("+", "0") | ("+", "-"):
                        results.add(True)
                    case ("0", "0") | ("0", "+") | ("-", "0") | ("-", "+"):
                        results.add(False)
                    case ("+", "+") | ("-", "-"):
                        results.update({True, False})
                    case _:
                        raise ValueError(f"Invalid signs: {s1}, {s2}")
        return results

    def __contains__(self, member: int) -> bool:
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

    def __div__(self, other: "SignSet") -> "SignSet":
        """Abstract division of two sign sets."""
        assert isinstance(other, SignSet)
        if "0" in other.signs and len(other) == 1:
            # Error: divide by zero
            return SignSet.bot()

        new_signs = set()
        for s1 in self.signs:
            for s2 in other.signs:
                # if s2 == "0":
                #     raise ValueError("divide by zero")
                new_signs.update(self._mul_signs(s1, s2))
        return SignSet(new_signs)

    def __floordiv__(self, other: Self) -> "SignSet":
        """Abstract integer division of two sign sets."""
        return self.__div__(other)

    def __mod__(self, other: Self) -> "SignSet":
        """Abstract modulus of two sign sets."""
        assert isinstance(other, SignSet)
        if "0" in other.signs and len(other) == 1:
            # Error: modulus by zero
            return SignSet.bot()

        new_signs: set[Sign] = {"0"}
        # JVM DOCS:
        # the result of the remainder operation
        # can be negative only if the dividend is negative and
        # can be positive only if the dividend is positive
        if "-" in other.signs:
            new_signs.add("-")
        if "+" in other.signs:
            new_signs.add("+")
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

    def __str__(self) -> str:
        return "{" + ",".join(sorted(self.signs)) + "}"

    def __len__(self) -> int:
        return len(self.signs)
