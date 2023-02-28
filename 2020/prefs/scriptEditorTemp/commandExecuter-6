import pymel.core as pm
class BaseWithMayaUI():
    def __init__(self):
        self.windowName='BaseWithMayaUI00'
        if pm.window(self.windowName, exists=True):
            pm.deleteUI(self.windowName, window=True)
        self.UI()
    def UI(self):
        with pm.window(self.windowName,menuBar=True,menuBarVisible=True,title='BASE_UI',w=400) as win:
            with pm.columnLayout():
                pm.button('topAbutton',label=u'BASE BUTTON',w=400,c=lambda _:self.run('value'))
                pm.textField('topAtextfield',w=400)
        pm.showWindow(win)
    def run(self,test):
        print test
        pm.textField('topAtextfield',e=1,text='run')
a = BaseWithMayaUI()
