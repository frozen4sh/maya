import maya.cmds as cmds
import random

def move_selected_controllers_randomly(move_range):
    # Get the currently selected objects
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.warning("Please select at least one object.")
        return

    for obj in selected_objects:
        # Generate random values for X and Z within the specified range
        random_x = random.uniform(-move_range, move_range)
        random_z = random.uniform(-move_range, move_range)

        # Move the object to the random position along X and Z axes
        cmds.move(random_x, 0, random_z, obj, relative=True)

# Set the move range 아래 수치로 영역 조절 10~100
move_range = 10  # Adjust as needed

# Call the function to move selected controllers randomly along X and Z axes
move_selected_controllers_randomly(move_range)
