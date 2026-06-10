# Copyright Epic Games, Inc. All Rights Reserved.
from typing import TYPE_CHECKING, List, Tuple, Optional

from .core import RangeFloatAttr

if TYPE_CHECKING:
    from .expression import Expression
    from .expression_function import ExpressionMultiplier


class PsdNet:
    """
    PsdNet class.
    Represents psd calculation network.
    """

    TYPE_MINIMUM = 1
    TYPE_PRODUCT = 2

    def __init__(self):
        self.name: str = ""  # (string)
        self.psd_net_type: int = PsdNet.TYPE_PRODUCT  # (int)
        self.inputs: List[RangeFloatAttr] = []  # (RangeFloatAttr[])
        self.output: RangeFloatAttr = RangeFloatAttr("", "")  # (RangeFloatAttr)
        self.on_attr: RangeFloatAttr = RangeFloatAttr("", "")  # (RangeFloatAttr)

    def __str__(self):
        return self.name

    def get_type_as_string(self) -> str:
        """
        Gets psd net object_type as string representation.

        @return Type string representation. (string)
        """

        if self.psd_net_type == PsdNet.TYPE_MINIMUM:
            return "minimum"
        if self.psd_net_type == PsdNet.TYPE_PRODUCT:
            return "product"
        return ""

    def get_input_by_name(self, object_name: str, attribute: str) -> Optional[RangeFloatAttr]:
        """
        Get range float attribute with given object and attribute names.

        @param object_name: Object pattern. (pattern)
        @param attribute: Attribute pattern. (pattern)
        @return Range float attribute (RangeFloatAttr)
        """

        for psd_input in self.inputs:
            if psd_input.object_name == object_name and psd_input.attr_name == attribute:
                return psd_input
        return None


class AssemblingPsd:
    """
    AssemblingPsd class.
    Represents expression and psd net pairs.
    """

    def __init__(self, expression: "Expression", psd_net: PsdNet):
        self.expression: Expression = expression
        self.psd_net: Optional[PsdNet] = psd_net  # (PsdNet)

    def __str__(self):
        return self.expression.name


