# Copyright Epic Games, Inc. All Rights Reserved.

# Built-in
import traceback
from typing import TYPE_CHECKING, Dict, List, Tuple, Optional
from functools import partial

# External
from maya import cmds

# Internal
from mh_pose_editor.log import LOG
from mh_pose_editor.model import exceptions, base_extension

if TYPE_CHECKING:
    from qtpy import QtWidgets

    from mh_pose_editor.model import context, rbf_node


class BakePosesToTimeline(base_extension.PoseEditorExtension):
    __category__ = "Core"

    @property
    def view(self) -> "QtWidgets.QWidget":
        if self._view is not None:
            return self._view

        from qtpy import QtWidgets

        self._view: QtWidgets.QWidget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self._view.setLayout(layout)

        label = QtWidgets.QLabel("Copy/Paste Driven Transforms")
        layout.addWidget(label)

        button_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(button_layout)

        copy_button = QtWidgets.QPushButton("Copy")
        copy_button.clicked.connect(partial(self.copy_driven_trs, None))
        button_layout.addWidget(copy_button)

        paste_button = QtWidgets.QPushButton("Paste")
        button_layout.addWidget(paste_button)

        spin_label = QtWidgets.QLabel("Multiplier: ")
        button_layout.addWidget(spin_label)

        self._spin_box = QtWidgets.QDoubleSpinBox()
        self._spin_box.setMinimum(0.01)
        self._spin_box.setSingleStep(0.1)
        self._spin_box.setValue(1.0)
        button_layout.addWidget(self._spin_box)

        paste_button.clicked.connect(self._paste_driven_trs)

        return self._view

    def execute(self, context: Optional["context.PoseEditorContext"] = None, **kwargs) -> None:
        copy = kwargs.get("copy", False)
        driver = kwargs.get("driver", True)
        multiplier = kwargs.get("multiplier", 1.0)
        if context is None:
            context = self.api.get_context()

        if context.current_solver is not None:
            if copy:
                if driver:
                    self.copy_driver_trs()
                else:
                    self.copy_driven_trs()
            else:
                if driver:
                    self.paste_driver_trs(multiplier=multiplier)
                else:
                    self.paste_driven_trs(multiplier=multiplier)

    def copy_driven_trs(self, solver: Optional["rbf_node.RBFNode"] = None) -> None:
        """
        Copy the driven transforms translate, rotate and scale for the specified solver
        :param solver :type rbf_node.RBFNode: solver reference
        """
        context = self.api.get_context()
        solver = solver or context.current_solver
        if solver:
            CopyPasteTRS.copy_driven(solver)

    def paste_driven_trs(self, multiplier: float = 1.0, solver: Optional["rbf_node.RBFNode"] = None) -> None:
        """
        Paste the driven transforms translate, rotate and scale based on the multiplier specified
        :param multiplier :type float: scale multiplier
        :param solver :type rbf_node.RBFNode: solver reference
        """
        context = self.api.get_context()
        solver = solver or context.current_solver
        if not solver:
            return

        edit_status = self.api.get_solver_edit_status(solver=solver)
        if not edit_status:
            self.api.edit_solver(edit=True, solver=solver)
        CopyPasteTRS.paste_driven(multiplier=multiplier)

    def copy_driver_trs(self, solver: Optional["rbf_node.RBFNode"] = None) -> None:
        """
        Copy the driver transforms translate, rotate and scale for the specified solver
        :param solver :type rbf_node.RBFNode: solver reference
        """
        context = self.api.get_context()
        # Get the solver if it hasn't been specified
        solver = solver or context.current_solver
        if solver:
            # Copy the driver transforms
            CopyPasteTRS.copy_driver(solver)

    def paste_driver_trs(self, multiplier: float = 1.0) -> None:
        """
        Paste the driver transforms rotate and scale based on the multiplier specified
        :param multiplier :type float: scale multiplier
        """
        CopyPasteTRS.paste_driver(multiplier=multiplier)

    def _paste_driven_trs(self):
        self.paste_driven_trs(self._spin_box.value(), None)


