import sys
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Self, cast

from abstraction import Abstraction, Comparison, SignSet
from interpreter import PC, Bytecode, Stack
from loguru import logger

import jpamb
from jpamb import jvm

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}", level="DEBUG")

@dataclass
class PerVarFrame[AV: Abstraction]:
    """
    Abstract frame at a SINGLE program point.

    Represents the abstract state of locals and stack at one PC.
    IMPORTANT: PC is stored here because we have a CALL STACK!
    When method A calls method B, we have:
      frames = [FrameA@PC_a, FrameB@PC_b]
    Each frame needs to track where it is in its own method.
    """

    locals: dict[int, AV]  # variable_index → abstract_value
    stack: Stack[AV]        # operand stack of abstract values
    pc: PC

    def __str__(self) -> str:
        locals_str = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals_str}}}, {self.stack}, {self.pc}>"

    @classmethod
    def from_method(cls, method: jvm.AbsMethodID) -> Self:
        """Create initial frame for a method entry."""
        return cls({}, Stack.empty(), PC(method, 0))

    def clone(self) -> "PerVarFrame[AV]":
        """Deep copy of the frame."""
        return PerVarFrame(
            locals=self.locals.copy(),
            stack=Stack(self.stack.items.copy()),
            pc=self.pc  # PC is immutable, safe to share
        )


@dataclass
class AState[AV: Abstraction]:
    """
    Complete abstract state of the program at ONE program point.

    Contains:
    - heap: abstract values at heap addresses
    - frames: call stack (multiple frames if methods are nested)
    - heap_ptr: next available heap address

    The "program point" is determined by the PC of the TOP frame.
    """

    heap: dict[int, AV]
    frames: Stack[PerVarFrame[AV]]
    heap_ptr: int = 0
    bc = Bytecode(jpamb.Suite(), {})

    def __ior__(self, other: "AState[AV]") -> Self:
        """
        In-place POINTWISE JOIN operation (⊔) for abstract states.

        "Pointwise" means: for each position/key, join the values at that position.

        We join:
        1. Heap: for each address, join the abstract values
        2. Frames: for each frame position in call stack, join the frame contents
           a. Locals: for each variable index, join the abstract values
           b. Stack: for each stack position, join the abstract values
        """
        assert isinstance(other, AState), f"expected AState but got {other}"
        assert (
            len(self.frames.items) == len(other.frames.items)
        ), f"frame stack sizes differ {self} != {other}"

        # Join heap POINTWISE (by address)
        for addr in other.heap:
            if addr in self.heap:
                self.heap[addr] = self.heap[addr] | other.heap[addr]
            else:
                self.heap[addr] = other.heap[addr]

        # Join frames POINTWISE (by call stack position)
        for f1, f2 in zip(self.frames.items, other.frames.items, strict=True):
            # Frames at same stack position must be at same PC
            # (otherwise program is malformed - different control flow paths
            # reached here with different call stacks)
            assert f1.pc == f2.pc, f"Program counters differ: {f1.pc} != {f2.pc}"

            # Join locals POINTWISE (by variable index)
            for var_idx in f2.locals:
                if var_idx in f1.locals:
                    f1.locals[var_idx] = f1.locals[var_idx] | f2.locals[var_idx]
                else:
                    f1.locals[var_idx] = f2.locals[var_idx]

            # Join stacks POINTWISE (by stack depth)
            # Stacks must have same length at same PC (type safety)
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
        """
        Current program counter = PC of the TOP frame.

        This is the "program point" where this state exists.
        Used as the key in StateSet.per_inst.
        """
        return self.frames.peek().pc

    def __str__(self) -> str:
        return f"{self.heap} {self.frames}"

    def clone(self) -> "AState[AV]":
        """Deep copy of the entire state."""
        return AState(
            heap=self.heap.copy(), # shallow copy of heap dict
            frames=Stack([deepcopy(f) for f in self.frames.items]),  # deep copy frames
            heap_ptr=self.heap_ptr
        )


