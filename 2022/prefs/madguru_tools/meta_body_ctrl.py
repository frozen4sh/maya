import os, sys
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import math

def mgBuildMetaHumansRigCntrls():
    metahuman_skeleton = [
    'root',
    'pelvis',
    'spine_01',
    'spine_02',
    'spine_03',
    'spine_04',
    'spine_05',
    'neck_01',
    'neck_02',
    'head',
    'clavicle_l',
    'clavicle_r',
    'bigtoe_01_l',
    'bigtoe_02_l',
    'indextoe_01_l',
    'indextoe_02_l',
    'middletoe_01_l',
    'middletoe_02_l',
    'ringtoe_01_l',
    'ringtoe_02_l',
    'littletoe_01_l',
    'littletoe_02_l',
    'bigtoe_01_r',
    'bigtoe_02_r',
    'indextoe_01_r',
    'indextoe_02_r',
    'middletoe_01_r',
    'middletoe_02_r',
    'ringtoe_01_r',
    'ringtoe_02_r',
    'littletoe_01_r',
    'littletoe_02_r',
    'pinky_metacarpal_r',
    'pinky_01_r',
    'pinky_02_r',
    'pinky_03_r',
    'ring_metacarpal_r',
    'ring_01_r',
    'ring_02_r',
    'ring_03_r',
    'middle_metacarpal_r',
    'middle_01_r',
    'middle_02_r',
    'middle_03_r',
    'index_metacarpal_r',
    'index_01_r',
    'index_02_r',
    'index_03_r',
    'thumb_01_r',
    'thumb_02_r',
    'thumb_03_r',
    'pinky_metacarpal_l',
    'pinky_01_l',
    'pinky_02_l',
    'pinky_03_l',
    'ring_metacarpal_l',
    'ring_01_l',
    'ring_02_l',
    'ring_03_l',
    'middle_metacarpal_l',
    'middle_01_l',
    'middle_02_l',
    'middle_03_l',
    'index_metacarpal_l',
    'index_01_l',
    'index_02_l',
    'index_03_l',
    'thumb_01_l',
    'thumb_02_l',
    'thumb_03_l',
    ]
    
    metahuman_ctrl_radius = [
    20,
    30,
    20,
    20,
    20,
    20,
    20,
    8,
    8,
    15,
    15,
    15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    1.15,
    ]
    
    dir_str_list = ['l', 'r']
    type_str_list = ['fk', 'ik']
    part_list = ['upperarm', 'lowerarm', 'hand', 'thigh', 'calf', 'foot', 'ball']
    digits_part_list = [['pinky_metacarpal', 'pinky_01', 'pinky_02', 'pinky_03'], ['ring_metacarpal', 'ring_01', 'ring_02', 'ring_03'], ['middle_metacarpal', 'middle_01', 'middle_02', 'middle_03'], ['index_metacarpal', 'index_01', 'index_02', 'index_03'], ['thumb_01', 'thumb_02', 'thumb_03']]
    constrain_parts = ['root', 'pelvis', 'spine', 'neck', 'head', 'clavicle', 'toe', 'metacarpal', 'thumb', 'index', 'middle', 'ring', 'pinky', '_ik_']
    run_script = 1
    user_decision = None

    if cmds.objExists('root_motion') or cmds.objExists('rig_setup') or cmds.objExists('rig_ctrls') or cmds.objExists('DHIbody:root_loc'):
        user_decision = cmds.confirmDialog( title='Confirm', message='Metahuman Body Ctrls found in scene. Delete and rebuild?', button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
    
    if user_decision == 'Yes':
        if cmds.objExists('root_motion'):
           cmds.delete('root_motion')
        if cmds.objExists('rig_setup'):
           cmds.delete('rig_setup')
        if cmds.objExists('rig_ctrls'):
            cmds.delete('rig_ctrls')
        if cmds.objExists('face_gui_custom_labels_sceneConfigurationScriptNode'):
            cmds.delete('face_gui_custom_labels_sceneConfigurationScriptNode')
        if cmds.objExists('face_gui_custom_labels_uiConfigurationScriptNode'):
            cmds.delete('face_gui_custom_labels_uiConfigurationScriptNode')
        if not cmds.objExists('DHIbody:root') and cmds.objExists('DHIbody:root_loc'):
            create_joints_from_fit_skeleton()
        cmds.upAxis(ax='z', rv=True)
        if cmds.objExists('root_drv'):
            cmds.setAttr('root_drv.rotateX', 0)
        if cmds.objExists('headRig_grp'):
            cmds.setAttr('headRig_grp.rotateX', 0)

    if user_decision == 'No':
        run_script = 0
    
    if run_script == 1:
        # load lookdevKit plugin if not already loaded
        if not cmds.pluginInfo('lookdevKit', query=1, loaded=1 ):
            cmds.loadPlugin('lookdevKit')

        # upaxis modification
        cmds.upAxis(ax='z', rv=True)

        # create motion skeleton (duplicate of driver skeleton to drive drv)
        cmds.duplicate('root_drv', n='root_motion', rc=1)

        cmds.select(cl=1)
        cmds.select('root_motion')
        cmds.select(hi=1)

        objLs = cmds.ls(sl=1)
        for num in range(0, len(objLs)):
            obj = objLs[num]
            if not '_motion' in obj:
                cmds.rename(obj, obj.replace(obj.split('_')[-1], 'motion'))
        
        # delete skinning helper bones from mocap skeleton
        delSkel()

        cmds.select(cl=1)
        cmds.select('root_motion')
        cmds.select(hi=1)
        objLs = cmds.ls(sl=1)
    
        # connect skeletons motion and drv
        for obj in objLs:  
            cmds.connectAttr(obj + '.translate', obj.replace('_motion', '_drv') + '.translate', f=1)
            cmds.connectAttr(obj + '.rotate', obj.replace('_motion', '_drv') + '.rotate', f=1)

        # rig setup group
        if not cmds.objExists('rig_setup'):
            cmds.group(n = 'rig_setup', em = 1)
            rig_setup_group = 'rig_setup'
    
        # rig ctrls group
        if not cmds.objExists('rig_ctrls'):
            cmds.group(n='rig_ctrls', em=1)
        else:
            cmds.delete('rig_ctrls')
            cmds.group(n='rig_ctrls', em=1)
        
        ###############################
        # create ik and fk limb joints
        for dir_str in dir_str_list:
            for type_str in type_str_list:
                for num in range(0, len(part_list)):
                    part = part_list[num]
                    cmds.duplicate(part + '_' + dir_str + '_motion', n=part + '_' + dir_str + '_' + type_str + '_motion', po = 1)

                    if num > 0 and not num == 3:
                        if not cmds.listRelatives(part + '_' + dir_str + '_' + type_str + '_motion', p=1)[0] == part_list[num-1] + '_' + dir_str + '_' + type_str + '_motion':
                            cmds.parent(part + '_' + dir_str + '_' + type_str + '_motion', part_list[num-1] + '_' + dir_str + '_' + type_str + '_motion')
                    else:
                        cmds.parent(part + '_' + dir_str + '_' + type_str + '_motion', rig_setup_group)
            
                for part in part_list:
                    cur_str = part + '_' + dir_str + '_' + type_str + '_motion'
                    if part == 'upperarm' or part == 'thigh':
                        cmds.parent(cur_str, cmds.listRelatives(part + '_' + dir_str + '_motion', p=1)[0])
            for part in part_list:
                # create constraints
                constraint_name = part + '_' + dir_str + '_ikfk_motion' + '_orient_con'
                cmds.orientConstraint(part + '_' + dir_str + '_ik_motion', part + '_' + dir_str + '_fk_motion', part + '_' + dir_str + '_motion', n = constraint_name , mo = 1)
                cmds.setAttr(constraint_name + '.' + part + '_' + dir_str + '_ik_motionW0', 0)
                cmds.setAttr(constraint_name + '.' + part + '_' + dir_str + '_fk_motionW1', 1)
                
            # create ik handles
            cmds.ikHandle( sj='upperarm_' + dir_str + '_ik_motion', ee='hand_' + dir_str + '_ik_motion', s = 'sticky', n = 'hand_' + dir_str + '_ikHandle')
            cmds.parent('hand_' + dir_str + '_ikHandle', rig_setup_group)
            cmds.ikHandle( sj='thigh_' + dir_str + '_ik_motion', ee='foot_' + dir_str + '_ik_motion', s = 'sticky', n = 'foot_' + dir_str + '_ikHandle')
            cmds.parent('foot_' + dir_str + '_ikHandle', rig_setup_group)
        
        # create ctrl objects
        for num in range(0, len(metahuman_skeleton)):
            current_joint = metahuman_skeleton[num]
            current_motion_joint = current_joint + '_motion'
            current_ctrl = current_joint + '_ctrl'

            if 'pelvis' in current_ctrl:
                current_ctrl = current_ctrl.replace('pelvis', 'hips')

            if cmds.objExists(current_motion_joint):
                cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = metahuman_ctrl_radius[num], tol = 0, n = current_ctrl)
                cmds.setAttr(current_ctrl+"Shape.lineWidth", 2)
                cmds.parent(current_ctrl, 'rig_ctrls')
            
                #rotate 90 degrees
                if not 'root' in current_ctrl:
                    cmds.setAttr(current_ctrl + '.ry', 90)
                #reset xform
                cmds.makeIdentity(current_ctrl, apply=True, t=1, r=1, s=1, n=0, pn=1)
                #parent con to get into position
                cmds.parentConstraint(current_motion_joint, current_ctrl, n = 'delete_con' )
                cmds.delete('delete_con')
                
                metahuman_offset = create_offset(source_object = current_ctrl, offset_name = current_ctrl.replace('_ctrl', '_offset'))
                
                # collapses rig
                constrain_joint = 0
                for constrain_string in constrain_parts:
                    if constrain_string in current_joint:
                        constrain_joint = 1
                if constrain_joint == 1:
                    cmds.pointConstraint(current_ctrl, current_motion_joint, n = current_ctrl + '_point_con' , mo = 1)
                    cmds.orientConstraint(current_ctrl, current_motion_joint, n = current_ctrl + '_orient_con' , mo = 1)                
                else:
                    cmds.connectAttr(current_ctrl + '.translate', current_motion_joint + '.translate')
                    cmds.connectAttr(current_ctrl + '.rotate', current_motion_joint + '.rotate')

        #parent ctrl
        for num in range(0, len(metahuman_skeleton)):
            current_joint = metahuman_skeleton[num]
            current_motion_joint = current_joint + '_motion'
            current_ctrl = current_joint + '_ctrl'
            current_offset = current_joint + '_offset'

            if 'pelvis' in current_ctrl:
                current_ctrl = current_ctrl.replace('pelvis', 'hips')

            if cmds.objExists(current_offset):
                if cmds.listRelatives(current_motion_joint, p=1):
                    parent_ctrl = (cmds.listRelatives(current_motion_joint, p=1)[0]).replace('_motion', '_ctrl')
                    if 'pelvis' in parent_ctrl:
                        parent_ctrl = parent_ctrl.replace('pelvis', 'hips')
                    if cmds.objExists(parent_ctrl):
                        cmds.parent(current_offset, parent_ctrl)
                    else:
                        if 'metacarpal' in current_ctrl or 'thumb_01_' in current_ctrl:
                            if '_r_' in current_ctrl:
                                cmds.parentConstraint('hand_r_motion', current_ctrl.replace('_ctrl', '_offset'), mo=1)
                            if '_l_' in current_ctrl:
                                cmds.parentConstraint('hand_l_motion', current_ctrl.replace('_ctrl', '_offset'), mo=1)
                        if 'toe' in current_ctrl:
                            if '_r_' in current_ctrl:
                                cmds.parentConstraint('ball_r_motion', current_ctrl.replace('_ctrl', '_offset'), mo=1)
                            if '_l_' in current_ctrl:
                                cmds.parentConstraint('ball_l_motion', current_ctrl.replace('_ctrl', '_offset'), mo=1)
                            

            
            if 'head' in current_ctrl or 'spine' in current_ctrl or 'clavicle' in current_ctrl:
                makeNode = str(findMakeNode(current_ctrl, 'makeNurbCircle'))
                if makeNode!='None':
                    cmds.setAttr (makeNode + '.degree', 1)
                    cmds.setAttr (makeNode + '.sections', 6)

            
            # color ctrl objects
            if '_r_' in current_ctrl:
                cmds.setAttr(current_ctrl + 'Shape.overrideEnabled', 1)
                cmds.setAttr(current_ctrl + 'Shape.overrideRGBColors', 1)
                cmds.setAttr(current_ctrl + 'Shape.overrideColorRGB', 0.5, 0.0, 0.0)
            
            if '_l_' in current_ctrl:
                cmds.setAttr(current_ctrl + 'Shape.overrideEnabled', 1)
                cmds.setAttr(current_ctrl + 'Shape.overrideRGBColors', 1)
                cmds.setAttr(current_ctrl + 'Shape.overrideColorRGB', 0.0, 0.0, 0.5)
            
            if not '_l_' in current_ctrl and not '_r_' in current_ctrl:
                cmds.setAttr(current_ctrl + 'Shape.overrideEnabled', 1)
                cmds.setAttr(current_ctrl + 'Shape.overrideRGBColors', 1)
                cmds.setAttr(current_ctrl + 'Shape.overrideColorRGB', 1.0, 0.25, 0.0)

            attribute_cleanup(object=current_ctrl, translate_key = 0, translate_visible = 0, translate_lock = 1, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 0, scale_visible = 0 , scale_lock = 1)

        #########################
        # create additional ctrls
        attr_list = ['tx', 'ty', 'tz', 'sx', 'sy', 'sz']
        
        #############
        # global ctrl
        str_val = 'global'
        cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 50, tol = 0, n = str_val + '_ctrl')
        cmds.setAttr(str_val + '_ctrl' + "Shape.lineWidth", 2)

        makeNode = str(findMakeNode(str_val + '_ctrl', 'makeNurbCircle'))
        if makeNode!='None':
            cmds.setAttr (makeNode + '.degree', 1)
            cmds.setAttr (makeNode + '.sections', 6)
        cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideEnabled', 1)
        cmds.setAttr(str_val + '_ctrl'  + 'Shape.overrideRGBColors', 1)
        cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.75, 0.75, 0.0)    
        cmds.parent(str_val + '_ctrl', 'rig_ctrls')
        
        metahuman_offset = create_offset(source_object = str_val + '_ctrl', offset_name = str_val + '_ctrl'.replace('_ctrl', '_offset'))

        attribute_cleanup(object=str_val+'_ctrl', translate_key = 1, translate_visible = 0, translate_lock = 0, rotation_key = 1, rotation_visible = 0, rotation_lock = 0, scale_key = 1, scale_visible = 1 , scale_lock = 1)

        ##################    
        # body offset ctrl
        cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 30, tol = 0, n = 'body_offset_ctrl')
        cmds.setAttr('body_offset_ctrl'+"Shape.lineWidth", 2)
        makeNode = str(findMakeNode('body_offset_ctrl', 'makeNurbCircle'))
        if makeNode!='None':
            cmds.setAttr (makeNode + '.degree', 1)
            cmds.setAttr (makeNode + '.sections', 6)
        cmds.setAttr('body_offset_ctrl' + 'Shape.overrideEnabled', 1)
        cmds.setAttr('body_offset_ctrl' + 'Shape.overrideRGBColors', 1)
        cmds.setAttr('body_offset_ctrl' + 'Shape.overrideColorRGB', 0.75, 0.75, 0.0) # 1 = 255

        metahuman_offset = create_offset(source_object = 'body_offset_ctrl', offset_name = 'body_offset_ctrl'.replace('_ctrl', '_offset'))

        cmds.parent('body_offset_offset', 'global_ctrl') 
        cmds.parent('root_offset', 'body_offset_ctrl')

        attribute_cleanup(object='body_offset_ctrl', translate_key = 1, translate_visible = 0, translate_lock = 0, rotation_key = 1, rotation_visible = 0, rotation_lock = 0, scale_key = 1, scale_visible = 1 , scale_lock = 1)

        ###########
        # body ctrl  
        cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 35, tol = 0, n = 'body_ctrl')
        cmds.setAttr('body_ctrl'+"Shape.lineWidth", 2)
        makeNode = str(findMakeNode('body_ctrl', 'makeNurbCircle'))
        if makeNode!='None':
            cmds.setAttr (makeNode + '.degree', 1)
            cmds.setAttr (makeNode + '.sections', 6)
        cmds.setAttr ('body_ctrl' + '.degree', 1)

        cmds.setAttr('body_ctrl' + 'Shape.overrideEnabled', 1)
        cmds.setAttr('body_ctrl' + 'Shape.overrideRGBColors', 1)
        cmds.setAttr('body_ctrl' + 'Shape.overrideColorRGB', 0.75, 0.5, 0.0) # 1 = 255
        cmds.setAttr('body_ctrl' + '.ry', 90)

        #reset xform
        cmds.makeIdentity('body_ctrl', apply=True, t=1, r=1, s=1, n=0, pn=1) 
    
        #parent con to get into position
        cmds.parentConstraint( 'hips_ctrl', 'body_ctrl', n = 'delete_con' )
        cmds.delete('delete_con')

        metahuman_offset = create_offset(source_object = 'body_ctrl', offset_name = 'body_ctrl'.replace('_ctrl', '_offset'))
    
        cmds.parent('body_offset', 'root_ctrl')
        cmds.parent('hips_offset', 'body_ctrl')    
        cmds.parent('spine_01_offset', 'body_ctrl')  
        
        attribute_cleanup(object='body_ctrl', translate_key = 1, translate_visible = 0, translate_lock = 0, rotation_key = 1, rotation_visible = 0, rotation_lock = 0, scale_key = 1, scale_visible = 1 , scale_lock = 1)
        
        # fk limbs controls
        for dir_str in dir_str_list:
            # create fk limb ctrls
            str_list = ['upperarm_'+ dir_str + '_fk', 'lowerarm_'+ dir_str + '_fk', 'hand_'+ dir_str + '_fk', 'thigh_'+ dir_str + '_fk', 'calf_'+ dir_str + '_fk', 'foot_'+ dir_str + '_fk', 'ball_'+ dir_str + '_fk', 'hand_'+ dir_str + '_ik', 'foot_'+ dir_str + '_ik']
            for str_val in str_list:
                if 'thigh' in str_val:
                    cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 15, tol = 0, n = str_val + '_ctrl')
                if 'ik' in str_val:
                    cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 15, tol = 0, n = str_val + '_ctrl')
                if not 'thigh' in str_val and not 'ik' in str_val:
                    cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 10, tol = 0, n = str_val + '_ctrl')
                cmds.setAttr(str_val + '_ctrl' + "Shape.lineWidth", 2)
                cmds.setAttr(str_val + '_ctrl' + '.ry', 90)

                if 'ball' in str_val + '_ctrl':
                    cmds.setAttr(str_val + '_ctrl' + '.sx', .55)
                    cmds.setAttr(str_val + '_ctrl' + '.sy', .55)
                    cmds.setAttr(str_val + '_ctrl' + '.sz', .55)

                #reset xform
                cmds.makeIdentity(str_val + '_ctrl', apply=True, t=1, r=1, s=1, n=0, pn=1)
        
                #parent con to get into position
                cmds.parentConstraint(str_val + '_motion', str_val + '_ctrl', n = 'delete_con' )
                cmds.delete('delete_con')

                if '_ik' in str_val:
                    makeNode = str(findMakeNode(str_val + '_ctrl', 'makeNurbCircle'))
                    if makeNode!='None':
                        cmds.setAttr (makeNode + '.degree', 1)
                        cmds.setAttr (makeNode + '.sections', 6)
                cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideEnabled', 1)
                cmds.setAttr(str_val + '_ctrl'  + 'Shape.overrideRGBColors', 1)
                if dir_str == 'l':
                    cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.0, 0.0, 0.75)    
                if dir_str == 'r':
                    cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.75, 0.0, 0.0)    
    
                metahuman_offset = str_val + '_ctrl'.replace('_ctrl', '_offset')
                create_offset(source_object = str_val + '_ctrl', offset_name = metahuman_offset)
                cmds.parent(str_val + '_offset', 'rig_ctrls')
                
                if not '_ik_' in (str_val + '_ctrl'):
                    for attr in attr_list:           
                        cmds.setAttr(str_val + '_ctrl' + '.' + attr, lock = 1, k = 0)

            for num in range(0, len(part_list)):
                part = part_list[num]
                if part == 'hand' or part == 'foot':
                    cmds.parentConstraint(part + '_'+ dir_str + '_ik_ctrl', part + '_' + dir_str + '_ikHandle', n = part + '_'+ dir_str + '_ik_ctrl_parent_con', mo=1 )
            
                if part == 'upperarm':
                    cmds.parent(part + '_' + dir_str + '_fk_offset', 'clavicle_' + dir_str + '_ctrl')
            
                if part == 'thigh':
                    cmds.parent('thigh_' + dir_str + '_fk_offset', 'hips_ctrl')

                if not part == 'upperarm' and not part == 'thigh':
                    cmds.parent(part + '_' + dir_str + '_fk_offset', part_list[num-1] + '_' + dir_str + '_fk_ctrl')
                # direct connection caused limbs orientation issue when root rotated
                cmds.orientConstraint(part + '_' + dir_str + '_fk_ctrl', part +'_' + dir_str + '_fk_motion', mo = 0, n = part + '_' + dir_str + '_fk_ctrl_parent_con')
                
            # create switch objects
            switch_object = 'hand_fkik_' + dir_str + '_switch'
            if not cmds.objExists(switch_object):
                cmds.group(n = switch_object, em = 1)
            cmds.textCurves( f='Arial', t='+', n = switch_object)

            shape_list = cmds.listRelatives(switch_object+'Shape', ad=1, typ='nurbsCurve')
        
            for current_shape in shape_list:
                cmds.parent(current_shape, switch_object, s=1, r=1)
            cmds.delete(switch_object+'Shape')

            #rotate 90 degrees
            cmds.setAttr(switch_object + '.rx', 90)
        
            #reset xform
            cmds.makeIdentity(switch_object, apply=True, t=1, r=1, s=1, n=0, pn=1)

            #parent con to get into position
            cmds.parentConstraint('upperarm_' + dir_str + '_fk_motion', switch_object, n = 'delete_con' )
            cmds.delete('delete_con')
            
            #cmds.setAttr(switch_object + '.rx', 90)
            cmds.setAttr(switch_object + '.sx', 10)
            cmds.setAttr(switch_object + '.sy', 10)
            cmds.setAttr(switch_object + '.sz', 10)

            if dir_str == 'l':
                cmds.setAttr(switch_object + '.tx', 30)
            if dir_str == 'r':
                cmds.setAttr(switch_object + '.tx', -40)
        
            #reset xform
            cmds.makeIdentity(switch_object, apply=True, t=1, r=1, s=1, n=0, pn=1)
            cmds.parent(switch_object, 'rig_ctrls')
            cmds.parentConstraint('spine_01_motion', switch_object, n = 'spine_01_motion_parent_con', mo=1 )
            
            # add attribute fk/ik
            cmds.addAttr(switch_object, longName='limb_fkik_switch', shortName='limb_fk_ik', attributeType='float', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
            cmds.setAttr(switch_object+'.limb_fk_ik', cb=1, c=1, keyable=True)
            attribute_cleanup(object=switch_object, translate_key = 0, translate_visible = 0, translate_lock = 0, rotation_key = 0, rotation_visible = 0, rotation_lock = 0, scale_key = 0, scale_visible = 0 , scale_lock = 0)

            switch_object = 'foot_fkik_' + dir_str + '_switch'
            if not cmds.objExists(switch_object):
                cmds.group(n = switch_object, em = 1)
            cmds.textCurves( f='Arial', t='+', n = switch_object)
            shape_list = cmds.listRelatives(switch_object+'Shape', ad=1, typ='nurbsCurve')
            for current_shape in shape_list:
                cmds.parent(current_shape, switch_object, s=1, r=1)
            cmds.delete(switch_object+'Shape')
            
            #parent con to get into position
            cmds.parentConstraint('thigh_' + dir_str + '_fk_motion', switch_object, n = 'delete_con' )
            cmds.delete('delete_con')
            cmds.setAttr(switch_object + '.rx', 90)
            cmds.setAttr(switch_object + '.sx', 10)
            cmds.setAttr(switch_object + '.sy', 10)
            cmds.setAttr(switch_object + '.sz', 10)
            
            if dir_str == 'l':
                cmds.setAttr(switch_object + '.tx', 30)
            if dir_str == 'r':
                cmds.setAttr(switch_object + '.tx', -40)

            #reset xform
            cmds.makeIdentity(switch_object, apply=True, t=1, r=1, s=1, n=0, pn=1)
            cmds.parent(switch_object, 'rig_ctrls')
            cmds.parentConstraint('spine_05_motion', switch_object, n = 'spine_05_motion_parent_con' , mo=1)

            # add attribute fk/ik
            cmds.addAttr(switch_object, longName='limb_fkik_switch', shortName='limb_fk_ik', attributeType='float', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
            cmds.setAttr(switch_object+'.limb_fk_ik', cb=1, c=1)
            attribute_cleanup(object=switch_object, translate_key = 0, translate_visible = 0, translate_lock = 1, rotation_key = 0, rotation_visible = 0, rotation_lock = 1, scale_key = 0, scale_visible = 0 , scale_lock = 1)

            # position pole vector
            pole_vector_location_ref = create_pole_vector_object(boneA='upperarm_' + dir_str + '_ik_motion', boneB='lowerarm_' + dir_str + '_ik_motion', boneC='hand_' + dir_str + '_ik_motion')

            # arm pole vectors
            str_val = 'arm_pole_vector_' + dir_str
            cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 5, tol = 0, n = str_val + '_ctrl')
            cmds.setAttr(str_val + '_ctrl' + "Shape.lineWidth", 2)

            #parent con to get into position
            cmds.parentConstraint(pole_vector_location_ref, str_val + '_ctrl', n = 'delete_con' )
            cmds.delete('delete_con')
            cmds.delete(pole_vector_location_ref)

            makeNode = str(findMakeNode(str_val + '_ctrl', 'makeNurbCircle'))
            if makeNode!='None':
                cmds.setAttr (makeNode + '.degree', 1)
                cmds.setAttr (makeNode + '.sections', 6)

            cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideEnabled', 1)
            cmds.setAttr(str_val + '_ctrl'  + 'Shape.overrideRGBColors', 1)
            if dir_str == 'l':
                cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.0, 0.0, 0.75)    
            if dir_str == 'r':
                cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.75, 0.0, 0.0)    

            cmds.setAttr(str_val + '_ctrl' + '.ty', 50)
            cmds.setAttr(str_val + '_ctrl' + '.ry', 90)
            
            cur_offset = str_val + '_offset'
            cur_str = str_val + '_ctrl'
            
            # creates offset for pole vectors
            if not cmds.objExists(str_val + '_offset'):
                cmds.group(n = str_val + '_offset', em = 1)

            # parent con to get into position
            cmds.parentConstraint(cur_str, cur_offset, n = 'delete_con' )
            cmds.delete('delete_con')
            cmds.parent(cur_str, cur_offset)
            cmds.parent(cur_offset, 'rig_ctrls')
            
            cmds.poleVectorConstraint(str_val + '_ctrl', 'hand_' + dir_str + '_ikHandle' )
            
            cur_match = str_val+'_match'
            cur_offset = str_val + '_match_offset'
            cmds.duplicate(str_val + '_ctrl', n=cur_match)
            cmds.scale( .3, .3, .3, cur_match, relative=True)

            #reset xform
            cmds.makeIdentity(cur_match, apply=True, t=1, r=1, s=1, n=0, pn=1)

            # creates offset for pole vectors
            if not cmds.objExists(cur_offset):    
                cmds.group(n = cur_offset, em = 1)

            # parent con to get into position
            cmds.parentConstraint(cur_match, cur_offset, n = 'delete_con' )
            cmds.delete('delete_con')
            
            if cmds.listRelatives(cur_match, p=1):
                if not cmds.listRelatives(cur_match, p=1)[0] == cur_offset:
                    cmds.parent(cur_match, cur_offset)
            else:
                cmds.parent(cur_match, cur_offset)

            cmds.parent(cur_offset, 'rig_ctrls')

            cmds.parentConstraint('lowerarm_' + dir_str + '_fk_motion', cur_offset, mo=1)

            # position pole vector
            pole_vector_location_ref = create_pole_vector_object(boneA='thigh_' + dir_str + '_ik_motion', boneB='calf_' + dir_str + '_ik_motion', boneC='foot_' + dir_str + '_ik_motion')

            # leg pole vector
            str_val = 'leg_pole_vector_' + dir_str
            cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 5, tol = 0, n = str_val + '_ctrl')
            cmds.setAttr(str_val + '_ctrl' + "Shape.lineWidth", 2)

            #parent con to get into position
            cmds.parentConstraint(pole_vector_location_ref, str_val + '_ctrl', n = 'delete_con' )
            cmds.delete('delete_con')
            cmds.delete(pole_vector_location_ref)

            makeNode = str(findMakeNode(str_val + '_ctrl', 'makeNurbCircle'))
            if makeNode!='None':
                cmds.setAttr (makeNode + '.degree', 1)
                cmds.setAttr (makeNode + '.sections', 6)

            cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideEnabled', 1)
            cmds.setAttr(str_val + '_ctrl'  + 'Shape.overrideRGBColors', 1)
            if dir_str == 'l':
                cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.0, 0.0, 0.75)    
            if dir_str == 'r':
                cmds.setAttr(str_val + '_ctrl' + 'Shape.overrideColorRGB', 0.75, 0.0, 0.0)    

            cmds.setAttr(str_val + '_ctrl' + '.ty', -50)
            cmds.setAttr(str_val + '_ctrl' + '.ry', 90)

            cur_offset = str_val + '_offset'
            cur_str = str_val + '_ctrl'
            
            # creates offset for pole vectors
            if not cmds.objExists(str_val + '_offset'):    
                cmds.group(n = str_val + '_offset', em = 1)

            # parent con to get into position
            cmds.parentConstraint(cur_str, cur_offset, n = 'delete_con' )
            cmds.delete('delete_con')
            cmds.parent(cur_str, cur_offset)
            cmds.parent(cur_offset, 'rig_ctrls')

            #reset xform
            cmds.makeIdentity(str_val + '_ctrl', apply=True, t=1, r=1, s=1, n=0, pn=1)

            cmds.poleVectorConstraint(str_val + '_ctrl', 'foot_' + dir_str + '_ikHandle', n='foot_' + dir_str + '_poleVector_con') 

            cur_match = str_val+'_match'
            cur_offset = str_val + '_match_offset'
            cmds.duplicate(str_val + '_ctrl', n=cur_match)
            cmds.scale( .3, .3, .3, cur_match, relative=True)

            #reset xform
            cmds.makeIdentity(cur_match, apply=True, t=1, r=1, s=1, n=0, pn=1)

            # creates offset for pole vectors
            if not cmds.objExists(cur_offset):    
                cmds.group(n = cur_offset, em = 1)

            # parent con to get into position
            cmds.parentConstraint(cur_match, cur_offset, n = 'delete_con' )
            cmds.delete('delete_con')
            
            if cmds.listRelatives(cur_match, p=1):
                if not cmds.listRelatives(cur_match, p=1)[0] == cur_offset:
                    cmds.parent(cur_match, cur_offset)
            else:
                cmds.parent(cur_match, cur_offset)

            cmds.parent(cur_offset, 'rig_ctrls')

            cmds.parentConstraint('calf_' + dir_str + '_fk_motion', cur_offset, mo=1)

            cmds.orientConstraint('hand_' + dir_str + '_ik_ctrl', 'hand_' + dir_str + '_ik_motion', mo=0)
            cmds.orientConstraint('foot_' + dir_str + '_ik_ctrl', 'foot_' + dir_str + '_ik_motion', mo=0)

            attribute_cleanup(object='hand_' + dir_str + '_ik_ctrl', translate_key = 1, translate_visible = 1, translate_lock = 0, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 0, scale_visible = 0 , scale_lock = 1)
            attribute_cleanup(object='foot_' + dir_str + '_ik_ctrl', translate_key = 1, translate_visible = 1, translate_lock = 0, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 0, scale_visible = 0 , scale_lock = 1)

            # parent con ik ctrls and pole vector ctrls
            cmds.parentConstraint('root_ctrl', 'hand_' + dir_str + '_ik_offset', mo=1)
            cmds.parentConstraint('root_ctrl', 'foot_' + dir_str + '_ik_offset', mo=1)

            cmds.parentConstraint('root_ctrl', 'arm_pole_vector_' + dir_str + '_offset', mo=1)
            cmds.parentConstraint('root_ctrl', 'leg_pole_vector_' + dir_str + '_offset', mo=1)
            
            attribute_cleanup(object='arm_pole_vector_' + dir_str + '_ctrl', translate_key = 1, translate_visible = 1, translate_lock = 0, rotation_key = 0, rotation_visible = 0, rotation_lock = 1, scale_key = 0, scale_visible = 0 , scale_lock = 1)
            attribute_cleanup(object='leg_pole_vector_' + dir_str + '_ctrl', translate_key = 1, translate_visible = 1, translate_lock = 0, rotation_key = 0, rotation_visible = 0, rotation_lock = 1, scale_key = 0, scale_visible = 0 , scale_lock = 1)
            
            # fk ik connections
            partA_list = ('upperarm', 'lowerarm', 'hand', 'thigh', 'calf', 'foot', 'ball')
            partB_list = ('hand', 'hand', 'hand', 'foot', 'foot', 'foot', 'foot')

            for num in range(0,len(partA_list)):
                partStrA = partA_list[num]
                partStrB = partB_list[num]
                if cmds.objExists('plusMinusAverage_' + partStrA + '_' + dir_str):
                    cmds.delete('plusMinusAverage_' + partStrA + '_' + dir_str)
                pmavg = cmds.shadingNode('plusMinusAverage', au=1, n = 'plusMinusAverage_' + partStrA + '_' + dir_str)
                cmds.setAttr(pmavg+'.operation', 2)
                if cmds.objExists('floatConstant_' + partStrA + '_'  + dir_str):
                    cmds.delete('floatConstant_' + partStrA + '_'  + dir_str)
                floatConst = cmds.shadingNode('floatConstant', au=1, n = 'floatConstant_' + partStrA + '_'  + dir_str)
                cmds.connectAttr(floatConst + '.outFloat', pmavg + '.input1D[0]',  f=1)
                cmds.connectAttr(partStrB + '_fkik_' + dir_str + '_switch' + '.limb_fkik_switch', partStrA + '_' + dir_str + '_ikfk_motion_orient_con' + '.' + partStrA + '_' + dir_str + '_ik_motionW0',  f=1)
                cmds.connectAttr(pmavg + '.output1D', partStrA + '_' + dir_str + '_ikfk_motion_orient_con' + '.' + partStrA + '_' + dir_str + '_fk_motionW1',  f=1)
            
                cmds.connectAttr(partStrB + '_fkik_' + dir_str + '_switch' + '.limb_fkik_switch', pmavg + '.input1D[1]',  f=1)

                if cmds.objExists(partStrA + '_' + dir_str + '_fk_ctrl'):
                    cmds.connectAttr(pmavg + '.output1D', partStrA + '_' + dir_str + '_fk_ctrl.visibility', f=1)
                if cmds.objExists(partStrA + '_' + dir_str + '_ik_ctrl'):
                    cmds.connectAttr(partStrB + '_fkik_' + dir_str + '_switch.limb_fkik_switch', partStrA + '_' + dir_str + '_ik_ctrl.visibility', f=1)
            
            cmds.setAttr('arm_pole_vector_' + dir_str + '_match.visibility',0)
            cmds.setAttr('leg_pole_vector_' + dir_str + '_match.visibility',0)
            cmds.setAttr('foot_fkik_' + dir_str +'_switch.limb_fkik_switch', c=1)

            if cmds.objExists('arm_pole_vector_' + dir_str + '_ctrl'):
                cmds.connectAttr('hand_fkik_' + dir_str + '_switch.limb_fkik_switch', 'arm_pole_vector_' + dir_str + '_ctrl.visibility', f=1)
            if cmds.objExists('leg_pole_vector_' + dir_str + '_ctrl'):
                cmds.connectAttr('foot_fkik_' + dir_str + '_switch.limb_fkik_switch', 'leg_pole_vector_' + dir_str + '_ctrl.visibility', f=1)
            
            ####################
            # reverse foot setup
            foot_roll_list = ['foot', 'ball', 'toe']
            for foot_roll_str in foot_roll_list:
                foot_loc = foot_roll_str + '_' + dir_str + '_loc'
                cmds.spaceLocator(n=foot_loc)
                if not foot_roll_str == 'toe':
                    cmds.parentConstraint(foot_roll_str + '_' + dir_str + '_ik_motion', foot_loc, mo=0, n = 'delete_con')
                else:
                    cmds.parentConstraint('ball_' + dir_str + '_ik_motion', foot_loc, mo=0, n = 'delete_con')
                cmds.delete('delete_con')

                if foot_roll_str == 'foot':
                    cmds.parent(foot_loc, 'rig_setup')
                else:
                    cmds.parent(foot_loc, 'foot_' + dir_str + '_loc')
                
                if foot_roll_str == 'ball':
                    cmds.makeIdentity(foot_loc, apply=True, t=1, r=1, s=1, n=0, pn=1)

                # position toe at front of foot
                if foot_roll_str == 'toe':
                    val = cmds.getAttr(foot_loc + '.translateY')
                    cmds.setAttr(foot_loc + '.translateY', val - 7)
                    cmds.setAttr(foot_loc + '.translateZ', 0)
                    #reset xform
                    cmds.makeIdentity(foot_loc, apply=True, t=1, r=1, s=1, n=0, pn=1)

                # position foot at heel lcoation
                if foot_roll_str == 'foot':
                    val = cmds.getAttr(foot_loc + '.translateY')
                    cmds.setAttr(foot_loc + '.translateY', val + 5)
                    cmds.setAttr(foot_loc + '.translateZ', 0)
                    #reset xform
                    cmds.makeIdentity(foot_loc, apply=True, t=1, r=1, s=1, n=0, pn=1)

                    cmds.group(foot_loc, n=foot_loc.replace('_loc', '_offset'))
                    cmds.parentConstraint('foot_' + dir_str + '_ik_ctrl', foot_loc.replace('_loc', '_offset'), mo=1)

                else:
                    cmds.group(foot_loc, n=foot_loc.replace('_loc', '_offset'))

                if foot_roll_str == 'toe':
                    current_joint = foot_roll_str + '_' + dir_str + '_ik_motion'
                    cmds.joint(n = current_joint,  p=(0, 0, 0) )
                    cmds.parentConstraint(foot_roll_str + '_' + dir_str + '_offset', current_joint, mo=0, n='delete_con')
                    cmds.delete('delete_con')
                    cmds.parent(current_joint,  'ball_' + dir_str + '_ik_motion')
            
            if cmds.objExists('foot_' + dir_str + '_ik_ctrl_parent_con'):
                cmds.delete('foot_' + dir_str + '_ik_ctrl_parent_con')
            cmds.ikHandle( sj='foot_' + dir_str + '_ik_motion', ee='ball_' + dir_str + '_ik_motion', p=2, w=.5, s = 'sticky', n = 'ball_rev_' + dir_str + '_ikHandle' )
            cmds.parent('ball_rev_' + dir_str + '_ikHandle', 'ball_'+dir_str+'_loc')
            cmds.ikHandle( sj='ball_' + dir_str + '_ik_motion', ee='toe_' + dir_str + '_ik_motion', p=2, w=.5, s = 'sticky', n = 'toe_rev_' + dir_str + '_ikHandle' )
            cmds.parent('toe_rev_' + dir_str + '_ikHandle', 'foot_'+dir_str+'_loc')
            cmds.parentConstraint('ball_'+dir_str+'_loc', 'foot_' + dir_str + '_ikHandle', mo=1, n='foot_' + dir_str + '_ikHandle_Con')
            cmds.parent('ball_' + dir_str + '_offset', 'toe_'+dir_str+'_loc')
            
            # create custom attributes
            ctrl_name = 'foot_' + dir_str + '_ik_ctrl'
            cmds.addAttr(ctrl_name, longName = 'Roll', shortName = 'Roll', attributeType='float', keyable=True, defaultValue=0.0, minValue=-30.0, maxValue=70.0)
            cmds.setAttr(ctrl_name+'.Roll', cb=1, c=1)
            cmds.addAttr(ctrl_name, longName = 'Bend_Limit_Angle', shortName = 'BendLimitAngle', attributeType='float', defaultValue=45.0, minValue=-180.0, maxValue=180.0)
            cmds.setAttr(ctrl_name+'.Bend_Limit_Angle', cb=1, c=1, l=1)
            cmds.addAttr(ctrl_name, longName = 'Toe_Straight', shortName = 'ToeStraight', attributeType='float', defaultValue=75.0, minValue=-180.0, maxValue=180.0)
            cmds.setAttr(ctrl_name+'.Toe_Straight', cb=1, c=1, l=1)

            nodeStr = 'foot_rot_clamp_' + dir_str
            if cmds.objExists(nodeStr):
                cmds.delete(nodeStr)
            cmds.shadingNode('clamp', au=1, n= nodeStr) 
            cmds.connectAttr('foot_' + dir_str + '_ik_ctrl.Roll', nodeStr + '.inputR', f=1)
            cmds.setAttr(nodeStr + '.minR', -90)
            cmds.setAttr(nodeStr + '.maxR', 0)
            cmds.connectAttr(nodeStr + '.outputR', 'foot_' + dir_str + '_loc.rotateX', f=1)
            
            nodeStr = 'ball_zeroToBlend_clamp_' + dir_str
            if cmds.objExists(nodeStr):
                cmds.delete(nodeStr)
            cmds.shadingNode('clamp', au=1, n= nodeStr) 
            cmds.connectAttr('foot_' + dir_str + '_ik_ctrl.Roll', nodeStr + '.inputR', f=1)
            cmds.setAttr(nodeStr + '.minR', 0)
            cmds.connectAttr(ctrl_name+'.Bend_Limit_Angle', nodeStr + '.maxR', f=1)
            
            nodeStrAB = 'toe_setRange_zeroToBendPercent' + dir_str
            if cmds.objExists(nodeStrAB):
                cmds.delete(nodeStrAB)
            cmds.shadingNode('setRange', au=1, n= nodeStrAB) 
            cmds.connectAttr(nodeStr + '.minR', nodeStrAB + '.oldMinX', f=1)
            cmds.connectAttr(nodeStr + '.maxR', nodeStrAB + '.oldMaxX', f=1)
            cmds.setAttr(nodeStrAB + '.maxX', 1)
            cmds.setAttr(nodeStrAB + '.minX', 0)
            cmds.connectAttr(nodeStr + '.inputR', nodeStrAB + '.valueX', f=1)

            nodeStr = 'toe_rot_clamp_' + dir_str
            if cmds.objExists(nodeStr):
                cmds.delete(nodeStr)
            cmds.shadingNode('clamp', au=1, n= nodeStr) 
            cmds.connectAttr('foot_' + dir_str + '_ik_ctrl.Bend_Limit_Angle', nodeStr + '.minR', f=1)
            cmds.connectAttr('foot_' + dir_str + '_ik_ctrl.Toe_Straight', nodeStr + '.maxR', f=1)
            cmds.connectAttr('foot_' + dir_str + '_ik_ctrl.Roll', nodeStr + '.inputR', f=1)
            
            nodeStrB = 'toe_setRange_bendToStraightPercent_' + dir_str
            if cmds.objExists(nodeStrB):
                cmds.delete(nodeStrB)
            cmds.shadingNode('setRange', au=1, n= nodeStrB) 
            cmds.connectAttr(nodeStr + '.minR', nodeStrB + '.oldMinX', f=1)
            cmds.connectAttr(nodeStr + '.maxR', nodeStrB + '.oldMaxX', f=1)
            cmds.setAttr(nodeStrB + '.maxX', 1)
            cmds.setAttr(nodeStrB + '.minX', 0)
            cmds.connectAttr(nodeStr + '.inputR', nodeStrB + '.valueX', f=1)
            
            nodeStrAC = 'toe_invertPercentage_' + dir_str
            if cmds.objExists(nodeStrAC):
                cmds.delete(nodeStrAC)
            cmds.shadingNode('plusMinusAverage', au=1, n= nodeStrAC)
            cmds.setAttr(nodeStrAC+'.input1D[0]', 1)
            cmds.setAttr(nodeStrAC+'.input1D[1]', 1)
            cmds.connectAttr(nodeStrB + '.outValueX', nodeStrAC + '.input1D[1]', f=1)
            cmds.setAttr(nodeStrAC + '.operation', 2)
            
            
            nodeStrBC = 'ball_percentMult_multiplydivide_' + dir_str
            if cmds.objExists(nodeStrBC):
                cmds.delete(nodeStrBC)
            cmds.shadingNode('multiplyDivide', au=1, n= nodeStrBC) 
            cmds.connectAttr(nodeStrAB + '.outValueX', nodeStrBC + '.input1X', f=1)
            cmds.connectAttr(nodeStrAC + '.output1D', nodeStrBC + '.input2X', f=1)
            
            nodeStrCC = 'ball_rollMult_multiplydivide_' + dir_str
            if cmds.objExists(nodeStrCC):
                cmds.delete(nodeStrCC)
            cmds.shadingNode('multiplyDivide', au=1, n= nodeStrCC) 
            cmds.connectAttr(nodeStrBC + '.outputX', nodeStrCC + '.input1X', f=1)
            cmds.connectAttr('foot_' + dir_str + '_ik_ctrl.Roll', nodeStrCC + '.input2X', f=1)
            cmds.connectAttr(nodeStrCC + '.outputX', 'ball_' + dir_str + '_loc.rotateX', f=1)
            
            nodeStrC = 'toe_rot_multiplydivide_' + dir_str
            if cmds.objExists(nodeStrC):
                cmds.delete(nodeStrC)
            cmds.shadingNode('multiplyDivide', au=1, n= nodeStrC) 
            cmds.connectAttr(nodeStrB + '.outValueX', nodeStrC + '.input1X', f=1)
            cmds.connectAttr(nodeStr + '.inputR', nodeStrC + '.input2X', f=1)
            cmds.connectAttr(nodeStrC + '.outputX', 'toe_' + dir_str + '_loc' + '.rotateX', f=1)
            
            #############################
            # additional ik toe controls

            # Toe Twist Ctrl
            ctrl_name =  'toe_twist' + '_' + dir_str + '_ik_ctrl'
            cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 3, tol = 0, n = ctrl_name)
            cmds.setAttr(ctrl_name + "Shape.lineWidth", 2)

            makeNode = str(findMakeNode(ctrl_name, 'makeNurbCircle'))
            if makeNode!='None':
                cmds.setAttr (makeNode + '.degree', 1)
                cmds.setAttr (makeNode + '.sections', 6)
            
            cmds.setAttr(ctrl_name + 'Shape.overrideEnabled', 1)
            cmds.setAttr(ctrl_name  + 'Shape.overrideRGBColors', 1)
            if dir_str == 'l':
                cmds.setAttr(ctrl_name + 'Shape.overrideColorRGB', 0.0, 0.0, 0.75)    
            if dir_str == 'r':
                cmds.setAttr(ctrl_name + 'Shape.overrideColorRGB', 0.75, 0.0, 0.0) 

            #parent con to get into position
            cmds.parentConstraint('toe_' + dir_str + '_loc', ctrl_name, n = 'delete_con' )
            cmds.delete('delete_con')

            current_offset = create_offset(source_object = ctrl_name, offset_name = ctrl_name.replace('_ctrl', '_offset'))

            cmds.parentConstraint('toe_' + dir_str + '_loc', current_offset, n = current_offset + '_con', mo = 1 )
            cmds.parent(current_offset, 'rig_ctrls')
            
            cmds.connectAttr('toe_twist_' + dir_str + '_ik_ctrl.rotateZ', 'toe_' + dir_str + '_loc.rotateZ', f=1)

            attribute_cleanup(object=ctrl_name, translate_key = 0, translate_visible = 0, translate_lock = 0, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 0, scale_visible = 0, scale_lock = 0)
            
            cmds.setAttr(ctrl_name + '.translate'+'X', keyable=0)
            cmds.setAttr(ctrl_name + '.rotate'+'X', k=0, cb=0, l=1)
            cmds.setAttr(ctrl_name + '.translate'+'Y', keyable=0)
            cmds.setAttr(ctrl_name + '.rotate'+'Y', k=0, cb=0, l=1)

            if cmds.objExists('leg_pole_vector_' + dir_str + '_ctrl'):
                cmds.connectAttr('foot_fkik_' + dir_str + '_switch.limb_fkik_switch', 'toe_twist_' + dir_str + '_ik_ctrl.visibility', f=1)
            
            # toe IK rotate ctrl
            ball_lift_joint = 'ball_lift_' + dir_str + '_ik_motion'

            cmds.duplicate('ball_' + dir_str + '_ik_motion', n=ball_lift_joint, rc=1)
            duplicates_list = cmds.listRelatives('ball_lift_' + dir_str + '_ik_motion')
            for duplicate in duplicates_list:
                if 'effector' in duplicate:
                    cmds.delete(duplicate)

            cmds.rename(cmds.listRelatives(ball_lift_joint, c=1)[0], ball_lift_joint.replace('ball_', 'toe_'))
            ball_lift_joint = 'ball_lift_' + dir_str + '_ik_motion'

            cmds.parent(ball_lift_joint, 'rig_setup')
            current_offset = create_offset(source_object = ball_lift_joint, offset_name = ball_lift_joint.replace('_motion', '_motion_offset'))
            cmds.parentConstraint('ball_' + dir_str + '_ik_motion', current_offset, n =current_offset + '_con', mo=1)

            # create control            
            ctrl_name =  'ball_lift' + '_' + dir_str + '_ik_ctrl'
            cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 5, tol = 0, n = ctrl_name)
            cmds.setAttr(ctrl_name + "Shape.lineWidth", 2)

            makeNode = str(findMakeNode(ctrl_name, 'makeNurbCircle'))
            if makeNode!='None':
                cmds.setAttr (makeNode + '.degree', 1)
                cmds.setAttr (makeNode + '.sections', 6)

            #rotate 90 degrees
            cmds.setAttr(ctrl_name + '.ry', 90)

            #reset xform
            cmds.makeIdentity(ctrl_name, apply=True, t=1, r=1, s=1, n=0, pn=1)

            cmds.setAttr(ctrl_name + 'Shape.overrideEnabled', 1)
            cmds.setAttr(ctrl_name  + 'Shape.overrideRGBColors', 1)
            if dir_str == 'l':
                cmds.setAttr(ctrl_name + 'Shape.overrideColorRGB', 0.0, 0.0, 0.75)    
            if dir_str == 'r':
                cmds.setAttr(ctrl_name + 'Shape.overrideColorRGB', 0.75, 0.0, 0.0)  

            # parent con to get into position
            cmds.parentConstraint('ball_' + dir_str + '_fk_ctrl', ctrl_name, n = 'delete_con' )
            cmds.delete('delete_con')

            cmds.parent(ctrl_name, 'rig_ctrls')
            current_offset = create_offset(source_object = ctrl_name, offset_name = ctrl_name.replace('_ctrl', '_offset'))
            if cmds.objExists(current_offset + '_parent_con'):
                print('deleteing old constraint')
                cmds.delete(current_offset + '_parent_con')
            cmds.parentConstraint('ball_' + dir_str + '_ik_motion', current_offset, n=current_offset + '_parent_con', mo=1)
            cmds.orientConstraint(ctrl_name, ball_lift_joint, n = ctrl_name + '_orient_con', mo=1)
            
            orient_con = 'ball' + '_' + dir_str + '_ikfk_motion_orient_con'
            if dir_str:
                if cmds.objExists(orient_con):
                    cmds.delete(orient_con)

                # create constraints
                cmds.orientConstraint(ball_lift_joint, 'ball' + '_' + dir_str + '_fk_motion', 'ball' + '_' + dir_str + '_motion', n = orient_con, mo = 1)

                # fk ik connections
                partStrA = 'ball_lift' #partA_list[num]
                partStrB = 'foot' #partB_list[num]
                if cmds.objExists('plusMinusAverage_' + partStrA + '_' + dir_str):
                    cmds.delete('plusMinusAverage_' + partStrA + '_' + dir_str)
                pmavg = cmds.shadingNode('plusMinusAverage', au=1, n = 'plusMinusAverage_' + partStrA + '_' + dir_str)
                cmds.setAttr(pmavg+'.operation', 2)
                if cmds.objExists('floatConstant_' + partStrA + '_'  + dir_str):
                    cmds.delete('floatConstant_' + partStrA + '_'  + dir_str)
                floatConst = cmds.shadingNode('floatConstant', au=1, n = 'floatConstant_' + partStrA + '_'  + dir_str)
                cmds.connectAttr(floatConst + '.outFloat', pmavg + '.input1D[0]',  f=1)
                cmds.connectAttr(partStrB + '_fkik_' + dir_str + '_switch' + '.limb_fkik_switch', orient_con + '.' + partStrA + '_' + dir_str + '_ik_motionW0',  f=1)
                cmds.connectAttr(pmavg + '.output1D', orient_con + '.' + partStrA.replace('_lift', '') + '_' + dir_str + '_fk_motionW1',  f=1)
            
                cmds.connectAttr(partStrB + '_fkik_' + dir_str + '_switch' + '.limb_fkik_switch', pmavg + '.input1D[1]',  f=1)

                if cmds.objExists(partStrA + '_' + dir_str + '_fk_ctrl'):
                    cmds.connectAttr(pmavg + '.output1D', partStrA + '_' + dir_str + '_fk_ctrl.visibility', f=1)
                if cmds.objExists(partStrA + '_' + dir_str + '_ik_ctrl'):
                    cmds.connectAttr(partStrB + '_fkik_' + dir_str + '_switch.limb_fkik_switch', partStrA + '_' + dir_str + '_ik_ctrl.visibility', f=1)

                cmds.setAttr(ctrl_name + '.translate'+'X', keyable=0)
                cmds.setAttr(ctrl_name + '.rotate'+'X', k=0, cb=0, l=1)
                cmds.setAttr(ctrl_name + '.translate'+'Y', keyable=0)
                cmds.setAttr(ctrl_name + '.rotate'+'Y', k=0, cb=0, l=1)
            
                ctrl_name = ctrl_name.replace('_lift', '').replace('_ik_', '_fk_')
                cmds.setAttr(ctrl_name + '.translate'+'X', keyable=0)
                cmds.setAttr(ctrl_name + '.rotate'+'X', k=0, cb=0, l=1)
                cmds.setAttr(ctrl_name + '.translate'+'Y', keyable=0)
                cmds.setAttr(ctrl_name + '.rotate'+'Y', k=0, cb=0, l=1)
            
            #################
            # finger custom attr controls
            ctrl_name =  'fingers' + '_' + dir_str + '_ctrl'
            cmds.circle( nr=(0, 0, 1), c=(0, 0, 0), r = 10, tol = 0, n = ctrl_name)
            cmds.setAttr(ctrl_name + "Shape.lineWidth", 2)

            #parent con to get into position
            cmds.parentConstraint('hand_' + dir_str + '_motion', ctrl_name, n = 'delete_con' )
            cmds.delete('delete_con')
            
            cmds.parentConstraint('middle_03_' + dir_str + '_ctrl', ctrl_name, n = 'delete_con' )
            cmds.delete('delete_con')

            cmds.setAttr(ctrl_name + '.rx', -105)
            cmds.setAttr(ctrl_name + '.sx', .25)
            # direct connection puts it in the wrong place
            cmds.parentConstraint('hand_' + dir_str + '_motion', ctrl_name, n = ctrl_name + '_con', mo = 1 )


            cmds.parent(ctrl_name, 'rig_ctrls')
            
            cmds.setAttr(ctrl_name + 'Shape.overrideEnabled', 1)
            cmds.setAttr(ctrl_name  + 'Shape.overrideRGBColors', 1)
            if dir_str == 'l':
                cmds.setAttr(ctrl_name + 'Shape.overrideColorRGB', 0.0, 0.0, 0.75)    
            if dir_str == 'r':
                cmds.setAttr(ctrl_name + 'Shape.overrideColorRGB', 0.75, 0.0, 0.0)   
            
            finger_list = ('thumb', 'index', 'middle', 'ring', 'pinky', 'spread')
            for finger_str in finger_list:
                # add attributes
                if not finger_str == 'spread':
                    cmds.addAttr(ctrl_name, longName = finger_str + '_curl', shortName = finger_str, attributeType='float', keyable=True, defaultValue=0.0, minValue=-30.0, maxValue=90.0  )
                    cmds.setAttr(ctrl_name + '.' + finger_str, cb=1, c=1)
                else:
                    if finger_str == 'index' or finger_str == 'middle':
                        cmds.addAttr(ctrl_name, longName = 'spread_fingers', shortName = 'spread', attributeType='float', keyable=True, defaultValue=0.0, minValue=-10.0, maxValue=10.0)
                    else:
                        cmds.addAttr(ctrl_name, longName = 'spread_fingers', shortName = 'spread', attributeType='float', keyable=True, defaultValue=0.0, minValue=-10.0, maxValue=10.0)
                    cmds.setAttr(ctrl_name + '.' + 'spread', cb=1, c=1)
            
            for finger_str in finger_list:
                if not finger_str == 'spread':
                    for num in range(1,3):
                        cur_str = finger_str + '_0' + str(num) + '_' + dir_str + '_motion'
                        cur_offset = cur_str.replace('_motion', '_offsetA')
                        cur_ctrl = cur_str.replace('_motion', '_ctrl')

                        if not cmds.objExists(cur_offset):
                            cmds.group(n=cur_offset, em=1)
                            #parent con to get into position
                            cmds.parentConstraint(cur_str, cur_offset, n = 'delete_con' )
                            cmds.delete('delete_con')

                            
                        if num == 1:
                            if not finger_str == 'thumb':
                                cmds.parent(cur_offset, 'rig_ctrls')
                                cmds.parentConstraint(finger_str + '_metacarpal_' + dir_str +'_motion',cur_offset, mo=1)
                            else:
                                cmds.parentConstraint('hand_' + dir_str +'_motion',cur_offset, mo=1)
                                cmds.parent(cur_offset, 'rig_ctrls')

                        else:
                            cmds.parent(cur_offset, finger_str + '_0' + str(num-1) + '_' + dir_str + '_ctrl')


                        cur_offsetB = cur_offset.replace('_offsetA', '_offsetB')
                        cmds.duplicate(cur_offset, n = cur_offsetB, po=1 )
                        cmds.parent(cur_offsetB, cur_offset)
                        attribute_cleanup(object=cur_ctrl, translate_key = 1, translate_visible = 0, translate_lock = 0, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 1, scale_visible = 0 , scale_lock = 0)
                        if not cmds.listRelatives(cur_ctrl, p=1)[0] == cur_offsetB:
                            cmds.parent(cur_ctrl, cur_offsetB)

                        attribute_cleanup(object=cur_ctrl, translate_key = 0, translate_visible = 0, translate_lock = 0, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 0, scale_visible = 1 , scale_lock = 0)

                        cmds.connectAttr('fingers_' + dir_str + '_ctrl.' + finger_str, finger_str + '_0' + str(num) + '_' + dir_str + '_offsetB.rotateZ', f=1)
                        
            for finger_str in finger_list:
                if not finger_str == 'spread' and not finger_str == 'thumb':
                    if finger_str == 'index' or finger_str == 'middle':
                        if finger_str == 'middle':
                            cmds.connectAttr('fingers_' + dir_str + '_ctrl.spread', finger_str + '_01_' + dir_str + '_offsetB.rotateY', f=1)
                        else:
                            nodeStr = finger_str + '_01_' + dir_str + '_multiplyDivide'
                            cmds.shadingNode('multiplyDivide', au=1, n= nodeStr)
                            cmds.setAttr(nodeStr + '.input2X', 2)
                            cmds.connectAttr('fingers_' + dir_str + '_ctrl.spread', nodeStr + '.input1X', f=1)
                            cmds.connectAttr(nodeStr + '.outputX', finger_str + '_01_' + dir_str + '_offsetB.rotateY', f=1)
                    
                    else:
                        mult = -1
                        if finger_str == 'pinky':
                            mult = -2
                        
                        nodeStr = finger_str + '_01_' + dir_str + '_multiplyDivide'
                        cmds.shadingNode('multiplyDivide', au=1, n= nodeStr)
                        cmds.setAttr(nodeStr + '.input2X', mult)
                        cmds.connectAttr('fingers_' + dir_str + '_ctrl.spread', nodeStr + '.input1X', f=1)
                        cmds.connectAttr(nodeStr + '.outputX', finger_str + '_01_' + dir_str + '_offsetB.rotateY', f=1)
                        
                        attribute_cleanup(object='fingers_' + dir_str + '_ctrl', translate_key = 0, translate_visible = 0, translate_lock = 1, rotation_key = 0, rotation_visible = 0, rotation_lock = 1, scale_key = 0, scale_visible = 0 , scale_lock = 1)
                        cmds.setAttr('fingers_' + dir_str + '_ctrl.v', k=0, cb=0)


        for dir_str in dir_str_list:

            cmds.parent('ball_lift_' + dir_str + '_ik_motion_offset', 'rig_ctrls')
            str_list = ['upperarm_'+ dir_str + '_fk', 'lowerarm_'+ dir_str + '_fk', 'hand_'+ dir_str + '_fk', 'thigh_'+ dir_str + '_fk', 'calf_'+ dir_str + '_fk', 'foot_'+ dir_str + '_fk', 'ball_'+ dir_str + '_fk', 'hand_'+ dir_str + '_ik', 'foot_'+ dir_str + '_ik'] #, 'ball_'+ dir_str + '_ik'
            for str_val in str_list:
                # lock axis
                if not '_ik_' in current_ctrl and not 'root' in current_ctrl:
                    attr_list = ['tx', 'ty', 'tz', 'sx', 'sy', 'sz']
                    for attr in attr_list:
                        cmds.setAttr(current_ctrl + '.' + attr, lock = 1, k = 0)

        # make custom attr keyable
        for dir_str in dir_str_list:
            cmds.setAttr('hand_fkik_' + dir_str + '_switch.limb_fk_ik', keyable = True)
            cmds.setAttr('foot_fkik_' + dir_str + '_switch.limb_fk_ik', keyable = True)
            cmds.setAttr('fingers_' + dir_str + '_ctrl.thumb', keyable = True)
            cmds.setAttr('fingers_' + dir_str + '_ctrl.index', keyable = True)
            cmds.setAttr('fingers_' + dir_str + '_ctrl.middle', keyable = True)
            cmds.setAttr('fingers_' + dir_str + '_ctrl.ring', keyable = True)
            cmds.setAttr('fingers_' + dir_str + '_ctrl.pinky', keyable = True)
            cmds.setAttr('fingers_' + dir_str + '_ctrl.spread', keyable = True)
            cmds.setAttr('foot_' + dir_str + '_ik_ctrl.Roll', keyable = True)
            cmds.setAttr('foot_' + dir_str + '_ik_ctrl.Bend_Limit_Angle', keyable = True)
            cmds.setAttr('foot_' + dir_str + '_ik_ctrl.Toe_Straight', keyable = True)

        # face gui labels
        script_path = os.path.dirname(__file__)
        face_gui_file = script_path + '/' + 'face_gui_custom_labels.ma'
        if not cmds.objExists('facial_gui_custom_labels_offset'):
            if os.path.exists(face_gui_file):
                cmds.file(face_gui_file, i=True)
        if cmds.objExists('facial_gui_custom_labels_offset') and cmds.objExists('CTRL_faceGUI'):
            cmds.parent('facial_gui_custom_labels_offset', 'rig_setup')
            cmds.parentConstraint('CTRL_faceGUI', 'facial_gui_custom_labels_offset', mo=0, n='facial_gui_custom_labels_parentCon')
        
        # create space switchers for ik pole vector limbs
        add_space_switch()

        cmds.select(cl=1)
        
        # upaxis y
        cmds.upAxis(ax='y', rv=True)
        if cmds.objExists('global_ctrl'):
            cmds.setAttr('global_ctrl.rotateX', -90)
        if cmds.objExists('headRig_grp'):
            cmds.setAttr('headRig_grp.rotateX', -90)
        
        mgTag_metahuman(remove = 0)

        print('Metahuman Body Ctrls created.')
    else:
        print('User canceled Metahuman Body Ctrls creation.')
        
