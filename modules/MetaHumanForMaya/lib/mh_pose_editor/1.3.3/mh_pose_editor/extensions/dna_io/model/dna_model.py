# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from enum import Enum, IntEnum
from typing import Dict, List, Optional
from dataclasses import field, dataclass

# External
from dna import (
    Gender_male,
    TwistAxis_X,
    TwistAxis_Y,
    TwistAxis_Z,
    Direction_up,
    Gender_other,
    Gender_female,
    Direction_back,
    Direction_down,
    Direction_left,
    Direction_front,
    Direction_right,
    CoordinateSystem,
    TranslationUnit_m,
    AutomaticRadius_On,
    TranslationUnit_cm,
    AutomaticRadius_Off,
    RotationUnit_degrees,
    RotationUnit_radians,
    RBFFunctionType_Cubic,
    RBFFunctionType_Linear,
    RBFSolverType_Additive,
    RBFFunctionType_Quintic,
    RBFFunctionType_Gaussian,
    ScaleRepresentation_Vector,
    RBFDistanceMethod_Euclidean,
    RBFFunctionType_Exponential,
    RBFSolverType_Interpolative,
    RBFDistanceMethod_Quaternion,
    RBFDistanceMethod_SwingAngle,
    RBFDistanceMethod_TwistAngle,
    TranslationRepresentation_Vector,
    RotationRepresentation_Quaternion,
    RBFNormalizeMethod_AlwaysNormalize,
    RotationRepresentation_EulerAngles,
    RBFNormalizeMethod_OnlyNormalizeAboveOne,
)


class TranslationUnit(Enum):
    cm = TranslationUnit_cm
    m = TranslationUnit_m


class RotationUnit(IntEnum):
    degrees = RotationUnit_degrees
    radians = RotationUnit_radians


class Direction(Enum):
    left = Direction_left
    right = Direction_right
    up = Direction_up
    down = Direction_down
    front = Direction_front
    back = Direction_back


class Gender(Enum):
    male = Gender_male
    female = Gender_female
    other = Gender_other


class JointRepresent(Enum):
    translation = TranslationRepresentation_Vector
    rotation_quaternion = RotationRepresentation_Quaternion
    rotation_euler = RotationRepresentation_EulerAngles
    scale = ScaleRepresentation_Vector


class AutomaticRadius(Enum):
    on = AutomaticRadius_On
    off = AutomaticRadius_Off


class TwistAxis(Enum):
    x = TwistAxis_X
    y = TwistAxis_Y
    z = TwistAxis_Z


class RBFFunctionType(Enum):
    gaussian = RBFFunctionType_Gaussian
    exponential = RBFFunctionType_Exponential
    linear = RBFFunctionType_Linear
    cubic = RBFFunctionType_Cubic
    quintic = RBFFunctionType_Quintic


class RBFDistanceMethod(Enum):
    euclidean = RBFDistanceMethod_Euclidean
    quaternion = RBFDistanceMethod_Quaternion
    swing_angle = RBFDistanceMethod_SwingAngle
    twist_angle = RBFDistanceMethod_TwistAngle


class RBFNormalizeMethod(Enum):
    normalize_above_one = RBFNormalizeMethod_OnlyNormalizeAboveOne
    normalize = RBFNormalizeMethod_AlwaysNormalize


class RBFSolverType(Enum):
    interpolative = RBFSolverType_Interpolative
    additive = RBFSolverType_Additive


@dataclass
class Version:
    generation: int = 2
    version: int = 5


