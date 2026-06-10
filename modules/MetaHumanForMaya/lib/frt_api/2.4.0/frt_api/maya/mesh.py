# Copyright Epic Games, Inc. All Rights Reserved.

import logging

import maya.OpenMaya as om
import maya.api.OpenMaya as om2
from maya import cmds

from .core import MayaUtil, BaseHandler
from ..model.maya.symmetry import MayaVtxPair, MayaSymmetryInfo

logger = logging.getLogger("frt_api.maya.mesh")


class MeshMayaHandler(BaseHandler):
    """
    Mesh Maya handler.

    Contains methods for manipulation with mesh objects in scene.
    @see BaseHandler
    """

    def duplicate_node(self, mesh, name):
        """
        Duplicates given mesh node.

        @param mesh_name: Mesh object or mesh pattern to be duplicated. (DagNode or string)
        @param name: New duplicated mesh pattern. (string)
        @return Duplicated mesh. (DagNode)
        """

        duplicated_node = cmds.duplicate(mesh, name=name)[0]
        MayaUtil.unlock_node_attributes(duplicated_node)
        cmds.delete(duplicated_node, constructionHistory=True)
        return duplicated_node

    def calculate_mesh_delta(self, neutral_vertex_positions, pose_vertex_positions):
        return [
            [poseVtx[0] - neutralVtx[0], poseVtx[1] - neutralVtx[1], poseVtx[2] - neutralVtx[2]]
            for poseVtx, neutralVtx in zip(pose_vertex_positions, neutral_vertex_positions)
        ]

    def calculate_vertex_position(self, neutral, delta, multiplier=(1.0, 1.0, 1.0)):
        product_values = [diffVtx * mirrorVectorValue for diffVtx, mirrorVectorValue in zip(delta, multiplier)]
        return [neutralVtx + product for neutralVtx, product in zip(neutral, product_values)]

    def get_mesh_vertex_positions(self, mesh_name, world_space=False, vert_ids=None, homogeneous=False):
        """
        Gets mesh vertex positions.

        @param mesh_name: Mesh node pattern in scene. (string)
        @param world_space: Indicates is vertex positions should be returned
            in world space. If False, they will be returned in object space. (boolean)
        @param vert_ids: List of vertex ids we want to read positions for.
            If it is equal to None, whole mesh is required. (int[])
        @param homogeneous: Return homogeneous (x, y, z, 1.0) coordinates if
            this parameter is True. (boolean)
        @return A list containing mesh vertex positions.
        """

        # new ways
        sel = om.MSelectionList()
        sel.add(mesh_name)

        dag_path = om.MDagPath()
        sel.getDagPath(0, dag_path)

        mf_mesh = om.MFnMesh(dag_path)
        positions = om.MPointArray()

        space = om.MSpace.kObject
        if world_space:
            space = om.MSpace.kWorld

        mf_mesh.getPoints(positions, space)

        if vert_ids:
            if homogeneous:
                return [[positions[i].x, positions[i].y, positions[i].z, 1.0] for i in vert_ids]
            return [[positions[i].x, positions[i].y, positions[i].z] for i in vert_ids]

        if homogeneous:
            return [[positions[i].x, positions[i].y, positions[i].z, 1.0] for i in range(positions.length())]
        return [[positions[i].x, positions[i].y, positions[i].z] for i in range(positions.length())]

    def _create_mesh(self, rig, vertex_positions, faces, face_vertices, mesh_name, new_mesh_name, layer=None):
        fn_mesh = om2.MFnMesh()

        mesh_object = fn_mesh.create(
            vertex_positions,
            faces,
            face_vertices,
        )

        dag_modifier = om2.MDagModifier()
        dag_modifier.renameNode(mesh_object, new_mesh_name)
        dag_modifier.doIt()

        self._add_texture_coordinates(rig, fn_mesh, mesh_name, new_mesh_name)

        if layer:
            mesh_layer = self.get_display_layer(layer)
            cmds.editDisplayLayerMembers(mesh_layer, new_mesh_name)

        return new_mesh_name

    def _create_mesh_points(self, vertex_positions):
        points = []
        for position in vertex_positions:
            points.append(om2.MPoint(position[0], position[1], position[2]))
        return points

    def _add_texture_coordinates(self, rig, fn_mesh, mesh_name, node_name):
        texture_coordinates = rig.get_texture_coordinates(mesh_name)

        layouts = rig.get_mesh_layouts(mesh_name)
        coordinate_indices = []
        for layout in layouts:
            coordinate_indices.append(layout[1])

        texture_coordinate_us = []
        texture_coordinate_vs = []
        texture_coordinate_indices = []

        index_counter = 0
        dna_faces = rig.get_dna_faces(mesh_name)
        polygon_faces, _ = rig.get_neutral_mesh_topology(mesh_name)

        for vertex_layout_index_array in dna_faces:
            for vertex_layout_index in vertex_layout_index_array:
                texture_coordinate = texture_coordinates[coordinate_indices[vertex_layout_index]]
                texture_coordinate_us.append(texture_coordinate[0])
                texture_coordinate_vs.append(texture_coordinate[1])
                texture_coordinate_indices.append(index_counter)
                index_counter += 1

        fn_mesh.setUVs(texture_coordinate_us, texture_coordinate_vs)
        fn_mesh.assignUVs(polygon_faces, texture_coordinate_indices)

        cmds.select(node_name, replace=True)
        cmds.polyMergeUV(distance=0.01, constructionHistory=False)

    def create_neutral_mesh(self, rig, mesh_name, layer=None, node_name=None):
        if node_name is None:
            node_name = mesh_name
        vertex_positions = self._create_mesh_points(rig.get_neutral_mesh_vertex_positions(mesh_name))
        faces, face_vertices = rig.get_neutral_mesh_topology(mesh_name)

        return self._create_mesh(rig, vertex_positions, faces, face_vertices, mesh_name, node_name, layer=layer)

    def create_sculpt_mesh(self, rig, mesh_name, expression_name, phase, layer=None):
        vertex_positions = self._create_mesh_points(
            rig.get_sculpt_mesh_vertex_positions(mesh_name, expression_name, phase)
        )
        faces, face_vertices = rig.get_neutral_mesh_topology(mesh_name)

        return self._create_mesh(rig, vertex_positions, faces, face_vertices, mesh_name, f"{mesh_name}_sc", layer=layer)

    def create_cbs_mesh(self, rig, mesh_name, expression_name, phase, layer=None):
        vertex_positions = self._create_mesh_points(
            rig.get_cbs_mesh_vertex_positions(mesh_name, expression_name, phase)
        )
        faces, face_vertices = rig.get_neutral_mesh_topology(mesh_name)

        return self._create_mesh(
            rig, vertex_positions, faces, face_vertices, mesh_name, f"{mesh_name}_cbs", layer=layer
        )

    def mirror_mesh(self, rig, mesh_name, mirror_direction, mesh_node, vtx_ids):
        """
        Mirrors asymmetric mesh in scene.

        Mirrors all vertices for selected mesh, or just selected vertices.
        @param mesh_node: Selected mesh node. (DagNode)
        @param vtx_ids: List of ids of selected vertices. (int[])
        @param mesh_name: Mesh which is being mirrored. (Mesh)
        @param mfmInfo: Mirror info. (maya.node.MayaFlipMirrorInfo)
        @return True if successfully mirrored. (boolean)
        """

        logger.debug(f"Mirroring mesh: {mesh_node}")

        rig_definition = rig.rig_definition
        rig_mesh = rig_definition.get_mesh_by_name(mesh_name)
        try:
            if not rig_mesh.maya_vtx_pairs:
                raise RuntimeError(f"Mesh {mesh_name} doesn't have symmetry info.")
            if not cmds.polyEvaluate(mesh_node, v=True) == len(rig_mesh.maya_vtx_pairs.vtx_pairs):
                raise RuntimeError("Wrong symmetry mesh selected.")
        except AttributeError as error:
            raise RuntimeError(f"Mesh {mesh_name} doesn't exist in the rig.") from error

        try:
            cmds.undoInfo(openChunk=True)
            # save current selection
            selection = cmds.ls(selection=True)

            # get vertex positions
            neutral_vtx_pos = rig.get_neutral_mesh_vertex_positions(mesh_name)
            pose_vtx_pos = self.get_mesh_vertex_positions(mesh_node)
            diff_vtx_pos = self.calculate_mesh_delta(neutral_vtx_pos, pose_vtx_pos)

            # mirror
            side = (
                MayaVtxPair.SIDE_LEFT if mirror_direction == MayaSymmetryInfo.LEFT_TO_RIGHT else MayaVtxPair.SIDE_RIGHT
            )
            mirror_plane = MayaSymmetryInfo.get_mirror_plane(rig_definition)
            mirror_vector = [1, 1, 1]
            mirror_vector[mirror_plane] = -1

            for vertex_id in vtx_ids:
                if rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].side == side:
                    for pairId in rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].pairs:
                        new_pos = self.calculate_vertex_position(
                            neutral_vtx_pos[pairId], diff_vtx_pos[vertex_id], mirror_vector
                        )
                        cmds.xform(f"{mesh_node}.vtx[{pairId}]", t=new_pos)

            cmds.select(selection)
            logger.debug("Mirroring mesh finished.")
        except Exception:  # pylint: disable=try-except-raise
            raise
        finally:
            cmds.undoInfo(closeChunk=True)

    def flip_mesh(self, rig, mesh_name, mirror_direction, mesh_node, vtx_ids):
        """
        Flips asymmetric mesh in scene.

        Flips all vertices for selected mesh, or just selected vertices.
        @param characterDef: Character whose mesh is being flipped. (CharacterDef)
        @param meshNode: Selected mesh node. (DagNode)
        @param vtxIds: List of ids of selected vertices. (int[])
        @param mesh: Mesh which is being flipped. (Mesh)
        @param mfmInfo: Mirror info. (maya.node.MayaFlipMirrorInfo)
        @return True if successfully flipped. (boolean)
        """

        logger.debug(f"Flipping mesh: {mesh_node}")

        rig_definition = rig.rig_definition
        rig_mesh = rig_definition.get_mesh_by_name(mesh_name)
        try:
            if not rig_mesh.maya_vtx_pairs:
                raise RuntimeError(f"Mesh {mesh_name} doesn't have symmetry info.")
            if not cmds.polyEvaluate(mesh_node, v=True) == len(rig_mesh.maya_vtx_pairs.vtx_pairs):
                raise RuntimeError("Wrong symmetry mesh selected.")
        except AttributeError as error:
            raise RuntimeError(f"Mesh {mesh_name} doesn't exist in the rig.") from error

        try:
            cmds.undoInfo(openChunk=True)
            # save current selection
            selection = cmds.ls(selection=True)

            # get vertex pairs
            logger.debug("Finding vertex pairs for mesh flip.")

            # get vertex positions
            logger.debug("Flipping mesh.")
            neutral_vtx_pos = rig.get_neutral_mesh_vertex_positions(mesh_name)
            pose_vtx_pos = self.get_mesh_vertex_positions(mesh_node)
            diff_vtx_pos = self.calculate_mesh_delta(neutral_vtx_pos, pose_vtx_pos)

            # mirror
            str_vtx = f"{mesh_node}.vtx["
            side = (
                MayaVtxPair.SIDE_LEFT if mirror_direction == MayaSymmetryInfo.LEFT_TO_RIGHT else MayaVtxPair.SIDE_RIGHT
            )
            mirror_plane = MayaSymmetryInfo.get_mirror_plane(rig_definition)
            mirror_vector = [1, 1, 1]
            mirror_vector[mirror_plane] = -1

            for vertex_id in vtx_ids:
                if (
                    rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].side == side
                    and rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].pairs
                ):
                    # set new position to source vertex
                    pair_id = rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].pairs[0]
                    new_pos = self.calculate_vertex_position(
                        neutral_vtx_pos[vertex_id], diff_vtx_pos[pair_id], mirror_vector
                    )
                    cmds.xform(f"{str_vtx}{vertex_id}]", t=new_pos)

                    # set new position to target vertices
                    for pair_id in rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].pairs:
                        new_pos = self.calculate_vertex_position(
                            neutral_vtx_pos[pair_id], diff_vtx_pos[vertex_id], mirror_vector
                        )
                        cmds.xform(f"{str_vtx}{pair_id}]", t=new_pos)
                elif rig_mesh.maya_vtx_pairs.vtx_pairs[vertex_id].side == MayaVtxPair.SIDE_CENTRAL:
                    new_pos = self.calculate_vertex_position(
                        neutral_vtx_pos[vertex_id], diff_vtx_pos[vertex_id], mirror_vector
                    )
                    cmds.xform(f"{str_vtx}{vertex_id}]", t=new_pos)

            cmds.select(selection)
            logger.debug("Flipping mesh finished.")
        except Exception:  # pylint: disable=try-except-raise
            raise
        finally:
            cmds.undoInfo(closeChunk=True)

    def set_to_mesh(self, is_mesh_selected, mesh_node, vtx_ids, vertices):
        """
        Sets mesh to a given pose in the scene.

        Sets all vertices for selected mesh, of just selected vertices.
        @param is_mesh_selected: Indicates whether mesh is selected. (boolean)
        @param mesh_node: Selected mesh node. (DagNode)
        @param vtx_ids: List of ids of selected vertices. (int[])
        @return True if successfully set to neutral. (boolean)
        """

        logger.debug(f"Set mesh to neutral for mesh: {mesh_node}")
        if not cmds.polyEvaluate(mesh_node, v=True) == len(vertices):
            raise RuntimeError("Wrong mesh data provided.")
        cmds.undoInfo(openChunk=True)

        # save current selection
        selection = cmds.ls(selection=True)

        if is_mesh_selected:
            vtx_ids = list(range(len(vertices)))
        vtx_ids = set(vtx_ids)

        sel = om.MSelectionList()
        sel.add(mesh_node)

        dag_path = om.MDagPath()
        sel.getDagPath(0, dag_path)

        mf_mesh = om.MFnMesh(dag_path)
        original_points = om.MPointArray()
        mf_mesh.getPoints(original_points)
        om_points = om.MPointArray()
        for i, vertex in enumerate(vertices):
            if i in vtx_ids:
                om_points.append(om.MPoint(vertex[0], vertex[1], vertex[2]))
            else:
                om_points.append(original_points[i])

        mf_mesh.setPoints(om_points)
        cmds.select(selection)
        cmds.undoInfo(closeChunk=True)
        logger.debug("Mesh set to neutral.")

    def set_to_neutral_mesh(self, rig, mesh_name, is_mesh_selected, mesh_node, vtx_ids):
        neutral_vertices = rig.get_neutral_mesh_vertex_positions(mesh_name)
        self.set_to_mesh(is_mesh_selected, mesh_node, vtx_ids, neutral_vertices)

    def set_to_expression_mesh(self, rig, mesh_name, is_mesh_selected, mesh_node, vtx_ids, expression_name, phase=1):
        sculpt_vertices = rig.get_sculpt_mesh_vertex_positions(mesh_name, expression_name, phase)
        self.set_to_mesh(is_mesh_selected, mesh_node, vtx_ids, sculpt_vertices)

    @staticmethod
    def get_bounding_box(mesh_name):
        dag_path = om.MDagPath()
        sel_list = om.MSelectionList()

        om.MGlobal.getSelectionListByName(mesh_name, sel_list)
        sel_list.getDagPath(0, dag_path)

        return om.MFnDagNode(dag_path).boundingBox()
