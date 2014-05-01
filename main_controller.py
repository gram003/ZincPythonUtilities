
from tools.diagnostics import funcname

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
    # View type
    #
    
    def view_reference(self, state):
        self._model.show_reference(state)
    
    def view_fitted(self, state):
        self._model.show_fitted(state)

    #
    # Selection mode
    #

    def select_data(self):
        self._zw.setSelectModeData()
        self._zw.setSelectionModeAdditive(True)

    def select_faces(self):
        self._zw.setSelectModeElement()
        self._zw.setSelectionModeAdditive(True)

    #
    # Registration
    #

    def mirror(self, axis):
        print funcname(), axis
        convert = {'x': 0, 'y': 1, 'z': 2}
        self._model.data_mirror(convert[axis], about_centroid=True)

    def register_automatic(self, translate, rotate, scale):
        print funcname(), translate, rotate, scale
        self._model.register_automatic(translate, rotate, scale)

    def register_manual(self):
        # least squares fit between 3 or more points on each body
        pass
    
    #
    # Fitting
    #
    
    def project(self):
        self._model.project()

    def fit(self):
        self._model.fit()