class CoorSystem:
    def __init__(self, coordinate_system: CoordinateSystem) -> None:
        self.coor_sys = coordinate_system

    # TODO check if values are OK

    @classmethod
    def create_maya_yup_coordinate_system(cls):
        return cls.from_axes(Direction.left, Direction.up, Direction.front)

    @classmethod
    def create_maya_zup_coordinate_system(cls):
        return cls.from_axes(Direction.left, Direction.back, Direction.up)

    @classmethod
    def create_ue5_coordinate_system(cls):
        return cls.from_axes(Direction.front, Direction.right, Direction.up)

    @classmethod
    def from_axes(cls, x_axis: Direction, y_axis: Direction, z_axis: Direction):
        coor = CoordinateSystem()
        coor.xAxis = x_axis.value
        coor.yAxis = y_axis.value
        coor.zAxis = z_axis.value
        return cls(coordinate_system=coor)

    def __repr__(self) -> str:
        return f"CoordinateSystem: {self.coor_sys.xAxis}, {self.coor_sys.yAxis}, {self.coor_sys.zAxis}"


@dataclass
class Descriptor:
    name: str = ""
    archetype: int = 0
    gender: Gender = Gender.other
    age: int = 0
    metadata: List[List[str]] = field(default_factory=list)
    translation_unit: TranslationUnit = TranslationUnit.cm
    rotation_unit: RotationUnit = RotationUnit.degrees
    coordinate_system: CoorSystem = CoorSystem.create_maya_yup_coordinate_system()
    lod_count: int = 0
    max_lod: int = 0
    complexity: str = "A1"
    db_name: str = "MHB.X"


@dataclass
class Mapping:
    lods: List[int] = field(default_factory=list)
    indices: List[List[int]] = field(default_factory=list)


@dataclass
class Definition:
    lod_joint_mapping: Mapping = field(default_factory=Mapping)
    lod_mesh_mapping: Mapping = field(default_factory=Mapping)
    lod_blend_shape_mapping: Mapping = field(default_factory=Mapping)
    lod_animated_maps_mapping: Mapping = field(default_factory=Mapping)
    gui_control_names: List[str] = field(default_factory=list)
    raw_control_names: List[str] = field(default_factory=list)
    joint_names: List[str] = field(default_factory=list)
    mesh_names: List[str] = field(default_factory=list)
    joint_hierarchy: List[int] = field(default_factory=list)
    neutral_joint_translations: Dict[str, List[float]] = field(default_factory=dict)
    neutral_joint_rotations: Dict[str, List[float]] = field(default_factory=dict)
    blend_shape_channel_names: List[str] = field(default_factory=list)
    animated_map_names: List[str] = field(default_factory=list)
    mesh_blend_shape_channel_mapping: Dict[str, List[int]] = field(default_factory=lambda: {"from": [], "to": []})


@dataclass
class JointGroup:
    lods: List[int] = field(default_factory=list)
    input_indices: List[int] = field(default_factory=list)
    output_indices: List[int] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    joint_indices: List[int] = field(default_factory=list)


@dataclass
class Conditionals:
    input_indices: List[int] = field(default_factory=list)
    output_indices: List[int] = field(default_factory=list)
    from_values: List[float] = field(default_factory=list)
    to_values: List[float] = field(default_factory=list)
    slope_values: List[float] = field(default_factory=list)
    cut_values: List[float] = field(default_factory=list)


@dataclass
class Controls:
    psd_count: int = 0
    conditionals: Conditionals = field(default_factory=Conditionals)
    psds: Dict[str, List[int]] = field(default_factory=lambda: {"rows": [], "columns": [], "values": []})


@dataclass
class BlendShapeChannels:
    lods: List[int] = field(default_factory=list)
    input_indices: List[int] = field(default_factory=list)
    output_indices: List[int] = field(default_factory=list)


@dataclass
class AnimatedMaps:
    lods: List[int] = field(default_factory=list)
    conditionals: Conditionals = field(default_factory=Conditionals)


@dataclass
class Behavior:
    row_count: int = 0
    col_count: int = 0
    joint_groups: List[JointGroup] = field(default_factory=list)
    controls: Controls = field(default_factory=Controls)
    blend_shape_channels: BlendShapeChannels = field(default_factory=BlendShapeChannels)
    animated_maps: AnimatedMaps = field(default_factory=AnimatedMaps)


