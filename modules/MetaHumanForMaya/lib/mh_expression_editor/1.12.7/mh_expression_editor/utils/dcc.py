# Copyright Epic Games, Inc. All Rights Reserved.

import re
import contextlib
from math import radians

import dnacalib2 as dnacalib
import maya.OpenMaya as om
import maya.api.OpenMaya as om2
import maya.OpenMayaAnim as oma
import maya.api.OpenMayaAnim as oma2
from maya import mel, cmds
from frt_api import ProgressEnd, ProgressStart, ProgressUpdate
from frt_api.rig import ExpressionMayaHandler
from frt_api.maya import MeshMayaHandler, JointMayaHandler, SkinWeightsMayaHandler
from frt_api.file.dna_file import DNAFileHandler
from frt_api.model.maya.joint import MayaJointDataHolder
from frt_api.model.maya.symmetry import MayaVtxPair, MayaSymmetryInfo

from . import general
from ..resource import Resources

TRANSLATION_ATTRIBUTES = ["tx", "ty", "tz"]
ROTATION_ATTRIBUTES = ["rx", "ry", "rz"]
SCALE_ATTRIBUTES = ["sx", "sy", "sz"]

ATTRS = TRANSLATION_ATTRIBUTES + ROTATION_ATTRIBUTES + SCALE_ATTRIBUTES

FACIAL_ROOT_JOINTS = ["FACIAL_C_FacialRoot", "FACIAL_C_Neck1Root", "FACIAL_C_Neck2Root"]

GROUPS_JOINT_LAYER_MAPPING = {
    "edit_grp": "edit_joints_layer",
    "phase_grp": "phase_joints_layer",
}

logger = general.get_logger()


def delete_workspace_control(control):
    if cmds.workspaceControl(control, q=True, exists=True):
        cmds.workspaceControl(control, e=True, close=True)
        cmds.deleteUI(control, control=True)


def get_root_joint_name(rig):
    return rig.rig_definition.joints[0].name


def get_joint_long_name(rig, joint_name):
    joint_names = [rig.dna_reader.getJointName(i) for i in range(rig.dna_reader.getJointCount())]
    joint_index = joint_names.index(joint_name)

    result = ""

    parent_index = rig.dna_reader.getJointParentIndex(joint_index)
    while parent_index != joint_index:
        result = f"|{rig.dna_reader.getJointName(parent_index)}" + result
        joint_index = parent_index
        parent_index = rig.dna_reader.getJointParentIndex(joint_index)

    return result + f"|{joint_name}"


def add_neutral_joints(rig):
    emh = ExpressionMayaHandler(rig)
    emh.set_neutral_joints(rig)


def add_neutral_mesh(rig, mesh_name):
    emh = ExpressionMayaHandler(rig)
    mmh = MeshMayaHandler()

    definition_mesh = rig.rig_definition.get_mesh_by_name(mesh_name)
    mesh_node = mmh.create_neutral_mesh(rig, mesh_name)

    _, shader_engine = emh._create_blinn_shader(definition_mesh.shader)
    cmds.select(mesh_node, replace=True)
    cmds.sets(edit=True, forceElement=shader_engine)
    return mesh_node


def add_skin_weights(rig, mesh_name, mesh_node):
    swmh = SkinWeightsMayaHandler()

    maya_skin_weights = rig.get_maya_skin_weights(mesh_name)
    swmh.create_skin_cluster(
        maya_skin_weights.joints,
        mesh_node,
        mesh_node + swmh.SUFFIX_SKINCLUSTER,
        maya_skin_weights.no_of_influences,
        maya_skin_weights.skinning_method,
    )

    swmh.set_skin_weights_to_scene(mesh_node, maya_skin_weights)


def get_skin_cluster_node_name(mesh_node):
    swmh = SkinWeightsMayaHandler()
    return swmh.get_skin_cluster(mesh_node)


def add_corrective_mesh(rig, mesh_name, expression_name, phase):
    mmh = MeshMayaHandler()
    mmh.create_cbs_mesh(rig, mesh_name, expression_name, phase)


def add_blend_shape_node(rig, mesh_name, mesh_node):
    mmh = MeshMayaHandler()

    mesh_nodes = []
    expressions = rig.rig_definition.expressions
    num = len(expressions)

    if mesh_name == "head_lod0_mesh":
        ProgressStart.emit(max_value=num)

    for expr in expressions:
        if mesh_name == "head_lod0_mesh":
            ProgressUpdate.emit(status=f"{expr}")
        if expr.assemble_to_rig:
            for mie in expr.meshes_in_expression:
                if mie.is_blends() and mie.mesh.name == mesh_name:
                    for phase_no in expr.get_phase_numbers():
                        node = mmh.create_cbs_mesh(rig, mie.mesh.name, expr.name, phase_no)
                        renamed_node = cmds.rename(node, expr.get_bs_channel_name(phase_no))
                        mesh_nodes.append(renamed_node)

    if mesh_nodes:
        cmds.select(mesh_nodes, r=True)
        cmds.select(mesh_node, add=True)
        cmds.blendShape(name=mesh_name + mmh.SUFFIX_BS, frontOfChain=True)
        cmds.delete(mesh_nodes)

    if mesh_name == "head_lod0_mesh":
        ProgressEnd.emit()


def optimized_add_blend_shape_node(
    rig,
    mesh_name,
    mesh_node,
    blend_shapes,
    blend_shape_node_name=None,
    skin_cluster_prefix="",
    cbs_deltas=None,
    cbs_vertex_indices=None,
):
    if not blend_shape_node_name:
        blend_shape_node_name = f"{mesh_name}_blendShapes"

    sel = om.MSelectionList()
    sel.add(mesh_node)
    neutral_node = om.MObject()
    sel.getDependNode(0, neutral_node)
    duplicate_name = cmds.duplicate(mesh_node)[0]
    sel = om.MSelectionList()
    sel.add(duplicate_name)
    duplicate_node = om.MObject()
    sel.getDependNode(0, duplicate_node)

    fn_item = om.MFnDagNode(neutral_node)
    neutral_shape = fn_item.child(0)

    fn_item = om.MFnDagNode(duplicate_node)
    duplicate_shape = fn_item.child(0)

    mf_blend_shape = oma.MFnBlendShapeDeformer()
    blend_shape_name = om.MFnDependencyNode(mf_blend_shape.create(neutral_node)).name()

    sel = om2.MSelectionList()
    sel.add(blend_shape_name, 0)
    blend_shape_node = om2.MFnDependencyNode(sel.getDependNode(0))

    for i, expression_name in enumerate(blend_shapes):
        mf_blend_shape.addTarget(neutral_shape, i, duplicate_shape, 1.0)
        cmds.aliasAttr(expression_name, f"{blend_shape_name}.w[{i}]")

    cmds.delete(duplicate_name)

    for i, expression_name in enumerate(blend_shapes):
        plug = (
            blend_shape_node.findPlug("inputTarget", False)
            .elementByPhysicalIndex(0)
            .child(0)
            .elementByPhysicalIndex(i)
            .child(0)
            .elementByPhysicalIndex(0)
        )
        points_plug = plug.child(3)
        indices_plug = plug.child(4)
        if cbs_vertex_indices and expression_name in cbs_vertex_indices:
            indices = cbs_vertex_indices[expression_name]
        else:
            indices = rig.rig.getCorrectiveBlendShapeVertexIndices(
                rig.expression_indices[expression_name], 0, rig._mesh_indices[mesh_name]
            )
        if cbs_deltas and expression_name in cbs_deltas:
            deltas = [list(value) for value in cbs_deltas[expression_name]]
        else:
            deltas = rig.rig.getCorrectiveBlendShapeDeltas(
                rig.expression_indices[expression_name], 0, rig._mesh_indices[mesh_name]
            )

        if indices and deltas:
            indices, deltas = (list(t) for t in zip(*sorted(zip(indices, deltas), key=lambda x: x[0])))

        index_list = om2.MIntArray(indices)
        deltas_list = om2.MPointArray(deltas)
        dg_component_fn = om2.MFnComponentListData()
        dg_component_data = dg_component_fn.create()
        single_component_fn = om2.MFnSingleIndexedComponent()
        single_component_data = single_component_fn.create(om2.MFn.kMeshVertComponent)
        single_component_fn.addElements(index_list)
        if not single_component_data.isNull():
            dg_component_fn.add(single_component_data)
            indices_plug.setMObject(dg_component_data)
        point_array_fn = om2.MFnPointArrayData()
        point_array_data = point_array_fn.create(deltas_list)
        if not point_array_data.isNull():
            points_plug.setMObject(point_array_data)

    cmds.rename(blend_shape_name, blend_shape_node_name)
    cmds.reorderDeformers(f"{skin_cluster_prefix}{mesh_name}_skinCluster", blend_shape_node_name, mesh_node)


def load_and_connect_gui(
    rig, left_arm_joint_name, eye_aim_control_name, right_eye_control_name, gui_object_name, up_axis, rotation
):
    cmds.file(Resources().gui_file_path, i=True, returnNewNodes=True)
    cmds.file(Resources().analog_gui_file_path, i=True, returnNewNodes=True)

    expressions = []
    for exp in rig.rig_definition.expressions:
        if exp.assemble_to_rig:
            expressions.append(exp)

    for expression in expressions:
        for exp_attr in expression.expression_attrs:
            if cmds.objExists(exp_attr.object_name) and not cmds.attributeQuery(
                exp_attr.attr_name, node=exp_attr.object_name, exists=True
            ):
                cmds.addAttr(
                    exp_attr.object_name,
                    longName=exp_attr.attr_name,
                    keyable=True,
                    attributeType="float",
                    minValue=exp_attr.min_value,
                    maxValue=exp_attr.max_value,
                )

    # position gui to char eyes level
    aim = cmds.xform(eye_aim_control_name, q=1, t=1, ws=1)[1]
    eye = cmds.xform(right_eye_control_name, q=1, t=1, ws=1)[1]
    gui = cmds.xform(gui_object_name, q=1, t=1, ws=1)
    arm = cmds.xform(
        f"head_grp{get_joint_long_name(rig, left_arm_joint_name)}",
        q=1,
        t=1,
        ws=1,
    )

    translation = [arm[0], gui[1] + (aim - eye), gui[2]]
    if up_axis == "z":
        translation = [arm[0], gui[2], gui[1] + (aim - eye)]

    cmds.xform(gui_object_name, t=translation)
    cmds.xform(gui_object_name, ro=rotation, relative=True)

    aas = general.source_module("aas", Resources().aas_file_path)
    aas.run_after_assemble("", "", rotation=rotation)

    root_nodes = [
        node
        for node in cmds.ls()
        if not cmds.listRelatives(node, parent=True)
        and "transform" in cmds.nodeType(node, inherited=True)
        and not cmds.objectType(f"{node}|{cmds.listRelatives(node)[0]}", isType="camera")
        and "_grp" not in node
    ]

    cmds.select(root_nodes, replace=True)
    cmds.group(name="head_rig_grp")


