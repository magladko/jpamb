import click
from pathlib import Path
import shlex
import enum
import math
import sys
import json

from jpamb import model, logger, jvm
from jpamb.logger import log

import subprocess
import dataclasses
from contextlib import contextmanager
from typing import IO


def re_parser(ctx_, parms_, expr):
    import re

    if expr:
        return re.compile(expr)


def run(cmd: list[str], /, timeout=2.0, logout=None, logerr=None, **kwargs):
    import threading
    from time import monotonic, perf_counter_ns

    if not logerr:

        def logerr(a):
            pass

    if not logout:

        def logout(a):
            pass

    cp = None
    stdout = []
    stderr = []
    tout = None
    try:
        start = monotonic()
        start_ns = perf_counter_ns()

        if timeout:
            end = start + timeout
        else:
            end = None

        cp = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            **kwargs,
        )
        assert cp and cp.stdout and cp.stderr

        def log_lines(cp):
            assert cp.stderr
            with cp.stderr:
                for line in iter(cp.stderr.readline, ""):
                    stderr.append(line)
                    logerr(line[:-1])

        def save_result(cp):
            assert cp.stdout
            with cp.stdout:
                for line in iter(cp.stdout.readline, ""):
                    stdout.append(line)
                    logout(line[:-1])

        terr = threading.Thread(
            target=log_lines,
            args=(cp,),
            daemon=True,
        )
        terr.start()
        tout = threading.Thread(
            target=save_result,
            args=(cp,),
            daemon=True,
        )
        tout.start()

        terr.join(end and end - monotonic())
        tout.join(end and end - monotonic())
        exitcode = cp.wait(end and end - monotonic())
        end_ns = perf_counter_ns()

        if exitcode != 0:
            raise subprocess.CalledProcessError(
                cmd=cmd,
                returncode=exitcode,
                stderr="".join(stderr),
                output="".join(stdout),
            )

        return ("".join(stdout), end_ns - start_ns)
    except subprocess.CalledProcessError as e:
        if tout:
            tout.join()
        e.stderr = "".join(stderr)
        e.stdout = "".join(stdout)
        raise e
    except subprocess.TimeoutExpired:
        if cp:
            cp.terminate()
            if cp.stdout:
                cp.stdout.close()
            if cp.stderr:
                cp.stderr.close()
        raise


@dataclasses.dataclass
class Reporter:
    report: IO
    prefix: str = ""

    @contextmanager
    def context(self, title):
        old = self.prefix
        print(f"{self.prefix[:-1]}┌ {title}", file=self.report)
        self.prefix = f"{self.prefix[:-1]}│ "
        try:
            yield
        finally:
            self.prefix = old
            print(f"{self.prefix[:-1]}└ {title}", file=self.report)

    def output(self, msgs):
        if not isinstance(msgs, str):
            msgs = str(msgs)

        for msg in msgs.splitlines():
            print(f"{self.prefix}{msg}", file=self.report)

    def run(self, args, **kwargs):
        with self.context(f"Run {shlex.join(args)}"):
            with self.context("Stderr"):
                out, time = run(args, logerr=self.output, **kwargs)
            with self.context("Stdout"):
                self.output(out)
            return out


def resolve_cmd(program, with_python=None):

    if with_python is None:
        if str(program[0]).lower().endswith(".py"):
            log.warning(
                "Automatically prepending the current python interpreter to the command. To disable this warning add the '--with-python' flag or prepend intented python interpreter to the command."
            )
            with_python = True
        else:
            with_python = False

    if with_python:
        try:
            executable = str(Path(sys.executable).relative_to(Path.cwd()))
        except ValueError:
            log.warning(
                "Python executable outside of current directory, might be a misconfiguration. "
                "Run the tool with `uv run jpamb ...`."
            )
            executable = sys.executable

        program = (executable,) + program

    return program


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="sets the verbosity of the program, more means more information",
)
@click.option(
    "--workdir",
    type=click.Path(
        exists=True,
        file_okay=False,
        path_type=Path,
        resolve_path=True,
    ),
    default=".",
    help="the base of the jpamb folder.",
)
@click.pass_context
def cli(ctx, workdir: Path, verbose):
    """This is the jpamb main entry point."""
    logger.initialize(verbose)
    log.debug(f"Setup suite in {workdir}")
    ctx.obj = model.Suite(workdir)


@cli.command()
@click.pass_obj
def checkhealth(suite):
    """Check that the repostiory is setup correctly"""
    suite.checkhealth()


