
from tools.diagnostics import funcname

class MainController(object):
    '''
    classdocs
    '''
        
    def __init__(self):#, model=None):
        '''
        Constructor
        '''
        #self._model = model
        self._undoStack = list()
        
        
    # The model can't be passed to the constructor because of the
    # initialisation order so this method is provided instead.    
    def setFitter(self, fitter):
        self._model = fitter
        fitter.observable.observe('region', self._onCurrentRegionChanged)
         
    def setZincWidget(self, zw):
        self._zw = zw

        if __debug__:
            import os
            os.chdir("test")
            #self.open_file("abi_femur.json")
            self.open_file("test_2d_fit.json")
            self._model.setPointSize(1) # this should be in the json
            os.chdir("..")
            # register the mesh to the mirrored the data 
#             f = self._model
#             f.register_automatic(translate=True, rotate=False, scale=False)
#             f.data_mirror(1) # mirror in y axis
#             f.register_automatic(translate=True, rotate=True)
            
            self._zw.viewAll()
#             # convert to cubic
#             self.convert_to_cubic()
#             # hide initial mesh
#             self.view_data(False)
#             self.view_reference(False)
#             self.view_fitted(False)
#             self.view_data_cubic(True)
#             self.view_reference_cubic(False)
#             self.view_fitted_cubic(True)
#             
#             self.project()
#             self.fit()
            
            self.convert_to_cubic()
            # hide initial mesh
            self.view_data(True)
            self.view_reference(True)
            self.view_fitted(True)
#             self.view_data_cubic(True)
#             self.view_reference_cubic(False)
#             self.view_fitted_cubic(True)
                   
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
    # Edit menu
    #

    def undo(self):
        try:
            command = self._undoStack.pop()
        except IndexError:
            return

        command()
        
    #
    # View menu
    #
    
    def view_all(self):
        self._zw.viewAll()
    
    #
    # View type
    #
    
    def view_data(self, state):
        self._model.show_data(state)

    def view_reference(self, state):
        self._model.show_initial(state)
    
    def view_fitted(self, state):
        self._model.show_fitted(state)

    def view_data_cubic(self, state):
        self._model.show_data_cubic(state)

    def view_reference_cubic(self, state):
        self._model.show_reference_cubic(state)
    
    def view_fitted_cubic(self, state):
        self._model.show_fitted_cubic(state)

    #
    # Selection mode
    #

    def select_data(self):
        self._zw.setSelectModeData()
        self._zw.setSelectionModeAdditive(True)

    def select_nodes(self):
        self._zw.setSelectModeNode()
        self._zw.setSelectionModeAdditive(True)
    def select_manual_reg(self):
        print funcname()
        self._zw.setSelectModeNode()
        self._zw.setSelectionModeAdditive(False)
        self._model.hostmesh_register_setup()

    def register_manual(self):
        self._model.hostmesh_register_fit()

    def select_faces(self):
        self._zw.setSelectModeFace()
        self._zw.setSelectionModeAdditive(True)

    #
    # Registration
    #

    def mirror(self, axis):
        convert = {'x': 0, 'y': 1, 'z': 2}

        undo = self._model.data_mirror(convert[axis], about_centroid=True)
        self._undoStack.append(undo)

    def register_automatic(self, translate, rotate, scale):
        undo = self._model.register_automatic(translate, rotate, scale)
        self._undoStack.append(undo)

    def register_manual(self):
        # least squares fit between 3 or more points on each body
        pass
    
    #
    # Fitting
    #

    def convert_to_cubic(self):
        self._model.convert_to_cubic()
        # how to set the active region?

    def project(self):
        self._model.project()

    def fit(self, alpha, beta):
        if len(alpha) == 0:
            alpha = 0
        if len(beta) == 0:
            beta = 0
        self._model.fit(float(alpha), float(beta))
        
    #
    # Signals
    #
    
    def _onCurrentRegionChanged(self, change):
        assert(change['name'] == 'region')
        region = change['value']
        if __debug__: print funcname(), region.getName()
        self._zw.setCurrentRegion(region)
        
