import os
import sys

from opencmiss.zinc.context import Context
from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field, FieldFindMeshLocation, FieldGroup
from opencmiss.zinc.optimisation import Optimisation

import tools.mesh as mesh
import numpy as np

try:
    from PySide import QtGui, QtCore
except ImportError:
    from PyQt4 import QtGui, QtCore

def funcname():
    return sys._getframe(1).f_code.co_name

# Create the UI file using:
#     pyside-uic fitting.ui -o fitting_ui.py
from fitting_ui import Ui_DlgFitting

#from fitting_tools import *

# Hungarian notation
# While use of this is generally frowned upon it could be useful
# in zinc python code because the underlying objects are strongly
# typed.
# s nodeset
# m mesh
# g group
# e element
# n node
# f field
# 1,2,3 dimension, e.g. m2 = 2d mesh

def _handleError(ex):
    m = QtGui.QMessageBox(QtGui.QMessageBox.Warning, "Error", str(ex))
    m.exec_()

class Model(object):
    # selection modes
    Faces = 1
    Nodes = 2
    Data = 4
    
    def __init__(self, zincWidget):
        object.__init__(self)
        
        self._context = Context("Fit")
        self._zw = zincWidget

    def context(self):
        return self._context
    
    def region(self):
        return self._context.getDefaultRegion()
    
    def setReferenceCoordinates(self, x):
        self._refcoords = x
    
    def setCoordinates(self, x):
        self._coords = x
    
    def setDataCoordinates(self, x):
        self._datacoords = x
        
    def setSelectMode(self, mode):
        self._selectMode = mode
        
    def meshLoaded(self):
        region = self.context().getDefaultRegion()
        fm = region.getFieldmodule()
        self._coordinates = fm.findFieldByName('coordinates')
        self._reference_coordinates = fm.findFieldByName('reference_coordinates')
        self._data_coordinates = fm.findFieldByName('data_coordinates')
        # self._data_coordinates_group = self._data_coordinates.castGroup()
        
        print funcname()
        print "self._coordinates", self._coordinates
        print "self._reference_coordinates", self._reference_coordinates
        print "self._data_coordinates", self._data_coordinates
        # print self._data_coordinates_group
        
        self._copyField(self._coordinates)
        
    def _copyField(self, field):
        pass
        
    def project(self):
        # project selected data points onto selected faces
#         self._create2DElementGroup(root_region)
#         self._readModelingPoints(root_region)
#         self._defineStoredFoundLocation(root_region)
#         self._defineOptimisationFields(root_region)
#         self._defineOptimisation(root_region)
#         self._createGraphics(root_region)

        # Create a face group
        region = self.context().getDefaultRegion()
        fm = region.getFieldmodule()
        mesh2d = fm.findMeshByDimension(2)
        self._mesh2d = mesh2d
        # m2 = mesh2d # should use m2 as the Hungarian prefix
        self._gefFaces = fm.createFieldElementGroup(mesh2d)
        print "self._gefFaces", self._gefFaces
        # Get a mesh group to contain the selected faces
        gmFaces = self._gefFaces.getMeshGroup()
        print "gmFaces", gmFaces 

        # outsideFaceIds = [3, 8, 13, 18, 23, 27]
        print "self._mesh2d", self._mesh2d

        # Create a data point group to contain the selected datapoints
        sData = fm.findNodesetByName('datapoints')
        print "sData", sData
        # The FieldNodeGroup is the "main" object containing the data,
        # but the NodesetGroup has the add/remove api.
        self._gnfData = fm.createFieldNodeGroup(sData)
        gsData = self._gnfData.getNodesetGroup()
        
        # get the selection field        
        # scene = region.getScene()
