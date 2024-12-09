"""
jpamb.jvm

This module provides primitives to talk about the contents of java bytefiles, 
as well as names and types.

"""

from functools import total_ordering
import re
from abc import ABC
from dataclasses import dataclass

type_instances = dict()


@total_ordering
class Type(ABC):
    """A jvm type"""

    def encode(self) -> str: ...

    @staticmethod
    def decode(input) -> tuple["Type", str]:
        r, stack = None, []
        i = 0
        r = None
        while i < input.length():
            match input[i]:
                case "Z":
                    r = JvmBoolean
                case "I":
                    r = JvmInt
                case "B":
                    r = JvmByte
                case "[":  # ]
                    stack.append(JvmList)
                    i += 1
                    continue
            break
        else:
            raise ValueError(f"Could not decode {input}")

        assert r is not None

        key = tuple(stack + [r])

        if (r := type_instances.get(key, None)) is None:
            for k in reversed(stack):
                r = k(r)
            type_instances[key] = r

        return r, input[i + 1 :]

    def __lt__(self, other):
        return self.encode() <= other.encode()

    def __eq__(self, other):
        return self.encode() <= other.encode()


@dataclass(frozen=True)
class JvmBoolean(Type):
    """
    A boolean
    """

    def encode(self):
        return "Z"


@dataclass(frozen=True)
class JvmInt(Type):
    """
    A 32bit signed integer
    """

    def encode(self):
        return "I"


@dataclass(frozen=True)
class JvmByte(Type):
    """
    An 8bit signed integer
    """

    def encode(self):
        return "B"


@dataclass(frozen=True, order=True)
class JvmList(Type):
    """
    A list of types
    """

    contains: Type

    def encode(self):
        return "[" + self.contains.encode()  # ]


@dataclass(frozen=True, order=True)
class Parameters:
    """A list of parameters types"""

    _elements: tuple[Type, ...]

    def __getitem__(self, index):
        return self._elements.__getitem__(index)

    def __len__(self):
        return self._elements.__len__()

    def encode(self):
        return "".join(e.encode() for e in self._elements)

    @staticmethod
    def decode(input: str) -> "Parameters":
        params = []
        while input:
            (tt, input) = Type.decode(input)
            params.append(tt)

        return Parameters(tuple(params))


@dataclass(frozen=True, order=True)
class ClassName:
    """The name of a class"""

    _as_string: str

    def encode(self) -> str:
        return self._as_string

    @staticmethod
    def decode(input: str) -> "ClassName":
        return ClassName(input)


METHOD_ID_RE_RAW = r"(?P<method_name>.*)\:\((?P<params>.*)\)(?P<return>.*)"
METHOD_ID_RE = re.compile(METHOD_ID_RE_RAW)
ABSMETHOD_ID_RE = re.compile(r"(?P<class_name>.+)." + METHOD_ID_RE_RAW)


@dataclass(frozen=True, order=True)
class MethodID:
    """A method ID consist of a name, a list of parameter types and a return type."""

    name: str
    params: Parameters
    return_type: Type | None

    @staticmethod
    def decode(input):
        match = None
        if not isinstance(input, str):
            match = input

        if match is None and (match := METHOD_ID_RE.match(input)) is None:
            raise ValueError("invalid method name: %r", input)

        return_type = None
        if match["return"] != "V":
            return_type, more = Type.decode(match["return"])
            if more:
                raise ValueError(
                    f"could not decode method id, bad return type {match['return']!r}"
                )

        return MethodID(
            name=match["method_name"],
            params=Parameters.decode(match["params"]),
            return_type=return_type,
        )

    @staticmethod
    def decode_absolute(input) -> tuple[ClassName, "MethodID"]:
        if (match := ABSMETHOD_ID_RE.match(input)) is None:
            raise ValueError("invalid absolute method name: %r", input)

        return (ClassName.decode(match["class_name"]), MethodID.decode(match))

    @staticmethod
    def encode_absolute(abs: tuple[ClassName, "MethodID"]) -> str:
        return f"{abs[0].encode()}.{abs[1].encode()}"

    def encode(self) -> str:
        rt = self.return_type.encode() if self.return_type is not None else "V"
        return f"{self.name}:(){self.params.encode()}){rt}"
