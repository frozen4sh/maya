import maya.cmds as mc
scriptVersion = 'v07'
scriptName = 'baker'

'''
Copyright (c) <2022> <JesseOngPho>
jesseongpho@hotmail.com


DESCRIPTION : 
A fast bake script that execute in only one click : fast bake of the selection , remove constraints, remove them from animation layers if they belong to one.
If you use temporary controller to quickly tweak animations (check out my Locator scripts), this script is great to bake back your animation to the original controllers in one click.  
After retiming, tweaking keys, you have a messy timeline:  try baking it on 1s, 2s or 4s with only two clicks. 

It can be really easy to get lost in big scene with tons of constraints, the Scene Constraints Baker will help you clearly see in a UI all the constraints in your scene. 
Constraints and pipeline usually don't get along well, avoid kick backs from next departments by making sure your scene is clean and without constraints before publishing.
Work on all the scene constraints that are not referenced so make sure your rigs are referenced before using script, otherwise the Bake All will bake all your rig constraints as well.

FEATURES:
All the functions work only on the current time slider range. 
- Bake on 1's / Bake on 2's / Bake on 4's: 
    - Work with multiple selection 
    - Automatically remove any constraint(s) and animLayer(s) attached to the selection. 
    - If anim layer contains multiple objects, it will only remove the selected object from the layer and not delete the animation layer.

- Scene Constraints Baker : 
    - Scroll bar on the list 
    - List all non referenced constraints in alphabetic order. 
    - Select the constraint in the UI will select the constraint in the scene. 
    - Can select multiple constraints.
    - Have the option to bake selected constraint(s) or bake all the constraints in the UI. 

- Merge all AnimLayer: 
    - Only on time slider range so it can be faster than the maya merge layer function.

- Work on maya 2016,2018,2020 both Linux and Windows (Did not try other version but it should work)

UPDATE: 
2022-07:
Fix error on merging layers (several objects in anim layer) 
Added an error for the Merge all layer with lock attributes

HOW TO USE : 
1) select object(s)
2) Click on the Baker icon (right click to see option)

INSTALLATION:
To install, drag and drop the install.mel file onto the maya viewport
'''
#=================CHECK FUNCTIONS=================#
def checkEmptySelection():
    mySelec = mc.ls(sl=True)
    if not mySelec :
        errorEmptySeletion()
    return mySelec

#Check if layer and children layer are empty to be able to delete them
def checkEmptyAnimLayerAllTheWay(layer):
    result = 1
    
    #if this layer has attributes, return false
    attributes = mc.animLayer(layer, q=True, attribute=True)
    if attributes:
        return 0
    
    #if this layer has children, then we go through them and do the same check
    layerChildren = mc.animLayer(layer, q=True, children=True)
    if layerChildren:
        for childLayer in layerChildren:
            if (not checkEmptyAnimLayerAllTheWay(childLayer)):
                return 0
    return result
 

#=================END CHECK FUNCTIONS=================#

#=================ERROR FUNCTIONS=================#   
def errorEmptySeletion():
        mc.confirmDialog( title='Selection Error', message='The selection is empty. Please select object(s) and try again', button=['ok'], defaultButton='ok')
        mc.error('Selection error')
def errorNoConstraintsInScene():
    mc.confirmDialog( title='Constraint ERROR', message='No constraints in scene', button=['ok'], defaultButton='ok')
    mc.error('No constraint in scene')        

def errorNoConstraintsSelected():
    mc.confirmDialog( title='Constraint ERROR', message='No constraints selected in the UI', button=['ok'], defaultButton='ok')
    mc.error('No constraints selected in the UI')


def errorAnimLayerReference():    
    mc.confirmDialog( title='Delete layers ERROR', message='Cannot delete all anim layers. Please check that references are all loaded.', button=['ok'], defaultButton='ok')
    mc.error("Delete layers error")
    
