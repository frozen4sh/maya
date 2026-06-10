# Copyright Epic Games, Inc. All Rights Reserved.

import os
import json
import logging
import importlib
import contextlib
from enum import Enum
from typing import Any, Dict


class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances: Dict[str, Any] = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls.__name__ not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls.__name__] = instance
        return cls._instances[cls.__name__]

    def clear(cls):
        with contextlib.suppress(KeyError):
            del SingletonMeta._instances[cls.__name__]


class Direction(Enum):
    LEFT_TO_RIGHT = 1
    RIGHT_TO_LEFT = 2


def resource(*path):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "res", *path)
    return path.replace("\\", "/")


def get_logger():
    logger = logging.getLogger(os.path.basename(os.path.dirname(os.path.abspath(__file__))))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(filename)s - %(message)s")

    level = logging.INFO
    debug = os.environ.get("MH_EXPRESSION_EDITOR_DEBUG") or "0"
    if debug == "1":
        level = logging.DEBUG

    logger.setLevel(level)
    return logger


def load_json(path):
    with open(path) as f:
        return json.load(f)


def source_module(name, path):
    if path and os.path.exists(path) and os.path.isfile(path) and path.endswith(".py"):
        spec = importlib.util.spec_from_loader(name, importlib.machinery.SourceFileLoader(name, path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


def linear_interpolate_color(t, lowest_influence=(106, 255, 147), highest_influence=(255, 147, 106)):
    r1, g1, b1 = lowest_influence
    r2, g2, b2 = highest_influence

    t = max(0, min(1, t))
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    a = int(t * 255.0)

    return r, g, b, a
