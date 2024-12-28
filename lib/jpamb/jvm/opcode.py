"""
jpamb.jvm.opcode

This module contains the decompilation of the output of jvm2json 
into a python structure, as well documentation and semantics for 
each instruction.

"""

from dataclasses import dataclass
from abc import ABC

from . import base as jvm


@dataclass(frozen=True, order=True)
class Opcode(ABC):
    """An opcode, as parsed from the jvm2json output."""

    offset: int

    @classmethod
    def from_json(cls, json: dict) -> "Opcode":
        match json["opr"]:
            case "push":
                opr = Push
            case "newarray":
                opr = NewArray
            case "dup":
                opr = Dup
            case "array_store":
                opr = ArrayStore
            case "store":
                opr = Store
            case "load":
                opr = Load
            case "arraylength":
                opr = ArrayLength
            case opr:
                raise NotImplementedError(
                    f"Unhandled opcode {opr!r} (implement yourself)"
                )
        return opr.from_json(json)

    def real(self) -> str:
        """return the real opcode, as documented in the jvm spec."""
        raise NotImplementedError(f"Unhandled real {self!r}")


@dataclass(frozen=True)
class Push(Opcode):
    """The push opcode"""

    docs = [
        "https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iconst_i"
    ]

    semantics = """
    bc[i].opr = 'push'
    bc[i].value = v
    -------------------------[push]
    bc |- (i, s) -> (i+1, s + [v])
    """

    value: jvm.Value

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
            value=jvm.Value.from_json(json["value"]),
        )

    def real(self) -> str:
        match self.value.type:
            case jvm.Int():
                match self.value.value:
                    case -1:
                        return "iconst_m1"
                    case 0:
                        return "iconst_0"
                    case 1:
                        return "iconst_1"
                    case 2:
                        return "iconst_2"
                    case 3:
                        return "iconst_3"
                    case 4:
                        return "iconst_4"
                    case 5:
                        return "iconst_5"
                return f"ldc [{self.value.value}]"

        raise NotImplementedError(f"Unhandled {self!r}")

    def __str__(self):
        return f"push {self.value}"


@dataclass(frozen=True)
class NewArray(Opcode):
    """The new array opcode"""

    docs = [
        "https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.newarray"
        "https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.multianewarray"
    ]

    type: jvm.Type
    dim: int

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
            type=jvm.Type.from_json(json["type"]),
            dim=json["dim"],
        )

    def real(self) -> str:
        if self.dim == 1:
            return f"newarray {self.type}"
        else:
            return f"multianewarray {self.type} {self.dim}"

    def __str__(self):
        return f"newarray[{self.dim}D] {self.type}"


@dataclass(frozen=True)
class Dup(Opcode):
    """The dublicate the stack opcode"""

    docs = [
        "https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.dup"
    ]

    semantics = """
    bc[i].opr = 'dup'
    bc[i].words = 1
    -------------------------[dup1]
    (i, s + [v]) -> (i+1, s + [v, v])
    """

    words: int

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
            words=json["words"],
        )

    def real(self) -> str:
        if self.words == 1:
            return f"dup"
        return super().real()

    def __str__(self):
        return f"dup {self.words}"


@dataclass(frozen=True)
class ArrayStore(Opcode):
    """The Array Store command that stores a value in the array."""

    docs = [
        "https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.aastore"
        "https://docs.oracle.com/javase/specs/jvms/se23/html/jvms-6.html#jvms-6.5.iastore"
    ]

    type: jvm.Type

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
            type=jvm.Type.from_json(json["type"]),
        )

    def real(self) -> str:
        match self.type:
            case jvm.Reference():
                return "aastore"
            case jvm.Int():
                return "iastore"

        return super().real()

    def __str__(self):
        return f"array_store {self.type}"


@dataclass(frozen=True)
class Store(Opcode):

    docs = []

    type: jvm.Type

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
            type=jvm.Type.from_json(json["type"]),
        )

    def __str__(self):
        return f"store {self.type}"


@dataclass(frozen=True)
class Load(Opcode):

    docs = []

    type: jvm.Type

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
            type=jvm.Type.from_json(json["type"]),
        )

    def __str__(self):
        return f"load {self.type}"


@dataclass(frozen=True)
class ArrayLength(Opcode):

    docs = []

    @classmethod
    def from_json(cls, json: dict) -> Opcode:
        return cls(
            offset=json["offset"],
        )

    def __str__(self):
        return f"arraylength"
