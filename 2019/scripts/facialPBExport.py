'''
Created on 2021. 1. 19.
NXN
@author: LeeSungJun
'''

import os , sys ,glob
import maya.cmds as cmds
import pymel.core as pm
import maya.mel as mel
import time
import cPickle
import logging
import shutil

_logger = logging.getLogger(__name__)

CAM_NAME = 'FrontCamShape'
TIME_UNIT = 'ntsc'

class FacialPBExport():
    def __init__(self,path):
        self.input_path = path
        self.output_mov = self.out_path(type='mov')
        self.output_bin = self.out_path(type='bin')
        self.open_file()
        
    
    def out_path(self,type='mov'):
        path ,fmt = os.path.splitext(self.input_path)
        if type == 'mov':
            re_path = path + '.mov'
        
        elif type == 'bin':
            re_path = path + '.bin'
        
        return re_path
        
    def open_file(self):
        try:
            cmds.file(self.input_path , o=True ,force=True)
            cmds.currentUnit(time = TIME_UNIT)
        except Exception as e:
            print 'open error:',e
            return
        
        self.set_maya_cam(0)
        self.set_playblast(self.output_mov)
        self.expAnim()
        self.set_maya_cam(1)
        
    def set_maya_cam(self,value):
        
        allCam = cmds.ls(type = 'camera')
    
        for cam in allCam:
            #print cam
            cmds.setAttr (cam + '. rnd', False) 
        
        myCam= cmds.ls(CAM_NAME)
        cmds.setAttr ('%s.rnd'%myCam[0], True)
        
        '''
        rig_grp = pm.ls('*:RIG*','*RIG*')
        for rig in rig_grp:
            rig.visibility.set(0)
        '''
        
        objs = pm.ls(type=('nurbsCurve','joint'))
        for obj in objs:
            obj.lodVisibility.set(value)
        
        
        ctrls = pm.ls('*:Controllers','*Controllers')
        
        for ctrl in ctrls:
            ctrl.visibility.set(value)
        
        
    def set_playblast(self,path):
        
        
        sound_track = cmds.ls(type='audio')
        
        if sound_track:
            try:
                cmds.playblast(f=path,fmt='qt',qlt=100,fp=0,c='H.264'
                               ,wh=[600,800],p=100,viewer=0,offScreen = True
                               ,fo=True,s=sound_track[0])
                
                sound_dir = os.path.dirname(path).replace('/movies','/sound')
                sound_file = os.path.basename(path).replace('.mov','.wav')
                sound_path = sound_dir + '/' + sound_file
                sound_file = cmds.sound(sound_track[0],q=True,f=True)
                shutil.copy(sound_file,sound_path)
            except Exception as e:
                print 'playblast ERROR:',e
        
            
        else:
            try:
                cmds.playblast(f=path,fmt='qt',qlt=100,fp=0,c='H.264'
                               ,wh=[600,800],p=100,viewer=0,offScreen = True
                               ,fo=True)
            except Exception as e:
                print 'playblast ERROR:',e
        
        return
    
    def getTransform(self,root):
            obj = pm.ls(root,dag=True ,type='transform')
            result = self.getKeyframes(obj)
            
            return result
    
    def getKeyframes(self,objs):
            
            all_key_frames = {}
            attr_list =[]
            time_list = []
            value_list =[]
            
            for obj in objs:
                anim_attr = pm.listAnimatable(obj)
                for attr in anim_attr:
                    num_key_frames = pm.keyframe(attr,q=True,keyframeCount=True)
                    if (num_key_frames > 0):
                        times = pm.keyframe(attr,q=True,index = (0,num_key_frames),timeChange=True)
                        values = pm.keyframe(attr,q=True,index = (0,num_key_frames),valueChange=True)
                        for i in range(0,num_key_frames):
                            
                            attr_list.append('%s'%attr)
                            time_list.append(times[i])
                            value_list.append(values[i])
            
            all_key_frames['Attribute'] = attr_list
            all_key_frames['Time'] = time_list
            all_key_frames['Value'] = value_list
            
            return all_key_frames
    
    
    def writeFile(self,path,keyData):
            
        with open(path,'wb') as f:
            f.write(cPickle.dumps(keyData,True))
    
        return
    
    def expAnim(self):
        print 'export key frames'
        
        if 0 != len(pm.ls('ControllersParent')):
            node = pm.ls('ControllersParent','EyeCntr_p')
        
        elif 0 != len(pm.ls('*:ControllersParent')):
            node = pm.ls('*:ControllersParent','*:EyeCntr_p')
            
        else:
            _logger.error('No object matches name: SnappersFacialRig')
            return
            
        get_key_data = self.getTransform(node)
        
        
        try:
            self.writeFile(self.output_bin , get_key_data)
        
       
        except Exception as e:
            print 'ERROR'
           
'''
path_list = ['D:/test/0035_0300_pc_facial_a_0006_v001.ma',
         'D:/test/0035_4000_npc_facial_f_0004_v001.ma',
         'D:/test/0035_4000_npc_facial_f_0010_v001.ma']

if __name__ == '__main__':
    for path_ in path_list:
        c = FacialDataExport(path_)
    
'''
    
        
    
        
        
    
    
   
    
    

    