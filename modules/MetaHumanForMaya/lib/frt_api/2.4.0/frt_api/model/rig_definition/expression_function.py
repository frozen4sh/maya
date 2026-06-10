# Copyright Epic Games, Inc. All Rights Reserved.
from typing import TYPE_CHECKING, List, Optional

from frt_api.model.rig_definition.mesh import SplitMap
from frt_api.model.rig_definition.joint import SplitJoint

if TYPE_CHECKING:
    from .expression import Expression


class ExpressionFunction:
    """
    Expression function base class.

    It describes how expression is calculated and from which other expressions.
    """

    # constants
    FUNCTION_DERIVED = 1
    FUNCTION_DIFF = 2
    FUNCTION_DIFF2 = 3
    FUNCTION_SUM = 10
    FUNCTION_CMX = 10

    def __init__(self, function_type: Optional[int] = None, output: Optional["Expression"] = None):
        self.function_type: Optional[int] = function_type
        self.output: Optional[Expression] = output

    @staticmethod
    def create_expression_function(expression_function_type) -> "ExpressionFunction":
        """
        Factory method for building expression function objects instances based
        on object_type.
        """

        if expression_function_type == ExpressionFunction.FUNCTION_DERIVED:
            return DerivedExpFunc()
        if expression_function_type == ExpressionFunction.FUNCTION_DIFF:
            return DifferenceExpFunc()
        if expression_function_type == ExpressionFunction.FUNCTION_DIFF2:
            return Difference2ExpFunc()
        if expression_function_type in (ExpressionFunction.FUNCTION_SUM, ExpressionFunction.FUNCTION_CMX):
            return SumExpFunc()
        return ExpressionFunction()

    def __str__(self) -> str:
        return f"{self.output.name if self.output else ''}_{self.get_type_as_string()}"

    def get_type_as_string(self) -> str:
        """
        Gets function object_type as string representation.

        @return Type string representation. (string)
        """

        if self.function_type == ExpressionFunction.FUNCTION_DERIVED:
            return "derived"
        if self.function_type == ExpressionFunction.FUNCTION_DIFF:
            return "difference"
        if self.function_type == ExpressionFunction.FUNCTION_DIFF2:
            return "difference2"
        if self.function_type == ExpressionFunction.FUNCTION_SUM:
            return "sum"
        return ""

    def get_input_expressions(self) -> List[Optional["Expression"]]:
        """
        Gets all input expressions.

        Input expressions are expression needed to claculate output expression.
        This function has to be overriden.
        """

        return []


class DerivedExpFunc(ExpressionFunction):
    """
    Expression function which defines how expression is derived from other.
    It is used when complex expression has to be split on more expressions.
    For example when smile is derived to smile_left and smile_right.
    Resulting expression is calculated by applying split maps and split joint
    on input expression.

    @see ExpressionFunction
    @see SplitMap
    @see SplitJoint
    """

    def __init__(self, output=None):
        super().__init__(ExpressionFunction.FUNCTION_DERIVED, output)
        self.input: Optional[Expression] = None  # (Expression)
        self.split_maps: List[SplitMap] = []  # (SplitMap[])
        self.split_joints: List[SplitJoint] = []  # (SplitJoint[])

    def get_input_expressions(self) -> List[Optional["Expression"]]:
        """
        Gets list of expression needed for this expression calculation.

        @return List of expressions. (Expression[])
        @see ExpressionFunction#getInputExpressions
        """

        return [self.input]


class DifferenceExpFunc(ExpressionFunction):
    """
    Expression function which defines how expression is calculated by
    subtracting two other expressions.
    It is used when two expressions are modeled at same time, and we actually
    need difference between those two (corrective expression).
    For example, we model open smile, which is combination of two expressions,
    smile and smile_open. We get smile_open by subtracting open smile - smile.
    Resulting expression is calculated by subtracting second input from first
    input expression. Before subtraction inputs are multiplied by multipliers.

    @see ExpressionFunction
    """

    def __init__(self, output=None):
        super().__init__(ExpressionFunction.FUNCTION_DIFF, output)
        self.input1: Optional[Expression] = None  # (Expression)
        self.input2: Optional[Expression] = None  # (Expression)
        self.multiplier1: float = 0.0  # (float)
        self.multiplier2: float = 0.0  # (float)

    def get_input_expressions(self) -> List[Optional["Expression"]]:
        """
        Gets list of expression needed for this expression calculation.

        @return List of expressions. (Expression[])
        @see ExpressionFunction#getInputExpressions
        """

        return [self.input1, self.input2]


class Difference2ExpFunc(ExpressionFunction):
    """
    Simmilar to DifferenceExpFunc. Difference is that multipliers are applied
    differently. This function is more of experimental one and it is not widly
    used.

    @see ExpressionFunction
    @see DifferenceExpFunc
    """

    def __init__(self, output=None):
        super().__init__(ExpressionFunction.FUNCTION_DIFF2, output)
        self.input1: Optional[Expression] = None  # (Expression)
        self.input2: Optional[Expression] = None  # (Expression)
        self.multiplier1: float = 0.0  # (float)
        self.multiplier2: float = 0.0  # (float)

    def get_input_expressions(self) -> List[Optional["Expression"]]:
        """
        Gets list of expression needed for this expression calculation.

        @return List of expressions. (Expression[])
        @see ExpressionFunction#getInputExpressions
        """

        return [self.input1, self.input2]


class SumExpFunc(ExpressionFunction):
    """
    Expression function which defines how expression is calculated by
    adding two or more other expressions.
    Resulting expression is calculated by making sum of input expressions.
    Each input expression is multiplied by multiplier before adding to sum.

    @see ExpressionFunction
    """

    def __init__(self, output=None):
        super().__init__(ExpressionFunction.FUNCTION_SUM, output)
        self.inputs: List[ExpressionMultiplier] = []  # (ExpressionMultiplier[])

    def get_input_expressions(self) -> List[Optional["Expression"]]:
        """
        Gets list of expression needed for this expression calculation.

        @return List of expressions. (Expression[])
        @see ExpressionFunction#getInputExpressions
        """

        input_expressions: List[Optional["Expression"]] = []
        for inp in self.inputs:
            input_expressions.append(inp.expression)
        return input_expressions


class ExpressionMultiplier:
    """
    Expression multipler class define expression which is multiplied with some
    coefficient.
    It is used in different calculations when some expression's strenght can be
    changed before calculation.
    """

    def __init__(self, expression: Optional["Expression"] = None, multiplier: float = 1.0):
        self.expression: Optional[Expression] = expression
        self.multiplier: float = multiplier

    def __str__(self) -> str:
        return f"{self.expression.name if self.expression else ''}"

    def __eq__(self, cmp_exp_mult) -> bool:
        """
        Compares if expression multiplier is equal to other.

        @param cmp_exp_mult: Expression multiplier which self is compared to. (ExpressionMultiplier)
        @return True if expression and multiplier are equal, othervise False. (boolean)
        """
        if not isinstance(cmp_exp_mult, ExpressionMultiplier):
            return False

        if self.expression and cmp_exp_mult.expression and self.expression.name != cmp_exp_mult.expression.name:
            return False
        if self.expression and self.multiplier != cmp_exp_mult.multiplier:
            return False
        return True
