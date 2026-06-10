# Copyright Epic Games, Inc. All Rights Reserved.

import logging

from qtpy import QtGui, QtCore, QtWidgets

from .constants import Color


class StatusObject(QtCore.QObject):
    changed = QtCore.Signal(str, int)


class StatusHandler(logging.Handler):
    def __init__(self, parent, emitter):
        super().__init__()
        self._emitter = emitter
        self.widget = StatusLine(parent)

        formatter = logging.Formatter("[%(levelname)s %(basename)s] %(message)s")
        self.setFormatter(formatter)

        self.emitter.changed.connect(self.widget.set_text)

    @property
    def emitter(self):
        return self._emitter

    def emit(self, record):
        record.basename = record.name.rsplit(".", 1)[-1]

        if record.levelname == "ERROR":
            level = StatusLine.ERROR
        elif record.levelname == "DEBUG":
            level = StatusLine.DEBUG
        elif record.levelname == "WARNING":
            level = StatusLine.WARNING
        else:
            level = StatusLine.INFO

        msg = record.getMessage()
        self.emitter.changed.emit(msg, level)


class StatusLine(QtWidgets.QLineEdit):
    (INFO, ERROR, DEBUG, WARNING) = range(4)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisabled(True)
        self._level = self.INFO
        self._parent = parent

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self.animation = QtCore.QPropertyAnimation(effect, b"opacity")
        self.animation.setDuration(5000)
        self.animation.setEasingCurve(QtCore.QEasingCurve(QtCore.QEasingCurve.InCubic))
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.textChanged.connect(self.fadeout)

    def fadeout(self, event):
        self.animation.stop()
        self.animation.updateCurrentValue(1.0)
        self.animation.start()

    def set_text(self, value, level=None):
        self.setText("")
        self._level = level or self.INFO
        self.setText(value)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        lenap = QtWidgets.QStyleOptionFrame()
        self.initStyleOption(lenap)
        backgroundRect = self.style().subElementRect(QtWidgets.QStyle.SE_LineEditContents, lenap, self)
        if self.text() != "":
            if self._level == self.ERROR:
                color = Color.RED
            elif self._level == self.DEBUG:
                color = Color.DISABLED
            elif self._level == self.WARNING:
                color = Color.YELLOW
            else:
                color = Color.TEXT
            qcolor = Color.qt(color)

            pen = QtGui.QPen(qcolor)
            painter.setPen(pen)
            painter.drawText(
                backgroundRect,
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
                self.text(),
            )
