# -*- coding: utf-8 -*- 

## MIN studio animationteam tools v05 2016.04.26
## Á÷Á¢¿¢¼¼½º·Î º¯°æ=¤µ= ¸íÄªµé ÂÉ²û º¯°æ 2017.05.26 // line.743 ffmpeg ÆÄÀÏ °æ·Î »óÈ²¿¡ ¸Â°Ô °æ·Î ¼öÁ¤ÇØÁÖ±â
## leeyoonsin@gmail.com


import maya.cmds as mc
import maya.mel as mel


## Ã¢ ¸¸µé±â ##

def anitools():
    win = 'MINwindow'
    if mc.window(win,exists=1) :
        mc.deleteUI(win)
    
    mc.window(win,title="anitool v01",widthHeight=(150,220),s=1)
    mc.columnLayout(adjustableColumn=1)
    mc.text("Ani Tools",fn="fixedWidthFont",h=40)
    #mc.separator(height=30, style='in')
    #mc.button(h=35,bgc=(0.8,0.8,0.8),l="¾À ¼¼ÆÃ",c="spp_sceneFormat_fix()")
    mc.button(h=35,bgc=(0.9,0.9,0.9),l="ÀÛ¾÷ÀÚ Á¤º¸ ¼öÁ¤",c="spp_animHUD_user()")
    mc.button(h=35,bgc=(0.67,0.67,0.67),l="¼¦ Á¤º¸ Ç¥½Ã",c="spp_animHUD()")
    #mc.button(h=35,bgc=(0.38,0.38,0.38),l="¿µ»ó ¸¸µé±â",c="UI()")
    #mc.button(h=35,bgc=(0,0,0),l="¼¦ ÀúÀå",c="clearUI()")    
    mc.button(h=35,bgc=(0.2,0.2,0.2),l="Close",c=("mc.deleteUI('%s',window=1)" %win))
    mc.showWindow(win)
    
    # È¯°æº¯¼ö ¸¸µê. ¾Æ·¡ HUDonoff¶û playblast ½ÇÇà ±¸°£¿¡µµ Áßº¹À¸·Î ³Ö¾î³ùÀ½.
    if not mc.optionVar(q='sppAnimHUDUserName'):
        mc.optionVar(sv=('sppAnimHUDUserName','UserName'))
    if not mc.optionVar(q='sppAnimHUDUserCorp'):
        mc.optionVar(sv=('sppAnimHUDUserCorp','UserCorp'))

    # HUD ÄÃ·¯ º¯°æ ¸í·É¾î, ÇöÀç 17¹ø ³ë¶ûÀ¸·Î ÁöÁ¤
    # 1 ºí·¢, 6 ÆÄ¶û, 9 ÇÎÅ©, 13 »¡°­, 16 È­ÀÌÆ®, 17 ³ë¶û, 18 ÇÏ´Ã, 27 ÃÊ·Ï
    mc.displayColor('headsUpDisplayLabels' ,17 ,dormant=1)
    mc.displayColor('headsUpDisplayValues' ,17 ,dormant=1)




## ---------------------------------------------------------------------------------------------
## pa_sceneFormat_fix.mel
## ---------------------------------------------------------------------------------------------
##
## Source by KeeKee (gmdirect@ocon.kr)
##
## ---------------------------------------------------------------------------------------------


#def spp_sceneFormat_fix_setup():
#    btn = spp_sceneFormat_fix(spp_installShelfButton)  
#    img = "sceneFormat.bmp"
#    cmd = spp_sceneFormat_fix
#    mc.shelfButton("spp_sceneFormat_fix", ex=1, command=cmd+btn)

def spp_sceneFormat_fix():

