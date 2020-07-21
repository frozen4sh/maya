import os
import sys
import math
import json
import re
from shutil import copyfile
from distutils.dir_util import copy_tree
from collections import OrderedDict
from functools import partial
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaAnim as oma
import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaAnim as OpenMayaAnim

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin, MayaQWidgetDockableMixin
from ui.Qt import QtCore, QtGui, QtWidgets, QtCompat
from ui.Qt.QtWidgets import QWidget
from ui.Qt.QtCore import Signal, Slot, QObject

# Import Generated UI
import ui.RigManager_UI as UI
reload(UI)


VERSION = "2.1.2"


def undo(func):
	def wrapper(*args, **kwargs):
		cmds.undoInfo(openChunk=True)
		try:
			ret = func(*args, **kwargs)
		finally:
			cmds.undoInfo(closeChunk=True)
		return ret
	return wrapper

class Logger(object):
	DEBUG = False
	import logging

	@classmethod
	def LOG(cls, args):
		if cls.DEBUG:
			print(args)

	@classmethod
	def LOGW(cls, args):
		if cls.DEBUG:
			logging.warning(args)
	
	@classmethod
	def LOGE(cls, args):
		if cls.DEBUG:
			logging.error(args)


class DockableWidget(object):
	def __init__(self):
		self.dockableWidget = self.__getDockableWindow()

	def __getMayaMainWindow(self):
		mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow() 
		mayaMainWindow = QtCompat.wrapInstance(long(mayaMainWindowPtr), QtWidgets.QWidget)
		return mayaMainWindow
	
	def __getDockableWindow(self):
		self.__deleteDockableWindow()
		self.workspaceControlName = self.__class__.__name__ + "WorkspaceControl"
		dock_ctrl = cmds.workspaceControl(self.workspaceControlName)
		ptr = OpenMayaUI.MQtUtil.findControl(dock_ctrl)
		dock_widget = QtCompat.wrapInstance(long(ptr), QtWidgets.QWidget)
		dock_widget.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		return dock_widget

	def __deleteDockableWindow(self):
		self.workspaceControlName = self.__class__.__name__ + "WorkspaceControl"
		if cmds.workspaceControl(self.workspaceControlName, exists = True, q = True):
			cmds.deleteUI(self.workspaceControlName)


# ************************************************************************************************** #

class RigManipulator(object):
	def __init__(self, mirrorFunc):
		self.toolName = self.__class__.__name__ + "Ctx"
		self.mirrorFunc = mirrorFunc
		self.__currentCntr = None
		self.__currentSelectionList  = None
		self.__currentCntrMirror = None
		self.__character_namespace = ""
		self.__m3dview = omui.M3dView.active3dView()
		self.__mouseModifier = 0
		self.__middleMouseButton = False
		self.__isEyesSelected = False
		self.__isJawSelected = False
		self.__bMirrorSelected = False
		self.__senstivity = 0.025
		self.__eyeSpeed = 1.0
		self.__anchorX = 0.0
		self.__anchorY = 0.0
		self.__posX = 0.0
		self.__posY = 0.0
		self.__deltX = 0.0
		self.__deltY = 0.0
		self.__deltaDistance = 0.0

		# loaded data
		self.__rigManagerPath = os.path.dirname(__file__).replace("\\", "/")
		self.__FACS_data_path = os.path.join(self.__rigManagerPath, "data", "Controllers_FACS.json").replace("\\", "/")
		self.__Adj_data_path = os.path.join(self.__rigManagerPath, "data", "Controllers_Adj.json").replace("\\", "/")
		
		f = open(self.__FACS_data_path, "r")
		self.__FACS_data_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		f = open(self.__Adj_data_path, "r")
		self.__Adj_data_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

	def createRigManipulator(self):
		if cmds.draggerContext(self.toolName, exists=True):
			cmds.deleteUI(self.toolName)
		cmds.draggerContext(self.toolName, inz = "cmds.selectPref(clickBoxSize = 5)" ,pressCommand = self.onPress ,dragCommand = self.onDrag ,
							 fnz = "cmds.selectPref(clickBoxSize = 4)" , rc = self.onRelease, name = self.toolName, cursor = "crossHair", 
							 undoMode = "step", i1 = "Snappers_Logo.png", i2 = "Snappers_Logo.png", i3 = "Snappers_Logo.png")
		cmds.setToolTo(self.toolName)

	def onPress(self):
		self.getMouseButton()
		self.__anchorX, self.__anchorY, _ = cmds.draggerContext( self.toolName, query=True, anchorPoint=True)
		self.__currentCntr = self.getObjectUnderCursor()
		self.__currentSelectionList = cmds.ls(sl = True) or []
		self.__mouseModifier = cmds.getModifiers()
		self.__bMirrorSelected = False
		self.__currentCntrMirror = []

		if self.__mouseModifier == 0:
			self.__currentSelectionList = []

		if self.__mouseModifier == 5:
			self.__bMirrorSelected = True

		# remove current cntr if in selection
		if self.__currentCntr in self.__currentSelectionList:
			self.__currentSelectionList.remove(self.__currentCntr)
		
		# get mirror 
		if self.__currentCntr or self.__mouseModifier == 5:
			selection_list = self.__currentSelectionList or []
			if self.__currentCntr:
				selection_list = [self.__currentCntr] + selection_list
			self.__currentCntrMirror = self.mirrorFunc(selection_list, self.__bMirrorSelected)
		
		
	def onDrag(self):
		dragVector = self.getDragVector()
		cntrVectorX, cntrVectorY, cntrVectorZ = self.getCurrentCntrVectors()

		dotValueX = dragVector * cntrVectorX
		dotValueY = dragVector * cntrVectorY
		dotValueZ = dragVector * cntrVectorZ

		deltaValueX = dotValueX * self.__deltaDistance * self.__senstivity
		deltaValueY = dotValueY * self.__deltaDistance * self.__senstivity
		deltaValueZ = dotValueZ * self.__deltaDistance * self.__senstivity

		if self.__mouseModifier != 4 :
			if self.__currentCntr:
				if self.__isEyesSelected:
					self.setAttr("%s.tx"%self.__currentCntr, cmds.getAttr("%s.tx"%self.__currentCntr) + self.__deltX * self.__senstivity * self.__eyeSpeed)
					self.setAttr("%s.ty"%self.__currentCntr, cmds.getAttr("%s.ty"%self.__currentCntr) + self.__deltY * self.__senstivity * self.__eyeSpeed)
				else:
					self.setAttr("%s.tx"%self.__currentCntr, cmds.getAttr("%s.tx"%self.__currentCntr) + deltaValueX)
					self.setAttr("%s.ty"%self.__currentCntr, cmds.getAttr("%s.ty"%self.__currentCntr) + deltaValueY)
					self.setAttr("%s.tz"%self.__currentCntr, cmds.getAttr("%s.tz"%self.__currentCntr) + deltaValueZ)
			
			if self.__currentCntrMirror and not self.__isEyesSelected:
				for cntr in self.__currentCntrMirror:
					self.setAttr("%s.tx"%cntr, cmds.getAttr("%s.tx"%cntr) + deltaValueX)
					self.setAttr("%s.ty"%cntr, cmds.getAttr("%s.ty"%cntr) + deltaValueY)
					self.setAttr("%s.tz"%cntr, cmds.getAttr("%s.tz"%cntr) + deltaValueZ)
			
			if self.__currentSelectionList and not self.__isEyesSelected:
				for cntr in self.__currentSelectionList:
					self.setAttr("%s.tx"%cntr, cmds.getAttr("%s.tx"%cntr) + deltaValueX)
					self.setAttr("%s.ty"%cntr, cmds.getAttr("%s.ty"%cntr) + deltaValueY)
					self.setAttr("%s.tz"%cntr, cmds.getAttr("%s.tz"%cntr) + deltaValueZ)

		self.__m3dview.refresh()

	def onRelease(self):
		if (self.__mouseModifier == 0) and not self.__isEyesSelected:
			cmds.select(self.__currentCntr, replace = True)
		
		if (self.__mouseModifier == 1 or self.__mouseModifier == 5) and not self.__isEyesSelected:
			cmds.select(self.__currentCntr, tgl = True)

		if self.__mouseModifier == 4:
			if self.__currentCntr:
				self.setAttr("%s.tx"%self.__currentCntr, 0.0)
				self.setAttr("%s.ty"%self.__currentCntr, 0.0)
				self.setAttr("%s.tz"%self.__currentCntr, 0.0)
			if self.__currentSelectionList:
				for cntr in self.__currentSelectionList:
					self.setAttr("%s.tx"%cntr, 0.0)
					self.setAttr("%s.ty"%cntr, 0.0)
					self.setAttr("%s.tz"%cntr, 0.0)

	def getObjectUnderCursor(self):
		self.__isEyesSelected = False
		self.__isJawSelected = False
		self.__m3dview = omui.M3dView.active3dView()
		panel = cmds.getPanel(underPointer=True) or None
		if panel:
			shape = (cmds.hitTest(panel, self.__anchorX, self.__m3dview.portHeight() - self.__anchorY) or [None])[0]
			if shape:
				cntr = cmds.listRelatives(shape, p = True)[0]
				if cmds.attributeQuery("EyesMesh", node = shape, exists=True):
					 self.__isEyesSelected = True
					 cntr = self.__character_namespace + ":EyeCntr"
					 return cntr
				elif "JawCntr" in cntr:
					self.__isJawSelected = True
					return cntr
				elif cntr.split(":")[-1] in self.__FACS_data_map["Attributes"].keys():
					return cntr
				elif cntr.split(":")[-1] in self.__Adj_data_map["Attributes"].keys():
					return cntr
				else:
					return None
		else:
			return None

	def setCharacterNamespace(self, character_namespace):
		self.__character_namespace = character_namespace

	def getCurrentCntrVectors(self):
		vec_x = om.MVector([0.0, 0.0, 0.0])
		vec_y = om.MVector([0.0, 0.0, 0.0])
		vec_z = om.MVector([0.0, 0.0, 0.0])
		matrix = om.MMatrix()

		if self.__currentCntr:
			matrix = om.MMatrix(cmds.getAttr("%s.worldMatrix[0]"%self.__currentCntr))
		else:
			if self.__currentSelectionList:
				matrix = om.MMatrix(cmds.getAttr("%s.worldMatrix[0]"%self.__currentSelectionList[-1]))

		if not self.__middleMouseButton:
			pnt_1 = om.MPoint([0.0, 0.0, 0.0, 1.0]) * matrix
			pnt_2 = om.MPoint([0.0, 1.0, 0.0, 1.0]) * matrix
			pnt_3 = om.MPoint([1.0, 0.0, 0.0, 1.0]) * matrix
			sp_1 = self.__m3dview.worldToView(pnt_1)
			sp_2 = self.__m3dview.worldToView(pnt_2)
			sp_3 = self.__m3dview.worldToView(pnt_3)
			vec_x = om.MVector((sp_3[0] - sp_1[0], sp_3[1] - sp_1[1], 0.0)).normalize()
			vec_y = om.MVector((sp_2[0] - sp_1[0], sp_2[1] - sp_1[1], 0.0)).normalize()
		else:
			vec_z = om.MVector([1.0, 0.0, 0.0])

		return vec_x, vec_y, vec_z

	def getDragVector(self):
		self.__posX, self.__posY, _ = cmds.draggerContext(self.toolName, query=True, dragPoint=True)
		self.__deltX = self.__posX - self.__anchorX
		self.__deltY = self.__posY - self.__anchorY
		vector = om.MVector([self.__deltX, self.__deltY, 0.0])
		self.__deltaDistance = vector.length()
		normVector = vector.normalize()
		self.__anchorX = self.__posX
		self.__anchorY = self.__posY
		return normVector

	def getMouseButton(self):
		mouseNumber = cmds.draggerContext(self.toolName, button = True, q = True)
		if mouseNumber == 2:
			self.__middleMouseButton = True
		else:
			self.__middleMouseButton = False

	def setAttr(self, attribute, value):
		try:
			cmds.setAttr(attribute, value)
		except:
			pass

	def setSenstivity(self, value):
		self.__senstivity = float(value)

	def setEyeSpeed(self, value):
		self.__eyeSpeed = float(value)