class TRSError(exceptions.PoseEditorException):
    pass


class CopyPasteTRS:
    """
    Class wrapper for copying and pasting TRS data
    """

    # Dicts to store the driver and driven data. Driver data is only used when auto generating poses
    TRS_DRIVEN_DATA: Dict[str, Dict[str, List[float]]] = {}
    TRS_DRIVER_DATA: Dict[str, Dict[str, List[float]]] = {}

    @classmethod
    def copy_driven(cls, solver: "rbf_node.RBFNode") -> None:
        """
        Copy the driven transforms TRS data for the specified solver
        :param solver :type rbf_node.RBFNode: solver reference
        """
        cls._copy(
            transforms=solver.driven_joints(),
            target_datastore=cls.TRS_DRIVEN_DATA,
        )

    @classmethod
    def paste_driven(cls, multiplier: float = 1.0) -> None:
        """
        Paste the copied driven values onto the driven with the specified modifier
        :param multiplier :type float: multiplier value
        """
        cls._paste(multiplier=multiplier, target_datastore=cls.TRS_DRIVEN_DATA)

    @classmethod
    def copy_driver(cls, solver: "rbf_node.RBFNode") -> None:
        """
        Copy the driver transforms TRS data for the specified solver
        :param solver :type rbf_node.RBFNode: solver reference
        """
        cls._copy(transforms=solver.drivers(), target_datastore=cls.TRS_DRIVER_DATA, attributes=("rotate", "scale"))

    @classmethod
    def paste_driver(cls, multiplier: float = 1.0) -> None:
        """
        Paste the copied driver values onto the driver with the specified modifier
        :param multiplier :type float: multiplier value
        """
        cls._paste(multiplier=multiplier, target_datastore=cls.TRS_DRIVER_DATA)

    @classmethod
    def _copy(
        cls,
        transforms: List[str],
        target_datastore: Dict[str, Dict[str, List[float]]],
        attributes: Optional[Tuple[str, ...]] = None,
    ) -> None:
        """
        Copy the specified transforms attributes to the specified datastore
        :param transforms :type list: list of maya transform nodes
        :param target_datastore :type dict: reference to cls.TRS_DRIVER_DATA or cls.TRS_DRIVEN_DATA
        :param attributes :type list: list of attribute names to store
        """
        # If no attributes are specified, use TRS
        if not attributes:
            attributes = ("translate", "rotate", "scale")
        # Clear the datastore before we copy
        target_datastore.clear()
        # For each transform, get the specified attributes and store them in a dictionary
        for transform in transforms:
            target_datastore[transform] = {attr: cmds.getAttr(f"{transform}.{attr}")[0] for attr in attributes}

        LOG.info(f"Successfully copied TRS for {transforms}")

    @classmethod
    def _paste(cls, multiplier: float, target_datastore: Dict[str, Dict[str, List[float]]]) -> None:
        """
        Paste the attributes from the target_datastore multiplied by the given multiplier
        :param multiplier :type float: multiplier value
        :param target_datastore : type dict: reference to cls.TRS_DRIVER_DATA or cls.TRS_DRIVEN_DATA
        """
        # If the target datastore is empty, we can't paste
        if not target_datastore:
            raise TRSError("No data has been copied. Unable to paste")

        # Iterate through the items in the datastore
        for transform, data in target_datastore.items():
            # Iterate through the attribute names and values in the datastore
            for attr, values in data.items():
                # Set the attribute to the multiplied value
                try:
                    cmds.setAttr(
                        f"{transform}.{attr}", values[0] * multiplier, values[1] * multiplier, values[2] * multiplier
                    )
                except AttributeError:
                    traceback.print_exc()

            # Calculate and set the scale
            scale = [((s - 1.0) * multiplier) + 1 for s in data["scale"]]
            try:
                cmds.setAttr(f"{transform}.scale", *scale)
            except AttributeError:
                traceback.print_exc()

        LOG.info(f"Successfully pasted TRS with multiplier: {multiplier} for {list(target_datastore.keys())}")
