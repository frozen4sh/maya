# Copyright Epic Games, Inc. All Rights Reserved.
import logging
from typing import List, Tuple

from maya import mel, cmds
from maya.api.OpenMaya import MPoint, MFnMesh, MDagModifier

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.model.element import MeshElement
from mh_assemble_lib.impl.maya.properties import MayaConfig
from mh_assemble_lib.impl.maya.scene.util import Util


class MayaMeshHandler:
    """
    Specialized Maya handler for handling meshes.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config
        self._maya_fn_mesh: MFnMesh = MFnMesh()
        self._maya_dag_modifier: MDagModifier = MDagModifier()

    def create_meshes(self, meshes: List[MeshElement]) -> None:
        """Create given meshes on scene with corresponding topology, uv and shader."""
        for mesh in meshes:
            logging.info(f"Creating mesh: {mesh.name}.")
            self.add_mesh_to_scene(mesh)
            self.add_mesh_uv(mesh)
            self.add_mesh_shader(mesh)
            self.add_mesh_to_display_layer(mesh)
            self.add_mesh_to_group(mesh)
            self.add_mesh_normals(mesh)

    def add_mesh_to_scene(self, mesh: MeshElement) -> None:
        # create
        mesh.poly_faces = self._get_poly_faces(mesh.index)
        mesh.poly_connections = self._get_poly_connections(mesh.index)
        mesh_obj = self._maya_fn_mesh.create(
            self._get_vtx_positions(mesh.index),
            mesh.poly_faces,
            mesh.poly_connections,
        )
        # rename
        self._maya_dag_modifier.renameNode(mesh_obj, mesh.name)
        self._maya_dag_modifier.doIt()

    def add_mesh_uv(self, mesh: MeshElement) -> None:
        us, vs, indices = self._get_texture_coordinate_data(mesh.index)
        self._maya_fn_mesh.setUVs(us, vs)
        self._maya_fn_mesh.assignUVs(mesh.poly_faces, indices)
        cmds.select(mesh.name, replace=True)
        cmds.polyMergeUV(mesh.name, distance=0.01, constructionHistory=False)

    def add_mesh_shader(self, mesh: MeshElement) -> None:
        cmds.select(mesh.name, replace=True)
        mel.eval("sets -e -forceElement initialShadingGroup")

    def add_mesh_to_display_layer(self, mesh: MeshElement) -> None:
        if self._config.create_display_layers:
            ly_name = self._config.get_lod_layer_name(mesh.lod)
            cmds.editDisplayLayerMembers(ly_name, mesh.name)

    def add_mesh_to_group(self, mesh: MeshElement) -> None:
        if self._config.group_by_lod:
            grp_name = self._config.get_lod_group_name(mesh.lod)
            cmds.parent(mesh.name, grp_name)

    def _get_vtx_positions(self, mesh_index: int) -> List[MPoint]:
        # Returns vertex positions as a List of MPoint objects.
        scene_orient = self._config.scene_orient
        points = self._dna.get_vertex_positions(mesh_index)
        return [Util.point3_to_mpoint(p, scene_orient) for p in points]

    def _get_poly_faces(self, mesh_index: int) -> List[int]:
        # Returns list of vertex count for each face.
        face_vertex_indices = self._dna.get_face_vertex_indices(mesh_index)
        return [len(i) for i in face_vertex_indices]

    def _get_poly_connections(self, mesh_index: int) -> List[int]:
        # ???
        poly_connections: List[int] = []
        vertex_uv_layouts = self._dna.get_vertex_layouts(mesh_index)
        for fvi in self._dna.get_face_vertex_indices(mesh_index):
            for v in fvi:
                conn = vertex_uv_layouts[v].vtx_index
                poly_connections.append(conn)
        return poly_connections

    def _get_texture_coordinate_data(self, mesh_index: int) -> Tuple[List[float], List[float], List[int]]:
        # ???
        us: List[float] = []
        vs: List[float] = []
        indices: List[int] = []
        index: int = 0

        coordinates = self._dna.get_vertex_texture_coordinate(mesh_index)
        vertex_uv_layouts = self._dna.get_vertex_layouts(mesh_index)
        for fvi in self._dna.get_face_vertex_indices(mesh_index):
            for vtx_index in fvi:
                uv = coordinates[vertex_uv_layouts[vtx_index].uv_index]
                us.append(uv.u)
                vs.append(uv.v)
                indices.append(index)
                index += 1
        return us, vs, indices

    def add_mesh_normals(self, mesh: MeshElement):
        normal_array = []
        face_array = []
        vertex_array = []

        dna_faces = self._dna.get_face_count(mesh.index)
        for face_index in range(dna_faces):
            vertex_layout_index_array = self._dna.get_face_vertex_layout_indices(mesh.index, face_index)
            for vertex_layout_index in vertex_layout_index_array:
                layout = self._dna.get_vertex_layout(mesh.index, vertex_layout_index)
                normal = self._dna.get_vertex_normal(mesh.index, layout.normal_index)
                normal_vector = Util.normal_to_mvector(normal, self._config.scene_orient)
                normal_array.append(normal_vector)
                face_array.append(face_index)
                vertex_array.append(layout.vtx_index)

        self._maya_fn_mesh.unlockVertexNormals(range(len(normal_array)))
        self._maya_fn_mesh.unlockFaceVertexNormals(face_array, vertex_array)
        self._maya_fn_mesh.setFaceVertexNormals(normal_array, face_array, vertex_array)
        mel.eval("BakeAllNonDefHistory;")
