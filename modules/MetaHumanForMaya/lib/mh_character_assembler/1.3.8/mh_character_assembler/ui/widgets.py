# Copyright Epic Games, Inc. All Rights Reserved.
from pathlib import Path

import qstyle
from qtpy import QtCore, QtGui, QtWidgets

material = qstyle.FontIcons("material")


class ThumbnailWidget(QtWidgets.QWidget):
    def __init__(
        self,
        image_file,
        parent=None,
        height=None,
        width=None,
        label=None,
    ):
        super().__init__(parent)
        self.label = label
        height = height or 100
        width = width or 100

        thumbnail = QtWidgets.QLabel()
        thumbnail.setScaledContents(True)
        thumbnail.setGeometry(QtCore.QRect(0, 0, width, height))
        thumbnail.setFixedSize(QtCore.QSize(height, width))
        thumbnail.setPixmap(QtGui.QPixmap(image_file))

        if label:
            thumb_lbl = QtWidgets.QLabel(thumbnail)
            thumb_lbl.setText(label)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(thumbnail)

        self.setLayout(layout)

    def get_value(self):
        return self.label

    def mousePressEvent(self, event):
        return super().mousePressEvent(event)


class FileChooser(QtWidgets.QWidget):
    """FileChooser.

    Custom file choose widget with drag and drop and open dialog button
    to select files needs for program
    """

    chosen = QtCore.Signal(str)

    (OPEN_DIRECTORY, OPEN_FILE, OPEN_FILES, SAVE_FILE) = range(4)

    def __init__(
        self,
        label_text,
        label_width=120,
        label_tool_tip=None,
        placeholder="",
        dialog_caption="Please select:",
        dialog_filter="All files (*.*)",
        minimum_width=None,
        on_changed=None,
        filename=None,
        mode=1,
        parent=None,
    ) -> None:
        super().__init__(parent=parent)

        # Defaults
        self.dialog = QtWidgets.QFileDialog(self)

        self.dialog_caption = dialog_caption
        self.dialog_filter = dialog_filter

        self.mode = mode

        self.dialog_options = None
        self.dialog_dir = None

        self.multi_files_len = 0
        self.setAcceptDrops(True)

        layout = QtWidgets.QHBoxLayout()

        # label
        self.label = QtWidgets.QLabel(label_text)
        if label_tool_tip:
            self.label.setToolTip(label_tool_tip)

        self.label.setAcceptDrops(True)
        self.label.dragEnterEvent = self.dragEnterEvent
        self.label.dragMoveEvent = self.dragMoveEvent
        self.label.dropEvent = self.dropEvent
        self.label.setMinimumWidth(label_width)

        # input field
        self.text_field = QtWidgets.QLineEdit()
        self.text_field.setAlignment(QtCore.Qt.AlignLeft)
        self.text_field.setDragEnabled(True)
        self.text_field.setAcceptDrops(True)
        self.text_field.dragEnterEvent = self.dragEnterEvent
        self.text_field.dragMoveEvent = self.dragMoveEvent
        self.text_field.dropEvent = self.dropEvent
        self.text_field.setPlaceholderText(placeholder)
        if filename is not None:
            self.text_field.setText(filename)
        self.text_field.textChanged.connect(on_changed)
        if minimum_width is not None:
            self.text_field.setMinimumWidth(minimum_width)

        # button
        self.button = QtWidgets.QToolButton()
        self.button.setText("Browse...")
        self.button.setIcon(material.icon("folder"))
        self.button.setAcceptDrops(True)
        self.button.dragEnterEvent = self.dragEnterEvent
        self.button.dragMoveEvent = self.dragMoveEvent
        self.button.dropEvent = self.dropEvent

        # layout
        layout.addWidget(self.label, alignment=QtCore.Qt.AlignVCenter)
        layout.addWidget(self.text_field, alignment=QtCore.Qt.AlignVCenter)
        layout.addWidget(self.button, alignment=QtCore.Qt.AlignVCenter)
        self.button.clicked.connect(self._open_dialog)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        # signals
        self.text_field.returnPressed.connect(self.onEnter)

    def clear(self):
        return self.text_field.clear()

    def get_value(self):
        return self.text_field.text()

    def set_value(self, value):
        return self.text_field.setText(value)

    def is_empty(self):
        return self.text_field.text() == ""

    def get_label_text(self):
        return self.label.text()

    def get_number_of_inputs(self):
        return self.multi_files_len

    def _open_dialog(self):
        kwargs = {
            "caption": self.dialog_caption,
            "dir": self.dialog_dir or "",
            "filter": self.dialog_filter,
            "options": self.dialog_options or QtWidgets.QFileDialog.Options(),
        }

        filepath = None
        if self.mode == FileChooser.OPEN_DIRECTORY:
            kwargs.pop("filter")
            path = self.dialog.getExistingDirectory(None, **kwargs)
            if path != ("", ""):
                filepath = path
        elif self.mode == FileChooser.OPEN_FILE:
            path = self.dialog.getOpenFileName(None, **kwargs)
            if path != ("", ""):
                filepath = path[0]
        elif self.mode == FileChooser.OPEN_FILES:
            path = self.dialog.getOpenFileNames(None, **kwargs)
            if path != ("", ""):
                filepath = ",".join(path[0])
        elif self.mode == FileChooser.SAVE_FILE:
            path = self.dialog.getSaveFileName(None, **kwargs)
            if path != ("", ""):
                filepath = path[0]

        if filepath:
            self.text_field.setText(filepath)
            self.chosen.emit(filepath)

    def onEnter(self):
        filepath = self.text_field.text()
        if filepath and Path(filepath).exists():
            self.chosen.emit(filepath)

    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == "file":
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == "file":
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        files = []
        for url in urls:
            files.append(str(url.path())[1:])
        for url in urls:
            if url.scheme() == "file":
                if self.mode == FileChooser.OPEN_FILES:
                    self.multi_files_len = len(files)
                    self.text_field.setText(",".join(files))
                else:
                    self.text_field.setText(files[0])
