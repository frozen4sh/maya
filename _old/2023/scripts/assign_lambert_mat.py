## 선택한 모든 메시들 램버트 생성 _mat 로 생성해서 적용 


import maya.cmds as cmds

def create_and_assign_material():
    # Get selected meshes
    selected_objects = cmds.ls(selection=True, type='transform')
    
    for obj in selected_objects:
        # Check if the object has a shape (i.e., is a mesh)
        shapes = cmds.listRelatives(obj, shapes=True)
        if shapes:
            # Create a new Lambert material
            lambert_material = cmds.shadingNode('lambert', asShader=True)
            
            # Generate material name based on the mesh name
            material_name = obj + "_mat"
            
            # Create a shading group and set its attributes
            shading_group = cmds.setAttr(lambert_material + ".color", 0.5, 0.5, 0.5, type="double3")
            
            # Rename the material to the mesh name with '_mat' suffix
            cmds.rename(lambert_material, material_name)
            
            # Assign the newly created material to the mesh
            cmds.select(obj)
            cmds.hyperShade(assign=material_name)

# Execute the function
create_and_assign_material()
