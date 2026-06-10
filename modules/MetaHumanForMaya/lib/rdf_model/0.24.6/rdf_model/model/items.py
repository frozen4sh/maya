# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

from enum import IntEnum
from typing import List, Optional

from .common import SectionDict, SectionItem, SectionList


class TranslationUnit(IntEnum):
    cm = 0
    m = 1


class RotationUnit(IntEnum):
    degrees = 0
    radians = 1


class Direction(IntEnum):
    left = 0
    right = 1
    up = 2
    down = 3
    front = 4
    back = 5


class CoordinateSystem:
    @classmethod
    def create_maya_coordinate_system(cls) -> CoordinateSystem:
        return cls(Direction.right, Direction.up, Direction.front)

    @classmethod
    def create_ue5_coordinate_system(cls) -> CoordinateSystem:
        return cls(Direction.front, Direction.right, Direction.up)

    def __init__(self, x_axis: Direction, y_axis: Direction, z_axis: Direction) -> None:
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.z_axis = z_axis

    def __repr__(self) -> str:
        return f"CoordinateSystem: {self.x_axis}, {self.y_axis}, {self.z_axis}"


class Descriptor:
    def __init__(
        self,
        translation_unit: TranslationUnit,
        rotation_unit: RotationUnit,
        coordinate_system: CoordinateSystem,
        db_complexity: str,
        db_name: str,
    ):
        self.translation_unit = translation_unit
        self.rotation_unit = rotation_unit
        self.coordinate_system = coordinate_system
        self.db_complexity = db_complexity
        self.db_name = db_name

    def __repr__(self) -> str:
        return f"Descriptor: {self.translation_unit}, {self.rotation_unit}, {str(self.coordinate_system)}, {self.db_complexity}, {self.db_name}"


class ControlType(IntEnum):
    Raw = 0
    PSD = 1
    ML = 2
    RBF = 3
    Unspecified = 65535
    GUI = 999


