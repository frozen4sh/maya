# Copyright Epic Games, Inc. All Rights Reserved.


class NLSJointsMatchingOptions:
    """
    Class containing options defining NLS joints matching options for 3lateral calculation.
    """

    def __init__(self):
        self.name = ""
        self.expressions = []  # string[]
        self.passes = []  # NLSJointsMatchingPass[]

    def get_expressions_from_definition(self, rig_definition):
        """
        Get list of .Expression objects corresponding expressions in this options object.

        @param rig_definition: Rig definition that is owner of expression objects we are searching for. (RigDefinition)
        @return List of model Expression objects. (Expression)
        """

        return [rig_definition.get_expression_by_name(expression) for expression in self.expressions]


class NLSJointsMatchingPass:
    """
    Class containing pass calculation data for 3lateral NLS joints matching calculation.
    """

    # default values
    NUM_ITERATIONS = 10
    TRANSLATE_REG = 0.0
    ROTATE_REG = 5.0
    STRAIN_WEIGHT = 0.001
    BENDING_WEIGHT = 0.001

    # starting joints positions
    START_TYPE_CURRENT = 0
    START_TYPE_NEUTRAL = 1

    def __init__(self, name):
        self.name = name
        self.mesh_name = ""
        self.sculpt_mesh_name = ""
        self.start_type = NLSJointsMatchingPass.START_TYPE_NEUTRAL
        self.paint_constraint_split_map = ""
        self.joint_options = []  # NLSJointsMatchingJointOptions[]

        # matching parameters
        self.n_iterations = NLSJointsMatchingPass.NUM_ITERATIONS
        self.translation_regularization = NLSJointsMatchingPass.TRANSLATE_REG
        self.rotation_regularization = NLSJointsMatchingPass.ROTATE_REG
        self.strain_weight = NLSJointsMatchingPass.STRAIN_WEIGHT
        self.bending_weight = NLSJointsMatchingPass.BENDING_WEIGHT

    def get_joint_options_by_name(self, joint_name):
        """
        Get joint options defined in this pass for joint with pattern joint_name.

        @param joint_name: Name of joint to find options for. (pattern)
        @return Joint options for provided joint. (NLSJointsMatchingJointOptions)
        """

        for joint_option in self.joint_options:
            if joint_option.name == joint_name:
                return joint_option
        return None


class NLSJointsMatchingJointOptions:
    """
    Class containing information what attributes should be used during 3lateral NLS joints matching calculation.
    """

    def __init__(self, joint_name):
        self.name = joint_name
        # [translate, rotate]
        self.is_variable = [True, True]

    def __eq__(self, other):
        if not isinstance(other, NLSJointsMatchingJointOptions):
            return False
        return self.name == other.name

    def __lt__(self, other):
        if not isinstance(other, NLSJointsMatchingJointOptions):
            return False
        return self.name < other.name
