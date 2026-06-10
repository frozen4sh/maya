# Copyright Epic Games, Inc. All Rights Reserved.

import re
from typing import Any, Dict, List, Tuple, Union, Optional

from .map import Map, MapType
from .psd import PsdNet, PsdDefinition
from .core import DataHolder
from .mask import Mask
from .mesh import Mesh, SplitMap, LodMeshes
from .joint import Joint, JointGroup
from .shader import Shader
from .expression import Expression, ExpressionsFilter
from .skin_weights import SkinningData, SkinTransferData
from .animated_maps import MapMaskMultipliers
from .expression_function import DerivedExpFunc, ExpressionFunction


class RigDefinition:
    """
    Rig definition class describes character facial rig into details.
    It contains all character metadata, and it is used to get character physical
    data from file system.
    Character of same character object_type should have same definition, though some
    differences can exist.

    Attributes:
        expression_range (int): Frame numbers for expression phases when assembled on timeline.
        neutral_range (int): Number of frames between two expressions when assembled on timeline.
        perspective_translate ([float, float, float]): Perspective camera default position.
        perspective_rotate([float, float, float]): Perspective camera default rotations.
        joint_display_scale (float): Joints display size when assembled on scene.
        joint_name_filter (int): Position of joint side (left or right) indicator in pattern.
        joint_name_left (string): Joint left side indicator literal.
        joint_name_right (string): Joint right side indicator literal.
        rig_up (string): Rig up direction.
        rig_front (string): Rig front direction.
        root_control (string): Root interface control pattern.
        psd_control (string): PSD control pattern.
        wm_control (string): Wrinkle map multipliers control pattern.
        mesh_type (int): Indicates if mesh will be saved as .obj, .mb or .ply file format.
        joints (util.DataHolder): Joints data holder.
        joint_groups (JointGroup[]): List of rig joints groups.
        map_types (MapType[]): List of rig map types.
        maps (Map[]): List of rig maps.
        masks (Mask[]): List of rig masks.
        shaders (Shader[]): List of rig shaders.
        meshes (Mesh[]): List of rig meshes.
        split_maps (SplitMap[]): List of rig slit maps.
        expressions (Expression[]): List of rig expressions.
        psd_nets (PsdNet[]): List of rig PSD networks.
        psd_definitions (PsdDefinition[]): List of PSD definitions.
        active_meshes (Mesh[]): List of rig meshes which should be included.
        lod_meshes (LodMeshes[]): List of meshes include in lods
        skin_transfer_data (SkinTransferData[]): List for skin data
    """

    FILTER_CONTAINS = 1

    MESH_TYPE_MB = 1
    MESH_TYPE_OBJ = 2
    MESH_TYPE_PLY = 3
    MESH_TYPE_MAP = ("", "mb", "obj", "ply")

    def __init__(self):
        self.expression_range: int = 0  # (int)
        self.neutral_range: int = 0  # (int)
        self.perspective_translate: List[float] = [28.0, 21.0, 28.0]  # float[]
        self.perspective_rotate: List[float] = [-28.0, 45.0, 0.0]  # float[]
        self.joint_display_scale: float = 1.0  # float
        self.joint_name_filter: int = RigDefinition.FILTER_CONTAINS
        self.joint_name_left: str = ""
        self.joint_name_right: str = ""
        self.rig_up: str = "Y+"  # (string)
        self.rig_front: str = "Z+"  # (string)
        self.root_control: str = ""  # (string)
        self.psd_control: str = ""  # (string)
        self.wm_control: str = ""  # (string)
        self.mesh_type: int = RigDefinition.MESH_TYPE_PLY  # (int)

        self.joints: DataHolder = DataHolder()
        self.joint_groups: List[JointGroup] = []  # (JointGroup[])
        self.map_types: List[MapType] = []  # (MapType[])
        self.maps: List[Map] = []  # (Map[])
        self.masks: List[Mask] = []  # (Mask[])
        self.shaders: List[Shader] = []  # (Shader[])
        self.meshes: List[Mesh] = []  # (Mesh[])
        self.split_maps: List[SplitMap] = []  # (SplitMap[])
        self.expressions: List[Expression] = []  # (Expression[])
        self.psd_nets: List[PsdNet] = []  # (PsdNet[])
        self.psd_definitions: List[PsdDefinition] = []  # (PsdDefinition[])
        self.active_meshes: List[Mesh] = []  # (Mesh[])
        self.lod_meshes: List[LodMeshes] = []  # (LodMeshes[])
        self.skin_transfer_data: List[SkinTransferData] = []  # (SkinTransferData[])
        self.region_joints = {}
        self.region_expressions = {}

    @staticmethod
    def _determine_vector(axis) -> Tuple[float, float, float]:
        if axis == "X+":
            return 1.0, 0.0, 0.0
        if axis == "X-":
            return -1.0, 0.0, 0.0
        if axis == "Y+":
            return 0.0, 1.0, 0.0
        if axis == "Y-":
            return 0.0, -1.0, 0.0
        if axis == "Z+":
            return 0.0, 0.0, 1.0
        if axis == "Z-":
            return 0.0, 0.0, -1.0
        return 0.0, 0.0, 0.0

    def get_rig_up_vector(self) -> Tuple[float, float, float]:
        """
        Gets unit vector defining rig up direction.

        @return Rig up unit vector. (float[3])
        """

        return self._determine_vector(self.rig_up)

    def get_rig_front_vector(self) -> Tuple[float, float, float]:
        """
        Gets unit vector defining rig front direction.

        @return Rig front unit vector. (float[3])
        """

        return self._determine_vector(self.rig_front)

    def get_rig_left_vector(self) -> Tuple[float, float, float]:
        """
        Gets unit vector defining rig left direction.

        @return Rig left unit vector. (float[3])
        """

        a = self.get_rig_up_vector()
        b = self.get_rig_front_vector()
        return a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]

    def get_rig_width(self, bounding_box) -> Union[Any, float]:
        """
        Gets rig width based on given bounding box and rig orientation
        (distance from left to right).

        @param bounding_box: Rig scene bounding box (BoundingBox)
        @return Rig width. (float)
        """

        vec = self.get_rig_left_vector()
        if vec[0]:
            return bounding_box.width()
        if vec[1]:
            return bounding_box.height()
        if vec[2]:
            return bounding_box.depth()
        return 0.0

    def get_mesh_extension_str(self) -> str:
        """
        Gets string representation of mesh object_type.

        @return Mesh file extension as string. (string)
        """

        return RigDefinition.MESH_TYPE_MAP[self.mesh_type]

    def get_joint_group_by_name(self, name: str) -> Optional[JointGroup]:
        """
        Find joint group with given pattern.

        @param name: Joint group pattern. (string)
        @return Joint group or None if joint group with that pattern doesn't exist. (JointGroup)
        """

        for joint_group in self.joint_groups:
            if joint_group.name == name:
                return joint_group
        return None

    def get_mask_by_name(self, name: str) -> Optional[Mask]:
        """
        Find mask with given pattern.

        @param name: Mask pattern. (string)
        @return Mask or None if mask with that pattern doesn't exist. (Mask)
        """

        for mask in self.masks:
            if mask.name == name:
                return mask
        return None

    def get_map_type_by_name(self, name: str) -> Optional[MapType]:
        """
        Find map object_type with given pattern.

        @param name: Map object_type pattern. (string)
        @return Map object_type or None if map object_type with that pattern doesn't exist. (MapType)
        """

        for map_type in self.map_types:
            if map_type.name == name:
                return map_type
        return None

    def get_base_map(self, map_type_name: str) -> Optional[Map]:
        """
        Gets base map for given map object_type pattern.

        @param map_type_name: Map object_type pattern. (string)
        @return Base map if exists, otherwise None. (Map)
        """

        base_map: Map
        for base_map in self.maps:
            assert base_map.map_type is not None
            if base_map.map_type.name == map_type_name and base_map.base_map:
                return base_map
        return None

    def get_animated_maps(self, map_type_name: str) -> List[Map]:
        """
        Gets animated map (not base maps) for given map object_type pattern.

        @param map_type_name: Map object_type pattern. (string)
        @return List of animated maps for given map object_type. (Map[])
        """

        animated_maps = []
        anim_map: Map
        for anim_map in self.maps:
            assert anim_map.map_type is not None
            if anim_map.map_type.name == map_type_name and not anim_map.base_map:
                animated_maps.append(anim_map)
        return animated_maps

    def get_map_by_name(self, name: str) -> Optional[Map]:
        """
        Find map with given pattern.

        @param name: Map pattern. (string)
        @return Map or None if map with that pattern doesn't exist. (Map)
        """

        for map_ in self.maps:
            if map_.name == name:
                return map_
        return None

    def get_shader_by_name(self, name: str) -> Optional[Shader]:
        """
        Find shader with given pattern.

        @param name: Shader pattern. (string)
        @return Shader or None if shader with that pattern doesn't exist. (Shader)
        """

        for shader in self.shaders:
            if shader.name == name:
                return shader
        return None

    def get_mesh_by_name(self, name: str) -> Optional[Mesh]:
        """
        Find mesh with given pattern.

        @param name: Mesh pattern. (string)
        @return Mesh or None if mesh with that pattern doesn't exist. (Mesh)
        """

        for mesh in self.meshes:
            if mesh.name == name:
                return mesh
        return None

    def get_split_map_by_name(self, name: str) -> Optional[SplitMap]:
        """
        Find split map with given pattern.

        @param name: Split map pattern. (string)
        @return Split map or None if split map with that pattern doesn't exist. (SplitMap)
        """

        for split_map in self.split_maps:
            if split_map.name == name:
                return split_map
        return None

    def get_psd_net_by_name(self, name: str) -> Optional[PsdNet]:
        """
        Find PSD net with given pattern.

        @param name: PSD pattern. (string)
        @return PSD net or None if PSD net with that pattern doesn't exist. (PsdNet)
        """

        for psd_net in self.psd_nets:
            if psd_net.name == name:
                return psd_net
        return None

    def get_psd_net_by_output(self, expression_name: str) -> Optional[PsdNet]:
        """
        Find PSD net with given output expression.

        @param expression_name: output expression's pattern. (string)
        @return PSD net or None if PSD net doesn't exist. (PsdNet)
        """

        expression = self.get_expression_by_name(expression_name)
        if not expression:
            return None
        for psd_net in self.psd_nets:
            for exp_attr in expression.expression_attrs:
                if (
                    psd_net.output.object_name == exp_attr.object_name
                    and psd_net.output.attr_name == exp_attr.attr_name
                ):
                    return psd_net
        return None

    def get_psd_def_by_name(self, name: str) -> Optional[PsdDefinition]:
        """
        Find PSD definition with given pattern.

        @param name: PSD definition pattern. (string)
        @return PSD definition or None if PSD definition with that pattern doesn't exist. (PsdDefinition)
        """

        for psd_def in self.psd_definitions:
            if psd_def.name == name:
                return psd_def
        return None

    def get_psd_def_for_expression(self, expression_name: str) -> Optional[PsdDefinition]:
        """
        Gets PSD definition for given expression pattern.

        @param expression_name: Expression pattern. (string)
        @return PSD definition for given expression if exists, otherwise None. (PsdDefinition)
        """

        for psd_definition in self.psd_definitions:
            if psd_definition.is_expression_in_psd(expression_name):
                return psd_definition
        return None

    def get_expression_by_id(self, index: int) -> Optional[Expression]:
        """
        Gets expression for given id.

        @param index: Expression id. (int)
        @return Expression if exists, otherwise None. (Expression)
        """

        for exp in self.expressions:
            if exp.id == index:
                return exp
        return None

    def get_expression_by_name(self, name: str) -> Optional[Expression]:
        """
        Gets expression for given expression pattern.

        @param name: Expression pattern. (string)
        @return Expression if exists, otherwise None. (Expression)
        """

        for exp in self.expressions:
            if exp.name == name:
                return exp
        return None

    def get_expressions_names(self) -> List[str]:
        """
        Gets names of all expressions.

        @return List of names.
        """

        expressions_names = []
        for expression in self.expressions:
            expressions_names.append(expression.name)
        return expressions_names

    def get_map_mask_multipliers(self, expressions: Optional[List[Expression]] = None) -> MapMaskMultipliers:
        """
        Gets MapMaskMultipliers object which holds information about shader node
        network and its multipliers.

        @param expressions: List of expression for which multipliers has to be calculated.
            If None than all expressions from definition are used. (Expression[])
        @return: Map mask multipliers object. (MapMaskMultipliers)
        """

        if not expressions:
            expressions = self.expressions
        multipliers = MapMaskMultipliers()
        for expression in expressions:
            for mie in expression.maps_in_expression:
                map_ = mie.map
                for mask in mie.masks:
                    multipliers.add_multiplier(map_, mask, expression)
        return multipliers

    def add_new_psd_definition(self, psd_definition: PsdDefinition):
        """
        Adds new PsdDefinition object into rig definition.

        This method makes sure that model stays consistent after adding new psd definition.
        @param psd_definition: Psd definition object. (PsdDefinition)
        """

        # connect with other psd definitions via sub_sets and super_sets
        for psd in self.psd_definitions:
            psd.connect_with(psd_definition)

        # add psd definition
        self.psd_definitions.append(psd_definition)

        # recalculate psd definition layers
        for psd in self.psd_definitions:
            psd.refresh_layer()

        # sort psd definitions by layers
        self.psd_definitions = sorted(self.psd_definitions, key=lambda psd_def: psd_def.layer)

    def psd_definition_changed(self, psd_definition: PsdDefinition):
        """
        Reconnects psd definitions after one psd_definition is changed.

        This method makes sure that model stays consistent after changing psd definition.
        @param psd_definition: Psd definition object. (PsdDefinition)
        """

        for psd in self.psd_definitions:
            psd.disconnect_with(psd_definition)

        psd_definition.super_sets = []
        psd_definition.sub_sets = []

        # connect with other psd definitions via sub_sets and super_sets
        for psd in self.psd_definitions:
            psd.connect_with(psd_definition)

        # recalculate psd definition layers
        for psd in self.psd_definitions:
            psd.refresh_layer()

        # sort psd definitions by layers
        self.psd_definitions = sorted(self.psd_definitions, key=lambda psd_def: psd_def.layer)

    def _remove_joint_from_joint_groups(self, joint: Joint):
        """
        Remove joint and its children from all joint groups.

        @param joint: Joint to remove. (Joint)
        """

        for joint_group in self.joint_groups:
            if joint in joint_group.joints:
                joint_group.joints.remove(joint)
        for child in joint.children:
            self._remove_joint_from_joint_groups(child)

    def remove_joint(self, joint_name: str):
        """
        Remove joint with given pattern from definition.

        @param joint_name: Joint pattern. (string)
        """

        joint = self.joints.get_element(joint_name)
        roots = self.joints.get_elements()
        if joint.parent:
            joint.parent.children.remove(joint)
        else:
            roots.remove(joint)
        self.joints = DataHolder(roots)
        self._remove_joint_from_joint_groups(joint)

    def remove_joint_group(self, joint_group_name: str):
        """
        Remove joint group with given pattern from definition.

        @param joint_group_name: Joint group pattern. (string)
        """
        joint_group: Optional[JointGroup] = self.get_joint_group_by_name(joint_group_name)
        if joint_group:
            self.joint_groups.remove(joint_group)
            for expression in self.expressions:
                if expression.function and expression.function.function_type == ExpressionFunction.FUNCTION_DERIVED:
                    assert isinstance(expression.function, DerivedExpFunc)
                    for split_joint in expression.function.split_joints:
                        if split_joint.joint_group == joint_group:
                            expression.function.split_joints.remove(split_joint)

    def remove_mask(self, mask_name: str):
        """
        Remove mask with given pattern from definition.

        @param mask_name: Mask pattern. (string)
        """

        mask: Optional[Mask] = self.get_mask_by_name(mask_name)
        if mask:
            self.masks.remove(mask)
            for expression in self.expressions:
                for mie in expression.maps_in_expression:
                    if mask in mie.masks:
                        mie.masks.remove(mask)

    def remove_map_type(self, map_type_name: str):
        """
        Remove map object_type with given pattern from definition.

        @param map_type_name: Map object_type pattern. (string)
        """

        map_type: Optional[MapType] = self.get_map_type_by_name(map_type_name)
        if map_type:
            self.map_types.remove(map_type)
            for map_ in self.maps:
                if map_.map_type == map_type:
                    map_.map_type = None
            for shader in self.shaders:
                for shader_input in shader.inputs:
                    if map_type in shader_input.map_types:
                        shader_input.map_types.remove(map_type)

    def remove_map(self, map_name: str):
        """
        Remove map with given pattern from definition.

        @param map_name: Map pattern. (string)
        """

        map_: Optional[Map] = self.get_map_by_name(map_name)
        if map_:
            self.maps.remove(map_)
            for expression in self.expressions:
                for mie in expression.maps_in_expression:
                    if mie.map == map_:
                        expression.maps_in_expression.remove(mie)

    def remove_shader(self, shader_name: str):
        """
        Remove shader with given pattern from definition.

        @param shader_name: Shader pattern. (string)
        """

        shader: Optional[Shader] = self.get_shader_by_name(shader_name)
        if shader:
            self.shaders.remove(shader)
            for mesh in self.meshes:
                if mesh.shader == shader:
                    mesh.shader = None

    def remove_mesh(self, mesh_name: str):
        """
        Remove mesh with given pattern from definition.

        @param mesh_name: Mesh pattern. (string)
        """

        mesh: Optional[Mesh] = self.get_mesh_by_name(mesh_name)
        if mesh:
            self.meshes.remove(mesh)
            for split_map in self.split_maps:
                if split_map.mesh == mesh:
                    split_map.mesh = None
            for expression in self.expressions:
                for mie in expression.meshes_in_expression:
                    if mie.mesh == mesh:
                        expression.meshes_in_expression.remove(mie)
                        continue

    def remove_split_map(self, split_map_name: str):
        """
        Remove split map with given pattern from definition.

        @param split_map_name: Split map pattern. (string)
        """

        split_map: Optional[SplitMap] = self.get_split_map_by_name(split_map_name)
        if split_map:
            self.split_maps.remove(split_map)
            for expression in self.expressions:
                if expression.function and expression.function.function_type == ExpressionFunction.FUNCTION_DERIVED:
                    assert isinstance(expression.function, DerivedExpFunc)
                    if split_map in expression.function.split_maps:
                        expression.function.split_maps.remove(split_map)

    def remove_expression(self, expression_name: str):
        """
        Remove expression with given pattern from definition.

        @param expression_name: Expression pattern. (string)
        """

        expression = self.get_expression_by_name(expression_name)
        if expression:
            self.expressions.remove(expression)

            for exp in self.expressions:
                exp.remove_expression(expression)

            for psd_definition in self.psd_definitions:
                psd_definition.remove_expression(expression_name)

    def remove_psd_net(self, psd_net_name: str):
        """
        Remove PSD net with given pattern from definition.

        @param psd_net_name: PSD nets pattern. (string)
        """

        psd_net = self.get_psd_net_by_name(psd_net_name)
        if psd_net:
            self.psd_nets.remove(psd_net)
            for psd_definition in self.psd_definitions:
                psd_definition.remove_psd_net(psd_net_name)

    def remove_psd_definition(self, psd_definition_name: str):
        """
        Removes PsdDefinition object from rig definition.

        This method makes sure that model stays consistent after removing PSD definition.
        @param psd_definition_name: PSD definition object. (PsdDefinition)
        """

        psd_definition = self.get_psd_def_by_name(psd_definition_name)
        if not psd_definition:
            return

        # connect with other psd definitions via sub_sets and super_sets
        for psd in self.psd_definitions:
            psd.disconnect_with(psd_definition)

        # remove psd definition
        self.psd_definitions.remove(psd_definition)

        # recalculate psd definition layers
        for psd in self.psd_definitions:
            psd.refresh_layer()

        # sort psd definitions by layers
        self.psd_definitions = sorted(self.psd_definitions, key=lambda psd_def: psd_def.layer)

    def filter_expressions_by_name(self, pattern: str) -> List[Expression]:
        """
        Filter all expressions by string.
        Returns list of expressions whose name contain pattern.

        @param pattern: String to find in names. (string)
        @return List of expressions whose names contain pattern. (Expression[])
        """

        reg = pattern.replace("*", ".*")
        prog = re.compile(reg, re.IGNORECASE)
        result = []
        for exp in self.expressions:
            if prog.search(exp.name):
                result.append(exp)
        return result

    def filter_psd_nets_by_name(self, pattern: str) -> List[PsdNet]:
        """
        Filter all psd nets by string.
        Returns list of psd nets whose pattern contain pattern.

        @param pattern: String to find in names. (string)
        @return List of psd nets whose names contain pattern. (PsdNet[])
        """

        reg = pattern.replace("*", ".*")
        prog = re.compile(reg, re.IGNORECASE)
        result = []
        for psd_net in self.psd_nets:
            if prog.search(psd_net.name):
                result.append(psd_net)
        return result

    def filter_psd_defs_by_name(self, pattern: str) -> List[PsdDefinition]:
        """
        Filter all psd defs by string.
        Returns list of psd defs whose pattern contain pattern.

        @param pattern: String to find in names. (string)
        @return List of psd defs whose names contain pattern. (PsdDefinition[])
        """

        reg = pattern.replace("*", ".*")
        prog = re.compile(reg, re.IGNORECASE)
        result = []
        for psd_def in self.psd_definitions:
            if prog.search(psd_def.name):
                result.append(psd_def)
        return result

    def filter_expressions_by_filter(self, exp_filter: ExpressionsFilter) -> List[Expression]:
        """
        Filter all expressions by filter object.
        Returns list of expressions that satisfies filter.

        @param exp_filter: String to find in names. (string)
        @return List of expressions whose names contain pattern. (Expression[])
        """

        if exp_filter.filter_string:
            filtered_expressions = self.filter_expressions_by_name(exp_filter.filter_string)
        else:
            filtered_expressions = self.expressions

        expressions = []
        for expression in filtered_expressions:
            if exp_filter.types[expression.type]:
                # if expression is psd expression
                if expression.is_psd_expression():
                    # if filter is set to all layers add expression to expressions list
                    if not exp_filter.layer:
                        expressions.append(expression)
                        continue
                    # if filter.layer is set append only psd expressions from provided layer
                    psd_def = self.get_psd_def_for_expression(expression.name)
                    if psd_def and psd_def.layer == exp_filter.layer:
                        expressions.append(expression)
                # if expression is not psd expression layer filter has no meaning
                else:
                    expressions.append(expression)
        filtered_expressions = expressions

        if exp_filter.active:
            active_expressions = exp_filter.active_expressions
            if exp_filter.active_dependent:
                dictionary: Dict[str, Expression] = {}
                for expression_name in active_expressions:
                    exp = self.get_expression_by_name(expression_name)
                    if exp:
                        exp.get_generated_expressions_dict(dictionary, exp_filter.include_targets)
                active_expressions = list(dictionary.keys())
                for expression_name in active_expressions:
                    self.get_dependent_psd_definitions_for_expression(expression_name, dictionary)
                active_expressions = list(dictionary.keys())

            filtered_expressions = []
            for expression in expressions:
                if expression.name in active_expressions:
                    filtered_expressions.append(expression)

        return filtered_expressions

    def get_dependent_psd_definitions_for_expression(self, expression_name: str, dictionary: Dict[str, Expression]):
        """
        Get all psd definitions dependent on expression with expression_name pattern.
        Returns list of expressions that satisfy filter.

        @param expression_name: Expression pattern. (string)
        @param dictionary: dictionary of dependent expressions (key - expression pattern, value - Expression). (dictionary)
        """
        for psd_def in self.psd_definitions:
            if psd_def and psd_def.complex_pose and psd_def.complex_pose.name in dictionary:
                continue
            if psd_def and psd_def.is_complex_dependent_on_expression(expression_name):
                if psd_def.complex_pose and psd_def.complex_pose.name not in dictionary:
                    dictionary[psd_def.complex_pose.name] = psd_def.complex_pose
                if psd_def.target_pose and psd_def.target_pose.name not in dictionary:
                    dictionary[psd_def.target_pose.name] = psd_def.target_pose
                if psd_def.corrective_pose and psd_def.corrective_pose.name not in dictionary:
                    dictionary[psd_def.corrective_pose.name] = psd_def.corrective_pose

    def sort_expressions(self, source_definition: "RigDefinition"):
        """
        Function will sort self. expression list in same order
        they are sorted in sourceDefinition.

        @param source_definition: Source definition. (RigDefinition)
        """

        t_index = 0
        s_expressions = source_definition.expressions
        for s_index, _ in enumerate(s_expressions):
            source_expression = s_expressions[s_index]
            target_expression = self.get_expression_by_name(source_expression.name)
            if target_expression:
                self.expressions.remove(target_expression)
                self.expressions.insert(t_index, target_expression)
                t_index += 1

    def update_active_meshes(self, active_mesh_names: List[str]):
        self.active_meshes = []
        if active_mesh_names:
            for mesh in self.meshes:
                if mesh.name in active_mesh_names:
                    self.active_meshes.append(mesh)

    def get_active_mesh_names(self) -> List[str]:
        mesh_names = []
        for mesh in self.get_active_meshes():
            mesh_names.append(mesh.name)
        return mesh_names

    def get_active_meshes(self) -> List[Mesh]:
        return self.active_meshes

    def get_dna_mesh_names(self) -> List[str]:
        all_meshes = [mesh.name for mesh in self.meshes]
        unique_meshes = set()
        dna_mesh_names = []

        for meshes in self.lod_meshes:
            if meshes is None:
                meshes = all_meshes
            for mesh in meshes.meshes:
                if mesh not in unique_meshes:
                    unique_meshes.add(mesh)
                    dna_mesh_names.append(mesh)

        return dna_mesh_names

    def clear_derived_skin_weights(self, mesh_name: str):
        skin_transfer_data: SkinTransferData
        for skin_transfer_data in self.skin_transfer_data:
            if skin_transfer_data.skin_base_mesh == mesh_name:
                skin_transfer_data.skinning_data = None
                self.clear_derived_skin_weights(skin_transfer_data.name)

    def get_skinning_data(self, mesh_name: str) -> Optional[SkinningData]:
        for skinTransferData in self.skin_transfer_data:
            if skinTransferData.name == mesh_name:
                return skinTransferData.skinning_data
        return None

    def set_skinning_data(self, mesh_name: str, skinning_data: SkinningData):
        for skinTransferData in self.skin_transfer_data:
            if skinTransferData.name == mesh_name:
                skinTransferData.skinning_data = skinning_data

    def get_skinning_base_mesh_name(self, mesh_name: str) -> Optional[str]:
        for skinTransferData in self.skin_transfer_data:
            if skinTransferData and skinTransferData.name == mesh_name:
                return skinTransferData.skin_base_mesh
        return None

    def get_geometry_base_mesh_name(self, mesh_name: str) -> Optional[str]:
        for skinTransferData in self.skin_transfer_data:
            if skinTransferData.name == mesh_name:
                return skinTransferData.geo_base_mesh
        return None

    def get_skinning_joint_mapping(self, mesh_name: str) -> Optional[Dict[str, Optional[List[str]]]]:
        for skinTransferData in self.skin_transfer_data:
            if skinTransferData.name == mesh_name:
                return skinTransferData.mapping
        return None
