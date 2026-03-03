import re
import maya.cmds as cmds

def increment_version():
    # Get the current file name
    current_file_path = cmds.file(query=True, sceneName=True)
   
    if not current_file_path:
        print("No scene is currently open. Please open a scene and run the script.")
        return

    # Extract information from the current file name using a regular expression
    match = re.match(r'^(.*?_w)(\d+)(\.mb)$', current_file_path)
   
    if not match:
        print(f"Unable to extract version number from file: {current_file_path}")
        return
   
    prefix, version, extension = match.groups()
   
    # Increment the version number
    new_version = int(version) + 1
   
    # Construct the new file name with the incremented version
    new_file_path = f"{prefix}{new_version:02d}{extension}"
   
    # Save the current scene as the new file
    cmds.file(rename=new_file_path)
    cmds.file(save=True, type='mayaBinary')
   
    print(f"File saved as: {new_file_path}")

# Example usage
increment_version()