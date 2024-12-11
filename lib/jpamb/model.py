"""
jpamb.model

This module provides the basic data model for working with the JPAMB.

"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from loguru import logger
import collections
import re

from typing import *  # type: ignore

from . import jvm


@dataclass(frozen=True, order=True)
class Input:
    """
    An 'Input' to a 'Case' is a comma seperated list of JVM values
    """

    values: tuple[jvm.Value, ...]

    @staticmethod
    def decode(input: str) -> "Input":
        if input[0] != "(" and input[-1] != ")":
            raise ValueError(f"Expected input to be in parenthesis, but got {input}")
        values = jvm.Value.decode_many(input)
        return Input(tuple(values))

    def encode(self) -> str:
        return "(" + ", ".join(v.encode() for v in self.values) + ")"


CASE_RE = re.compile(r"([^ ]*) +(\([^)]*\)) -> (.*)")


@dataclass(frozen=True, order=True)
class Case:
    """
    A 'Case' is an absolute method id, an input, and the expected result.
    """

    methodid: jvm.Absolute[jvm.MethodID]
    input: Input
    result: str

    @staticmethod
    def match(line) -> re.Match:
        if not (m := CASE_RE.match(line)):
            raise ValueError(f"Unexpected line: {line!r}")
        return m

    @staticmethod
    def decode(line):
        m = Case.match(line)
        return Case(
            jvm.Absolute.decode(m.group(1), jvm.MethodID.decode),
            Input.decode(m.group(2)),
            m.group(3),
        )

    def __str__(self) -> str:
        return f"{self.methodid.classname}.{self.methodid.extension.name}:{self.input.encode()} -> {self.result}"

    @staticmethod
    def by_methodid(
        iterable: Iterable["Case"],
    ) -> list[tuple[jvm.Absolute[jvm.MethodID], list["Case"]]]:
        """Given an interable of cases, group the cases by the methodid"""
        cases_by_id = collections.defaultdict(list)

        for c in iterable:
            cases_by_id[c.methodid].append(c)

        return sorted(cases_by_id.items())


@contextmanager
def _check(reason, failfast=False):
    """Used in the checkhealth command"""
    logger.info(reason)
    try:
        yield
    except AssertionError as e:
        msg = str(e)
        if msg:
            logger.error(f"FAILED: {e}")
        else:
            logger.error(f"FAILED")
        if failfast:
            e.args = (reason, *e.args)
            raise
    else:
        logger.info("ok")


class Suite:
    """The suite!

    Note that only one instance per abstract path exist to be able to cache
    information about the suite on read.

    """

    _instances = dict()

    def __new__(cls, workfolder: Path):
        if workfolder not in cls._instances:
            cls._instances[workfolder] = super().__new__(cls)
        return cls._instances[workfolder]

    def __init__(self, workfolder: Path):
        assert workfolder.is_absolute(), f"Assuming that {workfolder} is absolute."
        self.workfolder = workfolder
        self.invalidate_cache()

    def invalidate_cache(self):
        """Invalidate the case, and require a recomputation of the cached values."""
        self._cases = None

    @property
    def stats_folder(self) -> Path:
        """The folder to place the statistics about the repository"""
        return self.workfolder / "stats"

    @property
    def classfiles_folder(self) -> Path:
        """The folder containing the class files"""
        return self.workfolder / "target" / "classes"

    def classfiles(self) -> Iterable[Path]:
        yield from self.classfiles_folder.glob("**/*.class")

    def classfile(self, cn: jvm.ClassName) -> Path:
        return (self.classfiles_folder / Path(*cn.packages) / cn.name).with_suffix(
            ".class"
        )

    @property
    def sourcefiles_folder(self) -> Path:
        """The folder containing the class files"""
        return self.workfolder / "src" / "main" / "java"

    def sourcefiles(self) -> Iterable[Path]:
        yield from self.sourcefiles_folder.glob("**/*.java")

    def sourcefile(self, cn: jvm.ClassName) -> Path:
        return (
            self.sourcefiles_folder / Path(*cn.packages) / cn.name.split("$")[0]
        ).with_suffix(".java")

    @property
    def decompiled_folder(self) -> Path:
        return self.workfolder / "decompiled"

    def decompiledfiles(self) -> Iterable[Path]:
        yield from self.decompiled_folder.glob("**/*.json")

    def decompiledfile(self, cn: jvm.ClassName) -> Path:
        return (self.decompiled_folder / Path(*cn.packages) / cn.name).with_suffix(
            ".json"
        )

    def classes(self) -> Iterable[jvm.ClassName]:
        for file in self.classfiles():
            yield jvm.ClassName.from_parts(
                *file.relative_to(self.classfiles_folder).with_suffix("").parts
            )

    @property
    def case_file(self) -> Path:
        return self.stats_folder / "cases.txt"

    @property
    def version(self):
        with open(self.workfolder / "CITATION.cff") as f:
            import yaml

            return yaml.safe_load(f)["version"]

    @property
    def cases(self) -> tuple[Case, ...]:
        if self._cases is None:
            with open(self.case_file) as f:
                self._cases = tuple(Case.decode(line) for line in f)
        return self._cases

    def checkhealth(self, failfast=False):
        """Checks the health of the repository through a sequence of tests"""

        check = lambda msg: _check(msg, failfast)

        with check(f"The case file [{self.case_file}]."):
            assert self.case_file.exists(), "should exist"
            assert len(self.cases) > 0, "cases should be parsable and at least one"
            logger.info(f"Found {len(self.cases)} cases")

        with check(f"The source folder [{self.sourcefiles_folder}]."):
            assert self.sourcefiles_folder.exists(), "should exists"
            assert self.sourcefiles_folder.is_dir(), "should be a folder"
            files = list(self.sourcefiles())
            assert len(files) > 0, "should contain source files"
            logger.info(f"Found {len(files)} files")

        with check(f"The classfiles folder should exist [{self.classfiles_folder}]."):
            assert self.classfiles_folder.exists(), "should exists"
            assert self.classfiles_folder.is_dir(), "should be a folder"
            files = list(self.classfiles())
            assert len(files) > 0, "should contain class files"
            logger.info(f"Found {len(files)} files")

        with check(f"The decompiled folder should exist [{self.decompiled_folder}]."):
            assert self.decompiled_folder.exists(), "should exists"
            assert self.decompiled_folder.is_dir(), "should be a folder"
            files = list(self.decompiledfiles())
            assert len(files) > 0, "should contain decompiled class files"
            logger.info(f"Found {len(files)} files")
