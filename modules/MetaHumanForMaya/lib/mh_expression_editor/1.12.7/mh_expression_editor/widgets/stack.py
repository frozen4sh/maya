# Copyright Epic Games, Inc. All Rights Reserved.

from qtpy import QtCore, QtWidgets

from ..utils import ui, general
from .common import QHLine, QVLine, ElidedLabel

logger = general.get_logger()


class SlidingStackedWidget(QtWidgets.QStackedWidget):
    animationFinished = QtCore.Signal()
    LeftToRight, RightToLeft, TopToBottom, BottomToTop, Automatic = range(5)

    def __init__(self, parent=None, vertical_mode=False):
        super().__init__(parent)
        self.animation_easing_curve = QtCore.QEasingCurve.OutExpo
        self.animation_duration = 500
        self.vertical_mode = vertical_mode
        self.wrap = False
        self._active = False
        self._animation_group = QtCore.QParallelAnimationGroup()
        self._animation_group.finished.connect(self._animation_group_finished)

    def slide_next(self):
        next_index = self.currentIndex() + 1
        if self.wrap or next_index < self.count():
            self.slide_index(
                next_index % self.count(),
                direction=self.BottomToTop if self.vertical_mode else self.RightToLeft,
            )

    def slide_prev(self):
        previous_index = self.currentIndex() - 1
        if self.wrap or previous_index >= 0:
            self.slide_index(
                previous_index % self.count(),
                direction=self.TopToBottom if self.vertical_mode else self.LeftToRight,
            )

    def slide_index(self, index, direction=Automatic):
        self.slide_widget(self.widget(index), direction)

    def slide_widget(self, widget, direction=Automatic):
        if self.indexOf(widget) == -1 or widget is self.currentWidget():
            return

        if self._active:
            return

        self._active = True

        prev_widget = self.currentWidget()
        next_widget = widget

        if direction == self.Automatic:
            if self.indexOf(prev_widget) < self.indexOf(next_widget):
                direction = self.BottomToTop if self.vertical_mode else self.RightToLeft
            else:
                direction = self.TopToBottom if self.vertical_mode else self.LeftToRight

        width = self.frameRect().width()
        height = self.frameRect().height()

        # the following is important, to ensure that the new widget has correct geometry information
        # when sliding in the first time
        next_widget.setGeometry(0, 0, width, height)

        if direction in (self.TopToBottom, self.BottomToTop):
            offset = QtCore.QPoint(0, height if direction == self.TopToBottom else -height)
        elif direction in (self.LeftToRight, self.RightToLeft):
            offset = QtCore.QPoint(width if direction == self.LeftToRight else -width, 0)
        else:
            offset = 0

        # re-position the next widget outside of the display area
        prev_widget_position = prev_widget.pos()
        next_widget_position = next_widget.pos()

        next_widget.move(next_widget_position - offset)
        next_widget.show()
        next_widget.raise_()

        prev_widget_animation = QtCore.QPropertyAnimation(prev_widget, b"pos")
        prev_widget_animation.setDuration(self.animation_duration)
        prev_widget_animation.setEasingCurve(QtCore.QEasingCurve(self.animation_easing_curve))
        prev_widget_animation.setStartValue(prev_widget_position)
        prev_widget_animation.setEndValue(prev_widget_position + offset)

        next_widget_animation = QtCore.QPropertyAnimation(next_widget, b"pos")
        next_widget_animation.setDuration(self.animation_duration)
        next_widget_animation.setEasingCurve(QtCore.QEasingCurve(self.animation_easing_curve))
        next_widget_animation.setStartValue(next_widget_position - offset)
        next_widget_animation.setEndValue(next_widget_position)

        self._animation_group.clear()
        self._animation_group.addAnimation(prev_widget_animation)
        self._animation_group.addAnimation(next_widget_animation)
        self._animation_group.start()

    def _animation_group_finished(self):
        prev_widget_animation = self._animation_group.animationAt(0)
        next_widget_animation = self._animation_group.animationAt(1)
        prev_widget = prev_widget_animation.targetObject()
        next_widget = next_widget_animation.targetObject()
        self.setCurrentWidget(next_widget)
        prev_widget.hide()

        # move the out-shifted widget back to its original position
        prev_widget.move(prev_widget_animation.startValue())
        self._animation_group.clear()
        self._active = False
        self.animationFinished.emit()