def assemble_rig_editing_scene(
    rig, left_arm_joint_name, eye_aim_control_name, right_eye_control_name, gui_object_name, up_axis, rotation
):
    ProgressStart.emit(max_value=2)
    cmds.upAxis(ax=up_axis)
    ProgressUpdate.emit(status="New file...")
    cmds.file(newFile=True, force=True)

    ProgressUpdate.emit(status="Adding neutral joints")
    add_neutral_joints(rig)

    ProgressEnd.emit()

    root_joint_name = get_root_joint_name(rig)

    mesh_nodes = []
    mesh_node_mapping = {}
    meshes = rig.rig_definition.get_dna_mesh_names()
    ProgressStart.emit(max_value=len(meshes))
    for mesh in meshes:
        ProgressUpdate.emit(status=f"Initializing mesh: {mesh}")
        mesh_node = add_neutral_mesh(rig, mesh)
        ProgressUpdate.emit(status=f"Adding skin to mesh: {mesh}", hold=True)
        add_skin_weights(rig, mesh, mesh_node)
        mesh_nodes.append(mesh_node)
        mesh_node_mapping[mesh] = mesh_node
    ProgressEnd.emit()

    ProgressStart.emit(max_value=5)

    ProgressUpdate.emit(status="Getting head group")
    cmds.select(root_joint_name, mesh_nodes, replace=True)
    head_group = cmds.group(name="head_grp")

    ProgressUpdate.emit(status="Duplicating edit group")
    edit_group = cmds.duplicate(head_group, name="edit_grp", upstreamNodes=True)[0]
    for node in cmds.ls("|edit_grp|*"):
        if cmds.nodeType(node) != "joint":
            mesh_name = node.split("|")[1]
            cmds.rename(get_skin_cluster_node_name(node), f"edit_{mesh_name}_skinCluster")

    ProgressUpdate.emit(status="Duplicating preview group")
    cmds.duplicate(head_group, name="preview_grp", upstreamNodes=True)
    for node in cmds.ls("|preview_grp|*"):
        if cmds.nodeType(node) != "joint":
            mesh_name = node.split("|")[1]
            cmds.rename(get_skin_cluster_node_name(node), f"preview_{mesh_name}_skinCluster")

    ProgressUpdate.emit(status="Duplicating phase group")
    cmds.duplicate(head_group, name="phase_grp", upstreamNodes=True)
    for node in cmds.ls("|phase_grp|*"):
        if cmds.nodeType(node) != "joint":
            mesh_name = node.split("|")[1]
            cmds.rename(get_skin_cluster_node_name(node), f"phase_{mesh_name}_skinCluster")

    preview_mesh_names = [rig.dna_reader.getMeshName(i) for i in rig.dna_reader.getMeshIndicesForLOD(0)]
    for node in cmds.ls("preview_grp|*"):
        mesh_name = node.split("|")[-1]
        if cmds.nodeType(node) == "mesh" and mesh_name not in preview_mesh_names:
            cmds.delete(node)

    ProgressEnd.emit()

    blend_shapes_per_mesh = {}
    for i in range(rig.dna_reader.getMeshBlendShapeChannelMappingCount()):
        mesh_blend_shape_channel_mapping = rig.dna_reader.getMeshBlendShapeChannelMapping(i)
        if rig.dna_reader.getMeshName(mesh_blend_shape_channel_mapping.meshIndex) not in blend_shapes_per_mesh:
            blend_shapes_per_mesh[rig.dna_reader.getMeshName(mesh_blend_shape_channel_mapping.meshIndex)] = []
        blend_shapes_per_mesh[rig.dna_reader.getMeshName(mesh_blend_shape_channel_mapping.meshIndex)].append(
            rig.dna_reader.getBlendShapeChannelName(mesh_blend_shape_channel_mapping.blendShapeChannelIndex)
        )

    ProgressStart.emit(max_value=len(blend_shapes_per_mesh))
    for mesh_name, blend_shapes in blend_shapes_per_mesh.items():
        ProgressUpdate.emit(status=mesh_name)
        optimized_add_blend_shape_node(rig, mesh_name, f"|head_grp|{mesh_node_mapping[mesh_name]}", blend_shapes)
    ProgressEnd.emit()

    ProgressStart.emit(max_value=5)

    ProgressUpdate.emit(status="Initializing expressions")
    sculpt_meshes = set()
    for expression in rig.rig_definition.expressions:
        if expression.assemble_to_rig:
            for mie in expression.meshes_in_expression:
                if mie.is_blends():
                    sculpt_meshes.add(mie.mesh.name)

    ProgressUpdate.emit(status="Initializing mesh sculpts")
    for mesh in sculpt_meshes:
        cmds.duplicate(f"{edit_group}|{mesh}", n=f"sculpt_{mesh}")

    ProgressUpdate.emit(status="Adding layers")
    add_layers(rig)

    ProgressUpdate.emit(status="Loading gui")
    load_and_connect_gui(
        rig, left_arm_joint_name, eye_aim_control_name, right_eye_control_name, gui_object_name, up_axis, rotation
    )

    ProgressUpdate.emit(status="Setting up lods")
    cmds.setAttr("edit_grp.visibility", 0)
    cmds.setAttr("preview_grp.visibility", 0)
    cmds.setAttr("phase_grp.visibility", 0)
    for lod in rig.rig_definition.lod_meshes[1:]:
        for mesh in lod.meshes:
            cmds.setAttr(f"head_grp|{mesh}.visibility", 0)
            cmds.setAttr(f"edit_grp|{mesh}.visibility", 0)
            cmds.setAttr(f"preview_grp|{mesh}.visibility", 0)
            cmds.setAttr(f"phase_grp|{mesh}.visibility", 0)

    ProgressEnd.emit()


def ensure_plugin_available(plugin_name):
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        cmds.loadPlugin(plugin_name)


def add_dna_calib_node(
    node_name,
    dna_file_path,
    rdf_file_path,
    cbs_pruning_threshold,
    joint_pruning_threshold,
    head_main_exp,
    neck_joints,
    neck_joints_values,
    rotation,
):
    ensure_plugin_available("DNACalibMayaPlugin")
    cmds.initializeNode(
        nodeName=node_name,
        dnaPath=dna_file_path,
        rdfPath=rdf_file_path,
        cbsPruning=cbs_pruning_threshold,
        jntPruning=joint_pruning_threshold,
        headTurnsMain=head_main_exp,
        neckJointsNames=neck_joints,
        neckJointsValues=neck_joints_values,
        rigOrientation=rotation,
    )


def save_dna_from_node(node_name, dna_file_path):
    cmds.saveDNACommand(nodeName=node_name, dnaPath=dna_file_path)


def add_attribute_changed_callback(node, callback):
    cmds.select(clear=True)
    sel = om.MSelectionList()
    sel.add(node)
    obj = om.MObject()
    sel.getDependNode(0, obj)
    return om.MNodeMessage.addAttributeChangedCallback(obj, callback)


def remove_callbacks(callbacks):
    for callback in callbacks:
        with contextlib.suppress(RuntimeError):
            om.MMessage.removeCallback(callback)


def add_callbacks(rig, selected_lods, callback):
    callbacks = []
    cmds.select(rig.get_maya_neutral_joints()[0].name, replace=True, hierarchy=True)
    joints = cmds.ls(selection=True)

    for jnt in joints:
        callbacks.append(add_attribute_changed_callback(jnt, callback))

    for lod in rig.rig_definition.lod_meshes:
        if lod.name in selected_lods:
            callbacks.append(add_attribute_changed_callback(f"{lod.name}", callback))
            for mesh_name in lod.meshes:
                callbacks.append(add_attribute_changed_callback(f"{lod.name}|{mesh_name}", callback))

    cmds.select(clear=True)

    return callbacks


def assemble_skin_editing_scene(
    rig,
    selected_lods,
    callback,
    left_arm_joint_name,
    eye_aim_control_name,
    right_eye_control_name,
    gui_object_name,
    up_axis,
    rotation,
):
    ProgressStart.emit(max_value=3)

    ProgressUpdate.emit(status="Assembling skin editing scene")
    cmds.upAxis(ax=up_axis)
    cmds.file(newFile=True, force=True)

    ProgressUpdate.emit(status="Adding neutral joints")
    add_neutral_joints(rig)
    mesh_nodes = []
    mesh_nodes_per_lod = {}

    root_joint_name = get_root_joint_name(rig)
    for lod in rig.rig_definition.lod_meshes:
        if lod.name in selected_lods:
            mesh_nodes_per_lod[lod.name] = []
            for mesh_name in lod.meshes:
                mesh_node = add_neutral_mesh(rig, mesh_name)
                add_skin_weights(rig, mesh_name, mesh_node)
                mesh_nodes.append(mesh_node)
                mesh_nodes_per_lod[lod.name].append(mesh_node)

    cmds.select(*[mesh_node for mesh_node in mesh_nodes], root_joint_name, replace=True)
    cmds.group(name="head_grp")
    cmds.select(clear=True)

    ProgressUpdate.emit(status="Loading GUI")
    load_and_connect_gui(
        rig, left_arm_joint_name, eye_aim_control_name, right_eye_control_name, gui_object_name, up_axis, rotation
    )

    cmds.parent(root_joint_name, world=True)

    for lod, mesh_nodes in mesh_nodes_per_lod.items():
        cmds.select(*[mesh_node for mesh_node in mesh_nodes], replace=True)
        group = cmds.group(name=lod)
        cmds.parent(group, world=True)

    cmds.delete("head_grp")

    ProgressEnd.emit()

    return add_callbacks(rig, selected_lods, callback)


def add_rig_logic_node(dna_file_path):
    ensure_plugin_available("embeddedRL4")
    mel.eval(f'createEmbeddedNodeRL4 -n "embedded" -dfp "{dna_file_path}"')


def update_skin(rig, meshes):
    swmh = SkinWeightsMayaHandler()
    for mesh in meshes:
        mesh_name = mesh.split("|")[-1]
        skin_weights = swmh.get_skin_weights_from_scene(mesh)
        rig.set_skin_weights(mesh_name, skin_weights)

        # Joints with no influences fix
        weights_in_rig = rig.get_maya_skin_weights(mesh_name)
        starting_joints = set(skin_weights.joints)
        starting_joints.difference_update(weights_in_rig.joints)
        if starting_joints:
            logger.info(f"Adding joints with no influences as zero influences on the last vertex of {mesh_name}.")
            for joint_name in starting_joints:
                joint_index = len(weights_in_rig.joints)
                weights_in_rig.vertices_info[-1].append(joint_index)
                weights_in_rig.vertices_info[-1].append(0.0)
                weights_in_rig.joints.append(joint_name)
        rig.set_skin_weights(mesh_name, weights_in_rig)


def assemble_neutral_editing_scene(rig, geo_view_selected, callback, up_axis):
    cmds.upAxis(ax=up_axis)
    cmds.file(newFile=True, force=True)

    add_neutral_joints(rig)

    for lod in rig.rig_definition.lod_meshes:
        if lod.name in geo_view_selected:
            cmds.group(em=True, name=lod.name)
            for mesh_name in lod.meshes:
                mesh_node = add_neutral_mesh(rig, mesh_name)
                cmds.parent(mesh_node, lod.name)

    return add_callbacks(rig, geo_view_selected, callback)


def update_scene_lower_lods(rig, meshes_to_update):
    for mesh, mesh_node in meshes_to_update.items():
        vertex_positions = rig.get_neutral_mesh_vertex_positions(mesh)
        points = []
        for position in vertex_positions:
            points.append(om2.MPoint(position[0], position[1], position[2]))

        sel = om2.MSelectionList()
        sel.add(mesh_node)
        dag_path = sel.getDagPath(0)

        mf_mesh = om2.MFnMesh(dag_path)
        mf_mesh.setPoints(points)


def camera_position():
    cmds.viewFit("persp", f=1, all=True)


def rotate_point(point, rotation):
    original_matrix = om2.MTransformationMatrix()
    original_matrix.setTranslation(om2.MVector(point), om2.MSpace.kWorld)
    rotation_matrix = om2.MTransformationMatrix()
    rotation_matrix.setRotation(om2.MEulerRotation(list(map(radians, rotation))))
    original_matrix = om2.MTransformationMatrix(original_matrix.asMatrix() * rotation_matrix.asMatrix())
    rotated_point = original_matrix.translation(om2.MSpace.kWorld)

    return [rotated_point.x, rotated_point.y, rotated_point.z]


def update_volumetric_joints(mesh_name, volumetric_joints_mapping, rotation):
    for joint_name, (vertex_id, delta) in volumetric_joints_mapping.items():
        vertex_position = cmds.xform(
            f"{mesh_name}.vtx[{vertex_id}]",
            translation=True,
            worldSpace=True,
            query=True,
        )
        joint_position = [v + d for v, d in zip(vertex_position, rotate_point(delta, rotation))]
        cmds.xform(joint_name, worldSpace=True, translation=joint_position)


def update_surface_joints(mesh_name, surface_joints_mapping):
    for joint_name, vertex_id in surface_joints_mapping.items():
        vertex_position = cmds.xform(
            f"{mesh_name}.vtx[{vertex_id}]",
            translation=True,
            worldSpace=True,
            query=True,
        )
        cmds.xform(joint_name, worldSpace=True, translation=vertex_position)


def get_mesh_vertex_positions(mesh_name):
    mmh = MeshMayaHandler()

    return mmh.get_mesh_vertex_positions(mesh_name, world_space=True)


def get_object_uuid(name):
    matched = cmds.ls(name, uuid=True)
    if not matched:
        raise RuntimeError(f"Could not find UUID for object: {name}")
    return matched[0]


def select_object(objects):
    names = []
    for uuid in objects:
        matched = cmds.ls(uuid, uuid=True)
        name = matched[0]
        names.append(name)
    cmds.select(clear=True)
    cmds.select(names)


