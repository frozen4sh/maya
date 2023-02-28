from pymel.core import *

template = uiTemplate('ExampleTemplate', force=True)
template.define(button, width=100, height=40, align='left')
template.define(frameLayout, borderVisible=True, labelVisible=False)

with window(menuBar=True,menuBarVisible=True) as win:
    # start the template block
    with template:
        with columnLayout( rowSpacing=5 ):
            with frameLayout():
                with columnLayout():
                    button(label='One')
                    button(label='Two')
                    button(label='Three')
            with frameLayout():
                with optionMenu():
                    menuItem(label='Red')
                    menuItem(label='Green')
                    menuItem(label='Blue')
# add a menu to an existing window
with win:
    with menu():
        menuItem(label='One')
        menuItem(label='Two')
        with subMenuItem(label='Sub'):
            menuItem(label='A')
            menuItem(label='B')
        menuItem(label='Three')