def errorNoAnimLayer():       
    mc.confirmDialog( title='Anim Layer Selection ERROR', message='No animation Layers in the scene', button=['ok'], defaultButton='ok')
    mc.error("No animation Layers in the scene")

def errorObjectAnimLayer(anim_layer):       
    mc.confirmDialog( title='Objects in anim layer ERROR', message='Cannot detect objects in anim layer. You might need to delete manually layer named: ' + anim_layer, button=['ok'], defaultButton='ok')
    mc.error("Cannot detect objects in anim layer")

def errorDrivenObject(cts):    
    mc.confirmDialog( title='Driven object ERROR', message='Cannot find driven object for : ' + cts +'. Make sure all the references are loaded.', button=['ok'], defaultButton='ok')          
    mc.error('Cannot find driven object for : ' + cts)

def errorLayerMerge():    
    mc.confirmDialog( title='Merge Layer ERROR', message='Couldn\'t merge the aniamtion layer(s) properly. Check if Channel Box attributes have been locked after AnimLayer creation. Please unlock and try again', button=['ok'], defaultButton='ok')          
    mc.error('Merge Layer ERROR')   
#=================END ERROR FUNCTIONS=================#      
 
#=================VIEWPORT FUNCTIONS=================#
def UIOff():    
    '''
    #bake result is faster in DG mode 
    myEvaluation = mc.evaluationManager(mode=True, query=True)[0]
    if (myEvaluation!='off'):
        mc.evaluationManager(mode='off')
    '''
    mc.refresh(suspend=True)
    return 'myEvaluation'
    
def UIon(myEvaluation):
    #mc.evaluationManager(mode=myEvaluation)
    mc.refresh(suspend=False)
#=================END VIEWPORT FUNCTIONS=================#


#=================GET FUNCTIONS=================#
def getTimeline():
    minValue = minValueTimeline = int(mc.playbackOptions(q=1,min=1))
    maxValue = maxValueTimeline = int(mc.playbackOptions(q=1,max=1))
    return (minValue,maxValue)	

def getAllConstraints(): 
    allSceneCts = mc.ls(type="constraint")
    return allSceneCts    

#Return the constraint if the target object is mySel    
def getTargetConstraint (mySel):
    myCtsList = (mc.listConnections(mySel, connections=True, type='constraint'))  
    myConst = ''
    if  myCtsList:
        for i in myCtsList:
            if (".parentInverseMatrix" in i):
                myConst = (mc.listConnections(i))  
    return myConst
#=================END GET FUNCTIONS=================#
    
#=================BAKE FUNCTIONS=================#
def bakeEveryFrame(toBake, minTime,maxTime,sample): 
    myEvaluation = UIOff()
    try: 
        mc.bakeResults(toBake,
                       simulation=True,
                       disableImplicitControl=False,
                       preserveOutsideKeys =True,
                       time=(minTime,maxTime),
                       sampleBy=sample , 
                       #resolveWithoutLayer='AnimLayer1'
                       #bakeOnOverrideLayer=True
                       )
    except: 
        UIon(myEvaluation)
        mc.error ('ERROR during the Bake')
        
    UIon(myEvaluation)
    
def bakeCtlFromConstraints(textScrollList): 
    ctsList = mc.textScrollList(textScrollList, q=True,selectItem=True)
    if ctsList:
        slave=[]
        for cts in ctsList: 
            attributeList = mc.listConnections(cts,source=True, plugs=True)
            #If the constraint has a slave
            if  attributeList:
                try :
                    slaveAttribute = [s for s in attributeList if ".parentInverseMatrix" in s]
                    slave.append(slaveAttribute[0].split('.')[0])
                except: 
                    errorDrivenObject(cts)
            
        minValue,maxValue = getTimeline()
        bakeEveryFrame(slave, minValue,maxValue,1)
        mc.delete(ctsList) 
        updateTextScrollList(textScrollList)
        print ('%s constraint(s) deleted.' %ctsList)
    else: 
        errorNoConstraintsSelected()
               
