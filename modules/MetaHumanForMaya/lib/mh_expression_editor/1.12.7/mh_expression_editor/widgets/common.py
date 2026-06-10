# Copyright Epic Games, Inc. All Rights Reserved.

from qtpy import QtGui, QtCore, QtWidgets


class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setMaximumHeight(1)
        self.setProperty("line", True)


class QVLine(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setMaximumWidth(1)
        self.setProperty("line", True)


class QHSpacer(QtWidgets.QSpacerItem):
    def __init__(self):
        super().__init__(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)


class QVSpacer(QtWidgets.QSpacerItem):
    def __init__(self):
        super().__init__(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)


class ElidedLabel(QtWidgets.QLabel):
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(self.text(), QtCore.Qt.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)


class Section(QtWidgets.QWidget):
    def __init__(self, parent=None, title=None, collapsed=True, layout=None):
        super().__init__(parent=parent)
        self.is_collapsed = collapsed

        title_frame = TitleFrame(title=title, collapsed=self.is_collapsed)

        content_layout = layout or QtWidgets.QVBoxLayout()
        content = QtWidgets.QWidget(self)
        content.setLayout(content_layout)
        content.setVisible(not self.is_collapsed)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(4)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(title_frame)
        main_layout.addWidget(content)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(4)

        title_frame.clicked.connect(self.toggle_collapsed)

        self.controls = {
            "content": content,
            "title_frame": title_frame,
            "content_layout": content_layout,
            "arrow": title_frame.controls["arrow"],
        }

        title_frame.setObjectName("SectionTitle")
        content.setObjectName("SectionContent")

    def set_title(self, title):
        self.controls["title_frame"].set_title(title)

    def title(self):
        return self.controls["title_frame"].title()

    def addWidget(self, widget):
        self.controls["content_layout"].addWidget(widget)

    def addLayout(self, layout):
        self.controls["content_layout"].addLayout(layout)

    def addItem(self, item):
        self.controls["content_layout"].addItem(item)

    def toggle_collapsed(self):
        self.controls["content"].setVisible(self.is_collapsed)
        self.is_collapsed = not self.is_collapsed
        self.controls["arrow"].set_arrow_direction(int(self.is_collapsed))

    def clear_content(self):
        items_removed = []
        while self.controls["content_layout"].count() > 0:
            items_removed.append(self.controls["content_layout"].takeAt(0))
        return items_removed

    def collapse(self):
        self.controls["content"].setVisible(False)
        self.is_collapsed = True
        self.controls["arrow"].set_arrow_direction(True)

    def widget_count(self):
        return self.controls["content_layout"].count()


class TitleFrame(QtWidgets.QFrame):
    clicked = QtCore.Signal()

    def __init__(self, parent=None, title="", collapsed=False):
        super().__init__(parent=parent)
        self.setFixedHeight(22)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        arrow = Arrow(collapsed=collapsed)
        title = QtWidgets.QLabel(title)
        title.setStyleSheet("font-weight: bold")

        layout.addWidget(arrow)
        layout.addWidget(title)

        self.controls = {
            "arrow": arrow,
            "title": title,
        }

    def mousePressEvent(self, event):
        self.clicked.emit()
        return super().mousePressEvent(event)

    def set_title(self, title):
        self.controls["title"].setText(title)

    def title(self):
        return self.controls["title"].text()


class Arrow(QtWidgets.QFrame):
    VERTICAL, HORIZONTAL = range(2)

    def __init__(self, parent=None, collapsed=False):
        super().__init__(parent=parent)
        self.setMaximumSize(24, 24)
        self.arrow = None
        self.set_arrow_direction(int(collapsed))

    def set_arrow_direction(self, direction):
        if direction == self.VERTICAL:
            self.arrow = (
                QtCore.QPointF(7.0, 8.0),
                QtCore.QPointF(17.0, 8.0),
                QtCore.QPointF(12.0, 13.0),
            )
        else:
            self.arrow = (
                QtCore.QPointF(8.0, 7.0),
                QtCore.QPointF(13.0, 12.0),
                QtCore.QPointF(8.0, 17.0),
            )

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setBrush(QtGui.QColor(192, 192, 192))
        painter.setPen(QtGui.QColor(64, 64, 64))
        painter.drawPolygon(self.arrow)
        painter.end()


class SearchableComboBox(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.filter_model = QtCore.QSortFilterProxyModel(self)
        self.filter_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.filter_model.setSourceModel(self.model())

        self.completer = QtWidgets.QCompleter(self)
        self.completer.setModel(self.filter_model)
        self.completer.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)

        self.setCompleter(self.completer)

        def _filter(text):
            self.filter_model.setFilterFixedString(str(text))

        self.lineEdit().textEdited.connect(_filter)
        self.completer.activated.connect(self.on_completer_activated)

    def on_completer_activated(self, text):
        if text and self.findText(str(text)):
            index = self.findText(str(text))
            self.setCurrentIndex(index)

    def setModel(self, model):
        super().setModel(model)
        self.filter_model.setSourceModel(model)
        self.completer.setModel(self.filter_model)

    def setModelColumn(self, column):
        self.completer.setCompletionColumn(column)
        self.filter_model.setFilterKeyColumn(column)
        super().setModelColumn(column)

    def addItems(self, items):
        self.clear()
        super().addItems(items)


class Question(QtWidgets.QMessageBox):
    def __init__(self, title, text, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.title = title
        self.text = text

    def ask(self):
        return self.question(
            self.parent,
            self.title,
            self.text,
            QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )


class CustomPropQComboBox(QtWidgets.QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.custom_item_list = []

    def populate_custom_list(self, custom_list):
        self.custom_item_list = custom_list


class LowerLODQuestion(QtWidgets.QMessageBox):
    WINDOW_TITLE = "Calculate Lower LODs"
    QUESTION_STRING = "Calculate lower LODs based on"
    WARNING_STRING = "Warning: This will also update affected meshes present in the scene."

    def __init__(self, lod_count, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(LowerLODQuestion.WINDOW_TITLE)
        self.setText(LowerLODQuestion.QUESTION_STRING)
        self.addButton(QtWidgets.QMessageBox.Yes)
        self.addButton(QtWidgets.QMessageBox.No)
        self.setIcon(QtWidgets.QMessageBox.Question)

        label = self.layout().takeAt(2).widget()
        self.text_layout = QtWidgets.QHBoxLayout(self)
        self.layout().addLayout(self.text_layout, 0, 2)
        self.text_layout.addWidget(label)
        self.combo_box = QtWidgets.QComboBox()
        for lod in range(lod_count):
            self.combo_box.addItem(f"LOD {lod}")
        self.text_layout.addWidget(self.combo_box)
        self.layout().addWidget(QtWidgets.QLabel(LowerLODQuestion.WARNING_STRING), 1, 2)

    def show(self):
        return self.exec_() == QtWidgets.QMessageBox.Yes

    @property
    def selected_lod(self):
        return int(self.combo_box.currentText()[-1])


class NamedSlider(QtWidgets.QWidget):
    def __init__(self, slider_name, min_value=0, max_value=10000, orientation=QtCore.Qt.Horizontal, parent=None):
        super().__init__(parent=parent)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        label_layout = QtWidgets.QHBoxLayout(self)
        label_layout.setSpacing(0)
        slider_name = QtWidgets.QLabel(slider_name)
        slider_name.setStyleSheet("font-weight: bold")
        label_layout.addWidget(slider_name)

        button_layout = QtWidgets.QHBoxLayout(self)
        button_layout.setContentsMargins(4, 0, 4, 0)
        button_layout.setSpacing(4)
        label_layout.addLayout(button_layout)

        slider = QtWidgets.QSlider(self)
        slider.setOrientation(orientation)
        slider.setRange(min_value, max_value)

        main_layout.addLayout(label_layout)
        main_layout.addWidget(slider)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)

        self.controls = {
            "main_layout": main_layout,
            "label_layout": label_layout,
            "button_layout": button_layout,
            "slider_name": slider_name,
            "slider": slider,
        }

        self.valueChanged = slider.valueChanged
        self.maximum = slider.maximum
        self.setValue = slider.setValue
        self.value = slider.value
        self.sliderPressed = slider.sliderPressed

    def deleteLater(self):
        self.controls["slider"].deleteLater()
        self.controls["slider_name"].deleteLater()
        self.controls["label_layout"].deleteLater()
        self.controls["main_layout"].deleteLater()

    def add_phase_buttons(self, on_previous_phase_button_clicked, on_next_phase_button_clicked):
        previous_phase_button = QtWidgets.QToolButton(self)
        previous_phase_button.setArrowType(QtCore.Qt.LeftArrow)
        next_phase_button = QtWidgets.QToolButton(self)
        next_phase_button.setArrowType(QtCore.Qt.RightArrow)
        self.controls["button_layout"].addWidget(previous_phase_button)
        self.controls["button_layout"].addWidget(next_phase_button)
        self.controls["previous_phase"] = previous_phase_button
        self.controls["next_phase"] = next_phase_button
        previous_phase_button.clicked.connect(on_previous_phase_button_clicked)
        next_phase_button.clicked.connect(on_next_phase_button_clicked)

    def set_phase_buttons_visible(self, state):
        self.controls["previous_phase"].setVisible(state)
        self.controls["next_phase"].setVisible(state)

    def set_slider_label(self, label):
        self.controls["slider_name"].setText(label)
