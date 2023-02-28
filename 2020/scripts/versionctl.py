# -*-coding:utf-8 -*-

import maya.cmds as cmds
import os, re


class Versionctl():
    def __init__(self):
        print("versionctl")

    def version_up(self):
        filepath = cmds.file(q=True, sn=True)
        if not filepath :
            filepath = cmds.file(q=True, l=True)[0]
        if not filepath:
            print("The file name does not exist.")
            return
        
        fname, ext = os.path.splitext(filepath)
        fnameList = os.path.basename(fname).split("_")
        curVer = fnameList[-1]
        
        curVerGrp = re.search("v([0-9]+)", curVer)
        
        if curVerGrp:
            curVerNum = curVerGrp.group(1)
            zvalue = len(curVerNum)    
            nVer = int(curVerNum) + 1
            reVer = str(nVer).zfill(zvalue)
            nfilename = "/".join([os.path.dirname(fname), "_".join(fnameList[:-1])+"_v"+reVer+ext])
            
            checkSave = 0
            if os.path.exists(nfilename):
                confirmV = cmds.confirmDialog( 
                    title='Confirm', 
                    message=u'저장하려는 버젼 파일이 있습니다. 덮어쓸까요?', 
                    button=['Yes','No'], 
                    defaultButton='Yes', 
                    cancelButton='No', 
                    dismissString='No' 
                )
                if confirmV == "Yes":
                    checkSave = 1
            else:
                checkSave = 1
            if checkSave:
                cmds.file(rename=nfilename)
                if ext == ".ma":
                    cmds.file(save=True, type="mayaAscii")
                else:
                    cmds.file(save=True, type="mayaBinary")
            
                print(nfilename)
                        
def versionctl():
    verApp = Versionctl()
    verApp.version_up()
    
