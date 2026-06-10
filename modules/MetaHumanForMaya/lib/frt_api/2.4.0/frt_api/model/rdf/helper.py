# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

from typing import cast

import rdf
from rdf_model.model.items import ExpressionType
from rdf_model.model.definition import (
    RigDefinition,
    SumExpressionFunction,
    ExpressionFunctionType,
    SplitExpressionFunction,
    SubtractExpressionFunction,
)

from frt_api.model.maya.symmetry import MayaVtxPair, MayaVtxPairs
from frt_api.model.rig_definition.map import Map, MapType, MapInExpression
from frt_api.model.rig_definition.psd import PsdNet, AssemblingPsd, PsdDefinition
from frt_api.model.rig_definition.core import DataHolder, RangeFloatAttr
from frt_api.model.rig_definition.mask import Mask
from frt_api.model.rig_definition.mesh import (
    Mesh,
    SplitMap,
    LodMeshes,
    MeshInExpression,
)
from frt_api.model.rig_definition.joint import Joint, JointGroup, SplitJoint
from frt_api.model.rig_definition.shader import Shader, ShaderInput
from frt_api.model.rig_definition.expression import Expression
from frt_api.model.rig_definition.skin_weights import SkinningData, SkinTransferData
from frt_api.model.rig_definition.animated_maps import (
    MapInExpression as AnimatedMapInExpression,
)
from frt_api.model.rig_definition.rig_definition import RigDefinition as FRigDef
from frt_api.model.rig_definition.expression_function import (
    SumExpFunc,
    DerivedExpFunc,
    DifferenceExpFunc,
    ExpressionFunction,
    ExpressionMultiplier,
)


class FrtDefinition(FRigDef):
    pass


# FRT helper class


class FrtJoint(Joint):
    pass


class FrtJointGroup(JointGroup):
    pass


class FrtSplitJoint(SplitJoint):
    pass


class FrtDataHolder(DataHolder):
    pass


class FrtMesh(Mesh):
    pass


class FrtSplitMap(SplitMap):
    pass


class FrtMeshInExpression(MeshInExpression):
    pass


class FrtExpression(Expression):
    pass


class FrtRangeFloatAttr(RangeFloatAttr):
    pass


class FrtMapInExpression(MapInExpression):
    pass


class FrtAnimatedMapInExpression(AnimatedMapInExpression):
    pass


class FrtMask(Mask):
    pass


class FrtMap(Map):
    pass


class FrtMapType(MapType):
    pass


class FrtExpressionFunction(ExpressionFunction):
    pass


class FrtExpressionMultiplier(ExpressionMultiplier):
    pass


class FrtPsdNet(PsdNet):
    pass


class FrtPsdDefinition(PsdDefinition):
    pass


class FrtLodMeshes(LodMeshes):
    pass


class FrtShader(Shader):
    pass


class FrtShaderInput(ShaderInput):
    pass


class FrtMayaVtxPairs(MayaVtxPairs):
    pass


class FrtMayaVtxPair(MayaVtxPair):
    pass


class FrtAssemblingPsd(AssemblingPsd):
    pass


class FrtSkinTransferData(SkinTransferData):
    pass


class FrtSkinningData(SkinningData):
    pass


COLOR_MAPPING = {
    0: [0.0, 0.0, 0.0],
    1: [0.0, 0.0, 0.0],
    2: [0.25, 0.25, 0.25],
    3: [0.6, 0.6, 0.6],
    4: [0.607, 0.0, 0.157],
    5: [0.0, 0.016, 0.376],
    6: [0.0, 0.0, 1.0],
    7: [0.0, 0.275, 0.098],
    8: [0.149, 0.0, 0.263],
    9: [0.783, 0.0, 0.784],
    10: [0.541, 0.282, 0.2],
    11: [0.247, 0.137, 0.122],
    12: [0.6, 0.149, 0.0],
    13: [1.0, 0.0, 0.0],
    14: [0.0, 1.0, 0.0],
    15: [0.0, 0.255, 0.6],
    16: [1.0, 1.0, 1.0],
    17: [1.0, 1.0, 0.0],
    18: [0.392, 0.863, 1.0],
    19: [0.263, 1.0, 0.639],
    20: [1.0, 0.69, 0.69],
    21: [0.894, 0.675, 0.475],
    22: [1.0, 1.0, 0.388],
    23: [0.0, 0.6, 0.329],
    24: [0.63, 0.414, 0.189],
    25: [0.621, 0.63, 0.183],
    26: [0.409, 0.63, 0.189],
    27: [0.189, 0.63, 0.365],
    28: [0.189, 0.63, 0.63],
    29: [0.189, 0.405, 0.63],
    30: [0.436, 0.189, 0.63],
}

import math


