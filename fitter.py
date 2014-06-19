import sys
from functools import partial

from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field, FieldFindMeshLocation, FieldGroup
from opencmiss.zinc.optimisation import Optimisation
from opencmiss.zinc.region import Region

import tools.mesh as mesh
import tools.graphics as graphics
from tools.utilities import get_scene, get_field_module, get_tessellation_module

# for diagnostics
import numpy as np

def funcname():
    return sys._getframe(1).f_code.co_name

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

from atom.api import Atom, Typed, observe

class Fitter(object):
    # selection modes
    #Faces = 1
    #Nodes = 2
    #Data = 4
    class Observable(Atom):
        region = Typed(Region)
    
#         def _observe_region(self, change):
#             print change['name']
#             print change['value']

    observable = Observable()
    
    
    def __init__(self, context):
        object.__init__(self)
        
        self._context = context
        self._root_region = context.getDefaultRegion()
        self.observable.region = self._root_region
        self._projected_coordinates = None
        self._error_vector = None
        self._graphicsProjectedPoints = None
        self._graphicsErrorLines = None

        #self._fittedVisible = True
        
        self._cubic_graphics_data = []
        self._cubic_graphics_ref = []
        self._cubic_graphics = []
        
        with get_tessellation_module(context) as tm:
            t = tm.getDefaultTessellation()
            t.setMinimumDivisions([4])
            t.setRefinementFactors([4])
            tm.setDefaultTessellation(t)


    def context(self):
        return self._context
    
    def region(self):
        return self._root_region
    
    def setCurrentRegion(self, region):
        self.observable.region = region
    
    def setReferenceCoordinates(self, x):
        self._refcoords = x
    
    def setCoordinates(self, x):
        self._coords = x
    
    def setDataCoordinates(self, x):
        self._datacoords = x
        
    def setSelectMode(self, mode):
        self._selectMode = mode
        
    def meshLoaded(self):
#         fm = self._region_linear.getFieldmodule()

#         self._coordinates = fm.findFieldByName('coordinates')
#         self._reference_coordinates = fm.findFieldByName('reference_coordinates')
#         self._data_coordinates = fm.findFieldByName('data_coordinates')
        
