import maya.cmds as mc

scriptVersion = 'v04'
scriptName = 'followCam'

'''
Copyright (c) <2020> <JesseOngPho>
jesseongpho@hotmail.com

DESCRIPTION:
Create a camera that follows the selected controller.

FEATURES:
- Work on the focus window
- Work on locked attributes camera
- Clean outliner
- Have the option to omit some attributes when constrain (Right click on the icon)
- Work on maya 2016, 2018, 2020 both Linux and Windows  (Did not try other version but it should work)

UPDATE
2021/06/22: Made the script compatible with maya 2022

2020/11/12: New naming for created camera. All new cameras are under one node. Naming is consistent and easy to delete. 

HOW TO USE : 
1) Select Controller you want the camera to follow
2) Click on the followCam icon (Right Click to have options). 

INSTALLATION:
To install, drag and drop the install.mel file onto the maya viewport
'''
def checkSelection(myCtrlList):
    if not myCtrlList :
        mc.error('The selection is empty. Please select an object.')
    if len(myCtrlList) >1:
        mc.error('Too many objects selected. Please select only one object.')

def getCurrentCam(): 
    currentPanel = mc.getPanel(withFocus = True) 
    #print (currentPanel)
    if mc.getPanel(typeOf=currentPanel) != 'modelPanel':
        mc.confirmDialog( title='Camera Viewport Error', message='Please Select a camera viewport and try again', button=['ok'], defaultButton='ok')
        mc.error('Please Select a camera viewport.')     
    camShape = mc.modelEditor(currentPanel, query=True, camera=True)
    return camShape 
    
#create new cam from the current Window and look thru it in viewport 
def createDuplicateCamera():
    cameraName = 'jop_camera'
    #Duplicated camera Name is different if the current viewport is already a followCam
    if cameraName not in getCurrentCam():
        newCam = mc.duplicate(getCurrentCam(), name=cameraName+'_#')[0]
    else:
        newCam = mc.duplicate(getCurrentCam())[0]
        
    axis = ['X', 'Y', 'Z']
    attrs = ['translate', 'rotate']

    #unlock translate and rotate first then individual attribute (Studio rigs are sometimes locked twice)
    for attr in attrs:
        mc.setAttr(newCam+'.'+attr, lock=0)
        for ax in axis:
                mc.setAttr(newCam+'.'+attr+ax, lock=0)
            
            
    if (mc.listRelatives(newCam, parent=True)):
        mc.parent(newCam, world=True)
    mc.lookThru( newCam )

    return newCam
    
def createCamera():


    myMast = mc.ls(sl=True)
    checkSelection(myMast)
    
    
    newCam = createDuplicateCamera()
    newCamGroup = mc.duplicate(newCam, po=True, n='jop_camera_cts_#')
    mc.parent(newCam, newCamGroup)
    
    
    bigGroupName = 'jop_camera_grp'
    if not mc.objExists(bigGroupName):
        mc.group( em=True, name=bigGroupName)
    
    
    
    mc.parent(newCamGroup, bigGroupName)
    mc.lookThru( newCam )
    return myMast, newCamGroup
    
    
def main():
    myMast, newCamGroup = createCamera()
    parConst = mc.parentConstraint(myMast,newCamGroup,mo=True)

def menuCommand1():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True,skipTranslate=['x','y','z'])
    
def menuCommand2():
    myMast, newCamGroup = createCamera()
    mc.pointConstraint(myMast,newCamGroup,mo=True)
    
def menuCommand3():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True, skipTranslate='x')
    
def menuCommand4():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True, skipTranslate='y')
    
def menuCommand5():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True, skipTranslate='z')
    
def menuCommand6():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True, skipRotate='x')
    
def menuCommand7():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True, skipRotate='y')
    
def menuCommand8():
    myMast, newCamGroup = createCamera()
    mc.parentConstraint(myMast,newCamGroup,mo=True, skipRotate='z')
