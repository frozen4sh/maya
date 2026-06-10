# Copyright Epic Games, Inc. All Rights Reserved.

from typing import Optional

from maya import OpenMaya as om
from maya import cmds


class MayaSceneError(Exception):
    pass


class MayaUtil:
    """
    Maya utility class.

    This class is static class.
    Contains common PyMel utility methods.
    """

    @staticmethod
    def unlock_node_attributes(node, translate: bool = True, rotate: bool = True, scale: bool = True):
        """
        Unlocks translate, rotate and scale attributes.

        @param node: Node which is being unlocked. (DagNode)
        @param translate: Indicates if translate attributes has to be unlocked. (boolean)
        @param rotate: Indicates if rotate attributes has to be unlocked. (boolean)
        @param scale: Indicates if scale attributes has to be unlocked. (boolean)
        """

        # unlock translate attributes
        if translate:
            cmds.setAttr(f"{node}.tx", lock=False)
            cmds.setAttr(f"{node}.ty", lock=False)
            cmds.setAttr(f"{node}.tz", lock=False)
        # unlock rotate attributes
        if rotate:
            cmds.setAttr(f"{node}.rx", lock=False)
            cmds.setAttr(f"{node}.ry", lock=False)
            cmds.setAttr(f"{node}.rz", lock=False)
        # unlock scale attributes
        if scale:
            cmds.setAttr(f"{node}.sx", lock=False)
            cmds.setAttr(f"{node}.sy", lock=False)
            cmds.setAttr(f"{node}.sz", lock=False)

    @staticmethod
    def hide_node_attr(
        node,
        hide_translate: bool = True,
        hide_rotate: bool = True,
        hide_scale: bool = True,
        hide_visibility: bool = True,
    ):
        """
        Hides given attribute.

        @param node: Maya DAG node. (DagNode)
        @param hide_translate: Flag to hide translate attribute. (boolean)
        @param hide_rotate: Flag to hide rotate attribute. (boolean)
        @param hide_scale: Flag to hide scale attribute. (boolean)
        @param hide_visibility: Flag to hide visibility attribute. (boolean)
        """

        if hide_translate:
            cmds.setAttr(f"{node}.translateX", keyable=False, channelBox=False)
            cmds.setAttr(f"{node}.translateY", keyable=False, channelBox=False)
            cmds.setAttr(f"{node}.translateZ", keyable=False, channelBox=False)
        if hide_rotate:
            cmds.setAttr(f"{node}.rotateX", keyable=False, channelBox=False)
            cmds.setAttr(f"{node}.rotateY", keyable=False, channelBox=False)
            cmds.setAttr(f"{node}.rotateZ", keyable=False, channelBox=False)
        if hide_scale:
            cmds.setAttr(f"{node}.scaleX", keyable=False, channelBox=False)
            cmds.setAttr(f"{node}.scaleY", keyable=False, channelBox=False)
            cmds.setAttr(f"{node}.scaleZ", keyable=False, channelBox=False)
        if hide_visibility:
            cmds.setAttr(f"{node}.visibility", keyable=False, channelBox=False)

    @staticmethod
    def get_objects(name, object_type: Optional[str] = None, root: Optional[bool] = False):
        """
        Gets scene objects by pattern and expression_function_type.

        @param name: Object pattern. (string)
        @param object_type: Object expression_function_type. (string)
        @param root: Indicates if object is root object. (boolean)
        @return List of object node instances. (DagNode[])
        """

        obj_name = "|" + name if root else name
        if object_type:
            obj_nodes = cmds.ls(obj_name, type=object_type)
        else:
            obj_nodes = cmds.ls(obj_name)
        return obj_nodes

    @staticmethod
    def get_mplug_from_strings(object_name: str, attribute_name: str):
        # Create an MSelectionList to store the object pattern
        selection_list = om.MSelectionList()
        selection_list.add(object_name)

        # Create an MDagPath and MObject to get the node
        m_object = om.MObject()
        selection_list.getDependNode(0, m_object)

        # Create an MFnDependencyNode from the MObject
        dependency_node = om.MFnDependencyNode(m_object)

        # Get the MPlug for the specified attribute pattern
        if dependency_node.hasAttribute(attribute_name):
            plug = dependency_node.findPlug(attribute_name, False)
        else:
            plug = om.MPlug()
        return plug


