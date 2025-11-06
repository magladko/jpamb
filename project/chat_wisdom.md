# Abstract Interpretation Architecture Explained

## The Confusion: Theory vs Practice

The course materials describe a theoretical framework, but your implementation needs a slightly different structure. Let me clarify both and show how they relate.

---

## Theoretical Framework (from the papers)

### Trace Semantics → State Semantics → Per-Instruction → Per-Variable

```
Level 0: Concrete Traces
    Set of traces: 2^Trace
    Each trace: τ = [s₀, s₁, s₂, ...]
    Each state: s = ⟨σ, λ, ι⟩  (locals, stack, PC)

Level 1: State Abstraction
    Just keep final states: 2^State
    α(T) = {last_state(τ) | τ ∈ T}

Level 2: Per-Instruction Abstraction  
    Group states by PC: Pc = PC → 2^State
    {pc₁ → {state₁, state₂}, pc₂ → {state₃}, ...}

Level 3: Per-Variable Abstraction
    Abstract each variable independently: Pv = PC → AbstractFrame
    AbstractFrame = (ℕ → AbstractValue) × (AbstractValue)*
                    ^^^^locals^^^^         ^^^^stack^^^^
```

---

## Your Implementation Architecture (CORRECTED)

### Three-Layer Structure

```python
# Layer 1: Abstract Values (lowest level)
class SignSet(Abstraction):
    """Single abstract value (e.g., {Pos, Neg, Zero})"""
    values: set[Sign]
    
    def __or__(self, other):  # Join operation
        return SignSet(self.values | other.values)

# Layer 2: Abstract Frame (single program point)
class PerVarFrame[AV]:
    """Abstract state at ONE specific PC"""
    locals: dict[int, AV]           # var_index → abstract_value
    stack: Stack[AV]                # list of abstract_values
    pc: PC                          # WHERE this frame is
    
    # NOTE: PC IS needed here because frames are part of call stack!

# Layer 3: Abstract State (complete program state)
class AState[AV]:
    """Complete abstract state of the program"""
    heap: dict[int, AV]             # heap_addr → abstract_value
    frames: Stack[PerVarFrame[AV]]  # call stack of frames
    
    @property
    def pc(self) -> PC:
        """Current PC = PC of top frame"""
        return self.frames.peek().pc

# Layer 4: State Set (worklist algorithm container)
class StateSet[AV]:
    """Maps each PC to the abstract state at that PC"""
    per_inst: dict[PC, AState[AV]]  # PC → AState
    needswork: set[PC]              # PCs that need processing
```

---

## Key Insights: Why PC is in Multiple Places

### The Call Stack Problem

The theory assumes **no method calls** (flat control flow). Your implementation has:

```
Method A (PC=5) calls Method B (PC=0)
  → Need stack: [Frame_A@PC5, Frame_B@PC0]
```

**Each frame needs its own PC** because you have nested execution contexts!

### Two Meanings of PC

1. **Frame PC**: "Where am I in this method?"
   - Stored IN the frame
   - Changes as we step through method

2. **State PC**: "Where am I in the program?"
   - Derived from top frame: `state.pc = state.frames.peek().pc`
   - Used as key in `per_inst` dictionary

---

## The Pointwise Join - FINALLY CLEAR

### At StateSet Level (Layer 4)

```python
# StateSet: dict[PC, AState]
stateset1.per_inst = {
    pc₁: astate_A,  # State at program point 1
    pc₂: astate_B,  # State at program point 2
}

stateset2.per_inst = {
    pc₁: astate_C,  # Another state at program point 1
    pc₃: astate_D,  # State at program point 3
}

# Pointwise join = join at each PC independently
result.per_inst = {
    pc₁: astate_A |= astate_C,  # Join states at same PC
    pc₂: astate_B,               # Only in first
    pc₃: astate_D,               # Only in second
}
```

### At AState Level (Layer 3)

```python
# When joining two AStates at the SAME PC:
astate1 |= astate2

# Join heap pointwise (by address)
for addr in astate2.heap:
    if addr in astate1.heap:
        astate1.heap[addr] |= astate2.heap[addr]
    else:
        astate1.heap[addr] = astate2.heap[addr]

# Join frames pointwise (by stack position)
for f1, f2 in zip(astate1.frames, astate2.frames):
    # Join locals pointwise (by variable index)
    for var_idx in f2.locals:
        if var_idx in f1.locals:
            f1.locals[var_idx] |= f2.locals[var_idx]
        else:
            f1.locals[var_idx] = f2.locals[var_idx]
    
    # Join stacks pointwise (by stack depth)
    for i in range(len(f1.stack)):
        f1.stack[i] |= f2.stack[i]
```

**"Pointwise" = for each position/key, join the values at that position**

---

## Your Code Issues

### Issue 1: PerVarFrame.__str__ references self.pc

