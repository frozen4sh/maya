# Copyright Epic Games, Inc. All Rights Reserved.

from qtpy import QtCore, QtWidgets

from ..utils import ui


class FileChooser(QtWidgets.QWidget):
    """FileChooser.
    Custom file choose widget with drag and drop and open dialog button
    to select files needs for program
    """

    def __init__(
        self,
        label,
        parent=None,
        label_tool_tip=None,
        placeholder="",
        dialog_caption="Select a file:",
        dialog_filter="All files (*.*)",
        multi_files=False,
        dir_selector=False,
        minimum_width=None,
        on_changed=None,
        filename=None,
        allow_non_existent_files=False,
    ) -> None:
        super().__init__(parent=parent)

        # Defaults
        self.dialog_caption = dialog_caption
        self.dialog_filter = dialog_filter
        self.multi_files = multi_files
        self.dir_selector = dir_selector
        self.allow_non_existent_files = allow_non_existent_files
        self.dir_path = ""
        self.multi_files_len = 0
        self.setAcceptDrops(True)

        layout = QtWidgets.QHBoxLayout()

        # label
        self.fc_label = QtWidgets.QLabel(label)
        if label_tool_tip:
            self.fc_label.setToolTip(label_tool_tip)

        self.fc_label.setAcceptDrops(True)
        self.fc_label.dragEnterEvent = self.dragEnterEvent
        self.fc_label.dragMoveEvent = self.dragMoveEvent
        self.fc_label.dropEvent = self.dropEvent

        # input field
        self.fc_text_field = QtWidgets.QLineEdit()
        self.fc_text_field.setAlignment(QtCore.Qt.AlignLeft)
        self.fc_text_field.setDragEnabled(True)
        self.fc_text_field.setAcceptDrops(True)
        self.fc_text_field.dragEnterEvent = self.dragEnterEvent
        self.fc_text_field.dragMoveEvent = self.dragMoveEvent
        self.fc_text_field.dropEvent = self.dropEvent
        self.fc_text_field.setPlaceholderText(placeholder)
        if filename is not None:
            self.fc_text_field.setText(filename)
        self.fc_text_field.textChanged.connect(on_changed)
        if minimum_width is not None:
            self.fc_text_field.setMinimumWidth(minimum_width)

        # button
        self.fc_btn = QtWidgets.QToolButton()
        ui.set_icon(self.fc_btn, "open_file.png")
        self.fc_btn.setAcceptDrops(True)
        self.fc_btn.dragEnterEvent = self.dragEnterEvent
        self.fc_btn.dragMoveEvent = self.dragMoveEvent
        self.fc_btn.dropEvent = self.dropEvent

        # layout
        layout.addWidget(self.fc_label, alignment=QtCore.Qt.AlignVCenter)
        layout.addWidget(self.fc_text_field, alignment=QtCore.Qt.AlignVCenter, stretch=3)
        layout.addWidget(self.fc_btn, alignment=QtCore.Qt.AlignVCenter)
        self.fc_btn.clicked.connect(
            self._open_dialog,
        )

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.setLayout(layout)

    def set_file_path(self, file_path):
        self.fc_text_field.blockSignals(True)
        self.fc_text_field.setText(file_path)
        self.fc_text_field.blockSignals(False)

    def set_dir_path(self, dir_path):
        self.dir_path = dir_path

    def get_file_path(self):
        return self.fc_text_field.text()

    def is_empty(self):
        return self.fc_text_field.text() == ""

    def get_label_text(self):
        return self.fc_label.text()

    def get_number_of_inputs(self):
        return self.multi_files_len

    def _open_dialog(self):
        self.set_file_path("")
        if self.multi_files:
            path = QtWidgets.QFileDialog.getOpenFileNames(self, self.dialog_caption, self.dir_path, self.dialog_filter)
            if path != ("", ""):
                self.fc_text_field.setText(",".join(path[0]))
        if not self.multi_files and not self.dir_selector:
            if self.allow_non_existent_files:
                path = QtWidgets.QFileDialog.getSaveFileName(
                    self, self.dialog_caption, self.dir_path, self.dialog_filter
                )
            else:
                path = QtWidgets.QFileDialog.getOpenFileName(
                    self, self.dialog_caption, self.dir_path, self.dialog_filter
                )
            if path != ("", ""):
                self.fc_text_field.setText(path[0])
        if self.dir_selector:
            path = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.dialog_caption,
                "",
                QtWidgets.QFileDialog.Option.ShowDirsOnly,
            )
            if path != ("", ""):
                self.fc_text_field.setText(path)

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
                self.set_file_path("")
                if self.multi_files:
                    self.multi_files_len = len(files)
                    self.fc_text_field.setText(",".join(files))
                else:
                    self.fc_text_field.setText(files[0])
