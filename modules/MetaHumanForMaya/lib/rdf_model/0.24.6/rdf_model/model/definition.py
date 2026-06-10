# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

from typing import Any, Dict, List, Optional, cast

from .items import (
    LOD,
    Mesh,
    Joint,
    Swing,
    Twist,
    PSDNet,
    Region,
    Shader,
    Control,
    RBFPose,
    SplitMap,
    MixRegion,
    RBFSolver,
    Descriptor,
    Expression,
    GUIControl,
    JointGroup,
    TextureMap,
    AnimatedMap,
    ControlType,
    ShaderInput,
    SplitJoints,
    TextureMask,
    SkinTransfer,
    SymmetryMesh,
    PSDDefinition,
    SymmetryJoint,
    ControlMapping,
    ExpressionType,
    TextureMapType,
    DeformationType,
    ShaderParameter,
    AnimatedMapChannel,
    ExpressionFunction,
    SumExpressionFunction,
    ExpressionFunctionType,
    PhaseExpressionFunction,
    SplitExpressionFunction,
    SubtractExpressionFunction,
)
from .common import SectionDict, SectionList


class RigDefinition:
    def __init__(self) -> None:
        self.descriptor: Optional[Descriptor] = None
        self.gui_controls = SectionDict[GUIControl]()
        self.controls = SectionDict[Control]()
        self.gui_to_raw = SectionList[ControlMapping]()
        self.joints = SectionDict[Joint]()
        self.animated_map_channels = SectionDict[AnimatedMapChannel]()
        self.joint_groups = SectionDict[JointGroup]()
        self.regions = SectionDict[Region]()
        self.texture_masks = SectionDict[TextureMask]()
        self.texture_map_types = SectionDict[TextureMapType]()
        self.texture_maps = SectionDict[TextureMap]()
        self.shaders = SectionDict[Shader]()
        self.meshes = SectionDict[Mesh]()
        self.split_maps = SectionDict[SplitMap]()
        self.expressions = SectionDict[Expression]()
        self.psd_definitions = SectionDict[PSDDefinition]()
        self.psd_nets = SectionDict[PSDNet]()
        self.lods = SectionDict[LOD]()
        self.mix_regions = SectionDict[MixRegion]()
        self.symmetry_joints = SectionDict[SymmetryJoint]()
        self.symmetry_meshes = SectionDict[SymmetryMesh]()
        self.rbf_solvers = SectionDict[RBFSolver]()
        self.rbf_poses = SectionDict[RBFPose]()
        self.twists = SectionList[Twist]()
        self.swings = SectionList[Swing]()
        self.skin_transfers = SectionDict[SkinTransfer]()

    def __repr__(self) -> str:
        _spec = "RigDefinition:"
        for k, v in self.get_regular_attrs().items():
            _spec += f"\n    {k.title()}: {v}"
        return _spec

    def get_regular_attrs(self) -> dict:
        attributes = {
            attr: value for attr, value in self.__dict__.items() if not callable(value) and not attr.startswith("_")
        }
        return attributes

    def get_item(self, item_class: type, item_key: str) -> Any:
        for item in self.get_all_items(item_class):
            if hasattr(item, "key") and item.key() == item_key:
                return item

    def get_all_items(self, item_class: type, section: Optional[str] = None) -> list:
        all_items = []
        accepted_sections = self.get_regular_attrs()

        if section is not None:
            accepted_sections = {section: accepted_sections[section]}

        for attr_value in accepted_sections.values():
            # Check if the attribute is a SectionDict or SectionList and matches the item_class
            if isinstance(attr_value, (SectionDict, SectionList)):
                # Filter items in the collection that match the given class
                items = [item for item in attr_value.values() if isinstance(item, item_class)]
                all_items.extend(items)
            elif isinstance(attr_value, item_class):
                all_items.append(attr_value)

        return all_items

    # ----------------------------------------------------------------------------------------------
    # Get_all methods
    def get_all_shader_parameters(self) -> List[ShaderParameter]:
        result = []
        for shader in self.shaders:
            result.extend(shader.parameters.values())
        return result

    def get_all_shader_inputs(self) -> List[ShaderInput]:
        result = []
        for shader in self.shaders:
            result.extend(shader.inputs.values())
        return result

    def get_all_animated_maps(self) -> List[AnimatedMap]:
        result = []
        for exp in self.expressions:
            result.extend(exp.animated_maps.values())
        return result

    def get_all_split_joints(self) -> List[SplitJoints]:
        result = []
        for exp in self.expressions:
            if exp.function and exp.function.function_type == ExpressionFunctionType.Split:
                fn = cast(SplitExpressionFunction, exp.function)
                result.extend(fn.split_joints.values())
        return result

    def get_all_expression_functions(
        self, func_type: Optional[ExpressionFunctionType] = None
    ) -> List[ExpressionFunction]:
        result: List[ExpressionFunction] = []
        if func_type is None:
            for exp in self.expressions:
                if exp.function:
                    result.append(exp.function)
        else:
            for exp in self.expressions:
                if exp.function and exp.function.function_type == func_type:
                    result.append(exp.function)
        return result

    # ----------------------------------------------------------------------------------------------
    # Get methods
    def get_controls_by_exported(self, is_exported: bool = True) -> List[Control]:
        controls = []
        for ctrl in self.controls:
            if ctrl.is_exported == is_exported:
                controls.append(ctrl)
        return controls

    def get_joint_hierarchy(self) -> List[int]:
        indices = []
        for joint in self.joints:
            if joint.parent is None:
                indices.append(joint.index)
            else:
                indices.append(joint.parent.index)
        return indices

    def get_split_function_joint_groups(self) -> List[JointGroup]:
        joint_groups: Dict[str, JointGroup] = {}
        for function in self.get_all_expression_functions(ExpressionFunctionType.Split):
            fn = cast(SplitExpressionFunction, function)
            for sj in fn.split_joints:
                group_name = sj.joint_group.name
                if group_name not in joint_groups:
                    joint_groups[group_name] = sj.joint_group
        return list(joint_groups.values())

    def get_blend_shape_channels_by_exported(self, lod) -> List[str]:
        bs_channels = []
        for exp in self.expressions:
            if exp.is_exported:
                for md in exp.mesh_deformers:
                    if (
                        md.deformation_type in (DeformationType.BlendShapesOnly, DeformationType.JointsAndBlendShapes)
                        and md.mesh in lod.meshes
                    ):
                        bs_channels.append(exp.name)
                        break

        return bs_channels

    def get_blend_shape_channels_by_meshes(self) -> Dict[str, List[str]]:
        bs_channels: Dict[str, List[str]] = {}
        for mesh in self.meshes:
            bs_channels[mesh.name] = []
        for exp in self.expressions:
            if exp.is_exported:
                for md in exp.mesh_deformers:
                    if md.deformation_type in (DeformationType.BlendShapesOnly, DeformationType.JointsAndBlendShapes):
                        bs_channels[md.mesh.name].append(exp.name)
        return bs_channels

    def sort_output_controls(self):
        final_order = []
        raw_ctrl = []
        psd_ctrl = []
        ml_ctrl = []
        rbf_ctrl = []
        for e in self.expressions:
            if e.control and e.control.control_type == ControlType.Raw:
                raw_ctrl.append(e.control.name)
            if e.control and e.control.control_type == ControlType.PSD:
                psd_ctrl.append(e.control.name)
            if e.control and e.control.control_type == ControlType.ML:
                ml_ctrl.append(e.control.name)
            if e.control and e.control.control_type == ControlType.RBF:
                rbf_ctrl.append(e.control.name)

        for c in self.controls:
            if not c.is_exported:
                continue
            if c.control_type == ControlType.Raw and c.name not in raw_ctrl:
                raw_ctrl.append(c.name)
            if c.control_type == ControlType.PSD and c.name not in psd_ctrl:
                psd_ctrl.append(c.name)
            if c.control_type == ControlType.ML and c.name not in ml_ctrl:
                ml_ctrl.append(c.name)
            if c.control_type == ControlType.RBF and c.name not in rbf_ctrl:
                rbf_ctrl.append(c.name)

        final_order.extend(raw_ctrl)
        final_order.extend(psd_ctrl)
        final_order.extend(ml_ctrl)
        final_order.extend(rbf_ctrl)
        for i, name in enumerate(final_order):
            ctrl = self.controls.get(name)
            assert ctrl is not None
            ctrl.index = i

        sorted_objs = sorted(self.controls._store.values(), key=lambda obj: obj.index)
        self.controls._store = {obj.key(): obj for obj in sorted_objs}

        self.controls.index()

    def get_animated_map_channels_by_texture_map(self, texture_map_name: str) -> List[AnimatedMapChannel]:
        am_channels = []
        for am_channel in self.animated_map_channels:
            if am_channel.texture_map_name == texture_map_name:
                am_channels.append(am_channel)
        return am_channels

    def get_animated_map_channels_by_texture_map_type(self, texture_map_type_name: str) -> List[AnimatedMapChannel]:
        am_channels = []
        for am_channel in self.animated_map_channels:
            texture_map = self.texture_maps.get(am_channel.texture_map_name)
            if texture_map and texture_map.map_type and texture_map.map_type.name == texture_map_type_name:
                am_channels.append(am_channel)
        return am_channels

    def get_texture_base_map(self, type_name: str) -> Optional[TextureMap]:
        for tm in self.texture_maps:
            if tm.map_type and tm.map_type.name == type_name and tm.is_base:
                return tm
        return None

    def get_texture_maps_by_type(self, type_name: str) -> List[TextureMap]:
        texture_maps = []
        for texture_map in self.texture_maps:
            if texture_map.map_type and texture_map.map_type.name == type_name:
                texture_maps.append(texture_map)
        return texture_maps

    def get_meshes_by_exported(self, is_exported: bool = True) -> List[Mesh]:
        meshes = []
        for mesh in self.meshes:
            if mesh.is_exported == is_exported:
                meshes.append(mesh)
        return meshes

    def get_split_maps_by_mesh(self, mesh_name: str) -> List[SplitMap]:
        sm = []
        for split_map in self.split_maps:
            if split_map.mesh and split_map.mesh.name == mesh_name:
                sm.append(split_map)
        return sm

    def get_expressions_by_exported(self, is_exported: bool = True) -> List[Expression]:
        exps = []
        for expression in self.expressions:
            if expression.is_exported == is_exported:
                exps.append(expression)
        return exps

    def get_psd_definition_by_expression(self, expression_name: str) -> Optional[PSDDefinition]:
        for psd_def in self.psd_definitions:
            if psd_def.complex_expression and psd_def.complex_expression.name == expression_name:
                return psd_def
            if psd_def.target_expression and psd_def.target_expression.name == expression_name:
                return psd_def
            if psd_def.corrective_expression and psd_def.corrective_expression.name == expression_name:
                return psd_def
        return None

    def get_psd_net_by_output(self, out_expression_name: str) -> Optional[PSDNet]:
        for psd_net in self.psd_nets:
            if psd_net.output_expression and psd_net.output_expression.name == out_expression_name:
                return psd_net
        return None

    def get_lod_count(self) -> int:
        return len(self.lods)

    # ----------------------------------------------------------------------------------------------
    # Add methods
    def add_gui_control(self, control: GUIControl) -> None:
        self.gui_controls.add(control)
        self.gui_controls.index()

    def add_control(self, control: Control) -> None:
        self.controls.add(control)
        self.controls.index()

    def add_gui_to_raw(self, mapping: ControlMapping) -> None:
        self.gui_to_raw.add(mapping)
        self.gui_to_raw.index()

    def add_joint(self, joint: Joint) -> None:
        self.joints.add(joint)
        self.joints.index()

    def add_animated_map_channel(self, am_channel: AnimatedMapChannel) -> None:
        self.animated_map_channels.add(am_channel)
        self.animated_map_channels.index()

    def add_joint_group(self, joint_group: JointGroup) -> None:
        self.joint_groups.add(joint_group)
        self.joint_groups.index()

    def add_region(self, region: Region) -> None:
        self.regions.add(region)
        self.regions.index()

    def add_texture_mask(self, texture_mask: TextureMask) -> None:
        self.texture_masks.add(texture_mask)
        self.texture_masks.index()

    def add_texture_map_type(self, texture_map_type: TextureMapType) -> None:
        self.texture_map_types.add(texture_map_type)
        self.texture_map_types.index()

    def add_texture_map(self, texture_map: TextureMap) -> None:
        self.texture_maps.add(texture_map)
        self.texture_maps.index()

    def add_shader(self, shader: Shader) -> None:
        self.shaders.add(shader)
        self.index_shaders()

    def add_mesh(self, mesh: Mesh) -> None:
        self.meshes.add(mesh)
        self.meshes.index()

    def add_split_map(self, split_map: SplitMap) -> None:
        self.split_maps.add(split_map)
        self.split_maps.index()

    def add_expression(self, expression: Expression) -> None:
        self.expressions.add(expression)
        self.index_expressions()

    def add_expressions(self, expressions: list[Expression]) -> None:
        for expression in expressions:
            self.expressions.add(expression)
        self.index_expressions()

    def add_psd_definition(self, psd_definition: PSDDefinition) -> None:
        for psd in self.psd_definitions:
            psd._connect_with(psd_definition)

        self.psd_definitions.add(psd_definition)

        for psd in self.psd_definitions:
            psd.refresh_layer()

        self.psd_definitions._store = dict(sorted(self.psd_definitions._store.items(), key=lambda x: x[1].layer))
        self.psd_definitions.index()

    def psd_definition_changed(self, psd_definition: PSDDefinition) -> None:
        for psd in self.psd_definitions:
            psd._disconnect_with(psd_definition)

        psd_definition._sub_sets = []
        psd_definition._sup_sets = []

        for psd in self.psd_definitions:
            psd._connect_with(psd_definition)

        for psd in self.psd_definitions:
            psd.refresh_layer()

        self.psd_definitions._store = dict(sorted(self.psd_definitions._store.items(), key=lambda x: x[1].layer))
        self.psd_definitions.index()

    def add_psd_net(self, psd_net: PSDNet) -> None:
        self.psd_nets.add(psd_net)
        self.psd_nets.index()

    def add_lod(self, lod: LOD) -> None:
        self.lods.add(lod)
        self.lods.index()

    def add_mix_region(self, mix_region: MixRegion) -> None:
        self.mix_regions.add(mix_region)
        self.mix_regions.index()

    def add_symmetry_joint(self, symmetry_joint: SymmetryJoint) -> None:
        self.symmetry_joints.add(symmetry_joint)
        self.symmetry_joints.index()

    def add_symmetry_mesh(self, symmetry_mesh: SymmetryMesh) -> None:
        self.symmetry_meshes.add(symmetry_mesh)
        self.symmetry_meshes.index()

    def add_rbf_solver(self, rbf_solver: RBFSolver) -> None:
        self.rbf_solvers.add(rbf_solver)
        self.rbf_solvers.index()

    def add_rbf_pose(self, rbf_pose: RBFPose) -> None:
        self.rbf_poses.add(rbf_pose)
        self.rbf_poses.index()

    def add_twist(self, twist: Twist) -> None:
        self.twists.add(twist)
        self.twists.index()

    def add_swing(self, swing: Swing) -> None:
        self.swings.add(swing)
        self.swings.index()

    def add_skin_transfer(self, skin_transfer: SkinTransfer) -> None:
        self.skin_transfers.add(skin_transfer)
        self.skin_transfers.index()

    # ----------------------------------------------------------------------------------------------
    # Remove methods
    def remove_gui_control(self, name: str, force: bool = False) -> Optional[Control]:
        # Remove from control mapping
        self.remove_gui_to_raw(name, force)
        # Remove gui control
        removed = self.gui_controls.remove(name)
        self.gui_controls.index()
        return removed

    def remove_control(self, name: str, force: bool = False) -> Optional[Control]:
        # Remove from control mappoing
        if self.gui_controls.has(name):
            self.remove_gui_to_raw(name, force)
        # Remove from expressions
        for exp in self.expressions:
            if exp.control and exp.control.name == name:
                exp.control = None
        # Remove control
        removed = self.controls.remove(name)
        self.controls.index()
        return removed

    def remove_gui_to_raw(self, ctrl_name: str, force: bool = False) -> None:
        remove_indices = []
        for i, mapping in enumerate(self.gui_to_raw):
            if mapping.in_control and mapping.in_control.name == ctrl_name:
                mapping.in_control = None
                remove_indices.append(i)
            if mapping.out_control and mapping.out_control.name == ctrl_name:
                mapping.out_control = None
                remove_indices.append(i)
        if force:
            remove_indices.sort(reverse=True)
            for index in remove_indices:
                self.gui_to_raw.remove(index)

    def remove_joint(self, name: str, force: bool = False) -> Optional[Joint]:
        # Create a list to hold the joints to be removed
        joints_to_remove = []
        # Collect joints to be removed
        for jnt in self.joints.values():
            if jnt.parent and jnt.parent.name == name:
                joints_to_remove.append(jnt.name)
        # Remove collected joints
        for jnt_name in joints_to_remove:
            self.remove_joint(jnt_name, force)
        # Collect joint groups to remove the joint from
        joint_groups_to_update = list(self.joint_groups.values())
        for jnt_grp in joint_groups_to_update:
            jnt_grp.remove_joint(name)
        # Collect LODs to remove the joint from
        lods_to_update = list(self.lods.values())
        for lod in lods_to_update:
            lod.remove_joint(name)
        # Collect mix regions to remove the joint from
        mix_regions_to_update = list(self.mix_regions.values())
        for mix_reg in mix_regions_to_update:
            mix_reg.remove_joint_weight(name)
        # regions
        regions_to_update = list(self.regions.values())
        for region in regions_to_update:
            region.remove_joint(name)
        # remove skin transfer joint mapping
        skin_transfer_to_update = list(self.skin_transfers.values())
        mapping_jnt = self.joints.get(name)
        assert mapping_jnt is not None
        for skin_transfer in skin_transfer_to_update:
            for st_mapping in skin_transfer.mapping:
                st_mapping.remove_source_joint(mapping_jnt.name)
            skin_transfer.remove_mapping(mapping_jnt.name)
        # Remove symmetry joint
        self.remove_symmetry_joint(name)
        # Finally, remove the joint itself
        removed = self.joints.remove(name)
        self.joints.index()
        return removed

    def remove_animated_map_channel(self, name: str, force: bool = False) -> Optional[AnimatedMapChannel]:
        # Animated map
        for exp in self.expressions:
            for am in exp.animated_maps:
                am.remove_animated_map_channel(name)
        # Remove from lods
        for lod in self.lods:
            lod.remove_animated_map_channel(name)
        # Remove animated map channel
        removed = self.animated_map_channels.remove(name)
        self.animated_map_channels.index()
        return removed

    def remove_joint_group(self, name: str, force: bool = False) -> Optional[JointGroup]:
        # Remove from split joints
        for exp in self.expressions:
            if exp.function and exp.function.function_type == ExpressionFunctionType.Split:
                fn = cast(SplitExpressionFunction, exp.function)
                remove_indices: List[int] = []
                for i, sj in enumerate(fn.split_joints):
                    if sj.joint_group and sj.joint_group.name == name:
                        sj.joint_group = None
                        remove_indices.append(i)
                if force:
                    remove_indices.sort(reverse=True)
                    for index in remove_indices:
                        fn.split_joints.remove(index)

        # Remove joint group
        removed = self.joint_groups.remove(name)
        self.joint_groups.index()
        return removed

    def remove_region(self, name: str, force: bool = False) -> Optional[Region]:
        for exp in self.expressions:
            if exp.expression_type == ExpressionType.Main and force:
                exp.regions.remove(name)

        removed = self.regions.remove(name)
        self.regions.index()
        return removed

    def remove_texture_mask(self, name: str, force: bool = False) -> Optional[TextureMask]:
        # Remove from animated maps
        for exp in self.expressions:
            for am in exp.animated_maps:
                am.remove_texture_mask(name)
        # Remove texture mask
        removed = self.texture_masks.remove(name)
        self.texture_masks.index()
        return removed

    def remove_texture_map_type(self, name: str, force: bool = False) -> Optional[TextureMapType]:
        # Remove from texture maps
        remove_keys = []
        for tm in self.texture_maps:
            if tm.map_type and tm.map_type.name == name:
                tm.map_type = None
                remove_keys.append(tm.key())
        if force:
            for key in remove_keys:
                self.remove_texture_map(key, force)
        # Remove from shader inputs
        for shader in self.shaders:
            remove_keys = []
            for shader_input in shader.inputs:
                if shader_input.map_type and shader_input.map_type.name == name:
                    shader_input.map_type = None
                    remove_keys.append(shader_input.key())
            if force:
                for key in remove_keys:
                    shader.inputs.remove(key)
        # Remove texture map type
        removed = self.texture_map_types.remove(name)
        self.texture_map_types.index()
        return removed

    def remove_texture_map(self, name: str, force: bool = False) -> Optional[TextureMap]:
        # Remove from animated maps
        for exp in self.expressions:
            remove_indices = []
            for i, am in enumerate(exp.animated_maps):
                if am.texture_map and am.texture_map.name == name:
                    am.texture_map = None
                    remove_indices.append(i)
            if force:
                remove_indices.sort(reverse=True)
                for index in remove_indices:
                    exp.animated_maps.remove(index)
        # Remove texture map
        removed = self.texture_maps.remove(name)
        self.texture_maps.index()
        return removed

    def remove_shader(self, name: str, force: bool = False) -> Optional[Shader]:
        # Remove from meshes
        for mesh in self.meshes:
            if mesh.shader and mesh.shader.name == name:
                mesh.shader = None
        # Remove shader
        removed = self.shaders.remove(name)
        self.shaders.index()
        return removed

    def remove_mesh(self, name: str, force: bool = False) -> Optional[Mesh]:
        # Remove from split maps
        remove_keys = []
        for sm in self.split_maps:
            if sm.mesh and sm.mesh.name == name:
                sm.mesh = None
                remove_keys.append(sm.key())
        if force:
            for key in remove_keys:
                self.remove_split_map(key, force)
        # Remove from mesh deformers
        for exp in self.expressions:
            remove_indices = []
            for i, md in enumerate(exp.mesh_deformers):
                if md.mesh and md.mesh.name == name:
                    md.mesh = None
                    remove_indices.append(i)
            if force:
                remove_indices.sort(reverse=True)
                for index in remove_indices:
                    exp.mesh_deformers.remove(index)
        # Remove from lods
        for lod in self.lods:
            lod.remove_mesh(name)
        # Remove from symmetry meshes
        remove_keys = []
        for sym_mesh in self.symmetry_meshes:
            if sym_mesh.mesh and sym_mesh.mesh.name == name:
                sym_mesh.mesh = None
                remove_keys.append(sym_mesh.key())
        if force:
            for key in remove_keys:
                self.remove_symmetry_mesh(key, force)
        # Remove mesh
        removed = self.meshes.remove(name)
        self.meshes.index()
        return removed

    def remove_split_map(self, name: str, force: bool = False) -> Optional[SplitMap]:
        # Remove from split expression function
        for exp in self.expressions:
            if exp.function and exp.function.function_type == ExpressionFunctionType.Split:
                fn = cast(SplitExpressionFunction, exp.function)
                fn.split_maps.remove(name)
        # Remove from mix regions
        for mix_reg in self.mix_regions:
            mix_reg.remove_split_map(name)
        # Remove split map
        removed = self.split_maps.remove(name)
        self.split_maps.index()
        return removed

    def remove_expression(self, name: str, force: bool = False) -> Optional[Expression]:
        # Remove from raw controls
        for ctrl in self.controls:
            if ctrl.expression and ctrl.expression.name == name:
                ctrl.expression = None

        # Remove from expression functions
        for exp in self.expressions:
            if exp.function is None:
                continue
            if exp.function.function_type == ExpressionFunctionType.Split:
                split_fn = cast(SplitExpressionFunction, exp.function)
                remove_funct = False
                if split_fn.source_expression and split_fn.source_expression.name == name:
                    split_fn.source_expression = None
                    remove_funct = True
                if force and remove_funct:
                    exp.function = None  # type: ignore
            if exp.function and exp.function.function_type == ExpressionFunctionType.Subtract:
                sub_fn = cast(SubtractExpressionFunction, exp.function)
                remove_funct = False
                if sub_fn.minuend and sub_fn.minuend.expression and sub_fn.minuend.expression.name == name:
                    sub_fn.minuend.expression = None
                    remove_funct = True
                if sub_fn.subtrahend and sub_fn.subtrahend.expression and sub_fn.subtrahend.expression.name == name:
                    sub_fn.subtrahend.expression = None
                    remove_funct = True
                if force and remove_funct:
                    exp.function = None  # type: ignore
            if exp.function and exp.function.function_type == ExpressionFunctionType.Sum:
                sum_fn = cast(SumExpressionFunction, exp.function)
                remove_indices = []
                for i, el in enumerate(sum_fn.elements):
                    if el.expression and el.expression.name == name:
                        el.expression = None
                        remove_indices.append(i)
                if force:
                    remove_indices.sort(reverse=True)
                    for index in remove_indices:
                        del sum_fn.elements[index]
            if exp.function and exp.function.function_type == ExpressionFunctionType.Phase:
                phase_fn = cast(PhaseExpressionFunction, exp.function)
                remove_funct = False
                if phase_fn.source_expression and phase_fn.source_expression.name == name:
                    phase_fn.source_expression = None
                    remove_funct = True
                if force and remove_funct:
                    exp.function = None  # type: ignore

        # Remove from psd definitions
        remove_keys = []
        for psd_def in self.psd_definitions:
            cmx_exp = psd_def.complex_expression
            tgt_exp = psd_def.target_expression
            cor_exp = psd_def.corrective_expression
            if cmx_exp and cmx_exp.name == name:
                psd_def.complex_expression = None
                remove_keys.append(psd_def.key())
            if tgt_exp and tgt_exp.name == name:
                psd_def.target_expression = None
                remove_keys.append(psd_def.key())
            if cor_exp and cor_exp.name == name:
                psd_def.corrective_expression = None
                remove_keys.append(psd_def.key())
        if force:
            for key in remove_keys:
                self.remove_psd_definition(key)

        # Remove from psd nets
        remove_keys = []
        for psd_net in self.psd_nets:
            remove_indices = []
            for i, exp_mult in enumerate(psd_net.inputs):
                if exp_mult.expression and exp_mult.expression.name == name:
                    exp_mult.expression = None
                    remove_indices.append(i)
            if force:
                remove_indices.sort(reverse=True)
                for index in remove_indices:
                    psd_net.inputs.remove(index)
            if psd_net.output_expression and psd_net.output_expression.name == name:
                psd_net.output_expression = None
                remove_keys.append(psd_net.key())
        if force:
            for key in remove_keys:
                self.remove_psd_net(key)

        # Remove expression
        removed = self.expressions.remove(name)
        self.index_expressions()
        return removed

    def remove_psd_definition(self, name: str, force: bool = False) -> Optional[PSDDefinition]:
        # Remove from psd nets
        remove_keys = []
        for psd_net in self.psd_nets:
            if psd_net.psd_definition and psd_net.psd_definition.name == name:
                psd_net.psd_definition = None
                remove_keys.append(psd_net.key())
        if force:
            for key in remove_keys:
                self.remove_psd_net(key)

        psd_for_remove = self.psd_definitions.get(name)
        assert psd_for_remove is not None
        for psd in self.psd_definitions:
            psd._disconnect_with(psd_for_remove)

        # Remove psd definition
        removed = self.psd_definitions.remove(name)

        for psd in self.psd_definitions:
            psd.refresh_layer()

        self.psd_definitions.index()
        return removed

    def remove_psd_net(self, name: str, force: bool = False) -> Optional[PSDNet]:
        # Remove from lods
        for lod in self.lods:
            lod.remove_psd_net(name)
        # Remove psd net
        removed = self.psd_nets.remove(name)
        self.psd_nets.index()
        return removed

    def remove_lod(self, level: int, force: bool = False) -> Optional[LOD]:
        # TODO: should we update lod levels?
        removed = self.lods.remove(str(level))
        self.lods.index()
        return removed

    def remove_mix_region(self, name: str, force: bool = False) -> Optional[MixRegion]:
        removed = self.mix_regions.remove(name)
        self.mix_regions.index()
        return removed

    def remove_symmetry_joint(self, joint_name: str, force: bool = False) -> Optional[SymmetryJoint]:
        removed = self.symmetry_joints.remove(joint_name)
        self.symmetry_joints.index()
        return removed

    def remove_symmetry_mesh(self, mesh_name: str, force: bool = False) -> Optional[SymmetryMesh]:
        removed = self.symmetry_meshes.remove(mesh_name)
        self.symmetry_meshes.index()
        return removed

    def remove_rbf_solver(self, rbf_solver_name: str, force: bool = False) -> Optional[RBFSolver]:
        removed = self.rbf_solvers.remove(rbf_solver_name)
        self.rbf_solvers.index()
        return removed

    def remove_rbf_pose(self, rbf_pose_name: str, force: bool = False) -> Optional[RBFPose]:
        removed = self.rbf_poses.remove(rbf_pose_name)
        self.rbf_poses.index()
        return removed

    def remove_twist(self, twist_index: int, force: bool = False) -> Optional[Twist]:
        removed = self.twists.remove(twist_index)
        self.twists.index()
        return removed

    def remove_swing(self, swing_index: int, force: bool = False) -> Optional[Swing]:
        removed = self.swings.remove(swing_index)
        self.swings.index()
        return removed

    def remove_skin_transfer(self, skin_transfer_name: str, force: bool = False) -> Optional[SkinTransfer]:
        removed = self.skin_transfers.remove(skin_transfer_name)
        self.skin_transfers.index()
        return removed

    # ----------------------------------------------------------------------------------------------
    # index methods
    def index_shaders(self):
        self.shaders.index()
        shd_param_i = 0
        shd_input_i = 0
        for shader in self.shaders:
            for parameter in shader.parameters:
                parameter.index = shd_param_i
                shd_param_i += 1
            for shader_input in shader.inputs:
                shader_input.index = shd_input_i
                shd_input_i += 1

    def index_expressions(self):
        self.expressions.index()

        # Sort mesh deformers by mesh index
        for exp in self.expressions:
            exp.mesh_deformers._store.sort(key=lambda md: md.mesh.index if md.mesh else "")

        anim_map_i = 0
        func_split_i = 0
        func_subtract_i = 0
        func_sum_i = 0
        func_phase_i = 0
        split_joints_i = 0
        for exp in self.expressions:
            for anim_map in exp.animated_maps:
                anim_map.index = anim_map_i
                anim_map_i += 1
            if exp.function is not None:
                if exp.function.function_type == ExpressionFunctionType.Split:
                    exp.function.index = func_split_i
                    func_split_i += 1
                    split_fn = cast(SplitExpressionFunction, exp.function)
                    for sj in split_fn.split_joints:
                        sj.index = split_joints_i
                        split_joints_i += 1
                if exp.function.function_type == ExpressionFunctionType.Subtract:
                    exp.function.index = func_subtract_i
                    func_subtract_i += 1
                if exp.function.function_type == ExpressionFunctionType.Sum:
                    exp.function.index = func_sum_i
                    func_sum_i += 1
                if exp.function.function_type == ExpressionFunctionType.Phase:
                    exp.function.index = func_phase_i
                    func_phase_i += 1

    def index(self):
        self.gui_controls.index()
        self.controls.index()
        self.gui_to_raw.index()
        self.joints.index()
        self.animated_map_channels.index()
        self.joint_groups.index()
        self.texture_masks.index()
        self.texture_map_types.index()
        self.texture_maps.index()
        self.index_shaders()
        self.meshes.index()
        self.split_maps.index()
        self.index_expressions()
        self.sort_output_controls()
        self.psd_definitions.index()
        self.psd_nets.index()
        self.lods.index()
        self.mix_regions.index()
        self.symmetry_joints.index()
        self.symmetry_meshes.index()
        self.regions.index()
        self.rbf_solvers.index()
        self.rbf_poses.index()
        self.twists.index()
        self.swings.index()
        self.skin_transfers.index()
