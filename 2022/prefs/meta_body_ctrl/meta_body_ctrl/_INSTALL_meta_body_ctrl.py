import os, sys
from maya import cmds
import shutil

sys.dont_write_bytecode = True
scriptName = 'mgMHBodyCtrl'
annotation_string = 'metahuman body ctrl creator'
def create_shelf_btn(scriptFile = '', script_icon = '', scriptName = '', annotation_string = ''):
    command_str = 'import imp\n' +  scriptName + ' = imp.load_source(\'\', ' + '\'' + scriptFile + '\')'
    current_shelf = cmds.shelfTabLayout('ShelfLayout', query=1, selectTab=1)

    names = cmds.shelfLayout(current_shelf, query=True, childArray=True) or []
    labels = [cmds.shelfButton(n, query=True, label=True) for n in names]

    # delete existing button
    if scriptName in labels:
        index = labels.index(scriptName)
        cmds.deleteUI(names[index])

    cmds.shelfButton(p=current_shelf,
				annotation=annotation_string,
    				 label=scriptName,
    				 c=command_str,
    				 sourceType='python',
    				 style='iconOnly',
    				 image=script_icon)

def onMayaDroppedPythonFile(*args):
    user_dir = cmds.internalVar(userScriptDir=1)
    outputPath = user_dir + 'madguru_tools'
    if not os.path.exists(outputPath):
        os.mkdir(outputPath)
        print('Created ' + outputPath)

    sourcePath = os.path.split(__file__)[0]
    file_list = os.listdir(sourcePath)

    python_file = ''
    script_icon = ''
    for current_file in file_list:
        if not '_INSTALL_' in current_file:
            if not os.path.isdir(sourcePath + '/' + current_file):
                shutil.copyfile(sourcePath + '/' + current_file, outputPath + '/' + current_file)
                print('Copied ' + sourcePath + '/' + current_file + ' to ' + outputPath + '/' + current_file)
            else:
                if os.path.isdir(outputPath + '/' + current_file):
                    shutil.rmtree(outputPath + '/' + current_file)
                shutil.copytree(sourcePath + '/' + current_file, outputPath + '/' + current_file, symlinks = False, ignore = None)
                print('Copied ' + sourcePath + '/' + current_file + ' to ' + outputPath + '/' + current_file)
            if '.py' in current_file:
                python_file = current_file
            if '.png' in current_file:
                script_icon = current_file

    create_shelf_btn(scriptFile = outputPath + '/' + python_file, script_icon = outputPath + '/' + script_icon, scriptName = scriptName, annotation_string = annotation_string)