@cli.command()
@click.option(
    "--with-python/--no-with-python",
    "-W/-noW",
    help="the analysis is a python script, which should run in the same interpreter as jpamb.",
    default=None,
)
@click.option(
    "--fail-fast/--no-fail-fast",
    help="if we should stop after the first error.",
)
@click.option(
    "--timeout",
    show_default=True,
    default=2.0,
    help="timeout in seconds.",
)
@click.option(
    "--filter",
    "-f",
    help="A regular expression which filter the methods to run on.",
    callback=re_parser,
)
@click.option(
    "--report",
    "-r",
    default="-",
    type=click.File(mode="w"),
    help="A file to write the report to. (Good for golden testing)",
)
@click.argument("PROGRAM", nargs=-1)
@click.pass_obj
def test(suite, program, report, filter, fail_fast, with_python, timeout):
    """Test run a PROGRAM."""

    program = resolve_cmd(program, with_python)

    r = Reporter(report)

    if not filter:
        with r.context("Info"):
            out = r.run(program + ("info",))
            info = model.AnalysisInfo.parse(out)

            with r.context("Results"):
                for k, v in sorted(dataclasses.asdict(info).items()):
                    r.output(f"- {k}: {v}")

    total = 0
    for methodid, correct in suite.case_methods():
        if filter and not filter.search(str(methodid)):
            continue

        with r.context(f"Case {methodid}"):
            out = r.run(program + (str(methodid),), timeout=timeout)
            response = model.Response.parse(out)
            with r.context("Results"):
                for k, v in sorted(response.predictions.items()):
                    r.output(f"- {k}: {v} {v.wager:0.2f}")
            score = response.score(correct)
            r.output(f"Score {score:0.2f}")
            total += score

    r.output(f"Total {total:0.2f}")


@cli.command()
@click.option(
    "--with-python/--no-with-python",
    "-W/-noW",
    help="the analysis is a python script, which should run in the same interpreter as jpamb.",
    default=None,
)
@click.option(
    "--stepwise / --no-stepwise",
    help="continue from last failure",
)
@click.option(
    "--timeout",
    show_default=True,
    default=2.0,
    help="timeout in seconds.",
)
@click.option(
    "--filter",
    "-f",
    help="A regular expression which filter the methods to run on.",
    callback=re_parser,
)
@click.option(
    "--report",
    "-r",
    default="-",
    type=click.File(mode="w"),
    help="A file to write the report to. (Good for golden testing)",
)
@click.argument("PROGRAM", nargs=-1)
@click.pass_obj
def interpret(suite, program, report, filter, with_python, timeout, stepwise):
    """Use PROGRAM as an interpreter."""

    r = Reporter(report)
    program = resolve_cmd(program, with_python)

    last_case = None
    if stepwise:
        try:
            with open(".jpamb-stepwise") as f:
                last_case = model.Case.decode(f.read())
        except ValueError as e:
            log.warning(e)
            last_case = None
        except IOError:
            last_case = None

    total = 0
    count = 0
    for case in suite.cases:
        if last_case and last_case != case:
            continue
        last_case = None

        if filter and not filter.search(str(case)):
            continue

        with r.context(f"Case {case}"):
            try:
                out = r.run(
                    program + (case.methodid.encode(), case.input.encode()),
                    timeout=timeout,
                )
                ret = out.strip()
            except subprocess.TimeoutExpired:
                ret = "*"
            except subprocess.CalledProcessError as e:
                log.error(e)
                ret = "failure"
            r.output(f"Expected {case.result!r} and got {ret!r}")
            if case.result == ret:
                total += 1
            elif stepwise:
                with open(".jpamb-stepwise", "w") as f:
                    f.write(case.encode())
                sys.exit(-1)
            count += 1

    Path(".jpamb-stepwise").unlink(True)

    r.output(f"Total {total}/{count}")


