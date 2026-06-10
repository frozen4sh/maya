# Copyright Epic Games, Inc. All Rights Reserved.
import logging
from typing import List

import maya.OpenMaya as om
import maya.api.OpenMaya as api_om
import maya.OpenMayaAnim as oma
from maya import cmds

from mh_assemble_lib.control.form import ProcessForm
from mh_assemble_lib.model.dnalib import DNA
from mh_assemble_lib.model.element import Point3, MeshElement, BlendShapeElement
from mh_assemble_lib.impl.maya.properties import MayaConfig
from mh_assemble_lib.impl.maya.scene.util import Util


class MayaBlendShapeHandler:
    """
    Specialized Maya handler for handling blend shapes.
    """

    def __init__(self, dna: DNA, form: ProcessForm, config: MayaConfig):
        self._dna: DNA = dna
        self._form: ProcessForm = form
        self._config: MayaConfig = config
        self._maya_fn_mesh: api_om.MFnMesh = api_om.MFnMesh()
        self._maya_dag_modifier: api_om.MDagModifier = api_om.MDagModifier()

    def create_blend_shapes(self, meshes: List[MeshElement]) -> None:
        """Create blend shape targets and deformer on scene for given mesh."""
        for mesh in meshes:
            logging.info(f"Creating blend shapes for mesh: {mesh.name}.")
            blend_shapes = self._dna.get_blend_shape_targets(mesh.index)
            if blend_shapes:
                # self.add_target_meshes(mesh, blend_shapes)
                # self.add_bs_node(mesh, blend_shapes)
                self.create_bs(mesh, blend_shapes)

    def add_target_meshes(self, mesh: MeshElement, blend_shapes: List[BlendShapeElement]) -> None:
        # create group
        bs_group_name = self._config.get_bs_group_name(mesh.name)
        cmds.group(empty=True, name=bs_group_name)
        cmds.setAttr(f"{bs_group_name}.visibility", 0)
        # create tgts
        for bs in blend_shapes:
            self._add_target_mesh(mesh, bs, bs_group_name)

    def add_bs_node(self, mesh: MeshElement, blend_shapes: List[BlendShapeElement]) -> None:
        logging.debug(f"Creating bs node for mesh: {mesh.name}.")
        bs_node_name = self._config.get_bs_node_name(mesh.name)
        cmds.select([bs.name for bs in blend_shapes], replace=True)
        cmds.select(mesh.name, add=True)
        cmds.blendShape(name=bs_node_name)
        bs_group_name = self._config.get_bs_group_name(mesh.name)
        cmds.delete(bs_group_name)

    def _add_target_mesh(self, mesh: MeshElement, bs: BlendShapeElement, grp_name: str) -> None:
        logging.debug(f"Adding target mesh: {bs.name}.")
        # get target vertex postions
        tgt_vtx = self._get_target_vertex_positions(mesh.index, bs.tgt_index)
        # create
        mesh_obj = self._maya_fn_mesh.create(tgt_vtx, mesh.poly_faces, mesh.poly_connections)
        # rename
        bs.name = self._config.get_bs_channel_name(mesh.name, bs.name, self._form.combine_bs_name)
        self._maya_dag_modifier.renameNode(mesh_obj, bs.name)
        self._maya_dag_modifier.doIt()
        # group
        cmds.parent(bs.name, grp_name)

    def _get_target_vertex_positions(self, mesh_index: int, tgt_index: int) -> List[Point3]:
        scene_orient = self._config.scene_orient
        tgt_vtx = self._dna.get_vertex_positions(mesh_index)
        deltas = self._dna.get_blend_shape_deltas(mesh_index, tgt_index)
        for delta in deltas:
            tgt_vtx[delta.vtx_index].vector_add(delta.delta)
        return [Util.point3_to_mpoint(p, scene_orient) for p in tgt_vtx]

    def create_bs(self, mesh: MeshElement, blend_shapes: List[BlendShapeElement]) -> None:
        scene_orient = self._config.scene_orient
        # create duplicate template target
        neutral_node = Util.get_mobject(mesh.name)
        duplicate_name = cmds.duplicate(mesh.name)[0]
        duplicate_node = Util.get_mobject(duplicate_name)
        neutral_shape = Util.get_shape(neutral_node)
        duplicate_shape = Util.get_shape(duplicate_node)

        # create bs deformer
        mf_blend_shape = oma.MFnBlendShapeDeformer()
        bs_name = om.MFnDependencyNode(mf_blend_shape.create(neutral_node)).name()
        sel = api_om.MSelectionList()
        sel.add(bs_name, 0)
        bs_node = api_om.MFnDependencyNode(sel.getDependNode(0))

        # create blend shape channels
        for i, bs in enumerate(blend_shapes):
            mf_blend_shape.addTarget(neutral_shape, i, duplicate_shape, 1.0)
            bs.name = self._config.get_bs_channel_name(mesh.name, bs.name, self._form.combine_bs_name)
            cmds.aliasAttr(bs.name, f"{bs_name}.w[{i}]")
        cmds.delete(duplicate_name)

        # set blend shape deltas
        for i, bs in enumerate(blend_shapes):
            plug = (
                bs_node.findPlug("inputTarget", False)
                .elementByPhysicalIndex(0)
                .child(0)
                .elementByPhysicalIndex(i)
                .child(0)
                .elementByPhysicalIndex(0)
            )
            plug_indices = plug.child(4)
            plug_values = plug.child(3)

            delta_indices = self._dna.get_blend_shape_delta_indices(mesh.index, bs.tgt_index)
            delta_values = self._dna.get_blend_shape_delta_values(mesh.index, bs.tgt_index)
            if delta_indices and delta_values:
                cbs_data_tuple = zip(delta_indices, delta_values)
                cbs_data_tuple = sorted(cbs_data_tuple, key=lambda x: x[0])
                delta_indices, delta_values = (list(t) for t in zip(*cbs_data_tuple))
            delta_values_up = [Util.point3_to_position(p, scene_orient).as_tuple() for p in delta_values]

            array_indices = api_om.MIntArray(delta_indices)
            array_values = api_om.MPointArray(delta_values_up)
            dg_component_fn = api_om.MFnComponentListData()
            dg_component_data = dg_component_fn.create()
            single_component_fn = api_om.MFnSingleIndexedComponent()
            single_component_data = single_component_fn.create(api_om.MFn.kMeshVertComponent)
            single_component_fn.addElements(array_indices)
            if not single_component_data.isNull():
                dg_component_fn.add(single_component_data)
                plug_indices.setMObject(dg_component_data)
            point_array_fn = api_om.MFnPointArrayData()
            point_array_data = point_array_fn.create(array_values)
            if not point_array_data.isNull():
                plug_values.setMObject(point_array_data)
        # rename
        cmds.rename(bs_name, self._config.get_bs_node_name(mesh.name))