def select_objects_by_name(names):
    cmds.select(names, replace=True)


def check_scene_for_object_by_name(name):
    return cmds.objExists(name)


def get_selected_from_scene():
    return cmds.ls(selection=True, long=True)


def duplicate_mesh(mesh_to_duplicate, parent_group, translation_value=None, layer_name=None):
    mesh_name = mesh_to_duplicate.split["|"][-1]
    duplicate_mesh_node = cmds.duplicate(mesh_to_duplicate, n=f"duplicate_{mesh_name}")[0]
    cmds.parent(duplicate_mesh_node, parent_group)

    for attr in ATTRS:
        cmds.setAttr(f"{duplicate_mesh_node}.{attr}", lock=False)
    cmds.select(duplicate_mesh_node, replace=True)

    if translation_value:
        cmds.setAttr(
            f"{duplicate_mesh_node}.tx", len(cmds.listRelatives(parent_group, children=True)) * translation_value
        )
    if layer_name:
        cmds.editDisplayLayerMembers(layer_name, duplicate_mesh_node, nr=True)


def transfer_vertex_positions(main_mesh, new_mesh):
    cmds.undoInfo(openChunk=True)
    cmds.select(new_mesh, replace=True)
    cmds.select(main_mesh, add=True)

    bs_name = cmds.blendShape()[0]
    cmds.blendShape(bs_name, e=True, weight=(0, 1))
    delete_history(main_mesh)
    cmds.select(clear=True)
    cmds.undoInfo(closeChunk=True)


def validate_mesh_vertex_selection():
    is_mesh = True
    vtx_ids = []

    selection = cmds.ls(selection=True, flatten=True, long=True)
    if not selection:
        logger.warning("No valid selection for mesh manipulation.")
        return

    selection_string = str(selection[0])
    if re.match(".*\\.vtx\\[[0-9]*\\]$", str(selection_string)):
        # vertex selection
        for vtx in selection:
            if not re.match(".*\\.vtx\\[[0-9]*\\]$", str(vtx)):
                logger.warning(f"Selected object is not vertex: {vtx}")
                return None
            vtx_id = vtx.split("[")[1].split("]")[0]
            vtx_ids.append(int(vtx_id))
        mesh_node = selection[0].split(".")[0]
        is_mesh = False
    else:
        # mesh selection
        if len(selection) != 1:
            logger.warning("Exactly one mesh has to be selected.")
            return None
        mesh_node = selection[0]
        node_type = cmds.nodeType(mesh_node)
        if node_type != "transform":
            logger.warning("Selected object is not a mesh.")
            return None
        vtx_count = cmds.polyEvaluate(mesh_node, vertex=True)
        if not isinstance(vtx_count, int):
            logger.warning("Selected object is not a mesh.")
            return None
        vtx_ids = list(range(vtx_count))
    return is_mesh, mesh_node, vtx_ids


def mirror_skin(rig, rig_mesh_name, mesh_node, vtx_ids, mirror_direction):
    swmh = SkinWeightsMayaHandler()
    mirror_direction = (
        MayaSymmetryInfo.LEFT_TO_RIGHT
        if mirror_direction == general.Direction.LEFT_TO_RIGHT
        else MayaSymmetryInfo.RIGHT_TO_LEFT
    )
    mfm_infos = [
        MayaSymmetryInfo(
            MayaSymmetryInfo.NAME_CONTAINS,
            "_L_",
            "_R_",
            mirror_direction,
            MayaSymmetryInfo.JOINT_ORIENTATION_ORIENTATION,
            rig.rig_definition,
        ),
        MayaSymmetryInfo(
            MayaSymmetryInfo.NAME_ENDS_WITH,
            "_l",
            "_r",
            mirror_direction,
            MayaSymmetryInfo.JOINT_ORIENTATION_ORIENTATION,
            rig.rig_definition,
        ),
    ]
    rig_mesh = rig.rig_definition.get_mesh_by_name(rig_mesh_name)
    try:
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(status=f"Mirroring skin {mesh_node}...")
        swmh.mirror_skin_weights(mesh_node, vtx_ids, mfm_infos, rig_mesh.maya_vtx_pairs)
    except (RuntimeError, RuntimeWarning) as e:
        logger.warning(f"Mirroring skinning failed: {e}")
    finally:
        ProgressEnd.emit()


def colorize_differences(vertices_to_paint_by_weight, vertices_to_paint_by_joint, mesh_name):
    """
    Colorizes vertices that have different weight mirroring either by value, or by influence.
    @param vertices_to_paint_by_weight: List of vertex pairs that have different weight values. ([int])
    @param vertices_to_paint_by_joint: List of vertex pairs that have different influences. ([int])
    @param mesh_name: Mesh name. (string)
    @return none
    """

    vtx_paint_weight = []
    vtx_paint_joint = []

    if vertices_to_paint_by_weight:
        for i in range(len(vertices_to_paint_by_weight)):
            vtx_paint_weight.append(mesh_name + ".vtx[" + str(vertices_to_paint_by_weight[i]) + "]")

        cmds.select(vtx_paint_weight, r=True)
        cmds.polyColorPerVertex(rgb=(1.0, 1.0, 0.0), rel=False, colorDisplayOption=True)

    if vertices_to_paint_by_joint:
        for j in range(len(vertices_to_paint_by_joint)):
            vtx_paint_joint.append(mesh_name + ".vtx[" + str(vertices_to_paint_by_joint[j]) + "]")

        cmds.select(vtx_paint_joint, r=True)
        cmds.polyColorPerVertex(rgb=(1.0, 0.0, 0.0), rel=False, colorDisplayOption=True)

    cmds.polyOptions(colorShadedDisplay=True)
    cmds.select(vtx_paint_weight, deselect=True)
    cmds.select(vtx_paint_joint, deselect=True)


def analyze_skin_mirroring(rig, rig_mesh_name, mesh_node, threshold=3):
    rig_mesh = rig.rig_definition.get_mesh_by_name(rig_mesh_name)
    maya_vtx_pairs = rig_mesh.maya_vtx_pairs
    if cmds.polyEvaluate(mesh_node, v=True) != len(maya_vtx_pairs.vtx_pairs):
        logger.warning("Analyze skin weight symmetry failed: Wrong symmetry mesh selected.")
        return

    swmh = SkinWeightsMayaHandler()
    try:
        maya_skin_weights = swmh.get_skin_weights_from_scene(mesh_node)
    except RuntimeWarning as e:
        logger.warning(f"Analyze skin weight symmetry failed: {e}")
        return

    cmds.polyColorPerVertex(rgb=(0.0, 0.5, 0.5), a=1.0, rel=False, colorDisplayOption=True)
    cmds.polyOptions(colorShadedDisplay=True)

    vertices_to_paint_by_weight = []
    vertices_to_paint_by_joint = []
    epsilon = pow(10, -threshold)

    for i in range(len(maya_vtx_pairs.vtx_pairs)):
        if maya_vtx_pairs.vtx_pairs[i].side == MayaVtxPair.SIDE_LEFT:
            left_side_vert = maya_vtx_pairs.vtx_pairs[i].id
            right_side_vert = maya_vtx_pairs.vtx_pairs[i].pairs

            left_info = maya_skin_weights.vertices_info[left_side_vert]
            right_info_list = []

            if right_side_vert:
                for m in range(len(right_side_vert)):
                    right_info_list.append(maya_skin_weights.vertices_info[right_side_vert[m]])

            for j in range(int(len(left_info) / 2)):
                left_jnt = maya_skin_weights.joints[left_info[2 * j]]
                found_corresponding_joint = False

                left_weight = 0.0
                right_weight = 0.0

                for n in range(len(right_info_list)):
                    for k in range(int(len(right_info_list[n]) / 2)):
                        right_jnt = maya_skin_weights.joints[right_info_list[n][2 * k]]

                        # TODO - workaround for different joint symmetry strings
                        if (
                            (left_jnt.endswith("_l") and left_jnt[:-2] + "_r" == right_jnt)
                            or (left_jnt.endswith("_r") and left_jnt == right_jnt[:-2] + "_r")
                            or ("_L_" in left_jnt and left_jnt.replace("_L_", "_R_") == right_jnt)
                            or ("_R_" in left_jnt and left_jnt == right_jnt.replace("_L_", "_R_"))
                            or (
                                not left_jnt.endswith("_l")
                                and not left_jnt.endswith("_r")
                                and "_L_" not in left_jnt
                                and "_R_" not in left_jnt
                                and left_jnt == right_jnt
                            )
                        ):
                            left_weight = left_info[2 * j + 1]
                            right_weight = right_info_list[n][2 * k + 1]

                            found_corresponding_joint = True
                            break

                    if found_corresponding_joint:
                        if abs(left_weight - right_weight) > epsilon:
                            vertices_to_paint_by_weight.append(left_side_vert)
                            vertices_to_paint_by_weight.extend(right_side_vert)
                    else:
                        vertices_to_paint_by_joint.append(left_side_vert)
                        vertices_to_paint_by_joint.extend(right_side_vert)

    if vertices_to_paint_by_weight or vertices_to_paint_by_joint:
        colorize_differences(vertices_to_paint_by_weight, vertices_to_paint_by_joint, mesh_node)

    logger.info(
        f"Total differences found by weight: {repr(len(vertices_to_paint_by_weight))} and by influence: {repr(len(vertices_to_paint_by_joint))}"
    )


def toggle_vertex_shading(mesh_node):
    cmds.polyOptions(
        mesh_node, colorShadedDisplay=not (any(cmds.polyOptions(mesh_node, colorShadedDisplay=True, query=True)))
    )


def mirror_mesh(rig, rig_mesh_name, mesh_node, vtx_ids, mirror_direction):
    mmh = MeshMayaHandler()
    try:
        mirror_direction = (
            MayaSymmetryInfo.LEFT_TO_RIGHT
            if mirror_direction == general.Direction.LEFT_TO_RIGHT
            else MayaSymmetryInfo.RIGHT_TO_LEFT
        )
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(f"Mirroring mesh {mesh_node}...")
        mmh.mirror_mesh(rig, rig_mesh_name, mirror_direction, mesh_node, vtx_ids)
    except RuntimeError as e:
        logger.warning(f"Mirroring mesh failed: {e}")
    finally:
        ProgressEnd.emit()


def flip_mesh(rig, rig_mesh_name, mesh_node, vtx_ids, flip_direction):
    mmh = MeshMayaHandler()
    try:
        flip_direction = (
            MayaSymmetryInfo.LEFT_TO_RIGHT
            if flip_direction == general.Direction.LEFT_TO_RIGHT
            else MayaSymmetryInfo.RIGHT_TO_LEFT
        )
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(f"Flipping mesh {mesh_node}...")
        mmh.flip_mesh(rig, rig_mesh_name, flip_direction, mesh_node, vtx_ids)
    except RuntimeError as e:
        logger.warning(f"Flipping mesh failed: {e}")
    finally:
        ProgressEnd.emit()


def neutralize_mesh(rig, rig_mesh_name, is_mesh, mesh_node, vtx_ids):
    mmh = MeshMayaHandler()
    try:
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(f"Neutralizing mesh {mesh_node}...")
        mmh.set_to_neutral_mesh(rig, rig_mesh_name, is_mesh, mesh_node, vtx_ids)
    except RuntimeError as e:
        logger.warning(f"Neutralizing mesh failed: {e}")
    finally:
        ProgressEnd.emit()


def reset_mesh_to_dna(rig, rig_mesh_name, is_mesh, mesh_node, vtx_ids, expression_name, phase):
    mmh = MeshMayaHandler()
    try:
        phase = 1 if phase is None else phase
        ProgressStart.emit(max_value=1)
        ProgressUpdate.emit(f"Resetting mesh {mesh_node}...")
        mmh.set_to_expression_mesh(rig, rig_mesh_name, is_mesh, mesh_node, vtx_ids, expression_name, phase=phase)
    except RuntimeError as e:
        logger.warning(f"Resetting mesh to MetaHuman DNA shape failed: {e}")
    finally:
        ProgressEnd.emit()