#    mc.displayColor(c=1, dormant=1, headsUpDisplayValues=17)

    win = 'sppSceneFormatWindow'
    
    if mc.window(win,exists=1) :
        mc.deleteUI(win)

    mc.window(win, title='MIN Scene Format', sizeable=0, minimizeButton=0, maximizeButton=0)
    mc.columnLayout(adjustableColumn=1, columnOffset=('both', 5)) 
    mc.text(label='', height=5)
    mc.frameLayout(borderStyle="etchedIn", labelVisible=0)
    mc.columnLayout(adjustableColumn=1, columnOffset=('both', 10))
    mc.text(label='', height=20)
    mc.checkBox('sppSceneFormat_turnOnHud', label="Turn on HUD", value=1) 
    mc.text(label='', height=10)
    mc.rowLayout(numberOfColumns=2, columnWidth2=(100,100), columnOffset2=(0,0), columnAttach2=('both', 'both'), columnAlign2=('left','left')) 
    mc.text(label='Start Frame')
    mc.text(label='End Frame')
    mc.setParent('..')
    mc.rowLayout(numberOfColumns=2, columnWidth2=(100,100), columnOffset2=(0,0), columnAttach2=('both','both'), columnAlign2=('left','left')) 
    mc.intField('sppSceneFormat_startFrame', height=30, value=101)
    mc.intField('sppSceneFormat_endFrame', height=30, value=200)
    mc.setParent('..')
    mc.separator(height=30, style='in')
    mc.rowLayout(numberOfColumns=2, columnWidth2=(60,100), columnOffset2=(0,0), columnAttach2=('both','both'), columnAlign2=('left','left')) 
    mc.text(label='Linear', align='right')
    mc.textField(tx='centimeter', editable=0)
    mc.setParent('..')
    mc.rowLayout(numberOfColumns=2, columnWidth2=(60,100), columnOffset2=(0,0), columnAttach2=('both','both'), columnAlign2=('left','left'))
    mc.text(label='Angular', align='right')
    mc.textField(tx='degrees', editable=0)
    mc.setParent('..')
    mc.rowLayout(numberOfColumns=2, columnWidth2=(60,100), columnOffset2=(0,0), columnAttach2=('both','both'), columnAlign2=('left','left'))
    mc.text(label='Time', align='right')
   
    ### ÃÊ´ç ÇÁ·¹ÀÓ
    mc.optionMenu('timefps')
    mc.menuItem( label='Film (24 fps)')
    mc.menuItem( label='Pal (25 fps)')
    mc.menuItem( label='NTSC (30 fps)')

    mc.setParent('..')
    mc.separator(height=30, style='in')
    mc.rowLayout(numberOfColumns=2, columnWidth2=(100,100), columnOffset2=(0,0), columnAttach2=('both','both'), columnAlign2=('left','left')) 
    mc.text(label='Width')
    mc.text (label='Height')
    mc.setParent('..')
    mc.rowLayout(numberOfColumns=2, columnWidth2=(100,100), columnOffset2=(0,0), columnAttach2=('both','both'), columnAlign2=('left','left')) 
    mc.intField('sppSceneFormat_width', height=30, value=1920)
    mc.intField('sppSceneFormat_height', height=30, value=1080)
    mc.setParent('..')
    mc.text(label='', height=20)
    mc.button(label='SCENE FORMAT', height=30, command='spp_sceneFormat_fix_run()')
    mc.text(label='', height=10)
    mc.text(label='', height=5)
    mc.showWindow(win)

def spp_sceneFormat_fix_run():
    
    ## ÃÊ´ç ÇÁ·¹ÀÓ
    if mc.optionMenu('timefps',q=1,v=1) == 'Film (24 fps)':
        mc.currentUnit(time="film")
    if mc.optionMenu('timefps',q=1,v=1) == 'Pal (25 fps)':
        mc.currentUnit(time="pal")
    if mc.optionMenu('timefps',q=1,v=1) == 'NTSC (30 fps)':
        mc.currentUnit(time="ntsc")

    stFrame = mc.intField('sppSceneFormat_startFrame',q=1, value=1)
    edFrame = mc.intField('sppSceneFormat_endFrame',q=1, value=1)
    mc.playbackOptions(animationStartTime=(stFrame-5), animationEndTime=(edFrame+5), minTime=stFrame, maxTime=edFrame) 
    mc.currentTime(stFrame)
    
    hud = mc.checkBox('sppSceneFormat_turnOnHud', q=1,v=1)
    spp_animHUD_switch(hud)
    mc.currentUnit(l='centimeter')
    mc.currentUnit(angle="degree")
    
    width = mc.intField('sppSceneFormat_width', q=1, v=1)
    height = mc.intField('sppSceneFormat_height', q=1, v=1)
    ## vray°¡ ¾øÀ» °æ¿ì¸¦ À§ÇØ ¿¹¿ÜÃ³¸® 
    try :
        mc.setAttr('vraySettings.width',width)
        mc.setAttr('vraySettings.height',height)
    except :
        pass
    mc.setAttr('defaultResolution.width',width)
    mc.setAttr('defaultResolution.height',height)
    mc.setAttr('defaultResolution.imageSizeUnits', 0)
    mc.setAttr('defaultResolution.dotsPerInch', 72.0)
    mc.setAttr('defaultResolution.pixelDensityUnits', 0)
    mc.setAttr('defaultResolution.deviceAspectRatio', (width / (height*1.0)))
    mc.setAttr('defaultResolution.pixelAspect', 1.000)

    win = 'sppSceneFormatWindow'
    mc.deleteUI(win)
















# ---------------------------------------------------------------------------------------------
# spp_animHUD.mel
# ---------------------------------------------------------------------------------------------
#
# Source by KeeKee (gmdirect@ocon.kr)
#
# ---------------------------------------------------------------------------------------------

#g_animHudState=0  #¹»±î?


#def spp_animHUD_setup():
#    btn1 = spp_animHUD(spp_installShelfButton)
#    btn2 = spp_animHUD_user(spp_installShelfButton)
#       img1 = "animHUD.bmp";
#       img2 = "animHUD_user.bmp";
#    cmd1 = "spp_animHUD;";
#    cmd2 = "spp_animHUD_user;";
#    mc.shelfButton(label='spp_animHUD', editable=1, command=cmd1+btn1)
#    mc.shelfButton(label='spp_animHUD_user', editable=1, command=cmd2+btn2)

def spp_animHUD_user():

    
    win = 'sppAnimHUDWindow'
    if mc.window(win, exists=1):
        mc.deleteUI(win)
       
    
    mc.window(win, title='HUD Name', sizeable=0, minimizeButton=0, maximizeButton=0)    
    mainForm = mc.formLayout()
    mainFrame = mc.frameLayout('mainFrame', borderStyle='etchedIn', labelVisible=0)
    mc.columnLayout(adjustableColumn=1, columnOffset=('both',10))
    mc.text (label="", height=10)
    mc.text (label="Input your name to print on display")
    mc.text (label="", height=10)
    mc.rowColumnLayout(nc=2)
    
        
    mc.text (label="Corporation :   " ,align="right" ,font="boldLabelFont")    
    mc.textField ('sppAnimHUDWindow_inputUserCorp' ,height=22 ,text=mc.optionVar(q='sppAnimHUDUserCorp') )
    mc.text (label="Name :   " ,align="right" ,font="boldLabelFont")    
    mc.textField ('sppAnimHUDWindow_inputUsername' ,height=22 ,text=mc.optionVar(q='sppAnimHUDUserName') )
    mc.text (label="", height=10)
    mc.setParent('..')
    
    mc.button (label="SET TO THE NAME", height=30, command="spp_animHUD_user_execute()")
    mc.text (label="", height=10)
    mc.formLayout(mainForm, edit=1, attachForm=[(mainFrame, 'top', 5),(mainFrame, 'left', 5),(mainFrame, 'right', 5),(mainFrame, 'bottom', 5)])
    mc.showWindow(win)



 

def spp_animHUD_user_execute():
    win = 'sppAnimHUDWindow'
    corp = mc.textField('sppAnimHUDWindow_inputUserCorp',q=1, tx=1)
    name = mc.textField('sppAnimHUDWindow_inputUsername',q=1, tx=1)
    popcorp=0
    popname=0
    if corp :
        mc.optionVar(sv=('sppAnimHUDUserCorp',corp))
        popcorp=corp
    else :
        mc.optionVar(sv=('sppAnimHUDUserCorp','UserCorp'))
        popcorp='UserCorp'

    if name :
        mc.optionVar(sv=('sppAnimHUDUserName',name))
        popname=name
    else :
        mc.optionVar(sv=('sppAnimHUDUserName','UserName'))
        popname='UserName'
    
    digiart_confirm ("It is changed that the corporation of HUD to [ " + popcorp + " ]\nIt is changed that the name of HUD to [ " + popname + " ]")
    mc.deleteUI(win)







def spp_animHUD_state():
    if 'spp_animHUD_fps' in mc.headsUpDisplay(q=1,listHeadsUpDisplays=1):
        HudState = 1
    else:HudState = 0
    return HudState


def spp_animHUD():
#    g_animHudState = 0
#    if not mc.optionVar(ex='sppAnimHUDUserName'):
#        mc.optionVar('sppAnimHUDUserName', stringValue="MIN_USER")
    if not mc.optionVar(q='sppAnimHUDUserName'):
        mc.optionVar(sv=('sppAnimHUDUserName','UserName'))
    if not mc.optionVar(q='sppAnimHUDUserCorp'):
        mc.optionVar(sv=('sppAnimHUDUserCorp','UserCorp'))
        
    if spp_animHUD_state() == 1:spp_animHUD_switch(0)
    else:spp_animHUD_switch(1)
#HUDList = mc.headsUpDisplay(q=1,listHeadsUpDisplays=1)
#for selHud in HUDList:
#    if 'spp' in selHud:
#        mc.headsUpDisplay(selHud,rem=1)
#mc.headsUpDisplay('spp_animHUD_sceneFileName',rem=1)
#mc.headsUpDisplay('spp_animHUD_currentFrame',rem=1)

