'''
Created on 2021. 1. 19.
NXN
@author: LeeSungJun
'''

import os , sys ,glob
import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import pymel.core as pm
import maya.mel as mel
import time
from collections import Counter
import cPickle
import logging
import shutil

_logger = logging.getLogger(__name__)

CAM_NAME = 'FrontCamShape'
TIME_UNIT = 'ntsc'
path = sys.argv[1]

class FacialDataExport():
    def __init__(self,*args):
        self.input_path = args[0]
        print self.input_path
        self.main(self.input_path)
   
    
    def getFile(self,fullpath):
        file_list = glob.glob(fullpath+'/*')
        ma_f = [file_ for file_ in file_list if file_.endswith('.ma')]
        
        if 0 == len(ma_f):
            return 
        
        ma_f.sort()
        sort_list=[ma_f[0]]
        for ma in ma_f:
            
            sort_file = os.path.basename(sort_list[-1]).split('.')[0]
            ma_file = os.path.basename(ma).split('.')[0]
           
            if ma_file[:-5] != sort_file[:-5]:
                sort_list.append(ma)
            
            else:
                sort_list[-1] = ma
            
        return sort_list
    
    def openFile(self,open_file):
        try:
            cmds.file(open_file, o=True ,force=True)
            cmds.currentUnit(time = TIME_UNIT)
            self.expAnim(open_file)
        except Exception as e:
            print 'open error:',e
    
    def getTransform(self,root):
            obj = pm.ls(root,dag=True ,type='transform')
            result = self.getKeyframes(obj)
            
            return result
    
    def mayaCamSet(self,*args):
        
        allCam = cmds.ls(type = 'camera')
    
        for cam in allCam:
            print cam
            cmds.setAttr (cam + '. rnd', False) 
        
        myCam= cmds.ls(CAM_NAME)
        cmds.setAttr ('%s.rnd'%myCam[0], True)
        rig_grp = pm.ls('*:RIG*','*RIG*')
        for rig in rig_grp:
            rig.visibility.set(0)
        
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
    
    def expAnim(self,path):
       
        if 0 != len(pm.ls('ControllersParent')):
            node = pm.ls('ControllersParent','EyeCntr_p')
        
        elif 0 != len(pm.ls('*:ControllersParent')):
            node = pm.ls('*:ControllersParent','*:EyeCntr_p')
            
        else:
            _logger.error('No object matches name: SnappersFacialRig')
            return
            
        get_key_data = self.getTransform(node)
        rename_key_file = os.path.basename(path).replace('.ma','.bin')
        rename_pb_file = os.path.basename(path).replace('.ma','.mov')
        key_path = os.path.dirname(path).replace('/scenes','/data') + '/' + rename_key_file
        pb_path = os.path.dirname(path).replace('/scenes','/movies') + '/' + rename_pb_file
        
        try:
            self.writeFile(key_path , get_key_data)
            self.mayaCamSet()
            self.pbFile(pb_path)
            
        except Exception as e:
            print 'Maya set error:',e
            self.pbFile(pb_path)
    
    def pbFile(self,path):
        
        
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
        
    def main(self,seq_path):
        start_time = time.time()
        shot_file = self.getFile(seq_path)
               
        for file_ in shot_file:
            self.openFile(file_)


input_ = FacialDataExport(path)

    