#         selectionGroup = scene.getSelectionField()
        self._selectionGroup = self._zw.getSelectionGroup()
        
        # copy the selected faces to the _outsideMesh group
        gefSelection = self._selectionGroup.getFieldElementGroup(mesh2d)
        meshgroup = gefSelection.getMeshGroup()
        el_iter = meshgroup.createElementiterator()
        print "Adding elements to face group" 
        count = 0
        element = el_iter.next()
        while element.isValid():
            elem_id = element.getIdentifier()
            print elem_id,
            gmFaces.addElement(mesh2d.findElementByIdentifier(elem_id))
            element = el_iter.next()
            count += 1
        print
        
        # for developing just use a few faces
        if count == 0:
            elist = [int(x) for x in "34 77 158".split()]
            for eindex in elist:
                gmFaces.addElement(mesh2d.findElementByIdentifier(eindex))
        
        # get selected data points
        nodegroup = self._selectionGroup.getFieldNodeGroup(sData)
        gsDataSelected = nodegroup.getNodesetGroup()
        dp_iter = gsDataSelected.createNodeiterator()
        print "Adding points to data group"
        count = 0
        node = dp_iter.next()
        while node.isValid():
            node_id = node.getIdentifier()
            print node_id,
            gsData.addNode(gsDataSelected.findNodeByIdentifier(node_id))
            node = dp_iter.next()
            count += 1
        print

        if count == 0:
            # for developing use data points directly from the main datapoints set
            dlist = [int(x) for x in "24 26 113 132 157 165 200 228 229 254 269 281 304 312 349 355 374 389 406 427 454 469 490 508 520 533 552".split()]
            for dindex in dlist:
                gsData.addNode(sData.findNodeByIdentifier(dindex))
        
        print "self._selectionGroup", self._selectionGroup
        print "gsData", gsData
        # nodeGroup.
        # self._selectionGroup.getFieldNodeGroup(datapoints).addNode(228)
        # self._selectionGroup.addNode(228)

        self._defineStoredFoundLocation(region, gsData, gmFaces)


    def _defineStoredFoundLocation(self, region, gsData, gmFaces):
        '''
        Create a field which dynamically finds the nearest location to the scaled_data_coordinates on the 1-D mesh and 
        define a field for storing these locations so they are not recalculated during optimisation
        '''
        print funcname()
        fm = region.getFieldmodule()
        
        mesh2d = fm.findMeshByDimension(2)
                
        data_coordinates = fm.findFieldByName('data_coordinates')
        coordinates = fm.findFieldByName('coordinates')

#         self._found_location = fm.createFieldFindMeshLocation(self._data_coordinates, self._coordinates, self._outsideMesh)
        print data_coordinates
        print "self._coordinates", self._coordinates
        print "coordinates", coordinates
        print "gmFaces", gmFaces
        
        self._found_location = fm.createFieldFindMeshLocation(data_coordinates, coordinates, gmFaces)
        self._found_location.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_NEAREST)
        self._stored_location = fm.createFieldStoredMeshLocation(mesh2d)
         
#         dataNodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
#         boxpointsNodeGroup = self._boxpoints_group.getFieldNodeGroup(dataNodeset)
#         self._boxpoints_nodeset = boxpointsNodeGroup.getNodesetGroup()

        # region.writeFile("junk_region.exreg")

        dataNodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        print dataNodeset
        print "gsData", gsData
        gfDataCoords = fm.findFieldByName('data_coordinates').castGroup()
        print "gfDataCoords", gfDataCoords
        y = data_coordinates.castGroup()
        print "data_coordinates.castGroup", gfDataCoords, y
        
#         self._gnfData = gfDataCoords.getFieldNodeGroup(dataNodeset)
#         #self._datapoints_nodeset = datapointsNodeGroup.getNodesetGroup()
#         print "self._gnfData", self._gnfData

#         
#         masterNodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
#         gausspointsNodeGroup = self._gauss_points_group.getFieldNodeGroup(masterNodeset)
#         self._gauss_points_nodeset = gausspointsNodeGroup.getNodesetGroup()
#         nodeTemplate = self._boxpoints_nodeset.createNodetemplate()
#         nodeTemplate.defineField(self._stored_location)
#         node_iter = self._boxpoints_nodeset.createNodeiterator()
#         cache = fm.createFieldcache()
#         node = node_iter.next()
#         while node.isValid():
#             cache.setNode(node)
#             element, xi = self._found_location.evaluateMeshLocation(cache, 2)
#             if element.isValid():
#                 node.merge(nodeTemplate)
#                 self._stored_location.assignMeshLocation(cache, element, xi)
#             
#             node = node_iter.next()
        sData = fm.findNodesetByName('datapoints')
        print "sData", sData
