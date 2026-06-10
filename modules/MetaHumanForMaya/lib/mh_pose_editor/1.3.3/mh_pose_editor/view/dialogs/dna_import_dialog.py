# Copyright Epic Games, Inc. All Rights Reserved.

# External
from qtpy import QtCore, QtWidgets

# Internal
from mh_pose_editor.model.settings import SettingsManager


class DNAImportDialog(QtWidgets.QDialog):
    def __init__(self, default_directory: str = "", restore_directory: bool = False, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Import DNA")
        self.setModal(True)
        self._file_dialog = QtWidgets.QFileDialog(parent=self)
        self._file_dialog.setDirectory(default_directory)
        self._file_dialog.setWindowFlags(self._file_dialog.windowFlags() & ~QtCore.Qt.Dialog)
        self._file_dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        self._file_dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)
        self._file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
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

        properties_layout.addWidget(QtWidgets.QLabel("DNA Import Settings:"))
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        properties_layout.addWidget(divider)

        self._import_skeleton = QtWidgets.QCheckBox("Import Skeleton")
        self._import_skeleton.setToolTip("Import skeleton from DNA")
        self._import_skeleton.setChecked(True)
        properties_layout.addWidget(self._import_skeleton)

        self._import_geometry = QtWidgets.QCheckBox("Import Geometry")
        self._import_geometry.setToolTip("Import geometry from DNA")
        self._import_geometry.setChecked(True)
        properties_layout.addWidget(self._import_geometry)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        properties_layout.addWidget(divider)

        self._unpack_riglogic_checkbox = QtWidgets.QCheckBox("Unpack Riglogic")
        self._unpack_riglogic_checkbox.stateChanged.connect(self._unpack_riglogic_changed)
        self._unpack_riglogic_checkbox.setToolTip("Unpack RigLogic from DNA to editable Maya node networks")
        properties_layout.addWidget(self._unpack_riglogic_checkbox)

        self._unpack_rbf_checkbox = QtWidgets.QCheckBox("Unpack RBF")
        self._unpack_rbf_checkbox.setEnabled(True)
        self._unpack_rbf_checkbox.setToolTip("Unpack UERBFSolver nodes from DNA")
        self._unpack_rbf_checkbox.setChecked(True)
        properties_layout.addWidget(self._unpack_rbf_checkbox)

        self._unpack_swing_twist_checkbox = QtWidgets.QCheckBox("Unpack Swing/Twist")
        self._unpack_swing_twist_checkbox.setEnabled(True)
        self._unpack_swing_twist_checkbox.setToolTip("Unpack SwingTwistEvaluatorNodes nodes from DNA")
        self._unpack_swing_twist_checkbox.setChecked(True)
        properties_layout.addWidget(self._unpack_swing_twist_checkbox)
        self._unpack_riglogic_checkbox.setChecked(True)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        properties_layout.addWidget(divider)

        # Button group
        up_axis_label = QtWidgets.QLabel("Up Axis:")
        properties_layout.addWidget(up_axis_label)

        # Radio buttons
        from_dna_up = QtWidgets.QRadioButton("DNA")
        from_dna_up.setChecked(True)

        y_up = QtWidgets.QRadioButton("Y")
        z_up = QtWidgets.QRadioButton("Z")

        self._up_axis_checkboxes = [from_dna_up, y_up, z_up]

        # create button group
        scene_orient_group = QtWidgets.QButtonGroup()
        scene_orient_group.addButton(from_dna_up)
        scene_orient_group.addButton(y_up)
        scene_orient_group.addButton(z_up)

        # add buttons to horizontal layout
        scene_orient_layout = QtWidgets.QHBoxLayout()
        scene_orient_layout.addWidget(from_dna_up)
        scene_orient_layout.addWidget(y_up)
        scene_orient_layout.addWidget(z_up)
        properties_layout.addLayout(scene_orient_layout)

        properties_layout.addStretch()

        self.show()

        self._load_settings(restore_directory=restore_directory)

    @property
    def import_skeleton(self):
        return self._import_skeleton.isChecked()

    @property
    def import_geometry(self):
        return self._import_geometry.isChecked()

    @property
    def unpack_riglogic(self):
        return self._unpack_riglogic_checkbox.isChecked()

    @property
    def unpack_rbf(self):
        return self._unpack_riglogic_checkbox.isChecked() and self._unpack_rbf_checkbox.isChecked()

    @property
    def unpack_swing_twist(self):
        return self._unpack_riglogic_checkbox.isChecked() and self._unpack_swing_twist_checkbox.isChecked()

    @property
    def up_axis(self):
        for checkbox in self._up_axis_checkboxes:
            if checkbox.isChecked():
                return checkbox.text().lower()
        return "y"

    @property
    def success(self):
        return self._file_dialog.result()

    @property
    def import_path(self):
        if self.result:
            path = self._file_dialog.selectedFiles()[0]
            if not path.endswith(".dna"):
                path += ".dna"
            return path
        return None

    def _exit(self) -> None:
        self._save_settings()
        self.close()

    def _unpack_riglogic_changed(self, checked):
        self._unpack_rbf_checkbox.setEnabled(checked)
        self._unpack_swing_twist_checkbox.setEnabled(checked)

    def _load_settings(self, restore_directory: bool = False) -> None:
        if not SettingsManager.QSETTINGS:
            SettingsManager()

        import_skeleton = SettingsManager.get_setting("dna_importer:import_skeleton")
        if import_skeleton is not None:
            self._import_skeleton.setChecked(bool(int(import_skeleton)))

        unpack_rbf = SettingsManager.get_setting("dna_importer:unpack_rbf")
        if unpack_rbf is not None:
            self._unpack_rbf_checkbox.setChecked(bool(int(unpack_rbf)))

        unpack_swing_twist = SettingsManager.get_setting("dna_importer:unpack_swing_twist")
        if unpack_swing_twist is not None:
            self._unpack_swing_twist_checkbox.setChecked(bool(int(unpack_swing_twist)))

        unpack_riglogic = SettingsManager.get_setting("dna_importer:unpack_riglogic")
        if unpack_riglogic is not None:
            self._unpack_riglogic_checkbox.setChecked(bool(int(unpack_riglogic)))

        import_geometry = SettingsManager.get_setting("dna_importer:import_geometry")
        if import_geometry is not None:
            self._import_geometry.setChecked(bool(int(import_geometry)))

        current_directory = SettingsManager.get_setting("dna_importer:current_directory")
        if restore_directory and current_directory is not None:
            self._file_dialog.setDirectory(current_directory)

        up_axis = SettingsManager.get_setting("dna_importer:up_axis")
        if up_axis is not None:
            self._up_axis_checkboxes[int(up_axis)].setChecked(True)

    def _save_settings(self) -> None:
        if not SettingsManager.QSETTINGS:
            SettingsManager()
        SettingsManager.set_setting("dna_importer:unpack_riglogic", int(self.unpack_riglogic))
        SettingsManager.set_setting("dna_importer:unpack_rbf", int(self.unpack_rbf))
        SettingsManager.set_setting("dna_importer:unpack_swing_twist", int(self.unpack_swing_twist))
        SettingsManager.set_setting("dna_importer:import_geometry", int(self.import_geometry))
        SettingsManager.set_setting("dna_importer:import_skeleton", int(self.import_skeleton))
        SettingsManager.set_setting("dna_importer:current_directory", self._file_dialog.directory().absolutePath())

        up_axis = 0
        for index, checkbox in enumerate(self._up_axis_checkboxes):
            if checkbox.isChecked():
                up_axis = index

        SettingsManager.set_setting("dna_importer:up_axis", up_axis)