#         scene_viewer_module = self._context.getSceneviewermodule()
# 
#         # From the scene viewer module we can create a scene viewer, we set up the
#         # scene viewer to have the same OpenGL properties as the QGLWidget.
#         scene_viewer = scene_viewer_module.createSceneviewer(Sceneviewer.BUFFERING_MODE_DOUBLE,
#                                                                    Sceneviewer.STEREO_MODE_DEFAULT)
#         
#         scene_viewer.viewAll()
        #self.region().writeFile("junk.exregi")
        
        self.setCurrentRegion(self._root_region)
        
        self.show_data(True)
        self.show_initial(False)
        self.show_fitted(True)


    def register_automatic(self, translate=True, rotate=True, scale=True):
        
        undoFitted = self.create_fitted_nodes_undo(self._region_linear)
        undoReference = self.create_reference_nodes_undo(self._region_linear)
        def restore():
            undoFitted()
            undoReference()

        # Use Ju's ICP
        import ICP
        # extract nodes into a numpy array
        with get_field_module(self._region_linear) as fm:
            nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

            node_list = mesh.nodes_to_list(nodeset, 3, self._coords_name)
            # print node_list
            n = np.array(node_list)
        
            datapointset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            data_list = mesh.data_to_list(datapointset, 3, self._data_coords_name)
            # print data_list
            d = np.array(data_list)
        
        # FIXME: This uses all the nodes including internal nodes. It
        # would be better to use only the external nodes.
        
        # move the nodes near to the data
        T, trans_nodes = ICP.fitDataEPDP(n, d, translate=translate, rotate=rotate, scale=scale)
        # T, trans_nodes = ICP.fitDataRigidEPDP(n, d)
        # T, trans_nodes = ICP.fitDataRigidScaleEPDP(n, d)
        
        mesh.update_nodes(nodeset, trans_nodes.tolist(), 'coordinates')
        mesh.update_nodes(nodeset, trans_nodes.tolist(), 'reference_coordinates')

        return restore
    
        # save the original data state
        nodeset = region.getFieldmodule().findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        data_list = mesh.data_to_list(nodeset, 3, self._data_coords_name)
        
        def restore(data):
            mesh.update_data(nodeset, data, self._data_coords_name)
        undo = partial(restore, data_list)
        return undo

    # FIXME: should this take a region as a parameter?
    def _create_nodes_undo(self, region, coordinateFieldName):
        # save the nodes state
        nodeset = region.getFieldmodule().findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodes = mesh.nodes_to_list(nodeset, 3, coordinateFieldName)
        
        def restore(data):
            mesh.update_nodes(nodeset, nodes, coordinateFieldName)
        undo = partial(restore, nodes)
        return undo

    def create_fitted_nodes_undo(self, region):
        return self._create_nodes_undo(region, "coordinates")

    def create_reference_nodes_undo(self, region):
        return self._create_nodes_undo(region, "reference_coordinates")
        

        
    def data_mirror(self, axis, about_centroid=True):
        """
        Reflect the data about its centroid in the plane given by axis
        0 - yz, 1 - xz, 2 - xy
        """
        
        undo = self.create_data_undo()
        
        data_list = mesh.data_to_list(self.context(), self._region_linear, 3, self._data_coords_name)
                    
        t = np.identity(3)
        t[axis, axis] = -1
                
        if about_centroid:
            # translate centroid to origin, the centroid of the data is just the mean
            centroid = np.mean(data_list, axis=0)
            data_list = data_list - centroid
        
        # mirror
        a = np.array(data_list)
        mirrored = a.dot(t)

        if about_centroid:
            # translate it back to original position
            data_list = mirrored + centroid
        else:
            data_list = mirrored

        mesh.update_data(self.context(), self._region_linear, data_list.tolist(), self._data_coords_name)
        
        return undo

    def convert_to_cubic(self):
        region_cubic = self.region().createChild("cubic_lagrange")
        self._region_cubic = region_cubic
        #self.setCurrentRegion(region_cubic)
        #region_cubic.setName("cubic_lagrange")
        
        nodes = mesh.nodes_to_list(self.context(), self._region_linear)
        
        mesh.linear_to_cubic(self.context(), region_cubic, nodes, self._elements_linear,
                             coordinate_field_name=[self._coords_name, self._ref_coords_name])
        
        # copy the data to the cubic region for fitting
        data = mesh.data_to_list(self.context(), self._region_linear, 3)
        mesh.create_data_points(self.context(), region_cubic, data)
        
        self._cubic_graphics = self._create_graphics_mesh(region_cubic, self._coords_name, colour='bone')
        
        #self._cubic_graphics_ref = self._create_graphics_mesh(region_cubic, self._ref_coords_name, colour='blue')

        self._cubic_graphics_data = self._create_graphics_data(region_cubic, self._data_coords_name)

    def project(self):
        # project selected data points onto selected faces
