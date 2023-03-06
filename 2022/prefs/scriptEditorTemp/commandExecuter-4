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
        
        # 창 크기 조절
        self.setFixedSize(800, 1200)
        
        # 창 생성 위치
        self.setGeometry(500, 100, 940, 500)
        
        # QVBoxLayout() 은 메뉴들이 아래로 생김, QHBoxLayout() 는 옆으로 생김        
        self.allQVBoxLayout = QVBoxLayout()        
        
        
        # QFrame으로 실선 삽입 가능 - 디자인 요소
                               
        # addSpacing(30) 하면 위에서 부터 30픽셀 공간 들어감
        # self.allQVBoxLayout.addSpacing(30)        
                
        
        # self.allQVBoxLayout.addWidget(QFrame(), QFrame.setFrameStyle(QFrame.HLine | QFrame.Sunken))
        # self.allQVBoxLayout.addWidget(QFrame(1, QFrame.setFrameStyle(QFrame.HLine | QFrame.Sunken)))


        self.table_cMHdnaLoad_btn=QPushButton("Current_MH_DNA_load")

        self.table_cRjntLoad_btn=QPushButton("Custom_retagetJoint_load")
        # self.table_cRjntLoad_btn.clicked.connect(self.table_cRjntLoad_run)
        self.table_import_json_btn=QPushButton("json_import")
        
        # self.table_import_json_btn.clicked.connect(self.table_import_json_run)
        self.table_import_dna_btn=QPushButton("DNA_import")
        
        # self.table_import_dna_btn.clicked.connect(self.table_import_dna_run)
        self.textedit_dnaPath = QLineEdit()      
        self.table = QTableWidget( )
        self.table.setColumnCount( 7 )
# 스킨웨이트 값들 테이블 관련
        self.table.setColumnWidth(0,170)
        self.table.setColumnWidth(1,120)
        self.table.setColumnWidth(2,120)
        self.table.setColumnWidth(3,120)
        self.table.setColumnWidth(4,120)
        self.table.setColumnWidth(5,120)
        self.table.setHorizontalHeaderLabels(["Name" ,"Tx" , "Ty", "Tz", "Rx", "Ry", "Rz" ])
        self.dna_export_json_btn=QPushButton("DNA_export_json")
        # self.dna_export_json_btn.clicked.connect(self.dna_export_json_run)
        self.table_export_json_btn=QPushButton("TableWidget_export_json")        
        # self.table_export_json_btn.clicked.connect(self.table_export_json_run)
        self.table_save_json_btn=QPushButton("TableWidget_TO_DNA_save")        
        # self.table_save_json_btn.clicked.connect(self.table_save_json_run)
        self.allQVBoxLayout.addWidget(self.table_cMHdnaLoad_btn)
        
        self.DrawLine()
        
        self.allQVBoxLayout.addWidget(self.table_cRjntLoad_btn)

        self.DrawLine()

        self.allQVBoxLayout.addWidget(self.table_import_json_btn)

        self.DrawLine()
        
        self.allQVBoxLayout.addWidget(self.table_import_dna_btn)        

        self.DrawLine()
        
        self.allQVBoxLayout.addWidget(self.textedit_dnaPath)

        self.DrawLine()
        
        self.allQVBoxLayout.addWidget(self.table)

        self.DrawLine()
        
        self.allQVBoxLayout.addWidget(self.dna_export_json_btn)

        self.DrawLine()
        
        self.allQVBoxLayout.addWidget(self.table_export_json_btn)

        self.DrawLine()

        self.allQVBoxLayout.addWidget(self.table_save_json_btn)

        self.DrawLine()
        
        self.setLayout(self.allQVBoxLayout)
        
    def DrawLine(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.HLine)
        frame.setFrameShadow(QFrame.Sunken)
        self.allQVBoxLayout.addWidget(frame)
        
        
        
if cmds.window(u"UE_MH_DNA_Custom_UI_V20230220", q=True, ex=True):
    cmds.deleteUI(u"UE_MH_DNA_Custom_UI_V20230220", window=True)
if cmds.window(u"UE_MH_DNA_Custom_UI_V20230220", q=True, ex=True):
    cmds.deleteUI(u"UE_MH_DNA_Custom_UI_V20230220", window=True)
UE_MH_RDNA_UI().show()