def delSkel():
    metahuman_skeleton = [
    'root',
    'pelvis',
    'spine_01',
    'spine_02',
    'spine_03',
    'spine_04',
    'spine_05',
    'neck_01',
    'neck_02',
    'head',
    'clavicle_l',
    'upperarm_l',
    'lowerarm_l',
    'hand_l',
    'middle_metacarpal_l',
    'middle_01_l',
    'middle_02_l',
    'middle_03_l',
    'pinky_metacarpal_l',
    'pinky_01_l',
    'pinky_02_l',
    'pinky_03_l',
    'ring_metacarpal_l',
    'ring_01_l',
    'ring_02_l',
    'ring_03_l',
    'thumb_01_l',
    'thumb_02_l',
    'thumb_03_l',
    'index_metacarpal_l',
    'index_01_l',
    'index_02_l',
    'index_03_l',
    'clavicle_r',
    'upperarm_r',
    'lowerarm_r',
    'hand_r',
    'middle_metacarpal_r',
    'middle_01_r',
    'middle_02_r',
    'middle_03_r',
    'pinky_metacarpal_r',
    'pinky_01_r',
    'pinky_02_r',
    'pinky_03_r',
    'ring_metacarpal_r',
    'ring_01_r',
    'ring_02_r',
    'ring_03_r',
    'thumb_01_r',
    'thumb_02_r',
    'thumb_03_r',
    'index_metacarpal_r',
    'index_01_r',
    'index_02_r',
    'index_03_r',
    'thigh_l',
    'calf_l',
    'foot_l',
    'ball_l',
    'thigh_r',
    'calf_r',
    'foot_r',
    'ball_r',
    'bigtoe_01_l',
    'bigtoe_02_l',
    'indextoe_01_l',
    'indextoe_02_l',
    'middletoe_01_l',
    'middletoe_02_l',
    'ringtoe_01_l',
    'ringtoe_02_l',
    'littletoe_01_l',
    'littletoe_02_l',
    'bigtoe_01_r',
    'bigtoe_02_r',
    'indextoe_01_r',
    'indextoe_02_r',
    'middletoe_01_r',
    'middletoe_02_r',
    'ringtoe_01_r',
    'ringtoe_02_r',
    'littletoe_01_r',
    'littletoe_02_r'
    ]
    cmds.select(hi=1)
    objLs = cmds.ls(sl=1)
    
    current_namespace = str(objLs[0].split(':')[:-1])+':'
    for obj in objLs:
        checkObj = obj.replace('_' + obj.split('_')[-1], '')
        
        if not checkObj in metahuman_skeleton:
            if cmds.objExists(obj):
                cmds.delete(obj)

