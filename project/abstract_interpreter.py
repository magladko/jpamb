
import sys
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Self

from abstraction import Abstraction, SignSet
from interpreter import PC, Bytecode, Stack
from loguru import logger

import jpamb
from jpamb import jvm

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}", level="DEBUG")

@dataclass
class PerVarFrame[AV: Abstraction]:
    locals: dict[int, AV]
    stack: Stack[AV]
    pc: PC

    def __str__(self) -> str:
        locals_str = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals_str}}}, {self.stack}, {self.pc}>"

    @classmethod
    def from_method(cls, method: jvm.AbsMethodID) -> Self:
        return cls({}, Stack.empty(), PC(method, 0))

    def clone(self) -> "PerVarFrame[AV]":
        return PerVarFrame(
            locals=self.locals.copy(),
            stack=Stack(self.stack.items.copy()),
            pc=self.pc
        )


@dataclass
class AState[AV: Abstraction]:
    heap: dict[int, AV]
    frames: Stack[PerVarFrame[AV]]

    heap_ptr: int = 0
    bc = Bytecode(jpamb.Suite(), {})

    # def abstract(self) -> "AState[AV]":
    #     raise NotImplementedError

    # def __le__(self, other: "AState[AV]") -> bool:
    #     raise NotImplementedError

    # def __and__(self, other: "AState[AV]") -> "AState[AV]":
    #     raise NotImplementedError

    # def __or__(self, other: "AState[AV]") -> "AState[AV]":
    #     raise NotImplementedError

    def __ior__(self, other: "AState[AV]") -> Self:
        """
        In-place join operation (⊔) for abstract states.

        Performs pointwise join of:
        - Heap locations (join abstract values at same addresses)
        - Frame locals (join abstract values for same variable indices)
        - Frame stacks (join corresponding stack positions)
        """
        assert isinstance(other, AState), f"expected AState but got {other}"
        assert (
            len(self.frames.items) == len(other.frames.items)
        ), f"frame stack sizes differ {self} != {other}"

        # Join heap pointwise
        for addr in other.heap:
            if addr in self.heap:
                self.heap[addr] = self.heap[addr] | other.heap[addr]
            else:
                self.heap[addr] = other.heap[addr]

        # Join frames pointwise
        for f1, f2 in zip(self.frames.items, other.frames.items, strict=True):
            assert f1.pc == f2.pc, f"Program counters differ: {f1.pc} != {f2.pc}"

            # Join locals pointwise
            for var_idx in f2.locals:
                if var_idx in f1.locals:
                    f1.locals[var_idx] = f1.locals[var_idx] | f2.locals[var_idx]
                else:
                    f1.locals[var_idx] = f2.locals[var_idx]

            # Join stacks pointwise (must have same length at same PC)
            assert len(f1.stack.items) == len(f2.stack.items), (
                f"Stack sizes differ at {f1.pc}: "
                f"{len(f1.stack.items)} != {len(f2.stack.items)}"
            )
            for i in range(len(f1.stack.items)):
                f1.stack.items[i] = f1.stack.items[i] | f2.stack.items[i]

        return self

    def __eq__(self, other: object) -> bool:
        """Check equality of abstract states."""
        if not isinstance(other, AState):
            return False

        # Check heap equality
        if set(self.heap.keys()) != set(other.heap.keys()):
            return False
        for addr in self.heap:
            if self.heap[addr] != other.heap[addr]:
                return False

        # Check frames equality
        if len(self.frames.items) != len(other.frames.items):
            return False

        for f1, f2 in zip(self.frames.items, other.frames.items, strict=True):
            if f1.pc != f2.pc:
                return False

            # Check locals equality
            if set(f1.locals.keys()) != set(f2.locals.keys()):
                return False
            for var_idx in f1.locals:
                if f1.locals[var_idx] != f2.locals[var_idx]:
                    return False

            # Check stack equality
            if len(f1.stack.items) != len(f2.stack.items):
                return False
            for i in range(len(f1.stack.items)):
                if f1.stack.items[i] != f2.stack.items[i]:
                    return False

        return True

    @property
    def pc(self) -> PC:
        """Convenience accessor for current program counter."""
        return self.frames.peek().pc

    def __str__(self) -> str:
        return f"{self.heap} {self.frames}"

    def clone(self) -> "AState[AV]":
        return AState(
            heap=self.heap.copy(), # shallow copy of heap, adjust if AV is mutable
            frames=Stack([deepcopy(f) for f in self.frames.items]), # deep copy frames
            heap_ptr=self.heap_ptr
        )


@dataclass
class StateSet[AV: Abstraction]:
    per_inst : dict[PC, AState[AV]]
    needswork : set[PC]

    @classmethod
    def initialstate_from_method(cls, methodid: jvm.AbsMethodID,
                                 abstraction_cls: type[AV]) -> Self:
        frame = PerVarFrame[AV].from_method(methodid)
        params = methodid.extension.params
        for i, p in enumerate(params):
            if isinstance(p, (jvm.Float, jvm.Double)):
                raise NotImplementedError("Only integer parameters supported")
            frame.locals[i] = abstraction_cls.top()
        state = AState[AV]({}, Stack.empty().push(frame))
        return cls(per_inst={frame.pc: state}, needswork={frame.pc})

    def per_instruction(self) -> Iterable[tuple[PC, AState[AV]]]:
        # for pc in self.needswork:
        #     yield (pc, self.per_inst[pc])

        while self.needswork:
            pc = self.needswork.pop()
            yield (pc, self.per_inst[pc])

    # sts |= astate
    def __ior__(self, astate: AState) -> Self:
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

    # sts |= astate
    # def __ior__(self, astate: AState[AV]) -> Self:
    #     """
    #     Join an abstract state into the state set.

    #     If the PC doesn't exist, add it. Otherwise, join with existing state.
    #     Add to needswork if the state changed.
    #     """
    #     pc = astate.pc
    #     old = self.per_inst.get(pc)
    #     if old is None:
    #         # New PC: add state and mark for processing
    #         self.per_inst[pc] = astate
    #         self.needswork.add(pc)
    #     else:
    #         # Existing PC: join states and check if changed
    #         old_copy = old.clone()
    #         self.per_inst[pc] |= astate
    #         # Only add to needswork if state actually changed
    #         if self.per_inst[pc] != old_copy:
    #             self.needswork.add(pc)
    #     return self

    def __str__(self) -> str:
        return "\n".join(f"{pc}: {state}" for pc, state in self.per_inst.items())


