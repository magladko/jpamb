from abc import ABC, abstractmethod
from types import UnionType, get_original_bases
from typing import Literal, Self, TypeAliasType, get_args, get_origin

from jpamb import jvm

type Comparison = Literal["le", "eq", "lt", "gt", "ge", "ne"]
type JvmNumberAbs = (
    jvm.Int | jvm.Short | jvm.Long | jvm.Byte | jvm.Float | jvm.Double | jvm.Boolean
)


class Abstraction[T: jvm.Type](ABC):
    type DivisionResult = (
        Self | Literal["divide by zero"] | tuple[Self, Literal["divide by zero"]]
    )

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
    def get_supported_types(cls) -> tuple[type, ...]:
        """Return tuple of supported types from the generic parameter."""
        for base in getattr(cls, "__orig_bases__", ()):
            args = get_args(base)
            if args:
                type_arg = args[0]

                # Unwrap TypeAliasType
                while isinstance(type_arg, TypeAliasType):
                    type_arg = type_arg.__value__

                # Unwrap __value__ attribute if present
                while hasattr(type_arg, "__value__"):
                    type_arg = type_arg.__value__

                # Now extract Union members
                if get_origin(type_arg) is UnionType:
                    return get_args(type_arg)

                return (type_arg,)
        return ()

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

    @classmethod
    @abstractmethod
    def has_finite_lattice(cls) -> bool:
        """
        Return true if abstraction is based on a final lattice.

        No widening is necessary in case this method returns True.
        """

    @classmethod
    def comp_res_str(cls, result: dict[bool, tuple[Self, Self]]) -> str:
        return ", ".join(f"{k}: ({v[0]!s}, {v[1]!s})" for k, v in result.items())

    def compare(self, op: Comparison, other: Self) -> dict[bool, tuple[Self, Self]]:
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

    @abstractmethod
    def le(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        pass

    @abstractmethod
    def lt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        pass

    @abstractmethod
    def eq(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        pass

    @abstractmethod
    def ne(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        pass

    @abstractmethod
    def ge(self, other: Self) -> dict[bool, tuple[Self, Self]]:
        pass

    @abstractmethod
    def gt(self, other: Self) -> dict[bool, tuple[Self, Self]]:
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
    def __div__(self, other: Self) -> DivisionResult:
        pass

    @abstractmethod
    def __floordiv__(self, other: Self) -> DivisionResult:
        pass

    @abstractmethod
    def __mod__(self, other: Self) -> DivisionResult:
        pass

    @abstractmethod
    def __neg__(self) -> Self:
        """
        For abstractions not supporting number types, return Self.

        OBS: The negation of the maximum negative int results
             in that same maximum negative number
        """

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
    def widen(self, other: Self, k_set: set[T]) -> Self:
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass
