"""
This example demonstrates Maya UI Window for simple and non-programmatic creation the scene with the creating functional rig.
- usage in command line:
    - call without arguments:
        - will not start with error message: "DNAViewer needs to be run with Maya2022"
    NOTE: Script cannot be called with Python or mayapy, it' must be called in Maya Script Editor.
- usage in Maya:
    1. copy whole content of this file to Maya Script Editor
    2. change value of ROOT_DIR to absolute path of dna_calibration, e.g. `c:/dna_calibration` in Windows or `/home/user/dna_calibration`. Important:
    Use `/` (forward slash), because Maya uses forward slashes in path.

    Expected: Maya will show UI.

NOTE: If running on Linux, please make sure to append the LD_LIBRARY_PATH with absolute path to the lib/linux directory before running the example:
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:<path-to-lib-linux-dir>
"""
import json
from json import loads

from os import environ
from os import path as ospath
from sys import path as syspath
from sys import platform

# if you use Maya, use absolute path
#ROOT_DIR = f"{ospath.dirname(ospath.abspath(__file__))}".replace("\\", "/")
ROOT_DIR = f"C:/dna_calibration"
ROOT_LIB_DIR = f"{ROOT_DIR}/lib"

if platform == "win32":
    LIB_DIR = f"{ROOT_LIB_DIR}/windows"
elif platform == "linux":
    LIB_DIR = f"{ROOT_LIB_DIR}/linux"
else:
    raise OSError(
        "OS not supported, please compile dependencies and add value to LIB_DIR"
    )

# Add bin directory to maya plugin path
if "MAYA_PLUG_IN_PATH" in environ:
    separator = ":" if platform == "linux" else ";"
    environ["MAYA_PLUG_IN_PATH"] = separator.join([environ["MAYA_PLUG_IN_PATH"], LIB_DIR])
else:
    environ["MAYA_PLUG_IN_PATH"] = LIB_DIR

# Adds directories to path
syspath.insert(0, ROOT_DIR)
syspath.insert(0, LIB_DIR)

import dna
import sys
from maya import OpenMayaUI as omui 
from PySide2.QtCore import * 
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2 import __version__
from shiboken2 import wrapInstance 
from maya.app.general import mayaMixin
#mayaMainWindowPtr = omui.MQtUtil.mainWindow() 
#mayaMainWindow= wrapInstance( int(mayaMainWindowPtr), QWidget)

