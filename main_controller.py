
from tools.diagnostics import funcname
from functools import partial

class Action(object):
    """
    class defining a UI action with undo and redo
    """
    def __init__(self, doFunc):
        assert(callable(doFunc))
        self._do = doFunc
        # do the action
        self.do()
    
    def do(self):
        # overwrites the undo slot with the result of the do function
        undo = self._do()
        if callable(undo):
            self.undo = undo
    
    def undo(self):
        raise NotImplementedError("Can't undo")

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
        self._redoStack = list()
        
        
    # The model can't be passed to the constructor because of the
    # initialisation order so this method is provided instead.    
    def set_fitter(self, fitter):
        self._model = fitter
        fitter.observable.observe('region', self._on_model_changed)
        fitter.observable.observe('selectMode', self._on_model_changed)
        fitter.observable.observe('hmfProblemDefined', self._on_model_changed)

    def set_view(self, view):
        self._view = view
         
    def set_zinc_widget(self, zw):
        self._zw = zw
        
        self._zw.graphicsPicked.connect(self._on_graphics_selected)

        if __debug__:
            import os
            os.chdir("test")
            self._model.setPointSize(1) # this should be in the json
            self.open_file("abi_femur.json")
#             self.open_file("test_2d_fit.json")
            os.chdir("..")

            # for testing register the mesh to the mirrored the data 
            #f = self._model
            self.data_mirror('y') # mirror in y axis
            self.register_automatic(translate=True, rotate=False, scale=False)
            self.register_automatic(translate=True, rotate=True, scale=False)
            self._zw.viewAll()
            
            # convert to cubic
#            self.convert_to_cubic()
            # hide initial mesh via UI
            
            #self._view.mb.data_view.checked = False
            for name in [
                         #'view_data',
                         #'view_reference', 'view_fitted',
                         'cubic_data', 'cubic_reference', 'cubic_reference']:
                vobj = self._view.find(name)
                vobj.checked = False
                vobj.triggered()
            
            
#             self.view_data_cubic(True)
#             self.view_reference_cubic(False)
#             self.view_fitted_cubic(True)
#             
#             self.project()
#             self.fit()
            
#             self.convert_to_cubic()
#             self.open_file("test_2d_fit.json")
#             # hide initial mesh
#             self.view_data(True)
#             self.view_reference(True)
#             self.view_fitted(True)
#             self.view_data_cubic(True)
#             self.view_reference_cubic(False)
#             self.view_fitted_cubic(True)
    
    def set_status_message(self, msg):
        w = self._view.find("status")
        w.text = msg

    def _on_graphics_selected(self, item, fieldDomainType):
        self._model.graphics_selected(item, fieldDomainType)
                   
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

    def _create_action(self, doFunc):
        a = Action(doFunc)
        self._undoStack.append(a)
        del self._redoStack[:]
        w = self._view.find("redo")
        w.enabled = False

        w = self._view.find("undo")
        w.enabled = True


    def undo(self):
        try:
            #command = self._undoStack.pop()
            action = self._undoStack.pop()
            action.undo()
            w = self._view.find("undo")
            w.enabled = len(self._undoStack) != 0
            self._redoStack.append(action)
            w = self._view.find("redo")
            w.enabled = len(self._redoStack) != 0
        except IndexError:
            return

    def redo(self):
        try:
            action = self._redoStack.pop()
            action.do()
            self._undoStack.append(action)
            w = self._view.find("undo")
            w.enabled = len(self._undoStack) != 0
            self._redoStack.append(action)
            w = self._view.find("redo")
            w.enabled = len(self._redoStack) != 0
        except IndexError:
            return
        
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

    def select_data(self, additive=False):
        self._zw.setSelectModeData()
        self._zw.setSelectionModeAdditive(additive)
        self._model.storeSelectedFaces()

    def select_faces(self):
        self._zw.setSelectModeFaces()
        self._zw.setSelectionModeAdditive(True)

    def select_nodes(self, additive=False):
        self._zw.setSelectModeNodes()
        self._zw.setSelectionModeAdditive(additive)
        
    def select_no_mode(self):
        self._model.setFitMode(self._model.FIT_NONE)

    def select_manual_reg(self):
        print funcname()
        self._zw.setSelectModeNodes()
        self._zw.setSelectionModeAdditive(False)
        self._model.hostmesh_register_setup()

    def register_manual(self, displacement_penalty):
        if len(displacement_penalty) == 0:
            displacement_penalty = 0
        else:
            displacement_penalty = float(displacement_penalty)
        self._model.hostmesh_register_fit(displacement_penalty)


    #
    # Registration
    #
    
    def data_mirror(self, axis):
        convert = {'x': 0, 'y': 1, 'z': 2}
        
        #undo = self._model.data_mirror(convert[axis], about_centroid=True)
        self._create_action(partial(self._model.data_mirror, convert[axis], about_centroid=True))
        
    def register_automatic(self, translate, rotate, scale):
        #undo = self._model.register_automatic(translate, rotate, scale)
        self._create_action(partial(self._model.register_automatic, translate, rotate, scale))


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
    
    def _on_model_changed(self, change):
        print funcname(), 'changed:',  change['name'], 'new value:', change['value'] 
        if change['name'] == 'region':
            region = change['value']
            if __debug__: print funcname(), region.getName()
            self._zw.setCurrentRegion(region)
#         elif change['name'] == 'statusMessage':
#             self.set_status_message(change['value'])
        elif change['name'] == 'selectMode':
            mode = change['value']
            zw = self._zw
            m = self._model
            if mode == m.SelectModeData:
                zw.setSelectModeData()
                self.set_status_message("Select a data point")
            elif mode == m.SelectModeNodes:
                zw.setSelectModeNodes()
                self.set_status_message("Select a node")
            elif mode == m.SelectModeFaces:
                zw.setSelectModeFaces()
                self.set_status_message("Select a face")                
            elif mode == None:
                zw.setSelectModeNone()
                self.set_status_message("")
        elif change['name'] == 'hmfProblemDefined':
            defined = change['value']
            w = self._view.find('register_manual')
            w.enabled = defined
            
            
        
