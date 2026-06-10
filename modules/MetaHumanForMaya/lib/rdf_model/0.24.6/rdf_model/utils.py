# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

import os
import logging

LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def get_logger(debug: bool = False) -> logging.Logger:
    level = logging.INFO
    level_from_env = LEVELS.get(os.getenv("RDFTOOL_LOGLEVEL", "INFO"))
    if level_from_env:
        level = level_from_env
    if debug:
        level = logging.DEBUG

    logger = logging.getLogger(os.path.basename(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=level, format="%(levelname)s: %(filename)s - %(message)s")

    logger.setLevel(level)
    return logger
