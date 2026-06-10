# Copyright Epic Games, Inc. All Rights Reserved.

import logging
from typing import Dict, List, Optional

from nls.assetgeneration import LodGeneration

from .rig import RigDataHandler
from .calculation import RigCalculationHandler

logger = logging.getLogger("frt_api.rig.asset_generation")


class LODGeneration:
    def __init__(self, model_description_path: str, source_lod: int):
        self.lod_generation: Optional[LodGeneration] = None
        self.source_lod: Optional[int] = None
        lod_generation = LodGeneration()
        model_loaded = lod_generation.LoadModelBinary(model_description_path, source_lod)
        if model_loaded:
            self.lod_generation = lod_generation
            self.source_lod = source_lod
        else:
            logger.warning(f"Model load failed. Source LOD {source_lod} cannot be used to generate lower LOD meshes.")

    def apply(self, rig: RigDataHandler) -> Dict[str, List[List[float]]]:
        if not self.lod_generation or self.source_lod is None:
            logger.warning("LOD Generation failed. Model not loaded.")
            return {}
        source_lod_meshes = {}
        for mesh_index in rig.dna_reader.getMeshIndicesForLOD(self.source_lod):
            mesh_name = rig.dna_reader.getMeshName(mesh_index)
            source_lod_meshes[mesh_name] = rig.get_neutral_mesh_vertex_positions(mesh_name)
        lower_lod_meshes: Dict[str, List[List[float]]] = self.lod_generation.Apply(source_lod_meshes)
        if lower_lod_meshes:
            for mesh, vertex_positions in lower_lod_meshes.items():
                rig.set_neutral_mesh(mesh, vertex_positions)
            RigCalculationHandler.calculate_neutral_mesh(rig)
            RigCalculationHandler.ordered_calculation(
                rig, [expression.name for expression in rig.rig_definition.expressions]
            )
            logger.info(f"LOD Generation applied. Source LOD: {self.source_lod}.")
            return lower_lod_meshes
        else:
            logger.error(
                f"Source meshes don't match model data. Lower LOD mesh generation unsuccessful. Source LOD: {self.source_lod}."
            )
        return {}
