import maya.cmds as mc
scriptVersion = 'v09'
scriptName = 'locator'

'''
Copyright (c) <2022> <JesseOngPho>
jesseongpho@hotmail.com

DESCRIPTION : 
Create a locator to the location of the selected object.

FEATURES:
- Work with multiple selection 
- Work on Vertices / meshes / controllers  

- Work on maya 2018,2020, 2022 both Linux and Windows (Vertices option does not work on maya 2016 because of the point to poly constraint function)

UPDATE 
2022/06/04: 
- Changed the right click menu Layout 
- Added the zero group options

2021/12/02: 
-Change the algorithm from matrix to constraint+bakeresult. It solves the problem of controllers joints being controlled by follicles. 
-Speed Improvment
-Rename locators to selection name 

2021/06/22: 
- Script works on Vertices selection 
- Made the script compatible with maya 2022
- New right click menu seperators
- added the function to Constraint the selection to a newly created locator

2020/12/19: 
- Script works if the selection doens't have keys

HOW TO USE : 
1) select controller(s)
2) Click on the locator icon (right click to see option)

INSTALLATION:
To install, drag and drop the install.mel file onto the maya viewport
'''
def zeroOut(mySelect):
    tTab = ['tx', 'ty', 'tz']
    rTab = ['rx','ry','rz']
    
    try: 
        mc.setAttr('%s.%s' %(mySelect, tTab[0]), 0)
        mc.setAttr('%s.%s' %(mySelect, tTab[1]), 0)
        mc.setAttr('%s.%s' %(mySelect, tTab[2]), 0)
    except: 
        pass
    try: 
        mc.setAttr('%s.%s' %(mySelect, rTab[0]), 0)
        mc.setAttr('%s.%s' %(mySelect, rTab[1]), 0)
        mc.setAttr('%s.%s' %(mySelect, rTab[2]), 0)
    except: 
        pass    
 
#Function that avoid the duplicated name issue.
def generateNoDuplicateName(selection):
    i = 1
    locName='%s_loc_%i' %(selection, i )
    #Have to do the special character replacement for the vertex selection
    specialChars = "!#$%^&*().|[]" 
    for specialChar in specialChars: 
        locName = locName.replace(specialChar, '_')
    
    while ( mc.objExists (locName)):
        tempLocName, i = locName.rsplit('_',1)
        iter = int(i)+1 
        locName = '%s_%s' %(tempLocName, str(iter)) 
        #get out of loop not to block maya.
        if (iter == 100):
            mc.error('InfiniteLoop couldn\'t create the locator ')
    return locName
     
    
#bake result is faster in DG mode 
def UIOff():
    '''
    myEvaluation = mc.evaluationManager(mode=True, query=True)[0]
    if (myEvaluation!='off'):
        mc.evaluationManager(mode='off')
    '''
    mc.refresh(suspend=True)
    return 'myEvaluation'

def UIon(myEvaluation):
    #mc.evaluationManager(mode=myEvaluation)
    mc.refresh(suspend=False)   
    
#=================CHECK FUNCTIONS=================#
def checkEmptySelection():
    mySelec = mc.ls(sl=True,flatten=True)
    if not mySelec :
        mc.confirmDialog( title='Selection Error', message='The selection is empty. Please select object(s) and try again', button=['ok'], defaultButton='ok')
        mc.error('Selection error')
    return mySelec

def checkAttribute(oneObj):
    attrList = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']
    skipTranslate = []
    skipRotate = []  
    
    for attr in attrList:
        myAttributeName = '%s.%s' %(oneObj, attr)
        isLocked = mc.getAttr(myAttributeName,lock=True)
        isMute = mc.mute(myAttributeName,q=True)
        if (isLocked or isMute): 
            if (attr[0] == 't'):
                skipTranslate.append(attr[1])
            else: 
                skipRotate.append(attr[1])
    return skipTranslate, skipRotate
#=================END CHECK FUNCTIONS=================#


#=================GET FUNCTIONS=================#
def getKeyframeTab(myCtl):
    try: 
        keyFrameNumberList = list(set(mc.keyframe(myCtl, time=( ), query=True, absolute=True, timeChange=True)))
    except: 
        keyFrameNumberList =[]
    return keyFrameNumberList