titleA=u'UE_MH_DNA_NeutralJoint_Custom_UI_V20230220'
class UE_MH_RDNA_UI(mayaMixin.MayaQWidgetBaseMixin,QWidget):
    def __init__(self, parent=None):
        
        getPath_dna=pm.ls(type='embeddedNodeRL4')
        binaryFilePath=''
        if (getPath_dna):
            binaryFilePath=getPath_dna[0].dnaFilePath.get()
        readStream = dna.FileStream(binaryFilePath, dna.FileStream.AccessMode_Read , dna.FileStream.OpenMode_Binary)
        self.reader = dna.BinaryStreamReader(readStream)
        self.reader.read()         
        
        super(UE_MH_RDNA_UI, self).__init__(parent)
        self.setObjectName('UE_MH_DNA_Custom_UI_V20230220')
        self.setWindowTitle(titleA)
        self.setGeometry(500, 100, 940, 500)
        self.allQVBoxLayout = QVBoxLayout()
        self.table_cMHdnaLoad_btn=QPushButton("Current_MH_DNA_load")
        self.table_cMHdnaLoad_btn.clicked.connect(self.table_cMHdnaLoad_run)
        self.table_cRjntLoad_btn=QPushButton("Custom_retagetJoint_load")
        self.table_cRjntLoad_btn.clicked.connect(self.table_cRjntLoad_run)
        self.table_import_json_btn=QPushButton("json_import")
        self.table_import_json_btn.clicked.connect(self.table_import_json_run)
        self.table_import_dna_btn=QPushButton("DNA_import")
        self.table_import_dna_btn.clicked.connect(self.table_import_dna_run)
        self.textedit_dnaPath = QLineEdit()      
        self.table = QTableWidget( )
        self.table.setColumnCount( 7 )

        self.table.setColumnWidth(0,170)
        self.table.setColumnWidth(1,120)
        self.table.setColumnWidth(2,120)
        self.table.setColumnWidth(3,120)
        self.table.setColumnWidth(4,120)
        self.table.setColumnWidth(5,120)
        self.table.setHorizontalHeaderLabels(["Name" ,"Tx" , "Ty", "Tz", "Rx", "Ry", "Rz" ])
        self.dna_export_json_btn=QPushButton("DNA_export_json")
        self.dna_export_json_btn.clicked.connect(self.dna_export_json_run)
        self.table_export_json_btn=QPushButton("TableWidget_export_json")        
        self.table_export_json_btn.clicked.connect(self.table_export_json_run)
        self.table_save_json_btn=QPushButton("TableWidget_TO_DNA_save")        
        self.table_save_json_btn.clicked.connect(self.table_save_json_run)
        self.allQVBoxLayout.addWidget(self.table_cMHdnaLoad_btn)
        self.allQVBoxLayout.addWidget(self.table_cRjntLoad_btn)
        self.allQVBoxLayout.addWidget(self.table_import_json_btn)
        self.allQVBoxLayout.addWidget(self.table_import_dna_btn)        
        self.allQVBoxLayout.addWidget(self.textedit_dnaPath)
        
        self.allQVBoxLayout.addWidget(self.table)
        
        self.allQVBoxLayout.addWidget(self.dna_export_json_btn)
        self.allQVBoxLayout.addWidget(self.table_export_json_btn)

        self.allQVBoxLayout.addWidget(self.table_save_json_btn)
        self.setLayout(self.allQVBoxLayout)
    def table_setRowCount(self):
        count = self.reader.getJointCount()
        self.table.setRowCount( count )
    def table_setItem_name(self):
        count = self.reader.getJointCount()
        for i in range(count):
            textA = self.reader.getJointName(i)
            itemA = QTableWidgetItem(textA)
            self.table.setItem(i,0,itemA)
    def table_setTranslate(self):
        count = self.reader.getJointCount()
        for i in range(count):
            vectorA = self.reader.getNeutralJointTranslation(i)
            itemA = QTableWidgetItem('%0.3f'%(vectorA[0]))
            itemB = QTableWidgetItem('%0.3f'%(vectorA[1]))
            itemC = QTableWidgetItem('%0.3f'%(vectorA[2]))
            self.table.setItem(i,1,itemA)
            self.table.setItem(i,2,itemB)
            self.table.setItem(i,3,itemC)
    def table_setRotate(self):
        count = self.reader.getJointCount()
        for i in range(count):
            vectorA = self.reader.getNeutralJointRotation(i)
            itemA = QTableWidgetItem('%0.3f'%(vectorA[0]))
            itemB = QTableWidgetItem('%0.3f'%(vectorA[1]))
            itemC = QTableWidgetItem('%0.3f'%(vectorA[2]))
            self.table.setItem(i,4,itemA)
            self.table.setItem(i,5,itemB)
            self.table.setItem(i,6,itemC)
    def table_cMHdnaLoad_run(self):
        self.table.clear()
        self.table.setHorizontalHeaderLabels(["Name" ,"Tx" , "Ty", "Tz", "Rx", "Ry", "Rz" ])
        getPath_dna=pm.ls(type='embeddedNodeRL4')
        binaryFilePath=getPath_dna[0].dnaFilePath.get()
        readStream = dna.FileStream(binaryFilePath, dna.FileStream.AccessMode_Read , dna.FileStream.OpenMode_Binary)
        self.reader = dna.BinaryStreamReader(readStream)
        self.reader.read()        
        self.textedit_dnaPath.setText(binaryFilePath)
        self.table_setRowCount( )
        self.table_setItem_name( )
        self.table_setTranslate( )
        self.table_setRotate( )
        #print ('a')
    def table_cRjntLoad_run(self):
        count = reader.getJointCount()
        for i in range(1,count):
            nameA = self.reader.getJointName(i)
            vectorA = pm.PyNode(nameA).t.get()
            itemA = QTableWidgetItem('%0.3f'%(vectorA[0]))
            itemB = QTableWidgetItem('%0.3f'%(vectorA[1]))
            itemC = QTableWidgetItem('%0.3f'%(vectorA[2]))
            self.table.setItem(i,1,itemA)
            self.table.setItem(i,2,itemB)
            self.table.setItem(i,3,itemC)        
    def table_import_dna_run(self):
        self.table.clear()
        self.table.setHorizontalHeaderLabels(["Name" ,"Tx" , "Ty", "Tz", "Rx", "Ry", "Rz" ])
        files, _ = QFileDialog.getOpenFileNames(self,"getdna", "","All Files (*);;DNA Files (*.dna)", options=QFileDialog.DontUseNativeDialog)
        if files:
            binaryFilePathA=files[0]
            readStream = dna.FileStream(binaryFilePathA, dna.FileStream.AccessMode_Read , dna.FileStream.OpenMode_Binary)
            self.reader = dna.BinaryStreamReader(readStream)
            self.reader.read()        
            self.textedit_dnaPath.setText(binaryFilePathA)
            self.table_setRowCount( )
            self.table_setItem_name( )
            self.table_setTranslate( )
            self.table_setRotate( )
    def dna_export_json_run(self):
        fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()",".json","Json Files (*.json)", options=QFileDialog.DontUseNativeDialog)
        if fileName:
            getPath_dna=pm.ls(type='embeddedNodeRL4')
            binaryFilePath=getPath_dna[0].dnaFilePath.get()
            readStream = dna.FileStream(binaryFilePath, dna.FileStream.AccessMode_Read , dna.FileStream.OpenMode_Binary)
            self.reader = dna.BinaryStreamReader(readStream)
            self.reader.read()   
            jsonString='{"size":"%d"}'%self.reader.getJointCount()
            d = json.loads( jsonString )
            jointName={}
            NeutralTranslate={}
            NeutralRoattion={}
            count = self.reader.getJointCount()
            for i in range(count):
                jointName["%d"%i]        = self.reader.getJointName(i)
                NeutralTranslate["%d"%i] = self.reader.getNeutralJointTranslation(i)
                NeutralRoattion["%d"%i]  = self.reader.getNeutralJointRotation(i)
            d["jointName"]=jointName
            d["NeutralTranslate"]=NeutralTranslate
            d["NeutralRoattion"]=NeutralRoattion   
            with open(fileName, "w") as json_file:            
                json.dump(d, json_file)
    def table_export_json_run(self):
        fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()",".json","Json Files (*.json)", options=QFileDialog.DontUseNativeDialog)
        if fileName:        
            count=self.table.rowCount()    
            jsonString='{"size":"%d"}'%count
            d = json.loads( jsonString )  
            jointName={}
            NeutralTranslate={}
            NeutralRoattion={}
            for i in range(count):
                jointName["%d"%i]        = self.table.item(i, 0).text()            
                NeutralTranslate["%d"%i] = [ float(self.table.item(i, 1).text()) , float(self.table.item(i, 2).text()) , float(self.table.item(i, 3).text()) ]
                NeutralRoattion["%d"%i]  = [ float(self.table.item(i, 4).text()) , float(self.table.item(i, 5).text()) , float(self.table.item(i, 6).text()) ]
            d["jointName"]=jointName
            d["NeutralTranslate"]=NeutralTranslate
            d["NeutralRoattion"]=NeutralRoattion
            with open(fileName, "w") as json_file:            
                json.dump(d, json_file)
    def table_import_json_run(self):
        self.table.clear()
        self.table.setHorizontalHeaderLabels(["Name" ,"Tx" , "Ty", "Tz", "Rx", "Ry", "Rz" ])
        files, _ = QFileDialog.getOpenFileNames(self,"getdna", "","Json Files (*.json)", options=QFileDialog.DontUseNativeDialog)
        if files:  
            with open(files[0], "r") as json_file:
                json_data = json.load(json_file) 
            self.table.setRowCount( int(json_data['size']) )                             
            for i in range( int(json_data['size'])  ):
                itemZ = QTableWidgetItem( json_data['jointName']['%d'%i] ) 
                self.table.setItem(i,0,itemZ)
                itemA = QTableWidgetItem(str(json_data['NeutralTranslate']['%d'%i][0]))
                itemB = QTableWidgetItem(str(json_data['NeutralTranslate']['%d'%i][1]))
                itemC = QTableWidgetItem(str(json_data['NeutralTranslate']['%d'%i][2]))
                itemD = QTableWidgetItem(str(json_data['NeutralRoattion']['%d'%i][0]))
                itemE = QTableWidgetItem(str(json_data['NeutralRoattion']['%d'%i][1]))
                itemF = QTableWidgetItem(str(json_data['NeutralRoattion']['%d'%i][2]))
                self.table.setItem(i,1,itemA)
                self.table.setItem(i,2,itemB)
                self.table.setItem(i,3,itemC)
                self.table.setItem(i,4,itemD)
                self.table.setItem(i,5,itemE)
                self.table.setItem(i,6,itemF)                
    def table_save_json_run(self):
        pathA = self.textedit_dnaPath.text()
        fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","%s"%pathA.rsplit('/',1)[0],"DNA Files (*.dna)", options=QFileDialog.DontUseNativeDialog)
        if fileName:        
            stream = dna.FileStream(fileName, dna.FileStream.AccessMode_Write, dna.FileStream.OpenMode_Binary)
            self.writer = dna.BinaryStreamWriter(stream)
            readStream = dna.FileStream(pathA, dna.FileStream.AccessMode_Read , dna.FileStream.OpenMode_Binary)
            self.reader = dna.BinaryStreamReader(readStream)
            self.reader.read()   
            self.writer.setFrom(self.reader)
            #for i in dir(writer):
            #    print(i)
            count=self.table.rowCount() 
            setT=[]  
            for i in range(0,count):
                setT.append( [ float(self.table.item(i, 1).text()) , float(self.table.item(i, 2).text()) , float(self.table.item(i, 3).text()) ] )
                #setT.append( [ 0.0, 0.0, 0.0 ] )
            # Creates the DNA
            self.writer.setNeutralJointTranslations(setT)
            self.writer.write()                    
            print (fileName)
if cmds.window(u"UE_MH_DNA_Custom_UI_V20230220", q=True, ex=True):
    cmds.deleteUI(u"UE_MH_DNA_Custom_UI_V20230220", window=True)
if cmds.window(u"UE_MH_DNA_Custom_UI_V20230220", q=True, ex=True):
    cmds.deleteUI(u"UE_MH_DNA_Custom_UI_V20230220", window=True)
UE_MH_RDNA_UI().show()