# Copyright Epic Games, Inc. All Rights Reserved.

from typing import TYPE_CHECKING, Any, List, Optional
from dataclasses import dataclass

if TYPE_CHECKING:
    from frt_api.model.rig_definition.expression import Expression, ActiveExpression


@dataclass
class ViewData:
    """
    View data class holds information's what additional assembling should be
    done when assembling expression on timeline. It defines which inbetween
    expression should be assembled and where.
    """

    frame: int = 0
    expression: Any = None
    multiplier: float = 1.0


class ExpressionView:
    """
    ExpressionView base class.
    Base expression view class which describes how expression is represented on
    timeline.
    """

    # constants
    TARGET_VIEW = 1

    def __init__(self, expression_view_type: Optional[int] = None, expression: Optional["Expression"] = None):
        self.expression_view_type: Optional[int] = expression_view_type
        self.expression: Optional[Expression] = expression

    @staticmethod
    def create_expression_view(expression_view_type: int):
        """
        Factory method for building expression view objects instances based
        on object_type.
        """

        if expression_view_type == ExpressionView.TARGET_VIEW:
            return TargetExpView()
        return None

    def __str__(self):
        return f"{self.expression.name if self.expression else ''}_{self.get_type_as_string()}"

    def get_type_as_string(self) -> str:
        """
        Gets expression view object_type as string representation.

        @return Type string representation. (string)
        """

        if self.expression_view_type == ExpressionView.TARGET_VIEW:
            return "targetView"
        return ""

    def get_related_expressions(self) -> List["Expression"]:
        """
        Gets list of expressions which participate in view besides main expression.

        @return List of related expressions. (Expression[])
        """

        return []

    def get_view_data(self, start_frame: int = 0) -> List[ViewData]:  # dead: disable # pylint: disable=unused-argument
        """
        Gets data how expression should be representet on timeline.

        @param start_frame: Frame number from which expression have to be shown. (int)
        @return List of ViewData objects containing data on which frame should
            go which expression and with wich multiplier. (ViewData[])
        """

        return []

    def get_simple_view_data(
        self, start_frame: int = 0
    ) -> List[ViewData]:  # dead: disable# pylint: disable=unused-argument
        """
        Gets simple data (without phases) how expression should be representet on timeline.

        @param start_frame: Frame number from which expression have to be shown. (int)
        @return List of ViewData objects containing data on which frame should
            go which expression and with wich multiplier. (ViewData[])
        """

        return []

    def get_active_expression(
        self, start_frame: int = 0
    ) -> Optional["ActiveExpression"]:  # dead: disable # pylint: disable=unused-argument
        """
        Gets ActiveExpression object instance for expression.

        @param start_frame: Start frame of expression. (int)
        @return Active expression. (ActiveExpression)
        """

        return None

    def remove_expression(self, expression_name: str):
        """
        Remove expression with given pattern from expression view.

        @param expression_name: Name of expression to remove. (pattern)
        """


class TargetExpView(ExpressionView):
    """
    Expression view which defines in between expression which is being turned
    on on timeline between neutral and expression pose.
    For example, when we moddel open smile, we want to see expression changing
    from neutral to smile to smile open. In that case we want to add smile as
    expression view on smile open expression.

    @see ExpressionView
    @see ExpressionInView
    """

    def __init__(self, expression: Optional["Expression"] = None):
        super().__init__(ExpressionView.TARGET_VIEW, expression)
        self.expressions_in_view: List[ExpressionInView] = []  # (ExpressionInView[])

    def get_related_expressions(self) -> List["Expression"]:
        """
        Gets all related expressions which participate in expression view.

        @return List of related expressions. (Expression[])
        @see ExpressionView#getRelatedExpressions
        """

        related_expressions = []
        for eiv in self.expressions_in_view:
            related_expressions.append(eiv.expression)
        return related_expressions

    def get_expression_start_frame(self) -> int:
        if not self.expressions_in_view:
            return 0
        return self.expressions_in_view[-1].frame

    def get_view_data(self, start_frame: int = 0) -> List[ViewData]:
        """
        @see ExpressionView#getViewData
        """

        view_datas: List[ViewData] = []

        # get related expression data
        previous_offset = 0
        for exp_in_view in self.expressions_in_view:
            given_range = exp_in_view.frame - previous_offset
            current_range = exp_in_view.expression.get_expression_range()
            coef = given_range / float(current_range * exp_in_view.multiplier)
            for phase in exp_in_view.expression.phases:
                new_phase = previous_offset + coef * phase
                if new_phase <= exp_in_view.frame:
                    view_datas.append(
                        ViewData(start_frame + new_phase, exp_in_view.expression, phase / float(current_range))
                    )
                if new_phase == exp_in_view.frame:
                    break
                if new_phase > exp_in_view.frame:
                    view_datas.append(
                        ViewData(start_frame + exp_in_view.frame, exp_in_view.expression, exp_in_view.multiplier)
                    )
                    break
            previous_offset = exp_in_view.frame

        # get main expression data
        assert self.expression is not None
        previous_offset = self.get_expression_start_frame()
        given_range = self.expression.get_expression_range() - previous_offset
        current_range = self.expression.get_expression_range()
        coef = given_range / float(current_range)
        for phase in self.expression.phases:
            new_phase = int(previous_offset + coef * phase)
            view_datas.append(ViewData(start_frame + new_phase, self.expression, phase / float(current_range)))

        return view_datas

    def get_simple_view_data(self, start_frame: int = 0) -> List[ViewData]:
        """
        @see ExpressionView#getSimpleViewData
        """

        view_datas: List[ViewData] = []

        # get related expression data
        for exp_in_view in self.expressions_in_view:
            view_datas.append(ViewData(start_frame + exp_in_view.frame, exp_in_view.expression, exp_in_view.multiplier))
        return view_datas

    def get_active_expression(self, start_frame: int = 0) -> "ActiveExpression":
        """
        @see ExpressionView#getActiveExpression
        """
        from frt_api.model.rig_definition.expression import ActiveExpression

        assert self.expression is not None
        active_exp = ActiveExpression(self.expression)
        active_exp.start_frame = start_frame
        active_exp.expression_start_frame = start_frame + self.get_expression_start_frame()
        active_exp.expression_end_frame = start_frame + self.expression.get_expression_range()
        coef = (active_exp.expression_end_frame - active_exp.expression_start_frame) / float(
            self.expression.get_expression_range()
        )
        for phase in self.expression.phases:
            active_exp.phase_frames.append(int(active_exp.expression_start_frame + coef * phase))
        active_exp.neutral_end_frame = active_exp.expression_end_frame + self.expression.neutral_range
        return active_exp

    def set_expressions_in_view(self, expression_in_views: List[ExpressionView]):
        """
        Sorts and sets expressions in view.

        @param expression_in_views: List of ExpressionInView objects. (ExpressionInView[])
        """

        self.expressions_in_view = sorted(expression_in_views, key=lambda eiv: eiv.frame)  # type: ignore

    def remove_expression(self, expression_name: str):
        """
        Remove expression with given pattern from expression view.

        @param expression_name: Name of expression to remove. (pattern)
        """

        eivs_to_remove = []
        for eiv in self.expressions_in_view:
            if eiv.expression.name == expression_name:
                eivs_to_remove.append(eiv)
        for eiv in eivs_to_remove:
            self.expressions_in_view.remove(eiv)


@dataclass
class ExpressionInView:
    """
    Class which holds expression in view data.

    It describes which expression should be assembled on which frame with whic
    multiplier.
    """

    expression: Any = None
    frame: int = 0
    multiplier: float = 1.0
