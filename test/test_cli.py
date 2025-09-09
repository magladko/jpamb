"""
These test, check that the output of the tests remain the same.
"""

import pytest

from glob import glob
from pathlib import Path

from click.testing import CliRunner

from jpamb import cli


@pytest.mark.parametrize("solution", glob("solutions/*.py"))
def test_solutions(solution):
    runner = CliRunner()
    sol = Path(solution)
    solreport = Path("test/expected") / (sol.stem + ".txt")
    result = runner.invoke(
        cli.cli,
        [
            "test",
            "-f",
            "Simple",
            "-r",
            str(solreport),
            "--with-python",
            str(sol),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