def findMakeNode(srcNode, findStr):
    #makeNode = ''
    for inputNode in cmds.listHistory(srcNode): 
        if findStr in str(inputNode):
            makeNode = str(inputNode)
    return makeNode

def create_offset(source_object = '', offset_name = ''):
    cmds.select(cl=1)
    if not cmds.objectType(source_object)=='joint':
        cmds.duplicate(source_object, n = offset_name)
        if cmds.listRelatives(offset_name, s=1):
            cmds.delete(cmds.listRelatives(offset_name, s=1)[0])
        cmds.parent(source_object, offset_name)
    else:
        offset_name = cmds.group(n=offset_name, em=1)
        cmds.parentConstraint(source_object, offset_name, n='delete_con')
        cmds.delete('delete_con')
        if cmds.listRelatives(source_object, p=1):
            cmds.parent(offset_name, cmds.listRelatives(source_object, p=1)[0])
        cmds.parent(source_object, offset_name)
    return offset_name

def attribute_cleanup(object='', translate_key = 1, translate_visible = 1, translate_lock = 0, rotation_key = 1, rotation_visible = 1, rotation_lock = 0, scale_key = 1, scale_visible = 1 , scale_lock = 0):
    axis_list = ['X','Y','Z']
    if cmds.objExists(object):
        for axis_letter in axis_list:
            cmds.setAttr(object + '.translate'+axis_letter, keyable=True)
            cmds.setAttr(object + '.translate'+axis_letter, k=translate_key, cb=translate_visible, l=translate_lock)
            cmds.setAttr(object + '.rotate'+axis_letter, keyable=True)
            cmds.setAttr(object + '.rotate'+axis_letter, k=rotation_key, cb=rotation_visible, l=rotation_lock)
            cmds.setAttr(object + '.scale'+axis_letter, keyable=True)
            cmds.setAttr(object + '.scale'+axis_letter, k=scale_key, cb=scale_visible, l=scale_lock)
        set_keyable(object = object)
        
