# Copyright Epic Games, Inc. All Rights Reserved.

import math
from typing import Dict, List, Optional
from dataclasses import dataclass

from frt_api.model.rig_definition.core import RangeFloatAttr


@dataclass
class MayaAnimCurveAttribute:
    """
    Represents Maya animated curve attribute.
    """

    obj_name: Optional[str] = None
    attr_name: Optional[str] = None
    weight: Optional[float] = 1.0


class MayaAnimCurveKey:
    """
    Represents one key-frame (point) on animation curve.

    This is used to describe one value of driven key function.
    """

    # constants
    TANGENT_TYPE_FIXED = "fixed"

    def __init__(self):
        self.in_tangent_type: str = MayaAnimCurveKey.TANGENT_TYPE_FIXED
        self.out_tangent_type: str = MayaAnimCurveKey.TANGENT_TYPE_FIXED
        self.in_tangent: List[float] = [0.0, 0.0]
        self.out_tangent: List[float] = [0.0, 0.0]
        self.in_weight: float = 1.0
        self.out_weight: float = 1.0
        self.tangent_locked: bool = True
        self.time: float = 0.0
        self.unitless_input: float = 0.0
        self.value: float = 0.0
        self.weights_locked: bool = True
        self.breakdown: bool = False

    def shallow_copy(self) -> "MayaAnimCurveKey":
        """
        Copies MayaAnimCurveKey.

        @return Copied curve key. (MayaAnimCurveKey)
        """

        new_key = MayaAnimCurveKey()
        new_key.in_tangent_type = self.in_tangent_type
        new_key.out_tangent_type = self.out_tangent_type
        new_key.in_tangent = [self.in_tangent[0], self.in_tangent[1]]
        new_key.out_tangent = [self.out_tangent[0], self.out_tangent[1]]
        new_key.in_weight = self.in_weight
        new_key.out_weight = self.out_weight
        new_key.tangent_locked = self.tangent_locked
        new_key.time = self.time
        new_key.unitless_input = self.unitless_input
        new_key.value = self.value
        new_key.weights_locked = self.weights_locked
        new_key.breakdown = self.breakdown
        return new_key


class MayaAnimCurve:
    """
    Represents animation curve of driven key.
    """

    # Constants
    AC_TYPES_TIME = ("TL", "TA", "TT", "TU")
    AC_TYPES_DOUBLE = ("UL", "UA", "UT", "UU")

    MEANING_JOINT = "jnt"
    MEANING_MASK = "mask"

    def __init__(self):
        self.name: str = ""
        self.input: Optional[MayaAnimCurveAttribute] = None
        self.input_min: float = 0.0
        self.input_max: float = 0.0
        self.outputs: List[MayaAnimCurveAttribute] = []

        self.meaning = None
        self.anim_curve_type: str = ""
        self.weighted: bool = False
        self.keys: List[MayaAnimCurveKey] = []

    def shallow_copy(self) -> "MayaAnimCurve":
        """
        Copies MayaAnimCurve as a deep copy.

        @return Copied animation curve. (MayaAnimCurve)
        """

        new_ac = MayaAnimCurve()
        new_ac.name = self.name
        if self.input:
            new_ac.input = MayaAnimCurveAttribute(
                obj_name=self.input.obj_name, attr_name=self.input.attr_name, weight=self.input.weight
            )
        new_ac.input_min = self.input_min
        new_ac.input_max = self.input_max
        for output in self.outputs:
            new_ac.outputs.append(
                MayaAnimCurveAttribute(obj_name=output.obj_name, attr_name=output.attr_name, weight=output.weight)
            )

        new_ac.meaning = self.meaning
        new_ac.anim_curve_type = self.anim_curve_type
        new_ac.weighted = self.weighted

        for key in self.keys:
            new_ac.keys.append(key.shallow_copy())
        return new_ac

    def scale_time(self, k: float):
        """
        Scales animated curve time horizontally, by coefficient k.

        @param k: Scale coefficient. (float)
        """

        for key in self.keys:
            key.time = round(k * key.time)

    def scale_unitless_input(self, k):
        """
        Scales animated curve unitless input horizontally, by coefficient k.

        @param k: Scale coefficient. (float)
        """

        for key in self.keys:
            key.unitless_input *= k

    def reverse_tangents(self):
        """
        Reverses tangents for all keys.
        Input tangents become output tangents and other way around.
        """

        for key in self.keys:
            key.in_tangent, key.out_tangent = key.out_tangent, key.in_tangent
            key.in_tangent_type, key.out_tangent_type = key.out_tangent_type, key.in_tangent_type
            key.in_weight, key.out_weight = key.out_weight, key.in_weight

    def scale_tangents_horizontal(self, k: float):
        """
        Scales animated curves tangents, horizontally, by coefficient k.

        @param k: Scale coefficient. (float)
        """

        for key in self.keys:
            if key.in_tangent[1]:
                tan = key.in_tangent[0] * k / key.in_tangent[1]
                pow_y = 1 / (1 + pow(tan, 2))
                y = math.sqrt(pow_y)
                x = math.sqrt(1 - pow_y)
                key.in_tangent = [x, y]

            if key.out_tangent[1]:
                tan = key.out_tangent[0] * k / key.out_tangent[1]
                pow_y = 1 / (1 + pow(tan, 2))
                y = math.sqrt(pow_y)
                x = math.sqrt(1 - pow_y)
                key.out_tangent = [x, y]

    def copy_for_timeline_assemble(self, time_span: int, delta_time: int = 0, hor_scale: float = 1.0):
        """
        Creates copy of animated curve and changes its data for time line assemble.

        @param time_span: Time span for which curve copy has to be prepared. (int)
        @param delta_time: Integer indicating first frame of expression. (int)
        @param hor_scale: Horizontal scale factor. (float)
        @return Prepared animated curve. (AnimCurve)
        """

        anim_curve = self.shallow_copy()
        anim_curve.scale_time(hor_scale)
        anim_curve.scale_tangents_horizontal(hor_scale)
        keys = anim_curve.keys
        anim_curve.keys = []
        for key in keys:
            if key.time <= time_span:
                key.time += delta_time
                anim_curve.keys.append(key)
        return anim_curve

    def copy_for_interface_assemble(
        self, exp_attr: RangeFloatAttr, joints_naming: Dict[str, str], delta_value: float = 0.0, hor_scale: float = 1.0
    ) -> "MayaAnimCurve":
        """
        Creates copy of animated curve and changes its data for interface assemble.

        @param exp_attr: Driver expression attribute. (RangeFloatAttr)
        @param joints_naming: Dictionary containing joints naming mappings. ({string: string})
        @param delta_value: Driver attribute neutral value. (float)
        @param hor_scale: Horizontal scale factor. (float)
        @return Prepared animated curve. (AnimCurve)
        """

        anim_curve: MayaAnimCurve = self.shallow_copy()
        anim_curve.anim_curve_type = anim_curve.anim_curve_type.replace("T", "U", 1)
        anim_curve.input = MayaAnimCurveAttribute(exp_attr.object_name, exp_attr.attr_name)
        anim_curve.scale_unitless_input(hor_scale)
        anim_curve.scale_tangents_horizontal(abs(hor_scale))

        if anim_curve.meaning == MayaAnimCurve.MEANING_JOINT:
            for output in anim_curve.outputs:
                if output.obj_name in joints_naming:
                    output.obj_name = joints_naming[output.obj_name]

        if exp_attr.is_negative_oriented():
            anim_curve.reverse_tangents()
        for key in anim_curve.keys:
            key.value -= delta_value
        return anim_curve
