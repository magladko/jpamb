# Tool Flow Diagram - Markdown Plan

## Process Overview
A code analysis and rewriting tool that validates code transformations through static analysis and execution log comparison.

## Main Flow

### 1. Initial Processing
**Input:** Source code

The source code is processed through three parallel paths:

#### Path A: Syntactic Analysis
- Performs syntactic analysis on source code
- Outputs: Code insights

#### Path B: Execution Log Generation
- Generates execution log traces (dynamic analysis up to a fixed depth)
- Outputs: Unchanged code execution log

### 2. Triviality Check
**Decision Point:** Is case trivial?*

*Trivial = no method arguments, loops, nor recurrent calls

#### If Yes (Trivial):
- Proceeds to **Dynamic analysis**
- Outputs: Code coverage information

#### If No (Not Trivial):
- Proceeds to **Syntactically informed unbounded static analysis**
- Outputs: Code coverage information

### 3. Code Rewriting
Both paths (dynamic analysis and static analysis) feed into the **Code rewriter** along with:
- Code insights (from syntactic analysis)
- Code coverage information

**Output:** Debloated source

### 4. Validation Phase
- **Generate execution log traces** for the debloated code
- Outputs: Debloated code execution log

### 5. Log Comparison
Both execution logs are compared:
- Unchanged code execution log
- Debloated code execution log

**Decision Point:** Log changed?

#### If Yes (Logs Different):
- Process **FAILS** ✗
- Indicates the code transformation altered behavior

#### If No (Logs Identical):
- Proceeds to **Persist rewritten code**
- Process **COMPLETES** ⊙

## Key Components Summary
1. **Syntactic analysis** - analyzes code structure
2. **Generate execution log traces** - captures runtime behavior
3. **Dynamic analysis** - for trivial cases
4. **Syntactically informed unbounded static analysis** - for complex cases
5. **Code rewriter** - performs debloating transformation
6. **Log comparison** - validates behavior preservation
7. **Persist rewritten code** - saves validated output