#         gnfSelectedData = self._selectionGroup.getFieldNodeGroup(sData)
#         print "gnfSelectedData", gnfSelectedData
#         gsSelectedData = gnfSelectedData.getNodesetGroup()
#         dp_iter = gsSelectedData.createNodeiterator()

        dp_iter = gsData.createNodeiterator()

        dataTemplate = sData.createNodetemplate()
        dataTemplate.defineField(self._stored_location)
        cache = fm.createFieldcache()
        datapoint = dp_iter.next()
        print "Projecting data..."
        while datapoint.isValid():
            print datapoint.getIdentifier(),
            cache.setNode(datapoint)
            element, xi = self._found_location.evaluateMeshLocation(cache, 2)
            if element.isValid():
                datapoint.merge(dataTemplate)
                self._stored_location.assignMeshLocation(cache, element, xi)
             
            datapoint = dp_iter.next()
        print
        
        self._projected_coordinates = fm.createFieldEmbedded(self._coordinates, self._stored_location)
        self._error_vector = fm.createFieldSubtract(self._projected_coordinates, self._data_coordinates)
        
        self._createProjectionGraphics()
        
    def _createProjectionGraphics(self):
        materials_module = self.context().getMaterialmodule()
        materials_module.defineStandardMaterials()
        blue = materials_module.findMaterialByName('blue')

        default_region = self.context().getDefaultRegion()
        # Get the scene for the default region to create the visualisation in.
        scene = default_region.getScene()
        
        # We use the beginChange and endChange to wrap any immediate changes and will
        # streamline the rendering of the scene.
        scene.beginChange()
        
        # projected points
        proj = scene.createGraphicsPoints()
        proj.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        proj.setCoordinateField(self._projected_coordinates)
        # consider only the selected data points group
        proj.setSubgroupField(self._gnfData)
        proj.setMaterial(blue)
        attr = proj.getGraphicspointattributes()
        attr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        attr.setBaseSize([1])
        
        # error lines
        err = scene.createGraphicsPoints()
        err.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        err.setCoordinateField(self._projected_coordinates)
        err.setSubgroupField(self._gnfData)
        attr = err.getGraphicspointattributes()
        attr.setGlyphShapeType(Glyph.SHAPE_TYPE_LINE)
        attr.setOrientationScaleField(self._error_vector)
        attr.setScaleFactors([-1, 0, 0])
        
        scene.endChange()
        
    def fit(self):
        
        region = self.context().getDefaultRegion()
        
        region.writeFile("before.exregi")
        
#         self._defineOptimisationFields(root_region)
#     def _defineOptimisationFields(self, region):
#         '''
#         Define the outside surface fit objective field and the volume smoothing
#         objective field.
#         '''
        fm = region.getFieldmodule()
        # self._projected_coordinates = fm.createFieldEmbedded(self._coordinates, self._stored_location)
        # self._error_vector = fm.createFieldSubtract(self._projected_coordinates, self._data_coordinates)
        data_nodeset_group = self._gnfData.getNodesetGroup()
        self._outside_surface_fit_objective = fm.createFieldNodesetSumSquares(self._error_vector, data_nodeset_group)
        print "self._outside_surface_fit_objective", self._outside_surface_fit_objective
        
        # Diagnostics: print out data point ids
        dp_iter = data_nodeset_group.createNodeiterator()
        node = dp_iter.next()
        while node.isValid():
            node_id = node.getIdentifier()
            print node_id,
            node = dp_iter.next()
        print
        
        # Diagnostics: compute RMS error
        field = self._outside_surface_fit_objective
        cache = fm.createFieldcache()
        dp_iter = data_nodeset_group.createNodeiterator()
        dp = dp_iter.next()
        while dp.isValid():
            cache.setNode(dp)
            result, outValues = field.evaluateReal(cache, 3)
            print result, np.sum(outValues)
            dp = dp_iter.next()
            
        # Diagnostics write out node file.
        # use createStreamInformation to only write out nodes
        # use region.writeFile()