@dataclass
class StateSet[AV: Abstraction]:
    """
    Container for the worklist algorithm.

    Maps each program point (PC) to the abstract state at that PC.
    Tracks which PCs need processing (needswork = worklist).

    This is the "Per-Instruction Abstraction" from theory:
      Pc = PC → 2^State
    But we only keep ONE abstract state per PC (the join of all states).
    """

    per_inst: dict[PC, AState[AV]]  # PC → AState
    needswork: set[PC]              # PCs that need reprocessing

    @classmethod
    def initialstate_from_method(cls, methodid: jvm.AbsMethodID,
                                 abstraction_cls: type[AV]) -> Self:
        """
        Create initial state set for analyzing a method.

        Sets up:
        1. Initial frame at method entry (PC = 0)
        2. Parameters initialized to TOP (unknown values)
        3. Initial state added to per_inst
        4. Entry PC added to needswork
        """
        frame = PerVarFrame[AV].from_method(methodid)
        params = methodid.extension.params

        # Initialize parameters to TOP (⊤ = any possible value)  # noqa: RUF003
        for i, p in enumerate(params):
            if isinstance(p, (jvm.Float, jvm.Double)):
                raise NotImplementedError("Only integer parameters supported")
            frame.locals[i] = abstraction_cls.top()

        state = AState[AV]({}, Stack.empty().push(frame))
        return cls(
            per_inst={frame.pc: state},
            needswork={frame.pc}
        )

    def per_instruction(self) -> Iterable[tuple[PC, AState[AV]]]:
        """
        Iterate over states that need processing.

        Pops from needswork and yields (pc, state) pairs.
        This implements the worklist algorithm's "pick next item" step.
        """
        while self.needswork:
            pc = self.needswork.pop()
            yield (pc, self.per_inst[pc])

    def __ior__(self, astate: AState[AV]) -> Self:
        """
        Join an abstract state into the state set.

        This is the KEY operation for the worklist algorithm!

        If PC doesn't exist: add the state
        If PC exists: JOIN (⊔) with existing state

        Add to needswork if the state CHANGED (not at fixed point yet).
        """
        pc = astate.pc

        if pc not in self.per_inst:
            # New PC: add state and mark for processing
            self.per_inst[pc] = astate.clone()
            self.needswork.add(pc)
        else:
            # Existing PC: must JOIN states!
            old = self.per_inst[pc]

            # Create new state by joining
            new_state = old.clone()
            new_state |= astate

            # Only update if state actually changed
            if new_state != old:
                self.per_inst[pc] = new_state
                self.needswork.add(pc)  # ← Must reprocess this PC
            # else: fixed point reached at this PC, don't add to needswork
        return self

    def __str__(self) -> str:
        return "\n".join(f"{pc}: {state}" for pc, state in self.per_inst.items())