def step[AV: Abstraction](state: AState[AV],
                          abstraction_cls: type[AV]) -> Iterable[AState[AV] | str]:
    assert isinstance(state, AState), f"expected frame but got {state}"
    frame = state.frames.peek()
    opr = state.bc[frame.pc]
    logger.debug(f"STEP {opr}\n{state}")
    match opr:
        case jvm.Push(value=v):
            assert isinstance(v.value, int), F"Unsupported value type: {v.value!r}"
            frame.stack.push(abstraction_cls.abstract({v.value}))
            frame.pc += 1
            return [state]
        case jvm.Load(type=type, index=i):
            assert i in frame.locals, f"Local variable {i} not initialized"
            v = frame.locals[i]
            frame.stack.push(frame.locals[i])
            frame.pc += 1
            return [state]
        case jvm.Ifz(condition=_, target=t) | jvm.If(condition=_, target=t):
            # Pop the value being tested
            frame.stack.pop()
            # Clone state before modifying PC
            other = state.clone()
            # One path: continue to next instruction
            frame.pc += 1
            # Other path: jump to target
            other.frames.peek().pc.offset = t
            return (state, other)
        case jvm.Return(type=type):
            state.frames.pop()
            if state.frames:
                caller_frame = state.frames.peek()
                if type is not None:
                    v1 = frame.stack.pop()
                    caller_frame.stack.push(v1)
                return [state]
            return ["ok"]
        case jvm.Binary(type=jvm.Int(), operant=operant):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert isinstance(v1, Abstraction), f"expected Abstraction, but got {v1}"
            assert isinstance(v2, Abstraction), f"expected Abstraction, but got {v2}"

            v = None
            try:
                match operant:
                    case jvm.BinaryOpr.Div:
                        v = v1 // v2
                    case jvm.BinaryOpr.Rem:
                        v = v1 % v2
                    case jvm.BinaryOpr.Sub:
                        v = v1 - v2
                    case jvm.BinaryOpr.Mul:
                        v = v1 * v2
                    case jvm.BinaryOpr.Add:
                        v = v1 + v2
                    case _:
                        raise NotImplementedError(
                            f"Operand '{operant!r}' not implemented.")
                frame.stack.push(v)
            except ValueError as e:
                return [str(e)]
            frame.pc += 1
            return [state]
        case jvm.Get(
            static=True,
            field=jvm.AbsFieldID(
                classname=_,
                extension=jvm.FieldID(name="$assertionsDisabled", type=jvm.Boolean()),
            ),
        ):
            frame.stack.push(abstraction_cls.abstract({0}))
            frame.pc += 1
            return [state]
        case jvm.New(classname=jvm.ClassName(_as_string="java/lang/AssertionError")):
            logger.debug("Creating AssertionError object")
            return ["assertion error"]
        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")


def manystep[AV: Abstraction](sts: StateSet[AV],
                              abstraction_cls: type[AV]) -> Iterable[AState[AV] | str]:
    states = []
    for _pc, state in sts.per_instruction():
        # for ([va1, va2], after) in state.group(pop=[jvm.Int(), jvm.Int()]):
        #     pass
        # bc = state.bc
        # match bc[pc]:
        #     case jvm.Binary(type=jvm.Int(), operant=opr):
        #         pass
        # logger.debug(f"Many step at {pc}")
        states.extend(step(state, abstraction_cls))
        # yield from step(state, abstraction_cls)
        # if isinstance(state, AState):
        #     logger.debug(f"{state.frames.peek().pc}")
        # else:
        #     logger.debug(state)
    return states
# def many_step[AV: Abstraction](state: dict[PC, AState[AV] | str],
#                                abstraction_cls: type[AV]) -> dict[PC, AState[AV] | str]:
#     new_state = dict(state)
#     for pc, astate in state.items():
#         if isinstance(astate, str):
#             new_state[pc] = astate
#         else:
#             for s in step(astate, abstraction_cls):
#                 new_state[s.pc] |= s
#     return new_state

methodid = jpamb.getmethodid(
    "Abstract Interpreter",
    "0.1",
    "The Garbage Spillers",
    ["abstract interpretation", "sign analysis", "python"],
    for_science=True,
)

# import debugpy
# debugpy.listen(5678)
# logger.debug("Waiting for debugger attach")
# debugpy.wait_for_client()

if methodid is None:
    logger.error("Method ID not found")
    methodid, case_input = jpamb.getcase()
else:
    params = methodid.extension.params

AV = SignSet

MAX_STEPS = 10
final: set[str] = set()
sts = StateSet[AV].initialstate_from_method(methodid, AV)
logger.debug(f"Initial state:\n{sts}")
for _ in range(MAX_STEPS):
    for s in manystep(sts, AV):
        if isinstance(s, str):
            final.add(s)
        else:
            sts |= s
    logger.debug(f"manysteps length: {len(sts.needswork)}")
    logger.debug(f"Final: {final}")

for result in final:
    print(f"{result};100%")
