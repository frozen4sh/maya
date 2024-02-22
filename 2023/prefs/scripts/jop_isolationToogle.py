import maya.cmds as mc
scriptVersion = 'v06'
scriptName = 'isolationToggle'
 
'''
Copyright 2020 Jesse ONG PHO
jesseongpho@hotmail.com

DESCRIPTION : 
Toggle visibility of a list of objects. Really useful when animating in a heavy scene, it can make the panel lighter and help animating at a higher frame rate. 

FEATURES:
- Work on all model Panel of the scene
- Add or Delete objects from List 
- Select in the list = select in the viewport (can be used as a picker)
- Toggle different element in the option menu (viewport2.0, imagePlane, etc...)
- Custumizable UI 
- Work on maya 2016,2018,2020, 2022 both Linux and Windows (Did not try other version but it should work)

UPDATE 
2022/06 : Update list automatically. If the object is not in the scene, it will be removed from the list if selected.

2022/05/14: Added the function to delete from the list, objects that do not exist anymore in the scene.

2021/06/22: Made the script compatible with maya 2022

2020/11/02: + And - button add and remove automatically the selection to the all the model panel


HOW TO USE : 
1) Select objects or faces you want to isolate
2) Update the isolate List by clicking on the SELECT button
3) Click Toggle Visibility

INSTALLATION:
To install, drag and drop the install.mel file onto the maya viewport.
'''
def getPanel():
    allPanel = mc.getPanel(type ='modelPanel')   
    return allPanel   

def isolationToggle(textField,listCheckBox):
    oldSelect = mc.ls(sl=True)     
    selectAll(textField)
    
    vp2         = mc.checkBox(listCheckBox[0], q=True,value= True )
    curves      = mc.checkBox(listCheckBox[1], q=True,value= True )
    imgPlane    = mc.checkBox(listCheckBox[2], q=True,value= True )
    locators    = mc.checkBox(listCheckBox[3], q=True,value= True )
    texture     = mc.checkBox(listCheckBox[4], q=True,value= True )
    surfaces    = mc.checkBox(listCheckBox[5], q=True,value= True )
    antiAliasing= mc.checkBox(listCheckBox[6], q=True,value= True )
    lights      = mc.checkBox(listCheckBox[7], q=True,value= True )
    ambient     = mc.checkBox(listCheckBox[8], q=True,value= True )
    deformers   = mc.checkBox(listCheckBox[9], q=True,value= True )
    motionTrails= mc.checkBox(listCheckBox[10],q=True,value= True )
    greasePen   = mc.checkBox(listCheckBox[11],q=True,value= True )

    isolatedPanels = getPanel()
    isolateMode = mc.isolateSelect(isolatedPanels[0], q = True, state = True)

    
    for isolatedPanel in isolatedPanels: 

        if isolateMode :
            mc.isolateSelect(isolatedPanel, state = False)
            if vp2:
                mc.modelEditor(isolatedPanel, e=True, rendererName = 'vp2Renderer')
            if curves: 
                mc.modelEditor(isolatedPanel, e=True, nurbsCurves=False)
            if imgPlane:
                mc.modelEditor(isolatedPanel, e=True, imagePlane=True)    
            if locators:
                mc.modelEditor(isolatedPanel, e=True, locators=False)            
            if texture: 
                mc.modelEditor(isolatedPanel, e=True, displayTextures=True)   
            if surfaces: 
                mc.modelEditor(isolatedPanel, e=True, nurbsSurfaces=False)                   
            if antiAliasing: 
                mc.setAttr('hardwareRenderingGlobals.multiSampleEnable', 1) 
            if lights:     
                mc.modelEditor(isolatedPanel, e=True, displayLights='all')  
            if ambient: 
                mc.setAttr('hardwareRenderingGlobals.ssaoEnable', 1)         
            if deformers: 
                mc.setAttr(isolatedPanel, e=True, deformers=False)          
            if motionTrails: 
                mc.setAttr(isolatedPanel, e=True, motionTrails=False)         
            if greasePen: 
                mc.setAttr(isolatedPanel, e=True, greasePencils=False)   
            
        else:
        
            mc.editor (isolatedPanel, edit = True, lockMainConnection = True, mainListConnection='activeList')
            mc.isolateSelect(isolatedPanel, state =1)
            
            if vp2:
                mc.modelEditor(isolatedPanel, e=True, rendererName = 'base_OpenGL_Renderer')
            if curves: 
                mc.modelEditor(isolatedPanel, e=True, nurbsCurves=True)
            if imgPlane:
                mc.modelEditor(isolatedPanel, e=True, imagePlane=False) 
            if locators:
                mc.modelEditor(isolatedPanel, e=True, locators=True)    
            if texture: 
                mc.modelEditor(isolatedPanel, e=True, displayTextures=False) 
            if surfaces: 
                mc.modelEditor(isolatedPanel, e=True, nurbsSurfaces=True)
            if antiAliasing: 
                mc.setAttr('hardwareRenderingGlobals.multiSampleEnable', 0)  
            if lights:     
                mc.modelEditor(isolatedPanel, e=True, displayLights='default')  
            if ambient: 
                mc.setAttr('hardwareRenderingGlobals.ssaoEnable', 0)        
            if deformers: 
                mc.setAttr(isolatedPanel, e=True, deformers=True)       
            if motionTrails: 
                mc.setAttr(isolatedPanel, e=True, motionTrails=True)         
            if greasePen: 
                mc.setAttr(isolatedPanel, e=True, greasePencils=True)     
            
            
    mc.select(oldSelect)