class Control(SectionItem):
    NO_CONTROL: int = 65535

    @staticmethod
    def format_name(object_name: str, attribute_name: str) -> str:
        return f"{object_name}.{attribute_name}"

    def __init__(
        self,
        name: str,
        from_value: float,
        to_value: float,
        control_type: ControlType,
        is_exported: bool = False,
        expression: Optional[Expression] = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.is_exported = is_exported
        self.from_value = from_value
        self.to_value = to_value
        self.control_type = control_type
        self._expression: Optional[Expression] = None
        if expression:
            self.expression = expression

    @property
    def expression(self) -> Optional[Expression]:
        return self._expression

    @expression.setter
    def expression(self, exp: Expression) -> None:
        self._expression = exp
        if exp and exp.control is not self:
            exp.control = self

    def __repr__(self) -> str:
        return f"Control: {self.name}, {self.is_exported}, {self.from_value}, {self.to_value}"

    def key(self) -> str:
        return self.name

    def get_object_name(self) -> str:
        return self.name.split(".")[0]

    def get_attribute_name(self) -> str:
        parts = self.name.split(".")
        if len(parts) > 1:
            return parts[1]
        return ""


class GUIControl(Control):
    def __init__(
        self,
        name: str,
        from_value: float,
        to_value: float,
    ):
        super().__init__(name, from_value, to_value, ControlType.GUI)

    def __repr__(self) -> str:
        return f"GUI Control: {self.name}, {self.from_value}, {self.to_value}"


class ControlMapping(SectionItem):
    def __init__(
        self,
        in_control: GUIControl,
        out_control: Control,
        from_value: float = 0.0,
        to_value: float = 1.0,
        slope_value: float = 1.0,
        cut_value: float = 0.0,
    ) -> None:
        super().__init__()
        self.in_control = in_control
        self.out_control = out_control
        self.from_value = from_value
        self.to_value = to_value
        self.slope_value = slope_value
        self.cut_value = cut_value

    def __repr__(self) -> str:
        in_name = self.in_control.name
        out_name = self.out_control.name
        return f"ControlMapping: {in_name}, {out_name}, {self.from_value}, {self.to_value}, {self.slope_value}, {self.cut_value}"

    def key(self) -> str:
        return self.in_control.name


class Joint(SectionItem):
    def __init__(
        self,
        name: str,
        parent: Optional[Joint] = None,
        color: List[float] = [0.5, 0.5, 0.5],
        radius: float = 1.0,
    ) -> None:
        super().__init__()
        self.name = name
        self.parent = parent
        self.color = color.copy()
        self.radius = radius

    def __repr__(self) -> str:
        parent_name = self.parent.name if self.parent else ""
        return f"Joint: {self.name}, {parent_name}, {self.color}, {self.radius}"

    def key(self) -> str:
        return self.name

    def get_ancestors(self) -> List[Joint]:
        ancestors = [self]
        parent = self.parent
        while parent is not None:
            ancestors.append(parent)
            parent = parent.parent
        ancestors.reverse()
        return ancestors


class JointGroup(SectionItem):
    def __init__(self, name: str, joints: List[Joint] = []) -> None:
        super().__init__()
        self.name = name
        self.joints = SectionDict[Joint](joints)

    def __repr__(self) -> str:
        joint_names = [joint.name for joint in self.joints]
        return f"JointGroup: {self.name}, {joint_names}"

    def key(self) -> str:
        return self.name

    def add_joint(self, joint: Joint) -> None:
        self.joints.add(joint)

    def remove_joint(self, name: str) -> Optional[Joint]:
        return self.joints.remove(name)


class Region(SectionItem):
    def __init__(self, name: str, joints: List[Joint] = []) -> None:
        super().__init__()
        self.name = name
        self.joints = SectionDict[Joint](joints)

    def add_joint(self, joint: Joint) -> None:
        self.joints.add(joint)

    def remove_joint(self, name: str) -> Optional[Joint]:
        return self.joints.remove(name)

    def __repr__(self) -> str:
        return f"Region: {self.name}"

    def key(self) -> str:
        return self.name


class AnimatedMapChannel(SectionItem):
    @staticmethod
    def format_name(texture_map_name: str, texture_mask_name: str) -> str:
        return f"{texture_map_name}.{texture_mask_name}"

    def __init__(self, texture_map_name: str, texture_mask_name: str) -> None:
        super().__init__()
        self.name = AnimatedMapChannel.format_name(texture_map_name, texture_mask_name)
        self.texture_map_name = texture_map_name
        self.texture_mask_name = texture_mask_name

    def __repr__(self) -> str:
        return f"AnimatedMapChannel: {self.name}"

    def key(self) -> str:
        return self.name


class TextureMask(SectionItem):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __repr__(self) -> str:
        return f"TextureMask: {self.name}"

    def key(self) -> str:
        return self.name


class TextureMapType(SectionItem):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __repr__(self) -> str:
        return f"TextureMapType: {self.name}"

    def key(self) -> str:
        return self.name


class TextureMap(SectionItem):
    def __init__(self, name: str, map_type: TextureMapType, is_base: bool = True) -> None:
        super().__init__()
        self.name = name
        self.map_type: Optional[TextureMapType] = map_type
        self.is_base = is_base

    def __repr__(self) -> str:
        type_name = self.map_type.name if self.map_type else ""
        return f"TextureMap: {self.name}, {type_name}, {self.is_base}"

    def key(self) -> str:
        return self.name


class ShaderParameter(SectionItem):
    def __init__(self, name: str, value: float) -> None:
        super().__init__()
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return f"ShaderParameter: {self.name}, {self.value}"

    def key(self) -> str:
        return self.name


class ShaderInput(SectionItem):
    def __init__(self, name: str, map_type: TextureMapType) -> None:
        super().__init__()
        self.name = name
        self.map_type: Optional[TextureMapType] = map_type

    def __repr__(self) -> str:
        map_type_name = self.map_type.name if self.map_type else ""
        return f"ShaderInput: {self.name}, {map_type_name}"

    def key(self) -> str:
        return self.name


class ShaderType(IntEnum):
    Blinn = 1
    DX11 = 2
    Unspecified = 65535


class Shader(SectionItem):
    def __init__(
        self,
        name: str,
        shader_type: ShaderType,
        parameters: List[ShaderParameter] = [],
        inputs: List[ShaderInput] = [],
    ) -> None:
        super().__init__()
        self.name = name
        self.shader_type = shader_type
        self.parameters = SectionDict[ShaderParameter](parameters)
        self.inputs = SectionDict[ShaderInput](inputs)

    def __repr__(self) -> str:
        type_name = self.shader_type.name if self.shader_type else ""
        return f"Shader: {self.name}, {type_name}"

    def key(self) -> str:
        return self.name

    def add_parameter(self, parameter: ShaderParameter) -> None:
        self.parameters.add(parameter)

    def add_input(self, value: ShaderInput) -> None:
        self.inputs.add(value)

    def remove_parameter(self, name: str) -> Optional[ShaderParameter]:
        return self.parameters.remove(name)

    def remove_input(self, name: str) -> Optional[ShaderInput]:
        return self.inputs.remove(name)


class Face(SectionItem):
    def __init__(self, vertex_indices: List[int] = []) -> None:
        super().__init__()
        self.vertex_indices = vertex_indices

    def __repr__(self):
        return f"Face {self.index}: {self.vertex_indices}"

    def key(self) -> str:
        return str(self.index)


class Mesh(SectionItem):
    def __init__(
        self,
        name: str,
        shader: Shader,
        is_exported: bool = True,
        vertex_count: int = 0,
        uv_count: int = 0,
        faces: List[Face] = [],
        max_IPV: int = 8,
        blend_shape_count: int = 0,
    ) -> None:
        super().__init__()
        self.name = name
        self.shader: Optional[Shader] = shader
        self.is_exported = is_exported
        self.vertex_count = vertex_count
        self.uv_count = uv_count
        self.faces = SectionList[Face](faces)
        self.max_IPV = max_IPV
        self.blend_shape_count = blend_shape_count

    def __repr__(self) -> str:
        shader_name = self.shader.name if self.shader else ""
        return f"Mesh: {self.name}, {shader_name}, {self.is_exported}"

    def __eq__(self, value) -> bool:
        if isinstance(value, Mesh):
            return self.name == value.name
        return False

    def __hash__(self) -> int:
        return hash(self.name)

    def key(self) -> str:
        return self.name

    def add_face(self, face: Face) -> None:
        self.faces.add(face)


class AnimatedMap(SectionItem):
    def __init__(self, texture_map: TextureMap, texture_masks: List[TextureMask] = []) -> None:
        super().__init__()
        self.texture_map = texture_map
        self.texture_masks = SectionDict[TextureMask](texture_masks)
        self.animated_map_channels = SectionDict[AnimatedMapChannel]()

    def __repr__(self) -> str:
        map_name = self.texture_map.name
        mask_names = [mask.name for mask in self.texture_masks]
        return f"AnimatedMap: {map_name}, {mask_names}"

    def key(self) -> str:
        return self.texture_map.name

    def add_texture_mask(self, texture_mask: TextureMask) -> None:
        self.texture_masks.add(texture_mask)

    def add_animated_map_channel(self, am_channel: AnimatedMapChannel) -> None:
        self.animated_map_channels.add(am_channel)

    def remove_texture_mask(self, name: str) -> Optional[TextureMask]:
        return self.texture_masks.remove(name)

    def remove_animated_map_channel(self, name: str) -> Optional[AnimatedMapChannel]:
        return self.animated_map_channels.remove(name)


class SplitJoints(SectionItem):
    def __init__(
        self,
        joint_group: JointGroup,
        multiplier: float = 0.0,
        rotation: List[float] = [0.0, 0.0, 0.0],
    ) -> None:
        super().__init__()
        self.joint_group = joint_group
        self.multiplier = multiplier
        self.rotation = rotation.copy()

    def __repr__(self) -> str:
        joint_group_name = self.joint_group.name if self.joint_group else ""
        return f"SplitJoints: {joint_group_name}, {self.multiplier}, {self.rotation}"

    def key(self) -> str:
        return self.joint_group.name


class SplitMap(SectionItem):
    def __init__(self, name: str, mesh: Mesh, weights: List[float] = []) -> None:
        super().__init__()
        self.name = name
        self.mesh: Optional[Mesh] = mesh
        if len(weights) == 0:
            weights = [0.0 for _ in range(mesh.vertex_count)]
        self.weights = weights.copy()

    def __repr__(self) -> str:
        mesh_name = self.mesh.name if self.mesh else ""
        return f"SplitMap: {self.name}, {mesh_name}"

    def key(self) -> str:
        return self.name


class ExpressionType(IntEnum):
    Main = 1
    Split = 2
    Complex = 3
    Target = 4
    Corrective = 5
    RBFPose = 6
    Unspecified = 65535


class DeformationType(IntEnum):
    JointsOnly = 1
    BlendShapesOnly = 2
    JointsAndBlendShapes = 3
    Unspecified = 65535


class MeshDeformer(SectionItem):
    def __init__(
        self,
        mesh: Mesh,
        deformation_type: DeformationType,
    ) -> None:
        super().__init__()
        self.mesh = mesh
        self.deformation_type = deformation_type

    def __repr__(self) -> str:
        return f"MeshDeformer: {self.mesh.name}, {self.deformation_type}"

    def __eq__(self, value) -> bool:
        if isinstance(value, MeshDeformer):
            return self.mesh.name == value.mesh.name
        return False

    def __hash__(self) -> int:
        return hash(self.mesh.name)

    def key(self) -> str:
        return self.mesh.name

    def is_blends(self) -> bool:
        return self.deformation_type in (
            DeformationType.BlendShapesOnly,
            DeformationType.JointsAndBlendShapes,
        )

    def is_joints(self) -> bool:
        return self.deformation_type in (
            DeformationType.JointsOnly,
            DeformationType.JointsAndBlendShapes,
        )


class ExpressionFunctionType(IntEnum):
    NoOperation = 0
    Split = 1
    Subtract = 2
    Sum = 10
    Phase = 11
    Unspecified = 65535


class ExpressionFunction(SectionItem):
    def __init__(self) -> None:
        super().__init__()
        self.function_type = ExpressionFunctionType.Unspecified

    def get_input_expressions(self) -> List:
        return []

    @property
    def elements(self):
        return []


class Expression(SectionItem):
    def __init__(self, name: str, expression_type: ExpressionType, is_exported: bool, phase_count: int = 1) -> None:
        super().__init__()
        self.name = name
        self.expression_type = expression_type
        self.is_exported = is_exported
        self.phase_count = phase_count

        self._control: Optional[Control] = None

        self.animated_maps = SectionList[AnimatedMap]()
        self.mesh_deformers = SectionList[MeshDeformer]()

        self.function: (
            NoOperationExpressionFunction
            | SplitExpressionFunction
            | SubtractExpressionFunction
            | SumExpressionFunction
            | PhaseExpressionFunction
        ) = NoOperationExpressionFunction()
        self.regions = SectionDict[Region]()

    @property
    def control(self) -> Optional[Control]:
        return self._control

    @control.setter
    def control(self, ctrl: Optional[Control]):
        self._control = ctrl
        if ctrl and ctrl.expression is not self:
            ctrl.expression = self

    def __repr__(self) -> str:
        ctrl_name = self.control.name if self.control else ""
        return f"Expression: {self.name}, {self.expression_type}, {self.is_exported}, {self.phase_count}, {ctrl_name}"

    def key(self) -> str:
        return self.name

    def set_control(self, control: Control) -> None:
        self.control = control
        self.control.expression = self

    def add_animated_map(self, animated_map: AnimatedMap) -> None:
        self.animated_maps.add(animated_map)

    def add_mesh_deformer(self, mesh_deformer: MeshDeformer) -> None:
        self.mesh_deformers.add(mesh_deformer)

    def add_region(self, region: Region) -> None:
        self.regions.add(region)

    def remove_animated_map(self, index: int) -> Optional[AnimatedMap]:
        return self.animated_maps.remove(index)

    def remove_mesh_deformer(self, index: int) -> Optional[MeshDeformer]:
        return self.mesh_deformers.remove(index)

    def remove_region(self, name: str) -> Optional[Region]:
        return self.regions.remove(name)

    def is_psd(self) -> bool:
        return self.expression_type in (
            ExpressionType.Complex,
            ExpressionType.Target,
            ExpressionType.Corrective,
        )


class ExpressionMultiplier(SectionItem):
    def __init__(self, expression: Expression, multiplier: float = 1.0) -> None:
        self.expression: Optional[Expression] = expression
        self.multiplier = multiplier

    def __repr__(self) -> str:
        exp_name = self.expression.name if self.expression else ""
        return f"ExpressionMultiplier: {exp_name}, {self.multiplier}"

    def key(self) -> str:
        exp_name = self.expression.name if self.expression else ""
        return f"{self.multiplier} {exp_name}"


class NoOperationExpressionFunction(ExpressionFunction):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.function_type = ExpressionFunctionType.NoOperation
        self.index = None  # type: ignore

    def __repr__(self) -> str:
        return "NoOperationExpressionFunction"


class SplitExpressionFunction(ExpressionFunction):
    def __init__(
        self,
        source_expression: Expression,
        split_maps: List[SplitMap] = [],
        split_joints: List[SplitJoints] = [],
    ) -> None:
        super().__init__()
        self.function_type = ExpressionFunctionType.Split
        self.source_expression: Optional[Expression] = source_expression
        self.split_maps = SectionDict[SplitMap](split_maps)
        self.split_joints = SectionList[SplitJoints](split_joints)

    def __repr__(self) -> str:
        src_name = self.source_expression.name if self.source_expression else ""
        split_map_names = [sm.name for sm in self.split_maps]
        return f"SplitExpressionFunction: {src_name}, {split_map_names}"

    def get_input_expressions(self) -> List:
        return [self.source_expression]

    def add_split_map(self, split_map: SplitMap) -> None:
        self.split_maps.add(split_map)

    def add_split_joint(self, split_joint: SplitJoints) -> None:
        self.split_joints.add(split_joint)

    def remove_split_map(self, name: str) -> Optional[SplitMap]:
        return self.split_maps.remove(name)

    def remove_split_joint(self, index: int) -> Optional[SplitJoints]:
        return self.split_joints.remove(index)


class SubtractExpressionFunction(ExpressionFunction):
    def __init__(self, minuend: ExpressionMultiplier, subtrahend: ExpressionMultiplier) -> None:
        super().__init__()
        self.function_type = ExpressionFunctionType.Subtract
        self.minuend = minuend
        self.subtrahend = subtrahend

    def __repr__(self) -> str:
        return f"SubtractExpressionFunction: {str(self.minuend)}, {str(self.subtrahend)}"

    @property
    def elements(self):
        return [self.minuend, self.subtrahend]

    def get_input_expressions(self) -> List:
        return [self.minuend.expression, self.subtrahend.expression]


class SumExpressionFunction(ExpressionFunction):
    def __init__(self, elements: List[ExpressionMultiplier] = []) -> None:
        super().__init__()
        self.function_type = ExpressionFunctionType.Sum
        self._elements: List[ExpressionMultiplier] = elements.copy()

    def __repr__(self) -> str:
        elements = " ,".join([repr(s) for s in self._elements])
        return f"SumExpressionFunction: {elements}"

    @property
    def elements(self):
        return self._elements

    def get_input_expressions(self) -> List[Expression]:
        return [el.expression for el in self._elements if el.expression]

    def add_element(self, element: ExpressionMultiplier) -> None:
        self._elements.append(element)

    def remove_element(self, index: int) -> ExpressionMultiplier:
        element = self._elements[index]
        del self._elements[index]
        return element


class PhaseExpressionFunction(ExpressionFunction):
    def __init__(self, source_expression: Expression, phase_number: int) -> None:
        super().__init__()
        self.function_type = ExpressionFunctionType.Phase
        self.source_expression: Optional[Expression] = source_expression
        self.phase_number = phase_number

    def __repr__(self) -> str:
        exp_name = self.source_expression.name if self.source_expression else ""
        return f"PhaseExpressionFunction: {exp_name}, {self.phase_number}"

    def get_input_expressions(self) -> List:
        return [self.source_expression]


class PSDDefinition(SectionItem):
    def __init__(
        self,
        name: str,
        layer: int,
        complex_expression: Expression,
        target_expression: Expression,
        corrective_expression: Expression,
    ) -> None:
        super().__init__()
        self.name = name
        self.layer = layer
        self.complex_expression: Optional[Expression] = complex_expression
        self.target_expression: Optional[Expression] = target_expression
        self.corrective_expression: Optional[Expression] = corrective_expression
        # Internals
        self._sub_sets: list[PSDDefinition] = []
        self._sup_sets: list[PSDDefinition] = []

    def __repr__(self) -> str:
        cmx_name = self.complex_expression.name if self.complex_expression else ""
        tgt_name = self.target_expression.name if self.target_expression else ""
        cor_name = self.corrective_expression.name if self.corrective_expression else ""
        return f"PSDDefinition: {self.name}, {self.layer}, {cmx_name}, {tgt_name}, {cor_name}"

    def key(self) -> str:
        return self.name

    def __eq__(self, value):
        if isinstance(value, PSDDefinition):
            return self.name == value.name
        return False

    def _is_sub_set(self, psd_def: PSDDefinition):
        assert psd_def.complex_expression and self.complex_expression is not None
        for cmp_exp_multi in psd_def.complex_expression.function.elements:
            has_it = False
            for self_cmp_exp_multi in self.complex_expression.function.elements:
                if cmp_exp_multi.expression.name == self_cmp_exp_multi.expression.name:
                    has_it = True
                    break
            if not has_it:
                return False
        return len(psd_def.complex_expression.function.elements) != len(self.complex_expression.function.elements)

    def _is_sup_set(self, psd_def: PSDDefinition):
        assert psd_def.complex_expression and self.complex_expression is not None
        for self_cmp_exp_multi in self.complex_expression.function.elements:
            has_it = False
            for cmp_exp_multi in psd_def.complex_expression.function.elements:
                if cmp_exp_multi.expression.name == self_cmp_exp_multi.expression.name:
                    has_it = True
                    break
            if not has_it:
                return False
        return len(psd_def.complex_expression.function.elements) != len(self.complex_expression.function.elements)

    def _connect_with(self, psd_def: PSDDefinition):
        if self._is_sub_set(psd_def):
            self._sub_sets.append(psd_def)
            psd_def._sup_sets.append(self)
        if self._is_sup_set(psd_def):
            self._sup_sets.append(psd_def)
            psd_def._sub_sets.append(self)

    def _disconnect_with(self, psd_def: PSDDefinition):
        if psd_def in self._sub_sets:
            self._sub_sets.remove(psd_def)
        if psd_def in self._sup_sets:
            self._sup_sets.remove(psd_def)

    def refresh_layer(self):
        self.layer = self._get_deep()

    def _get_deep(self):
        deepest = 0
        for psd_def in self._sub_sets:
            deep = psd_def._get_deep()
            if deep > deepest:
                deepest = deep
        return deepest + 1


class PSDNet(SectionItem):
    def __init__(
        self,
        name: str,
        inputs: List[ExpressionMultiplier] = [],
        output_expression: Optional[Expression] = None,
        psd_definition: Optional[PSDDefinition] = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.inputs = SectionList[ExpressionMultiplier](inputs)
        self.output_expression = output_expression
        self.psd_definition = psd_definition

    def __repr__(self) -> str:
        out_name = self.output_expression.name if self.output_expression else ""
        return f"PSDNet: {self.name}, {out_name}"

    def key(self) -> str:
        return self.name

    def add_input(self, value: ExpressionMultiplier) -> None:
        self.inputs.add(value)

    def remove_input(self, index: int) -> Optional[ExpressionMultiplier]:
        return self.inputs.remove(index)


class LOD(SectionItem):
    def __init__(
        self,
        level: int,
        psd_nets: List[PSDNet] = [],
        joints: List[Joint] = [],
        blend_shape_channels: List[str] = [],
        animated_map_channels: List[AnimatedMapChannel] = [],
        meshes: List[Mesh] = [],
    ) -> None:
        super().__init__()
        self.level = level
        self.psd_nets = SectionDict[PSDNet](psd_nets)
        self.joints = SectionDict[Joint](joints)
        self.blend_shape_channels = blend_shape_channels
        self.animated_map_channels = SectionDict[AnimatedMapChannel](animated_map_channels)
        self.meshes = SectionDict[Mesh](meshes)

    def __repr__(self) -> str:
        return f"LOD: {self.level}"

    def key(self) -> str:
        return str(self.level)

    def add_psd_net(self, psd_net: PSDNet) -> None:
        self.psd_nets.add(psd_net)

    def add_joint(self, joint: Joint) -> None:
        self.joints.add(joint)

    def set_blend_shape_channels(self, blend_shape_channels: List[str]):
        self.blend_shape_channels = blend_shape_channels

    def add_animated_map_channel(self, am_channel: AnimatedMapChannel) -> None:
        self.animated_map_channels.add(am_channel)

    def add_mesh(self, mesh: Mesh) -> None:
        self.meshes.add(mesh)

    def remove_psd_net(self, name: str) -> Optional[PSDNet]:
        return self.psd_nets.remove(name)

    def remove_joint(self, name: str) -> Optional[Joint]:
        return self.joints.remove(name)

    def remove_animated_map_channel(self, name: str) -> Optional[AnimatedMapChannel]:
        return self.animated_map_channels.remove(name)

    def remove_mesh(self, name: str) -> Optional[Mesh]:
        return self.meshes.remove(name)


class JointWeight(SectionItem):
    def __init__(self, joint: Joint, weight: float) -> None:
        self.joint = joint
        self.weight = weight

    def __repr__(self) -> str:
        return f"JointWeight: {self.joint.name}, {self.weight}"

    def key(self) -> str:
        return self.joint.name


class MixRegion(SectionItem):
    def __init__(
        self,
        name: str,
        joint_weights: List[JointWeight] = [],
        split_maps: List[SplitMap] = [],
    ) -> None:
        super().__init__()
        self.name = name
        self.joint_weights = SectionDict[JointWeight](joint_weights)
        self.split_maps = SectionDict[SplitMap](split_maps)

    def __repr__(self) -> str:
        return f"MixRegion: {self.name}"

    def key(self) -> str:
        return self.name

    def add_joint_weight(self, joint_weight: JointWeight) -> None:
        self.joint_weights.add(joint_weight)

    def add_split_map(self, split_map: SplitMap) -> None:
        self.split_maps.add(split_map)

    def remove_joint_weight(self, joint_name: str) -> Optional[JointWeight]:
        return self.joint_weights.remove(joint_name)

    def remove_split_map(self, name: str) -> Optional[SplitMap]:
        return self.split_maps.remove(name)


class SymmetrySide(IntEnum):
    Left = 1
    Right = 2
    Center = 3
    NoSymmetry = 4
    Unspecified = 65535


class SymmetryJoint(SectionItem):
    def __init__(
        self,
        joint: Joint,
        pair: Optional[Joint] = None,
        side: SymmetrySide = SymmetrySide.NoSymmetry,
    ) -> None:
        self.joint = joint
        self.pair = pair
        self.side = side

    def __repr__(self) -> str:
        pair_name = self.pair.name if self.pair else ""
        return f"SymmetryJoint: {self.joint.name}, {pair_name}, {self.side}"

    def key(self) -> str:
        return self.joint.name


class SymmetryMesh(SectionItem):
    def __init__(
        self,
        name: str,
        mesh: Mesh,
        vertex_mapping: List[int] = [],
        vertex_side: List[SymmetrySide] = [],
    ) -> None:
        super().__init__()
        self.name = name
        self.mesh: Optional[Mesh] = mesh
        self.vertex_mapping = vertex_mapping.copy()
        self.vertex_side = vertex_side.copy()

    def __repr__(self) -> str:
        return f"SymmetryMesh: {self.name}"

    def key(self) -> str:
        return self.name


# Rbf spec


class JointAttributeType(IntEnum):
    Translation = 0
    Rotation = 1
    Scale = 2
    Unspecified = 65535


class JointAttributeRepresentation(IntEnum):
    Vector = 0
    EulerAngles = 1
    Quaternion = 2
    Unpsecified = 65535


class RBFSolverType(IntEnum):
    Additive = 0
    Interpolative = 1
    Unspecified = 65535


class RBFFunctionType(IntEnum):
    Gaussian = 0
    Exponential = 1
    Linear = 2
    Cubic = 3
    Quintic = 4
    Unspecified = 65535


class RBFDistanceMethod(IntEnum):
    Euclidean = 0
    Quaternion = 1
    SwingAngle = 2
    TwistAngle = 3
    Unspecified = 65535


class RBFPose(SectionItem):
    def __init__(
        self, name: str, input_controls: List[Control] = [], output_expressions: List[Expression] = []
    ) -> None:
        super().__init__()
        self.name = name
        self.input_controls = SectionDict[Control](input_controls)
        self.output_expressions = SectionDict[Expression](output_expressions)

    def add_input_control(self, input_control: Control) -> None:
        self.input_controls.add(input_control)

    def add_output_expression(self, output_expression: Expression) -> None:
        self.output_expressions.add(output_expression)

    def remove_input_control(self, name: str) -> Optional[Control]:
        return self.input_controls.remove(name)

    def remove_output_expression(self, name: str) -> Optional[Expression]:
        return self.output_expressions.remove(name)

    def __repr__(self) -> str:
        return f"RBFPose: {self.name}"

    def key(self) -> str:
        return self.name


# Custom rbf input joint/ctrl
class RBFInputJoint(SectionItem):
    def __init__(
        self, joint: Joint, jnt_attr_type: JointAttributeType, jnt_attr_repr: JointAttributeRepresentation
    ) -> None:
        super().__init__()
        self.joint: Joint = joint
        self.jnt_attr_type: JointAttributeType = jnt_attr_type
        self.jnt_attr_repr: JointAttributeRepresentation = jnt_attr_repr

    def __repr__(self):
        return f"RBFInputJoint: {self.joint.name}, {self.jnt_attr_type.name} , {self.jnt_attr_repr.name}"

    def key(self) -> str:
        return self.joint.name


class RBFSolver(SectionItem):
    def __init__(
        self,
        name: str,
        solver_type: Optional[RBFSolverType] = None,
        distance_method: Optional[RBFDistanceMethod] = None,
        function_type: Optional[RBFFunctionType] = None,
        input_joints: List[RBFInputJoint] = [],
        poses: List[RBFPose] = [],
    ) -> None:
        super().__init__()
        self.name = name
        self.solver_type = solver_type
        self.distance_method = distance_method
        self.function_type = function_type
        self.input_joints = SectionDict[RBFInputJoint](input_joints)
        self.poses = SectionDict[RBFPose](poses)

    def add_rbf_input_joint(self, rbf_input_jnt: RBFInputJoint) -> None:
        self.input_joints.add(rbf_input_jnt)

    def add_pose(self, pose: RBFPose) -> None:
        self.poses.add(pose)

    def remove_rbf_input_joint(self, name: str) -> Optional[RBFInputJoint]:
        return self.input_joints.remove(name)

    def remove_pose(self, name: str) -> Optional[RBFPose]:
        return self.poses.remove(name)

    def __repr__(self) -> str:
        return f"RBFPose: {self.name}"

    def key(self) -> str:
        return self.name


class Twist(SectionItem):
    def __init__(self, inputs: List[Joint] = [], outputs: List[Joint] = []) -> None:
        super().__init__()
        self.inputs = SectionDict[Joint](inputs)
        self.outputs = SectionDict[Joint](outputs)

    def __repr__(self) -> str:
        inputs = " ".join([x.name for x in self.inputs])
        outputs = " ".join([x.name for x in self.outputs])
        return f"Twist: {inputs}, {outputs}"


class Swing(SectionItem):
    def __init__(self, inputs: List[Joint] = [], outputs: List[Joint] = []) -> None:
        super().__init__()
        self.inputs = SectionDict[Joint](inputs)
        self.outputs = SectionDict[Joint](outputs)

    def __repr__(self) -> str:
        inputs = " ".join([x.name for x in self.inputs])
        outputs = " ".join([x.name for x in self.outputs])
        return f"Swing: {inputs}, {outputs}"


# skin transfer
class SkinTransferMapping(SectionItem):
    def __init__(self, target_joint: Joint, source_joints: List[Joint] = []) -> None:
        super().__init__()
        self.target_joint = target_joint
        self.source_joints = SectionDict[Joint](source_joints)

    def key(self) -> str:
        return self.target_joint.name

    def __repr__(self) -> str:
        outputs = " ".join([j.name for j in self.source_joints])
        return f"Mapping: {self.target_joint.name} -> {outputs} "

    def remove_source_joint(self, name: str) -> Optional[Joint]:
        return self.source_joints.remove(name)

    def __eq__(self, value):
        if isinstance(value, SkinTransferMapping):
            return self.target_joint.name == value.target_joint.name
        return False


class SkinTransfer(SectionItem):
    def __init__(
        self, geo_mesh: Mesh, target_mesh: Mesh, source_mesh: Mesh, mapping: List[SkinTransferMapping] = []
    ) -> None:
        super().__init__()
        self.name = target_mesh.name
        self.geo_mesh = geo_mesh
        self.target_mesh = target_mesh
        self.source_mesh = source_mesh
        self.mapping = SectionDict[SkinTransferMapping](mapping)

    def add_mapping(self, mapping: SkinTransferMapping) -> None:
        self.mapping.add(mapping)

    def remove_mapping(self, key: str) -> Optional[SkinTransferMapping]:
        return self.mapping.remove(key)

    def __repr__(self) -> str:
        return f"SkinTransfer: {self.name}"

    def key(self) -> str:
        return self.name