def bakeAll(textScrollList):
    updateTextScrollList(textScrollList)
    select = mc.textScrollList(textScrollList, q=True, allItems=True)
    mc.textScrollList(textScrollList, e=True, selectItem= select)
    bakeCtlFromConstraints(textScrollList)
    mc.deleteUI('constraintsBakerWindow' , window=True)    
#=================END BAKE FUNCTIONS=================#


#================= ANIM LAYERS FUNCTIONS=================#

#select all of the objects in the currently selected animation layers
def selectObjectsFromLayers(anim_layers):
    # empty list to hold objects to select
    objects = []

    for anim_layer in anim_layers:
        # return all keyed attributes in animation layer
        anim_layer_attrs = mc.animLayer(anim_layer, query=True, attribute=True)
        if anim_layer_attrs:
            # split attributes and return only the first part - the node - and add to objects list
            for attr in anim_layer_attrs:
                obj = attr.split('.')[0]
                objects.append(obj)
        else: 
            errorObjectAnimLayer(anim_layer)
    mc.select(objects)
    
    return list(set(objects))

#Get all layers except the BaseAnimation
def getAllLayers():
    rootLayer = mc.animLayer(q=True, r=True)
    if rootLayer:
        def search(layer, depth=0):
            children = mc.animLayer(layer, q=True, c=True)
            if children:
                for child in children:
                    layers.append(child)
                    search(child, depth + 1)

        layers = []
        search(rootLayer)
        if layers:
            return layers
    return

    
def removeFromAnimLayer(mySelec):
    #get all the anim layers the current selection is in
    for selection in mySelec: 
        mc.select(selection) 
        affectedLayer = mc.animLayer(q=True, affectedLayers= True)
        
        if (affectedLayer):
            #remove the baseAnimationlayer
            rootLayer = mc.animLayer(q=True, r= True)
            affectedLayer.remove(rootLayer)
            
            #remove object from anim layer
            list =  (mc.listAttr( selection,keyable =True ))
            for i in range(0,len(list)) : 
            
                list[i] = selection +'.'+ list[i]
                
            #lockedAttributes
            lockList =  (mc.listAttr( selection,locked =True, keyable=True ))  
            if (lockList):
                for i in range(0,len(lockList)) : 
                    lockList[i] = selection +'.'+ lockList[i]
                    list.remove(lockList[i] )
                
                
            for i in affectedLayer:
                mc.animLayer(i, e=True, removeAttribute= list)
            
            deleteEmptyLayers()
            affectedLayer2 = mc.animLayer(q=True, affectedLayers= True)
            if (affectedLayer2):  
                errorLayerMerge()
            else: 
                print('%s animation layer(s) merged.' %(selection) )
        
        else:
            print('%s does not belong to any animation layer.' %selection )

#================= END ANIM LAYERS FUNCTIONS=================#

#=================DELETE FUNCTIONS=================#
def deleteEmptyLayers():
    #Delete empty anim layers
    allLayers = getAllLayers()
            
    layerToDelete = []
    layerToKeep = [] 

    if allLayers:
        for layer in allLayers: 
            isEmpty =  checkEmptyAnimLayerAllTheWay(layer)
            if isEmpty:
                layerToDelete.append(layer)
            else: 
                layerToKeep.append(layer)

    if layerToDelete:
        print('%s layer(s) deleted' %layerToDelete)
        mc.delete(layerToDelete)

#=================END DELETE FUNCTIONS=================#