def spp_animHUD_switch(switch):
#    g_animHudState = switch

    ## Off the HUDViewAxis
    if mc.headsUpDisplay('HUDViewAxis', ex=1):
        mc.headsUpDisplay('HUDViewAxis', e=1, vis=0)
    
    hudList = ["spp_animHUD_cameraType",
        "spp_animHUD_stereoMode",
        "spp_animHUD_focalLength",
        "spp_animHUD_currentProject",
        "spp_animHUD_sceneFileName",
        "spp_animHUD_fps",
        "spp_animHUD_runningTime",
        "spp_animHUD_currentFrame",
        "spp_animHUD_corp",
        "spp_animHUD_staff",
        "spp_animHUD_time",
        "spp_animHUD_date"]


    for hud in hudList:
        if mc.headsUpDisplay(hud, ex=1):
            mc.headsUpDisplay(hud, rem=1)

    if switch:
        saveCorp=mc.optionVar(q='sppAnimHUDUserCorp') 
        saveName=mc.optionVar(q='sppAnimHUDUserName') 
        ##int $block = `headsUpDisplay -nextFreeBlock 4`;
        ##headsUpDisplay -section 4 -block $block -attachToRefresh -label "Camera Type"
        ##  -command "spp_animHUD_displayCameraType" spp_animHUD_cameraType;
        
        ##int $block = `headsUpDisplay -nextFreeBlock 4`;
        ##headsUpDisplay -section 4 -block $block -attachToRefresh -label "Stereo Mode"
        ##  -command "spp_animHUD_displayStereoMode" spp_animHUD_stereoMode;
        
        ##int $block = `headsUpDisplay -nextFreeBlock 4`;
        ##headsUpDisplay -section 4 -block $block -attachToRefresh -label "Project Dir"
        ##  -command "string $project = `workspace -q -o`;" spp_animHUD_currentProject;
        
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_sceneFileName', section=5, block=block, label='Scene', attachToRefresh=1, command='mc.file(q=1 ,sn=1 ,shn=1)')
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_fps', section=5, block=block, label='Fps', attachToRefresh=1, command='spp_animHUD_displayFps()') 
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_runningTime', section=5, block=block, label='Range', attachToRefresh=1, command='spp_animHUD_runningTime()') 
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_currentFrame', section=5, block=block, label='Frame', attachToRefresh=1, dataFontSize='large', command='mc.currentTime(q=1)')
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_focalLength', section=5, block=block, label='Focal Length', attachToRefresh=1, dataFontSize='large', command='spp_animHUD_camFocalLength()')
        block = mc.headsUpDisplay(nextFreeBlock=9)
        mc.headsUpDisplay('spp_animHUD_date', section=9, block=block, label='Date', attachToRefresh=1, command='mc.about(currentDate=1)')
        
        ##int $block = `headsUpDisplay -nextFreeBlock 9`;
        ##headsUpDisplay -section 9 -block $block -label "Time" -attachToRefresh
        ##  -command "about -currentTime" spp_animHUD_time;
        block = mc.headsUpDisplay(nextFreeBlock=9)
        mc.headsUpDisplay('spp_animHUD_staff', section=9, block=block, label='Name', attachToRefresh=1, command='mc.optionVar(q="sppAnimHUDUserName")')
        block = mc.headsUpDisplay(nextFreeBlock=9)
        mc.headsUpDisplay('spp_animHUD_corp' ,section=9 ,block=block ,label='Corp' ,attachToRefresh=1 ,command='mc.optionVar(q="sppAnimHUDUserCorp")')

        #return g_animHudState

    
    
def spp_animHUD_displayFps():
    time = mc.currentUnit(q=1, time=1)
    if time == "film":
        return "24fps"
    elif time == "ntsc":
        return "30fps"
    else:
        return mc.currentUnit(q=1, time=1)


def spp_animHUD_camFocalLength():
    focaLength=0
    try:
        whichPanel = mc.getPanel(withFocus=1)
        nameCamera = mc.modelPanel(whichPanel,q=1, camera=1)
        focalLength = mc.getAttr(nameCamera + ".focalLength")
    except:
        focalLength='cam'
    return focalLength



def spp_animHUD_runningTime():
    animationStartFrame = mc.playbackOptions(q=1, min=1)
    animationEndFrame = mc.playbackOptions(q=1, max=1)
    runningTime = animationEndFrame - animationStartFrame + 1
    form = '%d - %d ( %d )' % (int(animationStartFrame),int(animationEndFrame),int(runningTime))
    return form








#/////////////////////  spp_sceneFormat_fix ÇÔ¼ö¿¡¼­ ÇÊ¿äÇÑ ÇÔ¼ö //////////

def digiartArrayFirst (camList):
    if len(camList): 
        return camList[0]
    else : 
        return None

def digiart_confirm (printMsg):
    mc.confirmDialog(title="MIN : Report",messageAlign="center",message=printMsg,icon="information",button="OK")














#//////////////// playblast ¿øº» ¼Ò½º ÅëÂ°·Î ffmÀº ¿ÜºÎ °æ·Î °ü¸® ÇÏ±â

import os
#import maya.cmds as mc
from functools import partial
import maya.mel as mel
import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import ast

