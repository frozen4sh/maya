# Copyright Epic Games, Inc. All Rights Reserved.

import re
from typing import Dict, List, Tuple, Optional

from .core import RangeFloatAttr
from .mesh import MeshInExpression
from .view import ViewData, ExpressionView
from .animated_maps import MapInExpression
from .expression_function import (
    DifferenceExpFunc,
    Difference2ExpFunc,
    ExpressionFunction,
)


class Expression:
    """
    Represent single facial expression.
    In order to achive that facial expression, expression class has to know
    how to move joints, how to turn on blend shape, which wrinkle mask should
    be turned on and how fast these things would be turned on.
    Also some expressions know how can they be calculated from other expressions.

    Attributes:
        id (long): Expression database index.
        name (string): Expression pattern.
        type (int): Expression object_type. (main, derived, complex, target, corrective)
        phases (int[]): Frames on which expression phases will be assembled.
        neutral_range: Number of frames between this expression and next when assembled on timeline.
        expression_attrs (RangeFloatAttr[]): List of attributes which drive expression.
        dirty (boolean): Indicates if expression is dirty.
        assemble_to_rig (boolean): Indicates if expression will be assembled to rig.
        sdk_file_path (string): File path to expression sdk file.
        hasSDK (boolean): Indicates if expression has sdk file sved.
        rig_definition (RigDefinition): Parent rig definition.
        meshes_in_expression (MeshInExpression[]): List of meshes which are changed by this expression.
        maps_in_expression (MapInExpression[]): List of maps which are changed by this expression.
        generates (Expression[]): List of expressions which are dependent on this expression.
        function (ExpressionFunction): Data how expression is calculated from other expressions.
        view (ExpressionView): Data how expression will be assembled on timelin.
    """

    _DIGITS: int = 3
    _PHASE_MULT_DIGITS: int = 3
    MAIN_EXPRESSION: int = 1
    DERIVED_EXPRESSION: int = 2
    COMPLEXPOSE_EXPRESSION: int = 3
    CORRECTIVETARGET_EXPRESSION: int = 4
    CORRECTIVE_EXPRESSION: int = 5

    def __init__(self):
        self.id: int = 0
        self.name: str = ""
        self.type: int = self.MAIN_EXPRESSION
        self.phases: List[int] = []
        self.neutral_range: int = 0
        self.expression_attrs: List[RangeFloatAttr] = []  # (RangeFloatAttr[])
        self.dirty: bool = False
        self.assemble_to_rig: int = 0
        self.sdk_file_path: str = ""
        self._has_sdk: Optional[bool] = None
        self.meshes_in_expression: List[MeshInExpression] = []  # (MeshInExpression[])
        self.maps_in_expression: List[MapInExpression] = []  # (MapInExpression[])
        self.generates: List[Expression] = []  # (Expression[])
        self.function: Optional[ExpressionFunction] = None  # (ExpressionFunction)
        self.view: Optional[ExpressionView] = None  # (ExpressionView)
        self.marked: bool = False

    def __str__(self):
        return self.name

    @property
    def has_sdk(self):
        if self._has_sdk is None:
            self._has_sdk = False
        return self._has_sdk

    @has_sdk.setter
    def has_sdk(self, value):
        self._has_sdk = value

    def is_psd_expression(self) -> bool:
        """
        Indicates if expression is part of some psd definition.

        @return Indicator if expression is partof some psd definition. (boolean)
        """

        return self.type in (
            Expression.COMPLEXPOSE_EXPRESSION,
            Expression.CORRECTIVETARGET_EXPRESSION,
            Expression.CORRECTIVE_EXPRESSION,
        )

    def get_expression_range(self) -> int:
        """
        Gets expression range.
        """

        return self.phases[-1]

    def get_bs_channel_name(self, phase_no: int, new_exp_name: str = "") -> str:
        """
        Gets blend shape channel pattern for given phase no.

        @param phase_no: Phase number. (int)
        @param new_exp_name: Name to be used instead of expression pattern. (string)
        @return Blend shape channel pattern. (string)
        """

        if not new_exp_name:
            new_exp_name = self.name
        if len(self.phases) == 1:
            return new_exp_name
        return f"{new_exp_name}{phase_no}"

    def no_phases(self) -> int:
        """
        Gets number of phases expression has.

        @return Number of phases. (int)
        """

        return len(self.phases)

    def get_phase_numbers(self) -> List[int]:
        """
        Gets list of phase numbers.

        For example, for phases [10, 20, 30, 40] result will be [1, 2, 3, 4].
        @return One based list of phase numbers. (int[])
        """

        return list(range(1, len(self.phases) + 1))

    def get_phases_as_string(self) -> str:
        """
        Gets phases string.

        For example, for phases [10, 20, 30, 40] result will be "10, 20, 30, 40".
        @return Phases string. (pattern)
        """

        no_phases = self.no_phases()
        if not no_phases:
            return ""

        return_string = str(self.phases[0])
        for i in range(1, no_phases):
            return_string = return_string + ", " + str(self.phases[i])
        return return_string

    def get_phase_multipliers(self) -> List[float]:
        """
        Gets expression phases represented as multipliers whether than as frames.

        For example, phases [10, 20, 30, 40] will be represented as [0.25, 0.5, 0.75, 1].
        @return Phase multipliers representation. (float[])
        """

        expression_range = float(self.get_expression_range())
        phase_multipliers = []
        for phase in self.phases:
            phase_multipliers.append(round(phase / expression_range, Expression._PHASE_MULT_DIGITS))
        return phase_multipliers

    def get_expression_for_multiplier(self, multiplier: float) -> List[Tuple[int, float]]:
        """
        Gets data how expression should look like for given multiplier.

        For example, if expression has phases 10, 30, 40, for multiplier 0.375 (frame 15),
        return value would be [(1, 0.75), (2, 0.25)].
        That means that expression for multiplier 0.375 is contained of phases 1 and 2 (one based index)
        where phase 1 is with intensity 0.75, and pase 2 is with intensity 0.25.
        @param multiplier: Expression multiplier. (float)
        @return List of pairs (one based phase index, phase multiplier). ([(int, float), ])
        """

        phase_mult = self.get_phase_multipliers()
        if multiplier in phase_mult:
            return [(phase_mult.index(multiplier) + 1, 1.0)]
        if multiplier < phase_mult[0]:
            return [(1, multiplier / phase_mult[0])]
        for i in range(len(phase_mult) - 1):
            start_mult = phase_mult[i]
            end_mult = phase_mult[i + 1]
            if start_mult < multiplier < end_mult:
                start_temp = 1 - ((multiplier - start_mult) / (end_mult - start_mult))
                end_temp = (multiplier - start_mult) / (end_mult - start_mult)
                return [(i + 1, start_temp), (i + 2, end_temp)]
        return [(len(phase_mult), 1.0)]

    def get_view_data(self, start_frame: int = 0, ignore_view: bool = False) -> List[ViewData]:
        """
        Gets data how expression should be representet on timeline.

        @param start_frame: Frame number from which expression have to be shown. (int)
        @param ignore_view: Indicates if view data should be ignored. (boolean)
        @return List of ViewData objects containing data on which frame should go which expression and with wich multiplier. (ViewData[])
        """

        if self.view and not ignore_view:
            return self.view.get_view_data(start_frame)

        view_datas = []
        phase_mult = self.get_phase_multipliers()
        for i, phase in enumerate(self.phases):
            view_data = ViewData(start_frame + phase, self, phase_mult[i])
            view_datas.append(view_data)
        return view_datas

    def get_simple_view_data(self, start_frame=0, ignore_view=False):
        """
        Gets simple data (without phases) how expression should be representet on timeline.

        @param start_frame: Frame number from which expression have to be shown. (int)
        @param ignore_view: Indicates if view data should be ignored. (boolean)
        @return List of ViewData objects containing data on which frame should go which expression and with wich multiplier. (ViewData[])
        """

        if self.view and not ignore_view:
            return self.view.get_simple_view_data(start_frame)
        return []

    def get_active_expression(self, start_frame=0, ignore_view=False):
        """
        Gets ActiveExpression object instance for expression.

        @param start_frame: Start frame of expression. (int)
        @param ignore_view: Indicates if view data should be ignored. (boolean)
        @return Active expression. (ActiveExpression)
        """

        if self.view and not ignore_view:
            return self.view.get_active_expression(start_frame)

        active_exp = ActiveExpression(self)
        active_exp.start_frame = start_frame
        active_exp.expression_start_frame = start_frame
        active_exp.expression_end_frame = start_frame + self.get_expression_range()
        for phase in self.phases:
            active_exp.phase_frames.append(start_frame + phase)
        active_exp.neutral_end_frame = active_exp.expression_end_frame + self.neutral_range
        return active_exp

    def parse_phases(self, phases_str):
        """
        Parses phases string, and if successfully parsed, new phases are set.

        @param phases_str: Phases string. (string)
        @return Returns success indicator.
        """

        phases = Expression.parse_phases_string(phases_str)
        if phases is None:
            return False
        self.phases = sorted(phases)
        return True

    def is_dirty(self) -> bool:
        """
        Gets dirty flag.

        @return Dirty flag. (boolean)
        """

        return self.dirty

    def set_dirty_on(self, dirty_dict):
        """
        Marks expression as dirty.

        @param dirty_dict: Dictionary containing already set dirty espression names. ({string: None})
        @return List of expressions which became dirty. (Expression[])
        """

        if self.name in dirty_dict:
            return []
        self.dirty = True
        dirty_expressions = [self]
        dirty_dict[self.name] = None
        for exp in self.generates:
            dirty_expressions.extend(exp.set_dirty_on(dirty_dict))
        return dirty_expressions

    def get_mesh_in_expression(self, mesh_name):
        """
        Gets MeshInExpression for mesh pattern.

        @param mesh_name: Mesh pattern. (string)
        @return MeshInExpression if exists, otherwise None. (MeshInExpression)
        """

        for mie in self.meshes_in_expression:
            if mie.mesh and mie.mesh.name == mesh_name:
                return mie
        return None

    @staticmethod
    def parse_phases_string(in_string):
        """
        Parses phases string.

        Valid format is contained from numbers separated by commas.
        For example: 1,3,6,8.
        @param in_string: Phases string to be parsed. (string)
        @return List of integers if string is valid, otherwise None. (int[])
        """

        phases = []
        tokens = in_string.split(",")
        pattern = "^[0-9]*$"
        for token in tokens:
            token = token.strip()
            if not re.match(pattern, token):
                return None
            phases.append(int(token))
        return phases

    def get_attribute_by_name(self, control, attribute):
        """
        Gets expression attribute for given attribute pattern.

        @return Expression attribute. (RangeFloatAttr)
        """

        for attr in self.expression_attrs:
            if attr.object_name == control and attr.attr_name == attribute:
                return attr
        return None

    def get_description_str(self):
        """
        Gets description string which contains data about expression
        properties, view, dirty flag and pattern.

        @return Desription string. (string)
        """

        output_string = "P" if self.function else " "
        output_string += "V" if self.view else " "
        output_string += "D" if self.dirty else " "
        output_string += "  " + self.name
        return output_string

    def get_active_description_str(self):
        """
        Gets description string which contains data about expression
        properties and pattern.

        @return Desription string. (string)
        """

        output_string = "M" if self.marked else " "
        output_string += "  " + self.name
        return output_string

    def get_frame_for_multiplier(self, multiplier):
        """
        Get expressions frame equal to given multiplier.

        @param multiplier: Multiplier. (float)
        @return Frame number. (int)
        """

        return int(self.get_expression_range() * multiplier)

    def get_multiplier_for_frame(self, frame):
        """
        Get expressions multiplier equal to given frame.

        @param frame: Frame. (int)
        @return Multiplier. (float)
        """

        return float(frame) / self.get_expression_range()

    def get_generated_expressions_dict(
        self, expression_dict: Dict[str, "Expression"] = {}, include_targets: bool = False
    ):
        """
        Function will return dictionary of all expressions that are generated
        by self expression.

        If optional parametar dict is giving, same dictionary will be returned from function.
        @param expression_dict: Starting generated expressions dictionary. (dictionary)
        @param include_targets: Flag specifying if taget expressions from difference dependent expressions should be filtered too. (boolean)
        @return Generated expressions dictionary. (float)
        """

        if self.name not in expression_dict:
            expression_dict[self.name] = self
        if include_targets and self.function and self.function.function_type == ExpressionFunction.FUNCTION_DIFF:
            if isinstance(self.function, DifferenceExpFunc) and self.function.input2 and self.function.input1:
                if self.function.input2.name in expression_dict and self.function.input1.name not in expression_dict:
                    expression_dict[self.function.input1.name] = self.function.input1
        if include_targets and self.function and self.function.function_type == ExpressionFunction.FUNCTION_DIFF2:
            if isinstance(self.function, Difference2ExpFunc) and self.function.input2 and self.function.input1:
                if self.function.input2.name in expression_dict and self.function.input1.name not in expression_dict:
                    expression_dict[self.function.input1.name] = self.function.input1
        for exp in self.generates:
            exp.get_generated_expressions_dict(expression_dict, include_targets)
        return expression_dict

    def remove_expression(self, expression):
        """
        Remove expression from this expression.

        @param expression: Expression pattern. (string)
        """

        if self.view:
            self.view.remove_expression(expression.name)
        if self.function:
            if expression in self.function.get_input_expressions():
                self.function = None


class ExpressionsFilter:
    """
    Filter class by which list of expressions can be filtered.
    """

    def __init__(self):
        super().__init__()
        self.types = {
            Expression.MAIN_EXPRESSION: False,
            Expression.DERIVED_EXPRESSION: False,
            Expression.COMPLEXPOSE_EXPRESSION: False,
            Expression.CORRECTIVETARGET_EXPRESSION: False,
            Expression.CORRECTIVE_EXPRESSION: False,
        }
        self.filter_string: str = ""
        self.active: bool = False
        self.active_dependent: bool = False
        self.include_targets: bool = False
        self.active_expressions: List[str] = []
        self.layer: int = 0  # layer 0 means all layers, 1 is layer 1, 2 is layer 2, etc.


class ActiveExpression:
    """
    Active expression class.
    """

    def __init__(self, expression: "Expression"):
        self.expression: Expression = expression
        self.start_frame: int = 0
        self.expression_start_frame: int = 0
        self.expression_end_frame: int = 0
        self.phase_frames: List[int] = []
        self.neutral_end_frame: int = 0
