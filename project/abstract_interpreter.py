
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeVar, Self
from abstraction import Sign, SignSet

import jpamb
from jpamb import jvm
from interpreter import Stack, Bytecode
from loguru import logger
import sys
logger.remove()
logger.add(sys.stderr, format="[{level}] {message}", level="DEBUG")

A = TypeVar("A")


@dataclass(frozen=True)
class PC:
    method: jvm.AbsMethodID
    offset: int

    def __add__(self, delta: int) -> "PC":
        return PC(self.method, self.offset + delta)

    def __str__(self) -> str:
        return f"{self.method}:{self.offset}"

@dataclass
class PerVarFrame[AV]:
    locals: dict[int, AV]
    stack: Stack[AV]
    pc: PC

    def __str__(self) -> str:
        locals_str = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals_str}}}, {self.stack}, {self.pc}>"

    @classmethod
    def from_method(cls, method: jvm.AbsMethodID) -> "PerVarFrame":
        return PerVarFrame({}, Stack.empty(), PC(method, 0))


@dataclass
class AState[AV]:
    heap: dict[int, AV]
    frames: Stack[PerVarFrame[AV]]

    heap_ptr: int = 0
    bc = Bytecode(jpamb.Suite(), {})

    def abstract(self) -> "AState[AV]":
        raise NotImplementedError

    def __le__(self, other: "AState[AV]") -> bool:
        raise NotImplementedError

    def __and__(self, other: "AState[AV]") -> "AState[AV]":
        raise NotImplementedError

    def __or__(self, other: "AState[AV]") -> "AState[AV]":
        raise NotImplementedError
    
    @property
    def pc(self) -> PC:
        """Convenience accessor for current program counter."""
        return self.frames.peek().pc

    def __str__(self) -> str:
        return f"{self.heap} {self.frames}"


@dataclass
class StateSet:
    per_inst : dict[PC, AState]
    needswork : set[PC]

    @classmethod
    def initialstate_from_method(cls, methodid: jvm.AbsMethodID, input) -> "StateSet":
        frame = PerVarFrame.from_method(methodid)
        for i, v in enumerate(input.values):
            logger.debug(v)
            frame.locals[i] = v
        state = AState({}, Stack.empty().push(frame))
        return StateSet(per_inst={frame.pc: state}, needswork={frame.pc})
    
    def per_instruction(self):
        for pc in self.needswork:
            yield (pc, self.per_inst[pc])

    # sts |= astate
    def __ior__(self, astate: AState):
        pc = astate.pc
        old = self.per_inst.get(pc)
        if old is None:
            self.per_inst[pc] = astate
            self.needswork.add(pc)
        else:
            new = astate
            if new != old:
                self.per_inst[pc] = new
                self.needswork.add(pc)
        return self
        # old = self.per_inst[astate]
        # self.per_inst[astate.pc] |= astate
        # if old != self.per_inst[astate.pc]:
        #     self.needswork.add(astate.pc)

def step(state : AState) -> Iterable[AState | str]:
    return ["assertion error"]


def manystep(sts : StateSet) -> Iterable[AState | str]:
    new_states = list()
    for pc, state in sts.per_instruction():
        for s in step(state):
            new_states.append(s)
    return new_states


methodid, input = jpamb.getcase()
MAX_STEPS = 1000
final = set()
sts = StateSet.initialstate_from_method(methodid, input)
for i in range(MAX_STEPS):
    for s in manystep(sts):
        if isinstance(s, str):
            final.add(s)
        else:
            sts |= s

logger.debug(len(final))
for result in final:
    print(result)
