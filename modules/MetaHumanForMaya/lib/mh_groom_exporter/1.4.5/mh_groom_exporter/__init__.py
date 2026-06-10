# Copyright Epic Games, Inc. All Rights Reserved.
import time
import logging
from functools import wraps

logger = logging.getLogger("MetaHumanGroomExporter")
logger.setLevel(logging.DEBUG)

def timer(func):
    """
    Timer Decorator
    """
    @wraps(func)
    def wrapper(*args, **kwargs):

        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        logger.info(f"{func.__name__} ran in {round(end - start, 2)}s")
        return result
    return wrapper


from .version import version
from .gui.main_window import show


__all__ = [
    "version",
    "show",
]
