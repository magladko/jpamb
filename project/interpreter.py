from dataclasses import dataclass
from typing import Self

from loguru import logger

import jpamb
from jpamb import jvm

# methodid, input = jpamb.getcase()


@dataclass
class PC:
    method: jvm.AbsMethodID
    offset: int

    def __iadd__(self, delta: int) -> Self:
        self.offset += delta
        return self

    def __add__(self, delta: int) -> "PC":
        return PC(self.method, self.offset + delta)

    def __str__(self) -> str:
        return f"{self.method}:{self.offset}"


@dataclass
class Bytecode:
    suite: jpamb.Suite
    methods: dict[jvm.AbsMethodID, list[jvm.Opcode]]

    def __getitem__(self, pc: PC) -> jvm.Opcode:
        try:
            opcodes = self.methods[pc.method]
        except KeyError:
            opcodes = list(self.suite.method_opcodes(pc.method))
            self.methods[pc.method] = opcodes

        return opcodes[pc.offset]


@dataclass
class Stack[T]:
    items: list[T]

    def __bool__(self) -> bool:
        return len(self.items) > 0

    @classmethod
    def empty(cls) -> "Stack[T]":
        return cls([])

    def peek(self) -> T:
        return self.items[-1]

    def pop(self) -> T:
        return self.items.pop(-1)

    def push(self, value: T) -> Self:
        self.items.append(value)
        return self

    def __str__(self) -> str:
        if not self:
            return "ϵ"
        return "".join(f"{v}" for v in self.items)


@dataclass
class Frame:
    locals: dict[int, jvm.Value]
    stack: Stack[jvm.Value]
    pc: PC

    def __str__(self) -> str:
        locals_str = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals_str}}}, {self.stack}, {self.pc}>"

    @classmethod
    def from_method(cls, method: jvm.AbsMethodID) -> "Frame":
        return Frame({}, Stack.empty(), PC(method, 0))


@dataclass
class State:
    heap: dict[int, jvm.Value]
    frames: Stack[Frame]

    heap_ptr: int = 0
    bc = Bytecode(jpamb.Suite(), {})

    def __str__(self) -> str:
        return f"{self.heap} {self.frames}"


