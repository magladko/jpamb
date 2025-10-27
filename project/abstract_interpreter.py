
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
    def initialstate_from_method(cls, methodid: jvm.AbsMethodID) -> "StateSet":
        frame = PerVarFrame.from_method(methodid)
        state = AState({}, Stack.empty().push(frame))
        return StateSet(per_inst={frame.pc: state}, needswork={frame.pc})
        
        pass

    def per_instruction(self):
        for pc in self.needswork:
            yield (pc, self.per_inst[pc])

    # sts |= astate
    def __ior__(self, astate):
        pc = astate.pc
        old = self.per_inst.get(pc)
        if old is None:
            self.per_inst[pc] = astate
            self.needswork.add(pc)
        else:
            new = old | astate  # join in the lattice
            if new != old:
                self.per_inst[pc] = new
                self.needswork.add(pc)
        return self
        # old = self.per_inst[astate]
        # self.per_inst[astate.pc] |= astate
        # if old != self.per_inst[astate.pc]:
        #     self.needswork.add(astate.pc)

def step(state : AState) -> Iterable[AState | str]:
    return []


def manystep(sts : StateSet) -> Iterable[AState | str]:
    new_state = dict(sts.per_inst)
    for pc, state in sts.per_instruction():
        for s in step(state):
            if isinstance(s, AState):
                new_pc = s.pc
                if new_pc in new_state:
                    new_state[new_pc] |= s
                else:
                    new_state[new_pc] = s
    return new_state.values()



methodid = jpamb.getmethodid(
    "Interpreter",
    "1.0",
    "Garbage Spillers",
    ["random", "dynamic", "python"],
    for_science=True,
)

MAX_STEPS = 1000
final = set()
sts = StateSet.initialstate_from_method(methodid)
for i in range(MAX_STEPS):
    for s in manystep(sts):
        if isinstance(s, str):
            final.add(s)
        else:
            sts |= s
