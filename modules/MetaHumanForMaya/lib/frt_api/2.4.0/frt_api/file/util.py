# Copyright Epic Games, Inc. All Rights Reserved.


import os
import logging
from importlib import util, machinery

logger = logging.getLogger("frt_api.file.util")


def source_module(name: str, path: str):
    if not path or not os.path.exists(path) or not os.path.isfile(path) or not path.endswith(".py"):
        logger.warning("File %s is not found!" % path)
        raise FileNotFoundError(f"{path} was not found!")
    spec = util.spec_from_loader(name, machinery.SourceFileLoader(name, path))  # type: ignore
    module = util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return module