#=================UI FUNCTIONS=================#
def createWindow(constraintList): 
    constraintsBakerWindow = 'constraintsBakerWindow'
    if mc.window (constraintsBakerWindow, exists = True ):
        mc.deleteUI (constraintsBakerWindow, window = True)
    myWindow = mc.window(constraintsBakerWindow,title = 'Constraints Baker')
    
    form = mc.formLayout(width=280)
    
    list = mc.textScrollList( append=constraintList , allowMultiSelection=True)
    mc.textScrollList(list, e=True, selectCommand = lambda:  selectItemInList(list) )
    
    b1 = mc.button(l='Bake All', c=lambda x: mc.layoutDialog(dismiss=bakeAll(list)), height=30,backgroundColor = [.8,0.6,.1] )
    b2 = mc.button(l='Bake Selection', c=lambda x: mc.layoutDialog(dismiss=bakeCtlFromConstraints(list)), height=30 ) 
    b3 = mc.button(l='Cancel', c='mc.deleteUI(\"' + constraintsBakerWindow + '\", window=True)', height=30) 
    
    spacer = 2
    top = 2
    edge = 2
    bottom = 35
    
    mc.formLayout(form, edit=True,
    				attachForm=[(b1, 'bottom', edge), (b2, 'bottom', edge),(b1, 'left', edge),(b3, 'right', edge), (b3, 'bottom', edge),(list, 'top', edge),(list, 'right', edge),(list, 'left', edge),(list, 'bottom', bottom)],
    				attachNone=[],
    				attachControl=[],
    				attachPosition=[(b1, 'right',1, 33), (b2, 'left', 1, 33), (b2, 'right', 1, 66), (b3, 'left', 1, 66)])

    
    mc.showWindow(myWindow)

def selectItemInList(textScrollList):
    selection = mc.textScrollList( textScrollList,q=True,selectItem=True)
    for i in selection: 
        if not mc.objExists(i):
            selection.remove(i)
            updateTextScrollList(textScrollList)
    mc.select(selection)
             
def updateTextScrollList(textScrollList):
    allSceneCts = getAllConstraints()
    #delete duplicates
    constraintList = list(set(keep_non_referenced(allSceneCts))) 
    if constraintList:
        constraintList.sort()
    mc.textScrollList(textScrollList, e=True, removeAll = True )
    mc.textScrollList(textScrollList, e=True, append = constraintList)

    return textScrollList
#=================END UI FUNCTIONS=================#

#Only return objects that are not referenced
def keep_non_referenced(src):
    nonRefCts=[]
    if src:
        for i in src:
            refcheck = mc.referenceQuery(i, inr = True)
            if not refcheck:
                nonRefCts.append(i)
    return nonRefCts 

def bakeIt(sample)  : 
    mySelec = checkEmptySelection()
    minValue,maxValue = getTimeline()
    bakeEveryFrame(mySelec, minValue,maxValue,sample)
    
    for i in mySelec: 
        myCts = getTargetConstraint(i)
        constraintList = keep_non_referenced(myCts)
        
        if constraintList :         
            mc.delete(constraintList) 
            print ('%s constraint(s) deleted.' %constraintList)
        else: 
            print ('%s does not have local constraints.' %i)
                
            
    removeFromAnimLayer(mySelec)

    mc.select(mySelec)            

#=================MAIN FUNCTIONS=================#   
def main():
    bakeIt(1)
def bakeOnTwos():
    bakeIt(2)
def bakeOnForths():    
    bakeIt(4)
#Bake all constraints objects.
def bakeAllSceneConstraints():
    allSceneCts = getAllConstraints()
    #delete doublon
    constraintList = list(set(keep_non_referenced(allSceneCts))) 
    
    if not constraintList:
        errorNoConstraintsInScene()
    else: 
        constraintList.sort()
    
    createWindow(constraintList)

    
def mergeAllSceneLayers():
    deleteEmptyLayers()
    allLayers = getAllLayers()
    if allLayers: 
        myObjects = selectObjectsFromLayers(allLayers)
        main()
        
        #double check if all layers are deleted.
        allLayers = getAllLayers()
        if allLayers: 
            errorAnimLayerReference()
    else:
            errorNoAnimLayer()
    return
