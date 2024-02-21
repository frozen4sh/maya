import maya.cmds as cmds

class BoneControllerUI:
    def __init__(self):
        self.window_name = "boneControllerWindow"
        self.column_layout = "columnLayout"
        self.bone_list = ["Bone1", "Bone2", "Bone3"]  # Replace with your bone names
        self.controller_list = ["Controller1", "Controller2", "Controller3"]  # Replace with your controller names
        self.bone_text_scroll_list = "boneTextScrollList"
        self.controller_text_scroll_list = "controllerTextScrollList"

    def create_ui(self):
        # Check if the window exists and delete it if it does
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name, window=True)

        # Create the main window
        cmds.window(self.window_name, title="Bone Controller Connect", widthHeight=(450, 250))

        # Create a column layout for the UI
        cmds.columnLayout(self.column_layout, adjustableColumn=True)

        # Create headers for "Bone" and "Controller" columns
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(200, 200), columnAttach=[(1, 'both', 0), (2, 'both', 0)])
        cmds.text(label="Bone", align="center", font="boldLabelFont")
        cmds.text(label="Controller", align="center", font="boldLabelFont")
        cmds.setParent(self.column_layout)

        # Create text scroll lists for bones and controllers
        self.bone_text_scroll_list = cmds.textScrollList(
            numberOfRows=8,
            allowMultiSelection=False,
            append=self.bone_list,
            width=200
        )
        self.controller_text_scroll_list = cmds.textScrollList(
            numberOfRows=8,
            allowMultiSelection=False,
            append=self.controller_list,
            width=200
        )

        # Add buttons on the right side
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 100, 100),
                       columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'both', 0)])
        cmds.button(label="Add Bone", command=self.add_bone_button_callback, width=100)
        cmds.button(label="Add Controller", command=self.add_controller_button_callback, width=100)
        cmds.button(label="Clear Lists", command=self.clear_lists_button_callback, width=100)
        cmds.setParent(self.column_layout)

        # Connect button at the bottom
        cmds.button(label="Connect", command=self.connect_button_callback)

        # Show the window
        cmds.showWindow(self.window_name)

    def add_bone_button_callback(self, *args):
        # Get the selected bone
        selected_bone = cmds.ls(selection=True, type="joint")
        if not selected_bone:
            cmds.warning("Please select a bone.")
            return

        # Add the selected bone to the bone_list
        self.bone_list.append(selected_bone[0])

        # Update the bone text scroll list with the new data
        self.update_text_scroll_list(self.bone_text_scroll_list, self.bone_list)

        print(f"Bone '{selected_bone[0]}' added to the list.")

    def add_controller_button_callback(self, *args):
        # Get the selected controller
        selected_controller = cmds.ls(selection=True, type="transform")
        if not selected_controller:
            cmds.warning("Please select a controller.")
            return

        # Add the selected controller to the controller_list
        self.controller_list.append(selected_controller[0])

        # Update the controller text scroll list with the new data
        self.update_text_scroll_list(self.controller_text_scroll_list, self.controller_list)

        print(f"Controller '{selected_controller[0]}' added to the list.")

    def update_text_scroll_list(self, text_scroll_list, data_list):
        # Update the text scroll list with the given data list
        cmds.textScrollList(text_scroll_list, edit=True, removeAll=True)
        cmds.textScrollList(text_scroll_list, edit=True, append=data_list)

    def clear_lists_button_callback(self, *args):
        # Clear both text scroll lists
        self.bone_list = []
        self.controller_list = []
        self.update_text_scroll_list(self.bone_text_scroll_list, self.bone_list)
        self.update_text_scroll_list(self.controller_text_scroll_list, self.controller_list)

        print("Lists cleared.")

    def connect_button_callback(self, *args):
        # Connect each pair of bone and controller using parent constraint
        for bone, controller in zip(self.bone_list, self.controller_list):
            if cmds.objExists(bone) and cmds.objExists(controller):
                # Check if the pair exists and apply parent constraint
                constraint = cmds.parentConstraint(bone, controller, maintainOffset=True)
                print(f"Connected: {bone} -> {controller}")
            else:
                cmds.warning(f"Skipping connection for pair: {bone} -> {controller}. One or both objects do not exist.")

        print("Connection completed.")


# Create an instance of the BoneControllerUI class and show the UI
bone_controller_ui = BoneControllerUI()
bone_controller_ui.create_ui()