def UI():
    win='PB'
    if mc.window(win, exists=True):
        mc.deleteUI(win)
    
    mc.window(win, title="Playblaster ver.1.0", mnb=False, mxb=False, sizeable=False)
    
    mc.columnLayout(columnOffset=("both",10), adj=True)

    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=2, columnWidth=[(1, 110), (2, 410)] )
    mc.text(label="User Info", align="left",font="boldLabelFont") 
    mc.separator(style="in")    

    mc.setParent('..')
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=6, columnWidth=[(1, 5), (2, 70), (3, 160), (4, 70), (5, 160), (6, 50)] )
    mc.separator(h=10,style="none")
    
    if not mc.optionVar(q='sppAnimHUDUserName'):
        mc.optionVar(sv=('sppAnimHUDUserName','UserName'))
    if not mc.optionVar(q='sppAnimHUDUserCorp'):
        mc.optionVar(sv=('sppAnimHUDUserCorp','UserCorp'))
    
    saveCorp=mc.optionVar(q='sppAnimHUDUserCorp') 
    saveName=mc.optionVar(q='sppAnimHUDUserName') 
    
    mc.text(label="Corp : ", align="right")
    mc.textField("corp", text=saveCorp ,ed=0)
    mc.text(label="Name : ", align="right")
    mc.textField("userName", text=saveName ,ed=0) 
        
    mc.setParent('..')
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=2, columnWidth=[(1, 110), (2, 410)] )
    mc.text(label="Dispaly Options", align="left",font="boldLabelFont")    
    mc.separator(style="in")

    mc.setParent('..')
    mc.separator(h=10, style="none")
    mc.rowColumnLayout(nc=3, columnWidth=[(1,30),(2,250),(3,240)])
    mc.separator(h=10,style="none")
    rvalue=getDisplayOptions("displayResolution")
    mc.checkBox(label="Display Resolution", v=rvalue, onc=partial(displayOptions,"displayResolution", "on"), ofc=partial(displayOptions,"displayResolution", "off"))
    savalue=getDisplayOptions("displaySafeAction")
    mc.checkBox(label="Display Safe Action", v=savalue, onc=partial(displayOptions,"displaySafeAction", "on"), ofc=partial(displayOptions,"displaySafeAction", "off"))
    mc.separator(style="none")
    gmvalue=getDisplayOptions("displayGateMask")
    mc.checkBox(label="Display Gate Mask", v=gmvalue, onc=partial(displayOptions,"displayGateMask", "on"), ofc=partial(displayOptions,"displayGateMask", "off"))
    stvalue=getDisplayOptions("displaySafeTitle")
    mc.checkBox(label="Display Safe Title", v=stvalue, onc=partial(displayOptions,"displaySafeTitle", "on"), ofc=partial(displayOptions,"displaySafeTitle", "off"))
    #mc.separator(h=10,style="none")
    #mc.rowColumnLayout(nc=2, columnWidth=[(1, 90), (2, 480)] )
    #mc.text(label="Info ", align="left",font="boldLabelFont") 
    #mc.separator(style="in")
    
    #mc.setParent( '..' )
    #scName = mc.file(q=1,sceneName=1).split('/')[-1].partition(".")[0]
    #iniOutput = defaultPath()
    #duration = totalDuration()
    #Fps = fps()
    #mc.textScrollList("PBinof", h=80, numberOfRows=8, append=["Scene Name : " + scName, "Outpath : " + iniOutput, "Duration : " + duration, "Fps : "+ Fps +"fps"])
        
    # time range 
    mc.setParent( '..' )
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=2, columnWidth=[(1, 110), (2, 410)] )
    mc.text(label="Time Range  ", align="left",font="boldLabelFont")    
    mc.separator(style="in")
       
    mc.setParent( '..' )
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=5, columnWidth=[(1, 5), (2, 70), (3, 160), (4, 70), (5, 160)] )
    mc.separator(h=10,style="none")
    mc.text(label="Start : ", align="right")
    mc.intField("Start", value= mc.playbackOptions(q=True, minTime=True))
    mc.text(label="End : ", align="right")
    mc.intField("End", value = mc.playbackOptions(q=True, maxTime=True)) 
    
        # image size
    mc.setParent( '..' )
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=2,columnWidth=[(1, 100), (2, 420)])
    mc.text("Dispaly Size", h=20, align="left",font="boldLabelFont")
    
    mc.separator(h=10,style="in")
    mc.setParent( '..' )
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=5, columnWidth=[(1, 5), (2, 70), (3, 160), (4, 70), (5, 160)] )
    mc.separator(h=10,style="none")
    mc.text(label="Width :", align="right")
    mc.intField("Width", value = mc.getAttr('defaultResolution.width'))
    mc.text(label="Height :", align="right")
    mc.intField("Height", value = mc.getAttr('defaultResolution.height'))  
    mc.separator(h=15,style="none")
    mc.separator(h=15,style="none")
    mc.separator(h=15,style="none")
    
    #mc.setParent( '..' )
    mc.text(label="Scale:", align="right")
    if not mc.optionVar(q='playblastScale') : Defaultscale = 100
    else : Defaultscale = mc.optionVar(q='playblastScale')
    mc.intField("Scale", value = int(Defaultscale))
    
    # output
    mc.setParent( '..' )
    mc.separator(h=10,style="none")
    mc.rowColumnLayout(nc=2,columnWidth=[(1, 60), (2, 460)])
    mc.text("Output:", align="left",font="boldLabelFont")
    mc.separator(h=10, style="in")
    mc.setParent( '..' )
    mc.separator(h=10,style="none")
    
    
    mc.rowColumnLayout(nc=4, columnWidth=[(1, 5), (2, 200), (3, 5), (4, 200)])
    
    #mc.text(label="format : ", align="right")
    #Defaultfromat=defaultSet("format")
    mc.separator(style="none")
    formats=mc.optionMenu("formats", label="format : ", w=200, cc=formatMenu)
    formatMenu()

    
    #mc.text(label="Encoding : ", align="right")
    #Defaultencode = defaultSet("encoding")
    mc.separator(style="none")
    mc.optionMenu("Encoding", label="     Encoding : ", w=200, cc=encodeMenu)
    encodeMenu()

    #mc.menuItem(label='image')
    #mc.separator(h=10,style="none")    
    
    
    mc.setParent( '..' )
    mc.rowColumnLayout(nc=3)
    #mc.internalVar(uwd=True) +"default/movies/"
    mc.text(label="Path : ", align="right")
    DefaultPath = defaultSet("path")
    mc.textField("outputPath", h=30, w=420, text = DefaultPath)    
    mc.button(label="...", w=30, h=30, c=browseFilePath) #c=partial(browseFilePath, 3, "*.mov", "outputPath")
    mc.text(label="Movie file : ", align="right")
    movieName=mc.file(q=True, sceneName=True).split("/")[-1].partition(".")[0]
    movieFile = mc.textField("movieFile", h=30, w=420, text=movieName)    
    mc.separator(h=10,style="none")
    
    # button
    mc.setParent( '..' )
    mc.separator(h=20, style="in")
    mc.rowColumnLayout(nc=2, columnWidth=[(1, 258), (2, 258)])
    mc.button(label="Playblast", h=40, c=createMovie)
    #mc.button(label="Apply", c = Apply)
    mc.button(label="Reload", c = Reload)
    mc.separator(h=10, style="none")
    
    win='PB'
    mc.showWindow(win)
    
