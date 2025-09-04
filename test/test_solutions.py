"""
These test, check that the output of the tests remain the same.
"""

import pytest

from glob import glob
import subprocess
import sys
from pathlib import Path


@pytest.mark.parametrize("solution", glob("solutions/*.py"))
def test_solutions(solution):
    sol = Path(solution)
    solreport = Path("test/expected") / (sol.stem + ".txt")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "jpamb.cli",
            "test",
            "-f",
            "Simple",
            "-r",
            solreport,
            sol,
        ],
        check=True,
    )
