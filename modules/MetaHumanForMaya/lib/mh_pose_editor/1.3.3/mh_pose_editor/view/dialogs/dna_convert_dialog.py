# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from pathlib import Path

# External
from qtpy import QtCore, QtWidgets

# Internal
from mh_pose_editor.model.settings import SettingsManager


class DNAConvertDialog(QtWidgets.QDialog):
    event_convert_scene = QtCore.Signal(Path, bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Upgrade Legacy MetaHuman Scene to DNA.")
        self.setModal(True)

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        self._generate_swing_twist_checkbox = QtWidgets.QCheckBox("Generate Default Swing Twist Setup")
        self._generate_swing_twist_checkbox.setChecked(True)

        main_layout.addWidget(self._generate_swing_twist_checkbox)

        groupbox = QtWidgets.QGroupBox("Description")
        main_layout.addWidget(groupbox)

        help_layout = QtWidgets.QVBoxLayout()
        groupbox.setLayout(help_layout)

        description_label = QtWidgets.QLabel(
            "This process is designed to upgrade a legacy MetaHuman scene to be compatible with DNA. This involves "
            "removing the driver skeleton, migrating any RBF solvers to the current bind skeleton and optionally "
            "converting the legacy swing/twist setup to SwingTwistEvaluator nodes.\n\n"
            "Warning: This process is destructive, please ensure that you have saved your scene before you continue. "
            "Custom constraints and rigs will be lost."
        )
        description_label.setWordWrap(True)
        help_layout.addWidget(description_label)

        convert_button = QtWidgets.QPushButton("Upgrade Scene")
        convert_button.clicked.connect(self._convert_scene)
        main_layout.addWidget(convert_button)

        self._load_settings()
        self.show()

    def closeEvent(self, event) -> None:
        self._save_settings()
        super().closeEvent(event)

    def _load_settings(self) -> None:
        if SettingsManager.QSETTINGS:
            generate_default_swing_twist = SettingsManager.get_setting("dna_converter:default_swing_twist")
            if generate_default_swing_twist:
                self._generate_swing_twist_checkbox.setChecked(bool(generate_default_swing_twist))

    def _save_settings(self) -> None:
        if not SettingsManager.QSETTINGS:
            SettingsManager()

        SettingsManager.set_setting(
            "dna_converter:default_swing_twist", int(self._generate_swing_twist_checkbox.isChecked())
        )

    def _convert_scene(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption="Set Export Location", filter="DNA File (*.dna)"
        )
        if file_path:
            self.event_convert_scene.emit(Path(file_path), self._generate_swing_twist_checkbox.isChecked())
            self.close()
