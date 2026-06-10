# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from functools import partial

# External
from qtpy import QtCore, QtWidgets

# Internal
from mh_pose_editor.model.settings import SettingsManager


class MirrorOptionsDialog(QtWidgets.QDialog):
    event_mirror_solver = QtCore.Signal(str, str, str, str, str, str, str, str, bool, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Mirror Options")
        self.setModal(False)

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        rot_axis_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(rot_axis_layout)

        rot_axis_label = QtWidgets.QLabel("Mirror Rotation Across:")
        rot_axis_layout.addWidget(rot_axis_label)

        rot_x_axis_button = QtWidgets.QRadioButton("X Axis")
        rot_x_axis_button.setChecked(True)
        rot_y_axis_button = QtWidgets.QRadioButton("Y Axis")
        rot_z_axis_button = QtWidgets.QRadioButton("Z Axis")

        rot_axis_layout.addWidget(rot_x_axis_button)
        rot_axis_layout.addWidget(rot_y_axis_button)
        rot_axis_layout.addWidget(rot_z_axis_button)

        self._rot_button_group = QtWidgets.QButtonGroup()
        self._rot_button_group.setExclusive(True)
        self._rot_button_group.addButton(rot_x_axis_button)
        self._rot_button_group.addButton(rot_y_axis_button)
        self._rot_button_group.addButton(rot_z_axis_button)
        self._rot_axis_buttons = [rot_x_axis_button, rot_y_axis_button, rot_z_axis_button]

        trans_axis_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(trans_axis_layout)

        rot_axis_label = QtWidgets.QLabel("Mirror Translation Across:")
        trans_axis_layout.addWidget(rot_axis_label)

        trans_x_axis_button = QtWidgets.QRadioButton("X Axis")
        trans_x_axis_button.setChecked(True)
        trans_y_axis_button = QtWidgets.QRadioButton("Y Axis")
        trans_z_axis_button = QtWidgets.QRadioButton("Z Axis")

        trans_axis_layout.addWidget(trans_x_axis_button)
        trans_axis_layout.addWidget(trans_y_axis_button)
        trans_axis_layout.addWidget(trans_z_axis_button)

        self._trans_button_group = QtWidgets.QButtonGroup()
        self._trans_button_group.setExclusive(True)
        self._trans_button_group.addButton(trans_x_axis_button)
        self._trans_button_group.addButton(trans_y_axis_button)
        self._trans_button_group.addButton(trans_z_axis_button)
        self._trans_axis_buttons = [trans_x_axis_button, trans_y_axis_button, trans_z_axis_button]

        types = ["solvers", "joints", "poses"]
        self._line_edits = []
        self._regex_checkboxes = []
        for type_str in types:
            line_break = QtWidgets.QFrame()
            line_break.setFrameShape(QtWidgets.QFrame.HLine)
            main_layout.addWidget(line_break)
            layout = QtWidgets.QVBoxLayout()
            main_layout.addLayout(layout)

            use_regex_checkbox = QtWidgets.QCheckBox("Use Regex Pattern")
            layout.addWidget(use_regex_checkbox)
            self._regex_checkboxes.append(use_regex_checkbox)

            layout.addWidget(QtWidgets.QLabel(f"Replacement names for duplicated {type_str}"))

            search_layout = QtWidgets.QHBoxLayout()
            layout.addLayout(search_layout)
            search_label = QtWidgets.QLabel("Search for")
            search_layout.addWidget(search_label)

            search_line_edit = QtWidgets.QLineEdit()
            search_layout.addWidget(search_line_edit)
            self._line_edits.append(search_line_edit)

            replace_layout = QtWidgets.QHBoxLayout()
            layout.addLayout(replace_layout)
            replace_label = QtWidgets.QLabel("Replace with")
            replace_layout.addWidget(replace_label)

            replace_line_edit = QtWidgets.QLineEdit()
            replace_layout.addWidget(replace_line_edit)
            self._line_edits.append(replace_line_edit)

        main_layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        mirror_button = QtWidgets.QPushButton("Mirror")
        mirror_button.clicked.connect(partial(self._mirror_solver, True))
        button_layout.addWidget(mirror_button)

        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self._mirror_solver)
        button_layout.addWidget(apply_button)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        main_layout.addLayout(button_layout)

        self._load_settings()
        self.show()

    def closeEvent(self, event=None) -> None:
        self._save_settings()
        super().closeEvent(event)

    def _mirror_solver(self, close: bool = False):
        axis = ["x", "y", "z"]
        rot_index = 0
        for rot_index, button in enumerate(self._rot_axis_buttons):
            if button.isChecked():
                break

        trans_index = 0
        for trans_index, button in enumerate(self._trans_axis_buttons):
            if button.isChecked():
                break

        self.event_mirror_solver.emit(
            *[line_edit.text() for line_edit in self._line_edits],
            axis[rot_index],
            axis[trans_index],
            *[checkbox.isChecked() for checkbox in self._regex_checkboxes],
        )
        if close:
            self.close()

    def _load_settings(self) -> None:
        if SettingsManager.QSETTINGS:
            line_edit_state = SettingsManager.get_setting("mirror_solver_dialog:search_replace_state")
            if line_edit_state:
                for index, line in enumerate(line_edit_state.split("~")):
                    self._line_edits[index].setText(line)

            rot_axis_index = SettingsManager.get_setting("mirror_solver_dialog:rot_axis")
            if rot_axis_index:
                self._rot_axis_buttons[int(rot_axis_index)].setChecked(True)

            trans_axis_index = SettingsManager.get_setting("mirror_solver_dialog:trans_axis")
            if trans_axis_index:
                self._trans_axis_buttons[int(trans_axis_index)].setChecked(True)

            regex_checkboxes_state = SettingsManager.get_setting("mirror_solver_dialog:regex_checkboxes")
            if regex_checkboxes_state:
                for index, state in enumerate(regex_checkboxes_state.split("~")):
                    self._regex_checkboxes[index].setChecked(bool(int(state)))

    def _save_settings(self) -> None:
        if not SettingsManager.QSETTINGS:
            SettingsManager()

        SettingsManager.set_setting(
            "mirror_solver_dialog:search_replace_state", "~".join([line_edit.text() for line_edit in self._line_edits])
        )

        index = 0
        for index, button in enumerate(self._rot_axis_buttons):
            if button.isChecked():
                break

        SettingsManager.set_setting("mirror_solver_dialog:rot_axis", index)

        index = 0
        for index, button in enumerate(self._trans_axis_buttons):
            if button.isChecked():
                break

        SettingsManager.set_setting("mirror_solver_dialog:trans_axis", index)

        SettingsManager.set_setting(
            "mirror_solver_dialog:regex_checkboxes",
            "~".join([str(int(checkbox.isChecked())) for checkbox in self._regex_checkboxes]),
        )
