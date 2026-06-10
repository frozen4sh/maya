# Copyright Epic Games, Inc. All Rights Reserved.

# External
from qtpy import QtGui, QtCore, QtWidgets

# Internal
from mh_pose_editor.view.dialogs import mirror_options_dialog


class RBFPanel(QtWidgets.QWidget):
    # Solver Signals
    event_create_solver = QtCore.Signal(str)
    event_delete_solver = QtCore.Signal(object)
    event_edit_solver = QtCore.Signal(object, bool)
    event_mirror_solver = QtCore.Signal(object, str, str, str, str, str, str, str, str, bool, bool, bool)
    event_refresh_solvers = QtCore.Signal()
    event_set_current_solver = QtCore.Signal(object)

    # Utility Signals
    event_select = QtCore.Signal(list)

    def __init__(self):
        super().__init__()
        panel_layout = QtWidgets.QVBoxLayout()
        self.setLayout(panel_layout)

        solver_layout = QtWidgets.QVBoxLayout()

        self._group_box = QtWidgets.QGroupBox("RBF Solvers:")
        self._group_box.setLayout(solver_layout)
        panel_layout.addWidget(self._group_box)

        self._solver_list = QtWidgets.QListWidget()
        self._solver_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._solver_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._solver_list.itemSelectionChanged.connect(self._solver_selection_changed)
        self._solver_list.itemDoubleClicked.connect(self._select_in_scene)
        solver_layout.addWidget(self._solver_list)

        self._edit_button = QtWidgets.QPushButton("Edit Selected")
        self._edit_button.clicked.connect(self._edit_solver_toggle)
        solver_layout.addWidget(self._edit_button)

        top_button_layout = QtWidgets.QHBoxLayout()
        solver_layout.addLayout(top_button_layout)

        self._refresh_button = QtWidgets.QPushButton("Refresh")
        self._refresh_button.clicked.connect(self._refresh_solvers)
        top_button_layout.addWidget(self._refresh_button)

        self._mirror_button = QtWidgets.QPushButton("Mirror")
        self._mirror_button.clicked.connect(self._show_mirror_solver_options)
        top_button_layout.addWidget(self._mirror_button)

        bottom_button_layout = QtWidgets.QHBoxLayout()
        solver_layout.addLayout(bottom_button_layout)

        self._create_button = QtWidgets.QPushButton("Create")
        self._create_button.clicked.connect(self._create_solver)
        bottom_button_layout.addWidget(self._create_button)

        self._delete_button = QtWidgets.QPushButton("Delete")
        self._delete_button.clicked.connect(self._delete_solver)
        bottom_button_layout.addWidget(self._delete_button)

        self._editing_solver = None
        self._rbf_settings_panel = None
        self._mirror_options_dialog = None
        self._edit_mode_buttons = [self._delete_button, self._create_button, self._refresh_button, self._mirror_button]

    def add_rbf_solver(self, solver, edit=False, select=False):
        """
        Add a solver to the view
        :param solver :type rbf_node.RBFNode: solver reference
        :param edit :type bool: is this solver in edit mode?
        :param select :type bool: should this be selected
        """
        # Create a new widget item with the solver name
        item = QtWidgets.QListWidgetItem(str(solver))
        item.setStatusTip("Double click to select RBF solver node")
        # Add the solver and the edit status as custom data on the item
        item.setData(QtCore.Qt.UserRole, {"solver": solver, "edit": edit})
        # If we are editing, keep track of it
        if edit:
            self._editing_solver = solver

            for button in self._edit_mode_buttons:
                button.setEnabled(not edit)

        # Add the item to the solver list
        self._solver_list.addItem(item)
        item.setSelected(select)

    def clear(self):
        self._solver_list.clear()
        for button in self._edit_mode_buttons:
            button.setEnabled(True)
        # Clear the current solver
        self._editing_solver = None
        # Revert the button text
        self._edit_button.setText("Edit Selected")

    def delete_solver(self, solver):
        """
        Delete the specified solver from the view
        :param solver :type rbf_node.RBFNode: solver ref
        """
        # Iterate through the solvers
        for i in range(self._solver_list.count()):
            # Get the item
            item = self._solver_list.item(i)
            # If the solver matches the solver from the item data
            if item.data(QtCore.Qt.UserRole)["solver"] == solver:
                # Remove the item from the list and break early
                self._solver_list.takeItem(self._solver_list.row(item))
                break

    def edit_solver(self, solver, edit=False):
        """
        Set the UI in solver edit mode or finish editing.
        :param solver :type str: name of the solver to edit or finish editing
        :param edit :type bool: True = edit mode, False = finish editing
        """
        # Iterate through the solvers
        for i in range(self._solver_list.count()):
            # Get the widget item
            item = self._solver_list.item(i)
            # If the solver matches the item data, break
            if item.data(QtCore.Qt.UserRole)["solver"] == solver:
                break
        # No match found, return early
        else:
            return
        # Grab the item data for the item
        item_data = item.data(QtCore.Qt.UserRole)

        # If edit mode
        if edit:
            # If we are already editing a solver, finish editing that one first
            if self._editing_solver is not None:
                # Update the icon
                self._editing_solver.setIcon(QtGui.QIcon())
                # Finish editing
                self.event_edit_solver.emit(item_data["solver"], False)
            # Store the new item as the current edited solver
            self._editing_solver = item
            # Update the button text
            self._edit_button.setText("Finish Editing")
            # Set the edit icon
            item.setIcon(QtGui.QIcon(":/fileTextureEdit.png"))
        else:
            # Clear the current solver
            self._editing_solver = None
            # Revert the button text
            self._edit_button.setText("Edit Selected")
            # Clear the edit icon
            item.setIcon(QtGui.QIcon())

        # Update the item data with the new edit status
        item_data["edit"] = edit
        # Set the item data
        item.setData(QtCore.Qt.UserRole, item_data)

        # Update the solver related ui elements with the current edit status
        if self._rbf_settings_panel:
            self._rbf_settings_panel.set_editing(edit)

        for button in self._edit_mode_buttons:
            button.setEnabled(not edit)

    def get_solvers(self, selection: bool = False):
        if selection and self._solver_list.selectedItems():
            return [item.data(QtCore.Qt.UserRole)["solver"] for item in self._solver_list.selectedItems()]

        else:
            return [
                self._solver_list.item(i).data(QtCore.Qt.UserRole)["solver"] for i in range(self._solver_list.count())
            ]

    def get_solver_names(self, selection: bool = False):
        if selection:
            return [item.text() for item in self._solver_list.selectedItems()]

        else:
            return [self._solver_list.item(i).text() for i in range(self._solver_list.count())]

    def set_settings_panel(self, rbf_settings_panel):
        self._rbf_settings_panel = rbf_settings_panel

    def _create_solver(self):
        """
        Create a new solver with the given name
        """
        # Popup input widget to get the solver name
        interp_name, ok = QtWidgets.QInputDialog.getText(self, "Create RBF Solver", "RBF Solver Name:")

        # If no name, exit
        if not interp_name:
            return

        # Trigger solver creation
        self.event_create_solver.emit(interp_name)

    def _delete_solver(self):
        """
        Delete selected solvers
        """
        # Get the current solver selection
        selected_items = self._solver_list.selectedItems()

        selected_solvers = []
        # Iterate through the selection in reverse
        for item in reversed(selected_items):
            # Grab the solver from the item data
            selected_solvers.append(item.data(QtCore.Qt.UserRole)["solver"])

        # Delete the solvers from the backend
        for solver in selected_solvers:
            self.event_delete_solver.emit(solver)

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
        selected_items = self._solver_list.selectedItems()

        selected_solvers = []
        # Iterate through the selection in reverse
        for item in selected_items:
            # Grab the solver from the item data
            selected_solvers.append(item.data(QtCore.Qt.UserRole)["solver"])

        for solver in selected_solvers:
            self.event_mirror_solver.emit(
                solver,
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

    def _edit_solver_toggle(self):
        """
        Toggle edit mode for the currently selected driver
        """
        # Grab the current selection
        selection = self._solver_list.selectedItems()
        if selection:
            # Grab the last item
            item = selection[-1]
            # Get the item data
            item_data = item.data(QtCore.Qt.UserRole)
            # Get the solver
            solver = item_data["solver"]
            # Trigger edit mode enabled/disabled depending on the solvers current edit state
            self.event_edit_solver.emit(solver, not item_data.get("edit", False))

    def _refresh_solvers(self):
        """
        Refresh the solver list
        """
        self.event_refresh_solvers.emit()

    def _select_in_scene(self, item=None):
        """
        Select the specified items in the scene
        :param item :type QtWidgets.QListWidgetItem or None: optional item to select
        """
        # If no item is provided, select all the items from the list widget specified
        if item is None:
            items = [
                self._solver_list.item(i).data(QtCore.Qt.UserRole)["solver"] for i in range(self._solver_list.count())
            ]
        # Otherwise select the current item
        else:
            items = [item.data(QtCore.Qt.UserRole)["solver"]]
        # If we have items, select them
        if items:
            self.event_select.emit(items)

    def _solver_selection_changed(self):
        """
        When the solver selection changes, update the driver/driven and poses list accordingly
        """
        # Get the current selection
        items = self._solver_list.selectedItems()
        # If we have a selection
        if items:
            # Grab the last selected item
            item = items[-1]
            # Grab the item data
            item_data = item.data(QtCore.Qt.UserRole)
            # Set the current solver to the solver associated with this widget
            self.event_set_current_solver.emit(item_data["solver"])
            # Get the solvers edit status
            edit = item_data.get("edit", False)
            # Update the solver related ui elements with the current edit status
            if self._rbf_settings_panel:
                self._rbf_settings_panel.set_editing(edit)
            # If we are in edit mode
            if edit:
                # Update the button
                self._edit_button.setText("Finish Editing".format())
                # Set the icon
                item.setIcon(QtGui.QIcon(":/fileTextureEdit.png"))
        # No selection, clear all the lists
        else:
            if self._rbf_settings_panel:
                self._rbf_settings_panel.set_editing(False)
