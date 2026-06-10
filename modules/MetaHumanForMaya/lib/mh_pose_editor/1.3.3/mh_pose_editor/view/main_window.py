# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from typing import Any, Dict
from pathlib import Path

# External
import qstyle
from qtpy import QtCore, QtWidgets

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.view import log_widget, ui_context
from mh_pose_editor.view.widget import category
from mh_pose_editor.view.dialogs import (
    dna_export_dialog,
    dna_import_dialog,
    dna_convert_dialog,
)
from mh_pose_editor.view.rbf.rbf_panel import RBFPanel
from mh_pose_editor.view.rbf.rbf_settings_panel import RBFSettingsPanel


class MHPoseEditor(QtWidgets.QMainWindow):
    event_convert_scene = QtCore.Signal(Path, bool)

    event_import_drivers = QtCore.Signal(str, bool, bool, bool, bool, bool, str)
    event_export_drivers = QtCore.Signal(str, list, bool, bool, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("MetaHuman Pose Editor")
        css_file = Path(__file__).parents[1] / "resources" / "style" / "style.css"
        qstyle.install_fonts(silent=True)
        qstyle.set_style(self, css_file.as_posix())

        icons_dir = Path(__file__).parents[1] / "resources" / "icons"
        QtCore.QDir.addSearchPath("PoseEditor", icons_dir.as_posix())

        top_menubar = QtWidgets.QMenuBar(parent=self)
        self.setMenuBar(top_menubar)

        file_menu = QtWidgets.QMenu("File", parent=top_menubar)
        top_menubar.addMenu(file_menu)

        import_dna_action = QtWidgets.QAction("Import from DNA", parent=file_menu)
        import_dna_action.triggered.connect(self._import_dna)
        file_menu.addAction(import_dna_action)

        export_dna_action = QtWidgets.QAction("Export to DNA", parent=file_menu)
        export_dna_action.triggered.connect(self._export_dna)
        file_menu.addAction(export_dna_action)

        file_menu.addSeparator()

        close_app_action = QtWidgets.QAction("Close", parent=file_menu)
        close_app_action.triggered.connect(self._close_app)
        file_menu.addAction(close_app_action)

        tools_menu = QtWidgets.QMenu("Tools", parent=top_menubar)
        top_menubar.addMenu(tools_menu)

        upgrade_scene_action = QtWidgets.QAction("Convert Legacy MetaHuman Scene to DNA")
        help_txt = (
            "Converts the current legacy MetaHuman scene to a state that is compatible with DNA. "
            "Removes a driver skeleton and moves any non zero'd joint rotations to joint "
            "orient."
        )
        upgrade_scene_action.setToolTip(help_txt)
        upgrade_scene_action.setStatusTip(help_txt)
        upgrade_scene_action.triggered.connect(self._request_convert_scene)
        tools_menu.addAction(upgrade_scene_action)

        self._menu_actions = [import_dna_action, export_dna_action, upgrade_scene_action]

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Horizontal)
        left_panel = QtWidgets.QWidget()
        left_panel_layout = QtWidgets.QVBoxLayout()
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel.setLayout(left_panel_layout)

        self._tab_widget = QtWidgets.QTabWidget()
        left_panel_layout.addWidget(self._tab_widget)

        self._rbf_panel = RBFPanel()
        self._tab_widget.addTab(self._rbf_panel, "RBF")

        splitter.addWidget(left_panel)

        self._right_stack = QtWidgets.QStackedWidget()

        self._rbf_settings_panel = RBFSettingsPanel()
        self._right_stack.addWidget(self._rbf_settings_panel)
        self._rbf_panel.set_settings_panel(self._rbf_settings_panel)
        splitter.addWidget(self._right_stack)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self._tab_widget.currentChanged.connect(self._on_mode_changed)

        self._custom_extensions_dock = QtWidgets.QDockWidget("Utilities")

        self._extension_scroll_area = QtWidgets.QScrollArea()
        self._custom_extensions_dock.setWidget(self._extension_scroll_area)

        self._scroll_area_container_layout = QtWidgets.QVBoxLayout()
        self._extension_scroll_area.setLayout(self._scroll_area_container_layout)

        self._extensions_layout = QtWidgets.QVBoxLayout()
        self._extensions_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_area_container_layout.addLayout(self._extensions_layout)
        self._scroll_area_container_layout.addStretch()

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._custom_extensions_dock)

        # Create a log dock widget
        self._log_widget = log_widget.LogWidget()
        # Add the log widget as a handler for the current log to display log messages in the UI
        LOG.addHandler(self._log_widget)
        # Add the dock to the window
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._log_widget.log_dock)

        self._convert_dialog = None

    @property
    def rbf(self):
        return self._rbf_panel

    @property
    def rbf_settings(self):
        return self._rbf_settings_panel

    def _on_mode_changed(self, index):
        self._right_stack.setCurrentIndex(index)

    def clear(self):
        self._rbf_panel.clear()
        self._rbf_settings_panel.clear()

    def get_context(self):
        """
        Gets the current state of the ui
        :return: PoseEditorUIContext
        """
        return ui_context.PoseEditorUIContext(
            current_solvers=self._rbf_panel.get_solver_names(selection=True),
            current_poses=self._rbf_settings_panel.get_poses(selection=True),
            current_drivers=self._rbf_settings_panel.get_drivers(selection=True),
            current_driven=self._rbf_settings_panel.get_driven(selection=True),
            solvers=self._rbf_panel.get_solver_names(selection=False),
            poses=self._rbf_settings_panel.get_poses(selection=False),
            drivers=self._rbf_settings_panel.get_drivers(selection=False),
            driven=self._rbf_settings_panel.get_driven(selection=False),
        )

    def load_extensions(self, extensions):
        """
        Adds any found extensions to the utilities dock
        :param extensions :type list: list of PoseEditorExtension instances
        """
        # Clear the existing extension layout
        for i in reversed(range(0, self._extensions_layout.count())):
            item = self._extensions_layout.itemAt(i)
            if isinstance(item, QtWidgets.QWidgetItem):
                widget = item.widget()
                widget.deleteLater()
                del widget
            self._extensions_layout.removeItem(item)

        categories: Dict[str, Any] = {}
        min_width = 200
        for extension in extensions:
            extension_view = extension.view
            if extension_view:
                category_name = extension.__category__ or "Default"
                if category_name in categories:
                    category_widget = categories[category_name]
                else:
                    category_widget = category.CategoryWidget(category_name)
                    categories[category_name] = category_widget
                    self._extensions_layout.addWidget(category_widget)
                category_widget.add_extension(extension_view)
                if extension_view.sizeHint().width() > min_width:
                    min_width = extension_view.sizeHint().width()
        min_width += 40
        self._custom_extensions_dock.setMinimumWidth(min_width)

    def _trigger_context_menu_action(self, action):
        """
        Execute the specified action with the given data
        :param action :type base_action.BaseAction: action class
        """
        # Execute the action with the data
        action.execute(ui_context=self.get_context())

    def _import_dna(self):
        import_dialog_ref = dna_import_dialog.DNAImportDialog(restore_directory=True, parent=self)
        import_dialog_ref.exec_()
        if import_dialog_ref.success:
            self.event_import_drivers.emit(
                import_dialog_ref.import_path,
                import_dialog_ref.import_skeleton,
                import_dialog_ref.import_geometry,
                import_dialog_ref.unpack_riglogic,
                import_dialog_ref.unpack_rbf,
                import_dialog_ref.unpack_swing_twist,
                import_dialog_ref.up_axis,
            )

    def _export_dna(self):
        export_dialog_ref = dna_export_dialog.DNAExportDialog(restore_directory=True, parent=self)
        export_dialog_ref.exec_()
        if export_dialog_ref.success:
            self.event_export_drivers.emit(
                export_dialog_ref.export_path,
                self._rbf_panel.get_solvers(export_dialog_ref.export_selected_rbf),
                export_dialog_ref.export_geometry,
                export_dialog_ref.export_selected_geometry,
                export_dialog_ref.export_rbf,
                export_dialog_ref.export_swing_twist,
            )

    def _close_app(self):
        self.close()

    def _request_convert_scene(self):
        self._convert_dialog = dna_convert_dialog.DNAConvertDialog(parent=self)
        self._convert_dialog.event_convert_scene.connect(self._convert_scene)
        self._convert_dialog.exec_()

    def _convert_scene(self, dna_path: Path, generate_default_swing_twist_setup: bool):
        self.event_convert_scene.emit(dna_path, generate_default_swing_twist_setup)