def formatMenu(*args):
    menuItems = mc.optionMenu("formats", q=True, itemListLong=True)
    if menuItems != None :                                                                                           
        for item in menuItems:                                                                                    
            mc.deleteUI(item)
    
    items = [ "qt",]#"avi", "png"]
    
    #filePath = mc.internalVar(usd=True) + "YHplayblast.ini"
    
    #if os.path.isfile(filePath):
        #item = defaultSet("format")
        #mc.menuItem(label=item,  parent = "formats")
        ##items.remove[item]
        ##for item in items:
            ##mc.menuItem(label=item, parent = "formats")       
    #else:
    for item in items:
        mc.menuItem(label=item, parent = "formats")
    
def encodeMenu(*args):
    menuItems = mc.optionMenu("Encoding", q=True, itemListLong=True)
    if menuItems != None :                                                                                           
        for item in menuItems:                                                                                    
            mc.deleteUI(item)
            
    items = ['H.264'] #, 'photo_jepg']
    for item in items:
        mc.menuItem(label=item, parent = "Encoding")    
        
def currentViewCamName(*args):
        activeView = omui.M3dView.active3dView()
        cameraPath = om.MDagPath()
        activeView.getCamera(cameraPath)
        return str(cameraPath.partialPathName())

def displayOptions(change, state,*args):
    cameraName = currentViewCamName()
    if state == 'on':onoff = 1
    if state == 'off':onoff = 0
    mc.setAttr(cameraName +'.'+change, onoff)


def getDisplayOptions(case,*args):
    cameraName = currentViewCamName()
    return mc.getAttr(cameraName +'.'+case)

def Apply(*args):
    
    Path=mc.textField("outputPath", q=True, text =True)
    Scale = mc.intField("Scale", q=True, value = True) 
    mc.optionVar(sv=('playblastScale', Scale))
    Fromat = mc.optionMenu("formats", q=True, value = True)  
    Encoding = mc.optionMenu("Encoding", q=True, value = True)  
    corp = mc.textField("corp", q=True, text=True)
    name = mc.textField("userName", q=True, text=True)  
    
    filePath = mc.internalVar(usd=True)+"YHplayblast.ini"
    f=open(filePath, 'w')
    #f.write(corp+'\n')
    #f.write(name+'\n') 
    f.write(Path +'\n')
    f.write('%d'%Scale+'\n')
    f.write(Fromat+'\n')
    f.write(Encoding+'\n')
    
    f.close()
    
def Reload(*args):
    
    mc.intField("Start", edit=True, value= mc.playbackOptions(q=True, minTime=True))
    mc.intField("End", edit=True, value= mc.playbackOptions(q=True, maxTime=True))

    width = mc.intField("Width", q=True, value =True)
    height = mc.intField("Height", q=True, value =True)
    deviceAspectRatio = width/float(height)
    mc.setAttr('defaultResolution.width', width) 
    mc.setAttr('defaultResolution.height', height)  
    mc.setAttr('defaultResolution.deviceAspectRatio', deviceAspectRatio)


def browseFilePath(*arg):
    
    returnPath = mc.fileDialog2(fm=3, fileFilter="*.mov",  ds=2)
    
    if returnPath > 0 :
        returnPath = returnPath[0]
        mc.textField("outputPath", edit = True, text = returnPath)

def defaultSet(sets,*args):
    
    filePath = mc.internalVar(usd=True) + "YHplayblast.ini"
    
    if os.path.isfile(filePath):
        f=open(filePath, 'r')
        set=f.readlines()
    
        defaultPath = set[0].rstrip()
        defaultScale = set[1].rstrip()
        defaultFormat = set[2].rstrip()
        defaultEncoding = set[3].rstrip()
        f.close()

        if sets == "path":
            return defaultPath
        
        if sets == "scale":
            defaultScale = int(defaultScale)
            return defaultScale ### <------------------============= only panda project   ##
        
        if sets == "format":
            return defaultFormat
        
        if sets == "encoding":
            return defaultEncoding      
        
    else:

        if sets == "path":
            return mc.internalVar(uwd=True) +"default/movies/"
        
        if sets == "scale":
            return 100
        
        if sets == "format":
            return "qt"
        
        if sets == "encoding":
            return "h264"       
        

#def fps(*args):
    
#    time = mc.currentUnit(q=True, time=True)
        
#    if time == "film":
#        return "24"
    
