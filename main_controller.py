'''
Created on 8/04/2014

@author: glenn
'''
# for diagnostics
import sys
def funcname():
    return sys._getframe(1).f_code.co_name

class MainController(object):
    '''
    classdocs
    '''
    def __init__(self, model=None):
        '''
        Constructor
        '''
        self._model = model
        
    # The model can't be passed to the constructor because of the
    # initialisation order so this method is provided instead.    
    def setFitter(self, fitter):
        self._model = fitter
        #self._zw = fitter.widget()
         
    def setZincWidget(self, zw):
        self._zw = zw

        if __debug__:
            import os
            os.chdir("test")
            self.open_file("abi_femur.json")
            os.chdir("..")
           
    def on_closed(self):
        print funcname()
    #
    # File Menu
    #
    
    def open_file(self, path):
        print path
        self._model.load_problem(path)
        self.view_all()
        
    def load_nodes(self, path):
        print funcname()

    def load_elements(self, path):
        print funcname()

    def load_data(self, path):
        print funcname()
        
    def save_file(self, path):
        print funcname(), path
        self._model.save_problem(path)
        
    #
    # View menu
    #
    
    def view_all(self):
        self._zw.viewAll()
    
    #
    # Selection mode
    #
    
    def on_select_data(self):
        print funcname()
        self._zw.setSelectModeData()
        self._zw.setSelectionModeAdditive(True)
        
    def on_select_faces(self):
        print funcname()
        self._zw.setSelectModeElement()
        self._zw.setSelectionModeAdditive(True)
    
    #
    # Registration
    #
    
    def mirror(self, axis):
        print funcname(), axis
        convert = {'x': 0, 'y': 1, 'z': 2}
        self._model.data_mirror(convert[axis])
        #self.view_all()
    
    def register_automatic(self):
        print funcname()
        self._model.register_automatic()
        