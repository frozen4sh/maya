# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import abc
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from mh_pose_editor.model import rbf_node
    from mh_pose_editor.extensions.dna_io.model import dna_model


class Serializer:
    """
    Base serialization class to serialize/deserialize DNA files to MHDNAModel classes
    """

    @classmethod
    @abc.abstractmethod
    def can_process(cls, model: "dna_model.MHDNAModel", **kwargs) -> bool:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def serialize(
        cls,
        solvers: List["rbf_node.RBFNode"],
        export_selected_geometry: bool = False,
        export_geometry: bool = True,
        export_rbf: bool = True,
        export_swing_twist: bool = True,
        **kwargs,
    ) -> "dna_model.MHDNAModel":
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def deserialize(
        cls,
        model: "dna_model.MHDNAModel",
        unpack_rbf: bool,
        unpack_swing_twist: bool,
        solver_names: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        raise NotImplementedError
