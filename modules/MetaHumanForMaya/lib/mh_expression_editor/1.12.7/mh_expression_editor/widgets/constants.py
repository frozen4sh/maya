# Copyright Epic Games, Inc. All Rights Reserved.

from enum import Enum

from qtpy import QtGui


class Color(Enum):
    RED = (238, 96, 85, 255)
    GREEN = (131, 211, 96, 255)
    BLUE = (96, 161, 211, 255)
    LIGHT_GREEN = (170, 246, 131, 200)
    YELLOW = (255, 217, 125, 255)
    PINK = (255, 155, 133, 255)
    DISABLED = (175, 175, 175, 50)
    TEXT = (220, 220, 220, 255)

    @staticmethod
    def qt(value):
        return QtGui.QColor(*value.value)