def set_keyable(object = ''):
    axis_list = ['X','Y','Z']
    if cmds.objExists(object):
        for axis_letter in axis_list:
            if cmds.getAttr(object + '.translate'+axis_letter, cb=True) and not cmds.getAttr(object + '.translate'+axis_letter, keyable=True):
                cmds.setAttr(object + '.translate'+axis_letter, keyable=True)
            if cmds.getAttr(object + '.rotate'+axis_letter, cb=True) and not cmds.getAttr(object + '.rotate'+axis_letter, keyable=True):
                cmds.setAttr(object + '.rotate'+axis_letter, keyable=True)
            if cmds.getAttr(object + '.scale'+axis_letter, cb=True) and not cmds.getAttr(object + '.scale'+axis_letter, keyable=True):
                cmds.setAttr(object + '.scale'+axis_letter, keyable=True)

#from Craig Miller https://vimeo.com/66262994
def create_pole_vector_object(boneA='', boneB='', boneC=''):
    #sel = cmds.ls(sl = 1)
    
    start = cmds.xform(boneA ,q= 1 ,ws = 1,t =1 )
    mid = cmds.xform(boneB ,q= 1 ,ws = 1,t =1 )
    end = cmds.xform(boneC ,q= 1 ,ws = 1,t =1 )
    
    startV = OpenMaya.MVector(start[0] ,start[1],start[2])
    midV = OpenMaya.MVector(mid[0] ,mid[1],mid[2])
    endV = OpenMaya.MVector(end[0] ,end[1],end[2])
    
    startEnd = endV - startV
    startMid = midV - startV
    
    dotP = startMid * startEnd
    proj = float(dotP) / float(startEnd.length())
    startEndN = startEnd.normal()
    projV = startEndN * proj
    
    arrowV = startMid - projV
    arrowV*= 0.5
    finalV = arrowV + midV
    
    cross1 = startEnd ^ startMid
    cross1.normalize()
    
    cross2 = cross1 ^ arrowV
    cross2.normalize()
    arrowV.normalize()
    
    matrixV = [arrowV.x , arrowV.y , arrowV.z , 0 ,
    cross1.x ,cross1.y , cross1.z , 0 ,
    cross2.x , cross2.y , cross2.z , 0,
    0,0,0,1]
    
    matrixM = OpenMaya.MMatrix()
    
    OpenMaya.MScriptUtil.createMatrixFromList(matrixV , matrixM)
    
    matrixFn = OpenMaya.MTransformationMatrix(matrixM)
    
    rot = matrixFn.eulerRotation()
    
    loc = cmds.spaceLocator(n=boneB + 'space_locator_delete')[0]
    cmds.xform(loc , ws =1 , t= (finalV.x , finalV.y ,finalV.z))
    
    cmds.xform ( loc , ws = 1 , rotation = ((rot.x/math.pi*180.0),
    (rot.y/math.pi*180.0),
    (rot.z/math.pi*180.0)))

    return boneB + 'space_locator_delete'

