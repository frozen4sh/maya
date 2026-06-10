# Copyright Epic Games, Inc. All Rights Reserved.

import logging
import contextlib
from math import pi, sqrt
from typing import Any, Dict, List, Union

import maya.api.OpenMaya as om
from nls.jointsmatchingml import JointsMatchingML
from nls.jointrigoptimization import JointRigOptimization

from .rig import MeshNotFoundError
from ..publisher import ProgressStart, ProgressUpdate, progress_guard
from ..model.joints_matching import NLSJointsMatchingPass
from ..model.rig_definition.mesh import MeshInExpression

logger = logging.getLogger("frt_api.rig.joints_matching")


def decompose_into_scaling_rotation_and_translation(mat: om.MMatrix, allow_negative_scaling=False):
    """
    Decomposes the matrix @p mat into a scaling matrix, rotation matrix, and a translation matrix.
    The scaling matrix is a lower triangular matrix for the top left 3x3 block of the 4x4 matrix. It represents both scale and shear).
    The rotation matrix is a 3x3 rotation matrix.
    The translation matrix just has the translational component on the 4th row.
    S = |s00 0   0   0|
        |s10 s11 0   0|
        |s20 s21 s22 0|
        |0   0   0   1|

    R = |r00 r01 r02 0|
        |r10 s11 r12 0|
        |r20 s21 s22 0|
        |0   0   0   1|

    T = |1  0  0  0|
        |0  1  0  0|
        |0  0  1  0|
        |tx ty tz 1|

    @param allowNegativeScaling  When the matrix @p mat also contains a flip, then either the method triggers an assert, or the z scaling will be negative.
                                 The rotation matrix is always orthonormal with a determinant 1 (never negative 1)
    """

    S = om.MMatrix()
    R = om.MMatrix()
    T = om.MMatrix()
    # copy translation
    for i in range(3):
        T.setElement(3, i, mat.getElement(3, i))

    # the scale matrix S and rotation matrix R can be calculated using RQ decomposition.
    # note that S=R and R=Q in this case i.e. S is a lower triangular 3x3 matrix, and R the
    # rotation matrix
    def copy_row(src, target, index):
        for i in range(4):
            target.setElement(index, i, src.getElement(index, i))

    def scale_row(target, scale, index):
        for i in range(4):
            target.setElement(index, i, target.getElement(index, i) * scale)

    def dot_row(A, indexA, B, indexB):
        result = 0
        for i in range(4):
            result += A.getElement(indexA, i) * B.getElement(indexB, i)
        return result

    def row_norm(A, index):
        return sqrt(dot_row(A, index, A, index))

    def subtract_scaled_row(A, index1, index2, val):
        for i in range(4):
            A.setElement(index1, i, A.getElement(index1, i) - val * A.getElement(index2, i))

    # gram-schmidt rq decomposition
    copy_row(mat, R, 0)
    copy_row(mat, R, 1)
    copy_row(mat, R, 2)

    for i in range(3):
        for j in range(i):
            # subtract projections
            val = dot_row(R, i, R, j)
            S.setElement(i, j, val)
            subtract_scaled_row(R, i, j, val)

        n = row_norm(R, i)
        ninv = 1.0 / n
        S.setElement(i, i, n)
        scale_row(R, ninv, i)

    if R.det4x4() < 0:  # cross_product(row_vector(R, 0), row_vector(R, 1)) * row_vector(R,2) < 0:
        if not allow_negative_scaling:
            raise ValueError("No negative scaling supported.")
        S.setElement(2, 2, -S.getElement(2, 2))
        R.setElement(2, 0, -R.getElement(2, 0))
        R.setElement(2, 1, -R.getElement(2, 1))
        R.setElement(2, 2, -R.getElement(2, 2))

    return S, R, T


def decompose_into_scaling_and_shear(S: om.MMatrix):
    """
    Decompose a scaling matrix as returned from decomposeIntoScalingRotationAndTranslation into its scaling and shear matrices Sc and Sh such
    that S = Sc * Sh. Sc and Sh can directly be set for the Maya transformation matrix.
    """

    Sc = om.MMatrix()
    Sh = om.MMatrix()
    Sc.setElement(0, 0, S.getElement(0, 0))
    Sc.setElement(1, 1, S.getElement(1, 1))
    Sc.setElement(2, 2, S.getElement(2, 2))
    Sh.setElement(1, 0, S.getElement(1, 0) / S.getElement(1, 1))
    Sh.setElement(2, 0, S.getElement(2, 0) / S.getElement(2, 2))
    Sh.setElement(2, 1, S.getElement(2, 1) / S.getElement(2, 2))
    return Sc, Sh