def euclidean_distance(arr1, arr2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(arr1, arr2)))


def find_nearest_key(mapping, input_array):
    min_distance = float("inf")
    best_key = None

    for key, value_array in mapping.items():
        if len(value_array) != len(input_array):
            continue  # Skip if dimensions don't match
        dist = euclidean_distance(value_array, input_array)
        if dist < min_distance:
            min_distance = dist
            best_key = key

    return best_key


def map_frt(rig_definition: RigDefinition, reader: rdf.RigDefinitionBinaryStreamReader) -> FrtDefinition:
    frt_rig_def = FrtDefinition()

    joint_list = []
    joint_root_list = []

    for jnt in rig_definition.joints:
        joint = FrtJoint()
        joint.name = jnt.name
        joint.override_enabled = 1
        joint.override_color = find_nearest_key(COLOR_MAPPING, jnt.color)
        joint.radius = round(jnt.radius, 2)
        joint_list.append(joint)
        if jnt.index == 0:
            joint_root_list.append(joint)

    for chd_ind, par_ind in reversed(list(enumerate(rig_definition.get_joint_hierarchy()))):
        if chd_ind == 0:
            continue
        parent = joint_list[par_ind]
        child = joint_list[chd_ind]
        child.parent = parent
        parent.children.insert(0, child)

    frt_rig_def.joints = FrtDataHolder(joint_root_list)

    split_joint_groups_list = {}
    for jnt_grp in rig_definition.joint_groups:
        joint_group = FrtJointGroup()
        joint_group.name = jnt_grp.name
        joint_group.joints = [joint_list[jnt.index] for jnt in jnt_grp.joints]
        frt_rig_def.joint_groups.append(joint_group)
        split_joint_groups_list[jnt_grp.name] = joint_group

    for m in rig_definition.meshes:
        mesh = FrtMesh()
        mesh.name = m.name
        frt_rig_def.meshes.append(mesh)

    split_map_list = {}
    for sm in rig_definition.split_maps:
        split_map = FrtSplitMap()
        split_map.name = sm.name
        split_map.value = sm.weights
        split_map.mesh = frt_rig_def.get_mesh_by_name(sm.mesh.name)
        frt_rig_def.split_maps.append(split_map)
        split_map_list[sm.name] = split_map

    expression_list = []
    for exp in rig_definition.expressions:
        expression = FrtExpression()
        expression.name = exp.name
        frt_rig_def.expressions.append(expression)
        expression_list.append(expression)

        expression.id = exp.index
        expression.type = exp.expression_type.value
        expression.phases = sorted(range(exp.phase_count))
        expression.assemble_to_rig = bool(exp.is_exported)
        expression.dirty = False

        for deformer in exp.mesh_deformers:
            mie = FrtMeshInExpression()
            mie.type = deformer.deformation_type.value
            mie.mesh = frt_rig_def.meshes[deformer.mesh.index]
            mie.expression = expression
            expression.meshes_in_expression.append(mie)

        if exp.control:
            expression.expression_attrs.append(
                FrtRangeFloatAttr(
                    exp.control.get_object_name(),
                    exp.control.get_attribute_name(),
                    from_value=exp.control.from_value,
                    to_value=exp.control.to_value,
                )
            )

        for an_map in exp.animated_maps:
            map_in_exp = FrtAnimatedMapInExpression()
            mmap = FrtMap()
            mmap.map_type = FrtMapType()
            mmap.name = an_map.texture_map.name
            mmap.base_map = an_map.texture_map.is_base
            mmap.map_type.name = an_map.texture_map.map_type.name
            map_in_exp.map = mmap
            for msk in an_map.texture_masks:
                frt_msk = FrtMask()
                frt_msk.name = msk.name
                map_in_exp.masks.append(frt_msk)
            expression.maps_in_expression.append(map_in_exp)

        frt_rig_def.expressions[exp.index] = expression

    for exp in rig_definition.expressions:
        expression = cast(FrtExpression, frt_rig_def.get_expression_by_name(exp.name))
        if exp and exp.function and exp.function.index != -1 and exp.function.index is not None:
            expression_function = FrtExpressionFunction.create_expression_function(exp.function.function_type)
            expression_function.output = expression
            if exp.function.function_type == ExpressionFunctionType.Split:
                expression_function = cast(DerivedExpFunc, expression_function)
                split_exp_fnc: SplitExpressionFunction = exp.function
                source_exp = expression_list[exp.function.get_input_expressions()[0].index]
                expression_function.input = source_exp
                source_exp.generates.append(expression)

                expression_function.split_maps.extend(
                    [cast(SplitMap, split_map_list.get(sm.name)) for sm in split_exp_fnc.split_maps]
                )  # type: ignore

                for smj in split_exp_fnc.split_joints:
                    split_joint = FrtSplitJoint()
                    split_joint.multiplier = smj.multiplier
                    split_joint.joint_group = split_joint_groups_list.get(smj.joint_group.name)
                    split_joint.rotations = smj.rotation
                    expression_function.split_joints.append(split_joint)
            elif exp.function.function_type == ExpressionFunctionType.Subtract:
                expression_function = cast(DifferenceExpFunc, expression_function)
                sub_exp_fnc: SubtractExpressionFunction = exp.function

                tgt_exp = expression_list[sub_exp_fnc.minuend.expression.index]
                cmx_exp = expression_list[sub_exp_fnc.subtrahend.expression.index]

                expression_function.input1 = tgt_exp
                expression_function.multiplier1 = sub_exp_fnc.minuend.multiplier
                tgt_exp.generates.append(expression)

                expression_function.input2 = cmx_exp
                expression_function.multiplier2 = sub_exp_fnc.subtrahend.multiplier
                cmx_exp.generates.append(expression)
            elif exp.function.function_type == ExpressionFunctionType.Sum:
                expression_function = cast(SumExpFunc, expression_function)
                sum_exp_fnc: SumExpressionFunction = exp.function

                for multi in sum_exp_fnc.elements:
                    expression_function.inputs.append(
                        FrtExpressionMultiplier(expression_list[multi.expression.index], multi.multiplier)
                    )
            frt_exp = frt_rig_def.expressions[exp.index]
            frt_exp.function = expression_function

    psd_net_dict = {}
    for psd_net in rig_definition.psd_nets:
        frt_psd_net = FrtPsdNet()
        frt_psd_net.name = psd_net.name
        frt_psd_net.psd_net_type = 2
        frt_psd_net.output = FrtRangeFloatAttr(
            psd_net.output_expression.control.get_object_name(), psd_net.output_expression.name, 0.0, 1.0, 0.0, 1.0
        )
        frt_psd_net.on_attr = FrtRangeFloatAttr("CTRL_rigLogic", "OffOn", 0.0, 1.0, 0.0, 1.0)
        frt_psd_net.inputs = [
            FrtRangeFloatAttr(
                inp.expression.control.get_object_name(),
                inp.expression.control.get_attribute_name(),
                0.0,
                inp.multiplier,
                0.0,
                1.0,
            )
            for inp in psd_net.inputs
        ]
        frt_rig_def.psd_nets.append(frt_psd_net)
        psd_net_dict.update({frt_psd_net.name: frt_psd_net})

    for psd_def in rig_definition.psd_definitions:
        frt_psd_def = FrtPsdDefinition()
        frt_psd_def.name = psd_def.name
        frt_psd_def.layer = psd_def.layer

        frt_psd_def.complex_pose = expression_list[psd_def.complex_expression.index]
        frt_psd_def.target_pose = expression_list[psd_def.target_expression.index]
        frt_psd_def.corrective_pose = expression_list[psd_def.corrective_expression.index]

    for lod in rig_definition.lods:
        f_lod_meshes = FrtLodMeshes()
        f_lod_meshes.name = f"lod{lod.level}"
        f_lod_meshes.meshes = [m.name for m in lod.meshes]
        frt_rig_def.lod_meshes.append(f_lod_meshes)

    for mask in rig_definition.texture_masks:
        frt_mask = FrtMask()
        frt_mask.name = mask.name
        frt_rig_def.masks.append(frt_mask)

    for map_item in rig_definition.texture_map_types:
        frt_map_type = FrtMapType()
        frt_map_type.name = map_item.name
        frt_rig_def.map_types.append(frt_map_type)

    for maps_item in rig_definition.texture_maps:
        frt_map = FrtMap()
        frt_map.name = maps_item.name
        frt_map.base_map = maps_item.is_base
        frt_map.map_type = maps_item.map_type.name
        frt_rig_def.maps.append(frt_map)

    for shader_item in rig_definition.shaders:
        frt_shader = FrtShader()
        frt_shader.name = shader_item.name
        frt_shader.shader_type = shader_item.shader_type.value

        frt_shader.eccentricity = round(shader_item.parameters.get("eccentricity").value, 2)
        frt_shader.specular_roll_off = round(shader_item.parameters.get("specularRollOff").value, 2)
        frt_shader.specular_color = (
            round(shader_item.parameters.get("specularColorR").value, 2),
            round(shader_item.parameters.get("specularColorG").value, 2),
            round(shader_item.parameters.get("specularColorB").value, 2),
        )
        frt_shader.shader_color = (
            round(shader_item.parameters.get("shaderColorR").value, 2),
            round(shader_item.parameters.get("shaderColorG").value, 2),
            round(shader_item.parameters.get("shaderColorB").value, 2),
        )
        frt_shader.transparency = (
            round(shader_item.parameters.get("transparencyR").value, 2),
            round(shader_item.parameters.get("transparencyG").value, 2),
            round(shader_item.parameters.get("transparencyB").value, 2),
        )

        for inp in shader_item.inputs:
            frt_shader_inp = FrtShaderInput()
            frt_shader_inp.attr_name = inp.name
            frt_shader_inp.map_types.extend([mt for mt in frt_rig_def.map_types if mt.name == inp.map_type.name])
            frt_shader.inputs.append(frt_shader_inp)

        frt_rig_def.shaders.append(frt_shader)

    for mesh in rig_definition.meshes:
        frt_mesh = frt_rig_def.get_mesh_by_name(mesh.name)
        if mesh and frt_mesh and mesh.shader:
            frt_mesh.shader = frt_rig_def.get_shader_by_name(mesh.shader.name)

    for i in range(reader.getDNAJointGroupCount()):
        frt_rig_def.region_joints[reader.getDNAJointGroupName(i)] = [
            reader.getJointName(j) for j in reader.getDNAJointGroupJointIndices(i)
        ]
        frt_rig_def.region_expressions[reader.getDNAJointGroupName(i)] = set()

    joint_region_mapping = {
        joint_name: region_name
        for region_name in frt_rig_def.region_joints
        for joint_name in frt_rig_def.region_joints[region_name]
    }

    for exp in rig_definition.expressions:
        exp_region_joints = [reader.getJointName(j) for j in reader.getJointIndicesAffectedByExpression(exp.index)]
        for jnt_name in exp_region_joints:
            frt_rig_def.region_expressions[joint_region_mapping[jnt_name]].add(exp.name)

    for sym_mesh in rig_definition.symmetry_meshes:
        maya_vtx_pairs = FrtMayaVtxPairs()
        for chd_ind, pair_id in enumerate(sym_mesh.vertex_mapping):
            vtx_pair = FrtMayaVtxPair()
            vtx_pair.id = chd_ind
            vtx_pair.side = sym_mesh.vertex_side[chd_ind].value if sym_mesh.vertex_side[chd_ind].value != 3 else 0
            if sym_mesh.vertex_side[chd_ind].value != 3:
                vtx_pair.pairs.append(pair_id)
            maya_vtx_pairs.vtx_pairs.append(vtx_pair)
        frt_mesh = frt_rig_def.get_mesh_by_name(sym_mesh.mesh.name)
        if frt_mesh:
            frt_mesh.maya_vtx_pairs = maya_vtx_pairs

    for psd_def in rig_definition.psd_definitions:
        frt_psd_def = FrtPsdDefinition()
        frt_psd_def.name = psd_def.name
        frt_psd_def.layer = psd_def.layer

        frt_psd_def.complex_pose = frt_rig_def.get_expression_by_id(psd_def.complex_expression.index)
        if psd_def.complex_expression.function:
            for psd_cmx_elm in psd_def.complex_expression.function.elements:
                if psd_cmx_elm.expression.expression_type in [ExpressionType.Main, ExpressionType.Target]:
                    exp_multi = FrtExpressionMultiplier(expression_list[psd_cmx_elm.expression.index])
                    exp_multi.multiplier = psd_cmx_elm.multiplier
                    frt_psd_def.complex_pose_build.append(exp_multi)
                    frt_psd_def.target_pose_build.append(exp_multi)

        frt_psd_def.target_pose = frt_rig_def.get_expression_by_id(psd_def.target_expression.index)
        frt_psd_def.corrective_pose = frt_rig_def.get_expression_by_id(psd_def.corrective_expression.index)

        for psd_net in rig_definition.psd_nets:
            if psd_net.psd_definition.name == psd_def.name:
                frt_assemblig_psd = FrtAssemblingPsd(
                    expression_list[psd_net.output_expression.index],
                    cast(PsdNet, frt_rig_def.get_psd_net_by_name(psd_net.name)),
                )
                frt_psd_def.assembling_psds.append(frt_assemblig_psd)

        frt_rig_def.add_new_psd_definition(frt_psd_def)

    for skin_data_transfer in rig_definition.skin_transfers:
        frt_skin_data = FrtSkinTransferData()
        frt_skin_data.name = skin_data_transfer.name
        frt_skin_data.geo_base_mesh = skin_data_transfer.geo_mesh.name
        frt_skin_data.skin_base_mesh = skin_data_transfer.source_mesh.name
        for st_mapping in skin_data_transfer.mapping:
            frt_skin_data.mapping[st_mapping.target_joint.name] = [j.name for j in st_mapping.source_joints]

        frt_rig_def.skin_transfer_data.append(frt_skin_data)

    return frt_rig_def
