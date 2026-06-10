# Copyright Epic Games, Inc. All Rights Reserved.

import re
import logging
from typing import List
from contextlib import suppress

from maya import mel, cmds

from ..maya.core import MayaUtil, BaseHandler, MayaSceneError
from ..maya.mesh import MeshMayaHandler
from ..publisher import ProgressStart, ProgressUpdate, progress_guard
from ..maya.joint import JointMayaHandler
from ..maya.anim_curve import AnimCurveMayaHandler
from ..maya.skin_weights import SkinWeightsMayaHandler
from ..model.maya.anim_curve import MayaAnimCurve
from ..model.rig_definition.expression import Expression, ActiveExpression

logger = logging.getLogger("frt_api.rig.expression")


class ExpressionMayaHandler(BaseHandler):
    """
    Expression Maya handler.

    Contains methods for manipulation with scene objects on expression level.
    It uses other handler methods for manipulation.
    @see BaseHandler
    """

    def __init__(self, rig):
        super().__init__(rig)
        self.rig = rig
        self._jointsNaming = {}
        self._scale: float = 1.0
        self._scale_pivot: List[float] = [0.0, 0.0, 0.0]
        self._orient: List[float] = [0.0, 0.0, 0.0]
        self._assemble_constraint: bool = False
        self._delete_blend_shapes: bool = False
        self._create_cbs_node: bool = False
        self._ignore_view: bool = False
        self._use_cuda_bs: bool = False
        self._is_path_relative: bool = False
        self._create_shapes: bool = False
        self._fps: str = ""

    def set_open_data(self, create_shapes: bool, create_cbs_node: bool, ignore_view: bool):
        self._create_shapes = create_shapes
        self._create_cbs_node = create_cbs_node
        self._ignore_view = ignore_view

    def set_fps(self, fps: str):
        self._fps = fps

    # ---------------------------
    # Private methods
    # ---------------------------
    def _get_view_expressions(self, active_expressions: List[ActiveExpression]) -> List[Expression]:
        """
        Gets all expressions and its dependent (sequence) expressions.
        """

        expressions_list: List[Expression] = []
        for active_expression in active_expressions:
            expression = active_expression.expression
            self._add_view_expression(expression, expressions_list)
            if expression.view and not self._ignore_view:
                for related_exp in expression.view.get_related_expressions():
                    self._add_view_expression(related_exp, expressions_list)
        return expressions_list

    def _add_view_expression(self, expression, expressions_list):
        contains = False
        for item in expressions_list:
            if item.name == expression.name:
                contains = True
                break
        if not contains:
            expressions_list.append(expression)

    def _set_perspective_camera(self, rig_definition=None):
        """
        Sets perspective and joints display scale.

        @param rig_definition: Rig definition. (RigDefinition)
        """

        if rig_definition:
            persp = cmds.ls("|persp")[0]
            cmds.setAttr(f"{persp}.translate", *rig_definition.perspective_translate)
            cmds.setAttr(f"{persp}.rotate", *rig_definition.perspective_rotate)
            cmds.setAttr(f"{persp}.nearClipPlane", 1.0)
            cmds.joint_display_scale(rig_definition.joint_display_scale)

            mesh_names = rig_definition.get_active_mesh_names()
            if mesh_names:
                first_mesh = mesh_names[0]
                cmds.select(first_mesh, replace=True)
                cmds.viewFit("|persp")
                cmds.select(clear=True)

    # ---------------------------
    # Joint methods
    # ---------------------------
    def set_neutral_joints(self, exclusive=True):
        """
        Sets neutral joints to scene.

        @param characterDef: Character definition. (CharacterDef)
        @param version: File version. (int)
        @param temp: Indicates temporary file. (boolean)
        @param exclusive: If true joint hierachy has to be forced.
            If false, joints will be merged with existing joints on scene. (boolean)
        @return Success indicator. (boolean)
        """

        # set joints to scene
        try:
            jmh = JointMayaHandler()
            neutral_joints = self.rig.get_maya_neutral_joints()
            if exclusive:
                jmh.setJointsToScene(neutral_joints)
            else:
                jmh.append_joints_to_scene(neutral_joints)
        except MayaSceneError as e:
            msg = f"Maya scene error occurred. {e}"
            logger.error(msg)
            raise e
        logger.debug("Neutral joints set on scene.")

    def set_expression_joints_with_multiplier(self, expression, multiplier):
        """
        Sets expression joints to scene for given multiplier.

        @param characterDef: Character definition. (CharacterDef)
        @param expression: Expression. (Expression)
        @param multiplier: Multiplier. (float)
        @param temp: Indicates temporary file. (boolean)
        @param exclusive: If true joint hierachy has to forced.
            If false, joints will be merged with existing joints on scene. (boolean)
        @return Success indicator. (boolean)
        """

        # get neutral joints
        neutral_joints = self.rig.get_maya_neutral_joints()

        # get required data
        data = expression.get_expression_for_multiplier(multiplier)
        expression_joints = neutral_joints.copy()
        for pair in data:
            # phase_joints = self._scene_info.getExpressionJoints(expression, pair[0])
            phase_joints = self.rig.get_maya_expression_joints(expression.name, pair[0])
            if pair[1] != 1.0:
                phase_joints = phase_joints.copy()
                phase_joints.multiply(pair[1], neutral_joints)
            expression_joints.add(phase_joints, neutral_joints)

        # set joints to scene
        try:
            jmh = JointMayaHandler()
            jmh.setJointsToScene(expression_joints)
        except MayaSceneError as e:
            msg = f"Maya scene error occurred. {e}"
            logger.error(msg)
            return False
        return True

    # ---------------------------
    # Blend shape methods
    # ---------------------------

    def set_driven_keys_for_blend_shapes(
        self, expression, blend_shape_nodes, driver, driver_values=None, new_exp_name=None
    ):
        """
        Creates driven keys for expression blend shape.

        @param expression: Expression for which blend shapes are being created. (Expression)
        @param blend_shape_nodes: List of blend shape nodes in which,
            if expression channel(s) exists, driven key will be created. (BlendShape[])
        @param driver: Driver attribute. (string)
        @param driver_values: Driver attribute start and end values used for driving blend shape. (float[])
        @param new_exp_name: Expression pattern to be used in naming instead of default pattern. (string)
        """

        if driver_values is None:
            driver_values = [0.0, 1.0]
        phase_multipliers = [0.0]
        phase_multipliers.extend(expression.get_phase_multipliers())
        for pm, phase_multiplier in enumerate(phase_multipliers):
            phase_multipliers[pm] = driver_values[0] + phase_multiplier * (driver_values[1] - driver_values[0])

        num_phases = expression.no_phases()
        for blend_shape_node in blend_shape_nodes:
            for p, phaseNo in enumerate(expression.get_phase_numbers()):
                channel_name = expression.get_bs_channel_name(phaseNo, new_exp_name=new_exp_name)
                if cmds.attributeQuery(channel_name, node=blend_shape_node, exists=True):
                    driven = blend_shape_node + "." + channel_name
                    cmds.setDrivenKeyframe(
                        driven,
                        currentDriver=driver,
                        driverValue=phase_multipliers[p],
                        value=0,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
                    cmds.setDrivenKeyframe(
                        driven,
                        currentDriver=driver,
                        driverValue=phase_multipliers[p + 1],
                        value=1,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
                    if phaseNo != num_phases:
                        cmds.setDrivenKeyframe(
                            driven,
                            currentDriver=driver,
                            driverValue=phase_multipliers[p + 2],
                            value=0,
                            inTangentType="linear",
                            outTangentType="linear",
                        )

    def set_expression_bs_with_multiplier(self, expression, blend_shape_nodes, multiplier, new_exp_name=None):
        """
        Sets expression blendshapes on required values depending on multiplier.

        @param expression: Expression which blend shapes are being set for multiplier. (Expresion)
        @param blend_shape_nodes: List of blend shape nodes in which,
            if expression channel(s) exists, value will be changed. (BlendShape[])
        @param multiplier: Multiplier for which blend shape values are being set. (float)
        @param new_exp_name: Expression pattern to be used in naming instead of default pattern. (string)
        """

        # get required data
        data = expression.get_expression_for_multiplier(multiplier)
        for blend_shape_node in blend_shape_nodes:
            for phase_no in expression.get_phase_numbers():
                channel_name = expression.get_bs_channel_name(phase_no, new_exp_name=new_exp_name)
                if cmds.attributeQuery(channel_name, node=blend_shape_node, exists=True):
                    value = 0.0
                    for pair in data:
                        if pair[0] == phase_no:
                            value = pair[1]
                            break
                    cmds.setAttr(blend_shape_node + "." + channel_name, value)

    def _add_sculpted_shape(self, mesh, expression, phase_no):
        """
        Adds sculpted shape for given mesh and expression.
        """

        mmh = MeshMayaHandler()
        sculpted_node = mmh.create_sculpt_mesh(
            self.rig, mesh.name, expression.name, phase_no, layer=self.LAYER_SCULPTED
        )
        if not sculpted_node:
            return False

        name = BaseHandler.PREFIX_SCULPTED + mesh.name + "_" + expression.name + "_" + str(phase_no)
        cmds.rename(sculpted_node, name)
        self._scene_info.sculpted_nodes[name] = sculpted_node
        if mesh.shader and mesh.shader.name in self._scene_info.shader_nodes:
            cmds.select(name, replace=True)
            mel.eval(f"sets -e -forceElement {self._scene_info.shader_nodes[mesh.shader.name][1]}")
            # cmds.sets(self._scene_info.shader_nodes[mesh.shader.pattern][1], edit=True, forceElement=pattern)
        return True

    def _add_blend_shape(
        self,
        mesh,
        expression,
        phase_no,
        bs_position=0.0,
        bs_increment=0.0,
    ):
        """
        Adds blend shapes for given mesh and expression.
        """

        mmh = MeshMayaHandler()
        expression.get_phase_multipliers()
        channel_name = expression.get_bs_channel_name(phase_no)

        # get blend shape mesh
        corrective_node_name = mmh.create_cbs_mesh(
            self.rig, mesh.name, expression.name, phase_no, layer=BaseHandler.LAYER_CORRECTIVE
        )

        corrective_node_name = cmds.rename(corrective_node_name, channel_name)
        if mesh.shader and mesh.shader.name in self._scene_info.shader_nodes:
            cmds.select(channel_name, replace=True)
            mel.eval(f"sets -e -forceElement {self._scene_info.shader_nodes[mesh.shader.name][1]}")
            # cmds.sets(self._scene_info.shader_nodes[mesh.shader.pattern][1], edit=True, forceElement=channelName)

        # add blend shape channel
        blend_shape_node = self._scene_info.blend_shape_nodes.get(mesh.name, None)
        weights = {}
        if mesh.name in self._scene_info.blend_shape_weights:
            weights = self._scene_info.blend_shape_weights[mesh.name]
        else:
            self._scene_info.blend_shape_weights[mesh.name] = weights

        index = weights[channel_name] if channel_name in weights else len(list(weights.values()))
        weights[channel_name] = index
        cmds.select(corrective_node_name, replace=True)
        cmds.select("|" + mesh.name, add=True)

        if blend_shape_node is None:
            blend_shape_node = cmds.blendShape(name=mesh.name + BaseHandler.SUFFIX_BS, frontOfChain=True)[0]
            self._scene_info.blend_shape_nodes[mesh.name] = blend_shape_node
        else:
            cmds.blendShape(blend_shape_node, edit=True, target=("|" + mesh.name, index, corrective_node_name, 1))

        # rename and position blend shape
        cmds.select(clear=True)
        if self._delete_blend_shapes:
            cmds.delete(corrective_node_name)
        else:
            name = BaseHandler.PREFIX_CORRECTIVE + mesh.name + "_" + expression.name + "_" + str(phase_no)
            corrective_node_name = cmds.rename(corrective_node_name, name)
            cmds.setAttr(f"{corrective_node_name}.translateX", bs_position + (phase_no - 1) * bs_increment)
            self._scene_info.cbs_nodes[name] = corrective_node_name
        return True

    def _add_sc_and_cbs(
        self,
        mesh,
        expressions,
        add_sc=True,
        add_cbs=True,
        bs_position=0.0,
        bs_increment=0.0,
    ):
        """
        Adds sculpted and blend shapes for given expressions and sets them on scene.
        """

        for expression in expressions:
            mesh_in_exp = expression.get_mesh_in_expression(mesh.name)
            if mesh_in_exp and mesh_in_exp.is_blends():
                if add_sc:
                    for phase_no in expression.get_phase_numbers():
                        self._add_sculpted_shape(
                            mesh,
                            expression,
                            phase_no,
                        )
                if add_cbs:
                    for phase_no in expression.get_phase_numbers():
                        success = self._add_blend_shape(mesh, expression, phase_no, bs_position, bs_increment)
                        if not success and phase_no == expression.no_phases():
                            break

    def add_plugin_cbs_node(self, active_expression, active_meshes):
        """
        Runs createCbsNode command from "cbsNode" plugin, which creates cbsNode.

        CbsNode calculates corrective blend shape in realtime depending on sculpted mesh changes.
        @param active_expression: Active expression for which cbsNode is added. (pattern)
        """

        logger.debug("Creating cbs plugin nodes.")
        expression = active_expression.expression
        for mesh_in_exp in expression.meshes_in_expression:
            if mesh_in_exp.is_blends() and mesh_in_exp.mesh.name in active_meshes:
                for phaseNo in expression.get_phase_numbers():
                    cmds.currentTime(active_expression.phase_frames[phaseNo - 1])
                    pose_name = mesh_in_exp.mesh.name
                    sculpted_name = (
                        BaseHandler.PREFIX_SCULPTED + mesh_in_exp.mesh.name + "_" + expression.name + "_" + str(phaseNo)
                    )
                    corrective_name = (
                        BaseHandler.PREFIX_CORRECTIVE
                        + mesh_in_exp.mesh.name
                        + "_"
                        + expression.name
                        + "_"
                        + str(phaseNo)
                    )
                    cbs_node_name = (
                        BaseHandler.PREFIX_CBS_NODE + mesh_in_exp.mesh.name + "_" + expression.name + "_" + str(phaseNo)
                    )
                    self.create_plugin_cbs_node(pose_name, sculpted_name, corrective_name, cbs_node_name)
        logger.debug("Creating cbs plugin nodes finished.")

    def create_plugin_cbs_node(self, pose_name, sculpted_name, corrective_name, cbs_node_name):
        """
        Creates plugin cbs node for given pose, sculpted and corrective meshes.

        @param pose_name: Pose mesh pattern, deforming mesh. (string)
        @param sculpted_name: Sculpted mesh pattern, target mesh. (string)
        @param corrective_name: Corrective mesh pattern, calculated mesh. (string)
        @param cbs_node_name: Cbs node pattern. (string)
        """

        try:
            mel.eval(f"createCbsNode -p {pose_name}  -s {sculpted_name} -c {corrective_name} -n {cbs_node_name}")
            logger.debug("Plugin cbsNode added: " + cbs_node_name)
        except Exception:
            logger.warning("Unable to add plugin cbsNode: " + cbs_node_name)

    # ---------------------------
    # Save methods
    # ---------------------------

    def save_sculpted_meshes(self):
        """
        Saves expression sculpted meshes by naming.
        """

        mmh = MeshMayaHandler()

        # get sculpted from scene
        sculpted_nodes_dict = {}
        sculpted_nodes = cmds.ls(f"{BaseHandler.PREFIX_SCULPTED}*", type="transform")
        for node in sculpted_nodes:
            sculpted_nodes_dict[node] = node

        for expression in self.rig.rig_definition.expressions:
            for meshInExp in expression.meshes_in_expression:
                if meshInExp.is_blends():
                    for phaseNo in expression.get_phase_numbers():
                        sculpted_name = (
                            f"{BaseHandler.PREFIX_SCULPTED}{meshInExp.mesh.name}_{expression.name}_{phaseNo}"
                        )
                        if sculpted_name in sculpted_nodes_dict:
                            self.rig.set_sculpt(
                                meshInExp.mesh.name,
                                expression.name,
                                phaseNo,
                                mmh.get_mesh_vertex_positions(sculpted_nodes_dict[sculpted_name]),
                            )
                            logger.info(f"Sculpted meshes successfully saved for expression: {expression.name}")

    def save_sculpted_mesh(self, mesh_node, mesh_name, expression_name, phase):
        """
        Saves expression's sculpted mesh.

        @param mesh_node: Mesh dag node in scene. (DagNode)
        @param mesh_name: Mash which is being saved. (pattern)
        @param expression_name: Expressions which sculpted mesh is being saved. (pattern)
        @return True if successfully saved. Otherwise False. (boolean)
        """

        logger.debug("Save sculpted meshes for expression.")

        expression = self.rig.rig_definition.get_expression_by_name(expression_name)
        if expression is None:
            raise MayaSceneError(f"Unable to find expression {expression_name}")

        mmh = MeshMayaHandler()
        vertex_positions = mmh.get_mesh_vertex_positions(mesh_node)
        is_saved = False
        for meshInExp in expression.meshes_in_expression:
            if meshInExp.is_blends() and meshInExp.mesh.name == mesh_name:
                self.rig.set_sculpt(mesh_name, expression_name, phase, vertex_positions)
                is_saved = True
        if is_saved:
            logger.info(f"Sculpted mesh successfully updated for expression: {expression_name}")
        else:
            raise RuntimeWarning(f"No sculpted mesh is updated for expression: {expression_name}")
        return is_saved

    def save_corrective_meshes(self):
        """
        Saves expression corrective blend shapes by naming.
        """

        mmh = MeshMayaHandler()

        # get corrective from scene
        corrective_nodes_dict = {}
        corrective_nodes = cmds.ls(BaseHandler.PREFIX_CORRECTIVE + "*", type="transform")
        for node in corrective_nodes:
            corrective_nodes_dict[node] = node

        # get corrective names
        for expression in self.rig.rig_definition.expressions:
            for meshInExp in expression.meshes_in_expression:
                if meshInExp.is_blends():
                    for phaseNo in expression.get_phase_numbers():
                        corrective_name = (
                            f"{BaseHandler.PREFIX_CORRECTIVE}{meshInExp.mesh.name}_{expression.name}_{phaseNo}"
                        )
                        if corrective_name in corrective_nodes_dict:
                            self.rig.set_corrective_blend_shape(
                                meshInExp.mesh.name,
                                expression.name,
                                phaseNo,
                                mmh.get_mesh_vertex_positions(corrective_nodes_dict[corrective_name]),
                            )
                            logger.info(f"Corrective meshes successfully saved for expression: {expression.name}")

    def save_corrective_mesh(self, mesh_node, mesh_name, expression_name, phase):
        """
        Saves selected mesh as expression corrective mesh.

        @param mesh_node: Mesh dag node in scene. (DagNode)
        @param mesh_name: Mash which is being saved. (pattern)
        @param expression_name: Expressions which corrective mesh is being saved. (pattern)
        @return True if successfully saved. Otherwise False. (boolean)
        """

        logger.debug("Save selected corrective meshes for active expressions.")
        expression = self.rig.rig_definition.get_expression_by_name(expression_name)
        if expression is None:
            raise MayaSceneError(f"Unable to find expression {expression_name}")

        mmh = MeshMayaHandler()

        is_saved = False
        for mesh_in_exp in expression.meshes_in_expression:
            if mesh_in_exp.is_blends() and mesh_in_exp.mesh.name == mesh_name:
                self.rig.set_corrective_blend_shape(
                    mesh_name, expression_name, phase, mmh.get_mesh_vertex_positions(mesh_node)
                )
                is_saved = True
        if is_saved:
            logger.info(f"Corrective mesh successfully saved for expression: {expression_name}")
        else:
            raise RuntimeWarning(f"No corrective mesh is saved for expression: {expression_name}")
        return is_saved

    # ---------------------------
    # Shader methods
    # ---------------------------
    def _add_wm_multipliers_control(self, wm_control_name):
        """
        Checks if wrinkle maps and masks multiplier control exists. If not, creates locator.
        """

        if not wm_control_name:
            logger.warning("Unable to find WM control pattern in rig definition.")
            return None
        if not cmds.objExists(wm_control_name):
            logger.debug("Adding space locator instead of WM control.")
            locator_node = cmds.spaceLocator(name=wm_control_name, position=(0, 0, 0))[0]
            MayaUtil.hide_node_attr(locator_node)
        return wm_control_name

    def _add_expression_to_wm_control(
        self, active_expression, map_mask_multipliers, wm_control_node_name, connect_to_interface
    ):
        """
        Creates maps-mask multiplier if needed and adds expression node network which is driven
        by interface or by timeline.

        @param active_expression: Active expression which is being added. (ActiveExpression)
        @param map_mask_multipliers: Map mask multipliers which describe how expression has to be added to node network. (MapMaskMultipliers)
        @param wmControlNode: Mask-maps multipliers control node. (DagNode)
        @param connect_to_interface: Indicates if expressions has to be driven by interface or timeline. (bool)
        """

        expression = active_expression.expression
        if wm_control_node_name is None:
            logger.warning("Unable to find WM controls node.")
            return

        multipliers = map_mask_multipliers.get_multipliers_for_expression_name(expression.name)
        for multiplier in multipliers:
            # get multiplier sum node
            attr_name = multiplier.get_name()
            sum_node_name = "sumMM_" + attr_name
            if not cmds.objExists(sum_node_name):
                # add wm control attribute
                cmds.addAttr(
                    wm_control_node_name,
                    ln=attr_name,
                    at="float",
                    minValue=0.0,
                    maxValue=1.0,
                    defaultValue=0.0,
                    keyable=True,
                )
                range_node = cmds.shadingNode("setRange", asUtility=True, name="rangeMM_" + attr_name)
                cmds.setAttr(range_node + ".oldMaxX", 1.0)
                cmds.setAttr(range_node + ".maxX", 1.0)
                sum_node = cmds.shadingNode("plusMinusAverage", asUtility=True, name=sum_node_name)
                cmds.connectAttr(sum_node + ".output1D", range_node + ".valueX", force=True)
                cmds.connectAttr(range_node + ".outValueX", wm_control_node_name + "." + attr_name, force=True)
                logger.debug("Adding sum node to map mask multipliers network: " + sum_node_name)
            sum_plug = MayaUtil.get_mplug_from_strings(sum_node_name, "input1D")
            sum_index = sum_plug.numConnectedElements()

            # add expression multiplyCtrl node
            exp_sdk_node_name = "multiplyCtrl_" + expression.name + "_" + attr_name
            if not cmds.objExists(exp_sdk_node_name):
                exp_sdk_node = cmds.shadingNode("multiplyDivide", name=exp_sdk_node_name, asUtility=True)
                cmds.setAttr(exp_sdk_node + ".input1X", 1.0)
                cmds.setAttr(exp_sdk_node + ".input2X", 0.0)
                cmds.connectAttr(
                    exp_sdk_node + ".outputX", sum_node_name + ".input1D[" + str(sum_index) + "]", force=True
                )
                logger.debug("Adding multiply control to map mask multipliers network: " + exp_sdk_node_name)

            # drive expression
            driven_name = exp_sdk_node_name + ".input2X"
            if connect_to_interface:
                # connect to interface attribute
                for exp_attr in expression.expression_attrs:
                    # validate interface attributes
                    ctrl_node = self.get_object(exp_attr.object_name)
                    if not ctrl_node:
                        msg = "Unable to find interface control object: %s" % (exp_attr.object_name)
                        logger.warning(msg)
                        continue

                    if not cmds.attributeQuery(exp_attr.attr_name, node=ctrl_node, exists=True):
                        msg = "Unable to find interface control attribute : {}.{}".format(
                            exp_attr.object_name,
                            exp_attr.attr_name,
                        )
                        logger.warning(msg)
                        continue

                    # connect interface
                    driver = exp_attr.object_name + "." + exp_attr.attr_name
                    cmds.setDrivenKeyframe(
                        driven_name,
                        currentDriver=driver,
                        driverValue=exp_attr.from_value,
                        value=0,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
                    cmds.setDrivenKeyframe(
                        driven_name,
                        currentDriver=driver,
                        driverValue=exp_attr.to_value,
                        value=1,
                        inTangentType="linear",
                        outTangentType="linear",
                    )
            else:
                # connect to timeline
                cmds.setKeyframe(
                    driven_name,
                    time=active_expression.start_frame,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                cmds.setKeyframe(
                    driven_name,
                    time=active_expression.expression_start_frame,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                cmds.setKeyframe(
                    driven_name,
                    time=active_expression.expression_end_frame,
                    value=1,
                    inTangentType="linear",
                    outTangentType="linear",
                )
                cmds.setKeyframe(
                    driven_name,
                    time=active_expression.neutral_end_frame,
                    value=0,
                    inTangentType="linear",
                    outTangentType="linear",
                )

    def _add_file_node(self, file_path, name):
        """
        Adds file node and connects it with file.
        """

        if name in self._scene_info.file_nodes:
            return self._scene_info.file_nodes[name]

        file_node = cmds.shadingNode("file", asTexture=True, name=name)
        cmds.setAttr(file_node + ".fileTextureName", file_path, type="string")
        self._scene_info.file_nodes[name] = file_node
        return file_node

    def _add_shader(self, mesh):
        """
        Adds shader for given mesh.
        """

        shader = mesh.shader
        if shader is None:
            return

        # check if the shader already exists
        if shader.name in self._scene_info.shader_nodes:
            shader_node, shader_engine = self._scene_info.shader_nodes[shader.name]
        else:
            # create shader
            shader_node, shader_engine = self._create_blinn_shader(shader)
            self._scene_info.shader_nodes[shader.name] = [shader_node, shader_engine]
            logger.debug("Shader node created: " + shader.name)

        # apply shader to mesh
        mesh_node = self.get_object(mesh.name, type="transform", root=True)
        cmds.select(mesh_node, replace=True)
        mel.eval(f"sets -e -forceElement {shader_engine}")

    def _create_blinn_shader(self, shader):
        shader_name = cmds.shadingNode("blinn", name=BaseHandler.PREFIX_SHADER + shader.name, asShader=True)

        cmds.setAttr(f"{shader_name}.eccentricity", shader.eccentricity)
        cmds.setAttr(f"{shader_name}.specularRollOff", shader.specular_roll_off)
        cmds.setAttr(f"{shader_name}.specularColor", *shader.specular_color)
        cmds.setAttr(f"{shader_name}.color", *shader.shader_color)
        cmds.setAttr(f"{shader_name}.transparency", *shader.transparency)
        shader_engine = str(
            cmds.sets(
                renderable=True,
                noSurfaceShader=True,
                empty=True,
                name=f"{shader_name}SG",
            )
        )
        cmds.connectAttr(f"{shader_name}.outColor", f"{shader_engine}.surfaceShader")
        return [shader_name, shader_engine]

    def _connect_maps_to_shader(
        self, rig_definition, shader, active_expressions, connect_to_interface, map_data, mask_data, simple=False
    ):
        """
        Method called for each shader in definition for creating map file nodes and connecting them to their appropriate inputs.

        @param rig_definition: Rig definition. (RigDefinition)
        @param shader: Current shader to connect the maps to. (Shader)
        @param active_expressions: Currently active expression. (Expression[])
        @param connect_to_interface: Is the assemble object_type interface, i.e. rig assemble. (Boolean)
        @param temp: Are textures temp. (Boolean)
        @param simple: Is simple. (Boolean)
        """

        if not shader or shader.name not in self._scene_info.shader_nodes:
            return

        if map_data is None:
            map_data = {}
        if mask_data is None:
            mask_data = {}

        self._connect_maps_to_blinn_shader(
            rig_definition, shader, active_expressions, connect_to_interface, map_data, mask_data, simple
        )

    def _connect_maps_to_blinn_shader(
        self, rig_definition, shader, active_expressions, connect_to_interface, map_data, mask_data, simple=False
    ):
        logger.debug("Creating blinn maps network for shader node: " + shader.name)
        shader_node = self._scene_info.shader_nodes[shader.name][0]

        wm_control_node_name = self._add_wm_multipliers_control(rig_definition.wm_control)
        if wm_control_node_name is None:
            return

        # add base maps
        active_base_maps = {}
        for shader_input in shader.inputs:
            if len(shader_input.map_types) != 1:
                continue
            map_type = shader_input.map_types[0]
            base_map = rig_definition.get_base_map(map_type.name)
            if base_map is None:
                msg = "Unable to find base map for map object_type %s" % (map_type.name)
                logger.warning(msg)
                continue
            # add base map file node
            try:
                file_path = map_data[base_map.name]
            except KeyError:
                logger.warning(f"File for map object_type {base_map.name} not provided.")
                continue
            base_map_node = self._add_file_node(file_path, BaseHandler.PREFIX_BASE_MAP + base_map.name)
            if base_map_node:
                active_base_maps[map_type.name] = base_map_node

        if not simple:
            map_mask_multipliers = rig_definition.get_map_mask_multipliers()
            for active_expression in active_expressions:
                expression = active_expression.expression

                # connect expression network to WM multipliers control
                self._add_expression_to_wm_control(
                    active_expression, map_mask_multipliers, wm_control_node_name, connect_to_interface
                )

                # add animated maps
                for map_in_expression in expression.maps_in_expression:
                    map_ = map_in_expression.map
                    if map_.base_map or map_.map_type.name not in active_base_maps:
                        continue
                    base_map = rig_definition.get_base_map(map_.map_type.name)
                    base_map_node = active_base_maps[map_.map_type.name]

                    # create animated map file node
                    try:
                        file_path = map_data[map_.name]
                    except KeyError:
                        logger.warning(f"File for map object_type {map_.name} not provided.")
                        continue
                    map_node = self._add_file_node(file_path, BaseHandler.PREFIX_MAP + map_.name)

                    # add map subtract node (animated - base)
                    sub_map_node_name = "subMap_" + map_.name
                    if sub_map_node_name not in self._scene_info.add_subtract_nodes:
                        sub_map_node = cmds.shadingNode("plusMinusAverage", asUtility=True, name=sub_map_node_name)
                        cmds.setAttr(sub_map_node + ".operation", 2)
                        cmds.connectAttr(map_node + ".outColor", sub_map_node + ".input3D[0]", force=True)
                        cmds.connectAttr(base_map_node + ".outColor", sub_map_node + ".input3D[1]", force=True)
                        self._scene_info.add_subtract_nodes[sub_map_node_name] = sub_map_node
                    sub_map_node = self._scene_info.add_subtract_nodes[sub_map_node_name]

                    # add map sum node (base + animated deltas)
                    sum_map_node_name = "sumMap_" + base_map.name
                    if sum_map_node_name not in self._scene_info.add_subtract_nodes:
                        sum_map_node = cmds.shadingNode("plusMinusAverage", asUtility=True, name=sum_map_node_name)
                        cmds.connectAttr(base_map_node + ".outColor", sum_map_node + ".input3D[0]", force=True)
                        self._scene_info.add_subtract_nodes[sum_map_node_name] = sum_map_node
                    sum_map_node = self._scene_info.add_subtract_nodes[sum_map_node_name]

                    # add masks
                    for mask in map_in_expression.masks:
                        # create mask file node
                        try:
                            file_path = mask_data[mask.name]
                        except KeyError:
                            logger.warning(f"File for mask {mask.name} not provided.")
                            continue
                        mask_node = self._add_file_node(file_path, BaseHandler.PREFIX_MASK + mask.name)

                        # add mask multiply node
                        map_mask_name = map_.name + "_" + mask.name
                        multiply_mask_node_name = "multMask_" + map_mask_name
                        if multiply_mask_node_name not in self._scene_info.multiply_divide_nodes:
                            multiply_mask_node = cmds.shadingNode(
                                "multiplyDivide", asUtility=True, name=multiply_mask_node_name
                            )
                            cmds.connectAttr(mask_node + ".outColor", multiply_mask_node + ".input1", force=True)
                            cmds.connectAttr(sub_map_node + ".output3D", multiply_mask_node + ".input2", force=True)
                            self._scene_info.multiply_divide_nodes[multiply_mask_node_name] = multiply_mask_node
                        multiply_mask_node = self._scene_info.multiply_divide_nodes[multiply_mask_node_name]

                        # add interface multiply node
                        multiply_ctrl_node_name = "multCtrl_" + map_mask_name
                        if multiply_ctrl_node_name not in self._scene_info.multiply_divide_nodes:
                            multiply_ctrl_node = cmds.shadingNode(
                                "multiplyDivide", asUtility=True, name=multiply_ctrl_node_name
                            )
                            cmds.connectAttr(multiply_mask_node + ".output", multiply_ctrl_node + ".input1", force=True)
                            cmds.connectAttr(
                                wm_control_node_name + "." + map_mask_name,
                                multiply_ctrl_node + ".input2X",
                                force=True,
                            )
                            cmds.connectAttr(
                                wm_control_node_name + "." + map_mask_name,
                                multiply_ctrl_node + ".input2Y",
                                force=True,
                            )
                            cmds.connectAttr(
                                wm_control_node_name + "." + map_mask_name,
                                multiply_ctrl_node + ".input2Z",
                                force=True,
                            )
                            sumPlug = MayaUtil.get_mplug_from_strings(sum_map_node, "input3D")
                            sumIndex = sumPlug.numConnectedElements()
                            cmds.connectAttr(
                                multiply_ctrl_node + ".output",
                                sum_map_node + ".input3D[" + str(sumIndex) + "]",
                                force=True,
                            )
                            self._scene_info.multiply_divide_nodes[multiply_ctrl_node_name] = multiply_ctrl_node
                        multiply_ctrl_node = self._scene_info.multiply_divide_nodes[multiply_ctrl_node_name]

        # connect inputs to shader
        for shader_input in shader.inputs:
            if len(shader_input.map_types) != 1:
                continue
            map_type = shader_input.map_types[0]
            if map_type.name not in active_base_maps:
                continue
            base_map = rig_definition.get_base_map(map_type.name)
            base_map_node = active_base_maps[map_type.name]
            input_attr_name = shader_input.get_blinn_attribute_name(shader)

            # connect sum to shader
            sum_map_node_name = "sumMap_" + base_map.name
            sum_map_node = self._scene_info.add_subtract_nodes.get(sum_map_node_name, None)
            logger.debug("Connecting shader network to shader input: " + shader.name + "." + input_attr_name)
            if cmds.objExists(shader_node + "." + input_attr_name):
                if sum_map_node:
                    # connect sum to shader
                    cmds.connectAttr(sum_map_node + ".output3D", shader_node + "." + input_attr_name, force=True)
                else:
                    # connect base map to shader
                    cmds.connectAttr(base_map_node + ".outColor", shader_node + "." + input_attr_name, force=True)

    # ---------------------------
    # Skin weights methods
    # ---------------------------
    def add_skin_weights(self, mesh):
        """
        Adds skin weights to mesh.

        @param mesh: Mesh object. (Mesh)
        @return True if successfully saved. Otherwise, False. (boolean)
        """
        swmh = SkinWeightsMayaHandler()

        maya_skin_weights = self.rig.get_maya_skin_weights(mesh.name)
        if not maya_skin_weights:
            return False

        swmh.create_skin_cluster(
            maya_skin_weights.joints,
            mesh.name,
            mesh.name + BaseHandler.SUFFIX_SKINCLUSTER,
            maya_skin_weights.no_of_influences,
            maya_skin_weights.skinning_method,
        )

        try:
            swmh.setSkinWeightsToScene(mesh.name, maya_skin_weights)
        except MayaSceneError as e:
            msg = f"Maya scene error occurred. {e}"
            logger.error(msg)
            return False
        return True

    # ---------------------------
    # SDK methods
    # ---------------------------
    def _add_sdks_for_timeline_assemble(self, active_expression, multiplier=1.0):
        """
        Creates sdk key frames on timeline.

        @param active_expression: Active expression whose adks are being set. (ActiveExpression)
        @param multiplier: Expression multiplier. (float)
        @param temp: Temporary file indicator. (boolean)
        """

        expression = active_expression.expression
        # sdk_data = self._scene_info.getSdks(expression)
        sdk_data = self.rig.get_animated_map_curves(expression)
        if sdk_data:
            acmh = AnimCurveMayaHandler()
            time_span = active_expression.expression_end_frame - active_expression.expression_start_frame
            delta_time = active_expression.expression_start_frame
            hor_scale = time_span / float(expression.get_expression_range() * multiplier)

            msgs = []
            for anim_curve in list(sdk_data.values()):
                try:
                    anim_curve = anim_curve.copy_for_timeline_assemble(time_span, delta_time, hor_scale)
                    acmh.set_anim_curve_to_scene(anim_curve)
                except MayaSceneError as e:
                    msg = f"Maya scene error occurred. {e}"
                    msgs.append(str(e))
                    logger.error(msg)
            if msgs:
                raise MayaSceneError("\n".join(msgs))

    def _add_sdks_for_interface_assemble(self, expression, exp_attr):
        """
        Creates sdk driven keys on interface.

        @param expression: Expression whose adks are being set. (Expression)
        @param exp_attr: Expression attribute for which sdks are being set. (RangeFloatAttr)
        """

        sdk_data = self.rig.get_animated_map_curves(expression)
        # sdk_data = self._scene_info.getSdks(expression, version=self._buildData.getExpSdkVer(expression.pattern), temp=False)
        if sdk_data:
            acmh = AnimCurveMayaHandler()
            # hor_scale is not devided with expression.getExpressionRange() because it is already calculated in sdk.
            hor_scale = exp_attr.to_value - exp_attr.from_value

            for anim_curve in list(sdk_data.values()):
                try:
                    delta_value = 0.0
                    with suppress(Exception):
                        delta_value = cmds.getAttr(
                            anim_curve.outputs[0].obj_name + "." + anim_curve.outputs[0].attr_name
                        )

                    if anim_curve.meaning == MayaAnimCurve.MEANING_MASK:
                        if anim_curve.outputs and anim_curve.outputs[0].attr_name == "input2X":
                            anim_curve = anim_curve.copy_for_interface_assemble(
                                exp_attr, self._jointsNaming, delta_value, hor_scale
                            )
                            acmh.set_anim_curve_to_scene(anim_curve)
                            obj_name = anim_curve.outputs[0].obj_name
                            anim_curve_node = acmh.getAnimCurveForInOut(
                                exp_attr.object_name + "." + exp_attr.attr_name, obj_name + ".input2X"
                            )
                            if anim_curve_node:
                                cmds.connectAttr(anim_curve_node.output, obj_name + ".input2Y", force=True)
                                cmds.connectAttr(anim_curve_node.output, obj_name + ".input2Z", force=True)
                    else:
                        anim_curve = anim_curve.copy_for_interface_assemble(
                            exp_attr, self._jointsNaming, delta_value, hor_scale
                        )
                        acmh.set_anim_curve_to_scene(anim_curve)
                except MayaSceneError as e:
                    msg = f"Maya scene error occurred. {e}"
                    logger.error(msg)

    # ---------------------------
    # Keyframe methods
    # ---------------------------
    def _show_mesh(self, mesh_name, frame, value):
        """
        Adds mesh visibility to key-frame.
        """

        mesh_node = self.get_object(mesh_name, type="transform", root=True)
        if mesh_node:
            cmds.setAttr(f"{mesh_node}.visibility", value)
            cmds.setKeyframe(
                mesh_node, attribute="visibility", time=frame, inTangentType="linear", outTangentType="linear"
            )
            return True
        return False

    def _show_sculpted_expression(self, active_expression):
        """
        Adds sculpted mesh visibility to key-frame.
        """

        expression = active_expression.expression
        for mesh_in_exp in expression.meshes_in_expression:
            mesh_name = mesh_in_exp.mesh.name
            for p, phaseFrame in enumerate(active_expression.phase_frames):
                phase_no = p + 1
                sculpted_name = BaseHandler.PREFIX_SCULPTED + mesh_name + "_" + expression.name + "_" + str(phase_no)
                if self._show_mesh(sculpted_name, phaseFrame, 1):
                    self._show_mesh(sculpted_name, phaseFrame + 1, 0)
                    self._show_mesh(mesh_name, phaseFrame, 0)
                    self._show_mesh(mesh_name, phaseFrame + 1, 1)

    # ---------------------------
    # MAIN methods
    # ---------------------------
    def _add_expression_on_timeline(self, active_expression, timeline_assemble=False):
        """
        Adds expression keyframes on timeline.
        """

        expression = active_expression.expression
        view_datas = expression.get_view_data(active_expression.start_frame, self._ignore_view)
        simple_view_datas = expression.get_simple_view_data(active_expression.start_frame, self._ignore_view)

        # set expression joints and bs
        joint_nodes = cmds.ls(type="joint")
        blend_shape_nodes = list(self._scene_info.blend_shape_nodes.values())
        for view_data in view_datas:
            cmds.currentTime(view_data.frame)
            self.set_expression_joints_with_multiplier(view_data.expression, view_data.multiplier)
            self.set_expression_bs_with_multiplier(expression, blend_shape_nodes, view_data.multiplier)
            cmds.select(joint_nodes, replace=True)
            cmds.select(blend_shape_nodes, add=True)
            cmds.setKeyframe(time=view_data.frame, inTangentType="linear", outTangentType="linear")

        # set blend shapes
        # special case: sequential expression with view
        if expression.no_phases() > 1 and len(simple_view_datas) > 1:
            view_exp = simple_view_datas[-2].expression
            for blend_shape_node in blend_shape_nodes:
                channel_name = view_exp.get_bs_channel_name(1)
                if cmds.attributeQuery(channel_name, node=blend_shape_node, exists=True):
                    bs_attr = blend_shape_node + "." + channel_name
                    cmds.setAttr(bs_attr, 0.0)
                    cmds.setKeyframe(
                        bs_attr,
                        time=view_datas[-expression.no_phases()].frame,
                        inTangentType="linear",
                        outTangentType="linear",
                    )

        # set blend shapes
        for view_data in simple_view_datas:
            channel_name = view_data.expression.get_bs_channel_name(1)
            cmds.currentTime(view_data.frame)
            for blend_shape_node in blend_shape_nodes:
                for channel in cmds.listAttr(f"{blend_shape_node}.w", m=True):
                    cmds.setAttr(blend_shape_node + "." + channel, 0)
                if cmds.attributeQuery(channel_name, node=blend_shape_node, exists=True):
                    cmds.setAttr(blend_shape_node + "." + channel_name, view_data.multiplier)
            cmds.select(blend_shape_nodes, replace=True)
            cmds.setKeyframe(time=view_data.frame, inTangentType="linear", outTangentType="linear")

        # show sculpted mesh on expression frame
        if not timeline_assemble and self._create_shapes:
            self._show_sculpted_expression(active_expression)

        # add sdks
        self._add_sdks_for_timeline_assemble(active_expression, multiplier=1.0)

        logger.debug("Expression " + expression.name + " added on frame " + str(active_expression.expression_end_frame))
        return True

    def _add_neutral_expression_on_interface(self, add_key_on_root=False):
        """
        Sets keyframes for all joints but root when assembling with interface.
        """

        neutral_joints = self._scene_info.get_neutral_joints()
        if neutral_joints:
            jmh = JointMayaHandler()
            jmh.set_driven_key_for_neutral_joints(self._jointsNaming, neutral_joints, add_key_on_root=add_key_on_root)

    @progress_guard()
    def open_active_expressions(
        self, active_expressions, active_meshes, map_data=None, mask_data=None, hide_lower_lods_meshes=False
    ):
        """
        Creates Maya scene with active expressions.

        @param active_expressions: List of active expressions. (pattern)
        @param temp: Temporary file indicator. (boolean)
        """

        logger.debug("Open active expressions.")

        self.clean_cache(self.rig)
        rig_definition = self.rig.rig_definition

        active_expressions_obj = self.get_active_expressions(active_expressions)
        NEUTRAL_JOINTS = 1

        active_expressions_obj_coef = 2

        progress_max = (
            NEUTRAL_JOINTS
            + len(active_meshes)
            + len(rig_definition.shaders)
            + len(active_expressions_obj) * active_expressions_obj_coef
            + len(active_meshes)
        )
        ProgressStart.emit(max_value=progress_max)

        ProgressUpdate.emit(status="open active expressions")

        # open new scene
        cmds.file(force=True, new=True)
        if self._fps:
            cmds.currentUnit(time=self._fps)
        else:
            logger.info("FPS setting not provided.")

        logger.debug("New scene opened.")
        # rig_definition = active_expressions[0].expression.rig_definition
        # characterDef = rig_definition.characterDef
        mmh = MeshMayaHandler()

        # disable auto keyframe
        auto_keyframe = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(edit=True, state=False)

        # add NEUTRAL EXPRESSION
        expressions = self._get_view_expressions(active_expressions_obj)

        # add neutral joints
        self.set_neutral_joints()
        ProgressUpdate.emit(status="neutral joints added")

        # add neutral meshes, skin
        self.get_display_layer(BaseHandler.LAYER_CORRECTIVE, BaseHandler.COLOR_LAYER_CORRECTIVE)
        self.get_display_layer(BaseHandler.LAYER_SCULPTED, BaseHandler.COLOR_LAYER_SCULPTED)

        mesh_width = 0
        temp_mesh_nodes = []
        for mesh in active_meshes:
            mesh_node = mmh.create_neutral_mesh(self.rig, mesh, layer=mesh + BaseHandler.SUFFIX_LAYER)
            if mesh_node:
                temp_mw = mmh.get_bounding_box(mesh_node).width()
                if temp_mw > mesh_width:
                    mesh_width = temp_mw
            temp_mesh_nodes.append(mesh_node)
            ProgressUpdate.emit(status="create neutral mesh")

        for i, mesh_name in enumerate(active_meshes):
            if temp_mesh_nodes[i]:
                mesh = self.rig.rig_definition.get_mesh_by_name(mesh_name)
                if mesh:
                    self._add_shader(mesh)
                    self.add_skin_weights(mesh)
                    if self._create_shapes:
                        self._add_sc_and_cbs(
                            mesh,
                            expressions,
                            add_sc=True,
                            add_cbs=True,
                            bs_position=(mesh_width * 1.2),
                            bs_increment=(mesh_width * 1.2),
                        )
            ProgressUpdate.emit(status="adding meshes")
        self._set_perspective_camera(rig_definition)
        logger.debug("Neutral expression meshes, blend shapes, shader and skin weights added on frame: 0")

        # set neutral keys
        cmds.currentTime(0)
        joint_nodes = cmds.ls(type="joint")
        cmds.select(joint_nodes, replace=True)
        cmds.select(list(self._scene_info.blend_shape_nodes.values()), add=True)
        cmds.setKeyframe(inTangentType="linear", outTangentType="linear")

        for active_expression in active_expressions_obj:
            cmds.setKeyframe(
                time=active_expression.expression_end_frame, inTangentType="linear", outTangentType="linear"
            )
            cmds.setKeyframe(time=active_expression.neutral_end_frame, inTangentType="linear", outTangentType="linear")
            ProgressUpdate.emit(status="set keyframe")

        # add EXPRESSIONS
        # add maps
        for shader in rig_definition.shaders:
            self._connect_maps_to_shader(
                rig_definition, shader, active_expressions_obj, False, map_data, mask_data, False
            )
            ProgressUpdate.emit(status="adding meshes")

        # add expressions
        for active_expression in active_expressions_obj:
            self._add_expression_on_timeline(active_expression, timeline_assemble=False)
            ProgressUpdate.emit(status="adding expression to timeline")

        # set sculpted mesh visibility on frame 0
        sculpted_nodes = cmds.ls(BaseHandler.PREFIX_SCULPTED + "*", type="transform")
        for node in sculpted_nodes:
            self._show_mesh(node, 0, 0)

        hide_lower_lods_meshes = self.get_lower_lod_meshes(hide_lower_lods_meshes)

        for mesh_name in active_meshes:
            visibility = mesh_name not in hide_lower_lods_meshes
            cmds.setAttr(f"{mesh_name}_layer.visibility", visibility)
            self._show_mesh(mesh_name, 0, 1)

        # add cbs_nodes
        if self._create_cbs_node:
            for active_expression in active_expressions_obj:
                self.add_plugin_cbs_node(active_expression, active_meshes)

        # clean scene
        cmds.select(clear=True)

        # set animation play-back
        if active_expressions_obj:
            cmds.playbackOptions(minTime=0, maxTime=active_expressions_obj[-1].expression_end_frame)
            cmds.currentTime(active_expressions_obj[-1].expression_end_frame)
            cmds.autoKeyframe(edit=True, state=auto_keyframe)

        logger.debug("Active expressions oppened.")

    def get_lower_lod_meshes(self, hide_lower_lods_meshes):
        meshes = []
        if hide_lower_lods_meshes:
            for lod_mesh in self.rig.rig_definition.lod_meshes[1:]:
                meshes.extend(lod_mesh.meshes)
        return meshes

    def get_active_expressions(self, active_expressions):
        """
        Gets ActiveExpression object instance for expression.

        @param start_frame: Start frame of expression. (int)
        @param ignore_view: Indicates if view data should be ignored. (boolean)
        @return Active expression. (ActiveExpression)
        """

        frame = 0
        result = []

        for expression in active_expressions:
            exp = self.rig.rig_definition.get_expression_by_name(expression)
            if exp:
                active_exp = exp.get_active_expression(frame)
                frame = active_exp.neutral_end_frame
                result.append(active_exp)
        return result

    def get_active_expression_on_frame(self, active_expressions, frame):
        """
        Gets active expression on given frame.

        @param frame: Frame number. (float)
        @return Active expression. (ActiveExpression)
        """

        active_expressions_obj = self.get_active_expressions(active_expressions)
        for expression in active_expressions_obj:
            if expression.start_frame < frame <= expression.expression_end_frame:
                return expression.expression.name
        return None

    def get_active_expression_object(self, active_expression, active_expressions):
        active_expressions_obj = self.get_active_expressions(active_expressions)
        for expression in active_expressions_obj:
            if expression.expression.name == active_expression:
                return expression
        return None

    def set_active_expression_in_range(self, active_expression, active_expressions):
        """
        Sets active expression into expression frame range.

        Shows expressions blend shapes, and hide others.
        @param active_expression: Active expression pattern.
        @param active_expressions: List of active expressions pattern.
        """

        active_expression_obj = self.get_active_expression_object(active_expression, active_expressions)
        if active_expression_obj is None:
            return

        # hide all non expression corrective blend shapes
        all_corrective_nodes = cmds.ls(BaseHandler.PREFIX_CORRECTIVE + "*", type="transform")
        for node in all_corrective_nodes:
            if re.match(f".*_{active_expression}_\\d*$", node):
                cmds.setAttr(f"{node}.visibility", 1)
            else:
                cmds.setAttr(f"{node}.visibility", 0)

        # set frame range
        cmds.playbackOptions(minTime=active_expression_obj.startFrame, maxTime=active_expression_obj.expressionEndFrame)
        cmds.currentTime(active_expression_obj.expressionEndFrame)