#    if time == "ntsc":
#        return "30" 

#    if time == "ntscf":
#        return "60" 


def createMovie(*args):
    

    movieFormat = mc.optionMenu("formats", q=True, value=True)
        
#    if movieFormat == "qt":
    stframe=mc.playbackOptions(q=True, minTime=True)
    edframe=mc.playbackOptions(q=True, maxTime=True)
    mc.playbackOptions(e=True, minTime=mc.intField("Start", q=True, v=True))
    mc.playbackOptions(e=True, maxTime=mc.intField("End", q=True, v=True))
    playBlast()
    
    movieName = mc.textField("movieFile", q=True, text=True) 
    moviepath = mc.textField("outputPath", q=True, text=True)   
    avifileName= moviepath + "/"+ movieName + ".avi"
    movfileName= moviepath + "/"+ movieName + ".mov"
    
    strSceneFileFullName = avifileName
    strOutputMovFileFull = movfileName
    
    #strFfmpegOptions = '-y -i ' + strSceneFileFullName.replace('/', '\\') +' -vcodec prores -profile 0 -r  24 ' + strOutputMovFileFull.replace('/', '\\')
    strFfmpegOptions = '-y -i ' + strSceneFileFullName.replace('/', '\\') +' -vcodec libx264 -profile Baseline -level 20 -threads 0 -pix_fmt yuv420p ' + strOutputMovFileFull.replace('/', '\\')
    #strFfmpegOptions = '-y -i ' + strSceneFileFullName.replace('/', '\\') +' -vcodec libx264 -profile Baseline -level 20 -threads 0 -pix_fmt yuv420p -r ' + str(Fps) + ' '+ strOutputMovFileFull.replace('/', '\\')        
    #a= mc.internalVar(usd=True)
    a="Z:/min_wormhole/panda/tool/MIN_anitools"                  ####<< ffmpeg ÆÄÀÏ °æ·Î À§Ä¡ ¾Ë·ÁÁÖ±â >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    os.system( '%s/ffmpeg.exe' %a + ' ' + strFfmpegOptions)
    os.remove(avifileName)
    
    os.startfile(movfileName)
    
    mc.playbackOptions(e=True, minTime=stframe)
    mc.playbackOptions(e=True, maxTime=edframe)
    
#    if movieFormat == "avi":
        
#        playBlast()
    
def checkPanel(*args):
    
    panelName=mc.getPanel(wf=True)
    
    ## check show options of focus panel
    pcameras = mc.modelEditor(panelName, q=True, cameras=True )
    plocators = mc.modelEditor(panelName, q=True, locators=True )
    pdeformers = mc.modelEditor(panelName, q=True, deformers=True )
    pcurves = mc.modelEditor(panelName, q=True, nurbsCurves=True )  
    
    showset = [pcameras , plocators, pdeformers, pcurves]
    
    return showset


def playBlast(*arg):
    
    stFrame = mc.intField("Start", q=True, v=True)
    endFrame = mc.intField("End", q=True, v=True)
    wid = mc.intField("Width", q=True, v=True)
    hei = mc.intField("Height", q=True, v=True)

    movieName = mc.textField("movieFile", q=True, text=True) 
    moviepath = mc.textField("outputPath", q=True, text=True)   
    avifileName= moviepath + "/"+ movieName + ".avi"
    movfileName= moviepath + "/"+ movieName + ".mov"
    
    scale=mc.intField("Scale", q=True, v=True)  
    
    gPlayBackSlider = mel.eval( '$tmpVar=$gPlayBackSlider' )
    isSound = mc.timeControl( gPlayBackSlider, q=True, ds=True )
    strAudioNodeName =''
    
    ##check current panel show info
    panelName=mc.getPanel(wf=True)
    showset = checkPanel()
    
    mc.modelEditor(panelName, e=True, nurbsCurves=False)
    mc.modelEditor(panelName, e=True, cameras=False)
    mc.modelEditor(panelName, e=True, locators=False)  
    mc.modelEditor(panelName, e=True, deformers=False)      
    
    Apply()
    
    
    
    animHudSt = spp_animHUD_state()
    spp_animHUD_switch(1)

    if isSound:
        strAudioNodeName = mc.timeControl(gPlayBackSlider, query = True, s = True)
    
        mc.playblast( format= "avi", 
                          sound=strAudioNodeName,
                          startTime = stFrame, 
                          endTime = endFrame , 
                          filename=avifileName, 
                          forceOverwrite=1, 
                          sequenceTime=0, 
                          clearCache=1, 
                          viewer=0, 
                          showOrnaments=1, 
                          fp=4, 
                          percent=scale, 
                          compression= "none", 
                          quality=100, 
                          widthHeight=(wid,hei))
    else:
        mc.playblast( format= "avi", 
                          startTime = stFrame, 
                          endTime = endFrame , 
                          filename=avifileName, 
                          forceOverwrite=1, 
                          sequenceTime=0, 
                          clearCache=1, 
                          viewer=0, 
                          showOrnaments=1, 
                          fp=4, 
                          percent=scale, 
                          compression= "none",
                          quality=100, 
                          widthHeight=(wid,hei))            
    
    spp_animHUD_switch(animHudSt)
    
    mc.modelEditor(panelName, e=True, nurbsCurves=showset[3])
    mc.modelEditor(panelName, e=True, cameras=showset[0])
    mc.modelEditor(panelName, e=True, locators=showset[1])
    mc.modelEditor(panelName, e=True, deformers=showset[2]) 
    

            