@dataclass
class Solver:
    name: str = ""
    raw_control_indices: List[int] = field(default_factory=list)
    pose_indices: List[int] = field(default_factory=list)
    raw_control_values: List[float] = field(default_factory=list)
    radius: float = 0.0
    weight_threshold: float = 0.0
    solver_type: RBFSolverType = RBFSolverType.additive
    automatic_radius: AutomaticRadius = AutomaticRadius.on
    distance_method: RBFDistanceMethod = RBFDistanceMethod.swing_angle
    normalize_method: RBFNormalizeMethod = RBFNormalizeMethod.normalize
    function_type: RBFFunctionType = RBFFunctionType.gaussian
    twist_axis: TwistAxis = TwistAxis.x


@dataclass
class Pose:
    name: str = ""
    scale: float = 1.0


@dataclass
class RBFBehavior:
    lod_solver_mapping: Mapping = field(default_factory=Mapping)
    solvers: List[Solver] = field(default_factory=list)
    poses: List[Pose] = field(default_factory=list)


@dataclass
class RBFPose:
    input_control_indices: List[int] = field(default_factory=list)
    output_control_indices: List[int] = field(default_factory=list)
    output_control_weights: List[float] = field(default_factory=list)


@dataclass
class RBFExtension:
    pose_control_names: List[str] = field(default_factory=list)
    poses: List[RBFPose] = field(default_factory=list)


@dataclass
class JointRepresentation:
    translation: JointRepresent = JointRepresent.translation
    rotation: JointRepresent = JointRepresent.rotation_quaternion
    scale: JointRepresent = JointRepresent.scale


@dataclass
class Setup:
    input_indices: List[int] = field(default_factory=list)
    output_indices: List[int] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    axis: int = 0


@dataclass
class TwistSwing:
    twist: List[Setup] = field(default_factory=list)
    swing: List[Setup] = field(default_factory=list)


@dataclass
class JointMetadata:
    joint_representations: List[JointRepresentation] = field(default_factory=list)


@dataclass
class BlendShapeTarget:
    index: int = 0
    channel_index: int = 0
    vertex_indices: List[int] = field(default_factory=list)
    deltas: List[List[float]] = field(default_factory=list)


@dataclass
class SkinWeight:
    values: List[float] = field(default_factory=list)
    joint_indices: List[int] = field(default_factory=list)


@dataclass
class MeshGeometry:
    # Positions in form: [[x0, y0, z0], [x1, y1, z1], ...]
    positions: List[List[float]] = field(default_factory=list)
    # Texture coordinates in form: [[u0, v0], [u1, v1], ...]
    texture_coordinates: List[List[float]] = field(default_factory=list)
    # Normals in form: [[x0, y0, z0], [x1, y1, z1], ...]
    normals: List[List[float]] = field(default_factory=list)
    # Layouts contains indices in form: [[pos0, texc0, nor0], [pos1, texc1, nor1], ...]
    layouts: List[List[int]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    maximum_influence_per_vertex: int = 0
    skin_weights: List[SkinWeight] = field(default_factory=list)
    blend_shape_targets: List[BlendShapeTarget] = field(default_factory=list)


@dataclass
class Geometry:
    meshes: List[MeshGeometry] = field(default_factory=list)


@dataclass
class MHDNAModel:
    version: Version = field(default_factory=Version)
    descriptor: Descriptor = field(default_factory=Descriptor)
    definition: Definition = field(default_factory=Definition)
    behavior: Behavior = field(default_factory=Behavior)
    rbf_behavior: Optional[RBFBehavior] = None
    rbf_extension: Optional[RBFExtension] = None
    joint_metadata: Optional[JointMetadata] = None
    twist_swing: Optional[TwistSwing] = None
    geometry: Optional[Geometry] = None
