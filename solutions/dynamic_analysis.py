import random
import sys

from interpreter import Frame, Stack, State, step, type_stack_to_heap
from loguru import logger

import jpamb
from jpamb import jvm

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}", level="DEBUG")

MOCKUP_ARRAY_LENGTH = (0, 50)
JRANGES = {
    jvm.Byte():    (-2**7, 2**7-1),
    jvm.Short():   (-2**15, 2**15-1),
    # jvm.Int():     (-2**31, 2**31-1),
    jvm.Int():     (-100, 100),
    jvm.Long():    (-2**63, 2**63-1),
    jvm.Float():   (-(2-2**(-23))*2**127, (2-2**(-23))*2**127),
    jvm.Double():  (-(2-2**(-52))*2**1023, (2-2**(-52))*2**1023),
    jvm.Char():    (0, 2**16-1),
    jvm.Boolean(): (0, 1),
}

def gen_value(t: jvm.Type) -> jvm.Value:
    match t:
        case jvm.Float() | jvm.Double():
            return jvm.Value(t, random.uniform(*JRANGES[t]))
        case jvm.Byte() | jvm.Short() | jvm.Int() | jvm.Long() | \
             jvm.Char() | jvm.Boolean():
            return jvm.Value(t, random.randint(*JRANGES[t]))
        # case jvm.Array():
        #     return tuple(gen_value(t.contains)
        #                  for _ in range(random.randint(
        #                      *MOCKUP_ARRAY_LENGTH)))
        case _:
            raise NotImplementedError(f"Value generation not implemented for type {t!r}")

# import debugpy
# debugpy.listen(5678)
# logger.debug("Waiting for debugger attach")
# debugpy.wait_for_client()

methodid = jpamb.getmethodid(
    "Interpreter",
    "1.0",
    "Garbage Spillers",
    ["random", "dynamic", "python"],
    for_science=True,
)

results: dict[str, int] = {
    "ok": 0,
    "assertion error": 0,
    "divide by zero": 0,
    "out of bounds": 0,
    "null pointer": 0,
    "*": 0,
}

params = len(methodid.extension.params._elements) > 0


def execute(methodid: jvm.AbsMethodID, max_steps: int = 1000) -> str:

    frame = Frame.from_method(methodid)
    state = State({}, Stack.empty().push(frame))

    # Initialize locals, if there are any parameters
    for i, t in enumerate(methodid.extension.params._elements):
        match t:
            case jvm.Array():
                ref = jvm.Value(jvm.Reference(), state.heap_ptr)
                state.heap[state.heap_ptr] = jvm.Value.array(
                    t,
                    tuple(
                        type_stack_to_heap(gen_value(t.contains)).value
                        for _ in range(random.randint(*MOCKUP_ARRAY_LENGTH)))
                )
                state.heap_ptr += 1
                v = ref
            case _:
                v = gen_value(t)
                assert isinstance(v, jvm.Value)
        frame.locals[i] = v

    for _ in range(max_steps):
        state = step(state)
        if isinstance(state, str):
            return state
    return "*"

result = execute(methodid)

if not params:
    [print(f"{r};0%") for r in results.keys() if r != result]
    if result == "*":
        print(f"{result};99%")
    else:
        print(f"{result};100%")
else:
    results[result] += 1
    total = 1
    for _ in range(10):
        r = execute(methodid)
        results[r] += 1
        total += 1

    [print(f"{k};{max((v * 100) // total, 20)}%") for k, v in results.items()]
    # print(f"{result};99%")
