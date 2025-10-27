
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeVar
from abstraction import Sign, SignSet

import jpamb
from jpamb import jvm
from project.interpreter import PC, Stack, Bytecode


A = TypeVar("A")


@dataclass
class PerVarFrame[AV]:
    locals: dict[int, AV]
    stack: Stack[AV]


@dataclass
class AState[AV]:
    heap: dict[int, AV]
    frames: Stack[PerVarFrame[AV]]

    heap_ptr: int = 0
    bc = Bytecode(jpamb.Suite(), {})

    def abstract(self) -> "AState[AV]":
        pass

    def __str__(self) -> str:
        return f"{self.heap} {self.frames}"

    def __le__(self, other: "AState[AV]") -> bool:
        pass

    def __and__(self, other: "AState[AV]") -> "AState[AV]":
        pass

    def __or__(self, other: "AState[AV]") -> "AState[AV]":
        pass


@dataclass
class StateSet:
    per_inst : dict[PC, AState]
    needswork : set[PC]

    @classmethod
    def initialstate_from_method(cls, methodid: jvm.AbsMethodID) -> "StateSet":
        pass

    def per_instruction(self):
        for pc in self.needswork:
            yield (pc, self.per_inst[pc])

    # sts |= astate
    def __ior__(self, astate) -> None:
        old = self.per_inst[astate]
        self.per_inst[astate.pc] |= astate
        if old != self.per_inst[astate.pc]:
            self.needswork.add(astate.pc)


def step(state : AState) -> Iterable[AState | str]
    pass


def manystep(sts : StateSet) -> Iterable[AState | str]:
    new_state = dict(sts.per_inst)
    for k, v in sts.per_instruction():
        for s in step(v):
            new_state[s.pc] |= s
    return new_state.values()


final = {}
sts = StateSet.initialstate_from_method(methodid)
for i in range(MAX_STEPS):
    for s in manystep(sts):
        if isinstance(s, str):
            final.add(s)
        else:
            sts |= s