class SceneInfo:
    """
    Class containing scene informations.

    This class is used in various scene assembling for caching already
    created or imported data, in order to avoid redundant actions.
    This class is also used as proxy class. That means, if some requested
    data is not contained in class instance, that data will be requested
    from other classes to import or create that data.
    It is also used for communication between various classes and methods which
    are changing scene state.
    """

    def __init__(self, rig=None):
        # objects data
        self.neutral_joints = {}
        self.expression_joints = {}
        self.skin_weights = {}
        self.split_maps = {}
        self.sdks = {}

        # Maya scene objects
        self.sculpted_nodes = {}
        self.cbs_nodes = {}
        self.blend_shape_nodes = {}
        self.blend_shape_weights = {}
        self.shader_nodes = {}
        self.file_nodes = {}
        self.multiply_divide_nodes = {}
        self.add_subtract_nodes = {}

        self.rig = rig

    def get_key(self, name, version=0, temp=False):
        """
        Generates dictionary key for given parameters.
        """

        return name + "_" + str(version) + "_" + str(temp)

    def get_neutral_joints(self, version=0, temp=False, aa=None):
        """
        Gets neutral joints data holder from cache or from file.

        @param version: File version. If version is zero, last version will be read. (int)
        @param temp: Indicates whether file should be read as temp file. (boolean)
        @param aa: Additional adapter object which will change read data if necessary. (maya.adapter.AdditionalAdapter)
        @return Character neutral joints data. (maya.node.MayaJointDataHolder)
        """

        key = self.get_key("_neutral", version, temp)
        if key in self.neutral_joints:
            return self.neutral_joints[key]
        maya_joints = self.rig.get_maya_neutral_joints()
        if maya_joints and aa:
            aa.adapt(maya_joints)
        self.neutral_joints[key] = maya_joints
        return maya_joints

    def get_expression_joints(self, expression, phase):
        """
        Gets expression joints data holder from cache or from file.

        @param expression: Expression whose joints are requested. (Expression)
        @param phase: Phase number. (int)
        @param version: File version. If version is zero, last version will be read. (int)
        @param temp: Indicates whether file should be read as temp file. (boolean)
        @param aa: Additional adapter object which will change read data if necessary. (maya.adapter.AdditionalAdapter)
        @return Expression phase joints data. (maya.node.MayaJointDataHolder)
        """

        key = self.get_key(expression.name + "_" + str(phase))
        if key in self.expression_joints:
            return self.expression_joints[key]

        maya_joints = self.rig.get_maya_expression_joints(expression.name, phase)
        return maya_joints

    def get_skin_weights(self, mesh_name, version=0, temp=False, aa=None):
        """
        Gets skin weights data from cache or from file.

        @param mesh_name: Mesh pattern. (string)
        @param version: File version. If version is zero, last version will be read. (int)
        @param temp: Indicates whether file should be read as temp file. (boolean)
        @param aa: Additional adapter object which will change read data if necessary. (maya.adapter.AdditionalAdapter)
        @return Character skin weights data. (maya.node.MayaSkinWeights)
        """

        key = self.get_key(mesh_name, version, temp)
        if key in self.skin_weights:
            return self.skin_weights[key]
        skin_weights = self.rig.get_maya_skin_weights(mesh_name)
        if skin_weights and aa:
            aa.adapt(skin_weights)
        self.skin_weights[key] = skin_weights
        return skin_weights

    def get_sdks(self, expression):
        """
        Gets expression sdk data from cache or from file.

        @param expression: Expression whose sdk data is requested. (Expression)
        @param version: File version. If version is zero, last version will be read. (int)
        @param temp: Indicates whether file should be read as temp file. (boolean)
        @param aa: Additional adapter object which will change read data if necessary. (maya.adapter.AdditionalAdapter)
        @return Expression sdk data. ({string: .maya.node.MayaAnimCurve[]})
        """

        key = self.get_key(expression.name)
        if key in self.sdks:
            return self.sdks[key]
        sdks_dict = self.rig.get_animated_map_curves(expression)
        self.sdks[key] = sdks_dict
        return sdks_dict


class BaseHandler:
    """
    BaseHandler class.

    This class represent base handler class.
    All other handlers has to inherit this class.
    This class contains basic constants, attributes and methods which will be
    needed in all handlers.
    """

    # Constants
    MESSAGE_INFO = 0
    MESSAGE_WARN = 1

    LAYER_CORRECTIVE = "corrective_layer"
    LAYER_SCULPTED = "sculpted_layer"
    LAYER_CONTROL_CHAIN = "controlChain_layer"
    LAYER_JOINTS = "joints_layer"

    COLOR_LAYER_CORRECTIVE = 2
    COLOR_LAYER_SCULPTED = 1
    COLOR_LAYER_CONTROL_CHAIN = 13
    COLOR_LAYER_JOINTS = 12

    PREFIX_CORRECTIVE = "corrective_"
    PREFIX_SCULPTED = "sculpted_"
    PREFIX_CONTROL_CHAIN = "controlChain_"
    PREFIX_CBS_NODE = "cbsNode_"
    PREFIX_SHADER = "shader_"
    PREFIX_BASE_MAP = "baseMapFile_"
    PREFIX_MAP = "mapFile_"
    PREFIX_MASK = "maskFile_"

    SUFFIX_LAYER = "_layer"
    SUFFIX_BS = "_blendShapes"
    SUFFIX_SKINCLUSTER = "_skinCluster"

    def __init__(self, rig=None):
        self._scene_info = SceneInfo(rig)

    def clean_cache(self, rig=None):  # dead:disable # pylint: disable=unused-argument
        self._scene_info = SceneInfo(rig)

    @staticmethod
    def get_object(name, type=None, root=False, strict=False):
        """
        Gets exactly one scene object by pattern.

        If multiple objects exist with same pattern, first one will be returned.
        @param name: Object pattern. (string)
        @param type: Object object_type. (string)
        @param root: Indicates if object is root object. (boolean)
        @param strict: If object does not exist and strict is set to True, error will be raised. (boolean)
        @return Object node instance if object exists, otherwise None.
        @throws MayaSceneError: If node is not unique and strict is set to True.
        """

        obj_nodes = MayaUtil.get_objects(name, object_type=type, root=root)
        if strict:
            if len(obj_nodes) == 0:
                raise MayaSceneError("Unable to find object: " + name)
            if len(obj_nodes) > 1:
                raise MayaSceneError("Multiple objects with pattern: " + name)
        if obj_nodes:
            return obj_nodes[0]
        return None

    @staticmethod
    def get_display_layer(name, color=None):
        """
        Gets display layer by pattern. If doesn't exist creates it.

        @param name: Layer pattern. (string)
        @param color: Indicates color of layer if it is going to be created. (int)
        @return Layer object instance. (LayerNode)
        """

        # from scene
        layers = cmds.ls(name, type="displayLayer")
        if layers:
            return layers[0]
        # create new
        layer_node = cmds.createDisplayLayer(name=name, empty=True)
        if color:
            # layer_node.color.set(color)
            cmds.setAttr(f"{layer_node}.color", color)
        return layer_node