def create_mh_fit_skeleton():
    metahuman_skeleton = [
    'root',
    'pelvis',
    'spine_01',
    'spine_02',
    'spine_03',
    'spine_04',
    'spine_05',
    'neck_01',
    'neck_02',
    'head',
    'clavicle_l',
    'upperarm_l',
    'lowerarm_l',
    'hand_l',
    'middle_metacarpal_l',
    'middle_01_l',
    'middle_02_l',
    'middle_03_l',
    'pinky_metacarpal_l',
    'pinky_01_l',
    'pinky_02_l',
    'pinky_03_l',
    'ring_metacarpal_l',
    'ring_01_l',
    'ring_02_l',
    'ring_03_l',
    'thumb_01_l',
    'thumb_02_l',
    'thumb_03_l',
    'index_metacarpal_l',
    'index_01_l',
    'index_02_l',
    'index_03_l',
    'clavicle_r',
    'upperarm_r',
    'lowerarm_r',
    'hand_r',
    'middle_metacarpal_r',
    'middle_01_r',
    'middle_02_r',
    'middle_03_r',
    'pinky_metacarpal_r',
    'pinky_01_r',
    'pinky_02_r',
    'pinky_03_r',
    'ring_metacarpal_r',
    'ring_01_r',
    'ring_02_r',
    'ring_03_r',
    'thumb_01_r',
    'thumb_02_r',
    'thumb_03_r',
    'index_metacarpal_r',
    'index_01_r',
    'index_02_r',
    'index_03_r',
    'thigh_l',
    'calf_l',
    'foot_l',
    'ball_l',
    'thigh_r',
    'calf_r',
    'foot_r',
    'ball_r',
    'bigtoe_01_l',
    'bigtoe_02_l',
    'indextoe_01_l',
    'indextoe_02_l',
    'middletoe_01_l',
    'middletoe_02_l',
    'ringtoe_01_l',
    'ringtoe_02_l',
    'littletoe_01_l',
    'littletoe_02_l',
    'bigtoe_01_r',
    'bigtoe_02_r',
    'indextoe_01_r',
    'indextoe_02_r',
    'middletoe_01_r',
    'middletoe_02_r',
    'ringtoe_01_r',
    'ringtoe_02_r',
    'littletoe_01_r',
    'littletoe_02_r'
    ]
    if cmds.objExists('DHIbody:root'):
        cmds.select('DHIbody:root')
        cmds.select(hi=1)
        joint_list = cmds.ls(sl=1, type='joint')
        loc_list = []
        for current_joint in joint_list:
            if current_joint.replace('DHIbody:','') in metahuman_skeleton:
                current_loc = current_joint + '_loc'
                if not cmds.objExists(current_loc):
                    cmds.spaceLocator(n=current_loc)
                cmds.parentConstraint(current_joint, current_loc, n='delete_con', mo=0)
                cmds.delete('delete_con')
                loc_list.append(current_loc)
                
        for current_loc in loc_list:
            current_joint = current_loc.replace('_loc','')
            print(current_joint)
            if cmds.listRelatives(current_joint, p=1):
                current_loc_parent = cmds.listRelatives(current_joint, p=1)[0] + '_loc'
                if cmds.objExists(current_loc_parent):
                    cmds.parent(current_loc, current_loc_parent)
        print('Fit skeleton created.')
    else:
        print('DHIbody:root' + ' not found. Please run this script with a non referenced Metahuman in your scene file.')  
              