def validate_joint_selection(group_name=None):
    initial_selection = cmds.ls(sl=True)
    selection = initial_selection[:]
    if not selection:
        selection = cmds.ls(type="joint")
        if group_name:
            selection = [joint for joint in selection if joint.startswith(group_name)]
        cmds.select(selection)

    joint_selection = cmds.ls(sl=True, type="joint", long=True)
    if len(selection) != len(joint_selection):
        logger.warning("Not all selected objects are joints.")
        return
    if group_name:
        for joint in selection:
            if not joint.startswith(group_name):
                logger.warning(f"Not all selected objects are from the {group_name} group.")
                return
    return True, initial_selection


def mirror_joints(rig, mirror_direction):
    jmh = JointMayaHandler()
    mirror_direction = (
        MayaSymmetryInfo.LEFT_TO_RIGHT
        if mirror_direction == general.Direction.LEFT_TO_RIGHT
        else MayaSymmetryInfo.RIGHT_TO_LEFT
    )
    symmetry_info = MayaSymmetryInfo(
        MayaSymmetryInfo.NAME_CONTAINS,
        "_L_",
        "_R_",
        mirror_direction,
        MayaSymmetryInfo.JOINT_ORIENTATION_ORIENTATION,
        rig.rig_definition,
    )
    ProgressStart.emit(max_value=1)
    ProgressUpdate.emit("Mirroring joints...")
    try:
        jmh.mirror_joints(rig.get_maya_neutral_joints(), symmetry_info)
    except RuntimeError as e:
        logger.warning(f"Flipping mesh failed: {e}")
    finally:
        ProgressEnd.emit()


def flip_joints(rig, flip_direction):
    jmh = JointMayaHandler()
    flip_direction = (
        MayaSymmetryInfo.LEFT_TO_RIGHT
        if flip_direction == general.Direction.LEFT_TO_RIGHT
        else MayaSymmetryInfo.RIGHT_TO_LEFT
    )
    symmetry_info = MayaSymmetryInfo(
        MayaSymmetryInfo.NAME_CONTAINS,
        "_L_",
        "_R_",
        flip_direction,
        MayaSymmetryInfo.JOINT_ORIENTATION_ORIENTATION,
        rig.rig_definition,
    )
    ProgressStart.emit(max_value=1)
    ProgressUpdate.emit("Flipping joints...")
    try:
        jmh.flip_joints(rig.get_maya_neutral_joints(), symmetry_info)
    except RuntimeError as e:
        logger.warning(f"Flipping mesh failed: {e}")
    finally:
        ProgressEnd.emit()


def neutralize_joints(rig):
    jmh = JointMayaHandler()
    jmh.set_to_neutral_joints(rig.get_maya_neutral_joints())


def reset_joints_to_dna_expression(rig, expression_name, phase):
    jmh = JointMayaHandler()
    phase = 1 if phase is None else phase
    jmh.set_to_neutral_joints(rig.get_maya_expression_joints(expression_name, phase))


def get_joints_from_scene(rig, group_name):
    selection = cmds.ls(selection=True)

    cmds.select(f"{group_name}|{get_root_joint_name(rig)}", hierarchy=True, replace=True)
    jmh = JointMayaHandler()
    joints = {joint.name: joint for joint in jmh.get_selected_joints_from_scene()}
    cmds.select(selection, replace=True)
    return joints


def get_phase_sculpts_mesh_vertex_positions(rig, expression_name, phase):
    mmh = MeshMayaHandler()
    vertex_positions = {}
    for mesh_name in rig.rig_definition.lod_meshes[0].meshes:
        mesh_node = f"phase_grp|sculpted_{mesh_name}_{expression_name}_{phase}"
        if cmds.objExists(mesh_node):
            vertex_positions[mesh_name] = mmh.get_mesh_vertex_positions(mesh_node)
    return vertex_positions


def get_sculpt_mesh_vertex_positions(rig):
    mmh = MeshMayaHandler()
    vertex_positions = {}
    for mesh_name in rig.rig_definition.lod_meshes[0].meshes:
        mesh_node = f"sculpt_{mesh_name}"
        if cmds.objExists(mesh_node):
            vertex_positions[mesh_name] = mmh.get_mesh_vertex_positions(mesh_node)
    return vertex_positions


def remove_neck_rotations(rig, neck_joints, group_name):
    connected_attributes = {}

    for joint_name in neck_joints:
        for attribute in ROTATION_ATTRIBUTES:
            attribute_name = f"|{group_name}{get_joint_long_name(rig, joint_name)}.{attribute}"
            connected_attribute = cmds.listConnections(attribute_name, p=True)[0]
            connected_attributes[attribute_name] = connected_attribute
            cmds.disconnectAttr(connected_attribute, attribute_name)
            cmds.setAttr(attribute_name, 0.0)

    return connected_attributes


def reconnect_neck_joints(rig, connected_attributes, neck_joints, group_name):
    for joint_name in neck_joints:
        for attribute in ROTATION_ATTRIBUTES:
            attribute_name = f"|{group_name}{get_joint_long_name(rig, joint_name)}.{attribute}"
            connected_attribute = connected_attributes[attribute_name]
            cmds.connectAttr(connected_attribute, attribute_name)


def apply_ml_joints_matching_to_scene(rig, data, joints_to_update, group_name):
    joint_transforms = {}
    joint_long_names = {}

    joint_names = [rig.dna_reader.getJointName(i) for i in range(rig.dna_reader.getJointCount())]
    for ws_delta_transformation_matrix, joint_name in zip(data, joint_names):
        if joint_name in joints_to_update:
            joint_long_names[joint_name] = f"{group_name}|{get_joint_long_name(rig, joint_name)}"
            joint_transforms[joint_name] = ws_delta_transformation_matrix["data"]

    for joint_name in joint_names:
        if joint_name in joints_to_update:
            cmds.xform(joint_long_names[joint_name], matrix=joint_transforms[joint_name], ws=True)


def apply_ml_joints_matching_to_scene_for_head_turns(rig, data, joints_to_update):
    axes = ["x", "y", "z"]

    neck_01_long_name = f"edit_grp{get_joint_long_name(rig, 'neck_01')}"
    neck_02_long_name = f"edit_grp{get_joint_long_name(rig, 'neck_02')}"
    head_long_name = f"edit_grp{get_joint_long_name(rig, 'head')}"

    for axis in axes:
        cmds.setAttr(f"{neck_01_long_name}.r{axis}", lock=False)
        cmds.setAttr(f"{neck_02_long_name}.r{axis}", lock=False)
        cmds.setAttr(f"{head_long_name}.r{axis}", lock=False)

    neck_01_rotation = cmds.getAttr(f"{neck_01_long_name}.r")[0]
    cmds.setAttr(f"{neck_01_long_name}.r", *(0.0, 0.0, 0.0), type="double3")
    neck_02_rotation = cmds.getAttr(f"{neck_02_long_name}.r")[0]
    cmds.setAttr(f"{neck_02_long_name}.r", *(0.0, 0.0, 0.0), type="double3")
    head_rotation = cmds.getAttr(f"{head_long_name}.r")[0]
    cmds.setAttr(f"{head_long_name}.r", *(0.0, 0.0, 0.0), type="double3")

    apply_ml_joints_matching_to_scene(rig, data, joints_to_update, "edit_grp")

    cmds.setAttr(f"{neck_01_long_name}.r", *neck_01_rotation, type="double3")
    cmds.setAttr(f"{neck_02_long_name}.r", *neck_02_rotation, type="double3")
    cmds.setAttr(f"{head_long_name}.r", *head_rotation, type="double3")

    for axis in axes:
        cmds.setAttr(f"{neck_01_long_name}.r{axis}", lock=True)
        cmds.setAttr(f"{neck_02_long_name}.r{axis}", lock=True)
        cmds.setAttr(f"{head_long_name}.r{axis}", lock=True)