```python
# CURRENT (BROKEN):
def __str__(self) -> str:
    return f"<{{{locals_str}}}, {self.stack}, {self.pc}>"
    #                                          ^^^^^^^^ Uses it

# But commented out:
# pc: PC  ← commented out!

# FIX: Uncomment the pc field!
@dataclass
class PerVarFrame[AV: Abstraction]:
    locals: dict[int, AV]
    stack: Stack[AV]
    pc: PC  # ← UNCOMMENT THIS
```

### Issue 2: PerVarFrame.from_method creates PC but doesn't store it

```python
# CURRENT (BROKEN):
@classmethod
def from_method(cls, method: jvm.AbsMethodID) -> Self:
    return cls({}, Stack.empty(), PC(method, 0))
    #                             ^^^^^^^^^^^^^^ Creates PC but field is commented out!

# FIX: This will work once pc field is uncommented
```

### Issue 3: StateSet.__ior__ logic is confusing

```python
# CURRENT:
def __ior__(self, astate: AState) -> Self:
    pc = astate.pc
    old = self.per_inst.get(pc)
    if old is None:
        self.per_inst[pc] = astate
        self.needswork.add(pc)
    else:
        new = astate  # This is confusing
        if new != old:
            self.per_inst[pc] = new  # WRONG: should join!
            self.needswork.add(pc)
    return self

# CORRECTED:
def __ior__(self, astate: AState[AV]) -> Self:
    """Join an abstract state into the state set."""
    pc = astate.pc
    
    if pc not in self.per_inst:
        # New PC: just add it
        self.per_inst[pc] = astate.clone()
        self.needswork.add(pc)
    else:
        # Existing PC: join with existing state
        old = self.per_inst[pc]
        new_state = old.clone()
        new_state |= astate  # Join operation
        
        # Only update if something changed
        if new_state != old:
            self.per_inst[pc] = new_state
            self.needswork.add(pc)
    
    return self
```

---

## The Complete Picture

```
Program Execution:
┌──────────────────────────────────────────────────┐
│ StateSet (worklist algorithm)                    │
│ ┌──────────────────────────────────────────────┐ │
│ │ per_inst: dict[PC, AState]                   │ │
│ │   pc₁ → AState₁                              │ │
│ │   pc₂ → AState₂                              │ │
│ │   pc₃ → AState₃                              │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ Each AState contains:                            │
│ ┌──────────────────────────────────────────────┐ │
│ │ heap: {addr₁ → SignSet, addr₂ → SignSet}    │ │
│ │ frames: Stack of PerVarFrames                │ │
│ │   [Frame₁@pc_a, Frame₂@pc_b, ...]           │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ Each PerVarFrame contains:                       │
│ ┌──────────────────────────────────────────────┐ │
│ │ locals: {0 → SignSet, 1 → SignSet}          │ │
│ │ stack: [SignSet, SignSet, ...]              │ │
│ │ pc: PC(method, offset)                       │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘

Worklist Algorithm:
1. Start with initial state at entry PC
2. While needswork is not empty:
   a. Pop a PC from needswork
   b. Get state at that PC
   c. Step that state (execute one instruction)
   d. For each resulting state:
      - Join it into per_inst at its PC
      - If changed, add that PC to needswork
3. Fixed point reached when needswork is empty
```

---

## Critical Fixes Needed

### 1. Uncomment the PC field in PerVarFrame
```python
@dataclass
class PerVarFrame[AV: Abstraction]:
    locals: dict[int, AV]
    stack: Stack[AV]
    pc: PC  # ← UNCOMMENT THIS LINE
```

### 2. Fix StateSet.__ior__ to actually JOIN states
```python
def __ior__(self, astate: AState[AV]) -> Self:
    pc = astate.pc
    if pc not in self.per_inst:
        self.per_inst[pc] = astate.clone()
        self.needswork.add(pc)
    else:
        old = self.per_inst[pc]
        new_state = old.clone()
        new_state |= astate  # ← ACTUAL JOIN
        if new_state != old:
            self.per_inst[pc] = new_state
            self.needswork.add(pc)
    return self
```

### 3. Make sure clone() creates deep copies
Your current clone looks good, but verify that `Stack` has proper copying.

---

## Why This Is Confusing

The theory papers describe:
- **Flat programs** (no method calls)
- **Single frame** per state
- **PC separate** from frame

Your implementation needs:
- **Method calls** (call stack)
- **Multiple frames** per state
- **PC in each frame** (because call stack)

This is the right approach for a real implementation!

---

## Summary

**Pointwise join** means: **for each key/position, independently join the values at that position**

- StateSet: pointwise over PCs
- AState: pointwise over heap addresses and frame positions
- Frame: pointwise over variable indices and stack positions
- AbstractValue: join the abstract domains (e.g., Sign ⊔ Sign)

Your architecture is fundamentally correct, you just need:
1. Uncomment `pc: PC` in PerVarFrame
2. Fix the join logic in StateSet.__ior__
3. Ensure proper cloning to avoid aliasing issues