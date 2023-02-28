'''
Created on 2021. 1. 22.
NXN
@author: LeeSungJun
'''
from maya import cmds
from maya import mel
from maya import OpenMayaUI as omui 
import pymel.core as pm


import os, glob, time
import sys
import re
import subprocess

import logging 
import time



#sys.path.append('D:/jun_set/Git/mayaProj/FacialExpTool')

import facialPBExport 



_logger = logging.getLogger(__name__)


# Maya & Pyside
#------------------------------------------------------------------

try:
  from PySide2.QtCore import * 
  from PySide2.QtGui import * 
  from PySide2.QtWidgets import *
  from PySide2.QtUiTools import *
  from shiboken2 import wrapInstance 

except ImportError:
  from PySide.QtCore import * 
  from PySide.QtGui import * 
  from PySide.QtUiTools import *
  from shiboken import wrapInstance 

mayaMainWindowPtr= omui.MQtUtil.mainWindow() 
mayaMainWindow = wrapInstance(long(mayaMainWindowPtr), QWidget) 


# UI PATH
#------------------------------------------------------------------

UI_NAME = 'nxnUI/nxn_facialPBTool_UI.ui'
#UI_NAME = 'nxnUI/nxn_facial_export_UI.ui'
UI_PATH = cmds.internalVar(usd=True) + UI_NAME
'''    
UI_NAME = '/nxnUI/nxn_animBuildTools.ui'
UI_PATH = 'C:/NXN_Tools/maya/ANIMATION' + UI_NAME
'''
WIN_TITLE = 'NXN MOCAP PB Export Tool'
MAIN_WIN_NAME = 'facialExpToolWin'
MAYAPY_PATH = 'c:/program files/autodesk/maya2019/bin/mayapy.exe'
PYTHON_FILE = 'D:/jun_set/Git/mayaProj/FacialExpTool/facialPBExport.py'
#PYTHON_FILE = cmds.internalVar(usd=True) + '/facialPBExport.py'
ANIM_PATH= 'anim/facial/maya/scenes'

# Class / UI IMPORT / Button defined
#------------------------------------------------------------------
class FacialExpToolUI(QMainWindow):
 
    def __init__(self,*args,**kwargs):
       
        super(FacialExpToolUI,self).__init__(*args,**kwargs)
        self.setParent(mayaMainWindow)
        self.setWindowFlags( Qt.Window )
        

    def init_UI(self):
        for nMW in mayaMainWindow.findChildren(QMainWindow):
        # window name 
            if nMW.objectName()  == MAIN_WIN_NAME:
                nMW.deleteLater()
        loader = QUiLoader()
        uifile = QFile(UI_PATH)
        uifile.open(QFile.ReadOnly)
        self.faceExpTool_ui = loader.load(uifile, parentWidget= self)
        self.faceExpTool_ui.setWindowTitle(WIN_TITLE)
        uifile.close()
        self.faceExpTool_ui.show()
        self.signal_button()
    

    def signal_button(self):
        self.faceExpTool_ui.shotLoadBtn.clicked.connect(self.show_dialog)
        self.faceExpTool_ui.dataExpBtn.clicked.connect(self.send_data)

    def show_dialog(self):
        self.impFacefile = QFileDialog.getOpenFileNames()[0]
            
        if 0 < len(self.impFacefile) : self.faceExpTool_ui.shotPathListWdg.clear()
        
        for file in self.impFacefile:
            #print os.path.splitext(os.path.basename(file))
            self.faceExpTool_ui.shotPathListWdg.addItem(file)
     

    def get_facial_path(self):
        count_ = self.faceExpTool_ui.shotPathListWdg.count()
        wdg_items = []
        
        for i in range(count_):
            src_item = self.faceExpTool_ui.shotPathListWdg.item(i).text()
            wdg_items.append(src_item)

        return wdg_items
    

    def send_data(self):
        path_list = self.get_facial_path()
        
        selItem = self.faceExpTool_ui.PB_listWidget.selectedItems()
        selCamList = []
        for i in selItem:
            selCamList.append(str(i.text()))
        
        optDic = {
            "width":self.faceExpTool_ui.pb_width_spinBox.value(),
            "height":self.faceExpTool_ui.pb_height_spinBox.value(),
            "scale":self.faceExpTool_ui.pb_scale_doubleSpinBox.value(),
            "PB":self.faceExpTool_ui.PB_checkBox.isChecked(),
            "PBcam":selCamList,
            "BIN":self.faceExpTool_ui.BIN_checkBox.isChecked(),
            "WAV":self.faceExpTool_ui.WAV_checkBox.isChecked(),
        }
        print("optDic", optDic)
        
        for path_ in path_list:
            c = facialPBExport.FacialPBExport(path_, optDic)
            

if __name__ == '__main__':
    show_ui = FacialExpToolUI()
    show_ui.init_UI()
else:
    show_ui = FacialExpToolUI()
    show_ui.init_UI()