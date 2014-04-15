import os
import sys

import tools.mesh as mesh
import numpy as np

try:
    from PyQt4 import QtGui, QtCore
except ImportError:
    from PySide import QtGui, QtCore

def funcname():
    return sys._getframe(1).f_code.co_name

# Create the UI file using:
#     pyside-uic fitting.ui -o fitting_ui.py
from fitting_ui import Ui_DlgFitting

from fitter import Fitter

from opencmiss.zinc.context import Context

#from fitting_tools import *

def _handleError(ex):
    m = QtGui.QMessageBox(QtGui.QMessageBox.Warning, "Error", str(ex))
    m.exec_()
    
class FitDlg(QtGui.QWidget):
    def __init__(self, parent=None):
        super(FitDlg, self).__init__(parent)
        
        # Using composition to include the visual element of the GUI.
        self.ui = Ui_DlgFitting()
        self.ui.setupUi(self)
        # self.setWindowIcon(QtGui.QIcon("cmiss_icon.ico"))
        
        context = Context("Fitter")
        self.ui._zincWidget.setContext(context)
        self._model = Fitter(context)
        
        self.ui._zincWidget.setContext(self._model.context())
        self.ui._zincWidget.setSelectModeNone()
        
        self.ui._zincWidget.graphicsInitialized.connect(self.postGLInitialise)
        
        self.ui.btnLoadMesh.clicked.connect(self.on_load_mesh)
        self.ui.btnLoadData.clicked.connect(self.on_load_data)
        self.ui.btnSelFaces.clicked.connect(self.on_select_faces)
        self.ui.btnSelData.clicked.connect(self.on_select_data)
        self.ui.btnProject.clicked.connect(self.on_project)
        self.ui.btnFit.clicked.connect(self.on_fit)
        self.ui.rbFitted.clicked.connect(self.on_fitmodel)
        self.ui.rbReference.clicked.connect(self.on_refmodel)
    
    def postGLInitialise(self):
#         # It seems to work OK if this isn't called.               
#         self.ui._zincWidget.viewAll()
#         #self.ui._zincWidget.defineStandardGlyphs() # already done by initializeGL
#         self.ui._zincWidget.defineStandardMaterials()

        # from the volume_fitting example
#         root_region = self._context.getDefaultRegion()
#         self._readModel(root_region)
#         self._create2DElementGroup(root_region)
#         self._readModelingPoints(root_region)
#         self._defineStoredFoundLocation(root_region)
#         self._defineOptimisationFields(root_region)
#         self._defineOptimisation(root_region)
#         self._createGraphics(root_region)

        
        # for testing - this would normally be done by a user action
        self._load_mesh()
        # self._load_data()
        
    # for testing
    def _load_mesh(self):
        import ICP
        data = mesh.read_txtnode("abi_femur_head_500.ascii")
        
        # reflect data in in y axis to match mesh
        # FIXME: there needs to be a GUI for this        
        d = np.array(data)
        print d
        r = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        xdim = d.shape[0]
        ones = np.ones((xdim, 1))
        h = np.hstack([d, ones])
        print h.shape
        d = h.dot(r)[:, 0:3]
        print d

        mesh.data_points(self._model.context(), d.tolist())
        nodes = mesh.read_txtnode("abi_femur_head.node.txt")
        
        # move the nodes near to the data
        T, trans_points = ICP.fitDataRigidEPDP(nodes, d)
        
        elems = mesh.read_txtelem("abi_femur_head.elem.txt")

        coords = 'coordinates'
        ref_coords = 'reference_coordinates'
        
        mesh.linear_mesh(self._model.context(), trans_points.tolist(), elems,
                         coordinate_field_name=coords)
        
        # Load the mesh again, this time merging with the previous mesh
        # and renaming the coordinate field to reference_coordinates.
        # This adds another set of coordinates at each node.
        mesh.linear_mesh(self._model.context(), trans_points.tolist(), elems,
                         coordinate_field_name=ref_coords, merge=True)
        
#         # for debugging
#         self._model.context().getDefaultRegion().writeFile("junk_region.exreg")
        
        # The datapoint graphics don't appear until the rest of the mesh is loaded,
        # FIXME: Not sure why that is.
        mesh.createDatapointGraphics(self._model.context(), datapoints_name='data')
        mesh.createNodeGraphics(self._model.context(), nodes_name='nodes',
                                 coordinate_field_name=coords)
        mesh.createSurfaceGraphics(self._model.context(),
                                   surfaces_name='surfaces',
                                   lines_name='lines',
                                   coordinate_field_name=coords)
         
        self.ui._zincWidget.viewAll()
        
        self._model.meshLoaded()


    # for testing        
    def _load_data(self):
        data = mesh.read_txtnode("abi_femur_head_500.ascii")
        mesh.data_points(self._model.context(), data)  # , colour="blue")

        self.ui._zincWidget.viewAll()

    #
    # UI Button click handlers
    #         
    def on_load_mesh(self):
        try:
            files = QtGui.QFileDialog.getOpenFileNames(
                    self, "Select model file(s)", os.getcwd(), "CmGUI files (*.ex*)")
            
            # exclude the last item in the files list because it is
            # the filetype filter
            files, = files[:len(files) - 1]
            
#             # load the mesh
#             refcoords, coords = load_mesh(self._model.region(), files)
#             self._model.setReferenceCoordinates(refcoords)
#             self._model.setCoordinates(coords)
            raise NotImplementedError()
            
            self.ui._zincWidget.viewAll()
            
        except Exception as e:
            if __debug__: print e
            _handleError(e)         

    def on_load_data(self):
        try:
            files = QtGui.QFileDialog.getOpenFileNames(
                    self, "Select data file(s)", os.getcwd(), "CmGUI files (*.ex*)")
            
            # exclude the last item in the files list because it is
            # the filetype filter
            files, = files[:len(files) - 1]
            
#             # load the data
#             data = load_data(self._model.region(), files)
#             self._model.setDataCoordinates(data)
            raise NotImplementedError()
            
        except Exception as e:
            print e
            _handleError(e)         

    def on_select_faces(self):
        # Configure the UI to be in "face selection mode"
        self.ui._zincWidget.setSelectModeElement()
        self.ui._zincWidget.setSelectionModeAdditive(True)
    
    def on_select_data(self):
        self.ui._zincWidget.setSelectModeData()
        self.ui._zincWidget.setSelectionModeAdditive(True)
        
    def on_project(self):
        self._model.project()
        
    def on_fit(self):
        self._model.fit()
        
    def on_refmodel(self):
        self._model.show_reference()

    def on_fitmodel(self):
        self._model.show_fitted()
    
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = FitDlg()
    window.show()
    app.exec_()
