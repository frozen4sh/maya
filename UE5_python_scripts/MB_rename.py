from pyfbsdk import *

def find_and_replace_names(find_str, replace_str):
    # Get the root of the current scene
    root_model = FBSystem().Scene.RootModel
    
    def traverse_and_rename(node):
        if find_str in node.Name:
            node.Name = node.Name.replace(find_str, replace_str)
        
        # Recurse through all children
        for child in node.Children:
            traverse_and_rename(child)
            
    traverse_and_rename(root_model)
    print("Find and Replace complete.")

# Modify the strings below to your needs
find_and_replace_names("SearchString", "ReplacementString")
