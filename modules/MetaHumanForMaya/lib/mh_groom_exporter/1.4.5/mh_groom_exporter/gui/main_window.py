# Copyright Epic Games, Inc. All Rights Reserved.
import os
import sys
import json
import shutil
import tempfile
import contextlib
import subprocess
from pathlib import Path
from functools import partial

import qstyle
import maya.cmds as cmds
from qtpy import QtGui, QtCore, QtWidgets
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from .. import export_proc, scene_utils
from ..xgen_utils import get_descriptions, get_bound_geometry
from ..gui.gui_state import GuiState
from ..gui.file_dialog import FileOpenDialog, FileSaveDialog, FileOpenMayaProjectDialog
from ..gui.item_widget import TreeWidgetItem
from ..gui.list_widget import ListWidget
from ..gui.combo_widget import ModelComboWidget

module = sys.modules[__name__]
module.window = None  # type: ignore

app_css = os.path.join(os.path.dirname(__file__), "app.css")


class Window(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qstyle.install_fonts(silent=True)

        self.setWindowTitle("MetaHuman Groom Exporter")
        self.setMinimumSize(400, 400)

        self.settings = QtCore.QSettings(
            QtCore.QSettings.Format.IniFormat,
            QtCore.QSettings.Scope.UserScope,
            "Epic Games",
            "MetaHumanForMaya/MetaHumanGroomExporter",
        )

        qstyle.install_fonts(silent=True)
        qstyle.set_style(self, app_css, with_main=True)

        # Create Variables
        self.project_browse_widget = None
        self.scene_browse_widget = None
        self.model_browse_widget = None

        # Create Main Widget
        self.main_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QGridLayout()
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        # ------------------------------------------------------------------------------------------
        # Create Menu Bar
        bar = self.menuBar()

        file = bar.addMenu("File")

        new_config = QtGui.QAction("New", self)
        new_config.setShortcut("Ctrl+N")
        new_config.triggered.connect(self.new_config)
        file.addAction(new_config)

        open_config = QtGui.QAction("Open", self)
        open_config.setShortcut("Ctrl+O")
        open_config.triggered.connect(self.open_config)
        file.addAction(open_config)

        save_config = QtGui.QAction("Save", self)
        save_config.setShortcut("Ctrl+S")
        save_config.triggered.connect(self.save_config)
        file.addAction(save_config)

        file.addSeparator()

        quit_app = QtGui.QAction("Quit", self)
        quit_app.setShortcut("Ctrl+Q")
        quit_app.triggered.connect(self.quit_app)
        file.addAction(quit_app)

        # ------------------------------------------------------------------------------------------
        # Create Layouts
        self.__create_file_dialogs(self.main_layout)

        # Create Refresh Button
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh)
        self.main_layout.addWidget(self.refresh_button)

        # Create Model Combo
        self.model_combo_widget = ModelComboWidget("Model Mesh")
        self.main_layout.addWidget(self.model_combo_widget)

        # Create Lists
        self.__create_list_widgets(self.main_layout)

        # Create Output File Dialog
        self.__create_output_file_dialog(self.main_layout)

        # Gui State
        self.GuiState = GuiState(self)

        # Load stored user settings
        self.GuiState.load_geometry(self.settings)

        # store export completed stats windows
        self.stats = []

        self._init_from_current_scene()
        self.resize(600, 740)

    def closeEvent(self, e):
        self.GuiState.save_geometry(self.settings)

    def showEvent(self, event):
        super().showEvent(event)
        self._clear(fileDialogs=True)
        self._init_from_current_scene()

    def _init_from_current_scene(self):
        workspace = cmds.workspace(q=True, rd=True)
        if workspace:
            self.project_browser_widget.data = workspace

        scene_file = cmds.file(q=True, sn=True)
        if not scene_file:
            return

        self.scene_browser_widget.data = scene_file

        meshes = cmds.ls(type="mesh", noIntermediate=True)
        meshes = [cmds.listRelatives(mesh, parent=True)[0] for mesh in meshes]
        meshes = sorted(list(set(meshes)))  # remove duplicates if any
        if not meshes:
            print("No meshes found in the current scene")
        self.model_combo_widget.combo_box.addItems(meshes)

        # Get Scene Up Axis
        scene_up_axis = cmds.upAxis(q=True, axis=True).upper()  # NOTE: this does not get the axis from scene
        self.model_combo_widget.scene_up_axis_combo_box.setCurrentText(scene_up_axis)

        # get all palettes
        descriptions = get_descriptions()

        for description in descriptions:
            # Add Description
            item = TreeWidgetItem(self.description_list_widget.tree_widget, self.description_list_widget.group_names)
            item.setText(0, description)

        self.description_list_widget.tree_widget.clearSelection()

        if descriptions:
            geometry = get_bound_geometry(descriptions[0])
            if geometry and geometry[0] in meshes:
                self.model_combo_widget.model = geometry[0]

    def __create_file_dialogs(self, layout):
        self.project_browser_widget = FileOpenMayaProjectDialog("Project Directory: ")
        self.scene_browser_widget = FileOpenDialog("Scene File: ")
        self.model_browser_widget = FileOpenDialog("Model File: ")

        layout.addWidget(self.project_browser_widget)
        layout.addWidget(self.scene_browser_widget)
        layout.addWidget(self.model_browser_widget)

    def __create_list_widgets(self, layout):
        widget = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(h_layout)

        # Create List
        self.description_list_widget = ListWidget("Descriptions")
        h_layout.addWidget(self.description_list_widget)
        layout.addWidget(widget)

    def __create_output_file_dialog(self, layout):
        self.output_file_dialog = FileSaveDialog("Output File")
        layout.addWidget(self.output_file_dialog)

        self.export_button = QtWidgets.QPushButton("Export Selected")
        self.export_button.clicked.connect(partial(self._run, False))
        layout.addWidget(self.export_button)

        self.description_list_widget.tree_widget.selectionModel().selectionChanged.connect(self.updateExportButton)

        self.updateExportButton()

    def updateExportButton(self):
        if self.description_list_widget.tree_widget.selectedItems():
            self.export_button.setEnabled(True)
        else:
            self.export_button.setEnabled(False)

    def _clear(self, fileDialogs=False):
        if fileDialogs:
            self.project_browser_widget._clear()
            self.scene_browser_widget._clear()
            self.model_browser_widget._clear()
            self.output_file_dialog._clear()

        self.description_list_widget._clear()
        self.model_combo_widget._clear()

    def _refresh(self):
        self._clear()

        # Check data
        project_directory = self.project_browser_widget.data
        scene_filepath = self.scene_browser_widget.data
        model_filepath = self.model_browser_widget.data

        if not os.path.exists(project_directory):
            raise OSError(f'Invalid Project Path: "{project_directory}"')
        if not os.path.exists(scene_filepath):
            raise OSError(f'Invalid Scene Path: "{scene_filepath}"')
        if model_filepath and not os.path.exists(model_filepath):
            raise OSError(f'Invalid Model Path: "{model_filepath}"')

        # ------------------------------------------------------------------------------------------
        # Get Meshes
        if model_filepath:
            scene_utils.load_scene(model_filepath)

            meshes = cmds.ls(type="mesh", noIntermediate=True)
            meshes = [cmds.listRelatives(mesh, parent=True)[0] for mesh in meshes]
            meshes = sorted(list(set(meshes)))  # remove duplicates if any
            if not meshes:
                raise RuntimeError(f'No meshes found in: "{model_filepath}"')
            self.model_combo_widget.combo_box.addItems(meshes)

            # Get Scene Up Axis
            scene_up_axis = cmds.upAxis(q=True, axis=True).upper()  # NOTE: this does not get the axis from scene
            self.model_combo_widget.scene_up_axis_combo_box.setCurrentText(scene_up_axis)

        # Set Project
        scene_utils.set_project(project_directory)

        # Load Scene
        scene_utils.load_scene(scene_filepath)

        if not model_filepath:
            meshes = cmds.ls(type="mesh", noIntermediate=True)
            meshes = [cmds.listRelatives(mesh, parent=True)[0] for mesh in meshes]
            meshes = list(set(meshes))  # remove duplicates if any
            if not meshes:
                raise RuntimeError(f'No meshes found in: "{model_filepath}"')
            self.model_combo_widget.combo_box.addItems(meshes)

            # Get Scene Up Axis
            scene_up_axis = cmds.upAxis(q=True, axis=True).upper()  # NOTE: this does not get the axis from scene
            self.model_combo_widget.scene_up_axis_combo_box.setCurrentText(scene_up_axis)

        # ------------------------------------------------------------------------------------------
        # get all palettes
        descriptions = get_descriptions()

        for description in descriptions:
            # Add Description
            item = TreeWidgetItem(self.description_list_widget.tree_widget, self.description_list_widget.group_names)
            item.setText(0, description)

        self.description_list_widget.tree_widget.clearSelection()

    def _error_message(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(message)
        msg.setWindowTitle("Error")
        msg.exec_()

        raise OSError(message)

    def _run(self, _all=False):
        if _all:
            self.description_list_widget._select_items()
        selected_items = self.description_list_widget.tree_widget.selectedItems()

        export_options = {}
        export_options["project_directory"] = self.project_browser_widget.data
        export_options["scene_filepath"] = self.scene_browser_widget.data
        export_options["model_filepath"] = self.model_browser_widget.data
        export_options["model_mesh"] = self.model_combo_widget.combo_box.currentText()
        export_options["output_filepath"] = self.output_file_dialog.data

        export_options["scene_up_axis"] = self.model_combo_widget.scene_up_axis_combo_box.currentText()
        export_options["description_names"] = [item.text(0) for item in selected_items]
        export_options["groupids"] = [item.data[0] for item in selected_items]
        export_options["groupnames"] = [item.data[1] for item in selected_items]
        export_options["export_guides"] = [item.data[2] for item in selected_items]

        # Create temp directory for export options
        # Note: In batch mode we can clean up immediately, in GUI mode the subprocess
        # needs the file so we let the OS clean it up eventually
        TEMP_DIR = tempfile.mkdtemp()
        export_option_file = Path(TEMP_DIR) / "export_options.json"
        with open(export_option_file, "w") as fp:
            json.dump(export_options, fp)

        if cmds.about(batch=True):
            # batch mode (no GUI), block - we can clean up after
            print("Running export (sync):", export_option_file)
            try:
                results = export_proc.run_export(export_option_file)
                self.stats.append(self.export_completed_dialog(results[0], results[1], results[2]))
                self.stats[-1].open()
            finally:
                # Clean up temp directory after synchronous export
                shutil.rmtree(TEMP_DIR, ignore_errors=True)

        else:
            # GUI mode (both Windows and Linux)
            maya_location = os.getenv("MAYA_LOCATION")
            if not maya_location:
                raise RuntimeError("MAYA_LOCATION environment variable is not set")

            mayapy_path = Path(maya_location) / "bin" / "mayapy"
            export_script = Path(export_proc.__file__).resolve()

            commands = [str(mayapy_path), str(export_script), str(export_option_file)]

            print("Running export command (async):", commands)
            try:
                if cmds.about(win=True):
                    # On Windows, create a new console window that stays open after completion
                    cmd_with_pause = ["cmd", "/k"] + commands + ["&", "echo.", "&", "pause"]
                    subprocess.Popen(cmd_with_pause, creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    # On Linux/Mac, run in background
                    subprocess.Popen(commands)
                QtWidgets.QMessageBox.information(
                    self,
                    "Export Started",
                    f"Exporting to:\n{export_options['output_filepath']}",
                )
            except OSError as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to start export process:\n{e}\n\nCommand: {' '.join(commands)}",
                )

    def export_completed_dialog(self, output_filepath, guide_counts, spline_counts):
        msg = QtWidgets.QMessageBox()
        msg_pos = self.frameGeometry().center() - QtCore.QRect(QtCore.QPoint(), msg.sizeHint()).center()
        msg.move(msg_pos)
        msg.setModal(False)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle("MetaHuman Groom Exporter")
        msg.setText("Export Completed!")
        output_text = output_filepath + "\n"

        guide_counts_msg, total_guides = "", 0
        for item in guide_counts:
            for description, count in item.items():
                guide_counts_msg += f"\t{description} : {count} curves\n"
                total_guides += count

        guides_msg = f"\nGuides ({total_guides} curves):\n\n" + guide_counts_msg
        output_text += guides_msg

        interpolated_counts_msg, total_interpolated = "", 0
        for item in spline_counts:
            for description, count in item.items():
                interpolated_counts_msg += f"\t{description}: {count} curves\n"
                total_interpolated += count

        interpolated_msg = f"\nInterpolated ({total_interpolated} curves):\n\n" + interpolated_counts_msg
        output_text += interpolated_msg

        msg.setInformativeText(output_text)

        return msg

    def new_config(self):
        scene_utils.new_scene()
        self._clear(fileDialogs=True)

    def open_config(self):
        file_path, filter_ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Config File", "", "JSON (*.json)")
        if file_path:
            self.GuiState.load_data(file_path)

    def save_config(self):
        file_path, filter_ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Config File", "", "JSON (*.json)")
        if file_path:
            self.GuiState.save_data(file_path)

    def quit_app(self):
        self.close()


def on_destroyed():
    module.window = None


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        yield app
    else:
        yield app
    app.exec_()


def show(parent=None):
    with application():
        # create if it doesn't exist
        if module.window is None:
            module.window = Window(parent=parent)
            module.window.destroyed.connect(on_destroyed)

        # If the window is minimized, raise it
        if module.window.windowState() & QtCore.Qt.WindowMinimized:
            module.window.setWindowState(QtCore.Qt.WindowActive)

        # show and make active
        module.window.show(dockable=True)
        module.window.activateWindow()

        return module.window