def get_expression_joints_from_node(rig, node_name, expression_name):
    selection = cmds.ls(selection=True)
    expressions_joints = cmds.currentJointState(nodeName=node_name, expression=expression_name, phase=1)
    cmds.select(selection, replace=True)
    expressions_joints = [expressions_joints[i * 9 : i * 9 + 9] for i in range(0, len(expressions_joints) // 9)]
    edit_joints = get_joints_from_scene(rig, "edit_grp")
    for joint_name, joint_values in zip(edit_joints, expressions_joints):
        edit_joints[joint_name].translate = joint_values[:3]
        edit_joints[joint_name].rotate = joint_values[3:6]
        edit_joints[joint_name].scale = joint_values[6:]

    return edit_joints


def set_joints_to_scene(joints, user_selection, target_group_name="edit_grp"):
    cmds.undoInfo(openChunk=True)
    source_group_name = next(iter(joints)).split("|")[0]

    for target_joint_name in cmds.ls(selection=True):
        source_joint_name = target_joint_name
        if source_group_name and target_group_name:
            source_joint_name = target_joint_name.replace(target_group_name, source_group_name)
        if source_joint_name in joints:
            cmds.xform(
                target_joint_name,
                translation=joints[source_joint_name].translate,
                rotation=joints[source_joint_name].rotate,
                scale=joints[source_joint_name].scale,
            )
    select_objects_by_name(user_selection)
    cmds.undoInfo(closeChunk=True)


def clear_selection():
    cmds.select(clear=True)


def delete_history(meshes):
    cmds.delete(meshes, constructionHistory=True)


def load_animation(file_path):
    ensure_plugin_available("fbxmaya")
    frame_rate_value = mel.eval("FBXImportSetMayaFrameRate -q;")
    frame_range_value = mel.eval("FBXImportFillTimeline -q;")
    import_mode_value = mel.eval("FBXImportMode -q;")
    mel.eval("FBXImportSetMayaFrameRate -v true;")
    mel.eval("FBXImportFillTimeline -v true;")
    mel.eval("FBXImportMode -v exmerge;")
    mel.eval(f'FBXImport -f "{file_path}";')
    mel.eval(f"FBXImportSetMayaFrameRate -v {frame_rate_value};")
    mel.eval(f"FBXImportFillTimeline -v {frame_range_value};")
    mel.eval(f"FBXImportMode -v {import_mode_value};")


def create_preview_rig_logic_node(
    rig,
    dna_calib_node_name,
    preview_rig_logic_node_name,
    mesh_names,
    corrective_pose_name,
    input_names,
    psd_names,
    merged_expression_indices,
    merged_expression_drivers,
    psd_indices,
    control_indices,
    weights,
):
    ensure_plugin_available("PreviewRigLogic")
    cmds.createPreviewRigLogic(
        input_names,
        psd_names,
        merged_expression_indices,
        merged_expression_drivers,
        psd_indices,
        control_indices,
        weights,
        [rig.dna_reader.getJointName(i) for i in range(rig.dna_reader.getJointCount())],
        rig.get_neutral_joints(),
        [rig.dna_reader.getJointParentIndex(i) for i in range(rig.dna_reader.getJointCount())],
        mesh_names,
        "preview_ctrl",
        dna_calib_node_name,
        preview_rig_logic_node_name,
        corrective_pose_name,
    )


def clean_preview_elements(rig, preview_rig_logic_node_name):
    for mesh in rig.rig_definition.meshes:
        blend_shape_node = f"preview_{mesh.name}_blendShapes"
        if cmds.objExists(blend_shape_node):
            cmds.delete(blend_shape_node)
        cbs_node = f"cbs_node_{mesh}"
        if cmds.objExists(cbs_node):
            cmds.delete(cbs_node)
        cbs_mesh = f"preview_{mesh}_cbs"
        if cmds.objExists(cbs_mesh):
            cmds.delete(cbs_mesh)
    if cmds.objExists("preview_ctrl"):
        cmds.delete("preview_ctrl")
    if cmds.objExists(preview_rig_logic_node_name):
        cmds.delete(preview_rig_logic_node_name)
    cmds.flushUndo()


def main_expression_preview_setup(rig, node_name, preview_rig_logic_node_name, editing_expression):
    ProgressUpdate.emit(status="Setting up scene objects")
    root_joint_name = get_root_joint_name(rig)

    clean_preview_elements(rig, preview_rig_logic_node_name)

    cmds.spaceLocator(name="preview_ctrl")
    cmds.parent("preview_ctrl", "preview_grp")
    cmds.addAttr(attributeType="float", min=0.0, max=1.0, sn="expression", ln="expression")
    cmds.select(f"preview_grp|{root_joint_name}", hierarchy=True, replace=True)

    ProgressEnd.emit()

    joints = cmds.ls(selection=True)
    ProgressStart.emit(max_value=3)
    ProgressUpdate.emit(status="Setting up preview joints.")
    for jnt in joints:
        joint_name = jnt.split("|")[-1]
        neutral_joint_transformations = rig.get_neutral_joint(joint_name)
        for neutral_value, attr_name in zip(neutral_joint_transformations, ATTRS):
            if attr_name.startswith("r"):
                cmds.setDrivenKeyframe(
                    f"{jnt}.{attr_name}",
                    currentDriver="preview_ctrl.expression",
                    driverValue=0.0,
                    value=0.0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
            else:
                cmds.setDrivenKeyframe(
                    f"{jnt}.{attr_name}",
                    currentDriver="preview_ctrl.expression",
                    driverValue=0.0,
                    value=neutral_value,
                    inTangentType="linear",
                    outTangentType="linear",
                )

    joint_state = cmds.currentJointState(nodeName=node_name, expression=editing_expression, phase=1)
    joint_state = [
        [joint_state[index] for index in range(start_index, start_index + 9)]
        for start_index in range(0, len(joint_state), 9)
    ]

    joint_indices = {joint.name: i for i, joint in enumerate(rig.rig_definition.joints.get_all_elements())}
    cmds.select(f"preview_grp|{root_joint_name}", hierarchy=True, replace=True)

    for jnt in cmds.ls(selection=True):
        joint_name = jnt.split("|")[-1]
        joint_transformations = joint_state[joint_indices[joint_name]]

        for expression_value, attr_name in zip(joint_transformations, ATTRS):
            cmds.setDrivenKeyframe(
                f"{jnt}.{attr_name}",
                currentDriver="preview_ctrl.expression",
                driverValue=1.0,
                value=expression_value,
                inTangentType="linear",
                outTangentType="linear",
            )

    ProgressUpdate.emit(status="Setting preview blendshapes")
    cmds.setAttr("preview_ctrl.expression", 1)

    expression = rig.rig_definition.get_expression_by_name(editing_expression)
    for mie in expression.meshes_in_expression:
        if cmds.objExists(f"edit_grp|sculpt_{mie.mesh.name}"):
            if mie.is_blends():
                deform_mesh_name = f"preview_grp|{mie.mesh.name}"
                cbs_positions = rig.get_cbs_mesh_vertex_positions(mie.mesh.name, editing_expression, 1)
                cbs_mesh_name = cmds.duplicate(deform_mesh_name, name=f"preview_{mie.mesh.name}_cbs")[0]

                points = om.MPointArray()
                for cbs_position in cbs_positions:
                    points.append(om.MPoint(*cbs_position))
                sel = om.MSelectionList()
                sel.add(cbs_mesh_name)
                dag_path = om.MDagPath()
                sel.getDagPath(0, dag_path)
                cbs_mesh = om.MFnMesh(dag_path)
                cbs_mesh.setPoints(points, om.MSpace.kWorld)

                bs_node_name = f"preview_{mie.mesh.name}_blendShapes"
                if cmds.objExists(bs_node_name):
                    cmds.delete(bs_node_name)

                cmds.select(cbs_mesh_name, deform_mesh_name)
                cmds.blendShape(name=bs_node_name, frontOfChain=True)
                cmds.connectAttr("preview_ctrl.expression", f"{bs_node_name}.{cbs_mesh_name}")

                cmds.setAttr(f"{cbs_mesh_name}.visibility", 0)
                mel.eval(
                    f"createCbsNode -p {deform_mesh_name}  -s edit_grp|sculpt_{mie.mesh.name}"
                    f" -c {cbs_mesh_name} -n cbs_node_{mie.mesh.name}"
                )
    ProgressEnd.emit()


def phase_expression_preview_setup(rig, expression_name, node_name):
    elements_added = []
    root_joint_name = get_root_joint_name(rig)
    group_name = "phase_grp"
    preview_group_name = "preview_grp"
    cmds.setAttr(f"{preview_group_name}.visibility", 1)
    cmds.setAttr(f"{group_name}.visibility", 0)
    cmds.setAttr("head_grp.visibility", 0)

    control_name = "phase_ctrl"
    cmds.spaceLocator(name=control_name)
    cmds.setAttr(f"{control_name}.visibility", 0)
    cmds.parent("phase_ctrl", group_name)
    attribute_name = "expression"
    cmds.addAttr(attributeType="float", min=0.0, max=1.0, sn=attribute_name, ln=attribute_name)
    elements_added.append(control_name)

    cmds.select(f"|{group_name}|{root_joint_name}", hierarchy=True, replace=True)
    joints = cmds.ls(selection=True)

    for jnt in joints:
        joint_name = jnt.split("|")[-1]
        neutral_joint_transformations = rig.get_neutral_joint(joint_name)
        for neutral_value, attr_name in zip(neutral_joint_transformations, ATTRS):
            if attr_name.startswith("r"):
                cmds.setDrivenKeyframe(
                    f"{jnt}.{attr_name}",
                    currentDriver=f"{control_name}.{attribute_name}",
                    driverValue=0.0,
                    value=0.0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                cmds.setDrivenKeyframe(
                    f"{jnt}.{attr_name}".replace(group_name, preview_group_name),
                    currentDriver=f"{control_name}.{attribute_name}",
                    driverValue=0.0,
                    value=0.0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
            else:
                cmds.setDrivenKeyframe(
                    f"{jnt}.{attr_name}",
                    currentDriver=f"{control_name}.{attribute_name}",
                    driverValue=0.0,
                    value=neutral_value,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                cmds.setDrivenKeyframe(
                    f"{jnt}.{attr_name}".replace(group_name, preview_group_name),
                    currentDriver=f"{control_name}.{attribute_name}",
                    driverValue=0.0,
                    value=neutral_value,
                    inTangentType="linear",
                    outTangentType="linear",
                )

    mmh = MeshMayaHandler()
    rig_edit_expression = rig.rig_definition.get_expression_by_name(expression_name)
    active_expression = rig_edit_expression.get_active_expression()
    emh = ExpressionMayaHandler(rig)
    rig_expressions = emh._get_view_expressions([active_expression])
    driver_values = {}
    if len(rig_expressions) > 1:
        for rig_expression in rig_expressions:
            if rig_expression.name != rig_edit_expression.name:
                driver_values[rig_expression.name] = [(0.0, 0.1, 1.0 / len(rig_edit_expression.get_phase_numbers()))]
        for phase in rig_edit_expression.get_phase_numbers():
            if phase == 1:
                driver_values[rig_edit_expression.name] = [
                    (
                        0.1,
                        1 / len(rig_edit_expression.get_phase_numbers()),
                        2 / len(rig_edit_expression.get_phase_numbers()),
                    )
                ]
            else:
                driver_values[rig_edit_expression.name].append(
                    (
                        (phase - 1) / len(rig_edit_expression.get_phase_numbers()),
                        phase / len(rig_edit_expression.get_phase_numbers()),
                        (phase + 1) / len(rig_edit_expression.get_phase_numbers()),
                    )
                )
    else:
        driver_values[rig_edit_expression.name] = []
        for phase in rig_edit_expression.get_phase_numbers():
            driver_values[rig_edit_expression.name].append(
                (
                    (phase - 1) / len(rig_edit_expression.get_phase_numbers()),
                    phase / len(rig_edit_expression.get_phase_numbers()),
                    (phase + 1) / len(rig_edit_expression.get_phase_numbers()),
                )
            )

    for rig_expression in rig_expressions:
        for phase in rig_expression.get_phase_numbers():
            joint_state = cmds.currentJointState(nodeName=node_name, expression=rig_expression.name, phase=phase)
            joint_state = [
                [joint_state[index] for index in range(start_index, start_index + 9)]
                for start_index in range(0, len(joint_state), 9)
            ]

            joint_indices = {joint.name: i for i, joint in enumerate(rig.rig_definition.joints.get_all_elements())}
            cmds.select(f"|{group_name}|{root_joint_name}", hierarchy=True, replace=True)
            for jnt in cmds.ls(selection=True):
                joint_name = jnt.split("|")[-1]
                joint_transformations = joint_state[joint_indices[joint_name]]

                for expression_value, attr_name in zip(joint_transformations, ATTRS):
                    cmds.setDrivenKeyframe(
                        f"{jnt}.{attr_name}",
                        currentDriver=f"{control_name}.{attribute_name}",
                        driverValue=driver_values[rig_expression.name][phase - 1][1],
                        value=expression_value,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
                    cmds.setDrivenKeyframe(
                        f"{jnt}.{attr_name}".replace(group_name, preview_group_name),
                        currentDriver=f"{control_name}.{attribute_name}",
                        driverValue=driver_values[rig_expression.name][phase - 1][1],
                        value=expression_value,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            for mie in rig_expression.meshes_in_expression:
                if mie.is_blends():
                    # Blend shape creation
                    blend_shape_node = f"phase_{mie.mesh.name}_blendShapes"
                    if not cmds.objExists(blend_shape_node):
                        cmds.select(f"|{preview_group_name}|{mie.mesh.name}", r=True)
                        cmds.blendShape(name=blend_shape_node, frontOfChain=True)
                        elements_added.append(blend_shape_node)

                    # Sculpt creation
                    sculpt_name = f"sculpted_{mie.mesh.name}_{rig_expression.name}_{phase}"
                    vertex_values = cmds.currentVertexState(
                        nodeName=node_name, expression=rig_expression.name, meshName=mie.mesh.name, phase=phase
                    )
                    vertex_values = [vertex_values[i : i + 3] for i in range(0, len(vertex_values), 3)]
                    sculpt = cmds.duplicate(f"|{group_name}|{mie.mesh.name}")
                    cmds.rename(sculpt, sculpt_name)
                    mmh.set_to_mesh(True, sculpt_name, [], vertex_values)
                    cmds.editDisplayLayerMembers("phase_sculpt_layer", f"{sculpt_name}Shape", noRecurse=True)
                    cmds.editDisplayLayerMembers("phase_sculpt_layer", sculpt_name, noRecurse=True)
                    elements_added.append(sculpt_name)

                    # CBS creation
                    cbs_name = f"corrective_{mie.mesh.name}_{rig_expression.name}_{phase}"
                    vertex_values = rig.get_neutral_mesh_vertex_positions(mie.mesh.name)
                    vertices = cmds.currentCBSVertexIndices(
                        nodeName=node_name, expression=rig_expression.name, meshName=mie.mesh.name, phase=phase
                    )
                    deltas = cmds.currentCBSDeltas(
                        nodeName=node_name, expression=rig_expression.name, meshName=mie.mesh.name, phase=phase
                    )
                    if vertices and deltas:
                        deltas = [deltas[i : i + 3] for i in range(0, len(deltas), 3)]
                        for vertex, delta in zip(vertices, deltas):
                            vertex_values[vertex][0] += delta[0]
                            vertex_values[vertex][1] += delta[1]
                            vertex_values[vertex][2] += delta[2]
                    cbs = cmds.duplicate(f"|{group_name}|{mie.mesh.name}")
                    cmds.rename(cbs, cbs_name)
                    cmds.setAttr(f"{cbs_name}.visibility", 0)
                    mmh.set_to_mesh(True, cbs_name, [], vertex_values)
                    elements_added.append(cbs_name)

                    cmds.blendShape(
                        blend_shape_node,
                        e=True,
                        target=(
                            f"|{preview_group_name}|{mie.mesh.name}",
                            cmds.blendShape(blend_shape_node, weightCount=True, query=True),
                            cbs_name,
                            1.0,
                        ),
                    )

                    # Sculpt visibility
                    if rig_expression.name != rig_edit_expression.name:
                        cmds.setAttr(
                            f"{group_name}|sculpted_{mie.mesh.name}_{rig_expression.name}_{phase}.visibility", 0
                        )

                    # In zero keyframe
                    cmds.setDrivenKeyframe(
                        f"{blend_shape_node}.corrective_{mie.mesh.name}_{rig_expression.name}_{phase}",
                        currentDriver=f"{control_name}.{attribute_name}",
                        driverValue=driver_values[rig_expression.name][phase - 1][0],
                        value=0.0,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
                    # Max value keyframe
                    cmds.setDrivenKeyframe(
                        f"{blend_shape_node}.corrective_{mie.mesh.name}_{rig_expression.name}_{phase}",
                        currentDriver=f"{control_name}.{attribute_name}",
                        driverValue=driver_values[rig_expression.name][phase - 1][1],
                        value=1.0,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
                    if rig_expression.name != rig_edit_expression.name or phase < len(
                        rig_expression.get_phase_numbers()
                    ):
                        # Out zero keyframe
                        cmds.setDrivenKeyframe(
                            f"{blend_shape_node}.corrective_{mie.mesh.name}_{rig_expression.name}_{phase}",
                            currentDriver=f"{control_name}.{attribute_name}",
                            driverValue=driver_values[rig_expression.name][phase - 1][2],
                            value=0.0,
                            inTangentType="linear",
                            outTangentType="linear",
                        )
                    cmds.setAttr(f"{control_name}.{attribute_name}", phase / len(rig_expression.get_phase_numbers()))
                    if rig_expression.name == rig_edit_expression.name:
                        mel.eval(f"createCbsNode -p {group_name}|{mie.mesh.name}  -s {sculpt_name}" f" -c {cbs_name}")
    return elements_added


def update_phase_joints(rig, expression_name, phase):
    if phase:
        rig_expression = rig.rig_definition.get_expression_by_name(expression_name)
        root_joint = get_root_joint_name(rig)
        cmds.select(f"|phase_grp|{root_joint}", replace=True, hierarchy=True)
        joints = cmds.ls(selection=True)
        for jnt in joints:
            for attr in ATTRS:
                selection_list = om2.MSelectionList()
                selection_list.add(jnt)
                dependency_node = om2.MFnDependencyNode(selection_list.getDependNode(0))
                plug = dependency_node.findPlug(attr, True)
                anim_curve = oma2.MFnAnimCurve(plug)
                anim_curve.setValue(anim_curve.numKeys - (rig_expression.no_phases() - phase) - 1, plug.asDouble())
        clear_selection()


def set_all_phase_sculpt_visibility(expression_name, phase_numbers, visible_meshes, value):
    for phase in phase_numbers:
        for visible_mesh in visible_meshes:
            cmds_set_attr(f"sculpted_{visible_mesh}_{expression_name}_{phase}.visibility", value)


def set_single_phase_sculpt_visibility(expression_name, sculpt_mesh_names, number_of_phases, current_phase):
    for phase in range(number_of_phases):
        for mesh_name in sculpt_mesh_names:
            cmds_set_attr(f"sculpted_{mesh_name}_{expression_name}_{phase + 1}.visibility", phase + 1 == current_phase)


def cleanup_phase_elements(added_elements):
    cmds.delete(added_elements)
    cmds.setAttr("phase_grp.visibility", 0)
    cmds.setAttr("head_grp.visibility", 1)
    cmds.setAttr("phase_sculpt_layer.displayType", 2)
    cmds.setAttr("phase_joints_layer.displayType", 2)


def target_expression_preview_setup(
    rig, editing_expression, expressions, split_expressions, node_data, dna_calib_node_name, preview_rig_logic_node_name
):
    clean_preview_elements(rig, preview_rig_logic_node_name)

    cmds.spaceLocator(name="preview_ctrl")
    cmds.parent("preview_ctrl", "preview_grp")

    cmds.select("preview_ctrl", replace=True)
    for input_name in node_data["input_names"]:
        if input_name not in split_expressions:
            cmds.addAttr(
                attributeType="float", min=0.0, max=expressions[input_name], sn=input_name, ln=input_name, keyable=True
            )

    root_joint_name = get_root_joint_name(rig)
    cmds.select(f"preview_grp|{root_joint_name}", hierarchy=True, replace=True)
    cmds.cutKey()

    for mesh_name in rig.rig_definition.get_dna_mesh_names():
        skin_cluster_name = get_skin_cluster_node_name(f"preview_grp|{mesh_name}")
        if skin_cluster_name:
            cmds.setAttr(f"{skin_cluster_name}.envelope", 0.0)

    blend_shape_names = node_data["input_names"] + node_data["psd_names"]
    blend_shapes_per_mesh = {}
    cbs_vertex_indices = {}
    cbs_deltas = {}
    for expression in blend_shape_names:
        rig_expression = rig.rig_definition.get_expression_by_name(editing_expression)
        for mie in rig_expression.meshes_in_expression:
            if mie.is_blends():
                if mie.mesh.name in blend_shapes_per_mesh:
                    blend_shapes_per_mesh[mie.mesh.name].append(expression)
                else:
                    blend_shapes_per_mesh[mie.mesh.name] = [expression]
                vertex_indices = cmds.currentCBSVertexIndices(
                    nodeName=dna_calib_node_name,
                    expression=expression,
                    meshName=mie.mesh.name,
                    phase=1,
                )
                delta_list = cmds.currentCBSDeltas(
                    nodeName=dna_calib_node_name,
                    expression=expression,
                    meshName=mie.mesh.name,
                    phase=1,
                )
                try:
                    deltas = [delta_list[i : i + 3] for i in range(0, len(delta_list), 3)]
                except TypeError:
                    deltas = []
                    vertex_indices = []
                try:
                    cbs_vertex_indices[mie.mesh.name][expression] = vertex_indices
                except KeyError:
                    cbs_vertex_indices[mie.mesh.name] = {expression: vertex_indices}
                try:
                    cbs_deltas[mie.mesh.name][expression] = deltas
                except KeyError:
                    cbs_deltas[mie.mesh.name] = {expression: deltas}

    for mesh, blend_shapes in blend_shapes_per_mesh.items():
        optimized_add_blend_shape_node(
            rig,
            mesh,
            f"|preview_grp|{mesh}",
            blend_shapes,
            f"preview_{mesh}_blendShapes",
            skin_cluster_prefix="preview_",
            cbs_vertex_indices=cbs_vertex_indices[mesh],
            cbs_deltas=cbs_deltas[mesh],
        )

    for mesh, blend_shapes in blend_shapes_per_mesh.items():
        mesh_node = f"|preview_grp|{mesh}"
        blend_shape_node = f"preview_{mesh}_blendShapes"
        for blend_shape in blend_shapes:
            cmds.setAttr(f"{blend_shape_node}.{blend_shape}", 1)
            negative_node = cmds.duplicate(mesh_node, name=f"negative_{blend_shape}")[0]
            cmds.blendShape(
                blend_shape_node,
                edit=True,
                t=(mesh_node, len(cmds.listAttr(f"{blend_shape_node}.w", m=True)), negative_node, 1.0),
            )
            cmds.setAttr(f"{blend_shape_node}.{blend_shape}", 0)
            cmds.delete(negative_node)

        corrective_mesh_node = cmds.duplicate(mesh_node, name=f"preview_{mesh}_cbs")[0]
        mel.eval(
            f"createCbsNode -p edit_grp|{mesh}  -s edit_grp|sculpt_{mesh}"
            f" -c {corrective_mesh_node} -n cbs_node_{mesh}"
        )
        cmds.blendShape(
            blend_shape_node,
            edit=True,
            t=(mesh_node, len(cmds.listAttr(f"{blend_shape_node}.w", m=True)), corrective_mesh_node, 1.0),
        )
        cmds.setAttr(f"{corrective_mesh_node}.visibility", False)

    for mesh in rig.rig_definition.get_dna_mesh_names():
        skin_cluster_name = get_skin_cluster_node_name(f"preview_grp|{mesh}")
        if skin_cluster_name:
            cmds.setAttr(f"{skin_cluster_name}.envelope", 1.0)

    psd_definition = rig.rig_definition.get_psd_def_for_expression(editing_expression)
    corrective_pose_name = psd_definition.corrective_pose.name

    create_preview_rig_logic_node(
        rig,
        dna_calib_node_name,
        preview_rig_logic_node_name,
        list(blend_shapes_per_mesh.keys()),
        corrective_pose_name,
        **node_data,
    )


def run_after_edit_assemble(rig):
    aas = general.source_module("aas", Resources().aas_file_path)
    try:
        aas.run_after_edit_assemble(rig)
    except AttributeError:
        logger.warning("Run after edit assemble method missing from the additional assemble script.")


def run_before_propagate_changes(rig):
    aas = general.source_module("aas", Resources().aas_file_path)
    try:
        aas.run_before_propagate_changes(rig)
    except AttributeError:
        logger.warning("Run before propagate changes method missing from the additional assemble script.")


def preview_expressions(
    rig, expressions, sculpt_meshes, node_name, preview_head_offset, orientation, anchor_node, global_up_axis
):
    selection = cmds.ls(selection=True)

    if not cmds.objExists("downstream_grp"):
        cmds.group(name="downstream_grp", empty=True)

    mmh = MeshMayaHandler()

    preview_meshes = {}
    preview_expression_count = 0
    ProgressStart.emit(max_value=len(expressions))

    for expression in expressions:
        ProgressUpdate.emit(status=f"Creating downstream preview meshes for {expression}.")
        for sculpt_mesh in sculpt_meshes:
            preview_vertex_state = cmds.previewVertexState(
                nodeName=node_name, meshName=str(sculpt_mesh), expression=str(expression), phase=1
            )
            rig_mesh = rig.rig_definition.get_mesh_by_name(sculpt_mesh)
            if preview_vertex_state:
                preview_mesh = mmh.create_neutral_mesh(
                    rig, sculpt_mesh, node_name=f"downstream_preview_{expression}_{sculpt_mesh}"
                )
                cmds.parent(preview_mesh, "downstream_grp")
                preview_mesh = f"downstream_grp|{preview_mesh}"

                sel = om.MSelectionList()
                sel.add(preview_mesh)

                dag_path = om.MDagPath()
                sel.getDagPath(0, dag_path)

                mf_mesh = om.MFnMesh(dag_path)
                positions = om.MPointArray()
                space = om.MSpace.kObject
                for ii in range(0, len(preview_vertex_state), 3):
                    positions.append(
                        om.MPoint(preview_vertex_state[ii], preview_vertex_state[ii + 1], preview_vertex_state[ii + 2])
                    )
                mf_mesh.setPoints(positions, space)
                cmds.select(preview_mesh, replace=True)
                cmds.sets(edit=True, forceElement=f"shader_{rig_mesh.shader.name}SG")
                cmds.setAttr(f"{preview_mesh}.tx", (preview_expression_count + 1) * -preview_head_offset)
                if expression in preview_meshes:
                    preview_meshes[expression].append(preview_mesh)
                else:
                    preview_meshes[expression] = [preview_mesh]
        if expression in preview_meshes:
            text_mesh = create_text(
                expression,
                orientation,
                [(preview_expression_count + 1) * -preview_head_offset, -8.0, 0.0],
                f"shader_{rig.rig_definition.meshes[0].shader.name}SG",
                anchor_node,
                global_up_axis,
            )
            cmds.rename(text_mesh, f"downstream_preview_{expression}_text")
            cmds.parent(f"downstream_preview_{expression}_text", "downstream_grp")
            preview_meshes[expression].append(f"downstream_grp|downstream_preview_{expression}_text")
            preview_expression_count += 1

    cmds.select(selection)
    ProgressEnd.emit()
    return preview_meshes


def create_text(label, orientation, preview_head_offset, shading_group, anchor_node, text_orientation):
    text_group = cmds.textCurves(n=f"{label}_label", f="Arial|sz:56.3", t=label)[0]
    cmds.CenterPivot()
    cmds.setAttr(f"{text_group}.r", *orientation)
    cmds.delete(cmds.pointConstraint(anchor_node, text_group))
    cmds.move(preview_head_offset[0], preview_head_offset[1], preview_head_offset[2], text_group, r=1)
    cmds.select(text_group, replace=True)
    text_surface = cmds.planarSrf(ch=0, rn=0, po=0)
    text_poly = cmds.nurbsToPoly(text_surface)[0]
    cmds.delete(text_surface, text_group)
    cmds.sets(edit=True, forceElement=shading_group)
    cmds.xform(text_poly, centerPivots=True)
    cmds.setAttr(f"{text_poly}.r", *text_orientation)
    return text_poly


def move_perspective_camera_to_objects(objects, perspective_camera_rotation):
    selection = cmds.ls(sl=True)
    cmds.setAttr("persp.r", *perspective_camera_rotation)
    cmds.select(objects, replace=True)
    cmds.viewFit("persp", f=1)
    cmds.select(selection, replace=True)


def start_editing_phase(rig, editing_expression, node_name, expression_joints_mapping):
    cmds.setAttr(f"{node_name}.Expression_Name", editing_expression, type="string")
    cmds.setAttr(f"{node_name}.Editing", True)

    ProgressUpdate.emit(status="Adding layers")
    root_joint_name = get_root_joint_name(rig)
    cmds.select(f"phase_grp|{root_joint_name}", hierarchy=True, replace=True)

    layer_joints = set()
    for jnt in cmds.ls(selection=True):
        if jnt.split("|")[-1] in expression_joints_mapping[editing_expression]:
            name_elements = jnt.split("|")
            base_name = name_elements[0]
            for element in name_elements[1:]:
                joint_name = f"{base_name}|{element}"
                layer_joints.add(joint_name)
                base_name = joint_name
    locked_joints = []
    for jnt in cmds.ls(selection=True):
        if jnt.split("|")[-1] not in expression_joints_mapping[editing_expression]:
            if jnt not in layer_joints:
                locked_joints.append(jnt)
    cmds.select(locked_joints, r=True)
    non_editable_joints_layer = cmds.createDisplayLayer(name="non_editable_joints_layer", nr=True)
    cmds.setAttr(f"{non_editable_joints_layer}.displayType", 1)


def start_editing(rig, editing_expression, node_name, expression_joints_mapping):
    ProgressStart.emit(max_value=5)

    ProgressUpdate.emit(status="Setting expression joints")
    joints = cmds.currentJointState(nodeName=node_name, expression=editing_expression, phase=1)
    edit_joints = [jnt for jnt in cmds.ls(type="joint") if jnt.startswith("edit_grp")]
    for i, rig_joint in enumerate(rig.rig_definition.joints.get_all_elements()):
        for edit_jnt in edit_joints:
            if rig_joint.name == edit_jnt.split("|")[-1]:
                part = i * 9
                values = joints[part : part + 9]
                cmds.xform(edit_jnt, translation=values[0:3])
                cmds.xform(edit_jnt, rotation=values[3:6])
                cmds.xform(edit_jnt, scale=values[6:9])

    ProgressUpdate.emit(status="Setting expression sculpts")
    expression = rig.rig_definition.get_expression_by_name(editing_expression)
    mesh_names = []
    for mie in expression.meshes_in_expression:
        if cmds.objExists(f"edit_grp|sculpt_{mie.mesh.name}"):
            if mie.is_blends():
                mesh_names.append(mie.mesh.name)
                vertex_positions = cmds.currentVertexState(
                    nodeName=node_name,
                    expression=editing_expression,
                    meshName=mie.mesh.name,
                    phase=1,
                )
                points = om.MPointArray()
                for i in range(0, len(vertex_positions), 3):
                    points.append(
                        om.MPoint(
                            vertex_positions[i],
                            vertex_positions[i + 1],
                            vertex_positions[i + 2],
                        )
                    )
                sel = om.MSelectionList()
                sel.add(f"edit_grp|sculpt_{mie.mesh.name}")
                dag_path = om.MDagPath()
                sel.getDagPath(0, dag_path)
                destination_mesh = om.MFnMesh(dag_path)
                destination_mesh.setPoints(points, om.MSpace.kWorld)
                cmds.setAttr(f"edit_grp|sculpt_{mie.mesh.name}.visibility", 1)
            else:
                cmds.setAttr(f"edit_grp|sculpt_{mie.mesh.name}.visibility", 0)

    ProgressUpdate.emit(status="Setting preview joints")
    cmds.setAttr("edit_grp.visibility", 1)
    cmds.setAttr("head_grp.visibility", 0)

    cmds.setAttr(f"{node_name}.Expression_Name", editing_expression, type="string")
    cmds.setAttr(f"{node_name}.Editing", True)

    ProgressUpdate.emit(status="Adding layers")
    root_joint_name = get_root_joint_name(rig)
    cmds.select(f"edit_grp|{root_joint_name}", hierarchy=True, replace=True)
    selection = cmds.ls(selection=True)
    cmds.editDisplayLayerMembers("edit_joints_layer", selection, noRecurse=True)

    layer_joints = set()
    for jnt in cmds.ls(selection=True):
        if jnt.split("|")[-1] in expression_joints_mapping[editing_expression]:
            name_elements = jnt.split("|")
            base_name = name_elements[0]
            for element in name_elements[1:]:
                joint_name = f"{base_name}|{element}"
                layer_joints.add(joint_name)
                base_name = joint_name

    locked_joints = []
    for jnt in cmds.ls(selection=True):
        if jnt.split("|")[-1] not in expression_joints_mapping[editing_expression]:
            for attr in ATTRS:
                cmds.setAttr(f"{jnt}.{attr}", lock=True)
            if jnt not in layer_joints:
                locked_joints.append(jnt)

    cmds.select(locked_joints, r=True)
    non_editable_joints_layer = cmds.createDisplayLayer(name="non_editable_joints_layer", nr=True)
    cmds.setAttr(f"{non_editable_joints_layer}.displayType", 1)

    cmds.select(clear=True)
    ProgressEnd.emit()


def lock_expressions(node_view, node_name):
    not_locked = [
        node.name
        for node in node_view.scene().get_all_modeling_nodes()
        if not node.lock_btn.is_locked() and not node.is_disabled()
    ]

    locked_attribute = list(cmds.getAttr(f"{node_name}.Expressions_Locked")[0])
    for i in range(len(locked_attribute)):
        attribute_name = f"{node_name}.Expressions_Locked[" + str(i) + "]"
        alias = cmds.aliasAttr(attribute_name, q=True)
        if alias in not_locked:
            locked_attribute[i] = 0
        else:
            locked_attribute[i] = 1

    for i, value in enumerate(locked_attribute):
        cmds.setAttr(f"{node_name}.Expressions_Locked[{i}]", value)


def propagate_changes(rig, node_name, current_phase):
    ProgressStart.emit(max_value=2)
    cmds.setAttr("edit_grp.visibility", 0)
    cmds.setAttr("preview_grp.visibility", 0)
    cmds.setAttr("phase_grp.visibility", 0)
    cmds.setAttr("head_grp.visibility", 1)

    if current_phase:
        update_phase_joints(rig, cmds.getAttr(f"{node_name}.Expression_Name"), current_phase)

    ProgressUpdate.emit(status="Propagating changes")
    cmds.setAttr(f"{node_name}.Editing", False)

    cmds.delete("non_editable_joints_layer")
    root_joint_name = get_root_joint_name(rig)
    cmds.select(f"edit_grp|{root_joint_name}", hierarchy=True, replace=True)
    edit_joints = cmds.ls(selection=True)
    for jnt in edit_joints:
        for attr in ATTRS:
            cmds.setAttr(f"{jnt}.{attr}", lock=False)

    ProgressEnd.emit()


def clear_all_ctrl_anim_curves(animation_type):
    all_keys = cmds.ls(type="animCurve")
    ctrls = []
    for crv in all_keys:
        if "CTRL" in crv:
            ctrls.append(crv)

    if len(ctrls) > 0:
        first, last = get_first_last_frames()
        cmds.cutKey(ctrls, clear=True, time=(first, last))

    if animation_type == "gui":
        cmds.setAttr("GRP_faceGUI.visibility", True)
    elif animation_type == "raw":
        cmds.setAttr("GRP_faceGUI.visibility", False)


def get_first_last_frames():
    animated_objs = cmds.ls(type="animCurve")
    all_keys = sorted(cmds.keyframe(animated_objs, q=True) or [])
    if len(all_keys) > 1:
        return all_keys[0], all_keys[-1]
    return 0, 0


def add_layers(rig):
    additional_meshes = [mesh.name for mesh in rig.rig_definition.meshes[1:]]
    groups = ["head_grp", "edit_grp"]
    head_mesh_name = rig.rig_definition.meshes[0].name
    root_joint_name = rig.get_maya_neutral_joints()[0].name
    sculpt_meshes = set()
    for expression in rig.rig_definition.expressions:
        if expression.assemble_to_rig:
            for mie in expression.meshes_in_expression:
                if mie.is_blends():
                    sculpt_meshes.add(mie.mesh.name)

    cmds.select(clear=True)
    for group_name in groups:
        for mesh_name in additional_meshes:
            if cmds.objExists(f"{group_name}|{mesh_name}"):
                cmds.select(f"{group_name}|{mesh_name}", add=True)
    additional_meshes_layer = cmds.createDisplayLayer(name="additional_meshes_layer", nr=True)

    cmds.setAttr(f"{additional_meshes_layer}.displayType", 2)

    cmds.select(f"head_grp|{head_mesh_name}", replace=True)
    rig_head_layer = cmds.createDisplayLayer(name="rig_head_layer", nr=True)
    cmds.setAttr(f"{rig_head_layer}.displayType", 2)

    cmds.select(f"head_grp|{root_joint_name}", replace=True, hierarchy=True)
    rig_joints_layer = cmds.createDisplayLayer(name="rig_joints_layer", nr=True)
    cmds.setAttr(f"{rig_joints_layer}.displayType", 0)
    cmds.setAttr(f"{rig_joints_layer}.color", 12)
    cmds.setAttr(f"{rig_joints_layer}.overrideColorRGB", 0, 0, 0)
    cmds.setAttr(f"{rig_joints_layer}.overrideRGBColors", 0)
    cmds.setAttr(f"{rig_joints_layer}.displayType", 1)

    # Sculpts
    cmds.select(clear=True)
    for mesh in sculpt_meshes:
        cmds.select(f"edit_grp|sculpt_{mesh}", add=True)
    cmds.createDisplayLayer(name="edit_head_sculpt_layer", nr=True)

    cmds.select(f"edit_grp|{head_mesh_name}", replace=True)
    edit_head_skin_layer = cmds.createDisplayLayer(name="edit_head_skin_layer", nr=True)
    cmds.setAttr(f"{edit_head_skin_layer}.displayType", 2)

    cmds.select(f"edit_grp|{root_joint_name}", replace=True, hierarchy=True)
    edit_joints_layer = cmds.createDisplayLayer(name="edit_joints_layer", nr=True)
    cmds.setAttr(f"{edit_joints_layer}.displayType", 0)
    cmds.setAttr(f"{edit_joints_layer}.color", 12)
    cmds.setAttr(f"{edit_joints_layer}.overrideColorRGB", 0, 0, 0)
    cmds.setAttr(f"{edit_joints_layer}.overrideRGBColors", 0)

    # preview
    cmds.select(f"preview_grp|{root_joint_name}", replace=True, hierarchy=True)
    preview_layer = cmds.createDisplayLayer(name="preview_joints_layer")
    cmds.setAttr(f"{preview_layer}.displayType", 2)
    cmds.setAttr(f"{preview_layer}.color", 12)
    cmds.setAttr(f"{preview_layer}.overrideColorRGB", 0, 0, 0)
    cmds.setAttr(f"{preview_layer}.overrideRGBColors", 0)

    preview_meshes = cmds.ls("preview_grp|*mesh")
    cmds.select(preview_meshes, replace=True)
    preview_layer = cmds.createDisplayLayer(name="preview_meshes_layer")
    cmds.setAttr(f"{preview_layer}.displayType", 2)

    # phase
    cmds.select(f"phase_grp|{root_joint_name}", replace=True, hierarchy=True)
    preview_layer = cmds.createDisplayLayer(name="phase_joints_layer")
    cmds.setAttr(f"{preview_layer}.displayType", 2)
    cmds.setAttr(f"{preview_layer}.color", 12)
    cmds.setAttr(f"{preview_layer}.overrideColorRGB", 0, 0, 0)
    cmds.setAttr(f"{preview_layer}.overrideRGBColors", 0)

    phase_meshes = cmds.ls("phase_grp|*mesh")
    cmds.select(phase_meshes, replace=True)
    preview_layer = cmds.createDisplayLayer(name="phase_meshes_layer")
    cmds.setAttr(f"{preview_layer}.displayType", 2)
    cmds.select(clear=True)
    cmds.createDisplayLayer(name="phase_sculpt_layer", nr=True)

    # clear
    cmds.select(clear=True)


def update_preview(
    value, skip=False, expression_name=None, maximum_value=1.0, all_slider_values=None, maximum_slider_values=None
):
    if expression_name:
        cmds.setAttr(f"preview_ctrl.{expression_name}", value)
    else:
        if not skip:
            cmds.setAttr("preview_ctrl.expression", value)
    if value / maximum_value == 1.0:
        if expression_name:
            show_edit = True
            for slider_value, maximum_value in zip(all_slider_values, maximum_slider_values):
                if slider_value / maximum_value < 1.0:
                    show_edit = False
                    break
            if show_edit:
                cmds.setAttr("preview_grp.visibility", 0)
                cmds.setAttr("edit_grp.visibility", 1)
            else:
                cmds.setAttr("edit_grp.visibility", 0)
                cmds.setAttr("preview_grp.visibility", 1)
        else:
            cmds.setAttr("preview_grp.visibility", 0)
            cmds.setAttr("edit_grp.visibility", 1)
    else:
        cmds.setAttr("edit_grp.visibility", 0)
        cmds.setAttr("preview_grp.visibility", 1)


def assemble_fbx_export_scene(rig, up_axis):
    cmds.upAxis(ax=up_axis)
    cmds.file(newFile=True, force=True)

    add_neutral_joints(rig)

    for mesh in rig.rig_definition.meshes:
        if mesh.name not in rig.rig_definition.get_dna_mesh_names():
            continue
        mesh_node = add_neutral_mesh(rig, mesh.name)
        add_skin_weights(rig, mesh.name, mesh_node)

        mmh = MeshMayaHandler()
        cbs_nodes = []
        expressions = rig.rig_definition.expressions
        for expr in expressions:
            if expr.assemble_to_rig:
                for mie in expr.meshes_in_expression:
                    if mie.is_blends() and mie.mesh.name == mesh.name:
                        for phase_no in expr.get_phase_numbers():
                            node = mmh.create_cbs_mesh(rig, mie.mesh.name, expr.name, phase_no)
                            renamed_node = cmds.rename(node, f"{mesh.name}__{expr.get_bs_channel_name(phase_no)}")
                            cbs_nodes.append(renamed_node)

        if cbs_nodes:
            cmds.select(cbs_nodes, r=True)
            cmds.select(mesh_node, add=True)
            cmds.blendShape(name=mesh.name + mmh.SUFFIX_BS, frontOfChain=True)
            cmds.delete(cbs_nodes)

    raw_control_names = [rig.dna_reader.getRawControlName(i) for i in range(rig.dna_reader.getRawControlCount())]
    for raw_control_name in raw_control_names:
        object_name, attribute_name = tuple(raw_control_name.split("."))
        cmds.addAttr(
            "FACIAL_C_FacialRoot",
            longName=f"{object_name}_{attribute_name}",
            keyable=True,
            attributeType="float",
            minValue=0.0,
            maxValue=1.0,
        )

    animated_map_names = [rig.dna_reader.getAnimatedMapName(i) for i in range(rig.dna_reader.getAnimatedMapCount())]
    for animated_map_name in animated_map_names:
        cmds.addAttr(
            "FACIAL_C_FacialRoot",
            longName=animated_map_name.replace(".", "_"),
            keyable=True,
            attributeType="float",
            minValue=0.0,
            maxValue=1.0,
        )

    cmds.currentTime(0)
    cmds.select("FACIAL_C_FacialRoot", replace=True)
    cmds.setKeyframe()


def create_shader(name):
    cmds.shadingNode("blinn", asShader=True, name=name)

    shading_group = str(
        cmds.sets(
            renderable=True,
            noSurfaceShader=True,
            empty=True,
            name=f"{name}SG",
        )
    )
    cmds.connectAttr(f"{name}.outColor", f"{shading_group}.surfaceShader")
    return shading_group


def add_shader_and_color(lod, vtx_color):
    for m, mesh_name in enumerate(vtx_color.VTX_COLOR_MESHES):
        try:
            if f"lod{lod}" in mesh_name:
                cmds.select(mesh_name)
                for v, rgb in enumerate(vtx_color.VTX_COLOR_VALUES[m]):
                    cmds.polyColorPerVertex(f"{mesh_name}.vtx[{v}]", g=rgb[1], b=rgb[2])
        except Exception as e:
            print(f"Skipped adding vtx color for mesh {mesh_name}. Reason {e}")
            continue


def create_maya_neutral_joints(rig, dna_reader):
    joints = {}
    parent_child_mapping = {}
    root_joint_name = None

    joint_names = [dna_reader.getJointName(i) for i in range(dna_reader.getJointCount())]
    for joint_index, joint_name in enumerate(joint_names):
        if dna_reader.getJointParentIndex(joint_index) == joint_index:
            root_joint_name = joint_name
        else:
            parent_name = dna_reader.getJointName(dna_reader.getJointParentIndex(joint_index))
            if parent_name in parent_child_mapping:
                parent_child_mapping[parent_name].append(joint_name)
            else:
                parent_child_mapping[parent_name] = [joint_name]

        joint = [
            dna_reader.getNeutralJointRotation(joint_index),
            dna_reader.getNeutralJointTranslation(joint_index),
            [0, 0, 1],
        ]

        joints[joint_name] = joint
    if root_joint_name:
        root_joint = rig.create_joint(root_joint_name, joints, parent_child_mapping)
        return MayaJointDataHolder([root_joint])


def remove_body_joints(rig, maya_neutral_joints, head_joint_name):
    joints = set([jnt.name for jnt in rig.rig_definition.joints.get_all_elements()])
    neutral_joint = maya_neutral_joints.get_element(head_joint_name)

    while neutral_joint:
        joints.update([neutral_joint.name])
        neutral_joint = neutral_joint.parent

    cmds.select(maya_neutral_joints.get_all_elements()[0].name, hierarchy=True, replace=True)
    selection = cmds.ls(selection=True)
    for jnt in selection:
        if jnt not in joints and cmds.objExists(jnt):
            cmds.delete(jnt)


def add_body(rig, body_scene_file_path, neck_joints, up_axis_dna_orient, up_axis_orient, head_joint_name):
    scene_mesh_names = []
    skin_weights = []
    swmh = SkinWeightsMayaHandler()

    for mesh in rig.rig_definition.meshes:
        if cmds.objExists(mesh.name):
            scene_mesh_names.append(mesh.name)
            skin_weights.append(swmh.get_skin_weights_from_scene(mesh.name))
            cmds.delete(f"{mesh.name}_skinCluster")

    for facial_joint in FACIAL_ROOT_JOINTS:
        cmds.parent(facial_joint, world=True)
    cmds.delete(get_root_joint_name(rig))

    if body_scene_file_path.endswith(".dna"):
        body_dna_reader = DNAFileHandler.get_reader(body_scene_file_path)

        dna_calib_reader = dnacalib.DNACalibDNAReader(body_dna_reader)
        cmd = dnacalib.RotateCommand(up_axis_dna_orient, [0.0, 0.0, 0.0])
        cmd.run(dna_calib_reader)

        neutral_joints = create_maya_neutral_joints(rig, dna_calib_reader)
        jmh = JointMayaHandler()
        clear_selection()
        jmh.setJointsToScene(neutral_joints)
        remove_body_joints(rig, neutral_joints, head_joint_name)
    else:
        body_scene = cmds.file(body_scene_file_path, options="v=0", type="mayaAscii", i=True, returnNewNodes=True)
        root_joint = None
        for node in body_scene:
            if cmds.nodeType(node) == "joint" and not cmds.listRelatives(node, parent=True):
                root_joint = node
                break
        cmds.setAttr(f"{root_joint}.jointOrient", *up_axis_orient)

    for facial_joint, neck_joint in zip(FACIAL_ROOT_JOINTS, neck_joints):
        cmds.parent(facial_joint, neck_joint)

    for mesh_name, skin in zip(scene_mesh_names, skin_weights):
        swmh.create_skin_cluster(
            skin.joints,
            mesh_name,
            f"{mesh_name}_skinCluster",
            skin.no_of_influences,
        )
        swmh.set_skin_weights_to_scene(mesh_name, skin)


def update_material_names(material_names):
    for mesh_name, material_name in material_names.items():
        cmds.select(mesh_name, replace=True)
        cmds.hyperShade(shaderNetworksSelectMaterialNodes=True)
        current_shader = cmds.ls(sl=True)[0]
        cmds.select(mesh_name, replace=True)
        if cmds.objExists(material_name):
            cmds.sets(edit=True, forceElement=f"{material_name}SG")
            cmds.delete(current_shader)
        else:
            cmds.rename(current_shader, material_name)
            cmds.rename(f"{current_shader}SG", f"{material_name}SG")


def export_fbx(rig, export_folder_path, character_name, up_axis):
    ensure_plugin_available("fbxmaya")

    vtx_color = general.source_module("vtx_color", Resources().vertex_color_file_path)

    for lod in range(rig.dna_reader.getLODCount()):
        add_shader_and_color(lod, vtx_color)
        mesh_names = [rig.dna_reader.getMeshName(i) for i in rig.dna_reader.getMeshIndicesForLOD(lod)]
        cmds.select(mesh_names, replace=True)
        cmds.select("root", add=True)

        min_time = cmds.playbackOptions(minTime=True, query=True)
        max_time = cmds.playbackOptions(maxTime=True, query=True)

        mel.eval("FBXResetExport")
        mel.eval("FBXExportBakeComplexAnimation -v true")
        mel.eval(f"FBXExportBakeComplexStart -v {min_time}")
        mel.eval(f"FBXExportBakeComplexEnd -v {max_time}")
        mel.eval("FBXExportConstraints -v true")
        mel.eval("FBXExportSkeletonDefinitions -v true")
        mel.eval("FBXExportInputConnections -v true")
        mel.eval("FBXExportSmoothingGroups -v true")
        mel.eval("FBXExportSkins -v true")
        mel.eval("FBXExportShapes -v true")
        mel.eval("FBXExportCameras -v false")
        mel.eval("FBXExportLights -v false")
        mel.eval(f"FBXExportUpAxis {up_axis}")

        export_file_name = f"{export_folder_path}/{character_name}_lod{lod}.fbx"
        mel.eval(f'FBXExport -f "{export_file_name}" -s true')


def custom_body_file_check(custom_body_scene_file_path, neck_joints):
    cmds.file(custom_body_scene_file_path, options="v=0", type="mayaAscii", open=True, force=True)

    missing_joints = []
    for jnt in neck_joints:
        if not cmds.objExists(jnt):
            missing_joints.append(jnt)

    return missing_joints


def cmds_set_attr(ctrl_name, value):
    if (
        cmds.objExists(ctrl_name)
        and cmds.getAttr(ctrl_name, settable=True)
        and abs(cmds.getAttr(ctrl_name) - value) > 0.00000001
    ):
        cmds.setAttr(ctrl_name, value)


def cmds_get_attr(attribute):
    return cmds.getAttr(attribute)


def gui_visible():
    if cmds.objExists("GRP_faceGUI"):
        return cmds.getAttr("GRP_faceGUI.visibility")
    else:
        return False


def add_gui_ctrl_callbacks(callback):
    selection_callback = om.MEventMessage.addEventCallback("SelectionChanged", callback)
    return selection_callback


def check_if_gui_ctrl_is_selected(controls):
    selected = []
    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    for i in range(sel.length()):
        obj = om.MObject()
        sel.getDependNode(i, obj)
        # Create an MFnDependencyNode from the MObject
        dependency_node = om.MFnDependencyNode(obj)
        tx = f"{dependency_node.name()}.tx"
        ty = f"{dependency_node.name()}.ty"

        if dependency_node:
            if tx in controls:
                selected.append(tx)
            if ty in controls:
                selected.append(ty)

    return selected


def get_joints_from_head_grp(jnt):
    all_joints = cmds.ls(jnt, type="joint")
    for joint in all_joints:
        if "head_grp" in joint:
            return joint


def plugin_version(plugin_name):
    return cmds.pluginInfo(plugin_name, query=True, version=True)


def refresh():
    cmds.refresh()


def delete_objects(objects):
    for obj in objects:
        with contextlib.suppress(ValueError):
            cmds.delete(obj)


def toggle_face_board(state=None):
    if state is None:
        value = not cmds.getAttr("head_rig_grp.visibility")
    else:
        value = state
    cmds.setAttr("head_rig_grp.visibility", value)


def send_locked_expressions(nodes, maya_node_name):
    for node in nodes:
        cmds.expressionLock(nn=maya_node_name, e=node.name)


def send_unlocked_expressions(nodes, maya_node_name):
    for node in nodes:
        cmds.expressionUnlock(nn=maya_node_name, e=node.name)


def unlock_expression(maya_node_name, expression_name):
    cmds.expressionUnlock(nn=maya_node_name, e=expression_name)


def lock_expression(maya_node_name, expression_name):
    cmds.expressionLock(nn=maya_node_name, e=expression_name)