#         self._create2DElementGroup(root_region)
#         self._readModelingPoints(root_region)
#         self._defineStoredFoundLocation(root_region)
#         self._defineOptimisationFields(root_region)
#         self._defineOptimisation(root_region)
#         self._createGraphics(root_region)

        # Create a face group
        region = self._region_cubic
        with get_field_module(region) as fm:
            mesh2d = fm.findMeshByDimension(2)
            self._mesh2d = mesh2d
            # m2 = mesh2d # should use m2 as the Hungarian prefix
            try:
                self._gefFaces
            except AttributeError:
                self._gefFaces = None
            if self._gefFaces is None:
                self._gefFaces = fm.createFieldElementGroup(mesh2d)
            if __debug__: print "self._gefFaces", self._gefFaces
            # Get a mesh group to contain the selected faces
            gmFaces = self._gefFaces.getMeshGroup()
            if __debug__: print "gmFaces", gmFaces 
            gmFaces.removeAllElements()
    
            # outsideFaceIds = [3, 8, 13, 18, 23, 27]
            if __debug__: print "self._mesh2d", self._mesh2d
            
            # get the selection field        
            self._selectionGroup = fm.findFieldByName("SelectionGroup").castGroup()
            
            # copy the selected faces to the _outsideMesh group
            gefSelection = self._selectionGroup.getFieldElementGroup(mesh2d)
            meshgroup = gefSelection.getMeshGroup()
            el_iter = meshgroup.createElementiterator()
            if __debug__: print "Adding selected elements to face group" 
            count = 0
            element = el_iter.next()
            while element.isValid():
                elem_id = element.getIdentifier()
                if __debug__: print elem_id,
                gmFaces.addElement(mesh2d.findElementByIdentifier(elem_id))
                element = el_iter.next()
                count += 1
            if __debug__: print

            # for developing just use a few faces
            if count == 0:
                #elist = [int(x) for x in "34 77 158".split()] # linear
                #elist = [int(x) for x in "29 34 188 192".split()] # cubic
                elist = [int(x) for x in "1".split()] # cubic
                for eindex in elist:
                    gmFaces.addElement(mesh2d.findElementByIdentifier(eindex))
            
            # get selected data points
            # Create a data point group to contain the selected datapoints
            sData = fm.findNodesetByName('datapoints')
            print "sData", sData
            # The FieldNodeGroup is the "main" object containing the data,
            # but the NodesetGroup has the add/remove api.
            try:
                self._gnfData
            except AttributeError:
                self._gnfData = None
            
            if self._gnfData is None:
                self._gnfData = fm.createFieldNodeGroup(sData)
            gsData = self._gnfData.getNodesetGroup()
            gsData.removeAllNodes()
    
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
                #dlist = [int(x) for x in "24 26 113 132 157 165 200 228 229 254 269 281 304 312 349 355 374 389 406 427 454 469 490 520 533 552".split()]
                dlist = [x for x in xrange(1,37)]
                for dindex in dlist:
                    gsData.addNode(sData.findNodeByIdentifier(dindex))
            
            if __debug__: print "self._selectionGroup", self._selectionGroup
            if __debug__: print "gsData", gsData
            # nodeGroup.
            # self._selectionGroup.getFieldNodeGroup(datapoints).addNode(228)
            # self._selectionGroup.addNode(228)
            
            self._selectionGroup.clear()
    
            self._defineStoredFoundLocation(region, gsData, gmFaces)


    def _defineStoredFoundLocation(self, region, gsData, gmFaces):
        '''
        Create a field which dynamically finds the nearest location to the
        scaled_data_coordinates on the 2-D mesh and define a field for
        storing these locations so they are not recalculated during
        optimisation.
        '''
        print funcname()
        with get_field_module(region) as fm:
            
            mesh2d = fm.findMeshByDimension(2)
                    
            data_coordinates = fm.findFieldByName(self._data_coords_name)
            coordinates = fm.findFieldByName('coordinates')
            
            self._found_location = fm.createFieldFindMeshLocation(data_coordinates, coordinates, gmFaces)
            self._found_location.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_NEAREST)
            self._stored_location = fm.createFieldStoredMeshLocation(mesh2d)
             
    #         dataNodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
    #         boxpointsNodeGroup = self._boxpoints_group.getFieldNodeGroup(dataNodeset)
    #         self._boxpoints_nodeset = boxpointsNodeGroup.getNodesetGroup()
    
            # region.writeFile("junk_region.exreg")
    
