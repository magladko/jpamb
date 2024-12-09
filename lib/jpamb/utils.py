from typing import NoReturn, TypeAlias, Literal, Optional
from dataclasses import dataclass
from collections import namedtuple
from pathlib import Path
import re


def string_compare(cls):
    from functools import total_ordering

    cls.__eq__ = lambda self, other: str(self) == str(other)
    cls.__le__ = lambda self, other: str(self) < str(other)
    return total_ordering(cls)


@dataclass(frozen=True)
@string_compare
class BoolValue:
    value: bool

    def __str__(self):
        return "true" if self.value else "false"

    def tolocal(self):
        return IntValue(1) if self.value else IntValue(0)


@dataclass(frozen=True)
@string_compare
class IntValue:
    value: int

    def __str__(self):
        return str(self.value)

    def tolocal(self):
        return self.value


@dataclass(frozen=True)
@string_compare
class CharValue:
    value: str

    def __str__(self):
        return f"'{self.value}'"

    def tolocal(self):
        return IntValue(ord(self.value[0]))


@dataclass(frozen=True)
@string_compare
class IntListValue:
    value: tuple[int]

    def __str__(self) -> str:
        val = ", ".join(str(a) for a in self.value)
        return f"[I:{val}]"

    def tolocal(self):
        return self.value


@dataclass(frozen=True)
@string_compare
class CharListValue:
    value: tuple[str]

    def __str__(self) -> str:
        val = ", ".join(str(a) for a in self.value)
        return f"[C:{val}]"

    def tolocal(self):
        return self.value


JvmValue: TypeAlias = BoolValue | IntValue | CharValue | IntListValue | CharListValue


@dataclass
class InputParser:
    Token = namedtuple("Token", "kind value")

    tokens: list["InputParser.Token"]
    input: str

    def __init__(self, input) -> None:
        self.input = input
        self.tokens = list(InputParser.tokenize(input))

    @staticmethod
    def tokenize(string):
        token_specification = [
            ("OPEN_ARRAY", r"\[[IC]:"),
            ("CLOSE_ARRAY", r"\]"),
            ("OPEN_INPUTS", r"\("),
            ("CLOSE_INPUTS", r"\)"),
            ("INT", r"-?\d+"),
            ("BOOL", r"true|false"),
            ("CHAR", r"'[^']'"),
            ("COMMA", r","),
            ("SKIP", r"[ \t]+"),
        ]
        tok_regex = "|".join(f"(?P<{n}>{m})" for n, m in token_specification)

        for m in re.finditer(tok_regex, string):
            kind, value = m.lastgroup, m.group()
            if kind == "SKIP":
                continue
            yield InputParser.Token(kind, value)

    @staticmethod
    def parse(string) -> list[JvmValue]:
        return InputParser(string).parse_inputs()

    @property
    def head(self):
        if self.tokens:
            return self.tokens[0]

    def next(self):
        self.tokens = self.tokens[1:]

    def expected(self, expected) -> NoReturn:
        raise ValueError(
            f"Expected {expected} but got {self.tokens[:3]} in {self.input}"
        )

    def expect(self, expect) -> Token:
        head = self.head
        if head is None:
            self.expected(repr(expect))
        elif expect != head.kind:
            self.expected(repr(expect))
        self.next()
        return head

    def parse_input(self):
        next = self.head or self.expected("token")
        if next.kind == "INT":
            return self.parse_int()
        if next.kind == "OPEN_ARRAY":
            return self.parse_array()
        if next.kind == "BOOL":
            return self.parse_bool()
        self.expected("input")

    def parse_int(self):
        tok = self.expect("INT")
        return IntValue(int(tok.value))

    def parse_bool(self):
        tok = self.expect("BOOL")
        return BoolValue(tok.value == "true")

    def parse_char(self):
        tok = self.expect("CHAR")
        return CharValue(tok.value[1])

    def parse_array(self):
        key = self.expect("OPEN_ARRAY")
        if key.value == "[I:":  # ]
            listtype = IntListValue
            parser = self.parse_int
        elif key.value == "[C:":  # ]
            listtype = CharListValue
            parser = self.parse_char
        else:
            self.expected("int or char array")

        inputs = []

        if self.head is None:
            self.expected("input or ]")

        if self.head.kind == "CLOSE_ARRAY":
            self.next()
            return listtype(tuple())

        inputs.append(parser())

        while self.head and self.head.kind == "COMMA":
            self.next()
            inputs.append(parser())

        self.expect("CLOSE_ARRAY")

        return listtype(tuple(inputs))

    def parse_inputs(self):
        self.expect("OPEN_INPUTS")
        inputs = []

        if self.head is None:
            self.expected("input or )")

        if self.head.kind == "CLOSE_INPUTS":
            return inputs

        inputs.append(self.parse_input())

        while self.head and self.head.kind == "COMMA":
            self.next()
            inputs.append(self.parse_input())

        self.expect("CLOSE_INPUTS")

        return inputs