#         gauss_coordinates = fm.createEmbedded(self._coordinates, self._gauss_location)
#         xi = fm.findFieldByName('xi')
#         dX_dxi = fm.createFieldGradient(self._reference_coordinates, xi)
#         dV = fm.createFieldDeterminant(dX_dxi)
#          
#         displacement = fm.createFieldSubtract(self._coordinates, self._reference_coordinates)
#         two_fields = [fm.createFieldComponent(displacement, 1), fm.createFieldComponent(displacement, 2)]
#         displacement_xy = fm.createFieldConcatenate(two_fields)
#         displacement_gradient = fm.createFieldGradient(displacement_xy, self._reference_coordinates)
#         gauss_displacement_gradient = fm.createFieldEmbedded(displacement_gradient, self._gauss_location)
#         gauss_dV = fm.createFieldEmbedded(dV, self._gauss_location)
#         gauss_weight_dV = fm.createFieldMultiply(self._gauss_weight, gauss_dV)
#         alpha = fm.createFieldConstant([20])
#         weight = fm.createFieldMultiply(gauss_weight_dV, alpha)
#         scaled_gauss_displacement_gradient = fm.createFieldMultiply(gauss_displacement_gradient, weight)
#          
#         self._volume_smoothing_objective = fm.createFieldNodesetSumSquares(scaled_gauss_displacement_gradient, self._gauss_points_nodeset)       

#         self._defineOptimisation(root_region)
#     def _defineOptimisation(self, region):
#         '''
#         Define the optimisation field.  Set a least squares quasi newton
#         optimisation method for one iteration.  We also add the objective field
#         and independent field to the optimisation
#         '''
            
        self._opt = fm.createOptimisation()
        self._opt.setMethod(Optimisation.METHOD_LEAST_SQUARES_QUASI_NEWTON)
        self._opt.addObjectiveField(self._outside_surface_fit_objective)
        # self._opt.addObjectiveField(self._volume_smoothing_objective)
        self._opt.addIndependentField(self._coordinates)
        self._opt.setAttributeInteger(Optimisation.ATTRIBUTE_MAXIMUM_ITERATIONS, 1)
         
        print funcname(), "starting optimisation"
        self._opt.optimise()
        print funcname(), "finished optimisation"
        self._zw.updateGL()
        print self._opt.getSolutionReport()

        # Diagnostics: compute RMS error
        field = self._outside_surface_fit_objective
        cache = fm.createFieldcache()
        dp_iter = data_nodeset_group.createNodeiterator()
        dp = dp_iter.next()
        while dp.isValid():
            # cache.setMeshLocation(element, xi)
            cache.setNode(dp)
            # field.assignReal(cache, dp)
            result, outValues = field.evaluateReal(cache, 3)
            # Check result, use outValues
            print result, np.sum(outValues)
            dp = dp_iter.next()
            
        region.writeFile("after.exregi")

        
    def show_reference(self):
        scene = self.context().getDefaultRegion().getScene()
        surfaces = scene.findGraphicsByName("surfaces")
        surfaces.setCoordinateField(self._reference_coordinates)
        self._zw.updateGL() # shouldn't be necessary
        
    def show_fitted(self):
        scene = self.context().getDefaultRegion().getScene()
        surfaces = scene.findGraphicsByName("surfaces")
        surfaces.setCoordinateField(self._coordinates)
        self._zw.updateGL()
        
class FitDlg(QtGui.QWidget):
    def __init__(self, parent=None):
        super(FitDlg, self).__init__(parent)
        
        # Using composition to include the visual element of the GUI.
        self.ui = Ui_DlgFitting()
        self.ui.setupUi(self)
        # self.setWindowIcon(QtGui.QIcon("cmiss_icon.ico"))
        
        self._model = Model(self.ui._zincWidget)
        
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
        mesh.linear_mesh(self._model.context(), trans_points.tolist(), elems)
        nodeset = mesh.nodes(self._model.context(), trans_points.tolist(), 'reference_coordinates')
        print funcname(), "nodeset", nodeset
        
        # The datapoint graphics don't appear until the rest of the mesh is loaded,
        # Not sure why that is.
        mesh.createDatapointGraphics(self._model.context())
        mesh.createNodeGraphics(self._model.context())
        mesh.createSurfaceGraphics(self._model.context())
         
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
            
            # load the mesh
            refcoords, coords = load_mesh(self._model.region(), files)
            self._model.setReferenceCoordinates(refcoords)
            self._model.setCoordinates(coords)
            
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
            
            # load the data
            data = load_data(self._model.region(), files)
            self._model.setDataCoordinates(data)
            
        except Exception as e:
            print e
            _handleError(e)         

    def on_select_faces(self):
        # Configure the UI to be in "face selection mode"
        self.ui._zincWidget.setSelectModeElement()
        self.ui._zincWidget.setSelectionModeAdditive()
    
    def on_select_data(self):
        self.ui._zincWidget.setSelectModeData()
        self.ui._zincWidget.setSelectionModeAdditive()
        
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