def getFrameRange(myCtl):
    minValue = minValueTimeline = int(mc.playbackOptions(q=1,min=1))
    maxValue = maxValueTimeline = int(mc.playbackOptions(q=1,max=1))
    
    keyTab = getKeyframeTab(myCtl)
    if keyTab:
        minValue = min(keyTab)
        maxValue = max(keyTab)
        if minValue > minValueTimeline:
                minValue=minValueTimeline
        if maxValue < maxValueTimeline:
            maxValue=maxValueTimeline
    
    return (minValue,maxValue)
	
def getTimeline():
    minValue  = int(mc.playbackOptions(q=1,min=1))
    maxValue  = int(mc.playbackOptions(q=1,max=1))
    return (minValue,maxValue)	

#=================END GET FUNCTIONS=================#

#=================BAKING  FUNCTIONS=================#   
#fast every frame bake of a list on a specific time range
def bakeEveryFrame(toBake, min, max, ctsList):
    myEvaluation = UIOff()
    try: 
        mc.bakeResults(toBake,
               simulation=True,
               disableImplicitControl=False,
               preserveOutsideKeys =True,
               minimizeRotation =True,
               time=(min,max),
               sampleBy=1 )
    except: 
    
        UIon(myEvaluation)
        mc.delete(ctsList)
        mc.error ('ERROR during the Bake. Certainly a locator naming problem')
       
    UIon(myEvaluation)
    mc.delete(ctsList)


#fast every KEYframe bake of a list on a specific time range
def bakeKeyFrameTab(toBake, min, max, ctsList):

    myEvaluation = UIOff()
    try: 
        mc.bakeResults(toBake,
                   simulation=True,
                   disableImplicitControl=False,
                   preserveOutsideKeys =True,
                   minimizeRotation =True,
                   time=(min,max),
                   sparseAnimCurveBake =True,
                   smart  =True,
                   sampleBy=1 )
    except: 
        UIon(myEvaluation)
        mc.delete(ctsList)
        mc.error ('ERROR during the Bake')
        
    UIon(myEvaluation)
    mc.delete(ctsList)
#=================END BAKING FUNCTIONS=================#

#=================CREATE FUNCTIONS=================#    
#Create locator with same name as the selection.    
def createLocator(selection):
    locName=generateNoDuplicateName(selection)
    myLoc = mc.spaceLocator(name=locName)[0]
    if (locName!=myLoc):
        myLoc = mc.rename(myLoc,locName)
    
    mc.setAttr('%s.localScale' %myLoc, 2,2,2)
    return myLoc


#Create the parent group jop_locator and the collection.    
def createLocGrp ():
    grpName ='jop_locator_grp'
    if not mc.objExists (grpName):
        mc.group(name=grpName, empty=True)
    
    collecName ='jop_locator_collec_#'
    myCollec = mc.group(name=collecName, parent = grpName, empty=True)
    return myCollec  
    
#Create the parent group jop_locator and the collection to Selection  
def createZeroGroup(selection):
    zero_group = mc.duplicate(selection, po=True, n=selection+'_zero_grp')[0]
    mc.parent(selection, zero_group)
    return zero_group
#=================END CREATE FUNCTIONS=================#    

#PointOnPoly only works with Object which has UVs so need to check that the object has UVs
def uvCheck(vertex): 
    uvCoord= mc.polyEvaluate(vertex,uvcoord=True)
    if not (uvCoord):
        mc.confirmDialog( title='UVerror', message="The object containing : "+ vertex +" doesn't have UV. \nIn the menu bar, try UV > Automatic and run the script again.", button=['ok'], defaultButton='ok')
        mc.error('UV error')
        
#=================PARENT CONSTRAINTS FUNCTIONS=================#
#constraint new locators list to selection
#target list is given for World space driver, need to check if you can constraint all attributes the locator to the selection (locked or mute ) 
# - Check if it is a vertex.

def setlocType(selection, zeroGrp = False):
    myloc = createLocator(selection)
    #print (myloc)
    if zeroGrp: 
        #print('IN')
        myZeroGrp = createZeroGroup(myloc)
        result = myZeroGrp
    else:    
        result = myloc 
    return result

def parentConstraintLocToSel(selectionList, zeroGrp = False):
    #print (selectionList)
    ctsList = []   
    locList = []
    
    
    for i in range(0, len(selectionList)): 
        #if it is a vertex
        if (mc.filterExpand(selectionList[i],sm=31)):
            uvCheck(selectionList[i])
            
            locList.append(setlocType(selectionList[i],zeroGrp))
            
            mc.select(selectionList[i])
            ctsList.append (mc.pointOnPolyConstraint(selectionList[i],locList[i],mo=False)[0])

        #if NOT a vertex
        else:
            locList.append(setlocType(selectionList[i],zeroGrp))
            ctsList.append (mc.parentConstraint(selectionList[i],locList[i],mo=False)[0])
    
    
    return locList, ctsList 
    
