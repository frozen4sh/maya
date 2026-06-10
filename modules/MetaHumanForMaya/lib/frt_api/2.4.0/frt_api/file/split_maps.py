# Copyright Epic Games, Inc. All Rights Reserved.

import logging
import traceback
from typing import List
from contextlib import suppress

from .skin_weights import MayaSkinWeights

logger = logging.getLogger("frt_api.file.split_maps")


class SplitMapReadError(Exception):
    pass


def write_split_map(file_path: str, skin_weights: MayaSkinWeights, index: int):
    """
    Writes split map data to file.

    @param file_path: File path. (file.common.FileInfo)
    @param skin_weights: Skin weights object. (MayaSkinWeights)
    @param index: Skin weights joint index. (int)
    @throws IOError: If unable to write file.
    """

    logger.debug("Writing split map to file: " + file_path)

    with suppress(Exception), open(file_path, mode="w", encoding="utf-8", buffering=65536) as file:
        for vtx_info in skin_weights.vertices_info:
            for i in range(0, len(vtx_info), 2):
                if vtx_info[i] == index:
                    file.write(str(vtx_info[i + 1]) + "\n")
                    break
            else:
                file.write("0.0\n")
        logger.debug("Split map successfully saved in csv file.")


def read_split_map(file_path: str) -> List[float]:
    """
    Reads split map data from file.

    @param file_path: File path. (file.common.FileInfo)
    @return List containing weights for each vertex. (float[])
    @throws FileApiError: If file is corrupted.
    """

    logger.debug("Reading split map from file: " + file_path)

    try:
        with open(file_path, encoding="utf-8") as file:
            weight_strings = file.read().split("\n")
            weights = [float(weights_string) for weights_string in weight_strings if weights_string]
    except Exception as e:
        msg = f"Unable to read split map file. File is corrupted: {file_path}."
        logger.warning(f"{msg}\n{traceback.format_exc()}")
        raise SplitMapReadError(msg) from e
    return weights
