# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
from functools import partial

# External
from qtpy import QtGui, QtCore, QtWidgets

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.view.dialogs import mirror_options_dialog


class RBFSettingsPanel(QtWidgets.QWidget):
    # Driver Signals
    event_add_drivers = QtCore.Signal(object)
    event_remove_drivers = QtCore.Signal(object, list)

    # Driven Signals
    event_add_driven = QtCore.Signal(object, bool)
    event_remove_driven = QtCore.Signal(object, list)
    # Pose Signals
    event_add_pose = QtCore.Signal(object, str)
    event_delete_pose = QtCore.Signal(object, str)
    event_go_to_pose = QtCore.Signal(object, str)
    event_mirror_pose = QtCore.Signal(object, str, str, str, str, str, str, str, str, str, bool, bool, bool)
    event_rename_pose = QtCore.Signal(object, str, str)
    event_update_pose = QtCore.Signal(object, str)
    event_mute_pose = QtCore.Signal(object, str, object)

    # Utility Signals
    event_select = QtCore.Signal(list)

    def __init__(self):
        super().__init__()
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(settings_layout)

        self._tab_widget = QtWidgets.QTabWidget()
        settings_layout.addWidget(self._tab_widget)

        input_settings = QtWidgets.QWidget()
        self._tab_widget.addTab(input_settings, "Inputs")

        inputs_layout = QtWidgets.QVBoxLayout()
        input_settings.setLayout(inputs_layout)

        driver_group = QtWidgets.QGroupBox("RBF Driver Joints:")
        driver_layout = QtWidgets.QVBoxLayout()
        driver_group.setLayout(driver_layout)
        inputs_layout.addWidget(driver_group)

        self._driver_list = QtWidgets.QListWidget()
        self._driver_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._driver_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._driver_list.itemDoubleClicked.connect(partial(self._select_in_scene, self._driver_list))
        driver_layout.addWidget(self._driver_list)

        button_layout = QtWidgets.QHBoxLayout()
        driver_layout.addLayout(button_layout)

        add_driver_button = QtWidgets.QPushButton("Add Driver")
        add_driver_button.clicked.connect(self._add_drivers)
        button_layout.addWidget(add_driver_button)

        remove_driver_button = QtWidgets.QPushButton("Remove Driver")
        remove_driver_button.clicked.connect(self._remove_drivers)
        button_layout.addWidget(remove_driver_button)

        driven_group = QtWidgets.QGroupBox("RBF Driven Joints:")
        driven_layout = QtWidgets.QVBoxLayout()
        driven_group.setLayout(driven_layout)
        inputs_layout.addWidget(driven_group)

        self._driven_list = QtWidgets.QListWidget()
        self._driven_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._driven_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._driven_list.itemDoubleClicked.connect(partial(self._select_in_scene, self._driven_list))
        driven_layout.addWidget(self._driven_list)

        button_layout = QtWidgets.QHBoxLayout()
        driven_layout.addLayout(button_layout)

        add_driven_button = QtWidgets.QPushButton("Add Driven")
        add_driven_button.clicked.connect(self._add_driven)
        button_layout.addWidget(add_driven_button)

        remove_driven_button = QtWidgets.QPushButton("Remove Driven")
        remove_driven_button.clicked.connect(self._remove_driven)
        button_layout.addWidget(remove_driven_button)

        # ------------------------------------------------------------------------------------------------------------ #
        pose_settings = QtWidgets.QWidget()
        self._tab_widget.addTab(pose_settings, "Poses")

        pose_layout = QtWidgets.QVBoxLayout()
        pose_settings.setLayout(pose_layout)

        pose_button_layout = QtWidgets.QHBoxLayout()
        pose_button_layout.setContentsMargins(0, 0, 0, 0)
        pose_layout.addLayout(pose_button_layout)

        create_button = QtWidgets.QPushButton("Create")
        create_button.clicked.connect(self._create_pose)
        pose_button_layout.addWidget(create_button)

        update_button = QtWidgets.QPushButton("Update")
        update_button.clicked.connect(self._update_pose)
        pose_button_layout.addWidget(update_button)

        rename_button = QtWidgets.QPushButton("Rename")
        rename_button.clicked.connect(self._rename_pose)
        pose_button_layout.addWidget(rename_button)

        mute_button = QtWidgets.QPushButton("Toggle Mute")
        mute_button.clicked.connect(self._mute_pose)
        pose_button_layout.addWidget(mute_button)

        mirror_button = QtWidgets.QPushButton("Mirror")
        mirror_button.clicked.connect(self._show_mirror_solver_options)
        pose_button_layout.addWidget(mirror_button)

        delete_button = QtWidgets.QPushButton("Delete")
        delete_button.clicked.connect(self._delete_pose)
        pose_button_layout.addWidget(delete_button)

        pose_settings_splitter = QtWidgets.QSplitter()
        pose_layout.addWidget(pose_settings_splitter)

        pose_group = QtWidgets.QGroupBox("RBF Poses:")
        pose_list_layout = QtWidgets.QVBoxLayout()
        pose_group.setLayout(pose_list_layout)
        pose_settings_splitter.addWidget(pose_group)

        self._pose_list = QtWidgets.QListWidget()
        self._pose_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._pose_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._pose_list.itemSelectionChanged.connect(self._pose_selection_changed)
        pose_list_layout.addWidget(self._pose_list)

        pose_solver_settings_splitter = QtWidgets.QSplitter()
        pose_solver_settings_splitter.setOrientation(QtCore.Qt.Vertical)
        pose_settings_splitter.addWidget(pose_solver_settings_splitter)

        pose_joints_group = QtWidgets.QGroupBox("RBF Pose Joints:")
        pose_joints_layout = QtWidgets.QVBoxLayout()
        pose_joints_group.setLayout(pose_joints_layout)
        pose_solver_settings_splitter.addWidget(pose_joints_group)

        self._pose_joints_list = QtWidgets.QListWidget()
        self._pose_joints_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._pose_joints_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._pose_joints_list.itemDoubleClicked.connect(partial(self._select_in_scene, self._pose_joints_list))
        pose_joints_layout.addWidget(self._pose_joints_list)

        self._buttons = [
            add_driver_button,
            remove_driver_button,
            add_driven_button,
            remove_driven_button,
            create_button,
            update_button,
            rename_button,
            mute_button,
            mirror_button,
            delete_button,
            delete_button,
        ]
        self._current_solver = None
        self.set_editing(False)
        self._mirror_options_dialog = None

    def clear(self):
        self._current_solver = None
        self._driver_list.clear()
        self._driven_list.clear()
        self._pose_list.clear()
        self._pose_joints_list.clear()

    def load_solver_settings(self, solver, drivers, driven, poses):
        """
        Display the settings for the specified solver
        :param solver :type RBFNode: solver reference
        :param drivers :type dict: dictionary of driver name: driver data
        :param driven :type dict: dictionary of driven name: driven data
        :param poses :type dict: dictionary of pose data
        """
        self._current_solver = solver
        # Grab the current selection from the driver, driven and pose list
        current_drivers = [i.text() for i in self._driver_list.selectedItems()]
        current_driven = [i.text() for i in self._driven_list.selectedItems()]
        current_poses = [i.text() for i in self._pose_list.selectedItems()]
        current_pose_joints = [i.text() for i in self._pose_joints_list.selectedItems()]

        # Clear the driver, driven and pose lists
        self._driver_list.clear()
        self._driven_list.clear()
        self._pose_list.clear()
        self._pose_joints_list.clear()

        # Iterate through each driver
        for driver_name, driver_data in drivers.items():
            # Create new item widget
            item = QtWidgets.QListWidgetItem(driver_name)
            pose_item = QtWidgets.QListWidgetItem(driver_name)
            pose_item.setStatusTip("Double click to select joint")
            # Set the icon to a joint
            item.setIcon(QtGui.QIcon(":/kinJoint.png"))
            item.setStatusTip("Double click to select joint")
            pose_item.setIcon(QtGui.QIcon(":/kinJoint.png"))
            # Add item to the list
            self._driver_list.addItem(item)
            self._pose_joints_list.addItem(pose_item)
            # Set the item data so it can be referenced later
            item.setData(QtCore.Qt.UserRole, driver_data)
            pose_item.setData(QtCore.Qt.UserRole, driver_data)

        # Iterate through the driven transforms transform nodes
        for driven_name, driven_data in driven.items():
            # Create new item widget
            item = QtWidgets.QListWidgetItem(driven_name)
            pose_item = QtWidgets.QListWidgetItem(driven_name)
            pose_item.setStatusTip("Double click to select joint")
            # Store the solver and item type
            item.setData(QtCore.Qt.UserRole, driven_data)
            item.setStatusTip("Double click to select joint")
            pose_item.setData(QtCore.Qt.UserRole, driven_data)
            # Set the icon to a joint
            item.setIcon(QtGui.QIcon(":/kinJoint.png"))
            pose_item.setIcon(QtGui.QIcon(":/kinJoint.png"))
            # Add item to the list
            self._driven_list.addItem(item)
            self._pose_joints_list.addItem(pose_item)

        # Iterate through the poses
        for pose, pose_data in poses.items():
            # Create item and add it to the list
            item = QtWidgets.QListWidgetItem(pose)
            self._pose_list.addItem(item)
            muted = not pose_data.get("target_enable", True)
            if muted:
                font = item.font()
                font.setStrikeOut(True)
                item.setFont(font)
            # Set icon to a pose
            item.setIcon(QtGui.QIcon(":/p-head.png"))

        # Create a map between widgets: names of previously selected items
        existing_selection_to_list_map = {
            self._driver_list: current_drivers,
            self._driven_list: current_driven,
            self._pose_list: current_poses,
            self._pose_joints_list: current_pose_joints,
        }
        # Iterate through the widgets: target selections
        for list_ref, current in existing_selection_to_list_map.items():
            # Block signals so we don't fire any selection changed events
            list_ref.blockSignals(True)
            # Iterate through the list widget
            for i in range(list_ref.count()):
                # Get the item
                item = list_ref.item(i)
                # Check if the text is in the list of currently selected items (case sensitive) and select/deselect
                # as appropriate
                if item.text() in current:
                    item.setSelected(True)
                else:
                    item.setSelected(False)
            # Unblock the signals
            list_ref.blockSignals(False)

    def set_editing(self, editing: bool) -> None:
        for button in self._buttons:
            button.setEnabled(editing)

    # ================================================ Drivers ======================================================= #
    def get_drivers(self, selection: bool = True):
        if selection:
            return [item.text() for item in self._driver_list.selectedItems()]
        else:
            return [self._driver_list.item(i).text() for i in range(self._driver_list.count())]

    def _add_drivers(self):
        """
        Add drivers.
        """
        # Emit nothing so that the current scene selection will be used
        if self._current_solver:
            self.event_add_drivers.emit(self._current_solver)

    def _remove_drivers(self):
        """
        Remove the specified drivers
        """
        # Emit the selected drivers to be deleted
        if self._current_solver:
            self.event_remove_drivers.emit(
                self._current_solver, [i.data(QtCore.Qt.UserRole) for i in self._driver_list.selectedItems()]
            )

    # ================================================ Driven ======================================================== #
    def get_driven(self, selection: bool = True):
        if selection:
            return [item.text() for item in self._driven_list.selectedItems()]
        else:
            return [self._driven_list.item(i).text() for i in range(self._driven_list.count())]

    def _add_driven(self):
        """
        Add driven nodes to the solver
        """
        # Emit no driven nodes so that it uses scene selection and set edit mode to true
        if self._current_solver:
            self.event_add_driven.emit(self._current_solver, True)

    def _remove_driven(self):
        """
        Remove driven transforms from the specified solver
        """
        # Get currently selected driven items
        items = self._driven_list.selectedItems()
        # Exit early if nothing is selected
        if not items or not self._current_solver:
            return
        # Get the solver for the last item (they should all have the same solver)
        # Trigger event to remove specified nodes for the solver
        self.event_remove_driven.emit(self._current_solver, [i.text() for i in items])

    # ================================================= Poses ======================================================== #

    def get_poses(self, selection: bool = True):
        """
        Get the selected poses
        :return :type list: list of selected pose names
        """
        if selection:
            return [item.text() for item in self._pose_list.selectedItems()]
        else:
            return [self._pose_list.item(i).text() for i in range(self._pose_list.count())]

    def _create_pose(self):
        """
        Create a new pose
        """
        # Display popup to get pose name
        pose_name, ok = QtWidgets.QInputDialog.getText(self, "Create Pose", "Pose Name:")

        if pose_name and self._current_solver:
            # If a pose name is specified, create pose
            self.event_add_pose.emit(self._current_solver, pose_name)

    def _delete_pose(self):
        """
        Delete the selected poses
        """
        # Get the currently selected poses
        poses = self.get_poses()
        # Exit early if nothing is selected
        if not poses or not self._current_solver:
            return
        # Block the signals to stop UI event updates
        self._pose_list.blockSignals(True)
        # For each selected pose, delete it
        for pose_name in poses:
            self.event_delete_pose.emit(self._current_solver, pose_name)

        self._pose_list.blockSignals(False)

    def _mute_pose(self):
        """
        Toggles the muted status for the poses the selected poses
        """
        # Get the pose selection
        poses = self.get_poses()
        # Exit early if nothing is selected
        if not poses or not self._current_solver:
            return

        for pose_name in poses:
            self.event_mute_pose.emit(self._current_solver, pose_name, None)

    def _pose_selection_changed(self):
        """
        On pose selection changed, go to the new pose
        """
        # Get the current pose selection
        selected_poses = self.get_poses()
        if selected_poses and self._current_solver:
            # Get the last pose
            selected_pose = selected_poses[-1]
            self.event_go_to_pose.emit(self._current_solver, selected_pose)

    def _rename_pose(self):
        """
        Rename the currently selected pose
        """
        # Get the current pose selection
        poses = self.get_poses()
        # Exit early if nothing is selected
        if not poses or not self._current_solver:
            return
        # Get the last selected pose name
        pose_name = poses[-1]

        # Create a popup to get the new pose name
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename Pose", "New Pose Name:")

        # Exit if no new name is specified
        if not new_name:
            return

        # Get the existing pose names
        existing_names = [self._pose_list.item(i).text().lower() for i in range(self._pose_list.count())]
        # If the pose name already exists, log it and exit
        if new_name.lower() in existing_names:
            LOG.error(f"Pose '{new_name}' already exists")
            return
        # Pose doesn't already exist, rename it
        self.event_rename_pose.emit(self._current_solver, pose_name, new_name)

    def _select_in_scene(self, list_widget=None, item=None):
        """
        Select the specified items in the scene
        :param list_widget :type QtWidgets.QListWidget or None: optional list widget to select from
        :param item :type QtWidgets.QListWidgetItem or None: optional item to select
        """
        # If no item is provided, select all the items from the list widget specified
        if item is None:
            items = [list_widget.item(i).text() for i in range(list_widget.count())]
        # Otherwise select the current item
        else:
            items = [item.text()]
        # If we have items, select them
        if items:
            self.event_select.emit(items)

    def _update_pose(self):
        """
        Update the pose for the given solver
        """

        # Get the current pose selection
        poses = self.get_poses()
        # Exit early if nothing is selected
        if not poses or not self._current_solver:
            return
        # Get the last selected pose name
        pose_name = poses[-1]

        # Update the pose
        self.event_update_pose.emit(self._current_solver, pose_name)

    def _show_mirror_solver_options(self):
        self._mirror_options_dialog = mirror_options_dialog.MirrorOptionsDialog(parent=self)
        self._mirror_options_dialog.event_mirror_solver.connect(self._mirror_solver)
        self._mirror_options_dialog.exec_()

    def _mirror_solver(
        self,
        solver_search: str,
        solver_replace: str,
        joint_name_search: str,
        joint_name_replace: str,
        pose_name_search: str = "",
        pose_name_replace: str = "",
        mirror_rotation_axis: str = "x",
        mirror_translation_axis: str = "x",
        solver_use_regex: bool = False,
        joint_use_regex: bool = False,
        pose_use_regex: bool = False,
    ):
        selected_items = [i.text() for i in self._pose_list.selectedItems()]

        for pose in selected_items:
            self.event_mirror_pose.emit(
                self._current_solver,
                pose,
                solver_search,
                solver_replace,
                joint_name_search,
                joint_name_replace,
                pose_name_search,
                pose_name_replace,
                mirror_rotation_axis,
                mirror_translation_axis,
                solver_use_regex,
                joint_use_regex,
                pose_use_regex,
            )