#Check what attribute we can constraint to and then constraint the selectionList (driver) to targetList (driven )     
def parentToCtl (selectionList, targetList):
    for i in range(0, len(selectionList)): 
        skipTranslate, skipRotate = checkAttribute(targetList[i])
        mc.parentConstraint(selectionList[i],targetList[i],mo=False, skipTranslate=skipTranslate, skipRotate=skipRotate)


#=================END PARENT CONSTRAINTS FUNCTIONS=================#

#============================================================================ 
#snap Locator(s) to the current selected object(s) at current time
def main():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    mc.delete(ctsList)
    mc.select(mySelec)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))


#========================TIME SLIDER===============================
#SNAP Locator(s) to the current selected object(s) on the respective keyframes
def timeSliderKeyframes():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    minTime, maxTime = getTimeline()
    bakeKeyFrameTab(locList, minTime, maxTime, ctsList)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
	
#SNAP locator(s) every frame  
def timeSliderEveryFrames():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    minTime, maxTime = getTimeline()
    bakeEveryFrame(locList, minTime, maxTime, ctsList)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)

#CONSTRAINT : Locators Driver, selection driven
def timeSliderWorldSpaceDriver(): 

    mySelec = checkEmptySelection()
    if (mc.filterExpand(mySelec,sm=31)):
        mc.confirmDialog( title='Selection error', message="World space Driver doesn't work with vertices. Please remove the vertices from selection and try again.", button=['ok'], defaultButton='ok')
        return
        
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    minTime, maxTime = getTimeline()
    bakeEveryFrame(locList, minTime, maxTime, ctsList)
    
    parentToCtl(locList, mySelec)
    
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
   	
	
#==========================All Keys=======================================
#SNAP Locator(s) to the current selected object(s) on the respective keyframes
def allKeysKeyframes():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    minTime, maxTime = getFrameRange(mySelec)
    bakeKeyFrameTab(locList, minTime, maxTime, ctsList)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
	
#SNAP locator(s) every frame  
def allKeysEveryFrames():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    minTime, maxTime = getFrameRange(mySelec)
    bakeEveryFrame(locList, minTime, maxTime, ctsList)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)

def allKeysWorldSpaceDriver():
    mySelec = checkEmptySelection()
    if (mc.filterExpand(mySelec,sm=31)):
        mc.confirmDialog( title='Selection error', message="World space Driver doesn't work with vertices. Please remove the vertices from selection and try again.", button=['ok'], defaultButton='ok')
        return
        
    myCollec = createLocGrp ()
    locList, ctsList = parentConstraintLocToSel(mySelec)
    mc.parent (locList, myCollec)
    minTime, maxTime = getFrameRange(mySelec)
    bakeEveryFrame(locList, minTime, maxTime, ctsList)
    
    parentToCtl(locList, mySelec)
    
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
   		
	
#========================CONSTRAINTS==========================================	


#Create locators at selection, create zero Group.
def zeroGrpOnCurrentFrame():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    zeroGrpList, ctsList = parentConstraintLocToSel(mySelec, True)
    mc.delete(ctsList)
    mc.parent(zeroGrpList, myCollec)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
        
#Contraint a group at the selection, set a Locator under it, zeroOut the locator
def zeroGrpConstraint():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    zeroGrpList, ctsList = parentConstraintLocToSel(mySelec,True)
    mc.parent(zeroGrpList, myCollec)
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
            
#BAKE a group at the selection, set a Locator under it, zeroOut the locator
def zeroGrpBake():
    mySelec = checkEmptySelection()
    myCollec = createLocGrp ()
    zeroGrpList, ctsList = parentConstraintLocToSel(mySelec, True)
    mc.parent (zeroGrpList, myCollec)
    minTime, maxTime = getTimeline()
    bakeEveryFrame(zeroGrpList, minTime, maxTime, ctsList)
    
    mc.warning ('Success : %s locators created ' %(str(len(mySelec))))
    mc.select(mySelec)
		
	
def noAction():    
    mc.confirmDialog( title='No Action', message="This button doesn't do anything, it is just to make the menu more readable =)", button=['ok'], defaultButton='ok')
    return
    