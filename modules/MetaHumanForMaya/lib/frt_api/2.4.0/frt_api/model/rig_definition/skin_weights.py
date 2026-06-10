# Copyright Epic Games, Inc. All Rights Reserved.

from typing import Dict, List, Optional
from dataclasses import field, dataclass


@dataclass
class SkinningData:
    """
    SkinningData
    """

    joint_indices: List[List[int]] = field(default_factory=list)
    weights: List[List[float]] = field(default_factory=list)


@dataclass
class SkinTransferData:
    """
    SkinTransferData
    """

    name: str = ""
    skin_base_mesh: str = ""
    geo_base_mesh: str = ""
    mapping: Dict[str, Optional[List[str]]] = field(default_factory=dict)
    skinning_data: Optional[SkinningData] = None

    def __str__(self):
        return self.name