# ---------------------------------------------------------------------------------------------------------- #

class RigManager(MayaQWidgetDockableMixin, QtWidgets.QMainWindow, UI.Ui_RigManager):

	def __init__(self, dock = True):
		self.__deleteDockableWindow()
		super(RigManager, self).__init__(parent = None)
		self.setupUi(self)
		self.__createChannelBox()
		self.setWindowTitle("Snappers Rig Manager (%s)"%VERSION)


		self.initVariables()
		self.connectSignals()
		cmds.evalDeferred(self.refreshUI)
		cmds.evalDeferred( lambda :  self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True) )
		cmds.evalDeferred( lambda :  self.parentWidget().setAttribute(QtCore.Qt.WA_DeleteOnClose, True) )

	def __getMayaMainWindow(self):
		mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow() 
		mayaMainWindow = QtCompat.wrapInstance(long(mayaMainWindowPtr), QtWidgets.QWidget)
		return mayaMainWindow

	def __deleteDockableWindow(self):
		self.workspaceControlName = self.__class__.__name__ + "WorkspaceControl"
		if cmds.workspaceControl(self.workspaceControlName, exists = True, q = True):
			cmds.deleteUI(self.workspaceControlName)

	def initVariables(self):
		self.rigManagerPath = os.path.dirname(__file__).replace("\\", "/")
		self.image_01 = os.path.join(self.rigManagerPath, "ui", "Rig_Face_03.jpg").replace("\\", "/")
		self.image_02 = os.path.join(self.rigManagerPath, "ui", "Rig_Face_02.jpg").replace("\\", "/")
		self.image_01_dis = os.path.join(self.rigManagerPath, "ui", "Rig_Face_03_D.jpg").replace("\\", "/")
		self.image_02_dis = os.path.join(self.rigManagerPath, "ui", "Rig_Face_02_D.jpg").replace("\\", "/")
		self.facs_cntrs_grp.setStyleSheet("QGroupBox{\n border-image: url(%s) 0 0 0 0 stretch stretch; }"%self.image_01)
		self.adj_cntrs_grp.setStyleSheet("QGroupBox{\n border-image: url(%s) 0 0 0 0 stretch stretch; }"%self.image_02)
		self.FACS_data_path = os.path.join(self.rigManagerPath, "data", "Controllers_FACS.json").replace("\\", "/")
		self.Adj_data_path = os.path.join(self.rigManagerPath, "data", "Controllers_Adj.json").replace("\\", "/")
		self.ui_FACS_data_path = os.path.join(self.rigManagerPath, "data", "UI_FACS_Data.json").replace("\\", "/")
		self.ui_Adj_data_path = os.path.join(self.rigManagerPath, "data", "UI_Adj_Data.json").replace("\\", "/")
		self.ui_FACS_btns_path = os.path.join(self.rigManagerPath, "data", "UI_FACS_Btns.json").replace("\\", "/")
		self.ui_Adj_btns_path = os.path.join(self.rigManagerPath, "data", "UI_Adj_Btns.json").replace("\\", "/")
		
		f = open(self.ui_FACS_data_path, "r")
		self.ui_FACS_data_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		f = open(self.ui_Adj_data_path, "r")
		self.ui_Adj_data_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		f = open(self.FACS_data_path, "r")
		self.FACS_data_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		f = open(self.Adj_data_path, "r")
		self.Adj_data_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		f = open(self.ui_FACS_btns_path, "r")
		self.FACS_btns_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		f = open(self.ui_Adj_btns_path, "r")
		self.Adj_btns_map = json.load(f, object_pairs_hook = OrderedDict)
		f.close()

		self.character_namespace = ""
		self.character_namespace_list = []

		# list of [pose attributes]
		self.pose_attributes_list = []
		for cntr, attrs in self.FACS_data_map["Attributes"].iteritems():
			for attr in attrs:
				self.pose_attributes_list.append("%s.%s"%(cntr, attr))
		for cntr, attrs in self.Adj_data_map["Attributes"].iteritems():
			for attr in attrs:
				self.pose_attributes_list.append("%s.%s"%(cntr, attr))

		# dict of (pose attributes : float value) 
		self.current_pose_map = {}

		# slider lerp values and flags
		self.bSliderEntered = False
		self.sliderLerpValues = []

		# callbacks
		self.callback_id_array = om.MCallbackIdArray()
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "SelectionChanged", self.applyMirrorSelection ))
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "Undo", lambda *args: self.refreshPosesList() ))
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "Redo", lambda *args: self.refreshPosesList() ))
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "SceneOpened", lambda *args: self.refreshUI() ))
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "SceneImported", lambda *args: self.refreshUI() ))
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "NewSceneOpened", lambda *args: self.refreshUI() ))
		self.callback_id_array.append( om.MEventMessage.addEventCallback( "PostSceneRead", lambda *args: self.refreshUI() ))

		# rig manipulator 
		self.rigManipulator = RigManipulator(self.mirrorFunc)
		self.Cntr_Dragger_Button.clicked.connect( lambda : self.rigManipulator.createRigManipulator() )

	def connectSignals(self):
		self.tabWidget.currentChanged.connect( self.replaceButtons )
		# self.destroyed.connect( self.removeCallbacks )
		self.destroyed.connect( lambda : om.MMessage.removeCallbacks(self.callback_id_array) )

		# lists
		self.Characters_List_lst.currentItemChanged.connect( lambda : self.rigManipulator.setCharacterNamespace(self.Characters_List_lst.currentItem().text()) )
		self.Characters_List_lst.currentItemChanged.connect( self.setCurrentCharacter )
		self.Poses_List_lst.currentItemChanged.connect( self.setCurrentPose )
		self.Poses_List_lst.itemClicked.connect( self.setCurrentPose )
		
		# pose slider
		self.PoseWeightSlider.sliderPressed.connect( self.poseWeightDragEnter )
		self.PoseWeightSlider.valueChanged.connect( self.poseWeightDragMove )
		self.PoseWeightSlider.sliderReleased.connect( self.poseWeightDragLeave )

		# buttons
		self.ResetAllCntrs_Button.clicked.connect( self.restAllCntrs )
		self.Refresh_btn.clicked.connect( self.refreshUI )
		self.Add_Pose_btn.clicked.connect( self.addPose )
		self.Update_Pose_btn.clicked.connect( self.updatePose )
		self.Rename_Pose_btn.clicked.connect( self.renamePose )
		self.Delete_Pose_btn.clicked.connect( self.deletePose )
		self.Set_Pose_btn.clicked.connect( self.setPoseOnAllControllers )
		self.Set_Sel_Pose_btn.clicked.connect( self.setPoseOnSelectedControllers )
		self.Export_btn.clicked.connect( self.exportPoses )
		self.Import_btn.clicked.connect( self.importPoses )
		
		# connect FACS controllers
		cntr_list = self.FACS_data_map["Attributes"].keys()
		cntr_list.remove("EyeCntr_L")
		cntr_list.remove("EyeCntr_R")
		for cntr in cntr_list:
			self.__dict__[cntr].clicked.connect( self.pickCntr )
		
		# connect Adj controllers
		cntr_list = self.Adj_data_map["Attributes"].keys()
		cntr_list.remove("Fill_1_L_cntr")
		cntr_list.remove("Fill_1_R_cntr")
		for cntr in cntr_list:
			self.__dict__[cntr].clicked.connect( self.pickCntr )

		# connect Animation actions
		self.actionAdd_AnimCurves.triggered.connect( self.addAnimCurvesAttributes )
		self.actionRemove_AnimCurves.triggered.connect( self.removeAnimCurvesAttributes )

		# connect FACS/Adjustment actions
		self.AllControllers_SelectAll.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Attributes"].keys() + self.Adj_data_map["Attributes"].keys() ) )
		self.AllControllers_Select_Mouth.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Mouth"] + self.Adj_data_map["Mouth"] ) )
		self.AllControllers_Select_Eyes.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Eyes"] + self.Adj_data_map["Eyes"] ) )
		self.AllControllers_Select_Brows.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Brows"] + self.Adj_data_map["Brows"] ) )

		self.AllControllers_ResetAll.triggered.connect( lambda : self.restAllCntrs() )
		self.AllControllers_Reset_Selection.triggered.connect( lambda : self.resetFACS_Adj( cmds.ls(sl = True) ) )
		self.AllControllers_Reset_Mouth.triggered.connect( lambda : self.resetFACS_Adj( self.FACS_data_map["Mouth"] + self.Adj_data_map["Mouth"] ))
		self.AllControllers_Reset_Eyes.triggered.connect( lambda : self.resetFACS_Adj( self.FACS_data_map["Eyes"] + self.Adj_data_map["Eyes"] ))
		self.AllControllers_Reset_Brows.triggered.connect( lambda : self.resetFACS_Adj( self.FACS_data_map["Brows"] + self.Adj_data_map["Brows"] ))

		# connect FACS actions
		self.ShowActive_Deformation.clicked.connect( self.showActiveDeformation )
		self.ShowActive_Offset.clicked.connect( self.showActiveOffset )
		self.Debug_Anim.clicked.connect( self.showActiveOnly )
		self.HideAttributes.clicked.connect( self.hideChannelBoxAttributes )

		self.FACS_SelectAll.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Attributes"].keys() ) )
		self.FACS_Select_Mouth.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Mouth"] ) )
		self.FACS_Select_Eyes.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Eyes"] ) )
		self.FACS_Select_Brows.triggered.connect( lambda : self.selectCntrList( self.FACS_data_map["Brows"] ) )
		
		self.FACS_SelectAll_btn.clicked.connect( lambda : self.selectCntrList( self.FACS_data_map["Attributes"].keys() ) )
		self.FACS_Select_Mouth_btn.clicked.connect( lambda : self.selectCntrList( self.FACS_data_map["Mouth"] ) )
		self.FACS_Select_Eyes_btn.clicked.connect( lambda : self.selectCntrList( self.FACS_data_map["Eyes"] ) )
		self.FACS_Select_Brows_btn.clicked.connect( lambda : self.selectCntrList( self.FACS_data_map["Brows"] ) )

		self.FACS_ResetAll.triggered.connect( lambda : self.resetFACS( self.FACS_data_map["Attributes"].keys() ) )
		self.FACS_Reset_Selection.triggered.connect( lambda : self.resetFACS( cmds.ls(sl = True) ) )
		self.FACS_Reset_Mouth.triggered.connect( lambda : self.resetFACS( self.FACS_data_map["Mouth"] ))
		self.FACS_Reset_Eyes.triggered.connect( lambda : self.resetFACS( self.FACS_data_map["Eyes"] ))
		self.FACS_Reset_Brows.triggered.connect( lambda : self.resetFACS( self.FACS_data_map["Brows"] ))

		self.FACS_Reset_All_btn.clicked.connect( lambda : self.resetFACS( self.FACS_data_map["Attributes"].keys() ) )
		self.FACS_Reset_Selection_btn.clicked.connect( lambda : self.resetFACS( cmds.ls(sl = True) ) )
		self.FACS_Reset_Mouth_btn.clicked.connect( lambda : self.resetFACS( self.FACS_data_map["Mouth"] ))
		self.FACS_Reset_Eyes_btn.clicked.connect( lambda : self.resetFACS( self.FACS_data_map["Eyes"] ))
		self.FACS_Reset_Brows_btn.clicked.connect( lambda : self.resetFACS( self.FACS_data_map["Brows"] ))

		self.FACS_Show_Active_chbx.toggled.connect( self.FACS_Show_Active.setChecked )		
		self.FACS_Show_Active.toggled.connect( self.FACS_Show_Active_chbx.setChecked )
		self.FACS_Show_Active_chbx.toggled.connect( lambda : self.showActiveFACS() )

		# self.FACS_Show_Hide_UI.triggered.connect( self.showHideFACS )
		self.FACS_Show_Hide_UI_chbx.toggled.connect( self.FACS_Show_Hide_UI.setChecked )		
		self.FACS_Show_Hide_UI.toggled.connect( self.FACS_Show_Hide_UI_chbx.setChecked )
		self.FACS_Show_Hide_UI_chbx.toggled.connect( lambda : self.showHideFACS() )

		# self.FACS_2D_Mode.triggered.connect( self.set2DMode )
		self.FACS_2D_Mode_chbx.toggled.connect( self.FACS_2D_Mode.setChecked )		
		self.FACS_2D_Mode.toggled.connect( self.FACS_2D_Mode_chbx.setChecked )
		self.FACS_2D_Mode_chbx.toggled.connect( lambda : self.set2DMode() )

		# connect Adj actions
		self.Adj_SelectAll.triggered.connect( lambda : self.selectCntrList( self.Adj_data_map["Attributes"].keys() ) )
		self.Adj_Select_Mouth.triggered.connect( lambda : self.selectCntrList( self.Adj_data_map["Mouth"] ) )
		self.Adj_Select_Eyes.triggered.connect( lambda : self.selectCntrList( self.Adj_data_map["Eyes"] ) )
		self.Adj_Select_Brows.triggered.connect( lambda : self.selectCntrList( self.Adj_data_map["Brows"] ) )

		self.Adj_SelectAll_btn.clicked.connect( lambda : self.selectCntrList( self.Adj_data_map["Attributes"].keys() ) )
		self.Adj_Select_Mouth_btn.clicked.connect( lambda : self.selectCntrList( self.Adj_data_map["Mouth"] ) )
		self.Adj_Select_Eyes_btn.clicked.connect( lambda : self.selectCntrList( self.Adj_data_map["Eyes"] ) )
		self.Adj_Select_Brows_btn.clicked.connect( lambda : self.selectCntrList( self.Adj_data_map["Brows"] ) )
		
		self.Adj_Reset_All.triggered.connect( lambda : self.resetAdj( self.Adj_data_map["Attributes"].keys() ) )
		self.Adj_Reset_Selection.triggered.connect( lambda : self.resetAdj( cmds.ls(sl = True) ) )
		self.Adj_Reset_Mouth.triggered.connect( lambda : self.resetAdj( self.Adj_data_map["Mouth"] ) )
		self.Adj_Reset_Eyes.triggered.connect( lambda : self.resetAdj( self.Adj_data_map["Eyes"] ) )
		self.Adj_Reset_Brows.triggered.connect( lambda : self.resetAdj( self.Adj_data_map["Brows"] ) )

		self.Adj_Reset_All_btn.clicked.connect( lambda : self.resetAdj( self.Adj_data_map["Attributes"].keys() ) )
		self.Adj_Reset_Selection_btn.clicked.connect( lambda : self.resetAdj( cmds.ls(sl = True) ) )
		self.Adj_Reset_Mouth_btn.clicked.connect( lambda : self.resetAdj( self.Adj_data_map["Mouth"] ) )
		self.Adj_Reset_Eyes_btn.clicked.connect( lambda : self.resetAdj( self.Adj_data_map["Eyes"] ) )
		self.Adj_Reset_Brows_btn.clicked.connect( lambda : self.resetAdj( self.Adj_data_map["Brows"] ) )

		self.Adj_Show_Active_chbx.toggled.connect( self.Adj_Show_Active.setChecked )		
		self.Adj_Show_Active.toggled.connect( self.Adj_Show_Active_chbx.setChecked )
		self.Adj_Show_Active_chbx.toggled.connect( lambda : self.showActiveAdj() )

		# self.Adj_Show_Hide.triggered.connect( self.showHideAdj )
		self.Adj_Show_Hide_chbx.toggled.connect( self.Adj_Show_Hide.setChecked )		
		self.Adj_Show_Hide.toggled.connect( self.Adj_Show_Hide_chbx.setChecked )
		self.Adj_Show_Hide_chbx.toggled.connect( lambda : self.showHideAdj() )

		# self.Adj_Proximity.triggered.connect( self.setProximity )
		self.Adj_Proximity_chbx.toggled.connect( self.Adj_Proximity.setChecked )		
		self.Adj_Proximity.toggled.connect( self.Adj_Proximity_chbx.setChecked )
		self.Adj_Proximity_chbx.toggled.connect( lambda : self.setProximity() )

	def poseWeightDragEnter(self):
		self.sliderLerpValues = []
		selection_list = cmds.ls(sl = True, type = "transform")

		for key, value in self.current_pose_map.iteritems():
			if self.character_namespace:
				name = (self.character_namespace + ":" + key)
				cntr = name.split('.')[0]
			else:
				name = key
				cntr = name.split('.')[0]
			if self.PoseSliderMode.isChecked():
				if cntr in selection_list:
					self.sliderLerpValues.append( (name, cmds.getAttr(name), value) )
			else:
				if cmds.objExists(name):
					self.sliderLerpValues.append( (name, cmds.getAttr(name), value) )

		cmds.undoInfo(openChunk=True)
		self.bSliderEntered = True

	def poseWeightDragMove(self):
		if not self.bSliderEntered:
			return
		weight = float(self.PoseWeightSlider.value()) / 10000.0
		for i in range(len(self.sliderLerpValues)):
			value = self.sliderLerpValues[i][1] * (1.0 - weight) + (self.sliderLerpValues[i][2] * weight)
			self.setAttr(self.sliderLerpValues[i][0], value)

	def poseWeightDragLeave(self):
		self.bSliderEntered = False
		cmds.undoInfo(closeChunk=True)	

	@undo
	def addPose(self):
		pose_name = self.Pose_Name_txt.text()
		self.Pose_Name_txt.clear()

		if pose_name == "":
			cmds.error("invalid name")
			return

		if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == "" or
			 cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == None):
			cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", "[]", type = "string")
		
		if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues") == "" or
			 cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues") == None):
			cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", "[]", type = "string")

		pose_values = {}
		for attr in self.pose_attributes_list:
			if cmds.objExists(self.character_namespace + ":" + attr):
				pose_values[attr] = cmds.getAttr(self.character_namespace + ":" + attr)
			else:
				pose_values[attr] = 0.0

		current_name_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames")
		current_name_list = json.loads(current_name_list)
		current_name_list.append(pose_name)
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", json.dumps(current_name_list), type = "string" )

		current_values_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues")
		current_values_list = json.loads(current_values_list)
		current_values_list.append(pose_values)
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", json.dumps(current_values_list), type = "string" )

		self.refreshPosesList()

	@undo
	def updatePose(self):
		index = self.Poses_List_lst.currentIndex().row()
		if index < 0:
			cmds.error("Select Pose From List")
			return
		
		pose_values = {}
		for attr in self.pose_attributes_list:
			if cmds.objExists(self.character_namespace + ":" + attr):
				pose_values[attr] = cmds.getAttr(self.character_namespace + ":" + attr)
			else:
				pose_values[attr] = 0.0
		
		current_values_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues")
		current_values_list = json.loads(current_values_list)
		current_values_list[index] = pose_values
		self.current_pose_map = pose_values
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", json.dumps(current_values_list), type = "string" )
			
	@undo
	def renamePose(self):
		new_name = self.Pose_Name_txt.text()
		self.Pose_Name_txt.clear()
		index = self.Poses_List_lst.currentIndex().row()

		if index < 0:
			cmds.error("Select Pose From List")
			return
		if new_name == "":
			cmds.error("invalid name")
			return

		current_name_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames")
		current_name_list = json.loads(current_name_list)
		current_name_list[index] = new_name
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", json.dumps(current_name_list), type = "string" )
		
		self.refreshPosesList()

	@undo
	def deletePose(self):
		index = self.Poses_List_lst.currentIndex().row()
		if index < 0:
			cmds.error("Select Pose From List")
			return
		
		current_name_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames")
		current_name_list = json.loads(current_name_list)
		current_name_list.pop(index)
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", json.dumps(current_name_list), type = "string" )

		current_values_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues")
		current_values_list = json.loads(current_values_list)
		current_values_list.pop(index)
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", json.dumps(current_values_list), type = "string" )

		self.refreshPosesList()

	@undo
	def setPoseOnAllControllers(self):
		for key, value in self.current_pose_map.iteritems():
			self.setAttr(self.character_namespace + ":" + key, value)

	@undo
	def setPoseOnSelectedControllers(self):
		if(self.Poses_List_lst.currentIndex().row() < 0):
			cmds.warning("Select Pose From The List")
			return
		selection_list = cmds.ls(sl = True, type = "transform")
		filtered_FACS = []
		filtered_Adj = []
		namespace = self.character_namespace + ":"
		FACS_list = self.FACS_data_map["Attributes"].keys()
		Adj_list =  self.Adj_data_map["Attributes"].keys()

		for item in selection_list:
			if (namespace in item):
				name = item.replace(namespace, "")
			else:
				name = item
			if (name in FACS_list):
				filtered_FACS.append(name)
			elif (name in Adj_list):
				filtered_Adj.append(name)
			else:
				pass

		for item in filtered_FACS:
			for attr in self.FACS_data_map["Attributes"][item]:
				attr_name = self.character_namespace + ":" + item + "." + attr
				attr_value  = self.current_pose_map["%s.%s"%(item, attr)]
				self.setAttr(attr_name, attr_value)
		
		for item in filtered_Adj:
			for attr in self.Adj_data_map["Attributes"][item]:
				attr_name = self.character_namespace + ":" + item + "." + attr
				attr_value  = self.current_pose_map["%s.%s"%(item, attr)]
				self.setAttr(attr_name, attr_value)
		
	def exportPoses(self):
		if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == "" or
			 cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == None):
			cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", "[]", type = "string")
		
		if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues") == "" or
			 cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues") == None):
			cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", "[]", type = "string")

		current_name_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames")
		current_name_list = json.loads(current_name_list)

		current_values_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues")
		current_values_list = json.loads(current_values_list)

		export_map = {}
		export_map["poseNames"] = current_name_list
		export_map["poseValues"] = current_values_list

		export_dir =  cmds.fileDialog2(fileFilter = "*.pose" ,dialogStyle=2 , cap = "Export Poses" , fm = 0 , okc = "Export")
		if export_dir:
			export_dir = export_dir[0]
		else:
			return 

		f = open(export_dir, "w+")
		f.write(json.dumps(export_map))
		f.close()

	def importPoses(self):
		import_dir =  cmds.fileDialog2(fileFilter = "*.pose" ,dialogStyle=2 , cap = "Export Poses" , fm = 1 , okc = "Import")
		if import_dir:
			import_dir = import_dir[0]
		else:
			return 

		if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == "" or
			 cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == None):
			cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", "[]", type = "string")
		
		if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues") == "" or
			 cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues") == None):
			cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", "[]", type = "string")

		current_name_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames")
		current_name_list = json.loads(current_name_list)

		current_values_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues")
		current_values_list = json.loads(current_values_list)

		f = open(import_dir, "r")
		imported_poses = f.read()
		f.close()

		imported_map = json.loads(imported_poses)
		current_name_list = current_name_list + imported_map["poseNames"]
		current_values_list = current_values_list + imported_map["poseValues"]

		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", json.dumps(current_name_list), type = "string" )
		cmds.setAttr(self.character_namespace + ":Rig_Manager.posesValues", json.dumps(current_values_list), type = "string" )

		self.refreshPosesList()

	def refreshUI(self):
		# referesh character name spaces 
		self.refreshCharacterList()
		# refresh poses
		self.refreshPosesList()
		# refresh tabs visibility
		self.refreshTabsVisibility()
	
	def refreshPosesList(self):
		self.Poses_List_lst.clear()
		try:
			if (cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == "" or
				cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames") == None):
				cmds.setAttr(self.character_namespace + ":Rig_Manager.posesNames", "[]", type = "string")

			current_name_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesNames")
			current_name_list = json.loads(current_name_list)
			for name in current_name_list:
				self.Poses_List_lst.addItem(name)
		except:
			pass

	def setCurrentPose(self):
		index = self.Poses_List_lst.currentIndex().row()
		if index > -1:
			current_values_list = cmds.getAttr(self.character_namespace + ":Rig_Manager.posesValues")
			current_values_list = json.loads(current_values_list)
			self.current_pose_map = current_values_list[index]

	def refreshCharacterList(self):
		self.Characters_List_lst.blockSignals(True)
		
		# store current character namespace
		current_namespace = self.character_namespace

		self.Characters_List_lst.clear()
		self.character_namespace_list = [""]

		for ns in cmds.namespaceInfo(listOnlyNamespaces=True, sn=True):
			if cmds.objExists(ns + ":" + "Rig_Manager"):
				Logger.LOG(ns)
				self.character_namespace_list.append(ns)
		
		for ns in self.character_namespace_list:
			self.Characters_List_lst.addItem(ns)

		if (current_namespace in self.character_namespace_list) and (current_namespace != None):
			idx = self.character_namespace_list.index(current_namespace)
			self.Characters_List_lst.setCurrentRow(idx)
		else:
			self.Characters_List_lst.setCurrentRow(0)


		self.Characters_List_lst.blockSignals(False)

	def refreshTabsVisibility(self):
		if cmds.objExists(self.character_namespace + ":Rig_Manager"):
			self.facs_cntrs_grp.setStyleSheet("QGroupBox{\n border-image: url(%s) 0 0 0 0 stretch stretch; }"%self.image_01)
			self.tab.setEnabled(True)
			self.tab_3.setEnabled(True)
			# menu items
			self.menuAllControllers.setDisabled(False)
			self.menuFACS.setDisabled(False)
		else:
			self.facs_cntrs_grp.setStyleSheet("QGroupBox{\n border-image: url(%s) 0 0 0 0 stretch stretch; }"%self.image_01_dis)
			self.tab.setEnabled(False)
			self.tab_3.setEnabled(False)
			# menu items
			self.menuAllControllers.setDisabled(True)
			self.menuFACS.setDisabled(True)
		
		if cmds.objExists(self.character_namespace + ":AdjustmentLayer"):
			self.adj_cntrs_grp.setStyleSheet("QGroupBox{\n border-image: url(%s) 0 0 0 0 stretch stretch; }"%self.image_02)
			self.tab_2.setEnabled(True)
			# menu items
			self.menuAllControllers.setDisabled(False)
			self.menuAdjustment.setDisabled(False)
		else:
			self.adj_cntrs_grp.setStyleSheet("QGroupBox{\n border-image: url(%s) 0 0 0 0 stretch stretch; }"%self.image_02_dis)
			self.tab_2.setEnabled(False)
			# menu items
			self.menuAllControllers.setDisabled(True)
			self.menuAdjustment.setDisabled(True)

	def setCurrentCharacter(self):
		self.character_namespace = self.Characters_List_lst.currentItem().text()
		Logger.LOG(self.character_namespace)
		
		# refresh poses
		self.refreshPosesList()
		# refresh tabs visibility
		self.refreshTabsVisibility()

	@undo
	def showActiveOnly(self):
		self.FACS_Show_Active_chbx.blockSignals(True)
		self.Adj_Show_Active_chbx.blockSignals(True)

		self.ShowActive_Deformation.setChecked(False)
		self.ShowActive_Offset.setChecked(False)
		self.FACS_Show_Active.setChecked(False)
		self.Adj_Show_Active.setChecked(False)

		self.FACS_Show_Active_chbx.blockSignals(False)
		self.Adj_Show_Active_chbx.blockSignals(False)

		for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
			if self.Debug_Anim.isChecked():
				flag = False
				for attr in attr_list:
					if cmds.getAttr(self.character_namespace + ":" + cntr_name + "." + attr) > 0:
						flag = True
						break 
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", flag)
			else:
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)
		
		for cntr_name, attr_list in self.FACS_data_map["Attributes"].iteritems():
			if self.Debug_Anim.isChecked():
				flag = False
				for attr in attr_list:
					if cmds.getAttr(self.character_namespace + ":" + cntr_name + "." + attr) > 0:
						flag = True
						break 
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", flag)
			else:
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

	@undo
	def showActiveAdj(self):
		if self.Debug_Anim.isChecked():
			for cntr_name, attr_list in self.FACS_data_map["Attributes"].iteritems():
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)
		self.Debug_Anim.setChecked(False)

		for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
			if self.Adj_Show_Active.isChecked():
				flag = False
				for attr in attr_list:
					if cmds.getAttr(self.character_namespace + ":" + cntr_name + "." + attr) > 0:
						flag = True
						break 
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", flag)
			else:
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

	@undo
	def showHideAdj(self):
		self.setAttr(self.character_namespace + "AdjustmentLayerControllers.v", self.Adj_Show_Hide.isChecked())

	@undo
	def setProximity(self):
		if self.Adj_Proximity.isChecked():
			for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
				self.setAttr(self.character_namespace + ":" + cntr_name + '_tag.visibilityMode', 2)
		else:
			for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
				self.setAttr(self.character_namespace + ":" + cntr_name + '_tag.visibilityMode', 0)

	@undo
	def showActiveFACS(self):
		if self.Debug_Anim.isChecked():
			for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

		self.ShowActive_Deformation.setChecked(False)
		self.ShowActive_Offset.setChecked(False)
		self.Debug_Anim.setChecked(False)

		for cntr_name, attr_list in self.FACS_data_map["Attributes"].iteritems():
			if self.FACS_Show_Active_chbx.isChecked():
				flag = False
				for attr in attr_list:
					if cmds.getAttr(self.character_namespace + ":" + cntr_name + "." + attr) > 0:
						flag = True
						break 
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", flag)
			else:
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

	@undo
	def showActiveDeformation(self):
		if self.Debug_Anim.isChecked():
			for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

		self.FACS_Show_Active_chbx.blockSignals(True)

		self.FACS_Show_Active.setChecked(False)
		self.ShowActive_Offset.setChecked(False)
		self.Debug_Anim.setChecked(False)

		self.FACS_Show_Active_chbx.blockSignals(False)

		for cntr_name, attr_list in self.FACS_data_map["Attributes"].iteritems():
			if self.ShowActive_Deformation.isChecked():
				flag = False
				for attr in attr_list:
					if (cmds.getAttr(self.character_namespace + ":" + cntr_name + "." + attr) > 0) and "_offset" not in attr:
						flag = True
						break 
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", flag)
			else:
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

	@undo
	def showActiveOffset(self):
		if self.Debug_Anim.isChecked():
			for cntr_name, attr_list in self.Adj_data_map["Attributes"].iteritems():
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

		self.FACS_Show_Active_chbx.blockSignals(True)

		self.FACS_Show_Active.setChecked(False)
		self.ShowActive_Deformation.setChecked(False)
		self.Debug_Anim.setChecked(False)

		self.FACS_Show_Active_chbx.blockSignals(False)

		for cntr_name, attr_list in self.FACS_data_map["Attributes"].iteritems():
			if self.ShowActive_Offset.isChecked():
				flag = False
				for attr in attr_list:
					if (cmds.getAttr(self.character_namespace + ":" + cntr_name + "." + attr) > 0) and "_offset" in attr:
						flag = True
						break 
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", flag)
			else:
				self.setAttr(self.character_namespace + ":" + cntr_name + ".v", True)

	@undo
	def showHideFACS(self):
		self.setAttr(self.character_namespace + "Controllers.v", self.FACS_Show_Hide_UI.isChecked())

	@undo
	def set2DMode(self):
		self.setAttr(self.character_namespace + "UI2D.visibility", self.FACS_2D_Mode.isChecked())
		self.setAttr(self.character_namespace + "Tracks_blendShape.envelope", not self.FACS_2D_Mode.isChecked())
		self.setAttr(self.character_namespace + "UI2DBS.envelope", self.FACS_2D_Mode.isChecked())

		self.setAttr(self.character_namespace + "NoseCntr_pp_parentConstraint1.NoseLocatorW1", self.FACS_2D_Mode.isChecked())
		self.setAttr(self.character_namespace + "NoseCntr_pp_parentConstraint1.follicle177W0", not self.FACS_2D_Mode.isChecked())
		self.setAttr(self.character_namespace + "JawCntr_pp_parentConstraint1.JawLocatorW1", self.FACS_2D_Mode.isChecked())
		self.setAttr(self.character_namespace + "JawCntr_pp_parentConstraint1.follicle178W0", not self.FACS_2D_Mode.isChecked())

	@undo
	def setAttr(self, attr, value):
		try:
			cmds.setAttr(attr, value)
		except:
			pass

	@undo
	def selectCntr(self, cntr_name):
		Logger.LOG(cntr_name)
		mod = cmds.getModifiers()
		if (mod%2 == 1 ):
			cmds.select( self.character_namespace + ":" + cntr_name, tgl = True)
		else:
			cmds.select(cl=True)
			cmds.select( self.character_namespace + ":" + cntr_name, add = True)

	@undo
	def selectCntrList(self, inputList):
		cntr_list = inputList[:]
		for i in range(len(cntr_list)):
			cntr_list[i] = self.character_namespace + ":" + cntr_list[i]
		mod = cmds.getModifiers()
		if (mod%2 == 1 ):
			cmds.select(cntr_list, add = True)
		else:
			cmds.select(cntr_list, r = True)
		
		cmds.setFocus("MayaWindow")

	@undo
	def restAllCntrs(self):
		self.resetFACS( self.FACS_data_map["Attributes"].keys() )
		self.resetAdj( self.Adj_data_map["Attributes"].keys() )

	@undo
	def resetFACS_Adj(self, inputList):
		self.resetFACS( inputList )
		self.resetAdj( inputList )

	@undo	
	def resetFACS(self, inputList):
		for cntr_name in inputList:
			try:
				cntr_name = cntr_name.split(":")[-1]
				attr_list = self.FACS_data_map["Attributes"][cntr_name]
				for attr in attr_list:
					self.setAttr(self.character_namespace + ":" + cntr_name + "." + attr, 0.0)
			except:
				pass
	
	@undo		
	def resetAdj(self, inputList):
		for cntr_name in inputList:
			try:
				cntr_name = cntr_name.split(":")[-1]
				attr_list = self.Adj_data_map["Attributes"][cntr_name]
				for attr in attr_list:
					self.setAttr(self.character_namespace + ":" + cntr_name + "." + attr, 0.0)
			except:
				pass

	def pickCntr(self):
		cntr_name = self.sender().objectName()
		try:
			self.selectCntr(cntr_name)
		except:
			pass

	def __createChannelBox(self):
		# create holder window for channel box
		wnd = cmds.window(title = "channel box window holder", widthHeight = [420, 60])
		cmds.columnLayout()

		# create channel box
		offset_attrs = ['UprLip_R_MR_offset', 'Nose_offset', 'LwrLip_R_MR_offset', 'MouthCorner_R_ML_offset', 'Nostril_offset', 'MouthCorner_R_MR_offset', 'Cheek_R_MR_offset', 'Cheek_L_MR_offset', 'LwrLip_R_ML_offset', 'LwrLip_L_MR_offset', 'UprLip_L_ML_offset', 'UprLip_L_MR_offset', 'MouthCorner_L_ML_offset', 'Chin_offset', 'Cheek_L_ML_offset', 'LwrLip_offset', 'NasoBulge_offset', 'Nostril_L_ML_offset', 'Nostril_L_MR_offset', 'MouthCorner_L_MR_offset', 'UprLip_R_ML_offset', 'MouthCorner_offset', 'Nostril_R_MR_offset', 'LwrLid_offset', 'Brow_offset', 'UprLip_offset', 'LwrLip_L_ML_offset', 'Cheek_offset', 'Cheek_R_ML_offset', 'Nostril_R_ML_offset']
		deformation_attrs = ['StickyLips', 'LipBack', 'NeckSlide', 'Forward', 'CheekBlowB', 'NeckMuscle', 'LipBlowT', 'ChinDepress', 'CheekBlowT', 'InflateOut', 'UprLipLR', 'Suck', 'LipBlowB', 'LwrLipLR', 'ChinTension', 'Lower', 'InflateIn', 'JawClench_L', 'StickinessSpeed', 'JawClench_R', 'NeckBlow', 'LipVolume', 'LipRoll', 'Stickiness', 'Squeeze', 'LipLock', 'LwrLidUpDn', 'Blink', 'NarrowWide', 'Flatten', 'NoseOpenClose', 'CornerRound']
		
		offset_cb = cmds.channelBox('offset_cb', speed = 0.1 ,fixedAttrList = offset_attrs, attrRegex='*Offset', attrColor = (1.0, 1.0, 1.0), attrBgColor = (0.0, 0.5, 0.5))
		deformation_cb = cmds.channelBox('deformation_cb', speed = 0.1 ,fixedAttrList = deformation_attrs)

		# add maya generated widgets to QtWidgets
		offset_cb_ptr = OpenMayaUI.MQtUtil.findControl(offset_cb)
		deformation_cb_ptr = OpenMayaUI.MQtUtil.findControl(deformation_cb)

		offset_cb_widget = QtCompat.wrapInstance(long(offset_cb_ptr), QtWidgets.QWidget)
		deformation_cb_widget = QtCompat.wrapInstance(long(deformation_cb_ptr), QtWidgets.QWidget)

		self.rig_manager_cb_offset.layout().addWidget(offset_cb_widget)
		self.rig_manager_cb_deformation.layout().addWidget(deformation_cb_widget)

		cmds.deleteUI(wnd)

	def hideChannelBoxAttributes(self):
		if self.HideAttributes.isChecked():
			self.rig_manager_cb_offset.setVisible(False)
			self.rig_manager_cb_deformation.setVisible(False)
		else:
			self.rig_manager_cb_offset.setVisible(True)
			self.rig_manager_cb_deformation.setVisible(True)

	def replaceButtons(self):
		try:
			key_list = self.ui_FACS_data_map.keys()
			key_list.remove("DefaultSize")

			current_size = self.facs_cntrs_grp.size()
			aspect_ration = (float(self.ui_FACS_data_map["DefaultSize"][1]) / float(self.ui_FACS_data_map["DefaultSize"][0])) / (float(current_size.height())/ float(current_size.width()))
			ratio_x = float(current_size.width()) / float(self.ui_FACS_data_map["DefaultSize"][0])
			ratio_y = float(current_size.height()) / float(self.ui_FACS_data_map["DefaultSize"][1])

			for btn in key_list:
				value_x = self.ui_FACS_data_map[btn][0] * ratio_x
				value_y = self.ui_FACS_data_map[btn][1] * ratio_y
				size_x = int(round(self.ui_FACS_data_map[btn][2] * aspect_ration))
				size_y = int(round(self.ui_FACS_data_map[btn][3] * aspect_ration))
				eval("self.%s.setGeometry(%d,%d,%d,%d)"%(btn, value_x, value_y, size_x, size_y))
			
			for btn in self.FACS_btns_map.keys():
				value_x = self.FACS_btns_map[btn][0] * ratio_x
				value_y = self.FACS_btns_map[btn][1] * ratio_y
				size_x = int(round(self.FACS_btns_map[btn][2] * ratio_x))
				size_y = int(round(self.FACS_btns_map[btn][3] * ratio_y))
				eval("self.%s.setGeometry(%d,%d,%d,%d)"%(btn, value_x, value_y, size_x, size_y))

		except:
			Logger.LOG("block #1")

		try:
			key_list = self.ui_Adj_data_map.keys()
			key_list.remove("DefaultSize")

			current_size = self.adj_cntrs_grp.size()
			aspect_ration = (float(self.ui_Adj_data_map["DefaultSize"][1]) / float(self.ui_Adj_data_map["DefaultSize"][0])) / (float(current_size.height())/ float(current_size.width()))
			ratio_x = float(current_size.width()) / float(self.ui_Adj_data_map["DefaultSize"][0])
			ratio_y = float(current_size.height()) / float(self.ui_Adj_data_map["DefaultSize"][1])

			for btn in key_list:
				value_x = (self.ui_Adj_data_map[btn][0] + 4) * ratio_x
				value_y = self.ui_Adj_data_map[btn][1] * ratio_y
				size_x = int(round(self.ui_Adj_data_map[btn][2] * aspect_ration))
				size_y = int(round(self.ui_Adj_data_map[btn][3] * aspect_ration))
				eval("self.%s.setGeometry(%d,%d,%d,%d)"%(btn, value_x, value_y, size_x, size_y))

			for btn in self.Adj_btns_map.keys():
				value_x = self.Adj_btns_map[btn][0] * ratio_x
				value_y = self.Adj_btns_map[btn][1] * ratio_y
				size_x = int(round(self.Adj_btns_map[btn][2] * ratio_x))
				size_y = int(round(self.Adj_btns_map[btn][3] * ratio_y))
				eval("self.%s.setGeometry(%d,%d,%d,%d)"%(btn, value_x, value_y, size_x, size_y))

		except Exception as e:
			Logger.LOG("block #2")

	def resizeEvent(self, event):
		self.replaceButtons()
		super(RigManager, self).resizeEvent(event)
	
	def showEvent(self, event):
		event.accept()
		self.replaceButtons()

	# ----------------------------- Anim Curves ------------------------- #
	@undo
	def addAnimCurvesAttributes(self):
		selection = cmds.ls(sl = True)
		if not selection:
			cmds.confirmDialog( title='Confirm', message='Select Head Mesh !')
			return
		else:
			selection = selection[0]

		root_joint = self.getSkeletonRoot(selection)
		shader_name = self.getShaderNode(selection)
		mask_attr_list = self.getShaderAttributes(shader_name)

		for attr in mask_attr_list:
			try:
				cmds.addAttr(root_joint, sn = "%s_mat"%attr, k = True, at = "double")
			except:
				print("%s Exists"%attr)
			
			try:
				cmds.connectAttr("%s.%s"%(shader_name, attr), "%s.%s_mat"%(root_joint, attr), f = True)
			except:
				print("Connection Of %s Faild"%attr)

	@undo
	def removeAnimCurvesAttributes(self):
		selection = cmds.ls(sl = True)
		if not selection:
			cmds.confirmDialog( title='Confirm', message='Select Head Mesh !')
			return
		else:
			selection = selection[0]
		
		root_joint = self.getSkeletonRoot(selection)
		shader_name = self.getShaderNode(selection)
		mask_attr_list = self.getShaderAttributes(shader_name)

		for attr in mask_attr_list:
			try:
				cmds.deleteAttr(root_joint, at = "%s_mat"%attr)
			except:
				pass

	def getSkeletonRoot(self, mesh = ""):
		# Search through the rootJoint's top most joint parent node
		history = cmds.listHistory(mesh) or []
		rootJoint = cmds.ls(history, type = "joint")
		if not rootJoint:
			cmds.error("Skeleton Not Found!")
		else:
			rootJoint = rootJoint[0]
		while (True):
			parent = cmds.listRelatives( rootJoint, parent = True, type = 'joint' )
			if not parent:
				break
			rootJoint = parent[0]
		return rootJoint

	def getShaderNode(self, mesh = ""):
		shading_group = cmds.listConnections(cmds.listRelatives(mesh, shapes = True)[0], type = "shadingEngine")[0]
		shader_name = (cmds.ls(cmds.listHistory(shading_group), type = "dx11Shader") or [""])[0]
		if not shader_name:
			cmds.error("SkinShader Not Found!")
		return shader_name

	def getShaderAttributes(self, node = "SkinShader"):
		attr_list = cmds.listAttr(node, ud = True, k = True)
		attr_list = filter(lambda attr: re.search("Mask\d", attr), attr_list)
		return attr_list

	# ------------------------------------------------------------------- #

	# ------------------------------------------------------------------- #

	def mirrorFunc(self, current_selection_list = [], forceLeftRight = False, forceUpDown = False):
		Logger.LOG("selection changed!")
		# self.Mirror_Left_Right.isChecked()
		# self.Mirror_Up_Down.isChecked()
		if not current_selection_list:
			return

		bMLR = forceLeftRight or self.Mirror_Left_Right.isChecked()
		bMUD = forceUpDown or self.Mirror_Up_Down.isChecked()

		mirror_list = []
		for sel in current_selection_list:
			split_list = sel.split(":")
			namespace = ""
			if len(split_list) > 1:
				namespace = split_list[0] + ":"
				cntr_name = split_list[1]
			else:
				cntr_name = split_list[0]

			# Mirror Left Right
			if bMLR: 
				if cntr_name in self.FACS_data_map["LeftRight"]:
					value = namespace + self.FACS_data_map["LeftRight"][cntr_name]
					if (value not in current_selection_list) and (value not in mirror_list):
						mirror_list.append(value)
				
				if cntr_name in self.FACS_data_map["RightLeft"]:
					value = namespace + self.FACS_data_map["RightLeft"][cntr_name]
					if (value not in current_selection_list) and (value not in mirror_list):
						mirror_list.append(value)

			# Mirror Up Down
			if bMUD:
				if cntr_name in self.FACS_data_map["UpDown"]:
					v = self.FACS_data_map["UpDown"][cntr_name]
					value = namespace + v
					if (value not in current_selection_list) and (value not in mirror_list):
						mirror_list.append(value)
					
					# Check Left Right
					if bMLR:
						if cntr_name in self.FACS_data_map["LeftRight"]:
							value2 = namespace + self.FACS_data_map["LeftRight"][v]
							if (value2 not in current_selection_list) and (value2 not in mirror_list):
								mirror_list.append(value2)
						
						if cntr_name in self.FACS_data_map["RightLeft"]:
							value2 = namespace + self.FACS_data_map["RightLeft"][v]
							if (value2 not in current_selection_list) and (value2 not in mirror_list):
								mirror_list.append(value2)
				
				if cntr_name in self.FACS_data_map["DownUp"]:
					v = self.FACS_data_map["DownUp"][cntr_name]
					value = namespace + v
					if (value not in current_selection_list) and (value not in mirror_list):
						mirror_list.append(value)
					
					# Check Left Right
					if bMLR:
						if cntr_name in self.FACS_data_map["LeftRight"]:
							value2 = namespace + self.FACS_data_map["LeftRight"][v]
							if (value2 not in current_selection_list) and (value2 not in mirror_list):
								mirror_list.append(value2)
						
						if cntr_name in self.FACS_data_map["RightLeft"]:
							value2 = namespace + self.FACS_data_map["RightLeft"][v]
							if (value2 not in current_selection_list) and (value2 not in mirror_list):
								mirror_list.append(value2)

			# Mirror Adj Left Right Up Down
			if bMLR: 
				if cntr_name in self.Adj_data_map["LeftRight"]:
					value = namespace + self.Adj_data_map["LeftRight"][cntr_name]
					if (value not in current_selection_list) and (value not in mirror_list):
						mirror_list.append(value)
				
				if cntr_name in self.Adj_data_map["RightLeft"]:
					value = namespace + self.Adj_data_map["RightLeft"][cntr_name]
					if (value not in current_selection_list) and (value not in mirror_list):
						mirror_list.append(value)


		return mirror_list
						
	def applyMirrorSelection(self,  *args):
		current_selection_list = cmds.ls(sl = True, type = "transform")
		mirror_list = self.mirrorFunc(current_selection_list)
		if not mirror_list:
			return
		for cntr in mirror_list:
			OpenMaya.MGlobal.selectByName(cntr)
		


def create():
	wnd = RigManager(dock = True)
	wnd.show(True)
	return wnd