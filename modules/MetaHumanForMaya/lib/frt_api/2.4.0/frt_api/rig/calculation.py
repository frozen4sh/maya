# Copyright Epic Games, Inc. All Rights Reserved.
from typing import Dict

import dnacalib2 as dnacalib

from ..core import status_validator_dnacalib
from ..publisher import ProgressUpdate, progress_guard
from ..model.rig_definition.expression import Expression


class PhasesError(Exception):
    pass


class RigCalculationHandler:
    CALCULATE_CORRECTIVE = 0
    CALCULATE_SCULPT = 1

    CALCULATION_TYPES_MAPPING = {
        CALCULATE_CORRECTIVE: dnacalib.ExpressionCalculationType_JointAndCBS,
        CALCULATE_SCULPT: dnacalib.ExpressionCalculationType_Sculpt,
    }

    @staticmethod
    def _check_phases(src_expression, dst_expression):
        if src_expression.get_phase_numbers() != dst_expression.get_phase_numbers():
            message = f"Expressions {src_expression.name} and {dst_expression.name} don't have matching phases."
            raise PhasesError(message)

    @staticmethod
    def create_calculation_filter(rig_data_handler, calculation_type, expression_names=None):
        calculation_filter = dnacalib.ExpressionCalculationFilter()
        calculation_filter.setExpressionCalculationType(
            RigCalculationHandler.CALCULATION_TYPES_MAPPING[calculation_type]
        )

        if expression_names:
            calculation_filter.setExpressionIndices(
                [rig_data_handler.expression_indices[expression_name] for expression_name in expression_names]
            )
        return calculation_filter

    @staticmethod
    @status_validator_dnacalib
    def calculate_neutral_mesh(rig_data_handler):
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, RigCalculationHandler.CALCULATE_SCULPT
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)

        rig_data_handler.clean_expressions()
        rig_data_handler.update_dirty_expressions()

    @staticmethod
    @status_validator_dnacalib
    def calculate_skin_weights(rig_data_handler, calculation_type):
        calculation_filter = RigCalculationHandler.create_calculation_filter(rig_data_handler, calculation_type)
        rig_data_handler.rig.calculateExpressions(calculation_filter)
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, RigCalculationHandler.CALCULATE_SCULPT
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)

        rig_data_handler.clean_expressions()
        rig_data_handler.update_dirty_expressions()

    @staticmethod
    @status_validator_dnacalib
    def calculate_neutral_joints(rig_data_handler, calculation_type):
        calculation_filter = RigCalculationHandler.create_calculation_filter(rig_data_handler, calculation_type)
        rig_data_handler.rig.calculateExpressions(calculation_filter)
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, RigCalculationHandler.CALCULATE_SCULPT
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)

        rig_data_handler.clean_expressions()
        rig_data_handler.update_dirty_expressions()

    @staticmethod
    @status_validator_dnacalib
    def calculate_expression(rig_data_handler, expression_name, calculation_type):
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, calculation_type, [expression_name]
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)
        if calculation_type == RigCalculationHandler.CALCULATE_CORRECTIVE:
            calculation_filter = RigCalculationHandler.create_calculation_filter(
                rig_data_handler, RigCalculationHandler.CALCULATE_SCULPT, [expression_name]
            )
            rig_data_handler.rig.calculateExpressions(calculation_filter)

        rig_data_handler.clean_expressions([expression_name])
        rig_data_handler.update_dirty_expressions()

    @staticmethod
    @status_validator_dnacalib
    def calculate_expressions(rig_data_handler, expression_names, calculation_type):
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, calculation_type, expression_names
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)
        if calculation_type == RigCalculationHandler.CALCULATE_CORRECTIVE:
            calculation_filter = RigCalculationHandler.create_calculation_filter(
                rig_data_handler, RigCalculationHandler.CALCULATE_SCULPT, expression_names
            )
            rig_data_handler.rig.calculateExpressions(calculation_filter)
        rig_data_handler.clean_expressions(expression_names)
        rig_data_handler.update_dirty_expressions()

    @staticmethod
    def calculate_expression_sculpt(rig_data_handler, expression_name):
        RigCalculationHandler.calculate_expression(
            rig_data_handler, expression_name, RigCalculationHandler.CALCULATE_SCULPT
        )

    @staticmethod
    def calculate_expression_corrective(rig_data_handler, expression_name):
        RigCalculationHandler.calculate_expression(
            rig_data_handler, expression_name, RigCalculationHandler.CALCULATE_CORRECTIVE
        )

    @staticmethod
    @progress_guard(max_value=4)
    @status_validator_dnacalib
    def ordered_calculation(rig_data_handler, expression_names):
        ProgressUpdate.emit(status="ordered calculation")
        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, RigCalculationHandler.CALCULATE_CORRECTIVE, expression_names
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)
        ProgressUpdate.emit(status="calculate corrective expressions")

        calculation_filter = RigCalculationHandler.create_calculation_filter(
            rig_data_handler, RigCalculationHandler.CALCULATE_SCULPT, expression_names
        )
        rig_data_handler.rig.calculateExpressions(calculation_filter)

        ProgressUpdate.emit(status="calculate sculpt expressions")

        rig_data_handler.clean_expressions(expression_names)
        rig_data_handler.update_dirty_expressions()
        ProgressUpdate.emit(status="clean expressions")

    @staticmethod
    def transfer_joints(destination_rig, source_rig, expression_pairs):
        """
        Used to transfer joint deltas from a DNA file to the Rig currently being worked on.

        We need to calculate the delta first, because all the values in the Rig are absolute, and then add the delta
        to the destination neutral joints.
        Source expression rotations are taken as-is, because rotation values on neutral joints are actually joint
        orient values. The delta is then applied to the source expression to the destination expression rotations
        without adding the neutral rotation values for the same reason.

        :param source_dna_file_path: DNA file path for the DNA from which to transfer joint deltas.
        :param expression_pairs: Mapping of names for source and destination expression names.
        """
        source_neutral_joints = source_rig.get_neutral_joints()
        source_dna_joint_names = [
            source_rig.dna_reader.getJointName(i) for i in range(source_rig.dna_reader.getJointCount())
        ]

        destination_neutral_joints = destination_rig.get_neutral_joints()
        destination_dna_joint_names = [
            destination_rig.dna_reader.getJointName(i) for i in range(destination_rig.dna_reader.getJointCount())
        ]

        joint_indices_mapping = {}
        for index, source_dna_joint_name in enumerate(source_dna_joint_names):
            if source_dna_joint_name in destination_dna_joint_names:
                joint_indices_mapping[destination_dna_joint_names.index(source_dna_joint_name)] = index

        for source_expression_name, destination_expression_name in expression_pairs.items():
            source_rig_expression = source_rig.rig_definition.get_expression_by_name(source_expression_name)
            destination_rig_expression = destination_rig.rig_definition.get_expression_by_name(
                destination_expression_name
            )
            RigCalculationHandler._check_phases(source_rig_expression, destination_rig_expression)
            for phase in source_rig_expression.get_phase_numbers():
                source_expression_joints = source_rig.get_expression_joints(source_expression_name, phase)
                destination_expression_joints = destination_rig.get_expression_joints(
                    destination_expression_name, phase
                )

                new_destination_expression_joints = []

                for i in range(len(destination_dna_joint_names)):
                    if i in joint_indices_mapping:
                        for ii in range(9):
                            if ii in [3, 4, 5]:
                                new_destination_expression_joints.append(
                                    source_expression_joints[joint_indices_mapping[i] * 9 + ii]
                                )
                            else:
                                new_destination_expression_joints.append(
                                    destination_neutral_joints[i * 9 + ii]
                                    + source_expression_joints[joint_indices_mapping[i] * 9 + ii]
                                    - source_neutral_joints[joint_indices_mapping[i] * 9 + ii]
                                )
                    else:
                        for ii in range(9):
                            if ii in [3, 4, 5]:
                                new_destination_expression_joints.append(destination_expression_joints[i * 9 + ii])
                            else:
                                new_destination_expression_joints.append(
                                    destination_neutral_joints[i * 9 + ii] + destination_expression_joints[i * 9 + ii]
                                )

                destination_rig.set_expression_joints(
                    destination_expression_name, phase, new_destination_expression_joints
                )

    @staticmethod
    def transfer_neutral_joints(destination_rig, source_rig):
        source_neutral_joints = source_rig.get_neutral_joints()
        source_dna_joint_names = [
            source_rig.dna_reader.getJointName(i) for i in range(source_rig.dna_reader.getJointCount())
        ]

        destination_neutral_joints = destination_rig.get_neutral_joints()
        destination_dna_joint_names = [
            destination_rig.dna_reader.getJointName(i) for i in range(destination_rig.dna_reader.getJointCount())
        ]

        joint_indices_mapping = {}
        for i, source_dna_joint_name in enumerate(source_dna_joint_names):
            if source_dna_joint_name in destination_dna_joint_names:
                joint_indices_mapping[destination_dna_joint_names.index(source_dna_joint_name)] = i

        for i in range(len(destination_dna_joint_names)):
            if i in joint_indices_mapping:
                for ii in range(9):
                    destination_neutral_joints[i * 9 + ii] = source_neutral_joints[joint_indices_mapping[i] * 9 + ii]

        destination_rig.set_neutral_joints(destination_neutral_joints)

    @staticmethod
    def transfer_sculpts(
        destination_rig,
        source_rig,
        sculpt_meshes,
    ):
        expression_types = [1, 4]  # Main and Target expressions.
        expressions = []

        for exp in source_rig.rig_definition.expressions:
            if exp.function_type in expression_types and destination_rig.rig_definition.get_expression_by_name(
                exp.name
            ):
                expressions.append(exp)

        for source_expression in expressions:
            for mesh_name in sculpt_meshes:
                target_expression = destination_rig.rig_definition.get_expression_by_name(source_expression.name)

                source_mesh_in_expression = source_expression.get_mesh_in_expression(mesh_name)
                target_mesh_in_expression = target_expression.get_mesh_in_expression(mesh_name)

                if source_mesh_in_expression.function_type == 1 or target_mesh_in_expression.function_type == 1:
                    continue

                RigCalculationHandler._check_phases(source_expression, target_expression)

                for phase in source_expression.get_phase_numbers():
                    source_sculpt = source_rig.get_sculpt_mesh_vertex_positions(
                        mesh_name, source_expression.name, phase
                    )
                    destination_rig.set_sculpt(mesh_name, source_expression.name, phase, source_sculpt)

    @staticmethod
    @status_validator_dnacalib
    def apply_deltas(
        destination_rig,
        source_expression_name,
        destination_expression_names,
        calculate_joint_deltas,
        calculate_blend_shape_deltas,
        delta_multipliers,
    ):
        if len(destination_expression_names) != len(delta_multipliers):
            raise ValueError("Destination expressions pattern and delta multipliers needs to have same length")
        delta = destination_rig.get_rig_delta()
        source_expression = destination_rig.rig_definition.get_expression_by_name(source_expression_name)
        for destination_expression_name in destination_expression_names:
            destination_expression = destination_rig.rig_definition.get_expression_by_name(destination_expression_name)
            RigCalculationHandler._check_phases(source_expression, destination_expression)

        if calculate_joint_deltas and calculate_blend_shape_deltas:
            delta_option = dnacalib.DeltaTransferOption_JointsAndBlendShapes
        else:
            if calculate_joint_deltas:
                delta_option = dnacalib.DeltaTransferOption_JointsOnly
            else:
                delta_option = dnacalib.DeltaTransferOption_BlendShapesOnly
        for destination_expression_name, delta_multiplier in zip(destination_expression_names, delta_multipliers):
            for phase in source_expression.get_phase_numbers():
                destination_rig.rig.applyDelta(
                    delta,
                    destination_rig.expression_indices[source_expression_name],
                    phase - 1,
                    destination_rig.expression_indices[destination_expression_name],
                    phase - 1,
                    delta_option,
                    delta_multiplier,
                )
        destination_rig.update_dirty_expressions()

    @staticmethod
    @status_validator_dnacalib
    def add_head_turns(rig, head_turns_data):
        """
        Adds head turns to rig based on the joint animation data provided.

        The joint animation is provided for BODY_C_Neck1, BODY_C_Neck2, and BODY_C_Head joints only for main head turn
        expressions. Which target expressions should get which animation is determined using PSD definitions from the
        rig definition.

        After applying the provided joint animations, the rig is then calculated.
        """
        for expression_name, joint_animation in head_turns_data.items():
            expression_joints = {}
            for joint_name, joint_rotations in joint_animation.items():
                neutral_joint = rig.get_expression_joint(expression_name, 1, joint_name)
                expression_joint = neutral_joint[:]
                expression_joint[3:6] = joint_rotations
                expression_joints[joint_name] = expression_joint
                rig.set_expression_joint(expression_name, 1, joint_name, expression_joint)
            RigCalculationHandler.calculate_expression_sculpt(rig, expression_name)
            dictionary: Dict[str, Expression] = {}
            rig.rig_definition.get_dependent_psd_definitions_for_expression(expression_name, dictionary)
            for dependant_expression_name, dependant_expression in dictionary.items():
                if dependant_expression.type == Expression.COMPLEXPOSE_EXPRESSION:
                    RigCalculationHandler.calculate_expression_corrective(rig, dependant_expression_name)
                elif dependant_expression.type == Expression.CORRECTIVETARGET_EXPRESSION:
                    for joint_name, expression_joint in expression_joints.items():
                        rig.set_expression_joint(dependant_expression_name, 1, joint_name, expression_joint)
                    RigCalculationHandler.calculate_expression_sculpt(rig, dependant_expression_name)
                elif dependant_expression.type == Expression.CORRECTIVE_EXPRESSION:
                    RigCalculationHandler.calculate_expression_corrective(rig, dependant_expression_name)
        expressions = rig.rig_definition.get_expressions_names()
        RigCalculationHandler.ordered_calculation(rig, expressions)
