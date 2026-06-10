# Copyright Epic Games, Inc. All Rights Reserved.
from typing import List, Optional

from frt_api.model.rig_definition.mask import Mask


class MapType:
    """
    MapType class.
    """

    def __init__(self):
        self.name: str = ""  # (string)

    def __str__(self):
        return self.name


class Map:
    """
    Map class.
    """

    def __init__(self) -> None:
        self.name: str = ""  # (string)
        self.base_map: int = 0  # (int)
        self.file_exists: bool = False  # (boolean)
        self.file_path: str = ""  # (string)
        self.map_type: Optional[MapType] = None  # (MapType)

    def __str__(self):
        return self.name


class MapInExpression:
    """
    Class representing map which is deformed by expression.

    It is used when some expressions have for example wrinkle maps.
    This class holds information which map should be added to shader and through
    which masks should be passed.
    """

    def __init__(self):
        self.map: Optional[Map] = None  # (Map)
        self.masks: List[Mask] = []  # (Mask[])

    def __str__(self):
        return self.map.name if self.map else ""