def calculate_transformations_from_matrix(joint_orient, matrix, allow_negative_scaling=False):
    # joint does not have any pivots, so we cna get the translation component directly
    tx = matrix.getElement(3, 0)
    ty = matrix.getElement(3, 1)
    tz = matrix.getElement(3, 2)

    # remove the inverse scale compensate matrix
    m2 = matrix * om.MMatrix().inverse()

    s_, r_, _ = decompose_into_scaling_rotation_and_translation(m2, allow_negative_scaling)

    # M = [S] * [RO] * [R] * [JO] * [IS] * [T]
    # => R_ = RO * R * JO = R_
    orientation_matrix = om.MTransformationMatrix()
    orientation_matrix.setRotation(om.MEulerRotation(*[v * pi / 180 for v in joint_orient]))
    r = om.MMatrix() * r_ * om.MMatrix(orientation_matrix.asMatrix()).transpose()
    # [S] = S_ * R_ * invIS * invR_
    s, _ = decompose_into_scaling_and_shear(s_)

    r_quaternion = om.MQuaternion()
    r_quaternion.setValue(r)
    r_euler = r_quaternion.asEulerRotation()
    rx = r_euler[0] * (180 / pi)
    ry = r_euler[1] * (180 / pi)
    rz = r_euler[2] * (180 / pi)

    return [tx, ty, tz, rx, ry, rz, s.getElement(0, 0), s.getElement(1, 1), s.getElement(2, 2)]