class Toolbar(SlidingStackedWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []
        self.buttons = {}
        self.add_page()
        if self.vertical_mode:
            self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        else:
            self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)

    @property
    def page_count(self):
        return len(self.pages)

    def get_button(self, name):
        return self.buttons.get(name)

    def add_page(self):
        if self.vertical_mode:
            layout = QtWidgets.QVBoxLayout()
            layout.setAlignment(QtCore.Qt.AlignTop)
        else:
            layout = QtWidgets.QHBoxLayout()
            layout.setAlignment(QtCore.Qt.AlignRight)
        page = QtWidgets.QWidget(self)
        page.setLayout(layout)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        self.pages.append(page)
        self.addWidget(page)

    def add_tool(self, name, icon, tooltip, page=0, highlight=False):
        if self.page_count < (page + 1):
            for _ in range(self.page_count, page + 1):
                self.add_page()

        btn = QtWidgets.QToolButton(self)
        if highlight:
            btn.setProperty("highlight", True)
        ui.set_icon(btn, icon)
        btn.setToolTip(tooltip)

        self.buttons[name] = btn

        page_layout = self.pages[page].layout()
        page_layout.addWidget(btn)
        return btn

    def add_separator(self, page):
        page_layout = self.pages[page].layout()
        separator = QHLine() if self.vertical_mode else QVLine()
        separator.setProperty("separator", True)
        if self.vertical_mode:
            separator.setMaximumHeight(2)
        else:
            separator.setMaximumWidth(2)
        return page_layout.addWidget(separator)

    def set_page(self, page):
        self.slide_index(page, direction=self.TopToBottom)


class BusyIndicatorFrame(QtWidgets.QFrame):
    def __init__(self, parent=None, show_progress=False, width=300):
        super().__init__(parent)

        self._parent = parent
        self._show_progress = show_progress
        self._width = width

        self.data = dict()
        self.setupUI()

    def setupUI(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        text_layout = QtWidgets.QVBoxLayout(self)

        title_label = QtWidgets.QLabel(self)
        title_label.setObjectName("BusyTitle")
        title_label.setText("Please wait...")

        message_label = ElidedLabel(self)
        message_label.setText("This may take a few moments.")
        message_label.setObjectName("BusyMessage")

        body_frame = QtWidgets.QFrame(self)
        body_frame.setFixedWidth(self._width)
        body_frame.setObjectName("BusyFrame")

        text_layout.addWidget(title_label)
        text_layout.addWidget(message_label)
        text_layout.setContentsMargins(4, 4, 4, 4)
        text_layout.setSpacing(6)

        progress = QtWidgets.QProgressBar(self)
        progress.setFixedHeight(14)

        body_layout = QtWidgets.QVBoxLayout(body_frame)
        body_layout.addLayout(text_layout)
        body_layout.addWidget(progress)
        body_layout.setContentsMargins(10, 16, 10, 16)
        body_layout.setSpacing(10)

        main_layout.addWidget(body_frame, 0, QtCore.Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        self.setObjectName("BusyIndicatorFrame")

        self.data = {
            "title": title_label,
            "message": message_label,
            "progress": progress,
        }

        self.show_progress(self._show_progress)

    # --------------------------------------------------------------------------

    def set_title(self, value):
        if not isinstance(value, str):
            return
        self.data["title"].setText(value)
        QtWidgets.QApplication.processEvents()

    def set_message(self, value):
        if not isinstance(value, str):
            return

        self.data["message"].setText(value)

        # A very hacky way to force resize to take place
        self.data["message"].hide()
        self.data["message"].show()
        QtWidgets.QApplication.processEvents()

    def set_progress(self, value):
        if not isinstance(value, (int, float)):
            return
        self.data["progress"].setValue(value)
        QtWidgets.QApplication.processEvents()

    def show_progress(self, value):
        if not isinstance(value, bool):
            return

        progress = self.data["progress"]

        if value:
            progress.setVisible(True)
            progress.show()
        else:
            progress.setVisible(False)
            progress.hide()

    # --------------------------------------------------------------------------

    def start(self):
        self.show()
        self.setVisible(True)
        QtWidgets.QApplication.processEvents()

    def end(self):
        self.hide()
        self.setVisible(False)
        QtWidgets.QApplication.processEvents()
