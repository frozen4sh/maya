import maya.cmds as mc

scriptVersion = 'v10'
scriptName = 'lockToWorld'

'''
Copyright (c) <2020> <JesseOngPho>
jesseongpho@hotmail.com

DESCRIPTION : 
Lock 1 or multiple objects to the world. Really useful to fix feet sliding. 

FEATURES:
- Snap the selected controller to the world for the selected amount of frames 
- Work with multiple selection 
- Work with selected attributes on the channel box (Translation and Rotation only)
- Work on controllers that have frozen transformation
- Work on maya 2016,2018,2020, 2022 both Linux and Windows (Did not try other version but it should work)

UPDATE 
2021/11/28: 
-Change the algorithm from matrix to constraint+bakeresult. It solves the problem of controllers joints being controlled by follicles 
-Added error to muted and locked attributes selection.

2021/06/22: Made the script compatible with maya 2022

HOW TO USE : 
1) Get on the frame where the controller should start to be snapped
2) Click on the Start button
3) Get to the frame where the controller should stop to be snapped 
4) Click on the End button
5) Select the controller(s)
6) Click on Lock to World button

INSTALLATION:
To install, drag and drop the install.mel file onto the maya viewport
'''
#=================GET FUNCTIONS=================#

#return a list of attribute : ex = ['tx','ty','rx']. Raw data from Channel Box
def getSelectedChannelBoxAttributes(): 
    attributes = ['tx','ty','tz','rx','ry','rz']
    selectedChannelBoxAttr =  ([] + (mc.channelBox("mainChannelBox", selectedMainAttributes=True, q=True) or []))
    #if some attribute are selected in channel box
    if not selectedChannelBoxAttr: 
        selectedChannelBoxAttr=attributes
    #print (selectedChannelBoxAttr)
    return selectedChannelBoxAttr

#return 2 lists in the format : ['x', 'y', 'z'] describing the axis that didn't get selected in channel box
def getSkippedAttributes(selectedCBAttr):
    skipTranslation = ['x','y','z']
    skipRotate = ['x','y','z']  
    for i in selectedCBAttr :
        #remove selected Attributes from the skip lists
        if (i[0] =='t' and len(i)==2):
            if i[1] in skipTranslation: 
                skipTranslation.remove(i[1])
        elif i[0] =='r' and len(i)==2:
            if i[1] in skipRotate: 
                skipRotate.remove(i[1])
        else: 
            mc.confirmDialog( title='Selected Attribute Error', message='The script only supports translation and rotation attributes. \nPlease select the good attributes in the channel box and try again', button=['ok'], defaultButton='ok')
            mc.error('Sorry, the script only support translation and rotation attributes.')        

    return skipTranslation,skipRotate

#=================END GET FUNCTIONS=================#

#=================CHECK FUNCTIONS=================#
def checkEmptySelection(myCtrlList):
    if not myCtrlList :
        mc.confirmDialog( title='Selection Error', message='The selection is empty. Please select object(s) and try again', button=['ok'], defaultButton='ok')
        mc.error('The selection is empty. Please select an object')

#Check if attributes are locked or muted
def checkAttributes(obj, selectedChannelBoxAttr): 
    for o in obj: 
        for attr in selectedChannelBoxAttr: 
            myAttributeName = '%s.%s' %(o, attr)
            isLock = mc.getAttr(myAttributeName,lock=True)
            if isLock : 
                mc.confirmDialog( title='Selected Attribute Error', message='%s attribute is locked. \nPlease select unlocked attributes in the ChannelBox and try again.' %myAttributeName, button=['ok'], defaultButton='ok')
                mc.error('Some of the selected attributes are locked. Please unlock and try again.')     
           
            isMute = mc.mute(myAttributeName,q=True)
            if isMute :                 
                mc.confirmDialog( title='Selected Attribute Error', message='%s attribute is muted. \nPlease unmute and try again.' %myAttributeName, button=['ok'], defaultButton='ok')
                mc.error('Some of the selected attributes are muted. Please unmute and try again.')     
#=================END CHECK FUNCTIONS=================#          
 
#bake result is faster in DG mode 
def UIOff():
    myEvaluation = mc.evaluationManager(mode=True, query=True)[0]
    if (myEvaluation!='off'):
        mc.evaluationManager(mode='off')
    mc.refresh(suspend=True)
    return myEvaluation
    
def UIon(myEvaluation):
    mc.evaluationManager(mode=myEvaluation)
    mc.refresh(suspend=False)

#create locator, give him a name.    
def createLocator():
    locName = 'jop_worldSpace_tmpLoc_#'
    myLoc = mc.spaceLocator(name=locName)[0]
    mc.setAttr('%s.localScale' %myLoc, 2,2,2)
    return myLoc