def create_joints_from_fit_skeleton():
    if cmds.objExists('DHIbody:root_loc'):
        cmds.select('DHIbody:root_loc')
        cmds.select(hi=1)
        loc_list = cmds.ls(sl=1, type='transform') 
        joint_list = []
        
        for current_loc in loc_list:
            current_joint = current_loc.replace('_loc', '')
            cmds.select(cl=1)
            if not cmds.objExists(current_joint):
                cmds.joint(p=(0, 0, 0), n=current_joint)
            cmds.parentConstraint(current_loc, current_joint, mo=0, n='delete_con')
            cmds.delete('delete_con')
            joint_list.append(current_joint)
            
        for current_joint in joint_list:
            current_loc = current_joint + '_loc'
    
            if cmds.listRelatives(current_loc, p=1):
                current_joint_parent = cmds.listRelatives(current_loc, p=1)[0].replace('_loc', '')
                if cmds.objExists(current_joint_parent):
                    cmds.parent(current_joint, current_joint_parent)
                    
        cmds.duplicate('DHIbody:root')
        for current_joint in joint_list:
            current_drv_joint = current_joint.replace('DHIbody:', '') + '_drv'
            cmds.rename(current_joint.replace('DHIbody:', ''), current_drv_joint)
            cmds.parentConstraint(current_drv_joint, current_joint)

