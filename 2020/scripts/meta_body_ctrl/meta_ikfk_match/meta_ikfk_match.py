import os, sys
import maya.cmds as cmds

def ik_fk_match(start_frame = 0, end_frame = 0):

    object = cmds.ls(sl=1)[0]
    namespace=''
    type_str=''
    limb = ''    
    match_transform = 0
    
    if 'arm' in object or 'hand' in object:
        limb = 'arm'
    
    if 'leg' in object or 'foot' in object or 'thigh' in object or 'calf' in object:
        limb = 'leg'

    if ':' in object:
        namespace = object.split(':')[0]+':'
    if '_r_' in object:
        dir_str = 'r'
    if '_l_' in object:
        dir_str = 'l'
    if '_ik_' in object:
        type_str = 'ik'
    if '_fk_' in object:
        type_str = 'fk'
    
    if limb and type_str and dir_str:
        fk_arm_target_list = ['upperarm_' + dir_str + '_fk_ctrl',
        'lowerarm_' + dir_str + '_fk_ctrl',
        'hand_' + dir_str + '_fk_ctrl',
        'arm_pole_vector_' + dir_str + '_match']
        
        ik_arm_source_list =['upperarm_' + dir_str + '_ik_motion',
        'lowerarm_' + dir_str + '_ik_motion',
        'hand_' + dir_str + '_ik_ctrl',
        'arm_pole_vector_' + dir_str + '_ctrl']
        
        fk_leg_target_list =['thigh_' + dir_str + '_fk_ctrl',
        'calf_' + dir_str + '_fk_ctrl',
        'foot_' + dir_str + '_fk_ctrl',
        'ball_' + dir_str + '_fk_ctrl',
        'leg_pole_vector_' + dir_str + '_match']
        
        ik_leg_source_list = ['thigh_' + dir_str + '_ik_motion',
        'calf_' + dir_str + '_ik_motion',
        'foot_' + dir_str + '_ik_ctrl',
        'ball_lift_' + dir_str + '_ik_ctrl',
        'leg_pole_vector_' + dir_str + '_ctrl']
    
        fk_arm_source_list = ['hand_' + dir_str + '_fk_ctrl',
        'arm_pole_vector_' + dir_str + '_match']
    
        ik_arm_target_list =['hand_' + dir_str + '_ik_ctrl',
        'arm_pole_vector_' + dir_str + '_ctrl']
    
        fk_leg_source_list =['foot_' + dir_str + '_fk_ctrl', 'ball_' + dir_str + '_fk_ctrl',
        'leg_pole_vector_' + dir_str + '_match']
            
        ik_leg_target_list = ['foot_' + dir_str + '_ik_ctrl', 'ball_lift_' + dir_str + '_ik_ctrl',
        'leg_pole_vector_' + dir_str + '_ctrl']
    
        if limb == 'arm':
            if type_str == 'ik':
                source_list = fk_arm_source_list
                target_list = ik_arm_target_list
                match_transform = 1
                
            if type_str == 'fk':
                source_list = ik_arm_source_list
                target_list = fk_arm_target_list
                
        if limb == 'leg':
            if type_str == 'ik':
                source_list = fk_leg_source_list
                target_list = ik_leg_target_list
                match_transform = 1
                
            if type_str == 'fk':
                source_list = ik_leg_source_list
                target_list = fk_leg_target_list
        if start_frame and end_frame:
            for current_frame in range(start_frame, end_frame):
                cmds.currentTime(current_frame, update=True, edit=True)
                for num in range(0, len(source_list)):
                    if cmds.objExists(namespace+target_list[num]) and cmds.objExists(namespace+source_list[num]):
                        cmds.matchTransform(namespace+target_list[num], namespace+source_list[num], pos = match_transform, rot=1)
                        cmds.setKeyframe(namespace+target_list[num])

        else:
            for num in range(0, len(source_list)):
                if cmds.objExists(namespace+target_list[num]) and cmds.objExists(namespace+source_list[num]):
                    cmds.matchTransform(namespace+target_list[num], namespace+source_list[num], pos = match_transform, rot=1)
                    cmds.setKeyframe(namespace+target_list[num])
    else:
        print('Please select a hand or leg ik or fk control to apply match to.')