def step[AV: Abstraction](state: AState[AV],
                          abstraction_cls: type[AV]) -> Iterable[AState[AV] | str]:
    """Execute ONE instruction in the abstract domain."""
    assert isinstance(state, AState), f"expected AState but got {state}"
    frame = state.frames.peek()
    opr = state.bc[frame.pc]
    logger.debug(f"STEP {opr}\n{state}")

    match opr:
        case jvm.Push(value=v):
            assert isinstance(v.value, int), f"Unsupported value type: {v.value!r}"
            frame.stack.push(abstraction_cls.abstract({v.value}))
            frame.pc = frame.pc + 1
            return [state]

        case jvm.Load(type=_type, index=i):
            assert i in frame.locals, f"Local variable {i} not initialized"
            frame.stack.push(frame.locals[i])
            frame.pc = frame.pc + 1
            return [state]

        case jvm.Ifz(condition=c, target=t):
            # Compare ONE value to zero
            # Stack: [..., value] → [...]

            # Pop the value being tested
            v1 = frame.stack.pop()
            assert isinstance(v1, abstraction_cls), f"Unexpected type: {v1}"
            v2 = abstraction_cls.abstract({0})
            # Clone state before modifying PC
            other = state.clone()
            # One path: continue to next instruction
            frame.pc = frame.pc + 1
            # Other path: jump to target
            other.frames.peek().pc = PC(frame.pc.method, t)

            res = v1.compare(cast("Comparison", c), v2)
            logger.debug(f"res: {res}")
            computed_states = []
            if True in res:
                computed_states.append(other)
            if False in res:
                computed_states.append(state)
            assert len(computed_states) > 0, "At least one path must be possible"
            return computed_states

        case jvm.If(condition=c, target=t):
            # Compare TWO values
            # Stack: [..., value1, value2] → [...]
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert isinstance(v1, abstraction_cls), f"Unexpected type: {v1}"
            assert isinstance(v2, abstraction_cls), f"Unexpected type: {v2}"
            # Clone state before modifying PC
            other = state.clone()
            # One path: continue to next instruction
            frame.pc = frame.pc + 1
            # Other path: jump to target
            other.frames.peek().pc = PC(frame.pc.method, t)
            res = v1.compare(cast("Comparison", c), v2)
            computed_states = []
            if True in res:
                    computed_states.append(other)
            if False in res:
                    computed_states.append(state)
            return computed_states

        case jvm.Return(type=type):
            new_state = state.clone()
            new_frame = new_state.frames.pop()

            if new_state.frames:
                caller_frame = new_state.frames.peek()
                if type is not None:
                    v1 = new_frame.stack.pop()
                    caller_frame.stack.push(v1)
                return [new_state]
            return ["ok"]

        case jvm.Binary(type=jvm.Int(), operant=operant):
            new_state = state.clone()
            new_frame = new_state.frames.peek()

            v2, v1 = new_frame.stack.pop(), new_frame.stack.pop()
            assert isinstance(v1, abstraction_cls), f"Unexpected type: {v1}"
            assert isinstance(v2, abstraction_cls), f"Unexpected type: {v2}"
            computed_states = []
            if (operant in (jvm.BinaryOpr.Div, jvm.BinaryOpr.Rem) and
                0 in v2):
                logger.debug("Division by zero found!")
                computed_states.append("divide by zero")
                if isinstance(v2, SignSet) and len(v2) == 1:
                    # No more options left
                    return computed_states

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
            new_frame.stack.push(v)

            new_frame.pc = PC(frame.pc.method, frame.pc.offset + 1)
            computed_states.append(new_state)
            return computed_states

        case jvm.Get(
            static=True,
            field=jvm.AbsFieldID(
                classname=_,
                extension=jvm.FieldID(name="$assertionsDisabled", type=jvm.Boolean()),
            ),
        ):
            new_state = state.clone()
            new_frame = new_state.frames.peek()
            new_frame.stack.push(abstraction_cls.abstract({0}))
            new_frame.pc = PC(frame.pc.method, frame.pc.offset + 1)
            return [new_state]

        case jvm.New(classname=jvm.ClassName(_as_string="java/lang/AssertionError")):
            logger.debug("Creating AssertionError object")
            return ["assertion error"]

        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")

def manystep[AV: Abstraction](sts: StateSet[AV],
                              abstraction_cls: type[AV]) -> Iterable[AState[AV] | str]:
    """
    Process all states in the worklist.

    For each state that needs work:
    1. Step it (execute one instruction)
    2. Collect all successor states

    Returns all successor states (to be joined back into StateSet).
    """
    states = []
    for _pc, state in sts.per_instruction():
        states.extend(step(state, abstraction_cls))
    return states


# ============================================================================
# Main Analysis
# ============================================================================

methodid = jpamb.getmethodid(
    "Abstract Interpreter",
    "0.1",
    "The Garbage Spillers",
    ["abstract interpretation", "sign analysis", "python"],
    for_science=True,
)

if methodid is None:
    logger.error("Method ID not found")
    methodid, case_input = jpamb.getcase()
else:
    params = methodid.extension.params

results: dict[str, int] = {
    "ok": 0,
    "assertion error": 0,
    "divide by zero": 0,
    "out of bounds": 0,
    "null pointer": 0,
    "*": 0,
}

AV = SignSet

MAX_STEPS = 1000
final: set[str] = set()

# Initialize with entry state
sts = StateSet[AV].initialstate_from_method(methodid, AV)
logger.debug(f"Initial state:\n{sts}")

# Worklist algorithm: iterate until fixed point (or max steps)
for iteration in range(MAX_STEPS):
    # Step all states that need processing
    for s in manystep(sts, AV):
        if isinstance(s, str):
            # Terminal state (ok/error)
            final.add(s)
        else:
            # Successor state: join into per_inst
            sts |= s

    logger.debug(f"Iteration {iteration}: {len(sts.needswork)} PCs need work")
    logger.debug(f"Final states: {final}")

    # If needswork is empty, we've reached fixed point
    if not sts.needswork:
        logger.debug("Fixed point reached!")
        break

# Output results
for result in results:
    if result in final:
        print(f"{result};100%")
    else:
        print(f"{result};0%")