def mgTag(object = '', attribute_name = '', attribute_value = '', remove = 0):
    object_list=[]
    if not object:
        object_list = cmds.ls(sl=1)
    else:
        object_list = [object]

    for current_object in object_list:
        if not remove:
            if not cmds.attributeQuery(attribute_name, node = current_object, exists = True):
                cmds.addAttr(current_object, longName = attribute_name, dataType = 'string')
            cmds.setAttr(current_object + '.' + attribute_name, attribute_value, type='string')
            if attribute_value:
                print('Tagged ' + current_object + ' ' + attribute_name + ' as ' + attribute_value + '.')
            else:
                print('Tagged ' + current_object + ' ' + attribute_name + ' as empty.')
        else:
            if cmds.attributeQuery(attribute_name, node=current_object, ex=1):
                cmds.deleteAttr(current_object + '.' + attribute_name)
                print('Removed attribute ' + attribute_name + ' from ' + current_object + '.')

def mgTag_metahuman(remove = 0):
    attribute_name = 'ue_tag'
    attribute_value = ''

    metahuman_body_list = cmds.ls("*DHIbody:root")
    metahuman_face_list = cmds.ls("*FacialControls")
    
    for metahuman_body in metahuman_body_list:
        print('tagging metahumans bodies...')
        mgTag(object = metahuman_body, attribute_name = attribute_name, attribute_value = 'metahuman_body', remove = remove)
        mgTag(object = metahuman_body, attribute_name = 'variant_override', attribute_value = '', remove = remove)
        
    for metahuman_face in metahuman_face_list:
        print('tagging metahumans faces...')
        mgTag(object = metahuman_face, attribute_name = attribute_name, attribute_value = 'metahuman_face', remove = remove)


