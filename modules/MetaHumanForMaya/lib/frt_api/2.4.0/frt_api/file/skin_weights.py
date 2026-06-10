# Copyright Epic Games, Inc. All Rights Reserved.

import logging
import traceback
from typing import List, Union
from contextlib import suppress

from ..model.skin_weights import MayaSkinWeights

logger = logging.getLogger("frt_api.file.skin_weights")


class SkinWeightsReadError(Exception):
    pass


def write_skin_weights(file_path: str, skin_weights: MayaSkinWeights):
    """
    Writes Maya skin weights to file.

    @param file_path: File path. (strs)
    @param skin_weights: Maya skin weights object. (MayaSkinWeights)
    @throws IOError: If unable to write file.
    """

    logger.debug("Writing skin weights to file: " + file_path)

    with suppress(Exception), open(file_path, mode="w", encoding="utf-8", buffering=65536) as file:
        file.write(str(skin_weights.no_of_influences) + "," + str(skin_weights.skinning_method) + "\n")
        file.write(",".join(skin_weights.joints))
        for vtxInfo in skin_weights.vertices_info:
            file.write("\n")
            skin_weights_string = [repr(info) for info in vtxInfo]
            file.write(",".join(skin_weights_string))

    logger.debug("Skin weights successfully saved in csv file.")


def read_skin_weights(file_path):
    """
    Reads Maya skin weights from file.

    @param file_path: File path. (file.common.FileInfo)
    @return Maya Skin weights object. (maya.node.MayaSkinWeights)
    @throws FileApiError: If file is corrupted.
    """

    logger.debug("Reading skin weights from file: " + file_path)
    maya_skin_weights = MayaSkinWeights()

    try:
        with open(file_path, encoding="utf-8") as file:
            # read no of influences
            line = file.readline().strip()
            tokens = line.split(",")
            maya_skin_weights.no_of_influences = int(tokens[0])
            if len(tokens) == 2:
                maya_skin_weights.skinning_method = int(tokens[1])

            # read joints
            line = file.readline()
            maya_skin_weights.joints = line.strip().split(",")

            # read weights
            lines = file.read().split("\n")
            for line in lines:
                parts = line.strip().split(",")
                vertex_info: List[Union[int, float]] = []
                for i in range(0, len(parts), 2):
                    vertex_info.append(int(parts[i]))
                    vertex_info.append(float(parts[i + 1]))
                maya_skin_weights.vertices_info.append(vertex_info)
    except Exception as e:
        msg = f"Unable to read skin weights file. File is corrupted: {file_path}."
        logger.warning(f"{msg}\n{traceback.format_exc()}")
        raise SkinWeightsReadError(msg) from e
    return maya_skin_weights
