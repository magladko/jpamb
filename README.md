# JPAMB: Java Program Analysis Micro Benchmarks

## What is this?

JPAMB is a collection of small Java programs with various behaviors (crashes, infinite loops, normal completion). Your task is to build a program analysis tool that can predict what will happen when these programs run.

Think of it like a fortune teller for code: given a Java method, can your analysis predict if it will crash, run forever, or complete successfully?

## Quick Links

- **[uv documentation](https://docs.astral.sh/uv/)** - Python package manager we use
- **[Tree-sitter Java](https://tree-sitter.github.io/tree-sitter/using-parsers)** - For parsing Java source code
- **[JVM2JSON codec](https://github.com/kalhauge/jvm2json/blob/main/CODEC.txt)** - Understanding bytecode format
- **[Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)** - Windows C++ compiler
- **[JPAMB GitHub Issues](https://github.com/kalhauge/jpamb/issues)** - Get help if stuck

## Setup 

### Step 1: Install GCC (required for compilation)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install build-essential
```

**Windows:**
```bash
# Install Microsoft Visual C++ 14.0 (required for Python C extensions)
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Or install via Visual Studio Installer and select "C++ build tools"

# Alternative: Install Visual Studio Community (includes build tools)
winget install Microsoft.VisualStudio.2022.Community
```

**Mac:**
```bash
# Install Xcode command line tools
xcode-select --install
```

### Step 2: Install uv (Python package manager)
```bash
# On Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Important:** Restart your terminal/command prompt after installing uv!

### Step 3: Install JPAMB
```bash
# Navigate to this directory and run:
uv tool install -e ./lib
```

### Step 4: Verify everything works
```bash
uvx jpamb checkhealth
```
You should see several green "ok" messages. If you see any red errors, check troubleshooting below!

## How It Works

### Your Task
Build a program that analyzes Java methods and predicts what will happen when they run.

### Your Program Must Support Two Commands:

**1. Info command** - tells us about your analyzer:
```bash
./your_analyzer info
```
This should output 5 lines:
- Your analyzer's name
- Version number  
- Your team/group name
- Tags describing your approach (e.g., "static,dataflow")
- Either your system info (to help us improve) or "no" (for privacy)

**2. Analysis command** - makes predictions:
```bash
./your_analyzer "jpamb.cases.Simple.divideByZero:()I"
```

### What Can Happen to Java Methods?

Your analyzer predicts these possible outcomes:

| Outcome | What it means |
|---------|---------------|
| `ok` | Method runs and finishes normally |
| `divide by zero` | Method tries to divide by zero |
| `assertion error` | Method fails an assertion (like `assert x > 0`) |
| `out of bounds` | Method accesses array outside its bounds |
| `null pointer` | Method tries to use a null reference |
| `*` | Method runs forever (infinite loop) |

### Making Predictions

For each outcome, you give either:
- **A percentage**: `75%` means "75% confident this will happen"
- **A wager**: `5` means "bet 5 points this will happen", `-10` means "bet 10 points this WON'T happen"

**Example output:**
```
ok;80%
divide by zero;20%
assertion error;0%
out of bounds;0%
null pointer;0%
*;0%
```


## Your First Analyzer

### Step 1: Look at Example Java Code
Check out the test cases in `src/main/java/jpamb/cases/Simple.java` - these are the methods your analyzer will predict.

### Step 2: Create Your First Analyzer
Create a file called `my_analyzer.py`:

```python
#!/usr/bin/env python3
import sys

if len(sys.argv) == 2 and sys.argv[1] == "info":
    # Info mode - tell JPAMB about your analyzer
    print("My First Analyzer")        # name
    print("1.0")                      # version  
    print("Student Name")             # group/team
    print("simple,python")            # tags
    print("no")                       # privacy mode - use "yes" to share system info to help us improve
else:
    # Analysis mode - make predictions
    method_name = sys.argv[1]
    
    # Simple strategy: guess everything just works
    print("ok;90%")
    print("divide by zero;10%") 
    print("assertion error;5%")
    print("out of bounds;0%")
    print("null pointer;0%")
    print("*;0%")
```

Make it executable:
```bash
# Linux/Mac:
chmod +x my_analyzer.py

# Windows: No need - Python files run directly
```

### Step 3: Test Your Analyzer
```bash
# Test on just the Simple cases to start
# Linux/Mac/Windows (all the same):
uvx jpamb test --filter "Simple" python my_analyzer.py
```

You should see output showing scores for each test case. Don't worry about the scores yet - focus on getting it working!

### Step 4: Improve Your Analyzer
Now look at the Java code and try to make better predictions. For example:
- If you see `1/0` in the code, predict `divide by zero;100%`
- If you see `assert false`, predict `assertion error;100%`
- If you see `while(true)`, predict `*;100%` (infinite loop)

## Scoring (Advanced)

**For most assignments, you can ignore this section and just use percentages!**

Instead of percentages, you can use **wagers** (betting points):
- Positive wager (e.g., `divide by zero;5`) means "I bet 5 points this WILL happen"  
- Negative wager (e.g., `divide by zero;-10`) means "I bet 10 points this WON'T happen"
- Higher wagers = higher risk/reward

The scoring formula: `points = 1 - 1/(wager + 1)` if you win, `-wager` if you lose.

## Testing Your Analyzer

```bash
# Test on simple cases first
uvx jpamb test --filter "Simple" python my_analyzer.py

# Test on all cases  
uvx jpamb test python my_analyzer.py

# Generate final evaluation report
uvx jpamb evaluate python my_analyzer.py > my_results.json
```

## Advanced: Analyzing Approaches

### Source Code Analysis
- Java source code is in `src/main/java/jpamb/cases/`
- Example: `solutions/syntaxer.py` uses tree-sitter to parse Java

### Bytecode Analysis  
- Pre-decompiled JVM bytecode in `decompiled/` directory
- Example: `solutions/bytecoder.py` analyzes JVM opcodes
- Python interface: `lib/jpamb/jvm/opcode.py`

### Statistics-Based
- Historical data in `stats/distribution.csv`
- Example: `solutions/apriori.py` uses statistical patterns

## Troubleshooting

**"Command not found" errors:**
- Make sure you restart your terminal after installing uv
- Try `which uvx` to see if it's installed correctly

**"Health check fails":**
- Make sure you're in the jpamb directory
- Make sure GCC is installed (Step 1 above)
- Try `mvn compile` to build the Java code first

**"Permission denied" when running analyzer:**
- Linux/Mac: Use `chmod +x my_analyzer.py` to make it executable
- All platforms: Use `python my_analyzer.py` instead of `./my_analyzer.py`

**Windows users:**
- Use PowerShell or Command Prompt
- Replace `/` with `\` in file paths if needed
- Consider using [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) for easier setup

**Still stuck?** Check the example solutions in `solutions/` directory or ask for help!
