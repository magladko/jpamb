# JPAMB: Java Program Analysis Micro Benchmarks

The goal of this benchmark suite is to make a collection of interesting
micro-benchmarks to be solved by some program analysis.

## Installing

To get started you need to first install Python on your system. 
The easiest way to do that is by downloading and running the `uv` package manager. 
Please see the [instructions](https://docs.astral.sh/uv/getting-started/installation/) for how 
to get setup.


First you should build the repository:

```bash
$> uv build
```

After which you should be able to run the tool using the following command, which should spit out a number of checks, that all should be green.
```bash
$> uv run jpamb checkhealth
```

You should also check that prebuild analyses work: 
```bash
$> uv run solutions/apriori.py info
<lines of info>
```

Which should allow you to run the tool like this:
```bash
$> uv run jpamb test uv run solutions/apriori.py
<lines of information>
```

### Giving Your Analysis Access to JPAMB

It is possible to add the `jpamb` dependencies to a python script by running 
the following command:

```bash
$> uv add --editable --script=your_analysis.py .
```

You can even add other dependencies you might need:

```bash
$> uv add --script=your_analysis.py z3-solver
```

Now you can run it from anywhere like so:

```bash
$> uv run --script your_analysis.py info
```

## Troubleshooting

Here is a list of common problems you might encounter while running the code.

### Windows: C++ version 14 not installed.

Download the requested upgrader and make sure to press "modify" before installing 
and add the C++ tools to the tool-chain.


## Rules of the Game

The goal is to build a program analysis that takes a method ID as an argument, and 
returns a list of lines, each line consisting of a query and a prediction separated by semicolon `;`.
A method ID is the fully qualified name of the class, the method name, ":", and 
then the [method descriptor](https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-4.html#jvms-4.3.3), 
for example:
```
jpamb.cases.Simple.assertPositive:(I)V
jpamb.cases.Simple.divideByZero:()I 
jpamb.cases.Simple.divideZeroByZero:(II)I
jpamb.cases.Arrays.arraySpellsHello:([C)V
```

And the query is one of: 

| query              | description                               |
| :-----             | :-----                                    |
| `assertion error`  | an execution throws an assertion error    |
| `ok`               | an execution runs to completion           | 
| `*`                | an execution runs forever                 | 
| `divide by zero`   | an execution divides by zero              | 
| `out of bounds`    | an execution index an array out of bounds | 
| `null pointer`     | an execution throws an null pointer exeception | 

And the prediction is either a wager (`-3`, `inf`) (the number of points you 
want to bet on you being right) or a probability (`30%`, `72%`)


A wager is the number of points waged [`-inf`, `inf`] on your prediction. A negative wager is against the query, and 
a positive is for the query. A failed wager is subtracted from your points, however 
a successful wager is converted into points like so:
$$\mathtt{points} = 1 - \frac{1}{\mathtt{wager} + 1}$$

If you are sure that the method being analyzed does not contain an "assertion error", 
you can wager -200 points. If you are wrong, and the program does exhibit an assertion error, 
you lose 200 point, but if you are correct, you gain $1 - 1 / 201 = 0.995$ points.

Below are some example values. Note that small wagers equal smaller risk.

|  wager | points |
|   ---: |    ---:|
|   0.00 |   0.00 |
|   0.25 |   0.20 |
|   0.50 |   0.33 |
|   1.00 |   0.50 | 
|   3.00 |   0.75 | 
|   9.00 |   0.90 | 
|  99.00 |   0.99 | 
|    inf |   1.00 | 

Examples of such scripts can be seen in `solutions/`.

You can also respond with a probability [`0%`: `100%`], which is automatically converted into 
the optimal wager. An example of this is in `solutions/apriori.py`, which uses the distribution 
of errors from `stats/distribution.csv` to gain an advantage (which is cheating :D).

If you are curious, the optimal wager is found by solving the following quadratic function, where $p$ is the probability:
$$(1 - p) \cdot \mathtt{wager} = p \cdot \mathtt{points} = p \cdot (1 - \frac{1}{\mathtt{wager} + 1})$$
And dividing by 2 to get the optimal wager:
$$\mathtt{wager} = \frac{1 - 2 p }{2 (p - 1)}$$

|   prob |  wager |
|   ---: |    ---:|
|     0% |   -inf |
|    10% |     -8 |
|    25% |     -2 |
|    50% |      0 |
|    75% |      2 |
|    90% |      8 |
|   100% |    inf | 

## Getting Started

To get started create your first program analysis. The recommended implementation language is Python (as there is extra support via the library), but any language you can run from the command line will do.

Your analysis should supprot two modes. The first is info mode:

```shell
$> ./analysis info
<name>
<version>
<comma seperated tags>
<system string, if you want to paticipate in science> else "no"
````

And the second is prediction mode. Here running your analysis should look like this:

```shell
$> ./analysis "jpamb.cases.Simple.assertPositive:(I)V" 
divide by zero;5 
ok;25%
```

### Test

To test your script simply run the following command:

```shell
uvx jpamb -- test ./analysis
```
It will spit out a report.

You can also filter the report on some methods. In the begining it might be a good idea to focus on the simple cases:

```shell
uvx jpamb -- test --filter "Simple" ./analysis
```

### Evaluating

When your script is working, you can evaluate it using the `evaluate` command.
This will produce a json report you can share with others.


```shell
uvx jpamb -- evaluate ./analysis > report.json
```


If you have problems getting started, please file an [issue](https://github.com/kalhauge/jpamb/issues).


### Source code

The source code is located under the `src/main/java`. 
A simple solution that analyzes the source code directly using the [tree-sitter
library](https://tree-sitter.github.io/tree-sitter/) is located at
`solutions/syntaxer.py`.

### Byte code

To write more advanced analysis it makes sense to make use of the byte-code. To lower the bar to entrance, the byte code of the benchmarks have already been decompiled by the 
[`jvm2json`](https://github.com/kalhauge/jvm2json) tool. 
The codec for the output is described [here](https://github.com/kalhauge/jvm2json/blob/main/CODEC.txt).

Some sample code for how to get started can be seen in `solutions/bytecoder.py`.

There is an interface for using the opcode directly in `lib/jpamb/jvm/opcode.py`. 


### Debug

You can debug your code by running some of the methods or some of the tools, like this: 

```shell
$> ./evaluate your-experiment.yaml --filter-methods=Simple --filter-tools=syntaxer -o experiment.json
```

Also, if you want more debug information you can add multiples `-vvv` to get more information.


## Interpreting

... pending ...


## Developing

... pending ...

## Citation

To cite this work, please use the cite botton on the right.