def add_space_switch():
    # add space switches to rig thanks to Ben Pettit
    dir_str_list = ['l', 'r']

    for letter in dir_str_list:
        ctrl_str = 'arm_pole_vector_' + letter + '_ctrl'
        cmds.addAttr(ctrl_str, ln='space', at='enum', en='World:Hand:')
        cmds.group(em=1, n='arm_pole_vector_' + letter + '_handSpace')
        cmds.parent('arm_pole_vector_' + letter + '_handSpace', cmds.listRelatives(ctrl_str, p =1)[0])
        cmds.parent(ctrl_str, 'arm_pole_vector_' + letter + '_handSpace')
        parent_con = 'hand_' + letter + '_ik_space_ParentCon'
        cmds.parentConstraint('hand_' + letter + '_ik_ctrl', 'arm_pole_vector_' + letter + '_handSpace', mo=1, weight=1, n=parent_con)

        # create set driven keys
        cmds.setAttr(ctrl_str + '.space', 1)
        cmds.setAttr(parent_con + '.hand_' + letter + '_ik_ctrlW0', 1)
        cmds.setDrivenKeyframe(currentDriver='arm_pole_vector_' + letter + '_ctrl.space', at=parent_con + '.hand_' + letter + '_ik_ctrlW0')

        cmds.setAttr(ctrl_str + '.space', 0)
        cmds.setAttr(parent_con + '.hand_' + letter + '_ik_ctrlW0', 0)
        cmds.setDrivenKeyframe(currentDriver='arm_pole_vector_' + letter + '_ctrl.space', at=parent_con + '.hand_' + letter + '_ik_ctrlW0')

        ctrl_strB = 'hand_' + letter + '_ik_ctrl'
        cmds.addAttr(ctrl_strB, longName='space_world_hand_switch', shortName='space_world_hand', attributeType='float', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.connectAttr(ctrl_strB + '.space_world_hand', parent_con + '.hand_' + letter + '_ik_ctrlW0', f=1)
        
        ctrl_str = 'leg_pole_vector_' + letter + '_ctrl'
        cmds.addAttr(ctrl_str, ln='space', at='enum', en='World:Leg:')
        cmds.group(em=1, n='leg_pole_vector_' + letter + '_legSpace')
        cmds.parent('leg_pole_vector_' + letter + '_legSpace', cmds.listRelatives(ctrl_str, p =1)[0])
        cmds.parent(ctrl_str, 'leg_pole_vector_' + letter + '_legSpace')
        parent_con = 'foot_' + letter + '_ik_space_ParentCon'
        cmds.parentConstraint('foot_' + letter + '_ik_ctrl', 'leg_pole_vector_' + letter + '_legSpace', mo=1, weight=1, n=parent_con)

        # create set driven keys
        cmds.setAttr(ctrl_str + '.space', 1)
        cmds.setAttr(parent_con + '.foot_' + letter + '_ik_ctrlW0', 1)
        cmds.setDrivenKeyframe(currentDriver='leg_pole_vector_' + letter + '_ctrl.space', at=parent_con + '.foot_' + letter + '_ik_ctrlW0')

        cmds.setAttr(ctrl_str + '.space', 0)
        cmds.setAttr(parent_con + '.foot_' + letter + '_ik_ctrlW0', 0)
        cmds.setDrivenKeyframe(currentDriver='leg_pole_vector_' + letter + '_ctrl.space', at=parent_con + '.foot_' + letter + '_ik_ctrlW0')

        ctrl_strB = 'foot_' + letter + '_ik_ctrl'
        cmds.addAttr(ctrl_strB, longName='space_world_foot_switch', shortName='space_world_foot', attributeType='float', keyable=True, defaultValue=0.0, minValue=0.0, maxValue=1.0)
        cmds.connectAttr(ctrl_strB + '.space_world_foot', parent_con + '.foot_' + letter + '_ik_ctrlW0', f=1)

mgBuildMetaHumansRigCntrls()
