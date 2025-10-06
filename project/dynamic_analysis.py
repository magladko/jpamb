import random
import sys

from interpreter import Frame, Stack, State, step, type_stack_to_heap
from loguru import logger

import jpamb
from jpamb import jvm
from syntactic_helper import SyntacticHelper

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}", level="DEBUG")

MAX_EXEC_STEPS        = 1000
ARGS_REROLL           = 50
ARG_GUESS_LOWER_LIMIT = 20

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

params = methodid.extension.params
params_present = len(methodid.extension.params) > 0

sh = SyntacticHelper()
interesting_values = sh.find_interesting_values(methodid)
logger.debug(f"interesting values: {interesting_values}")
# assert False

# Currently - random value selected indepentently for each argument
# TODO: Prepare input sets for multiple executions

# Generate domain
# for t in params:

def execute(methodid: jvm.AbsMethodID, max_steps: int = 1000) -> str:

    frame = Frame.from_method(methodid)
    state = State({}, Stack.empty().push(frame))

    # Initialize locals, if there are any parameters
    for i, t in enumerate(params):
        vals = [v for v in interesting_values if v.type == t]
        logger.debug(f"vals: {vals}")
        match t:
            case jvm.Array():
                ref = jvm.Value(jvm.Reference(), state.heap_ptr)
                arr_vals = tuple()
                rr = range(random.randint(*MOCKUP_ARRAY_LENGTH))
                if len(vals) > 0:
                    arr_vals = tuple(random.choice(vals).value for _ in rr)
                else:
                    arr_vals = tuple(
                        type_stack_to_heap(gen_value(t.contains)).value 
                        for _ in rr)
                state.heap[state.heap_ptr] = jvm.Value.array(t, arr_vals)
                
                logger.debug(f"Arr: {state.heap[state.heap_ptr]}")

                state.heap_ptr += 1
                v = ref
            case _:
                v = random.choice(vals) if len(vals) > 0 else gen_value(t)
                logger.debug(f"v: {v}")
                assert isinstance(v, jvm.Value)
        frame.locals[i] = v

    for _ in range(max_steps):
        state = step(state)
        if isinstance(state, str):
            return state
    return "*"

result = execute(methodid, MAX_EXEC_STEPS)#, 0)

if not params_present:
    if result == "*":
        [print(f"{r};0%") for r in results.keys() if r not in (result, "ok") ]
        print(f"{result};99%")
        print("ok;1%")
    else:
        [print(f"{r};0%") for r in results.keys() if r != result]
        print(f"{result};100%")
else:
    results[result] += 1
    total = 1
    for _ in range(ARGS_REROLL):
        r = execute(methodid)
        results[r] += 1
        total += 1

    [print(f"{k};{((v * (100-ARG_GUESS_LOWER_LIMIT)) // total + ARG_GUESS_LOWER_LIMIT)}%") 
     for k, v in results.items()]
    # print(f"{result};99%")
