# Copyright Epic Games, Inc. All Rights Reserved.

import logging

logger = logging.getLogger("frt_api.file.rig_definition")


class RigDefinitionReadError(Exception):
    pass


class RigDefinitionWriteError(Exception):
    pass