#constraint a target list to selection, if no target constraint new locators to selection
def parentConstraintToSel(selectionList,maintainOffsetValue,targetList=[],skipTranslate='none',skipRotate='none'):
    #print(skipTranslate,skipRotate)
    ctsList = []   
    locList = []
    
    for i in range(0, len(selectionList)): 
        if not targetList: 
            locList.append(createLocator())
            ctsList.append(mc.parentConstraint(selectionList[i], locList[i], maintainOffset=maintainOffsetValue, skipTranslate=skipTranslate,skipRotate=skipRotate)[0])
        else:    
            ctsList.append(mc.parentConstraint(selectionList[i], targetList[i], maintainOffset=maintainOffsetValue, skipTranslate=skipTranslate,skipRotate=skipRotate)[0])
    if locList: 
        targetList = locList
    return targetList, ctsList

#fast bake of a list on a specific time range
def bakeEveryFrame(toBake, minTime,maxTime, ctsList, attributeTab):
    myEvaluation = UIOff()
    try: 
        mc.bakeResults(toBake,
                       simulation=True,
                       attribute =  attributeTab,
                       disableImplicitControl=False,
                       preserveOutsideKeys =True,
                       time=(minTime,maxTime),
                       sampleBy=1 )
    except: 
        UIon(myEvaluation)
        mc.delete(ctsList)
        mc.error ('ERROR during the Bake')
        
    UIon(myEvaluation)


def lockToWorld(min,max ):    
    #User input 
    attributeToKeyList = getSelectedChannelBoxAttributes()
    mySelection = mc.ls(sl=True)
    
    #check inputs 
    checkEmptySelection(mySelection)
    checkAttributes(mySelection,attributeToKeyList)
    
    skipTranslate,skipRotate= getSkippedAttributes(attributeToKeyList)
    
    mc.currentTime (min)
    #empty loc constraint
    tempLocList,ctsList = parentConstraintToSel(mySelection,False)
    mc.delete(ctsList)
    #constraint ctl to locators
    targetList,ctsList = parentConstraintToSel(tempLocList,False,mySelection, skipTranslate,skipRotate)
    
    bakeEveryFrame(targetList, min,max,ctsList, attributeToKeyList )
    
    mc.delete(ctsList)
    mc.delete(tempLocList)

    mc.select(mySelection)
    
    
class MyLockWorldWindowClass (object):
    def __init__(self):
        self.window = scriptName + '_' + scriptVersion
        self.title = scriptName
        self.size = (184 , 105)
        self.minValue = mc.playbackOptions(q=1,min=1)
        self.maxValue = mc.playbackOptions(q=1,max=1)
        self.startString = 'Start \n'
        self.endString = 'End \n'
        self.buttonHeight = 50
        self.buttonWidth = 180
        self.buttonSmallWidth = 90
        self.backgroundColor = [.8,0.6,.1] 
        
    def create (self):
        #Makes sure we close previous window
        if mc.window (self.window, exists = True ):
            mc.deleteUI (self.window, window = True)
        self.window = mc.window (self.window, title = self.title , widthHeight = self.size,sizeable=False)
        
        #master Layouts
        myMasterLayout = mc.columnLayout()
        #horizontal layout
        myRowLayout = mc.rowColumnLayout(numberOfColumns =2)
        
        #button
        startButton = mc.button(label =self.startString+str(self.minValue), width = self.buttonSmallWidth, height= self.buttonHeight , command = lambda x : self.updateStartButton(startButton))
        endButton = mc.button(label =self.endString+str(self.maxValue), width = self.buttonSmallWidth, height= self.buttonHeight ,command =lambda x: self.updateEndButton(endButton))
        
        mc.setParent(myMasterLayout)
        mySecondLayout = mc.columnLayout()
        
        mc.button(label ='Lock to World', command= lambda x: lockToWorld(self.minValue,self.maxValue), width = self.buttonWidth, height= self.buttonHeight ,backgroundColor=self.backgroundColor  )

        mc.showWindow ()
    
    #Everytime the user click on start or end, it updates the string on the button and set new range    
    def updateStartButton(self, startButton):
        self.minValue = mc.currentTime(q=True)
        mc.button(startButton, e=True, label = self.startString + str(self.minValue ))
    def updateEndButton (self, endButton):
        self.maxValue = mc.currentTime(q=True)
        mc.button(endButton, e=True, label = self.endString + str(self.maxValue ))
       
def main():
    lockWorldWindow = MyLockWorldWindowClass()
    lockWorldWindow.create()