def spp_animHUD_switch(switch):
    
    if mc.headsUpDisplay('HUDViewAxis', ex=1):
        mc.headsUpDisplay('HUDViewAxis', e=1, vis=0)
        
    hudList = ["spp_animHUD_cameraType",
        "spp_animHUD_stereoMode",
        "spp_animHUD_focalLength",
        "spp_animHUD_currentProject",
        "spp_animHUD_sceneFileName",
        "spp_animHUD_fps",
        "spp_animHUD_runningTime",
        "spp_animHUD_currentFrame",
        "spp_animHUD_corp",
        "spp_animHUD_staff",
        "spp_animHUD_time",
        "spp_animHUD_date"]
    
    for hud in hudList:
        if mc.headsUpDisplay(hud, ex=1):
            mc.headsUpDisplay(hud, rem=1)

    if switch:
        saveCorp=mc.optionVar(q='sppAnimHUDUserCorp') 
        saveName=mc.optionVar(q='sppAnimHUDUserName') 
        
        
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_fps', section=5, block=block, label='Fps', attachToRefresh=1, command='spp_animHUD_displayFps()') 
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_runningTime', section=5, block=block, label='Range', attachToRefresh=1, command='spp_animHUD_runningTime()') 
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_currentFrame', section=5, block=block, label='Frame', attachToRefresh=1, dataFontSize='large', command='mc.currentTime(q=1)')
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_focalLength', section=5, block=block, label='Focal Length', attachToRefresh=1, dataFontSize='large', command='spp_animHUD_camFocalLength()')
        block = mc.headsUpDisplay(nextFreeBlock=9)
        mc.headsUpDisplay('spp_animHUD_date', section=9, block=block, label='Date', attachToRefresh=1, command='mc.about(currentDate=1)')
        block = mc.headsUpDisplay(nextFreeBlock=9)
        mc.headsUpDisplay('spp_animHUD_staff', section=9, block=block, label='Name', attachToRefresh=1, command='mc.optionVar(q="sppAnimHUDUserName")')
        block = mc.headsUpDisplay(nextFreeBlock=9)
        mc.headsUpDisplay('spp_animHUD_corp' ,section=9 ,block=block ,label='Corp' ,attachToRefresh=1 ,command='mc.optionVar(q="sppAnimHUDUserCorp")')
        block = mc.headsUpDisplay(nextFreeBlock=5)
        mc.headsUpDisplay('spp_animHUD_sceneFileName', section=5, block=block, label='Scene', attachToRefresh=1, command='mc.file(q=1 ,sn=1 ,shn=1)')

        


def spp_animHUD_displayFps():
    time = mc.currentUnit(q=1, time=1)
    if time == "film":
        return "24fps"
    elif time == "ntsc":
        return "30fps"
    else:
        return mc.currentUnit(q=1, time=1)


def spp_animHUD_camFocalLength():
    focaLength=0
    try:
        whichPanel = mc.getPanel(withFocus=1)
        nameCamera = mc.modelPanel(whichPanel,q=1, camera=1)
        focalLength = mc.getAttr(nameCamera + ".focalLength")
    except:
        focalLength='cam'
    return focalLength



def spp_animHUD_runningTime():
    animationStartFrame = mc.playbackOptions(q=1, min=1)
    animationEndFrame = mc.playbackOptions(q=1, max=1)
    runningTime = animationEndFrame - animationStartFrame + 1
    form = ' %d - %d ( %d )' % (int(animationStartFrame),int(animationEndFrame),int(runningTime))
    return form







# ---------------------------------------------------------------------------------------------
# AssetA_gui.py
# ---------------------------------------------------------------------------------------------
#
# Source by J.H.M MINstudio
#
# ---------------------------------------------------------------------------------------------


def clearUI():
    
    # get windows list
    UI_list = mc.lsUI(windows = True)
    
    # close all windows without MainWindow
    for del_UI in UI_list:
        if not del_UI == 'MayaWindow':
            mc.deleteUI(del_UI)    
    
    # remove all window preferences
    mc.windowPref(removeAll = 1)
    
    # zoom to selected object
    viewcamera = ['frontShape', 'perspShape', 'sideShape', 'topShape']
    
    for camerallist in viewcamera:
        mc.viewFit(camerallist)
    
    # Edit shaded mode to boundingBox
    viewport = ['Persp View', 'Top View', 'Front View', 'Side View']
    
    for panellist in viewport:
        panelmode = mc.getPanel(withLabel = panellist)
        mc.modelEditor(panelmode, edit = True, displayAppearance = 'boundingBox')
        
    # set panel Layout to Single Perspective View
    mel.eval('setNamedPanelLayout("Single Perspective View")')
    
    # open the 'Save Scene As'
    mc.SaveSceneAs()




#spp_animHUD_user()
spp_animHUD()
