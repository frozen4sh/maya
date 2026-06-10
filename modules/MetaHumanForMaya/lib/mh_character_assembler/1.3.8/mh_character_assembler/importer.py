# Copyright Epic Games, Inc. All Rights Reserved.
import os
import time

from frt_api.maya.skin_weights import SkinWeightsMayaHandler
from maya import cmds, mel
from mh_assemble_lib.control.form import MeshForm, ProcessForm
from mh_assemble_lib.impl.maya.handler import MayaHandler
from mh_assemble_lib.impl.maya.properties import MayaSceneOrient
from mh_assemble_lib.model.dnalib import DNAReader, Layer

import mh_character_assembler.core.consts as consts
from mh_character_assembler.core.progress_bar import ProgressBar
from mh_character_assembler.core.util import MayaUtil

from .config import Config
from .core import logger


class CharacterImporter:
    Instance = None

    def __init__(self):
        self.config = None
        self.logger = logger.get_logger()
        CharacterImporter.Instance = self

    def execute(self, message, options):
        """Shows a confirmation dialog and starts assembly process on confirmation."""
        self.logger.info("Received message for MetaHuman assembly...")

        confirm_dialog_response = cmds.confirmDialog(
            title="Confirm dialog",
            message="Are you sure you want to import MetaHuman character? All unsaved progress will be lost.",
            button=["Yes", "No"],
            defaultButton="Yes",
            cancelButton="No",
            dismissString="No",
        )

        if confirm_dialog_response == "Yes":
            self.logger.info("Importing MetaHuman character...")
            self._load_plugins()

            # prepare config
            self.config = Config(message)

            self.config.options.import_head = options["import_head"]
            self.config.options.import_body = options["import_body"]
            self.config.options.import_textures = options["import_textures"]
            self.config.options.combine_skeletons = options["combine_skeletons"]

            self.config.scene_orientation_string_value = options["scene_orientation"].lower()
            self.config.scene_orientation = self.config.resolve_scene_orientation()

            self.logger.info(self.config)

            self.assemble()

    def _load_plugins(self):
        cmds.loadPlugin("embeddedRL4")
        if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
            try:
                cmds.loadPlugin('fbxmaya')
            except:
                print("Failed to load fbxmaya plugin!")
                raise

    def assemble(self):
        """Assemble character based on a passed configuration"""
        try:
            start_time = time.time()
            ProgressBar.start_progress_bar("Loading character...", 12)

            self._scene_setup()
            self._import_assets()
            self.post_import()
            ProgressBar.end_progress_bar()
            self.logger.info("--- Import finished in %s seconds ---" % (time.time() - start_time))
        except Exception as ex:
            self.logger.error("Error building scene", ex)
            ProgressBar.end_progress_bar()

    def _scene_setup(self):
        """
        Initialize new scene with proper orientation
        :return:
        """
        cmds.file(new=True, force=True)
        # having it set on 0 breaks import when moving lookDir to parent space
        self.original_deformation_use_component_tag = cmds.optionVar(q="deformationUseComponentTags")
        cmds.optionVar(iv=("deformationUseComponentTags", 1))
        cmds.upAxis(ax=self.config.scene_orientation_string_value, rv=True)

    def _import_assets(self):
        """
        Import assets based on passed configuration
        :return:
        """
        # import head
        if self.config.options.import_head:
            dna = DNAReader.read(self.config.head_dna_path, Layer.all)
            self.import_head(dna)
            self.namespace_head_joints()

            if self.config.options.import_textures:
                self.import_head_shaders()

        # import body
        if self.config.options.import_body:
            self.import_body_and_parent_constraint()
            self.move_body_meshes_to_lod_groups(self.config.body_mesh_name)
            if self.config.options.import_textures:
                self.import_body_shader(self.config.body_mesh_name)

    def scene_cleanup(self):
        """Remove sufficient elements from assembled scene"""
        # remove sufficient meshes
        resolved_body_mesh_name = self.config.body_mesh_name

        self.logger.info("Removing sufficient objects...")

        if cmds.objExists("ROM_root"):
            cmds.delete("ROM_root")

        if cmds.objExists(resolved_body_mesh_name + "_lod0"):
            cmds.delete(resolved_body_mesh_name + "_lod0")

        if cmds.objExists(resolved_body_mesh_name + "_lod1"):
            cmds.delete(resolved_body_mesh_name + "_lod1")

        if cmds.objExists(resolved_body_mesh_name + "_lod2"):
            cmds.delete(resolved_body_mesh_name + "_lod2")

        if cmds.objExists(resolved_body_mesh_name + "_lod3"):
            cmds.delete(resolved_body_mesh_name + "_lod3")

        if cmds.objExists(resolved_body_mesh_name + "_body_uExport"):
            cmds.delete(resolved_body_mesh_name + "_body_uExport")

        # remove animation joint chain0
        if cmds.objExists("anim:root"):
            cmds.delete("anim:root")

        # remove unused layers
        self.logger.info("Removing unused layers...")
        if cmds.objExists(resolved_body_mesh_name + "_LOD0_layer"):
            cmds.delete(resolved_body_mesh_name + "_LOD0_layer")

        if cmds.objExists(resolved_body_mesh_name + "_LOD1_layer"):
            cmds.delete(resolved_body_mesh_name + "_LOD1_layer")

        if cmds.objExists(resolved_body_mesh_name + "_LOD2_layer"):
            cmds.delete(resolved_body_mesh_name + "_LOD2_layer")

        if cmds.objExists(resolved_body_mesh_name + "_LOD3_layer"):
            cmds.delete(resolved_body_mesh_name + "_LOD3_layer")

        # remove unused body group and meshes
        if cmds.objExists("export_geo_GRP"):
            cmds.delete("export_geo_GRP")
        if cmds.objExists("headRig_grp1"):
            cmds.delete("headRig_grp1")
        if cmds.objExists("geometry_grp") and not self.config.options.import_head:
            cmds.delete("geometry_grp")
        if cmds.objExists("geometry_grp1"):
            cmds.delete("geometry_grp1")
        if cmds.objExists("head_grp1"):
            cmds.delete("head_grp1")
        if cmds.objExists("bodyRig_grp"):
            cmds.delete("bodyRig_grp")
        if cmds.objExists("root_drv"):
            cmds.parent("root_drv", world=True)
        if cmds.objExists("Skeletons"):
            cmds.delete("Skeletons")

        cmds.group(world=True, empty=True, name="rig")
        if self.config.options.import_body:
            cmds.select("root")
            body_joint_names = cmds.listRelatives(allDescendents=True, type="joint")
            body_joint_names.append("root")
            cmds.parent("body_grp", "rig")
            self.add_joints_to_namespace(consts.BODY_NAMESPACE, body_joint_names)

        self.logger.info("Creating control sets...")
        if self.config.options.import_head:
            cmds.parent("head_grp", "rig")

        self.group_all_joints()

    def group_all_joints(self):
        """Create a joints group and add all head and body joints."""
        cmds.group(parent="rig", empty=True, name="joints_grp")
        if self.config.options.import_head:
            cmds.parent(f"{consts.HEAD_NAMESPACE}:spine_04", "joints_grp")

        if self.config.options.import_body:
            cmds.parent(f"{consts.BODY_NAMESPACE}:root", "joints_grp")
            if cmds.objExists("root_drv"):
                cmds.parent("root_drv", "joints_grp")

    def post_import(self):
        """Creates a workspace, import lights and perform scene cleanup."""
        ProgressBar.step_progress_bar("Assembly done... Cleaning up the scene...")

        self.logger.info("Import lights...")
        MayaUtil.create_lights(self.config.light_scene_path, self.config.scene_orientation)

        self.logger.info("Creating workspace...")
        MayaUtil.create_workspace(self.config.workspace_dir)

        self.logger.info("Cleaning up the scene...")
        self.scene_cleanup()

        self.logger.info("Cleaning skeleton...")
        if self.config.options.import_head and self.config.options.import_body:
            self.combine_head_body_skeleton()

        if self.config.options.combine_skeletons:
            self.remove_joints_namespaces()

        self.connect_follow_head()
        self.create_rl_nodes()
        self.order_display_layers()
        if self.config.options.import_head:
            self.create_head_controls_set()

        MayaUtil.save_maya_scene(
            self.config.workspace_dir + "/scene.mb",
            file_type="mayaBinary",
        )

        cmds.optionVar(iv=("deformationUseComponentTags", self.original_deformation_use_component_tag))

    def get_meshes(self):
        mesh_names = []

        if self.config.options.import_head:
            head_dna = DNAReader.read(self.config.head_dna_path, Layer.all)
            for mesh_id in range(head_dna.get_mesh_count()):
                mesh_names.append(head_dna.get_mesh_name(mesh_id))

        if self.config.options.import_body:
            body_dna = DNAReader.read(self.config.body_dna_path, Layer.all)
            for mesh_id in range(body_dna.get_mesh_count()):
                mesh_names.append(body_dna.get_mesh_name(mesh_id))
        return mesh_names

    def order_display_layers(self):
        # Get current layer members
        layers = []
        if self.config.options.import_body:
            layers.extend(
                [
                    "body_lod3_layer",
                    "body_lod2_layer",
                    "body_lod1_layer",
                    "body_lod0_layer",
                ]
            )

        if self.config.options.import_head:
            layers.extend(
                [
                    "head_lod7_layer",
                    "head_lod6_layer",
                    "head_lod5_layer",
                    "head_lod4_layer",
                    "head_lod3_layer",
                    "head_lod2_layer",
                    "head_lod1_layer",
                    "head_lod0_layer",
                ]
            )

        layer_data = {}
        for layer in layers:
            if cmds.objExists(layer):
                members = cmds.editDisplayLayerMembers(layer, query=True) or []
                layer_data[layer] = members
                cmds.delete(layer)

        for layer in layers:
            new_layer = cmds.createDisplayLayer(name=layer, empty=True)
            if "lod0" not in layer:
                cmds.setAttr(layer + ".visibility", 0)
            if layer_data[layer]:
                cmds.editDisplayLayerMembers(new_layer, layer_data[layer])

    def create_rl_nodes(self):
        """
        Create rl nodes and reconnect connections
        :return:
        """

        if self.config.options.import_head:
            if self.config.options.combine_skeletons:
                self.connect_rl4_node("head", self.config.head_dna_path)
            else:
                self.connect_rl4_node_namespaced("head", self.config.head_dna_path, consts.HEAD_NAMESPACE)

        if self.config.options.import_body:
            if self.config.options.combine_skeletons:
                self.connect_rl4_node("body", self.config.body_dna_path)
            else:
                self.connect_rl4_node_namespaced("body", self.config.body_dna_path, consts.BODY_NAMESPACE)

    def remove_joints_namespaces(self):
        # remove namespace
        joints = [joint for joint in cmds.ls(type="joint")]
        for j in joints:
            if cmds.objExists(j):
                cmds.rename(j, j.split(":", 1)[1])

    def create_head_controls_set(self):
        """Reads a dna raw controls and add them to the control set"""
        # read the controls From MH DNA
        dna = DNAReader.read(self.config.head_dna_path, Layer.all)
        cmds.select(clear=True)
        for i in range(dna._reader.getGUIControlCount()):
            control_name = dna._reader.getGUIControlName(i).split(".")[0]
            if cmds.objExists(control_name):
                cmds.select(control_name, add=True)

        # add custom controls to the set
        additional_control_names = [
            "CTRL_C_eye",
            "CTRL_rigLogicSwitch",
            "CTRL_lookAtSwitch",
            "CTRL_C_eyesAim",
            "CTRL_C_neck_swallow",
            "CTRL_L_eyeAim",
            "CTRL_R_eyeAim",
            "CTRL_convergenceSwitch",
            "CTRL_neckCorrectivesMultiplyerU",
            "CTRL_neckCorrectivesMultiplyerM",
            "CTRL_neckCorrectivesMultiplyerD",
            "CTRL_faceGUIfollowHead",
            "CTRL_eyesAimFollowHead",
        ]

        for additional_control in additional_control_names:
            if cmds.objExists(additional_control):
                cmds.select(additional_control, add=True)

        cmds.sets(n="FacialControls")

    def move_body_meshes_to_lod_groups(self, body_mesh_name):
        ProgressBar.step_progress_bar("Organizing body meshes to LOD groups...")
        try:
            # create layer groups
            self.logger.info("Creating layer groups...")
            if not cmds.objExists("geometry_grp"):
                cmds.group(world=True, empty=True, name="geometry_grp")

            cmds.select(clear=True)
            cmds.select("body_lod3_grp", replace=True)
            cmds.setAttr(f"{body_mesh_name}_lod3_layer.visibility", 0)

            cmds.select("body_lod2_grp", replace=True)
            cmds.setAttr(f"{body_mesh_name}_lod2_layer.visibility", 0)

            cmds.select("body_lod1_grp", replace=True)
            cmds.setAttr(f"{body_mesh_name}_lod1_layer.visibility", 0)

            cmds.select("body_lod0_grp", replace=True)
            cmds.setAttr(f"{body_mesh_name}_lod0_layer.visibility", 1)
            cmds.select(clear=True)

            # move body meshes to world, so we can group them in LOD (no parents allowed)
            self.logger.info("Moving body meshes to world...")

        except Exception as err:
            self.logger.error("Error moving body meshes to their corresponding LOD groups", err)
            pass

    def namespace_head_joints(self):
        """Add a namespace to head joints"""
        ProgressBar.step_progress_bar("Namespacing head joints...")
        head_joints = [joint for joint in cmds.ls(type="joint")]
        self.add_joints_to_namespace(consts.HEAD_NAMESPACE, head_joints)

    def import_body_and_parent_constraint(self):
        """Import body with MH Viewer and connect head and body joints."""
        mel.eval('namespace -set ":"')
        self.logger.info(f"Importing body scene from path {self.config.body_dna_path}")
        ProgressBar.step_progress_bar(f"Importing body scene from path {self.config.body_dna_path}")

        head_joints = [joint for joint in cmds.ls(type="joint")]

        # import body to scene
        self.import_body()

        # parent constraint body and head
        cmds.select("root")
        body_joints = cmds.listRelatives(allDescendents=True, type="joint")
        body_joints.append("root")

        for joint in body_joints:
            head_joint = consts.HEAD_NAMESPACE + ":" + joint
            if head_joint in head_joints:
                cmds.parentConstraint(joint, head_joint, maintainOffset=True)
                cmds.scaleConstraint(joint, head_joint, maintainOffset=True)

    def add_joints_to_namespace(self, namespace, joints):
        """
        Add all passed joints to namespace.
            Parameters:
                namespace: Namespace to add joints to.
                joints: List of joints to add.
        """
        self.logger.info(f"Adding joints to namespace {namespace}...")
        for joint in joints:
            if cmds.objExists(joint):
                cmds.rename(joint, f":{namespace}:{joint}")

    def import_head_shaders(self):
        """Import head shaders and connect all texture maps."""
        ProgressBar.step_progress_bar(f"Importing head shader: {self.config.shader_scene_path}")
        MayaUtil.import_shader(self.config.shader_scene_path, consts.MESH_SHADER_MAPPING)

        if self.config.platform == "Windows":
            MayaUtil.resolve_scene_shader_paths(consts.SHADERS, self.config.shaders_dir_path)

        MayaUtil.set_mask_textures(consts.MASKS, self.config.masks_dir_path)
        MayaUtil.set_map_textures(consts.COMMON_MAP_INFOS, self.config.head_maps_path)
        MayaUtil.set_map_textures(consts.MAP_INFOS, self.config.maps_dir_path)
        MayaUtil.set_map_textures(consts.EYES_MAP_INFOS, self.config.eyes_dir_path)

        shader_mapping = (
            consts.WIN_SHADER_ATTRIBUTES_MAPPING
            if self.config.platform == "Windows"
            else consts.LINUX_SHADER_ATTRIBUTES_MAPPING
        )
        MayaUtil.connect_attributes_to_shader(shader_mapping)

    def import_body_shader(self, body_mesh_name):
        """Import body shader and connect all texture maps."""
        shader_scene_path = self.config.body_shader_scene_path
        ProgressBar.step_progress_bar(f"Importing body shader from {shader_scene_path}... ")
        self.logger.info(f"Importing body shader from {shader_scene_path}...")
        cmds.file(shader_scene_path, op="v=0", typ="mayaAscii", i=True)

        # Apply shader to all meshes based on LOD level
        for lod_lvl in range(0, 4):
            try:
                resolved_mesh_name = f"{body_mesh_name}_lod{str(lod_lvl)}_mesh"
                cmds.select(resolved_mesh_name, replace=True)
                mel.eval("sets -e -forceElement shader_body_shaderSG")
            except Exception as ex:
                self.logger.error(f"Error: {ex}")
                self.logger.info("Skipped adding shader for body mesh %s." % lod_lvl)

        MayaUtil.set_map_textures(consts.BODY_MAP_INFOS, self.config.maps_dir_path)
        MayaUtil.set_map_textures(consts.BODY_MAP_INFOS, self.config.maps_dir_path, "body_shader_")
        MayaUtil.set_map_textures(consts.COMMON_MAP_INFOS_BODY, self.config.head_maps_path)
        if self.config.platform == "Windows":
            MayaUtil.resolve_scene_shader_paths(consts.BODY_SHADERS, self.config.shaders_dir_path)

    def import_head(self, dna):
        """Import head by using MH Viewer."""
        ProgressBar.step_progress_bar("Importing head...")
        handler = MayaHandler()
        if self.config.scene_orientation_string_value == "z":
            handler.config.scene_orient = MayaSceneOrient.get_head_z_up_orient()
        else:
            handler.config.scene_orient = MayaSceneOrient.get_head_y_up_orient()

        form = ProcessForm()
        form.add_joints = True
        form.add_rig_logic = False
        form.add_skin_cluster = True
        form.add_blend_shapes = True
        form.gui_ctrls_path = self.config.gui_path
        form.analog_ctrls_path = self.config.ac_path
        form.aas_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assets",
            self.config.dna_version,
            "additional_assemble_script.py",
        )

        form.meshes = []
        for mesh_id in range(dna.get_mesh_count()):
            mesh_name = dna.get_mesh_name(mesh_id)
            form.meshes.append(MeshForm(mesh_id, mesh_name))

        handler.set_state(dna, form)
        handler.build_mh()

    def import_body(self):
        """Import body by using MH Viewer."""
        dna = DNAReader.read(self.config.body_dna_path, Layer.all)

        handler = MayaHandler()
        handler.config.open_new_scene = False
        handler.config.top_level = "body"
        handler.config.top_level_group: str = "body_grp"
        handler.config.geometry_group: str = "body_geometry_grp"
        handler.config.rig_group: str = "bodyRig_grp"
        if self.config.scene_orientation_string_value == "z":
            handler.config.scene_orient = MayaSceneOrient.get_body_z_up_orient()
        else:
            handler.config.scene_orient = MayaSceneOrient.get_body_y_up_orient()

        form = ProcessForm()
        form.add_joints = True
        form.add_rig_logic = False
        form.add_skin_cluster = True
        form.add_blend_shapes = True
        form.add_ctrl_attr = False
        form.add_anim_map_attr = False

        form.meshes = []
        for mesh_id in range(dna.get_mesh_count()):
            mesh_name = dna.get_mesh_name(mesh_id)
            form.meshes.append(MeshForm(mesh_id, mesh_name))

        handler.set_state(dna, form)
        handler.build_mh()

    def connect_rl4_node_namespaced(self, name, dna_path, joint_namespace):
        mel_command = (
            f'createEmbeddedNodeRL4 -n "{name}_rl4Embedded" -dfp "{dna_path}" -ijn "{joint_namespace}:<objName>.<attrName>" '
            f'-jn "{joint_namespace}:<objName>.<attrName>" -bsn "<objName>_blendShapes.<attrName>" -amn "FRM_WMmultipliers.<objName>_<attrName>";'
        )
        mel.eval(mel_command)

    def connect_rl4_node(self, name, dna_path):
        mel_command = (
            f'createEmbeddedNodeRL4 -n "{name}_rl4Embedded" -dfp "{dna_path}" -ijn "<objName>.<attrName>" '
            f'-jn "<objName>.<attrName>" -bsn "<objName>_blendShapes.<attrName>" -amn "FRM_WMmultipliers.<objName>_<attrName>";'
        )
        mel.eval(mel_command)

    def recreate_connections(self, mesh_name, connections):
        tweak, poly_normal_per_vertex, mesh_blendshapes, mesh_shape_orig = connections
        mesh_skincluster = f"{mesh_name}_skinCluster"

        if mesh_blendshapes and mesh_shape_orig:
            cmds.connectAttr(f"{mesh_shape_orig}.outMesh", f"{mesh_blendshapes}.originalGeometry[0]", force=True)

        if tweak and mesh_blendshapes:
            cmds.connectAttr(f"{tweak}.outputGeometry[0]", f"{mesh_blendshapes}.input[0].inputGeometry", force=True)

        if mesh_blendshapes and mesh_skincluster:
            cmds.connectAttr(
                f"{mesh_blendshapes}.outputGeometry[0]", f"{mesh_skincluster}.input[0].inputGeometry", force=True
            )

    def get_connection_names(self, mesh_name: str):
        history = cmds.listHistory(mesh_name) or []
        deformers = cmds.ls(history)
        tweak = next((item for item in deformers if "tweak" in item), None)
        poly_normal_per_vertex = next((item for item in deformers if "polyNormalPerVertex" in item), None)
        mesh_blendshapes = next((item for item in deformers if "blendShapes" in item), None)
        mesh_shape_orig = next((item for item in deformers if "meshShapeOrig" in item), None)

        return tweak, poly_normal_per_vertex, mesh_blendshapes, mesh_shape_orig

    def break_connections(self, connections):
        tweak, poly_normal_per_vertex, mesh_blendshapes, mesh_shape_orig = connections

        if tweak and poly_normal_per_vertex:
            cmds.connectAttr(f"{tweak}.outputGeometry[0]", f"{poly_normal_per_vertex}.inputPolymesh", force=True)

        if mesh_blendshapes and mesh_shape_orig:
            cmds.disconnectAttr(f"{mesh_shape_orig}.outMesh", f"{mesh_blendshapes}.originalGeometry[0]")

        if tweak and mesh_blendshapes:
            cmds.disconnectAttr(f"{tweak}.outputGeometry[0]", f"{mesh_blendshapes}.input[0].inputGeometry")

    def combine_head_body_skeleton(self):
        # get skin cluster data
        skin_weights = []
        mesh_names = self.get_meshes()
        swmh = SkinWeightsMayaHandler()
        for mesh_name in mesh_names:
            if cmds.objExists(mesh_name):
                skin_weights.append(swmh.get_skin_weights_from_scene(mesh_name))
                cmds.delete(f"{mesh_name}_skinCluster")

        # delete neck joints
        if self.config.options.combine_skeletons:
            cmds.parent(consts.FACIAL_ROOT_JNT, world=True)
            cmds.parent(consts.NECK1_ROOT_JNT, world=True)
            cmds.parent(consts.NECK2_ROOT_JNT, world=True)
            cmds.delete(f"{consts.HEAD_NAMESPACE}:{consts.NECK_JOINTS[0]}")

            cmds.parent(consts.NECK1_ROOT_JNT, f"{consts.BODY_NAMESPACE}:{consts.NECK_JOINTS[1]}")
            cmds.parent(consts.NECK2_ROOT_JNT, f"{consts.BODY_NAMESPACE}:{consts.NECK_JOINTS[2]}")
            cmds.parent(consts.FACIAL_ROOT_JNT, f"{consts.BODY_NAMESPACE}:{consts.NECK_JOINTS[3]}")
        else:
            cmds.select(f"{consts.BODY_NAMESPACE}:root")
            body_joints = cmds.listRelatives(allDescendents=True, type='joint')
            body_joints.append("root")
            head_joints = [
                f"{consts.HEAD_NAMESPACE}:FACIAL_C_FacialRoot",
                f"{consts.HEAD_NAMESPACE}:FACIAL_C_Neck1Root",
                f"{consts.HEAD_NAMESPACE}:FACIAL_C_Neck2Root",
            ]
            for bj in body_joints:
                hj = f"{consts.HEAD_NAMESPACE}:{bj}"
                if hj in head_joints:
                    cmds.parent(bj, hj, maintainOffset=True)
                    cmds.scaleConstraint(bj, hj, maintainOffset=True)

        self.unlock_normals()

        connections = {}
        for mesh_name in consts.mesh_names_to_break_connections:
            connections[mesh_name] = self.get_connection_names(mesh_name)
            self.break_connections(connections[mesh_name])

        MayaUtil.delete_history(consts.mesh_names_to_break_connections)
        # recreate skin cluster
        i = 0
        for mesh_name in mesh_names:
            replaced_joints = []
            if cmds.objExists(mesh_name):
                for s in skin_weights[i].joints:
                    if not cmds.objExists(s):
                        replaced_joints.append(s.replace(consts.HEAD_NAMESPACE, consts.BODY_NAMESPACE))
                    else:
                        replaced_joints.append(s)
                skin_weights[i].joints = replaced_joints
                swmh.create_skin_cluster(
                    skin_weights[i].joints,
                    mesh_name,
                    f"{mesh_name}_skinCluster",
                    skin_weights[i].no_of_influences,
                )
                swmh.set_skin_weights_to_scene(mesh_name, skin_weights[i])
                i += 1

        for mesh_name in consts.mesh_names_to_break_connections:
            self.recreate_connections(mesh_name, connections[mesh_name])

    def connect_follow_head(self):  # 2d + aim to follow head
        """
        This method would connect switch which will enable user to enable/disable option to GUI and Aim interface to
        follow head rotations.
        """

        if not self.config.options.import_head:
            return

        cmds.spaceLocator(name="LOC_world")
        if cmds.objExists("headGui_grp"):
            cmds.parent("LOC_world", "headGui_grp")
        cmds.setAttr("LOC_world.rx", 0.0)
        cmds.setAttr("LOC_world.ry", 0.0)
        cmds.setAttr("LOC_world.rz", 0.0)
        cmds.setAttr("LOC_world.visibility", 0)

        # joint hierarchy is different if we import head only or head+body
        hierarchy = ""
        if cmds.objExists("joints_grp|root|pelvis|spine_01|spine_02|spine_03|spine_04|spine_05|neck_01|neck_02|head"):
            hierarchy = "joints_grp|root|pelvis|spine_01|spine_02|spine_03|spine_04|spine_05|neck_01|neck_02|head"

        if cmds.objExists(
            f"joints_grp|{consts.HEAD_NAMESPACE}:spine_04|{consts.HEAD_NAMESPACE}:spine_05|{consts.HEAD_NAMESPACE}:neck_01|{consts.HEAD_NAMESPACE}:neck_02|{consts.HEAD_NAMESPACE}:head"
        ):
            hierarchy = f"joints_grp|{consts.HEAD_NAMESPACE}:spine_04|{consts.HEAD_NAMESPACE}:spine_05|{consts.HEAD_NAMESPACE}:neck_01|{consts.HEAD_NAMESPACE}:neck_02|{consts.HEAD_NAMESPACE}:head"

        if not cmds.objExists(hierarchy):
            return

        cmds.parentConstraint(
            [
                hierarchy,
                "GRP_faceGUI",
            ],
            maintainOffset=True,
            name="GRP_faceGUI_parentConstraint1",
        )
        cmds.parentConstraint(
            ["LOC_world", "GRP_faceGUI"],
            maintainOffset=True,
            name="GRP_faceGUI_parentConstraint1",
        )
        cmds.setAttr("GRP_faceGUI_parentConstraint1.interpType", 0)
        cmds.setDrivenKeyframe(
            "GRP_faceGUI_parentConstraint1.LOC_worldW1",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_faceGUIfollowHead.ty",
            driverValue=0.0,
            value=1.0,
        )
        cmds.setDrivenKeyframe(
            "GRP_faceGUI_parentConstraint1.LOC_worldW1",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_faceGUIfollowHead.ty",
            driverValue=1.0,
            value=0.0,
        )
        cmds.setDrivenKeyframe(
            "GRP_faceGUI_parentConstraint1.headW0",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_faceGUIfollowHead.ty",
            driverValue=0.0,
            value=0.0,
        )
        cmds.setDrivenKeyframe(
            "GRP_faceGUI_parentConstraint1.headW0",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_faceGUIfollowHead.ty",
            driverValue=1.0,
            value=1.0,
        )

        cmds.parentConstraint(
            [
                hierarchy,
                "GRP_C_eyesAim",
            ],
            maintainOffset=True,
            name="GRP_C_eyesAim_parentConstraint1",
        )
        cmds.parentConstraint(
            ["LOC_world", "GRP_C_eyesAim"],
            maintainOffset=True,
            name="GRP_C_eyesAim_parentConstraint1",
        )
        cmds.setAttr("GRP_C_eyesAim_parentConstraint1.interpType", 0)
        cmds.setDrivenKeyframe(
            "GRP_C_eyesAim_parentConstraint1.LOC_worldW1",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_eyesAimFollowHead.ty",
            driverValue=0.0,
            value=1.0,
        )
        cmds.setDrivenKeyframe(
            "GRP_C_eyesAim_parentConstraint1.LOC_worldW1",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_eyesAimFollowHead.ty",
            driverValue=1.0,
            value=0.0,
        )
        cmds.setDrivenKeyframe(
            "GRP_C_eyesAim_parentConstraint1.headW0",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_eyesAimFollowHead.ty",
            driverValue=0.0,
            value=0.0,
        )
        cmds.setDrivenKeyframe(
            "GRP_C_eyesAim_parentConstraint1.headW0",
            itt="linear",
            ott="linear",
            currentDriver="CTRL_eyesAimFollowHead.ty",
            driverValue=1.0,
            value=1.0,
        )

    def unlock_normals(self):
        head_lods = [f"head_lod{i}_mesh" for i in range(8)]
        body_lods = [f"body_lod{i}_mesh" for i in range(4)]
        if self.config.options.import_head:
            for i, mesh in enumerate(head_lods):
                MayaUtil.unlock_mesh_normals(mesh, consts.head_neck_seam_vertices[f"lod{i}"])
        if self.config.options.import_body:
            for i, mesh in enumerate(body_lods):
                MayaUtil.unlock_mesh_normals(mesh, consts.body_neck_seam_vertices[f"lod{i}"])
