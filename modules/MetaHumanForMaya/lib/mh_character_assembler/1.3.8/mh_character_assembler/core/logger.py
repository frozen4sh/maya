# Copyright Epic Games, Inc. All Rights Reserved.
import logging
import os

LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

LOG_LEVEL = LEVELS[os.getenv("MAYATOOLS_LOGLEVEL", "INFO")]


def get_logger():
    logger = logging.getLogger(os.path.basename(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s: %(filename)s - %(message)s")
    return logger