#             dataNodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
#             gfDataCoords = fm.findFieldByName(self._data_coords_name).castGroup()
#             y = data_coordinates.castGroup()
            
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
#             print "sData", sData
    #         gnfSelectedData = self._selectionGroup.getFieldNodeGroup(sData)
    #         print "gnfSelectedData", gnfSelectedData
    #         gsSelectedData = gnfSelectedData.getNodesetGroup()
    #         dp_iter = gsSelectedData.createNodeiterator()
    
            dp_iter = gsData.createNodeiterator()
    
            dataTemplate = sData.createNodetemplate()
            dataTemplate.defineField(self._stored_location)
            cache = fm.createFieldcache()
            datapoint = dp_iter.next()
            if __debug__: print "Projecting data..."
            while datapoint.isValid():
                if __debug__: print datapoint.getIdentifier(),
                cache.setNode(datapoint)
                element, xi = self._found_location.evaluateMeshLocation(cache, 2)
                if element.isValid():
                    datapoint.merge(dataTemplate)
                    self._stored_location.assignMeshLocation(cache, element, xi)
                 
                datapoint = dp_iter.next()
            if __debug__: print
            
            # del self._projected_coordinates
            # del self._error_vector
            coords = fm.findFieldByName(self._coords_name)
            self._projected_coordinates = fm.createFieldEmbedded(coords, self._stored_location)
            data_coords = fm.findFieldByName(self._data_coords_name)
            self._error_vector = fm.createFieldSubtract(self._projected_coordinates, data_coords)
            
            self._createProjectionGraphics(region)
        
    def _createProjectionGraphics(self, region):
        materials_module = self.context().getMaterialmodule()
        materials_module.defineStandardMaterials()
        blue = materials_module.findMaterialByName('blue')
        
        with get_scene(region) as scene:
        
            # projected points
            if not self._graphicsProjectedPoints is None:
                scene.removeGraphics(self._graphicsProjectedPoints)
            proj = scene.createGraphicsPoints()
            # save graphics object so that it can be destroyed later
            self._graphicsProjectedPoints = proj
            proj.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            proj.setCoordinateField(self._projected_coordinates)
            # consider only the selected data points group
            proj.setSubgroupField(self._gnfData)
            proj.setMaterial(blue)
            attr = proj.getGraphicspointattributes()
            attr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
            attr.setBaseSize([0.2]) # FIXME: this needs to be settable
            
            # error lines
            if not self._graphicsErrorLines is None:
                scene.removeGraphics(self._graphicsErrorLines)
            err = scene.createGraphicsPoints()
            self._graphicsErrorLines = err
            err.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            err.setCoordinateField(self._projected_coordinates)
            err.setSubgroupField(self._gnfData)
            attr = err.getGraphicspointattributes()
            attr.setGlyphShapeType(Glyph.SHAPE_TYPE_LINE)
            attr.setOrientationScaleField(self._error_vector)
            attr.setScaleFactors([-1, 0, 0])
        
    def fit(self, alpha=0, beta=0):
        region = self._region_cubic
        region.writeFile("before.exregi")
        
#         self._defineOptimisationFields(root_region)
#     def _defineOptimisationFields(self, region):
#         '''
#         Define the outside surface fit objective field and the volume smoothing
#         objective field.
#         '''
        with get_field_module(region) as fm:
            # self._projected_coordinates = fm.createFieldEmbedded(self._coordinates, self._stored_location)
            # self._error_vector = fm.createFieldSubtract(self._projected_coordinates, self._data_coordinates)
            data_nodeset_group = self._gnfData.getNodesetGroup()
            self._outside_surface_fit_objective = fm.createFieldNodesetSumSquares(self._error_vector, data_nodeset_group)
            if __debug__:
                print "self._outside_surface_fit_objective", self._outside_surface_fit_objective
            
            # Diagnostics: print out data point ids
            if __debug__: 
                print "Data point ids"
                dp_iter = data_nodeset_group.createNodeiterator()
                node = dp_iter.next()
                while node.isValid():
                    node_id = node.getIdentifier()
                    print node_id,
                    node = dp_iter.next()
                print
            
                print "RMS error"
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
            
            # create penalty objective functions
            coords = fm.findFieldByName(self._coords_name)
            du_dx = [fm.createFieldDerivative(coords, 1),
                     fm.createFieldDerivative(coords, 2)]
            sNodes = fm.findNodesetByName('nodes')
            mesh2d = self._mesh2d

            # create an arc length penalty objective function
            if alpha > 0:
                du_dx_cat = fm.createFieldConcatenate(du_dx)
                
                sumsq = fm.createFieldNodesetSumSquares(du_dx_cat, sNodes)
                const = fm.createFieldConstant(alpha)
                weighted = fm.createFieldAdd(const, sumsq)
                self._line_arc_length_objective = fm.createFieldMeshIntegral(weighted, coords, mesh2d)
                self._opt.addObjectiveField(self._line_arc_length_objective)

            # create a curvature penalty function
            # FIXME: need basis_derivative to be put in the API to enable
            # second derivatives
            # The technique below of applying the derivative field twice will not work