class MLJointsMatchingHandler:
    def __init__(self, rig, rig_orientation: List[float]):
        self.rig = rig
        self.rig_orientation = rig_orientation or [0.0, 0.0, 0.0]
        self.bind_pose: List[om.MMatrix] = []
        self.inverse_bind_pose: Dict[str, om.MMatrix] = {}
        self.model_loaded = False
        self.ml_joints_matching = JointsMatchingML()

        self.root_joint_translation, self.rotation_matrix, self.inverse_translation = self._prepare_rotation_data()
        bind_pose = self._get_bind_pose()
        neutral_geometry = self._get_neutral_geometry()
        self.ml_joints_matching.setBindPose(bind_pose, neutral_geometry)

    def load_model(self, configuration_file_path, batch_size=1):
        self.ml_joints_matching.loadModel(configuration_file_path, batch_size)
        self.model_loaded = True

    def _get_neutral_joint_rotations_and_translations(self):
        neutral_joint_translations = []
        neutral_joint_rotations = []
        for i in range(self.rig.dna_reader.getJointCount()):
            neutral_joint = self.rig.get_neutral_joint(self.rig.dna_reader.getJointName(i))
            neutral_joint_translations.append(neutral_joint[:3])
            neutral_joint_rotations.append(neutral_joint[3:6])
        return neutral_joint_translations, neutral_joint_rotations

    def _prepare_rotation_data(self):
        root_joint_translation = self.rig.get_neutral_joint(self.rig.rig_definition.joints[0].name)[0:3]

        translation_matrix = om.MTransformationMatrix()
        translation_matrix.setTranslation(om.MVector(root_joint_translation), om.MSpace.kWorld)
        rotation_matrix = om.MTransformationMatrix()
        rotation_matrix.setRotation(om.MEulerRotation([v / 180 * pi for v in self.rig_orientation]))

        inverse_translation_matrix = om.MTransformationMatrix(
            translation_matrix.asMatrix() * rotation_matrix.asMatrix()
        )
        inverse_translation = inverse_translation_matrix.translation(om.MSpace.kWorld)

        return root_joint_translation, rotation_matrix, inverse_translation

    def _rotate_matrix(self, matrix, inverse=False):
        if inverse:
            translation = -self.inverse_translation
            rotation_matrix = self.rotation_matrix.asMatrix().inverse()
            inverse_translation = om.MVector(self.root_joint_translation)
        else:
            translation = -om.MVector(self.root_joint_translation)
            rotation_matrix = self.rotation_matrix.asMatrix()
            inverse_translation = self.inverse_translation
        original_matrix = om.MTransformationMatrix(matrix)
        original_matrix.translateBy(translation, om.MSpace.kWorld)
        original_matrix = om.MTransformationMatrix(original_matrix.asMatrix() * rotation_matrix)
        original_matrix.translateBy(inverse_translation, om.MSpace.kWorld)

        return original_matrix.asMatrix()

    def _rotate_point(self, point):
        original_matrix = om.MTransformationMatrix()
        original_matrix.setTranslation(om.MVector(point), om.MSpace.kWorld)
        original_matrix.translateBy(-om.MVector(self.root_joint_translation), om.MSpace.kWorld)
        original_matrix = om.MTransformationMatrix(original_matrix.asMatrix() * self.rotation_matrix.asMatrix())
        original_matrix.translateBy(self.inverse_translation, om.MSpace.kWorld)

        return original_matrix.translation(om.MSpace.kWorld)

    def _get_bind_pose(self):
        bind_pose: List[Dict[str, Union[int, List[float]]]] = []
        bind_pose_dict: Dict[str, om.MMatrix] = {}
        temp_bind_pose: List[om.MMatrix] = []
        neutral_joint_translations, neutral_joint_rotations = self._get_neutral_joint_rotations_and_translations()

        for jnt in self.rig.rig_definition.joints.get_all_elements():
            ws_transformation_matrix = self._get_neutral_joint_transformation_matrix(
                neutral_joint_translations, neutral_joint_rotations, bind_pose_dict, jnt.name
            )
            bind_pose_dict[jnt.name] = ws_transformation_matrix
            temp_bind_pose.append(ws_transformation_matrix)

        for jnt, ws_transformation_matrix in zip(self.rig.rig_definition.joints.get_all_elements(), temp_bind_pose):
            rotated_ws_transformation_matrix = self._rotate_matrix(ws_transformation_matrix)
            ws_transformation_matrix_dict: Dict[str, Union[int, List[float]]] = {
                "cols": 4,
                "data": list(rotated_ws_transformation_matrix),
                "rows": 4,
            }
            bind_pose.append(ws_transformation_matrix_dict)
            self.bind_pose.append(rotated_ws_transformation_matrix)
            self.inverse_bind_pose[jnt.name] = rotated_ws_transformation_matrix.inverse()
        return bind_pose

    def _get_neutral_geometry(self):
        neutral_mesh_data = []
        for mesh_index in self.rig.dna_reader.getMeshIndicesForLOD(0):
            for vertex_index in range(self.rig.dna_reader.getVertexPositionCount(mesh_index)):
                neutral_mesh_data.extend(
                    self._rotate_point(self.rig.dna_reader.getVertexPosition(mesh_index, vertex_index))
                )
        return {
            "cols": len(neutral_mesh_data) / 3,
            "data": neutral_mesh_data,
            "rows": 3,
        }

    @staticmethod
    def _get_transformation_matrix(translation, rotation, orient=None):
        tm = om.MTransformationMatrix()
        tm.setTranslation(om.MVector(*translation), om.MSpace.kTransform)
        tm.setRotation(om.MEulerRotation(*[v * pi / 180 for v in rotation]))
        if orient:
            tm.rotateBy(om.MEulerRotation(*[v * pi / 180 for v in orient]), om.MSpace.kTransform)
        return om.MMatrix(tm.asMatrix())

    def _get_neutral_joint_transformation_matrix(
        self,
        neutral_joint_translations,
        neutral_joint_rotations,
        neutral_joint_ws_transformation_matrices,
        joint_name,
    ):
        joint_chain_indices = self.rig.get_joint_hierarchy_indices(joint_name)

        tm = MLJointsMatchingHandler._get_transformation_matrix(
            neutral_joint_translations[joint_chain_indices[0]],
            neutral_joint_rotations[joint_chain_indices[0]],
        )

        with contextlib.suppress(IndexError):
            tm *= neutral_joint_ws_transformation_matrices[self.rig.dna_reader.getJointName(joint_chain_indices[1])]

        return tm

    def _get_expression_joint_transformation_matrix(
        self, joint_translations, joint_rotations, joint_ws_transformation_matrices, joint_name
    ):
        joint_chain_indices = self.rig.get_joint_hierarchy_indices(joint_name)

        tm = MLJointsMatchingHandler._get_transformation_matrix(
            joint_translations[joint_chain_indices[0]],
            joint_rotations[joint_chain_indices[0]],
            self.rig.get_neutral_joint(joint_name)[3:6],
        )

        with contextlib.suppress(IndexError):
            tm *= joint_ws_transformation_matrices[self.rig.dna_reader.getJointName(joint_chain_indices[1])]

        return tm

    def match_joints(
        self, expressions, phases, all_expression_joints, all_expression_shapes, update_rig=False, joint_locking=None
    ):
        if not self.model_loaded:
            raise RuntimeError("ML Joints Matching Model Not Loaded.")
        all_current_joints = []
        all_current_joints_ws_deltas = {}
        all_mask_joints = []
        all_target_meshes = []

        joint_names = [jnt.name for jnt in self.rig.rig_definition.joints.get_all_elements()]
        joint_names_set = set(joint_names)

        for expression, phase_number in zip(expressions, phases):
            current_joints = []
            current_joints_ws_deltas = {}
            expression_joints = all_expression_joints[(expression, phase_number)]
            expression_joints_dict: Dict[str, om.MMatrix] = {}
            joint_translations = []
            joint_rotations = []

            for i in range(0, len(expression_joints), 9):
                joint_translations.append(expression_joints[i : i + 3])
                joint_rotations.append(expression_joints[i + 3 : i + 6])

            for jnt in self.rig.rig_definition.joints.get_all_elements():
                expression_ws_transformation_matrix = self._get_expression_joint_transformation_matrix(
                    joint_translations, joint_rotations, expression_joints_dict, jnt.name
                )
                expression_joints_dict[jnt.name] = expression_ws_transformation_matrix
            for jnt in self.rig.rig_definition.joints.get_all_elements():
                rotated_expression_ws_transformation_matrix = self._rotate_matrix(expression_joints_dict[jnt.name])
                delta_ws_transformation_matrix = (
                    rotated_expression_ws_transformation_matrix * self.inverse_bind_pose[jnt.name]
                )
                delta_ws_transformation_matrix_dict = {
                    "cols": 4,
                    "data": list(delta_ws_transformation_matrix),
                    "rows": 4,
                }
                current_joints.append(delta_ws_transformation_matrix_dict)
                current_joints_ws_deltas[jnt.name] = delta_ws_transformation_matrix_dict
            all_current_joints.append(current_joints)
            all_current_joints_ws_deltas[expression] = current_joints_ws_deltas

            mask_joints = []
            if joint_locking and expression in joint_locking:
                allowed_joints = set(joint_locking[expression])
            else:
                allowed_joints = joint_names_set
            for jnt in joint_names:
                if jnt in allowed_joints:
                    mask_joints.append(True)
                else:
                    mask_joints.append(False)
            all_mask_joints.append(mask_joints)

            target_mesh_data = []
            for mesh_name in self.rig.rig_definition.lod_meshes[0].meshes:
                if mesh_name not in all_expression_shapes[(expression, phase_number)]:
                    sculpt_mesh_vertex_positions = [
                        self._rotate_point(point) for point in self.rig.get_neutral_mesh_vertex_positions(mesh_name)
                    ]
                else:
                    sculpt_mesh_vertex_positions = [
                        self._rotate_point(point)
                        for point in all_expression_shapes[(expression, phase_number)][mesh_name]
                    ]
                target_mesh_data.extend([value for values in sculpt_mesh_vertex_positions for value in values])

            all_target_meshes.append(
                {
                    "cols": len(target_mesh_data) // 3,
                    "data": target_mesh_data,
                    "rows": 3,
                }
            )

        matched_joints = dict(
            zip(
                zip(expressions, phases),
                self.ml_joints_matching.optimize(all_target_meshes, all_current_joints, all_mask_joints),
            )
        )

        for key, values in matched_joints.items():
            for neutral_matrix, value in zip(self.bind_pose, values):
                value["data"] = list(self._rotate_matrix(om.MMatrix(value["data"]) * neutral_matrix, inverse=True))

        if update_rig:
            self.update_rig(matched_joints, joint_locking, all_current_joints_ws_deltas)
        return matched_joints

    def update_rig(self, expressions_ws_transformation_matrices, joint_locking, all_current_joints_ws_deltas):
        joint_hierarchy = {
            self.rig.dna_reader.getJointName(i): self.rig.dna_reader.getJointName(
                self.rig.dna_reader.getJointParentIndex(i)
            )
            for i in range(self.rig.dna_reader.getJointCount())
        }

        bind_pose_dict: Dict[str, om.MMatrix] = {}
        neutral_joint_translations, neutral_joint_rotations = self._get_neutral_joint_rotations_and_translations()
        for (
            expression,
            phase_number,
        ), expression_ws_transformation_matrix in expressions_ws_transformation_matrices.items():
            expression_world_space_matrices = {}
            final_joint_values = []
            for i in range(self.rig.dna_reader.getJointCount()):
                joint_name = self.rig.dna_reader.getJointName(i)
                if joint_locking and expression in joint_locking and joint_name not in joint_locking[expression]:
                    expression_ws_delta_transformation_matrix = om.MTransformationMatrix(
                        om.MMatrix(all_current_joints_ws_deltas[expression][joint_name]["data"])
                    )
                    neutral_ws_transformation_matrix = self._get_neutral_joint_transformation_matrix(
                        neutral_joint_translations, neutral_joint_rotations, bind_pose_dict, joint_name
                    )
                    bind_pose_dict[joint_name] = neutral_ws_transformation_matrix

                    expression_world_space_matrix = om.MTransformationMatrix(
                        expression_ws_delta_transformation_matrix.asMatrix() * neutral_ws_transformation_matrix
                    )

                else:
                    expression_world_space_matrix = om.MTransformationMatrix(
                        om.MMatrix(expression_ws_transformation_matrix[i]["data"])
                    )

                expression_world_space_matrices[joint_name] = expression_world_space_matrix
                if joint_hierarchy[joint_name] == self.rig.dna_reader.getJointName(i):
                    parent_ws_mat = om.MTransformationMatrix()
                else:
                    parent_ws_mat = expression_world_space_matrices[joint_hierarchy[joint_name]]
                final_result = om.MTransformationMatrix(
                    om.MMatrix(expression_world_space_matrix.asMatrix())
                    * om.MMatrix(parent_ws_mat.asMatrix()).inverse()
                )
                joint_orient = self.rig.get_neutral_joint(joint_name)[3:6]
                final_joint_values.extend(calculate_transformations_from_matrix(joint_orient, final_result.asMatrix()))

            self.rig.set_expression_joints(expression, phase_number, final_joint_values)


