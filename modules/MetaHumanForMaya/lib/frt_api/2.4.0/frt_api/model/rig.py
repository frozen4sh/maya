# Copyright Epic Games, Inc. All Rights Reserved.


from typing import Optional
from dataclasses import dataclass


class Expression:
    """
    Represents expression as higher level of abstraction.
    """

    @staticmethod
    def get_expression_group(name):
        """
        Returns expression pattern first token which usually represents part of
        face rig, such as mouth, brows,...

        @param name: Expression pattern. (string)
        @return Rig group (part) pattern. (sting)
        """

        return name.split("_")[0]

    def __init__(self, name="", expression_type=1, from_value=0.0, to_value=0.0, group=None):
        self.name = name
        self.expression_type = expression_type
        self.from_value = from_value
        self.to_value = to_value
        if group:
            self.group = group
        else:
            self.group = Expression.get_expression_group(name)


class PlugInfo:
    """
    Base class representing plugable attribute which is described with its pattern,
    role and border values.
    """

    ROLE_TX = "TranslateX"
    ROLE_TY = "TranslateY"
    ROLE_TZ = "TranslateZ"
    ROLE_RX = "RotateX"
    ROLE_RY = "RotateY"
    ROLE_RZ = "RotateZ"
    ROLE_SX = "ScaleX"
    ROLE_SY = "ScaleY"
    ROLE_SZ = "ScaleZ"
    ROLE_CUSTOM = "Custom"

    @staticmethod
    def get_plug_role(attr_name):
        """
        Gets plug role based on attribute pattern.

        @param attr_name: Attribute pattern. (string)
        @return Role pattern. (string)
        """

        if attr_name in ("tx", "translateX"):
            return PlugInfo.ROLE_TX
        if attr_name in ("ty", "translateY"):
            return PlugInfo.ROLE_TY
        if attr_name in ("tz", "translateZ"):
            return PlugInfo.ROLE_TZ
        if attr_name in ("rx", "rotateX"):
            return PlugInfo.ROLE_RX
        if attr_name in ("ry", "rotateY"):
            return PlugInfo.ROLE_RY
        if attr_name in ("rz", "rotateZ"):
            return PlugInfo.ROLE_RZ
        if attr_name in ("sx", "scaleX"):
            return PlugInfo.ROLE_SX
        if attr_name in ("sy", "scaleY"):
            return PlugInfo.ROLE_SY
        if attr_name in ("sz", "scaleZ"):
            return PlugInfo.ROLE_SZ
        return PlugInfo.ROLE_CUSTOM

    def __init__(self, id=0, obj_name="", attr_name="", min_value=0.0, max_value=1.0, role=None):
        self.id = id
        self.obj_name = obj_name
        self.attr_name = attr_name
        self.min_value = min_value
        self.max_value = max_value
        if role:
            self.role = role
        else:
            self.role = PlugInfo.get_plug_role(attr_name)

    def get_full_name(self):
        return self.obj_name + "." + self.attr_name

    def get_interface_name(self):
        return self.obj_name + "__" + self.attr_name


class PlugInputValue(PlugInfo):
    """
    Rig logic input attribute.
    """

    TYPE_PLUG = 1
    TYPE_PSD = 2

    def __init__(self, id=0, obj_name="", attr_name="", min_value=0.0, max_value=1.0, role=None):
        super().__init__(id, obj_name, attr_name, min_value, max_value, role)
        self.type = PlugInputValue.TYPE_PLUG
        self.expressions = []

    def get_affected_by(self, affected_by):
        """
        Adds itself to affected_by list if not already in list.
        """

        if self not in affected_by:
            affected_by.append(self)


@dataclass
class RangedInputValue:
    """
    Input attribute with given range.
    """

    input: Optional[PlugInputValue] = None
    startValue: float = 0.0
    endValue: float = 0.0


class PsdInputValue(PlugInputValue):
    """
    Rig logic input PSD attribute.
    """

    def __init__(self, id=0, obj_name="", attr_name="", min_value=0.0, max_value=1.0, role=None, on_off_input=None):
        super().__init__(id, obj_name, attr_name, min_value, max_value, role)
        self.type = PlugInputValue.TYPE_PSD
        self.on_off_input = on_off_input
        self.ranged_inputs = []

    def get_affected_by(self, affected_by):
        """
        Adds inputs by which it is affected to affected_by list.
        """

        for ranged_input in self.ranged_inputs:
            ranged_input.input.get_affected_by(affected_by)
        self.on_off_input.get_affected_by(affected_by)
