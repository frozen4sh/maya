# Copyright Epic Games, Inc. All Rights Reserved.
"""
Form objects are used for exchanging data between UI and controler.
"""
from typing import List, Callable


class MeshForm:
    """
    Mesh information displayed on UI.
    """

    def __init__(self, index: int, name: str):
        self.index: int = index
        self.name: str = name


class LodForm:
    """
    LOD information displayed on UI.
    """

    def __init__(self, lod_id: int):
        self.id: int = lod_id
        self.meshes: List[MeshForm] = []

    def get_mesh_by_name(self, name: str) -> MeshForm:
        for mesh in self.meshes:
            if mesh.name == name:
                return mesh
        return None

    def get_mesh_count(self) -> int:
        return len(self.meshes)

    def add_mesh(self, mesh: MeshForm) -> None:
        self.meshes.append(mesh)


class MeshLayoutForm:
    """
    LOD and meshes hierarchy information displayed on UI.
    """

    def __init__(self):
        self.lods: List[LodForm] = []

    def get_lod_count(self) -> int:
        return len(self.lods)

    def get_mesh_by_name(self, name: str) -> MeshForm:
        for lod in self.lods:
            mesh = lod.get_mesh_by_name(name)
            if mesh is not None:
                return mesh
        return None

    def get_all_meshes(self) -> List[MeshForm]:
        meshes = []
        for lod in self.lods:
            meshes.extend(lod.meshes)
        return meshes

    def get_mesh_count(self) -> int:
        count = 0
        for lod in self.lods:
            count += lod.get_mesh_count()
        return count

    def add_lod(self, lod: LodForm) -> None:
        self.lods.append(lod)

    def add_mesh(self, lod_id: int, mesh: MeshForm) -> None:
        self.lods[lod_id].add_mesh(mesh)


class ProgressBarForm:
    """
    Delegate class for updating UI progress bar.

    Callable function has to have two arguments, string and int.
    """

    def __init__(self, callback: Callable[[str, int], None]):
        self._callback: Callable[[str, int], None] = callback

    def set_progress(self, message: str, percent: int) -> None:
        self._callback(message, percent)


class ProcessForm:
    """
    UI parameters for building (processing) MetaHuman.
    """

    def __init__(self):
        self.dna_path: str = None
        self.meshes: List[MeshForm] = []
        self.add_joints: bool = False
        self.add_skin_cluster: bool = False
        self.add_blend_shapes: bool = False
        self.add_rig_logic: bool = False
        self.add_ctrl_attr: bool = False
        self.add_anim_map_attr: bool = False
        self.combine_bs_name: bool = False
        self.add_key_frames: bool = False
        self.gui_ctrls_path: str = None
        self.analog_ctrls_path: str = None
        self.aas_path: str = None
        self.shader_dir: str = None
        self.bar: ProgressBarForm = None

    def set_progress(self, message: str, percent: int) -> None:
        if self.bar is not None:
            self.bar.set_progress(message, percent)

    def __str__(self) -> str:
        result: str = "ProcessForm: "
        result += f"dna_path: {self.dna_path}, "
        result += f"meshes: {[m.name for m in self.meshes]}"
        result += f"add_joints: {self.add_joints}, "
        result += f"add_skin_cluster: {self.add_skin_cluster}, "
        result += f"add_blend_shapes: {self.add_blend_shapes}, "
        result += f"add_rig_logic: {self.add_rig_logic}, "
        result += f"add_ctrl_attr: {self.add_ctrl_attr}, "
        result += f"add_anim_map_attr: {self.add_anim_map_attr}, "
        result += f"combine_bs_name: {self.combine_bs_name}, "
        result += f"add_key_frames: {self.add_key_frames}, "
        result += f"gui_ctrls_path: {self.gui_ctrls_path}, "
        result += f"analog_ctrls_path: {self.analog_ctrls_path}, "
        result += f"aas_path: {self.aas_path}, "
        result += f"shader_dir: {self.shader_dir}"
        return result