class NLSJointsMatchingHandler:
    """
    NLS Joints Matching data handler.
    """

    def __init__(self, rig):
        self.rig = rig

    def validate_options(self, options, rig_definition):
        """
        This function should validate NLS joints matching options and check file system for all needed data.
        It returns true if validation passes, false if there are errors in options.

        @param options: NLS Joints Matching Options. (NLSJointsMatchingOptions)
        @param rig_definition: Characters rig definition. (RigDefinition)
        @return Indicates whether validation passed without errors.
        """

        logger.debug("****** NLS joints matching validation start. ******")

        for nlsExpression in options.expressions:
            expression = rig_definition.get_expression_by_name(nlsExpression)

            for nls_pass in options.passes:
                # check if sculpt mesh is defined
                mesh_name = nls_pass.sculpt_mesh_name
                if not mesh_name:
                    logger.warning("Pass " + nls_pass.name + ": sculpt mesh is not selected.")
                    return False
                mesh_in_exp = expression.get_mesh_in_expression(mesh_name)
                if mesh_in_exp and mesh_in_exp.type == MeshInExpression.BLENDS:
                    logger.warning(
                        "Expression "
                        + expression.name
                        + ": mesh "
                        + mesh_name
                        + " is blends only for this expression. Sculpt does not exist."
                    )
                    return False

                # check existence of start joints data
                if nls_pass.start_type != NLSJointsMatchingPass.START_TYPE_NEUTRAL:
                    # check if pass mesh is joints in expression
                    mesh_in_exp = expression.get_mesh_in_expression(nls_pass.mesh_name)
                    if mesh_in_exp and mesh_in_exp.type == MeshInExpression.BLENDS:
                        logger.warning(
                            "Expression " + expression.name + ", pass " + nls_pass.mesh_name + ": mesh is blends only."
                        )
                        return False

        logger.debug("****** NLS joints matching validation end. ******")

        # return true if validation finished without errors
        return True

    def get_skinning_data(self, mesh_name):
        return self.rig.get_skin_weights(mesh_name)

    def create_skinning_dict(self, mesh_name, skinning_data):
        """
        Creates a dictionary with the joints, their local and world matrices, and the skin weights.

        Format for joints and geometry:

        joints {
            "pattern of joint" : {

                "parent" : pattern of parent joint (not available means root node)
                "local": 4x4 matrix (column major, pre multiply - should be possible to calculate it from the parent)
                "world": 4x4 matrix (column major, pre multiply)
                "influence": {
                    "pattern of geometry": {
                        "vertex indices": []
                        "vertex weights": []
                    }
                }
            }
        }

        "geometry" : {
            "pattern of geometry" : {
                "vertices" : 3xN matrix
            },
            ...
        }

        :param mesh_name: Mesh pattern of the mesh for which the skinning dictionary is created.
        :param skinning_data: Skinning data for the mesh.
        :return: Skinning dictionary containing the previously described data.
        """
        geometry_key = f"|{mesh_name}|{mesh_name}Shape"
        rig_joints = list(self.rig.rig_definition.joints.get_all_elements())

        joints = []
        for indices in skinning_data.joint_indices:
            joints.append(indices)

        if any(joints):
            joints = list({index for joint_indices in joints for index in joint_indices})

        joints = self.get_joint_parents(joints, rig_joints)

        joint_state: Dict[str, Dict[str, Union[int, List[float], om.MMatrix]]] = {"joints": {}}
        joint_path_names = []
        skinning_dict: Dict[str, Any] = {
            "joints": {},
            "geometry": {
                geometry_key: {
                    "vertices": {
                        "rows": 3,
                        "cols": self.rig.get_mesh_vertex_count(mesh_name),
                        "data": [],
                    }
                }
            },
        }

        joint_keys_mapping = {}

        for joint_id in joints:
            hierarchy_ids = [joint_id]
            parent_id = joint_id
            try:
                joint_parent_index = rig_joints.index(rig_joints[joint_id].parent)
            except ValueError:
                joint_parent_index = rig_joints.index(rig_joints[joint_id])
            while parent_id != joint_parent_index:
                hierarchy_ids.insert(0, joint_parent_index)
                parent_id = joint_parent_index
                try:
                    joint_parent_index = rig_joints.index(rig_joints[joint_parent_index].parent)
                except ValueError:
                    joint_parent_index = rig_joints.index(rig_joints[joint_parent_index])

            matrix = om.MTransformationMatrix()
            joint_transformations = self.rig.get_neutral_joint(rig_joints[joint_id].name)
            matrix.setRotation(om.MEulerRotation(*[v * pi / 180 for v in joint_transformations[3:6]]))
            matrix.setTranslation(om.MVector(*joint_transformations[0:3]), om.MSpace.kTransform)
            om2_matrix = om.MMatrix(matrix.asMatrix())

            key = "|%s" % "|".join([rig_joints[i].name for i in hierarchy_ids])
            joint_keys_mapping[joint_id] = key
            joint_path_names.append(key)
            joint_state["joints"][key] = {"local": {"cols": 4, "rows": 4, "data": om2_matrix}}

        joint_path_names.sort(key=lambda x: x.count("|"))

        neutral_mesh_positions = self.rig.get_neutral_mesh_vertex_positions(mesh_name)
        for vtx_position in neutral_mesh_positions:
            skinning_dict["geometry"][geometry_key]["vertices"]["data"].extend(vtx_position)

        temp_skinning_dict: Dict[str, Dict[str, List[Union[int, float]]]] = {}
        for joint_path_name in joint_path_names:
            temp_skinning_dict[joint_path_name] = {"vertex indices": [], "vertex weights": []}

        for i in range(self.rig.get_mesh_vertex_count(mesh_name)):
            for joint_index, weight in zip(skinning_data.joint_indices[i], skinning_data.weights[i]):
                temp_skinning_dict[joint_keys_mapping[joint_index]]["vertex indices"].append(i)
                temp_skinning_dict[joint_keys_mapping[joint_index]]["vertex weights"].append(weight)

        for joint_path_name in joint_path_names:
            world_matrix = om.MMatrix(joint_state["joints"][joint_path_name]["local"]["data"])  # type: ignore
            parent_name = joint_path_name

            if parent_name.count("|") > 1:
                parent_name = parent_name[: parent_name.rfind("|")]
                parent_matrix = skinning_dict["joints"][parent_name]["world"]["data"]
                world_matrix *= parent_matrix

            local_matrix = joint_state["joints"][joint_path_name]["local"]["data"]  # type: ignore
            skinning_dict["joints"][joint_path_name] = {
                "world": {"rows": 4, "cols": 4, "data": world_matrix},
                "influence": {},
                "local": {
                    "rows": 4,
                    "cols": 4,
                    "data": list(local_matrix),
                },
            }
            if joint_path_name.count("|") > 1:
                skinning_dict["joints"][joint_path_name]["parent"] = joint_path_name[
                    : joint_path_name.rfind("|")
                ]  # type: ignore

            if (
                temp_skinning_dict[joint_path_name]["vertex indices"]
                and temp_skinning_dict[joint_path_name]["vertex weights"]
            ):
                skinning_dict["joints"][joint_path_name]["influence"][geometry_key] = temp_skinning_dict[
                    joint_path_name
                ]

        for joint_path_name in joint_path_names:
            local_matrix = joint_state["joints"][joint_path_name]["local"]["data"]  # type: ignore
            joint_state["joints"][joint_path_name]["local"]["data"] = list(local_matrix)  # type: ignore

            world_matrix = skinning_dict["joints"][joint_path_name]["world"]["data"]
            skinning_dict["joints"][joint_path_name]["world"]["data"] = list(world_matrix)

        return joint_path_names, skinning_dict

    def get_joint_parents(self, joints, rig_joints):
        parent_joint_indices = []

        for joint in joints:
            try:
                joint_parent_index = rig_joints.index(rig_joints[joint].parent)
            except ValueError:
                joint_parent_index = rig_joints.index(rig_joints[joint])
            if joint_parent_index not in joints and joint_parent_index not in parent_joint_indices:
                parent_joint_indices.append(joint_parent_index)

        joints.extend(parent_joint_indices)
        if parent_joint_indices:
            return self.get_joint_parents(joints, rig_joints)
        joints.sort()
        return joints

    def get_mesh_dict(self, mesh_name, skinning_dict):
        """
        Creates a mesh dictionary:
        {
            "vertices" : 3xN matrix,
            "topology" : {
                "polygons" : [3, 4, 4, 3, 3, ...]     // number of vertices per polygon
                "vtxIDs" : [0, 1, 2, 1, 3, 4, 2, ...] // the vertex ids for the polygons, len(vtxIDs) == sum(polygonCount)
            }
        }

        :param mesh_name: Mesh pattern of the mesh for which the mesh dictionary is created.
        :param skinning_dict: Skinning data for the mesh.
        :return: Mesh data dictionary described above.
        """
        geometry_key = f"|{mesh_name}|{mesh_name}Shape"
        faces, edges = self.rig.get_neutral_mesh_topology(mesh_name)

        return {
            geometry_key: {
                "vertices": skinning_dict["geometry"][geometry_key]["vertices"],
                "topology": {
                    "polygons": faces,
                    "vtxIDs": edges,
                },
            }
        }

    def get_target_dictionary(self, mesh_name, expression_name, phase):
        """
        Creates a named geometry dictionary:
        {
            "geometry" : {
                "pattern/targetname" : {
                    "vertices" : 3xN matrix
                },
                ...
            },
            ...
        }

        :param mesh_name: Mesh pattern for the mesh being deformed.
        :param expression_name: Expression pattern for which the joint transformations are calculated.
        :return: Returns the data described above.
        """
        geometry_key = f"|{mesh_name}|{mesh_name}Shape"
        if mesh_name not in self.rig.rig_definition.get_dna_mesh_names():
            geometry_base_mesh_name = self.rig.rig_definition.get_geometry_base_mesh_name(mesh_name)
            if geometry_base_mesh_name is None:
                raise MeshNotFoundError(mesh_name)
            mesh_name = geometry_base_mesh_name

        result = {
            "geometry": {
                geometry_key: {
                    "vertices": {
                        "rows": 3,
                        "cols": self.rig.get_mesh_vertex_count(mesh_name),
                        "data": [],
                    }
                }
            }
        }
        sculpt = self.rig.get_sculpt_mesh_vertex_positions(mesh_name, expression_name, phase)
        for vertex in sculpt:
            result["geometry"][geometry_key]["vertices"]["data"].extend(vertex)

        return result

    def get_initial_joint_state(self, expression_name, phase, mutable_joints):
        """
        Returns a list of joint expression joint transformation for every joint that is not mutable. For mutable joints,
        neutral transformations are used.

        :param expression_name: Expression pattern for which the joint transformations are calculated.
        :param mutable_joints: List of joint names which can be changed.
        :return: List of joint transformations.
        """
        joint_state = []
        if not mutable_joints:
            return [
                self.rig.get_expression_joint(expression_name, phase, joint.name)
                for joint in self.rig.rig_definition.joints.get_all_elements()
            ]
        for joint in self.rig.rig_definition.joints.get_all_elements():
            if joint.name in mutable_joints:
                neutral_transformations = self.rig.get_neutral_joint(joint.name)
                neutral_transformations[3:6] = [0.0, 0.0, 0.0]
                joint_state.append(neutral_transformations)
            else:
                joint_state.append(self.rig.get_expression_joint(expression_name, phase, joint.name))
        return joint_state

    def get_joint_state(self, joint_path_names, joint_state):
        """
        Creates a named joint state dictionary:
        {
            "joints" : {
                "pattern of joint" : {
                    "local": 4x4 matrix (column major, pre multiply - should be possible to calculate it from the parent)
                },
                ...
            },
            ...
        }

        :param joint_path_names: List of joint names containing the whole joint hierarchy.
        :param joint_state:
        :return: Dictionary containing the joint state data described above.
        """

        result: Dict[str, Any] = {"joints": {}}

        joint_indices = {joint.name: i for i, joint in enumerate(self.rig.rig_definition.joints.get_all_elements())}

        for joint_path_name in joint_path_names:
            joint_name = joint_path_name.split("|")[-1]
            joint_transformations = joint_state[joint_indices[joint_name]]

            neutral_transformations = self.rig.get_neutral_joint(joint_name)

            matrix = om.MTransformationMatrix()
            matrix.setRotation(om.MEulerRotation(*[v * pi / 180 for v in joint_transformations[3:6]]))
            matrix.rotateBy(
                om.MEulerRotation(*[v * pi / 180 for v in neutral_transformations[3:6]]), om.MSpace.kTransform
            )
            matrix.setTranslation(om.MVector(*joint_transformations[0:3]), om.MSpace.kTransform)
            matrix_om2 = matrix.asMatrix()

            result["joints"][joint_path_name] = {"local": {"cols": 4, "rows": 4, "data": list(matrix_om2)}}
        return result

    def update_expression_joints(self, expression, phase, merged_joint_states, new_joint_states):
        """
        Updates the joints for the expression from the joint state data. The data contains the transformations as a
        local transformation matrix so the translation, rotation and scale values need to be extracted.

        :param expression: Name of expression for which the joints need to be updated.
        :param joint_state: Joint state data.
        :param joint_path_names: List of joint names containing the whole joint hierarchy.
        """

        joint_indices = {joint.name: i for i, joint in enumerate(self.rig.rig_definition.joints.get_all_elements())}

        for joint_state in new_joint_states["joints"]:
            joint_name = joint_state.split("|")[-1]
            local_matrix = om.MMatrix(new_joint_states["joints"][joint_state]["local"]["data"])
            joint_orient = self.rig.get_neutral_joint(joint_name)[3:6]
            merged_joint_states[joint_indices[joint_name]] = calculate_transformations_from_matrix(
                joint_orient, local_matrix
            )

        self.rig.set_expression_joints(
            expression.name, phase, [value for joint_state in merged_joint_states for value in joint_state]
        )