class PsdDefinition:
    """
    PsdDefinition class.
    Represents psd hierarchy and expression dependacies.
    """

    def __init__(self):
        self.name: str = ""  # (string)
        self.layer: int = 0  # (int)

        self.complex_pose: Optional[Expression] = None  # ("Expression")
        self.complex_pose_build: List[ExpressionMultiplier] = []  # ("ExpressionMultiplier"[])

        self.target_pose: Optional[Expression] = None  # ("Expression")
        self.target_pose_build: List[ExpressionMultiplier] = []  # ("ExpressionMultiplier"[])

        self.corrective_pose: Optional[Expression] = None  # ("Expression")

        self.sub_sets: List[PsdDefinition] = []  # (PsdDefinition[])
        self.super_sets: List[PsdDefinition] = []  # (PsdDefinition[])

        self.assembling_psds: List[AssemblingPsd] = []  # (AssemblingPsd[])

    def __str__(self):
        return self.name

    def is_dirty(self) -> Tuple[bool, bool, bool]:
        """
        Returns dirty flags.

        @return Tuple of three elements. Dirty for complex, target and corrective pose expression. (boolean[3])
        """

        return (
            all([self.complex_pose, self.complex_pose.is_dirty() if self.complex_pose else False]),
            all([self.target_pose, self.target_pose.is_dirty() if self.target_pose else False]),
            all([self.corrective_pose, self.corrective_pose.is_dirty() if self.corrective_pose else False]),
        )

    def set_dirty_on(self, dirty_dict, dirty_complex_pose=True):
        """
        Marks psd definition complex and corrective expression as dirty.
        Propagates dirty flag to upper layers.

        @param dirty_dict: Dictionary containing already set dirty espression names. ({string: None})
        @param dirty_complex_pose: Indicates should complex pose be set as dirty. (boolean)
        @return List of expressions which became dirty. ("Expression"[])
        """

        dirty_expressions = []
        if dirty_complex_pose and self.complex_pose:
            dirty_expressions.extend(self.complex_pose.set_dirty_on(dirty_dict))
        if self.target_pose:
            dirty_expressions.extend(self.target_pose.set_dirty_on(dirty_dict))
        if self.corrective_pose:
            dirty_expressions.extend(self.corrective_pose.set_dirty_on(dirty_dict))

        for psd in self.super_sets:
            dirty_expressions.extend(psd.set_dirty_on(dirty_dict))
        return dirty_expressions

    def is_sub_set(self, psd_def: "PsdDefinition") -> bool:
        """
        Checks if given psd_def is sub set of self psd definition.

        @param psd_def: Psd definition which is checked if it is sub set. (PsdDefinition)
        @return True if given psd definition is sub set.
        """

        for cmp_exp_mult in psd_def.complex_pose_build:
            has_it = False
            for self_cmp_exp_mult in self.complex_pose_build:
                if (
                    cmp_exp_mult.expression
                    and self_cmp_exp_mult.expression
                    and cmp_exp_mult.expression.name == self_cmp_exp_mult.expression.name
                ):
                    has_it = True
                    break
            if not has_it:
                return False
        if len(psd_def.complex_pose_build) == len(self.complex_pose_build):
            return False
        return True

    def is_super_set(self, psd_def: "PsdDefinition") -> bool:
        """
        Checks if given psd_def is super set of self psd definition.

        @param psd_def: Psd definition which is checked if it is super set. (PsdDefinition)
        @return True if given psd definition is super set.
        """

        for self_cmp_exp_mult in self.complex_pose_build:
            has_it = False
            for cmp_exp_mult in psd_def.complex_pose_build:
                if (
                    cmp_exp_mult.expression
                    and self_cmp_exp_mult.expression
                    and cmp_exp_mult.expression.name == self_cmp_exp_mult.expression.name
                ):
                    has_it = True
                    break
            if not has_it:
                return False
        if len(psd_def.complex_pose_build) == len(self.complex_pose_build):
            return False
        return True

    def connect_with(self, psd_def: "PsdDefinition"):
        """
        Informs psd definition that new psd definition is added and that dependacies
        between them should be reevaluated.

        @param psd_def: Newly created psd definition.
        """

        if self.is_sub_set(psd_def):
            self.sub_sets.append(psd_def)
            psd_def.super_sets.append(self)
        if self.is_super_set(psd_def):
            self.super_sets.append(psd_def)
            psd_def.sub_sets.append(self)

    def disconnect_with(self, psd_def: "PsdDefinition"):
        """
        Informs psd definition that psd definition is removed and that dependacies
        should be reevaluated.

        @param psd_def: Removed psd definition.
        """

        if psd_def in self.sub_sets:
            self.sub_sets.remove(psd_def)
        if psd_def in self.super_sets:
            self.super_sets.remove(psd_def)

    def refresh_layer(self):
        """
        Recalculates psd definition layer number.
        """

        self.layer = self.get_deep()

    def get_deep(self) -> int:
        """
        Gets psd definition maximum tree depth based on sub sets.

        @return Psd definition depth. (int)
        """

        deepest = 0
        for psd_def in self.sub_sets:
            deep = psd_def.get_deep()
            if deep > deepest:
                deepest = deep
        return deepest + 1

    def get_psd_all_expressions(self) -> List["Expression"]:
        """
        Gets all expressions related with psd definition.
        """

        expressions = []
        if self.complex_pose:
            expressions.append(self.complex_pose)
        if self.target_pose:
            expressions.append(self.target_pose)
        if self.corrective_pose:
            expressions.append(self.corrective_pose)
        for assembling_psd in self.assembling_psds:
            if assembling_psd.expression not in expressions:
                expressions.append(assembling_psd.expression)
        return expressions

    def get_psd_corrective_pose_expressions(self) -> List["Expression"]:
        """
        Gets psd definition corrective expressions.
        """
        expressions: List["Expression"] = []

        if self.corrective_pose:
            expressions.append(self.corrective_pose)

        for assembling_psd in self.assembling_psds:
            if assembling_psd.expression not in expressions:
                expressions.append(assembling_psd.expression)
        return expressions

    def get_complex_pose_build_by_name(self, name: str) -> Optional["ExpressionMultiplier"]:
        """
        Gets expression multiplier for given expression pattern from complex pose build.

        @param name: "Expression" pattern. (string)
        @return "Expression" multiplier from complex pose build. ("ExpressionMultiplier")
        """

        for exp_multiplier in self.complex_pose_build:
            if exp_multiplier.expression and exp_multiplier.expression.name == name:
                return exp_multiplier
        return None

    def get_target_pose_build_by_name(self, name: str) -> Optional["ExpressionMultiplier"]:
        """
        Gets expression multiplier for given expression pattern from target pose build.

        @param name: "Expression" pattern. (string)
        @return "Expression" multiplier from target pose build. ("ExpressionMultiplier")
        """

        for exp_multiplier in self.target_pose_build:
            if exp_multiplier.expression and exp_multiplier.expression.name == name:
                return exp_multiplier
        return None

    def get_assembling_psd_build_by_name(self, name: str) -> Optional[AssemblingPsd]:
        """
        Gets expression multiplier for given expression pattern from assembling PSDs.

        @param name: "Expression" pattern. (string)
        @return "Expression" multiplier from assemling PSDs. (AssemblingPsd)
        """

        for assembling_psd in self.assembling_psds:
            if assembling_psd.expression.name == name:
                return assembling_psd
        return None

    def is_expression_in_psd(self, expression_name: str) -> int:
        """
        Gets if expression is PSD expression and if it is, indicates which object_type.

        @param expression_name: "Expression" pattern. (string)
        @return Indicatr of expression PSD object_type or zero. (int)
        """
        from .expression import Expression

        if self.complex_pose and expression_name == self.complex_pose.name:
            return Expression.COMPLEXPOSE_EXPRESSION
        if self.target_pose and expression_name == self.target_pose.name:
            return Expression.CORRECTIVETARGET_EXPRESSION
        if self.corrective_pose and expression_name == self.corrective_pose.name:
            return Expression.CORRECTIVE_EXPRESSION
        for assembling_psd in self.assembling_psds:
            if assembling_psd.expression and expression_name == assembling_psd.expression.name:
                return Expression.CORRECTIVE_EXPRESSION
        return 0

    def remove_expression(self, expression_name: str):
        """
        Removes expression from PSD definition.

        @param expression_name: Name of expression to be removed. (string)
        """

        complex_to_remove = []
        if self.complex_pose and self.complex_pose.name == expression_name:
            self.complex_pose = None
        for exp_multiplier in self.complex_pose_build:
            if exp_multiplier.expression and exp_multiplier.expression.name == expression_name:
                complex_to_remove.append(exp_multiplier)
        for cmx in complex_to_remove:
            self.complex_pose_build.remove(cmx)

        target_to_remove = []
        if self.target_pose and self.target_pose.name == expression_name:
            self.target_pose = None
        for exp_multiplier in self.target_pose_build:
            if exp_multiplier.expression and exp_multiplier.expression.name == expression_name:
                target_to_remove.append(exp_multiplier)
        for tgt in target_to_remove:
            self.target_pose_build.remove(tgt)

        if self.corrective_pose and self.corrective_pose.name == expression_name:
            self.corrective_pose = None

        assembling_to_remove = []
        for assembling_psd in self.assembling_psds:
            if assembling_psd.expression and assembling_psd.expression.name == expression_name:
                assembling_to_remove.append(assembling_psd)
        for item in assembling_to_remove:
            self.assembling_psds.remove(item)

    def remove_psd_net(self, psd_net_name: str):
        """
        Removes PSD net from PSD definition.

        @param psd_net_name: Name of psd net to be removed. (string)
        """

        for assembling_psd in self.assembling_psds:
            if assembling_psd.psd_net and assembling_psd.psd_net.name == psd_net_name:
                assembling_psd.psd_net = None

    def get_description_str(self) -> str:
        """
        Gets description string which contains data about psd definition dirty flags and pattern.
        """

        dirty = self.is_dirty()
        output_string = str(self.layer) + " "
        output_string += "d" if dirty[0] else "_"
        output_string += "d" if dirty[1] else "_"
        output_string += "d" if dirty[2] else "_"
        output_string += "  " + self.name
        return output_string

    def is_complex_dependent_on_expression(self, expression_name: str) -> bool:
        """
        Returns True if complex pose is build by given expression. False if same is not true.

        @param expression_name: "Expression" pattern. (string)
        @return True if complex pose is dependent on exp, False otherwise. (boolean)
        """

        return any(
            exp_multiplier.expression.name == expression_name
            for exp_multiplier in self.complex_pose_build
            if exp_multiplier.expression
        )