def step(state: State) -> State | str:  # noqa: C901, PLR0911, PLR0912, PLR0915
    assert isinstance(state, State), f"expected frame but got {state}"
    frame = state.frames.peek()
    opr = state.bc[frame.pc]
    logger.debug(f"STEP {opr}\n{state}")
    match opr:
        case jvm.Push(value=v):
            if isinstance(v.type, jvm.Array):
                state.heap[state.heap_ptr] = v
                v = jvm.Value(jvm.Reference(), state.heap_ptr)
                state.heap_ptr += 1
            frame.stack.push(v)
            frame.pc += 1
            return state
        case jvm.Load(type=type, index=i):
            assert i in frame.locals, f"Local variable {i} not initialized"
            v = frame.locals[i]
            frame.stack.push(frame.locals[i])
            frame.pc += 1
            return state
        case jvm.Binary(type=jvm.Int(), operant=operant):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert v1.type is jvm.Int(), f"expected int, but got {v1}"
            assert v2.type is jvm.Int(), f"expected int, but got {v2}"
            assert isinstance(v1.value, int)
            assert isinstance(v2.value, int)

            v = None
            match operant:
                case jvm.BinaryOpr.Div:
                    if v2.value == 0:
                        return "divide by zero"
                    v = jvm.Value.int(v1.value // v2.value)
                case jvm.BinaryOpr.Rem:
                    if v2.value == 0:
                        return "divide by zero"
                    v = jvm.Value.int(v1.value % v2.value)
                case jvm.BinaryOpr.Sub:
                    v = jvm.Value.int(v1.value - v2.value)
                case jvm.BinaryOpr.Mul:
                    v = jvm.Value.int(v1.value * v2.value)
                case jvm.BinaryOpr.Add:
                    v = jvm.Value.int(v1.value + v2.value)
                case _:
                    raise NotImplementedError(f"Operand '{operant!r}' not implemented.")
            frame.stack.push(v)
            frame.pc += 1
            return state
        case jvm.Return(type=type):
            state.frames.pop()
            if state.frames:
                caller_frame = state.frames.peek()
                if type is not None:
                    v1 = frame.stack.pop()
                    caller_frame.stack.push(v1)
                return state
            return "ok"
        case jvm.Get(
            static=True,
            field=jvm.AbsFieldID(
                classname=_,
                extension=jvm.FieldID(name="$assertionsDisabled", type=jvm.Boolean()),
            ),
        ):
            frame.stack.push(type_heap_to_stack(jvm.Value.boolean(False)))  # noqa: FBT003
            frame.pc += 1
            return state
        case jvm.Ifz(condition=condition, target=target):
            v = frame.stack.pop()
            if compare(v, condition, jvm.Value.int(0)):
                frame.pc.offset = target
            else:
                frame.pc += 1
            return state
        case jvm.If(condition=condition, target=target):
            v2, v1 = frame.stack.pop(), frame.stack.pop()

            if compare(v1, condition, v2):
                frame.pc.offset = target
            else:
                frame.pc += 1
            return state
        case jvm.New(classname=jvm.ClassName(_as_string="java/lang/AssertionError")):
            return "assertion error"
        case jvm.NewArray(type=type, dim=_):
            count = frame.stack.pop()
            assert count.type is jvm.Int()
            assert isinstance(count.value, int)
            if count.value < 0:
                return "NegativeArraySizeException"
            default = 0
            if type is jvm.Boolean():
                default = False
            arr = [default] * count.value
            state.heap[state.heap_ptr] = jvm.Value.array(type, arr)
            frame.stack.push(jvm.Value(type=jvm.Reference(), value=state.heap_ptr))
            state.heap_ptr += 1
            frame.pc += 1
            return state
        case jvm.ArrayLength():
            ref = frame.stack.pop()
            arr = None
            if ref.type is jvm.Reference():
                if ref.value is None:
                    return "null pointer"
                assert isinstance(ref.value, int), (
                    f"Expected int, but got {ref.value!r}"
                )
                arr = state.heap[ref.value].value
            elif isinstance(ref.type, jvm.Array):
                arr = ref.value
            else:
                raise ValueError(f"Unexpected ref type got: {ref.type!r}")

            assert isinstance(arr, tuple)

            frame.stack.push(jvm.Value.int(len(arr)))
            frame.pc += 1
            return state
        case jvm.ArrayStore(type=type):
            val, idx, ref = frame.stack.pop(), frame.stack.pop(), frame.stack.pop()
            # TODO(kornel): if ref is null -> throw null_ptr exception
            assert ref.type is jvm.Reference()
            assert val.type is jvm.Int()
            assert idx.type is jvm.Int()

            if ref.value is None:
                return "null pointer"

            assert isinstance(ref.value, int)
            assert isinstance(val.value, int)
            assert isinstance(idx.value, int)

            arr = state.heap[ref.value].value
            assert isinstance(arr, tuple)

            if idx.value < 0 or idx.value >= len(arr):
                return "out of bounds"

            state.heap[ref.value] = jvm.Value.array(
                type,
                (
                    *arr[: idx.value],
                    type_stack_to_heap(jvm.Value(type, val.value)).value,
                    *arr[idx.value + 1 :],
                ),
            )

            frame.pc += 1
            return state
        case jvm.ArrayLoad(type=type):
            idx, arr = frame.stack.pop(), frame.stack.pop()
            assert idx.type is jvm.Int()
            assert isinstance(idx.value, int)

            if isinstance(arr.type, jvm.Array):
                arr = arr.value
            elif isinstance(arr.type, jvm.Reference):
                assert isinstance(arr.value, int)
                arr = state.heap[arr.value].value
            else:
                raise TypeError(f"Unexpected ref type got: {arr.type!r}")

            assert isinstance(arr, tuple)
            if idx.value < 0 or idx.value >= len(arr):
                return "out of bounds"

            frame.stack.push(
                type_heap_to_stack(jvm.Value(type=type, value=arr[idx.value]))
            )
            # jvm.Value(type=type, value=arr[idx.value]))
            frame.pc += 1
            return state
        case jvm.Dup(words=1):
            assert len(frame.stack.items) > 0, "Unexpected empty stack"
            frame.stack.push(frame.stack.peek())
            frame.pc += 1
            return state
        case jvm.Store(type=type, index=index):
            v = frame.stack.pop()
            if v and v.value is not None:
                assert isinstance(v.value, int), (
                    f"Expected type {int}, but got {v.value!r}"
                )
            frame.locals[index] = v
            frame.pc += 1
            return state
        case jvm.Goto(target=target):
            frame.pc.offset = target
            return state
        case jvm.Incr(index=i, amount=amount):
            local_var = frame.locals[i].value
            assert isinstance(local_var, int)
            frame.locals[i] = jvm.Value.int(local_var + amount)
            frame.pc += 1
            return state
        case jvm.InvokeStatic(method=m):
            nargs = len(m.extension.params)
            args = [frame.stack.pop() for _ in range(nargs)][::-1]
            new_frame = Frame.from_method(m)
            for i, v in enumerate(args):
                new_frame.locals[i] = v
            state.frames.push(new_frame)
            frame.pc += 1
            return state
        case jvm.Cast(from_=from_, to_=to_):
            # TODO(kornel): make lossful casts
            v = frame.stack.pop()
            assert v.type is from_, f"Expected type {from_!r}, but got {v.type!r}"
            v = jvm.Value(to_, v.value)
            frame.stack.push(v)
            frame.pc += 1
            return state
        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")


def compare(v1: jvm.Value, op: str, v2: jvm.Value) -> bool:
    assert isinstance(v1.value, (int, float)), f"Unexpected value {v1.value!r}"
    assert isinstance(v2.value, (int, float)), f"Unexpected value {v2.value!r}"

    match op:
        case "eq":
            return v1.value == v2.value
        case "ge":
            return v1.value >= v2.value
        case "gt":
            return v1.value > v2.value
        case "le":
            return v1.value <= v2.value
        case "lt":
            return v1.value < v2.value
        case "ne":
            return v1.value != v2.value
        case c:
            raise NotImplementedError(f"Comparison not implemented for condition {c}")


def type_stack_to_heap(val: jvm.Value) -> jvm.Value:
    match val.type:
        case jvm.Int() | jvm.Float() | jvm.Reference():
            return val
        case jvm.Boolean():
            assert isinstance(val.value, int)
            return jvm.Value(jvm.Boolean(), bool(val.value != 0))
        case jvm.Char():
            assert isinstance(val.value, int)
            return jvm.Value(jvm.Char(), chr(val.value))
        case jvm.Array():
            raise NotImplementedError(
                "Stack to heap conversion not implemented for arrays"
            )
        case _:
            raise NotImplementedError(
                f"Stack to heap conversion not implemented for {val.type!r}"
            )


def type_heap_to_stack(val: jvm.Value) -> jvm.Value:
    match val.type:
        case jvm.Int() | jvm.Float() | jvm.Reference():
            return val
        case jvm.Boolean():
            assert isinstance(val.value, bool), f"Expected bool, but got {val.value!r}"
            return jvm.Value(jvm.Boolean(), (1 if val.value else 0))
        case jvm.Char():
            assert isinstance(val.value, str), f"Expected str, but got {val.value!r}"
            return jvm.Value(jvm.Char(), ord(val.value))
        case jvm.Array():
            raise NotImplementedError(
                "Heap to stack conversion not implemented for arrays"
            )
        case _:
            raise NotImplementedError(
                f"Heap to stack conversion not implemented for {val.type!r}"
            )
