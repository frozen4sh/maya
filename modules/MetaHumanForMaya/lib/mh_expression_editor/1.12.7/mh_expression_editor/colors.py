# Copyright Epic Games, Inc. All Rights Reserved.
import qstyle
from qtpy import QtGui

# fmt: off
COLORS = {
    "border":       QtGui.QColor(qstyle.get_value("--gray020")),
    "text":         QtGui.QColor(qstyle.get_value("--text")),
    "gray":         QtGui.QColor(qstyle.get_value("--gray100")),
    "selected":     QtGui.QColor(qstyle.get_value("--selection")),
}
# fmt: on