def selectAll(list):
    selection = mc.textScrollList( list,q=True,allItems=True)
    newList = []
    for i in selection: 
        if mc.objExists(i):
            newList.append(i)
        else:
            mc.textScrollList(list, e=True, removeItem = i )
    mc.select(newList)
    
def selectItem(list):
    selection = mc.textScrollList( list,q=True,selectItem=True)
    try: 
        mc.select(selection)
    except: 
        mc.textScrollList(list, e=True, removeItem = selection )


    
class MyToggleIsolation ():
    def __init__(self):
        self.window = scriptName + '_' + scriptVersion
        self.title = scriptName
        self.size = (180 , 120)
        self.buttonWidth = 180
        self.buttonHeight = 50
        self.backgroundColor = [.8,0.6,.1] 
        
        self.labelObject = '1. What \n Object \n to \n Isolate'
        self.labeltoggleIsolation = '2. Toggle Isolation'
        
        self.legsTextField = None
        self.selection =[]
        
    def updateSelection(self):
        mc.textScrollList( self.legsTextField,e=True,removeAll=True)
        
        newSelection = mc.ls(sl=True)
        
        expanded = mc.filterExpand(newSelection, selectionMask=34)
        if expanded:
            newSelection = expanded
        
        self.selection = newSelection
        for object in self.selection:
            mc.textScrollList( self.legsTextField, e=True, append=object)
           
 
 
    def addItem(self):
        addedSelection =  mc.ls(sl=True)
        expanded = mc.filterExpand(addedSelection, selectionMask=34)
        if expanded:
            addedSelection = expanded
        
        for object in addedSelection: 
            if object not in self.selection:
                self.selection.append(object)
                mc.textScrollList(self.legsTextField ,e=True,append=object)
       
                
        isolatedPanels = getPanel()
        for isolatedPanel in isolatedPanels:
            mc.isolateSelect(isolatedPanel, addSelected =True)
        
    def deleteItem(self):
        delSelection = mc.ls(sl=True)
        expanded = mc.filterExpand(delSelection, selectionMask=34)
        if expanded:
            delSelection = expanded
        
        for object in delSelection: 
            if object in self.selection:
                self.selection.remove(object)
                mc.textScrollList(self.legsTextField ,e=True,removeItem=object)
        
                
        isolatedPanels = getPanel()
        for isolatedPanel in isolatedPanels:
            mc.isolateSelect(isolatedPanel, removeSelected =True)
        
    def create (self):

        #Makes sure we close previous window
        if mc.window (self.window, exists = True ):
            mc.deleteUI (self.window, window = True)
        self.window = mc.window(self.window, title = self.title, widthHeight=(200,200))
        
        
        dadForm = mc.paneLayout( configuration='top3',paneSize=[3,100,1],staticHeightPane=3) 
        child1 = mc.formLayout()
        self.legsTextField  = mc.textScrollList( allowMultiSelection=True,height=90, width=1)
        mc.textScrollList(self.legsTextField, e=True, selectCommand = lambda:  selectItem(self.legsTextField) )
        
        
        button1 = mc.button(label='SELECT',width=50, height=30,command = lambda x:  self.updateSelection())
        button2 = mc.button(label='+',width=50, height=30,command = lambda x:  self.addItem())
        button3 = mc.button(label='-',width=50, height=30,command = lambda x:  self.deleteItem())
        
        
        mc.formLayout(child1, edit=True, attachForm=[self.legsTextField, "left",0])
        mc.formLayout(child1, edit=True, attachForm=[self.legsTextField, "top",0])
        mc.formLayout(child1, edit=True, attachForm=[self.legsTextField, "bottom",0])
        mc.formLayout(child1, edit=True, attachControl=[self.legsTextField, "right",3,button2])
        mc.formLayout(child1, edit=True, attachControl=[self.legsTextField, "right",3,button1])
        mc.formLayout(child1, edit=True, attachControl=[self.legsTextField, "right",3,button3])
        
        
        mc.formLayout(child1, edit=True, attachForm=[button1, "right",0])
        mc.formLayout(child1, edit=True, attachForm=[button1, "top",0])
        mc.formLayout(child1, edit=True, attachControl=[button1, "bottom",3, button2])
        
        
        mc.formLayout(child1, edit=True, attachPosition=[button2, "top",0,33])
        mc.formLayout(child1, edit=True, attachForm=[button2, "right",0])
        mc.formLayout(child1, edit=True, attachControl=[button2, "bottom",0,button3])
        
        mc.formLayout(child1, edit=True, attachPosition=[button3, "top",0,66])
        mc.formLayout(child1, edit=True, attachForm=[button3, "right",0])
        mc.formLayout(child1, edit=True, attachForm=[button3, "bottom",0])
        
        mc.setParent('..')
        button4 = mc.button(label='Toggle Visibility', height=50,command = lambda x : isolationToggle(self.legsTextField,listCheckBox))
        
        
        
        mc.setParent(dadForm)   
        optionFormDad =  mc.formLayout()
        optionFrame = mc.frameLayout( label='option', collapsable=True,collapse= True)
        optionForm =  mc.formLayout()
        check1 = mc.checkBox(label='Vp2')
        check2 = mc.checkBox(label='Curves')
        check3 = mc.checkBox(label='ImagePlane')
        check4 = mc.checkBox(label='Locators')
        check5 = mc.checkBox(label='Texture')
        check6 = mc.checkBox(label='Surfaces')
        check7 = mc.checkBox(label='AntiAliasing')
        check8 = mc.checkBox(label='Lights')
        check9 = mc.checkBox(label='Ambient OCC')
        check10 = mc.checkBox(label='Deformers')
        check11 = mc.checkBox(label='MotionTrails')
        check12 = mc.checkBox(label='greasePencils')
        
        
        listCheckBox = [check1,check2,check3,check4,check5,check6,check7,check8,check9,check10,check11,check12]
        
        mc.formLayout(optionFormDad, edit=True, attachForm=[optionFrame, "bottom",0])
        mc.formLayout(optionFormDad, edit=True, attachForm=[optionFrame, "top",0])
        mc.formLayout(optionFormDad, edit=True, attachForm=[optionFrame, "left",0])
        mc.formLayout(optionFormDad, edit=True, attachForm=[optionFrame, "right",0])
        
        mc.formLayout(optionForm, edit=True, 
                    attachForm=[(check1, "left",5),
                                  (check2, "right",5),
                                  
                                  (check3, "left",5),
                                  (check4, "right",5),
                                  
                                  (check5, "left",5),
                                  (check6, "right",5),
                                  
                                  (check7, "left",5),
                                  (check8, "right",5),
                                  
                                  (check9, "left",5),
                                  (check10, "right",5),
                                  
                                  (check11, "left",5),
                                  (check12, "right",5),
                                  
                                  
                                  (check11, "bottom",0),
                                  (check12, "bottom",0),
                                  ],
                                  
                    attachControl=[
                                   (check1, 'bottom', 0, check3),
                                   (check2, 'bottom', 0, check4),
                                   (check3, 'bottom', 0, check5),
                                   (check4, 'bottom', 0, check6),
                                   (check5, 'bottom', 0, check7),
                                   (check6, 'bottom', 0, check8),
                                   (check7, 'bottom', 0, check9),
                                   (check8, 'bottom', 0, check10),
                                   (check9, 'bottom', 0, check11),
                                   (check10, 'bottom', 0, check12),
                                   
                                   
                                   
                                   ],
                    attachPosition=[(check1, "right", 0, 33),
                                    (check2, "left", 0, 35),  
                                    
                                    
                                    (check3, "right", 0, 33),
                                    (check4, "left", 0, 35),  
                                    
                                    (check5, "right", 0, 33),
                                    (check6, "left", 0, 35),  
                                    
                                    (check7, "right", 0, 33),
                                    (check8, "left", 0, 35),  
                                    
                                    (check9, "right", 0, 33),
                                    (check10, "left", 0, 35),  
                                    
                                    (check11, "right", 0, 33),
                                    (check12, "left", 0, 35),  
                                    ])

        mc.showWindow()
def main():
    toggleIsolationWindow = MyToggleIsolation()
    toggleIsolationWindow.create()