@progress_guard()
def match_joints(rig, options, expressions=None):
    """
    Calculates joints matching for given expressions using algorithm from NLS framework.

    @param expressions: List of expression objects to be calculated. (Expression[])
    @param options: Options object containing data needed for joints matching. (NLSJointsMatchingOptions)
    @return Calculation log list. (CalculationLog[])
    @throws CalculationError: If some of data is missing.
    """
    nlsjmh = NLSJointsMatchingHandler(rig)

    skinning_dicts = {}
    mesh_dicts = {}
    joint_path_names_dict = {}
    for nlsPass in options.passes:
        skinning_data = nlsjmh.get_skinning_data(nlsPass.mesh_name)
        joint_path_names, skinning_dict = nlsjmh.create_skinning_dict(nlsPass.mesh_name, skinning_data)
        if joint_path_names is not None and skinning_dict is not None:
            mesh_dict = nlsjmh.get_mesh_dict(nlsPass.mesh_name, skinning_dict)
            skinning_dicts[nlsPass.mesh_name] = skinning_dict
            mesh_dicts[nlsPass.mesh_name] = mesh_dict
            joint_path_names_dict[nlsPass.mesh_name] = joint_path_names

    expression_regions = {}

    for region, region_expression in rig.rig_definition.region_expressions.items():
        for exp in region_expression:
            if exp not in expression_regions:
                expression_regions[exp] = [region]
            else:
                expression_regions[exp].append(region)

    expression_joints: Dict[str, List[Any]] = {}

    for exp, regions in expression_regions.items():
        expression_joints[exp] = []
        for region in regions:
            expression_joints[exp].extend(rig.rig_definition.region_joints[region])

    if expressions is None:
        expressions = []
        for expression_name in options.expressions:
            expression = rig.rig_definition.get_expression_by_name(expression_name)
            expressions.append(expression)

    progress_max = len(expressions) * len(options.passes)

    ProgressStart.emit(max_value=progress_max)

    ProgressUpdate.emit(status="match joints")

    # for EXPRESSION
    for expression in expressions:
        opt = JointRigOptimization()

        logger.debug("Calculating joints matching: " + expression.name + ". Type: calculateNLSJointsMatching.")

        # for PASS
        for passIdx, nlsPass in enumerate(options.passes):
            mesh_name = nlsPass.mesh_name
            sculpt_mesh_name = nlsPass.sculpt_mesh_name
            # get sculpt to be matched: nlsPass.sculpt_mesh_name
            mesh_in_exp = expression.get_mesh_in_expression(sculpt_mesh_name)
            if mesh_in_exp:
                if mesh_in_exp.type == MeshInExpression.BLENDS:
                    logger.warning(
                        "Nothing to calculate. Expression skipped: " + expression.name + ", mesh: " + mesh_name
                    )
                    continue

            paint_constraint_weights = None

            joint_path_names = joint_path_names_dict[mesh_name]
            skinning_dict = skinning_dicts[mesh_name]
            mesh_dict = mesh_dicts[mesh_name]
            opt.addPass(passIdx, None, joint_path_names, skinning_dict, mesh_dict)

            mutable_joints = [
                jnt for jnt in expression_joints[expression.name] if nlsPass.get_joint_options_by_name(jnt)
            ]

            if not mutable_joints:
                continue

            opt.passes[passIdx].setConstantAll()
            for joint_path in opt.passes[passIdx].jointDOFs:
                joint_name = joint_path.split("|")[-1]
                nls_joint = nlsPass.get_joint_options_by_name(joint_name)
                if joint_name in mutable_joints:
                    opt.passes[passIdx].jointDOFs[joint_path]["fixed"] = False
                    opt.passes[passIdx].jointDOFs[joint_path]["rotation"] = nls_joint.is_variable[1]
                    opt.passes[passIdx].jointDOFs[joint_path]["translation"] = nls_joint.is_variable[0]

            # read paint constraint weights from file
            if nlsPass.paint_constraint_split_map:
                split_map = rig.rig_definition.get_split_map_by_name(nlsPass.paint_constraint_split_map)
                if split_map:
                    paint_constraint_weights = {"splitMap": split_map.value}

            # set split map for pass
            if paint_constraint_weights is not None:
                opt.passes[passIdx].setSplitMap(paint_constraint_weights)

            # for PASS for EXPRESSION for PHASENO
            for phaseNo in expression.get_phase_numbers():
                logger.debug(
                    "Calculating joints matching - expression: "
                    + expression.name
                    + ", mesh: "
                    + mesh_name
                    + ", phase: "
                    + str(phaseNo)
                )
                logger.debug("Getting start joints.")

                if nlsPass.start_type != NLSJointsMatchingPass.START_TYPE_NEUTRAL:
                    mutable_joints = None  # type: ignore

                target_dict = nlsjmh.get_target_dictionary(mesh_name, expression.name, phaseNo)
                merged_joint_states = nlsjmh.get_initial_joint_state(expression.name, phaseNo, mutable_joints)
                joint_state = nlsjmh.get_joint_state(joint_path_names, merged_joint_states)

                # MATCH JOINTS
                logger.debug("Start joints matching.")

                new_joint_states = opt.optimize(
                    passIdx,
                    None,
                    nlsPass.n_iterations,
                    nlsPass.translation_regularization,
                    nlsPass.rotation_regularization,
                    nlsPass.strain_weight,
                    nlsPass.bending_weight,
                    target_dict,
                    joint_state,
                )

                # save joints
                logger.info(f"Saving matched joints for {expression.name}.")
                nlsjmh.update_expression_joints(expression, phaseNo, merged_joint_states, new_joint_states)
            ProgressUpdate.emit(status=f"expression {expression.name} mesh {nlsPass.mesh_name} matched")

        ProgressUpdate.emit(status=f"expression {expression.name} matched")