#             if beta > 0:
#                 du2_dx2 = [fm.createFieldDerivative(du_dx[0], 1), fm.createFieldDerivative(du_dx[1], 2),
#                            fm.createFieldDerivative(du_dx[0], 2), fm.createFieldDerivative(du_dx[1], 1)]
#                 du_dx_cat = fm.createFieldConcatenate(du2_dx2)
#                 sumsq = fm.createFieldNodesetSumSquares(du_dx_cat, sNodes)
#                 const= fm.createFieldConstant(beta)
#                 weighted = fm.createFieldAdd(const, sumsq)
#                 self._curvature_objective = fm.createFieldMeshIntegral(weighted, coords, mesh2d)
#                 self._opt.addObjectiveField(self._curvature_objective)
            
            coords = fm.findFieldByName('coordinates')
            self._opt.addIndependentField(coords)
            self._opt.setAttributeInteger(Optimisation.ATTRIBUTE_MAXIMUM_ITERATIONS, 1)
             
            print funcname(), "starting optimisation"
            self._opt.optimise()
            print funcname(), "finished optimisation"
    
            # FIXME: generate an event here
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


#     def _setGraphicsCoordinates(self, coordinate_field):
#         with get_scene(self.context().getDefaultRegion()) as scene:
#             for name in ['nodes', 'lines', 'surfaces']:
#                 graphics = scene.findGraphicsByName(name)
#                 graphics.setCoordinateField(coordinate_field)

    def show_data(self, state):
#         self._setGraphicsCoordinates(self._reference_coordinates)
#         self._fittedVisible = False
        
        for g in self._data_graphics:
            g.setVisibilityFlag(state)

    def show_initial(self, state):
#         self._setGraphicsCoordinates(self._reference_coordinates)
#         self._fittedVisible = False
        
        for g in self._initial_graphics_ref:
            g.setVisibilityFlag(state)
        
    # FIXME: We don't need a fitted mesh for the initial graphics
    def show_fitted(self, state):
#         self._setGraphicsCoordinates(self._coordinates)
#         self._fittedVisible = True
        for g in self._initial_graphics:
            g.setVisibilityFlag(state)

    def show_data_cubic(self, state):
        for g in self._cubic_graphics_data:
            g.setVisibilityFlag(state)

    def show_reference_cubic(self, state):
        for g in self._cubic_graphics_ref:
            g.setVisibilityFlag(state)
        
    def show_fitted_cubic(self, state):
        for g in self._cubic_graphics:
            g.setVisibilityFlag(state)
            
        
#     # This is a hack to force the view to update. It should not be
#     # necessary but I don't know the right way to do it.
#     def update_visible(self):
#         if self._fittedVisible:
#             self.show_reference()
#             self.show_fitted()
#         else:
#             self.show_fitted()
#             self.show_reference()
# 
#         scene = self.context().getDefaultRegion().getScene()
#         graphics = scene.findGraphicsByName('datapoints')
#         graphics.setCoordinateField(self._data_coordinates)
        
    def load_problem(self, path):
        # file is json
        import json
        
        try:
            with open(path, 'r') as f:
                record = json.load(f)
        except Exception as ex:
            # couldn't load json
            # FIXME: log diagnostics
            raise ex
        ctxt = self.context()
        region = self.region().createChild("linear")
        self._region_linear = region

        self._coords_name = 'coordinates'
        self._ref_coords_name = 'reference_coordinates'
        self._data_coords_name = 'data_coordinates'
        
        # returns a python list
        datapoints = mesh.read_txtnode(record['data'])
        mesh.create_data_points(ctxt, region, datapoints)
        self._data_graphics = self._create_graphics_data(region, self._coords_name)
        
        nodes = mesh.read_txtnode(record['nodes'])
        
        elems = mesh.read_txtelem(record['elems'])
        self._elements_linear = elems
                
        
        mesh.linear_mesh(ctxt, region, nodes, elems,
                         coordinate_field_name=self._coords_name)
        
        # Load the mesh again, this time merging with the previous mesh
        # and renaming the coordinate field to reference_coordinates.
        # This adds another set of coordinates at each node.
        mesh.linear_mesh(ctxt, region, nodes, elems,
                         coordinate_field_name=self._ref_coords_name, merge=True)
    
        self._initial_graphics = self._create_graphics_mesh(region, self._coords_name)
        self._initial_graphics_ref = self._create_graphics_mesh(region, self._ref_coords_name, colour="green")
        
        self.meshLoaded()
        
    def _create_graphics_data(self, region, coords_field, **kwargs):
        ctxt = self.context()
        mygraphics = graphics.createDatapointGraphics(ctxt, region, datapoints_name='data', datapoints_size=0.2)
        return mygraphics

    def _create_graphics_mesh(self, region, coords_field, **kwargs):
        ctxt = self.context()
        
        mygraphics = []
        
        colour = kwargs.get("colour", "white")
        
        mygraphics.extend(graphics.createNodeGraphics(ctxt,
                                        region,
                                        nodes_name='nodes',
                                        coordinate_field_name=coords_field,
                                        colour=colour,
                                        nodes_size=0.2))
        
        mygraphics.extend(
            graphics.createSurfaceGraphics(ctxt,
                                           region,
                                           surfaces_name='surfaces',
                                           lines_name='lines',
                                           coordinate_field_name=coords_field,
                                           colour=colour))
        
