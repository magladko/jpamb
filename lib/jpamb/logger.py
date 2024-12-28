""" jpamb.logger

This module contains modules to handle consitent logging across 
the different tools.
"""

import sys
from loguru import logger


log = logger


def initialize(verbose: int):
    LEVELS = ["SUCCESS", "INFO", "DEBUG", "TRACE"]

    lvl = LEVELS[verbose]

    if verbose >= 2:
        log.remove()
        log.add(
            sys.stderr,
            format="<green>{elapsed}</green> | <level>{level: <8}</level> | <red>{extra[process]:<8}</red> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=lvl,
        )
    else:
        log.remove()
        log.add(
            sys.stderr,
            format="<red>{extra[process]:<8}</red>: <level>{message}</level>",
            level=lvl,
        )

    log.configure(extra={"process": "main"})