@cli.command()
@click.pass_context
@click.option(
    "--with-python/--no-with-python",
    "-W/-noW",
    help="the analysis is a python script, which should run in the same interpreter as jpamb.",
    default=None,
)
@click.option(
    "--iterations",
    "-N",
    show_default=True,
    default=3,
    help="number of iterations.",
)
@click.option(
    "--timeout",
    show_default=True,
    default=2.0,
    help="timeout in seconds.",
)
@click.option(
    "--report",
    "-r",
    default="-",
    type=click.File(mode="w"),
    help="A file to write the report to",
)
@click.argument("PROGRAM", nargs=-1)
def evaluate(ctx, program, report, timeout, iterations, with_python):
    """Evaluate the PROGRAM."""

    program = resolve_cmd(program, with_python)

    def calibrate(count=100_000):
        from time import perf_counter_ns
        from jpamb import timer

        start = perf_counter_ns()
        timer.sieve(count)
        end = perf_counter_ns()
        return end - start

    try:
        (out, _) = run(
            program + ("info",),
            logout=log.info,
            logerr=log.debug,
            timeout=timeout,
        )
        info = model.AnalysisInfo.parse(out)
    except ValueError:
        log.error("Expected info, but got:")
        for o in out.splitlines():
            log.error(o)

    total_score = 0
    total_time = 0
    total_relative = 0
    total_methods = 0
    bymethod = {}

    for methodid, correct in ctx.obj.case_methods():
        log.success(f"Running on {methodid}")
        results = []

        _score = 0
        _time = 0
        _relative = 0
        for i in range(iterations):
            log.info(f"Running on {methodid}, iter {i}")
            r1 = calibrate()
            out, time = run(
                program + (methodid.encode(),), logerr=log.debug, timeout=timeout
            )
            r2 = calibrate()
            response = model.Response.parse(out)
            score = response.score(correct)
            relative = math.log10(time / (r1 + r2) * 2)

            result = {k: v.wager for k, v in response.predictions.items()}

            results.append(
                {
                    "iteration": i,
                    "response": result,
                    "score": score,
                    "time": time,
                    "relative": relative,
                    "calibrates": [r1, r2],
                }
            )

            _score += score
            _relative += relative
            _time += time

        bymethod[str(methodid)] = {
            "score": _score / iterations,
            "time": _time / iterations,
            "relative": _relative / iterations,
            "iterations": results,
        }

        total_score += _score / iterations
        total_time += _time / iterations
        total_relative += _relative / iterations

        total_methods += 1

    json.dump(
        {
            "info": dataclasses.asdict(info),
            "bymethod": bymethod,
            "score": total_score,
            "time": total_time / total_methods,
            "relative": total_relative / total_methods,
        },
        report,
        indent=2,
    )


@cli.command()
@click.option(
    "--decompile / --no-decompile",
    help="decompile the classfiles using jvm2json.",
)
@click.option(
    "--test / --no-test",
    help="test that all cases are correct.",
)
@click.pass_obj
def build(suite, decompile, test):
    """Rebuild all benchmarks."""

    run(
        ["mvn", "compile"],
        logerr=log.warning,
        logout=log.info,
        timeout=600,
    )

    if decompile:
        log.info("Decompiling")
        for cl in suite.classes():
            log.info(f"Decompiling {cl}")
            res, t = run(
                [
                    "jvm2json",
                    "-s",
                    suite.classfile(cl),
                ],
                logerr=log.warning,
            )
            with open(suite.decompiledfile(cl), "w") as f:
                json.dump(json.loads(res), f, indent=2, sort_keys=True)
        log.success("Done decompiling")

    if test:
        log.info("Testing")

        for case in suite.cases:
            log.info(f"Testing {case}")

            folder = suite.classfiles_folder

            try:
                res, x = run(
                    [
                        "java",
                        "-cp",
                        folder,
                        "-ea",
                        "jpamb.Runtime",
                        case.methodid.encode(),
                        case.input.encode(),
                    ],
                    logout=log.info,
                    logerr=log.debug,
                    timeout=2,
                )
            except subprocess.TimeoutExpired:
                res = "*"

            if case.result == res.strip():
                log.success(f"Correct {case}")
            else:
                log.error(f"Incorrect (got {res.strip()}) expected {case}")

        log.success("Done testing")


@cli.command()
@click.option(
    "--format",
    type=click.Choice(["pretty", "real", "repr", "json"], case_sensitive=True),
    default="pretty",
    help="The format to print the instruction in.",
)
@click.argument("METHOD")
@click.pass_obj
def inspect(suite, method, format):
    method = jvm.AbsMethodID.decode(method)
    for i, res in enumerate(suite.findmethod(method)["code"]["bytecode"]):
        op = jvm.Opcode.from_json(res)
        match format:
            case "pretty":
                res = str(op)
            case "real":
                res = op.real()
            case "repr":
                res = repr(op)
            case "json":
                res = json.dumps(res)
        print(f"{i:03d} | {res}")


if __name__ == "__main__":
    cli()