#         graphics.append(
#             graphics.createNodeGraphics(ctxt,
#                                         region,
#                                         nodes_name='nodes',
#                                         coordinate_field_name=ref_coords_field))
# 
#         graphics.append(
#             graphics.createSurfaceGraphics(ctxt,
#                                            region,
#                                            surfaces_name='ref_surfaces',
#                                            lines_name='ref_lines',
#                                            coordinate_field_name=ref_coords_field,
#                                            colour="green"))
        
        return mygraphics
        
    def save_problem(self, path):
        # There are 2 parts to this: one is the fields and data, the
        # other is the visualisation
        # How do we save the visualisation?
        self.region().writeFile(str(path))

        # extract nodes and datapoints as text
        # extract elements as text
        # create object to store the names and save as json 
        
#     def _load_mesh(self):
#         import ICP
#         data = mesh.read_txtnode("abi_femur_head_500.ascii")
#         
#         # reflect data in in y axis to match mesh
#         # FIXME: there needs to be a GUI for this        
#         d = np.array(data)
#         print d
#         r = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
#         xdim = d.shape[0]
#         ones = np.ones((xdim, 1))
#         h = np.hstack([d, ones])
#         print h.shape
#         d = h.dot(r)[:, 0:3]
#         print d
# 
#         mesh.data_points(self._model.context(), d.tolist())
#         
#         nodes = mesh.read_txtnode("abi_femur_head.node.txt")
#         
#         # move the nodes near to the data
#         T, trans_points = ICP.fitDataRigidEPDP(nodes, d)
#         
#         elems = mesh.read_txtelem("abi_femur_head.elem.txt")
# 
#         coords = 'coordinates'
#         ref_coords = 'reference_coordinates'
#         
#         mesh.linear_mesh(self._model.context(), trans_points.tolist(), elems,
#                          coordinate_field_name=coords)
#         
#         # Load the mesh again, this time merging with the previous mesh
#         # and renaming the coordinate field to reference_coordinates.
#         # This adds another set of coordinates at each node.
#         mesh.linear_mesh(self._model.context(), trans_points.tolist(), elems,
#                          coordinate_field_name=ref_coords, merge=True)
#         
# #         # for debugging
# #         self._model.context().getDefaultRegion().writeFile("junk_region.exreg")
#         
#         # The datapoint graphics don't appear until the rest of the mesh is loaded,
#         # FIXME: Not sure why that is.
#         mesh.createDatapointGraphics(self._model.context(), datapoints_name='data')
#         mesh.createNodeGraphics(self._model.context(), nodes_name='nodes',
#                                  coordinate_field_name=coords)
#         mesh.createSurfaceGraphics(self._model.context(),
#                                    surfaces_name='surfaces',
#                                    lines_name='lines',
#                                    coordinate_field_name=coords)
#          
#         
#         self.meshLoaded()

    def SaveState(self):
        state = None
        self.region().writeFile("state.exregi")

        return state
        
    def RestoreState(self, state):
        pass
        
