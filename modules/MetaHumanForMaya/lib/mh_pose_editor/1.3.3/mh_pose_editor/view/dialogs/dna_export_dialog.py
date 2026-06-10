# Copyright Epic Games, Inc. All Rights Reserved.

# External
from qtpy import QtCore, QtWidgets

# Internal
from mh_pose_editor.model.settings import SettingsManager


class DNAExportDialog(QtWidgets.QDialog):
    def __init__(self, default_directory: str = "", restore_directory: bool = False, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Export DNA")
        self.setModal(True)
        self._file_dialog = QtWidgets.QFileDialog(parent=self)
        self._file_dialog.setDirectory(default_directory)
        self._file_dialog.setWindowFlags(self._file_dialog.windowFlags() & ~QtCore.Qt.Dialog)
        self._file_dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        self._file_dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)
        self._file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        self._file_dialog.accepted.connect(self._exit)
        self._file_dialog.rejected.connect(self._exit)
        self._file_dialog.setWindowFlags(QtCore.Qt.MSWindowsFixedSizeDialogHint)
        self._file_dialog.setSizeGripEnabled(False)
        self._file_dialog.setNameFilter("DNA Files (*.dna)")

        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)
        splitter = QtWidgets.QSplitter()
        main_layout.addWidget(splitter)
        splitter.addWidget(self._file_dialog)
        properties_layout = QtWidgets.QVBoxLayout()
        properties_widget = QtWidgets.QWidget()
        properties_widget.setLayout(properties_layout)
        splitter.addWidget(properties_widget)

        properties_layout.addWidget(QtWidgets.QLabel("DNA Export Settings:"))
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        properties_layout.addWidget(divider)

        self._export_geometry = QtWidgets.QCheckBox("Export Geometry")
        self._export_geometry.setChecked(True)
        self._export_geometry.setToolTip("Export geometry to DNA")
        self._export_geometry.stateChanged.connect(self._export_geometry_state_changed)
        properties_layout.addWidget(self._export_geometry)

        self._export_selected_geometry = QtWidgets.QCheckBox("Export Selected Geometry")
        self._export_selected_geometry.setToolTip("Export the selected geometry to DNA")
        properties_layout.addWidget(self._export_selected_geometry)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        properties_layout.addWidget(divider)

        self._export_rbf_checkbox = QtWidgets.QCheckBox("Export RBF")
        self._export_rbf_checkbox.setChecked(True)
        self._export_rbf_checkbox.setToolTip("Export UERBFSolver nodes to DNA")
        self._export_rbf_checkbox.stateChanged.connect(self._export_rbf_state_changed)
        properties_layout.addWidget(self._export_rbf_checkbox)

        self._export_selected_rbf_checkbox = QtWidgets.QCheckBox("Export Selected RBF Solvers")
        self._export_selected_rbf_checkbox.setToolTip("Export the current UERBFSolver UI selection to DNA")
        properties_layout.addWidget(self._export_selected_rbf_checkbox)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        properties_layout.addWidget(divider)

        self._export_swing_twist_checkbox = QtWidgets.QCheckBox("Export Swing/Twist")
        self._export_swing_twist_checkbox.setToolTip("Export SwingTwistEvaluatorNodes nodes to DNA")
        self._export_swing_twist_checkbox.setChecked(True)
        properties_layout.addWidget(self._export_swing_twist_checkbox)

        properties_layout.addStretch()

        self._load_settings(restore_directory=restore_directory)
        self.show()

    @property
    def export_geometry(self):
        return self._export_geometry.isChecked()

    @property
    def export_selected_geometry(self):
        if self._export_selected_geometry.isEnabled():
            return self._export_selected_geometry.isChecked()

        return False

    @property
    def export_rbf(self):
        return self._export_rbf_checkbox.isChecked()

    @property
    def export_selected_rbf(self):
        if self._export_selected_rbf_checkbox.isEnabled():
            return self._export_selected_rbf_checkbox.isChecked()

        return False

    @property
    def export_swing_twist(self):
        return self._export_swing_twist_checkbox.isChecked()

    @property
    def success(self):
        return self._file_dialog.result()

    @property
    def export_path(self):
        if self.result:
            path = self._file_dialog.selectedFiles()[0]
            if not path.endswith(".dna"):
                path += ".dna"
            return path
        return None

    def _export_geometry_state_changed(self, checked: bool):
        self._export_selected_geometry.setEnabled(checked)

    def _export_rbf_state_changed(self, checked: bool):
        self._export_selected_rbf_checkbox.setEnabled(checked)

    def _exit(self) -> None:
        self._save_settings()
        self.close()

    def _load_settings(self, restore_directory: bool = False) -> None:
        if SettingsManager.QSETTINGS:
            export_rbf = SettingsManager.get_setting("dna_exporter:export_rbf")
            if export_rbf is not None:
                self._export_rbf_checkbox.setChecked(bool(int(export_rbf)))

                export_selected_rbf = SettingsManager.get_setting("dna_exporter:export_selected_rbf")
                if export_selected_rbf is not None:
                    self._export_selected_rbf_checkbox.setChecked(bool(int(export_selected_rbf)))

            export_swing_twist = SettingsManager.get_setting("dna_exporter:export_swing_twist")
            if export_swing_twist is not None:
                self._export_swing_twist_checkbox.setChecked(bool(int(export_swing_twist)))

            export_geometry = SettingsManager.get_setting("dna_exporter:export_geometry")
            if export_geometry is not None:
                self._export_geometry.setChecked(bool(int(export_geometry)))

                export_selected_geometry = SettingsManager.get_setting("dna_exporter:export_selected_geometry")
                if export_selected_geometry is not None:
                    self._export_selected_geometry.setChecked(bool(int(export_selected_geometry)))

            current_directory = SettingsManager.get_setting("dna_exporter:current_directory")
            if restore_directory and current_directory is not None:
                self._file_dialog.setDirectory(current_directory)

    def _save_settings(self) -> None:
        if not SettingsManager.QSETTINGS:
            SettingsManager()

        SettingsManager.set_setting("dna_exporter:export_rbf", int(self.export_rbf))
        SettingsManager.set_setting("dna_exporter:export_selected_rbf", int(self.export_selected_rbf))
        SettingsManager.set_setting("dna_exporter:export_swing_twist", int(self.export_swing_twist))
        SettingsManager.set_setting("dna_exporter:export_geometry", int(self.export_geometry))
        SettingsManager.set_setting("dna_exporter:export_selected_geometry", int(self.export_selected_geometry))
        SettingsManager.set_setting("dna_exporter:current_directory", self._file_dialog.directory().absolutePath())
