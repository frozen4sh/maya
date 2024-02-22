import maya.cmds as mc
scriptVersion = 'v08'
scriptName = 'copyTiming'

'''
Copyright (c) <2020> <JesseOngPho>
jesseongpho@hotmail.com

DESCRIPTION:
Set keys on the children at the same frames as the master.

FEATURES:
- Work with multiple child selection 
- Work on selected curves in the graph editor
- Work on the current timeline
- Work on maya 2016, 2018, 2020, 2022 both Linux and Windows  (Did not try other version but it should work)

UPDATE 
2021/06/22: Made the script compatible with maya 2022

2020/11/02: Added right click option on Icon: KeyAll function = set a key on every keyframes of all selected objects.


HOW TO USE : 
1) Select Controller you want the keyframes to be copied
2) Then the children
3) Click the copyTiming icon

INSTALLATION:
To install, drag and drop the install.mel file onto the maya viewport
'''

def checkEmptySelection(myCtrlList):
    if not myCtrlList :
        mc.confirmDialog( title='Selection Error', message='The selection is empty. Please select object(s) and try again', button=['ok'], defaultButton='ok')
        mc.error('The selection is empty. Please select an object')
 
 
 
#=================GET FUNCTIONS=================#
#Get list of keyframes of an object on the timeline
def getKeyframeNumberList(myController,minValue,maxValue ):
    allKeys = (mc.keyframe(myController, time=( minValue , maxValue ), query=True, absolute=True, timeChange=True))
    if not allKeys:
        keyFrameList =[]
    else:
        keyFrameList =  set(allKeys)
    return keyFrameList
    
#Get difference of two lists 
def getListDifference(li1, li2): 
    return (list(set(li1) - set(li2))) 

#=================END GET FUNCTIONS=================#

#insert a key at all keyframe given in a list
def insertKeys(controller,keyFramesOfMaster):
    for keyFrame in keyFramesOfMaster:
        mc.setKeyframe(controller, insert=True, time=keyFrame,itt='auto', ott='auto')        
        
def organizeSelection(myControllers):
    #CURVE selection order working
    selectedCurveGE = mc.keyframe(q = True, selected = True, name = True) or []
    
    mySelection =[]
    
    #if only one object selected : works only on GE selection   
    if len(myControllers) == 1 :    
        if selectedCurveGE: 
            mySelection = selectedCurveGE    
    #if 2 or more objects selected :   
    else :  
        if selectedCurveGE:
            mySelection = selectedCurveGE
        else:
            mySelection = myControllers

    if  (len(mySelection)) <= 1:
        mc.confirmDialog( title='Selection Error', message='Selection is not correct, Please select at least 2 objects and try again', button=['ok'], defaultButton='ok')
        mc.error('Selection is not correct, Please select at least 2 objects.')
    
    return mySelection


def main():
    #GET MIN AND MAX OF TIMELINE
    minValue = mc.playbackOptions(q=1,min=1)
    maxValue = mc.playbackOptions(q=1,max=1)

    #keyframe tab of the master 
    keyFramesOfMaster = []

    myControllers = mc.ls(sl=True)
    checkEmptySelection(myControllers)
    mySelection = organizeSelection (myControllers)
    #print (mySelection)


    for controller in mySelection:
        #if it is the master
        if (controller == mySelection[0]):
            keyFramesOfMaster = getKeyframeNumberList(controller,minValue,maxValue )
            if not keyFramesOfMaster:
                mc.confirmDialog( title='Keyframe Error', message='The master object does not have any keys, please set at least one keyframe on the master Object and try again', button=['ok'], defaultButton='ok')
                mc.error('The master object does not have any keys, please set at least one keyframe on the master Object')
        
        #else they are slave
        else:
            #make a tab of keyframe of the slave 
            keyFramesOfSlave = getKeyframeNumberList(controller,minValue,maxValue )
            if not keyFramesOfSlave:
                mc.setKeyframe(controller)
            
            
            #insert keys
            insertKeys(controller,keyFramesOfMaster)
            #get All Slave keyframes after inserted keys 
            keyFramesOfSlave = getKeyframeNumberList(controller,minValue,maxValue )
            #see what frames to delete
            keyFrameToDelete = getListDifference (keyFramesOfSlave,keyFramesOfMaster )
            #delete the child unecessary frames
            for time in keyFrameToDelete:
                mc.cutKey( controller, time=(time,time),option="keys" )
            mc.warning('Success : %s timing was copied to %s' %(mySelection[0],controller))

#keyAll function 
def menuCommand1():
    #GET MIN AND MAX OF TIMELINE
    minValue = mc.playbackOptions(q=1,min=1)
    maxValue = mc.playbackOptions(q=1,max=1)

    myControllers = mc.ls(sl=True)
    checkEmptySelection(myControllers)
    keys = getKeyframeNumberList(myControllers,minValue,maxValue )
    insertKeys(myControllers,keys)
    mc.warning('Success : All selection have now keys at the same frames.' )