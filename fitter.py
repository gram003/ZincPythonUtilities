import sys
from functools import partial

from opencmiss import zinc

from opencmiss.zinc.glyph import Glyph
#from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field, FieldFindMeshLocation, FieldGroup
from opencmiss.zinc.optimisation import Optimisation
from opencmiss.zinc.region import Region

#from opencmiss.zinc.selection import Selectioncallback

import tools.mesh as mesh
import tools.graphics as graphics
from tools.utilities import get_scene, get_field_module, get_tessellation_module

from atom.api import Atom, Typed, Int, Bool
import numpy as np

# for diagnostics
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


class Fitter(object):
    # selection modes - use Field.DOMAIN_TYPE_* for this
    #Faces = 1
    #Nodes = 2
    #Data = 4
    FIT_NONE = 0
    FIT_REGISTER_AUTO = 1
    FIT_HOST = 2
    FIT_SURFACE = 3
    
    # Selection mode for picking in the scene. These can potentially be combined.
    SelectModeNone = 0
    SelectModeNodes = 1
    SelectModeData = 2
    SelectModeFaces = 4
    
    class Observable(Atom):
        # if a field is added here, be sure to add an observer in main_controller.set_fitter
        region = Typed(Region)
        selectMode = Int()
        hmfProblemDefined = Bool()
    
    observable = Observable()
    
    def __init__(self, context):
        object.__init__(self)
        
        self._context = context
        self._root_region = context.getDefaultRegion()
        self.observable.region = self._root_region

        self.observable.selectMode = self.SelectModeNone
        self.observable.hmfProblemDefined = False

        self._projected_coordinates = None
        self._error_vector = None
        self._graphicsProjectedPoints = None
        self._graphicsErrorLines = None
        self._pointSize = 1
        #self._fittedVisible = True
        
        self._cubic_graphics_data = []
        self._cubic_graphics_ref = []
        self._cubic_graphics = []
        
        self._selectedFaces = []
        self._fitMode = None
        
        with get_tessellation_module(context) as tm:
            t = tm.getDefaultTessellation()
            t.setMinimumDivisions([4])
            t.setRefinementFactors([4])
            tm.setDefaultTessellation(t)


#     def _selectionCallback(self, evt):
#         print funcname(), evt

    def context(self):
        return self._context
    
    def region(self):
        return self._root_region
    
    def setCurrentRegion(self, region):
        self.observable.region = region
        self._root_region = region
    
    def setReferenceCoordinates(self, x):
        self._refcoords = x
    
    def setCoordinates(self, x):
        self._coords = x
    
    def setDataCoordinates(self, x):
        self._datacoords = x
        
    def setSelectMode(self, mode):
        self.observable.selectMode = mode

    def getSelectMode(self):
        return self.observable.selectMode
    
    def setFitMode(self, mode):
        fitModePrevious = self._fitMode
        self._fitMode = mode 
        if fitModePrevious == self.FIT_HOST:
            # delete the host mesh
            self._deleteBoundingBoxMesh()

    def setPointSize(self, size):
        self._pointSize = size
        
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
        
#         # The Selectionnotifier is not really what we want as it only tells
#         # us if the designated selection group has changed. We really want to
#         # know the details of what was added or removed.
#         # Create a callable selection notifier class
#         # http://cmiss.sourceforge.net/classOpenCMISS_1_1Zinc_1_1Selectioncallback.html
#         class SelectionEvent(Selectioncallback):
#             def __init__(self):
#                 pass
#             def __call__(self, evt):
#                 print evt
# 
#         callbackObj = SelectionEvent()

#         with get_scene(self._root_region) as scene:
#             notifier = scene.createSelectionnotifier()
#             notifier.setCallback(callbackObj)
#             notifier.setCallback(self._selectionCallback)
        

    def register_automatic(self, translate=True, rotate=True, scale=True):
        self.setFitMode(self.FIT_REGISTER_AUTO)
        # Use Ju's ICP
        import ICP
        # extract nodes into a numpy array
        with get_field_module(self._region_linear) as fm:
            nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            
            # Create the undo function
            undoFitted = self.create_fitted_nodes_undo(nodeset)
            undoReference = self.create_reference_nodes_undo(nodeset)
            def restore():
                undoFitted()
                undoReference()
            
            # Uses only the exterior nodes to do the fit
            # Create a node group for exterior nodes
            fExt = fm.createFieldIsExterior()
            # create a meshgroup and add
            gfExt = fm.createFieldGroup()
            gfExt.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
            #gfExt.setManaged(True) # prevent group from being destroyed when not in use
            #gfExt.setName('exterior')
            meshExt = fm.findMeshByDimension(2)
            geExt = gfExt.createFieldElementGroup(meshExt)
            sExt = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gsExt = gfExt.createFieldNodeGroup(sExt)
            meshGroup = geExt.getMeshGroup()
            meshGroup.addElementsConditional(fExt)
            
            ng = gsExt.getNodesetGroup()
            
            ext_list = mesh.nodes_to_list(ng, 3, self._coords_name)
            print len(ext_list)
            
            # diagnostics: compare with full nodeset
            master_node_list = mesh.nodes_to_list(nodeset, 3, self._coords_name)
            print len(master_node_list)

            n = np.array(ext_list)
        
            datapointset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            data_list = mesh.data_to_list(datapointset, 3, self._data_coords_name)
            # print data_list
            d = np.array(data_list)

        # Move the nodes near to the data, note that the nodes being moved
        # are different to the nodes used to do the fit. 
        T, trans_nodes = ICP.fitDataEPDP(n, d, translate=translate,
                                         rotate=rotate, scale=scale,
                                         nodes_to_move=master_node_list)
        # T, trans_nodes = ICP.fitDataRigidEPDP(n, d)
        # T, trans_nodes = ICP.fitDataRigidScaleEPDP(n, d)
        print len(trans_nodes)
        
        mesh.update_nodes(nodeset, trans_nodes.tolist(), 'coordinates')
        mesh.update_nodes(nodeset, trans_nodes.tolist(), 'reference_coordinates')

        return restore
    
    def _createBoundingBoxMesh(self, nodesetGroup, coordinateFieldName):
        # get the list of nodes in the region
        with get_field_module(nodesetGroup) as fm:
            #nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nodes = mesh.nodes_to_list(nodesetGroup, 3, coordinateFieldName)
            npnodes = np.array(nodes)
            nmin = np.min(npnodes, axis=0)
            nmax = np.max(npnodes, axis=0)
            
            max_node = len(nodes)
            
            # make the bounding box 5% larger than the mesh
            for i, _ in enumerate(nmin):
                dx = 1.05 * (nmax[i] - nmin[i])
                new_min = nmax[i] - dx
                new_max = nmin[i] + dx
                nmax[i] = new_max
                nmin[i] = new_min
    
            # create bounding box vertex nodes
            n = [nmin, nmax]
            
    #         nodes = [[ n[0][0], n[0][1], n[0][2] ],
    #                  [ n[1][0], n[0][1], n[0][2] ],
    #                  [ n[0][0], n[1][1], n[0][2] ],
    #                  [ n[1][0], n[1][1], n[0][2] ],
    #                  ]
            
            host_nodes = []
             
            for z in [0, 1]: 
                for y in [0, 1]:
                    for x in [0, 1]:
                        host_nodes.append([ n[x][0], n[y][1], n[z][2]])
                        
            #print np.array(host_nodes)
            
            element = [[i for i in xrange(max_node+1, max_node+9)]]
            gfHost = fm.createFieldGroup()
            gfHost.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
            gfHost.setManaged(True) # prevent group from being destroyed when not in use
            gfHost.setName('host')
            mesh3d = fm.findMeshByDimension(3)
            hostElemGroup = gfHost.createFieldElementGroup(mesh3d)
            meshGroup = hostElemGroup.getMeshGroup()
            # newly created element(s) and nodes will have the highest id's
            mesh.linear_mesh(meshGroup, host_nodes, element, coordinate_field_name="host_"+coordinateFieldName)
            
            return gfHost

    def _addPointsToMarkerGroups(self, targets):
        """
        Copies the coordinates of the given nodes to a 'marker' field on
        the corresponding datapoints. 
        param: targets a dict containing node_id : datapoint_id pairs
        """
        
        with get_field_module(self._region_hmf) as fm:
            sData = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

            gnfData = fm.findFieldByName("hmf_datapoints").castNodeGroup()
            if gnfData.isValid():
                gsData = gnfData.getNodesetGroup()
                for dindex in targets.values():
                    gsData.addNode(sData.findNodeByIdentifier(dindex))
            else:
                raise RuntimeError("HMF datapoint field not found")
        
            dataTemplate = sData.createNodetemplate()
            marker_coordinates = fm.findFieldByName('marker_coordinates')
            if not marker_coordinates.isValid():
                raise RuntimeError("HMF marker_coordinates field not found")

            stored_location = fm.findFieldByName('hmf_stored_location')
            if not stored_location.isValid():
                raise RuntimeError("HMF stored_location field not found")
            
            found_location = fm.findFieldByName('hmf_found_location')
            if not found_location.isValid():
                raise RuntimeError("HMF found_location field not found")

            node_coordinates = fm.findFieldByName(self._coords_name)
            data_coordinates = fm.findFieldByName(self._data_coords_name)

            dataTemplate.defineField(marker_coordinates)
            dataTemplate.defineField(stored_location)

            cache = fm.createFieldcache()

            for node_id, dp_id in targets.iteritems():
                node = sNodes.findNodeByIdentifier(node_id)
                dp = sData.findNodeByIdentifier(dp_id)
                # get the node coordinates
                cache.setNode(node)
                result, nodeCoords = node_coordinates.evaluateReal(cache, 3)
                dp = sData.findNodeByIdentifier(dp_id)
                cache.setNode(dp)
                # assign node coords to the marker field on the datapoint nodeset
                dp.merge(dataTemplate)
                marker_coordinates.assignReal(cache, nodeCoords)
                
                # find the host element xi location and assign it to the
                # stored location field on the datapoint nodeset
                element, xi = found_location.evaluateMeshLocation(cache, 3)
                if element.isValid():
                    stored_location.assignMeshLocation(cache, element, xi)

                if __debug__:
                    result, outValues = data_coordinates.evaluateReal(cache, 3)
                    print "_addPointsToMarkerGroups", 'dp', dp_id, "coords=", result, outValues, 
                    result, outValues = marker_coordinates.evaluateReal(cache, 3)
                    print "marker=", result, outValues

#             # embed the nodes in the host mesh
#             nodes_found_location = fm.createFieldFindMeshLocation(node_coordinates, host_coordinates, meshGroup)
#             nodes_found_location.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_EXACT)
#             nodes_stored_location = fm.createFieldStoredMeshLocation(mesh3d)
#             nodes_stored_location.setName('nodes_stored_location')
#  
#             sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
#             nd_iter = sNodes.createNodeiterator()
#       
#             nodeTemplate = sNodes.createNodetemplate()
#             nodeTemplate.defineField(nodes_stored_location)
#             cache = fm.createFieldcache()
#             node = nd_iter.next()
#             if __debug__: print "Embedding nodes..."
#             while node.isValid():
#                 if __debug__: print "nd", node.getIdentifier(),
#                 cache.setNode(node)
#                 element, xi = nodes_found_location.evaluateMeshLocation(cache, 3)
#                 if element.isValid():
#                     node.merge(nodeTemplate)
#                     nodes_stored_location.assignMeshLocation(cache, element, xi)
#                     if __debug__: print "elem", element.getIdentifier(), xi
#  
#                 node = nd_iter.next()


    def graphics_selected(self, item, fieldDomainType):
        print funcname(), "domainType", fieldDomainType, "item id", item.getIdentifier()
        if self._fitMode == self.FIT_HOST:
            if self.getSelectMode() == self.SelectModeNodes and \
                    fieldDomainType == Field.DOMAIN_TYPE_NODES:
                # add to nodes group
                node_id = item.getIdentifier()
                self._selected_node_id = node_id
                self._selectState = Field.DOMAIN_TYPE_DATAPOINTS
                self.setSelectMode(self.SelectModeData)
                
            elif self.getSelectMode() == self.SelectModeData and \
                    fieldDomainType == Field.DOMAIN_TYPE_DATAPOINTS:
                # add to datapoints group
                datapoint_id = item.getIdentifier()
                d = {self._selected_node_id : datapoint_id}
                self._addPointsToMarkerGroups(d)
                self._selectState = Field.DOMAIN_TYPE_NODES
                self.setSelectMode(self.SelectModeNodes)

    def hostmesh_register_setup(self):
        """
        Given a list of fiducial marker nodes and a list of target datapoints
        host mesh fit the nodes to the data.
        This works by creating a (fiducial) marker field in the datapoints
        nodeset corresponding to the target datapoints and then copying the
        node coordinates to this marker field. The marker field is then used
        to do the optimisation. It is done this way because of the way that
        the optimiser works.
        """
        self._region_hmf = self._region_linear
        
        self.setFitMode(self.FIT_HOST)
        self.setSelectMode(self.SelectModeNodes)
        #self._selectState = Field.DOMAIN_TYPE_NODES
        # TODO need to save state and set the status bar text, then swap state to "data" when a node is selected 
        
        # FIXME: get nodes from selection
        #nodes = [9, 39, 89, 25, 90, 129]
        #datapoints = [160, 549, 112, 19, 428, 274]
        nodes = []
        datapoints = []
        
        # Create a dict where the target data point ids are the keys. This is
        # because we need to get the datapoints back later by iterating a
        # nodeset and they will be in numerical order then. 
        #targets = dict(zip(nodes, datapoints))

        with get_field_module(self._region_hmf) as fm:
            
            # Get the model nodeset group
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gfModel = fm.findFieldByName('model').castGroup()
            assert(gfModel.isValid())
            gsModel = gfModel.getFieldNodeGroup(sNodes).getNodesetGroup()
            assert(gsModel.isValid())

            undoFitted = self.create_fitted_nodes_undo(gsModel)
            undoReference = self.create_reference_nodes_undo(gsModel)
            def restore():
                undoFitted()
                undoReference()
            
            # Create a bounding box
            # This has to be done in the same region as the mesh so it will need to
            # use the next highest node numbers.
            # FIXME: Will this break cubic conversion? I could delete this element after the fit is done.
            # FIXME: Could I clone the region to work around this?
                        
            gfHost = self._createBoundingBoxMesh(gsModel, self._coords_name)
    
            self._region_linear.writeFile("host.exregi")
            
            self._host_graphics = self._create_graphics_nodes(self._region_linear, "host_"+self._coords_name, sub_group_field=gfHost)
            self._host_graphics.extend(self._create_graphics_lines(self._region_linear, "host_"+self._coords_name, sub_group_field=gfHost))
            for g in self._host_graphics:
                g.setVisibilityFlag(True)
    
            # define stored found location and create projections
            mesh3d = fm.findMeshByDimension(3)
                    
            node_coordinates = fm.findFieldByName(self._coords_name)
            data_coordinates = fm.findFieldByName(self._data_coords_name)
            host_coordinates = fm.findFieldByName('host_coordinates')
            marker_coordinates = fm.createFieldFiniteElement(3)
            marker_coordinates.setName('marker_coordinates')
            
            hostElemGroup = gfHost.getFieldElementGroup(mesh3d)
            meshGroup = hostElemGroup.getMeshGroup()
            
            # create a nodeset group containing the selected datapoints
            sData = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
    
            gnfData = fm.createFieldNodeGroup(sData)
            gnfData.setName("hmf_datapoints")
            gsData = gnfData.getNodesetGroup()
            gsData.removeAllNodes()

#             # add datapoints for development/testing set datapoints to [] to disable
#             for dindex in datapoints:
#                 gsData.addNode(sData.findNodeByIdentifier(dindex))
            
            # store it so other methods can use it - not that useful since we need the field module to be able to modify it    
            #self._hmf_gsData = gsData
            
            # Copy the corresponding node coords to the marker field on the
            # datapoints nodeset.

#             sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
#             dataTemplate = sData.createNodetemplate()
#             dataTemplate.defineField(marker_coordinates)
#             cache = fm.createFieldcache()
#             # add nodes for development/testing set nodes to [] to disable
#             # this will have to be done dynamically for interactive use
#             #print "copy node coords to marker field in data nodeset" 
#             for node_id in nodes:
#                 print 'node', node_id,
#                 node = sNodes.findNodeByIdentifier(node_id)
#                 cache.setNode(node)
#                 result, outValues = node_coordinates.evaluateReal(cache, 3)
#                 print result, outValues
#                 dp_id = targets[node_id]
#                 dp = sData.findNodeByIdentifier(dp_id)
#                 cache.setNode(dp)
#                 # assign to new field
#                 dp.merge(dataTemplate)
#                 marker_coordinates.assignReal(cache, outValues)
#                 result, outValues = data_coordinates.evaluateReal(cache, 3)
#                 print 'dp', dp_id,
#                 print "coords", result, outValues
#                 result, outValues = marker_coordinates.evaluateReal(cache, 3)
#                 print "marker", result, outValues

            #self._addNodeCoordToMarkerGroup(nodes)

            # create fields for embedding the fiducial markers 
            found_location = fm.createFieldFindMeshLocation(marker_coordinates, host_coordinates, meshGroup)
            found_location.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_EXACT)
            found_location.setName('hmf_found_location')
            found_location.setManaged(True)
            stored_location = fm.createFieldStoredMeshLocation(mesh3d)
            stored_location.setName('hmf_stored_location')
            stored_location.setManaged(True)
            

#             dp_iter = gsData.createNodeiterator()    
#             dataTemplate = sData.createNodetemplate()
#             dataTemplate.defineField(stored_location)
#             cache = fm.createFieldcache()
#             datapoint = dp_iter.next()
#             if __debug__: print "Embedding fiducial markers..."
#             while datapoint.isValid():
#                 if __debug__: print "dp", datapoint.getIdentifier(),
#                 cache.setNode(datapoint)
#                 element, xi = found_location.evaluateMeshLocation(cache, 3)
#                 if element.isValid():
#                     datapoint.merge(dataTemplate)
#                     stored_location.assignMeshLocation(cache, element, xi)
#                     if __debug__: print "elem", element.getIdentifier(), xi
#                  
#                 datapoint = dp_iter.next()
# 
            # embed all of the nodes in the host mesh so they can be
            # moved after the new host mesh has been calculated
            nodes_found_location = fm.createFieldFindMeshLocation(node_coordinates, host_coordinates, meshGroup)
            nodes_found_location.setSearchMode(FieldFindMeshLocation.SEARCH_MODE_EXACT)
            nodes_stored_location = fm.createFieldStoredMeshLocation(mesh3d)
            nodes_stored_location.setName('nodes_stored_location')
 
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nd_iter = sNodes.createNodeiterator()
      
            nodeTemplate = sNodes.createNodetemplate()
            nodeTemplate.defineField(nodes_stored_location)
            cache = fm.createFieldcache()
            node = nd_iter.next()
            if __debug__: print "Embedding nodes..."
            while node.isValid():
                #if __debug__: print "nd", node.getIdentifier(),
                cache.setNode(node)
                element, xi = nodes_found_location.evaluateMeshLocation(cache, 3)
                if element.isValid():
                    node.merge(nodeTemplate)
                    nodes_stored_location.assignMeshLocation(cache, element, xi)
                    #if __debug__: print "elem", element.getIdentifier(), xi
 
                node = nd_iter.next()
            
            # At initialisation this field is the same as the marker_coordinates field. However
            # it is required so that the optimizer can recalculate the new host coordinates.
            self._hmf_projected_coordinates = fm.createFieldEmbedded(host_coordinates, stored_location)
            
            error_vector = fm.createFieldSubtract(self._hmf_projected_coordinates, data_coordinates)
            error_vector.setName('error')
            self._hmf_error = error_vector

            # Embed the nodes in the host mesh so that we can later use it for transforming them 

            #self._region_linear.writeFile("proj.exregi")

            with get_scene(self._region_linear) as scene:
                self._createProjectionGraphics(scene, self._hmf_projected_coordinates, gnfData, error_vector)
 
        return restore        

    def hostmesh_register_fit(self, alpha=0):
        self.setSelectMode(self.SelectModeNone)
        self._fitMode = None

        # define an optimisation problem    
        with get_field_module(self._region_linear) as fm:
            #data_nodeset_group = self._hmf_gsData
            gnfData = fm.findFieldByName("hmf_datapoints").castNodeGroup()
            if not gnfData.isValid():
                raise RuntimeError("HMF hmf_datapoints field not found")
            gsData = gnfData.getNodesetGroup()
            hmf_objective = fm.createFieldNodesetSumSquares(self._hmf_error, gsData)

            self._opt = fm.createOptimisation()
            self._opt.setMethod(Optimisation.METHOD_LEAST_SQUARES_QUASI_NEWTON)
            self._opt.addObjectiveField(hmf_objective)
            # self._opt.addObjectiveField(self._volume_smoothing_objective)
            
            host_coords = fm.findFieldByName('host_coordinates')
            self._opt.addIndependentField(host_coords)
            #self._opt.setAttributeInteger(Optimisation.ATTRIBUTE_MAXIMUM_ITERATIONS, 1)
             
            du_dx = [fm.createFieldDerivative(host_coords, 1),
                     fm.createFieldDerivative(host_coords, 2),
                     fm.createFieldDerivative(host_coords, 3)]
            
            # Get the host nodeset group
            gfHost = fm.findFieldByName('host').castGroup()
            assert(gfHost.isValid())
            sHost = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gsHost = gfHost.getFieldNodeGroup(sHost).getNodesetGroup()
            assert(gsHost.isValid())
            
            # get the host mesh group
            meshHost = fm.findMeshByDimension(3)
            gmHost = gfHost.getFieldElementGroup(meshHost).getMeshGroup()
            assert(gmHost.isValid())

            # create an arc length penalty objective function
            # doesn't work
            if alpha > 0:
                du_dx_cat = fm.createFieldConcatenate(du_dx)
                
                sumsq = fm.createFieldNodesetSumSquares(du_dx_cat, gsHost)
                const = fm.createFieldConstant(alpha)
                weighted = fm.createFieldAdd(const, sumsq)
                # need to integrate w.r.t reference coords here
                line_arc_length_objective = fm.createFieldMeshIntegral(weighted, host_coords, gmHost)
                self._opt.addObjectiveField(line_arc_length_objective)
            
            self._opt.optimise()
    
            # FIXME: generate an event here
            print self._opt.getSolutionReport()
            
            # Transform the nodes based on the new host configuration            
            nodes_stored_location = fm.findFieldByName('nodes_stored_location')
                        
            # replace node coordinates with embedded_coordinates
            host_coordinates = fm.findFieldByName('host_coordinates')
            embedded_coordinates = fm.createFieldEmbedded(host_coordinates, nodes_stored_location)
            nodes_coordinates = fm.findFieldByName('coordinates')
            cache = fm.createFieldcache()
            
            # Get the model nodeset group
            gfModel = fm.findFieldByName('model').castGroup()
            assert(gfModel.isValid())
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gsModel = gfModel.getFieldNodeGroup(sNodes).getNodesetGroup()
            assert(gsModel.isValid())

            nd_iter = gsModel.createNodeiterator()
            node = nd_iter.next()
                        
            if __debug__: print "Transforming nodes..."
            while node.isValid():
                if __debug__: print "nd", node.getIdentifier(),
                cache.setNode(node)
                result, outValues = embedded_coordinates.evaluateReal(cache, 3)
                nodes_coordinates.assignReal(cache, outValues)
            
                node = nd_iter.next()
                
            # FIXME: need to delete the host mesh so that it can be recreated
            # Find and delete the host element and nodes

            self._region_linear.writeFile("hmf.exregi")
    
    def create_data_undo(self, nodesetGroup):
        # save the original data state
        data_list = mesh.data_to_list(nodesetGroup, 3, self._data_coords_name)
        
        def restore(data):
            mesh.update_data(nodesetGroup, data, self._data_coords_name)
        undo = partial(restore, data_list)
        return undo

    def _create_nodes_undo(self, nodesetGroup, coordinateFieldName):
        # save the nodes state
        nodes = mesh.nodes_to_list(nodesetGroup, 3, coordinateFieldName)
        
        def restore(data):
            mesh.update_nodes(nodesetGroup, nodes, coordinateFieldName)
        undo = partial(restore, nodes)
        return undo

    def create_fitted_nodes_undo(self, nodesetGroup):
        return self._create_nodes_undo(nodesetGroup, "coordinates")

    def create_reference_nodes_undo(self, nodesetGroup):
        return self._create_nodes_undo(nodesetGroup, "reference_coordinates")
        
    def data_mirror(self, axis, about_centroid=True):
        """
        Reflect the data about its centroid in the plane given by axis
        0 - yz, 1 - xz, 2 - xy
        """
        
        fm = self._region_linear.getFieldmodule()
        datapointset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        undo = self.create_data_undo(datapointset)
        data_list = mesh.data_to_list(datapointset, 3, self._data_coords_name)
                    
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

        mesh.update_data(datapointset, data_list.tolist(), self._data_coords_name)
        
        return undo

    def convert_to_cubic(self):
        region_cubic = self.region().createChild("cubic_lagrange")
        self._region_cubic = region_cubic
        #self.setCurrentRegion(region_cubic)
        #region_cubic.setName("cubic_lagrange")
        with get_field_module(self._region_linear) as fm, \
                        get_field_module(region_cubic) as fmc:
            nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nodes = mesh.nodes_to_list(nodeset)
            
            mesh_cubic = fmc.findMeshByDimension(3)
            
            mesh.linear_to_cubic(mesh_cubic, nodes, self._elements_linear,
                                 coordinate_field_name=[self._coords_name, self._ref_coords_name])
            
            # copy the data to the cubic region for fitting
            datapointset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            data = mesh.data_to_list(datapointset, 3)
            with get_field_module(region_cubic) as fmc:
                datapointset_cubic = fmc.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
                mesh.define_datapoints(datapointset_cubic, data)
        
        self._cubic_graphics = self._create_graphics_mesh(region_cubic, self._coords_name, colour='bone', exterior=True)
        
        #self._cubic_graphics_ref = self._create_graphics_mesh(region_cubic, self._ref_coords_name, colour='blue')

        self._cubic_graphics_data = self._create_graphics_data(region_cubic, self._data_coords_name)

    def storeSelectedFaces(self):
        self._selectedFaces = []
        region = self._region_cubic
        with get_field_module(region) as fm:
            mesh2d = fm.findMeshByDimension(2)

#             # Copy the selected faces to the "FacesGroup" group
            # Get the selection field        
            selectionGroup = fm.findFieldByName("SelectionGroup").castGroup()
            gefSelection = selectionGroup.getFieldElementGroup(mesh2d)
            meshgroup = gefSelection.getMeshGroup()
#             print "meshgroup.getMasterMesh().getName()", meshgroup.getMasterMesh().getName()
#                         
#             facesGroupName = "FacesGroup"
#             gFaces = fm.findFieldByName(facesGroupName).castGroup()            
#             if not gFaces.isValid():
#                 gFaces = fm.createFieldGroup()
#                 gFaces.setName(facesGroupName)
#                 gFaces.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
#                 gFaces.setManaged(True) # prevent group from being destroyed when not in use
# 
#             gefFaces = gFaces.getFieldElementGroup(mesh2d)
#             gmFaces = gefFaces.getMeshGroup()
#             gmFaces.removeAllElements()
#             print "gmFaces.getMasterMesh().getName()", gmFaces.getMasterMesh().getName()

            
            el_iter = meshgroup.createElementiterator()
            if __debug__: print "Adding selected elements to face group" 
            count = 0
            element = el_iter.next()
            while element.isValid():
                elem_id = element.getIdentifier()
                self._selectedFaces.append(elem_id)
                if __debug__: print elem_id,
                #print mesh2d.findElementByIdentifier(elem_id)
                #print element.getMesh().getFieldmodule().getRegion().getName()
                #res = gmFaces.addElement(element)
                #print res
                #assert(zinc.status.OK == res)
                
                element = el_iter.next()
                count += 1
            if __debug__: print

#             print "Num faces in group=", gmFaces.getSize() 
# 
#             el_iter = gmFaces.createElementiterator()
#             if __debug__: print "Elements in face group..." 
#             count = 0
#             element = el_iter.next()
#             while element.isValid():
#                 elem_id = element.getIdentifier()
#                 if __debug__: print elem_id,
#                 element = el_iter.next()
#                 count += 1
#             if __debug__: print
        

    def project(self):
        # project selected data points onto selected faces
#         self._create2DElementGroup(root_region)
#         self._readModelingPoints(root_region)
#         self._defineStoredFoundLocation(root_region)
#         self._defineOptimisationFields(root_region)
#         self._defineOptimisation(root_region)
#         self._createGraphics(root_region)

        # Create a face group
        region = self._region_cubic # need to convert to cubic first
        with get_field_module(region) as fm:
            mesh2d = fm.findMeshByDimension(2)
            self._mesh2d = mesh2d
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            # m2 = mesh2d # should use m2 as the Hungarian prefix
#             try:
#                 self._gfFaces
#             except AttributeError:
            # Find or create a group to contain the selected faces
            faceGroupName = 'FaceGroup'
            self._gfFaces = fm.findFieldByName(faceGroupName).castGroup()
            if self._gfFaces.isValid():
                self._gfFaces.clear()
            else:
                self._gfFaces = fm.createFieldGroup()
                self._gfFaces.setManaged(True)
                self._gfFaces.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
                self._gfFaces.setManaged(True) # prevent group from being destroyed when not in use
                self._gfFaces.setName(faceGroupName)

            self._gefFaces = self._gfFaces.createFieldElementGroup(mesh2d)

            if __debug__: print "self._gefFaces", self._gefFaces
            
            gmFaces = self._gefFaces.getMeshGroup()
            #if __debug__: print "gmFaces", gmFaces 
            #gmFaces.removeAllElements()
    
            # outsideFaceIds = [3, 8, 13, 18, 23, 27]
            if __debug__: print "self._mesh2d", self._mesh2d
            
            # get the selection field        
            self._selectionGroup = fm.findFieldByName("SelectionGroup").castGroup()
            
            # copy the selected faces to the _outsideMesh group
            gefSelection = self._selectionGroup.getFieldElementGroup(mesh2d)
            meshgroup = gefSelection.getMeshGroup()
            count = 0
            if meshgroup.getSize() == 0:
                if __debug__: print "Adding previously selected elements to face group" 
                for elem_id in self._selectedFaces:
                    if __debug__: print elem_id,
                    gmFaces.addElement(mesh2d.findElementByIdentifier(elem_id))
            else:
                el_iter = meshgroup.createElementiterator()
                if __debug__: print "Adding currently selected elements to face group" 
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
                #elist = [int(x) for x in "29 34 188 192".split()] # cubic proximal femur
                elist = [int(x) for x in "34 77 106 148 158 160 192 223 244 265 286 300".split()] # proximal hemisphere
                #elist = [158]
                #elist = [int(x) for x in "1".split()] # 2d cubic example
                for eindex in elist:
                    gmFaces.addElement(mesh2d.findElementByIdentifier(eindex))
            
            # get selected data points
            # Create a data point group to contain the selected datapoints
            sData = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
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
                dlist = [int(x) for x in "19 22 24 26 34 40 55 56 57 61 72 75" # proximal hemisphere
                    " 84 88 94 104 110 112 113 115 132 133 135 146 156 157 159"
                    " 165 172 183 184 186 187 188 191 193 200 207 210 211 214"
                    " 220 228 229 244 254 256 262 268 269 273 275 278 279 280"
                    " 281 282 289 293 300 304 312 313 314 319 338 347 349 351"
                    " 355 361 364 367 368 374 389 390 393 394 395 405 406 409"
                    " 418 423 426 427 438 454 462 464 465 469 478 489 490 498"
                    " 504 506 510 512 520 533 534 547 552 555".split()]
                
                #dlist = [int(x) for x in "26 113 228 281 312 349 355 367 406 469 520 533 552".split()]

                #dlist = [x for x in xrange(1,37)] # 2d cubic problem
                for dindex in dlist:
                    gsData.addNode(sData.findNodeByIdentifier(dindex))
            
            if __debug__: print "self._selectionGroup", self._selectionGroup
            if __debug__: print "gsData", gsData
            # nodeGroup.
            # self._selectionGroup.getFieldNodeGroup(datapoints).addNode(228)
            # self._selectionGroup.addNode(228)
            
            # Get selected nodes to fix
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gnfNodes = fm.createFieldNodeGroup(sNodes)
            gnfNodes.setName("SelectedNodes")
            gnfNodes.setManaged(True)
            gsNodes = gnfNodes.getNodesetGroup()
    
            nodegroup = self._selectionGroup.getFieldNodeGroup(sNodes)
            gsNodesSelected = nodegroup.getNodesetGroup()
            nd_iter = gsNodesSelected.createNodeiterator()
            print "Adding nodes to node group"
            count = 0
            node = nd_iter.next()
            while node.isValid():
                node_id = node.getIdentifier()
                print node_id,
                gsNodes.addNode(gsNodesSelected.findNodeByIdentifier(node_id))
                node = nd_iter.next()
                count += 1
            print
            
            if count == 0:
                nlist = [int(x) for x in "25 27 45 61 89 102 130 137 402 403 784 785 1030 1031 1394 1395 1772 1773 2404 2405 2586 2587 2720 2721".split()]
                for nindex in nlist:
                    gsNodes.addNode(sNodes.findNodeByIdentifier(nindex))
                    
            print "number of nodes to remove =", gsNodes.getSize()
            
            self._gnfRemove = gnfNodes
            
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
            
            with get_scene(region) as scene:
                self._createProjectionGraphics(scene, self._projected_coordinates, self._gnfData, self._error_vector)

    # FIXME: this should probably be in a "view" class
    def _createProjectionGraphics(self, scene, projected_coordinates, gnfData, error_vector):
        materials_module = scene.getMaterialmodule()
        materials_module.defineStandardMaterials()
        blue = materials_module.findMaterialByName('blue')
        
        # projected points
        if not self._graphicsProjectedPoints is None:
            scene.removeGraphics(self._graphicsProjectedPoints)
        proj = scene.createGraphicsPoints()
        # save graphics object so that it can be destroyed later
        self._graphicsProjectedPoints = proj
        proj.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        proj.setCoordinateField(projected_coordinates)
        # consider only the selected data points group
        proj.setSubgroupField(gnfData)
        proj.setMaterial(blue)
        attr = proj.getGraphicspointattributes()
        attr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        attr.setBaseSize([self._pointSize*1.1])
        
        # error lines
        if not self._graphicsErrorLines is None:
            scene.removeGraphics(self._graphicsErrorLines)
        err = scene.createGraphicsPoints()
        self._graphicsErrorLines = err
        err.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        err.setCoordinateField(projected_coordinates)
        err.setSubgroupField(gnfData)
        attr = err.getGraphicspointattributes()
        attr.setGlyphShapeType(Glyph.SHAPE_TYPE_LINE)
        attr.setOrientationScaleField(error_vector)
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
            outside_surface_fit_objective = fm.createFieldNodesetSumSquares(self._error_vector, data_nodeset_group)
            if __debug__:
                print "outside_surface_fit_objective", outside_surface_fit_objective
            
#             # Diagnostics: print out data point ids
#             if __debug__: 
#                 print "Data point ids"
#                 dp_iter = data_nodeset_group.createNodeiterator()
#                 node = dp_iter.next()
#                 while node.isValid():
#                     node_id = node.getIdentifier()
#                     print node_id,
#                     node = dp_iter.next()
#                 print
#             
#                 print "RMS error"
#                 # Diagnostics: compute RMS error
#                 field = self._outside_surface_fit_objective
#                 cache = fm.createFieldcache()
#                 dp_iter = data_nodeset_group.createNodeiterator()
#                 dp = dp_iter.next()
#                 while dp.isValid():
#                     cache.setNode(dp)
#                     result, outValues = field.evaluateReal(cache, 3)
#                     print result, np.sum(outValues)
#                     dp = dp_iter.next()
                
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
            self._opt.addObjectiveField(outside_surface_fit_objective)
            # self._opt.addObjectiveField(self._volume_smoothing_objective)
            
            # create penalty objective functions
            # Get NodesetGroup and MeshGroup for the selected faces
            coords = fm.findFieldByName(self._coords_name)
            ref_coords = fm.findFieldByName(self._ref_coords_name)
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gnfFaces = self._gfFaces.getFieldNodeGroup(sNodes)
            gsFaces = gnfFaces.getNodesetGroup()
            mesh2d = fm.findMeshByDimension(2)
            gmFaces = self._gfFaces.getFieldElementGroup(mesh2d).getMeshGroup()
            mesh1d = fm.findMeshByDimension(1)
            gmLines = self._gfFaces.getFieldElementGroup(mesh1d).getMeshGroup()
            mesh3d = fm.findMeshByDimension(3)
            gmElems = self._gfFaces.getFieldElementGroup(mesh3d).getMeshGroup()
            
            # remove fixed nodes from group
#             gfRemove = fm.findFieldByName("SelectedNodes").castGroup()
#             assert(gfRemove.isValid())
#             gsRemove = gfRemove.getFieldNodeGroup(sNodes).getNodesetGroup()
#             assert(gsRemove.isValid())
            
            print "number of nodes in fit before removal =", gsFaces.getSize()
            gsRemove = self._gnfRemove.getNodesetGroup()
            nd_iter = gsRemove.createNodeiterator()
            node = nd_iter.next()
            print "nodes to remove"
            while node.isValid():
                print node.getIdentifier(),
                gsFaces.removeNode(node)
                node = nd_iter.next()
            print

            print "number of nodes in fit after removal =", gsFaces.getSize()
           
            print "number of faces in fit =", gmFaces.getSize()
 
            # create an arc length penalty objective function                 = fm.createFieldMultiply(weight, area)

            if alpha > 0:
                print "alpha =", alpha 
                du_dx = [fm.createFieldDerivative(coords, 1),
                         fm.createFieldDerivative(coords, 2)]
                du_dx_cat = fm.createFieldConcatenate(du_dx)
                 
                weight = fm.createFieldConstant(alpha)

#                 sumsq = fm.createFieldNodesetSumSquares(du_dx_cat, gsFaces)
#                 weighted = fm.createFieldMultiply(const, sumsq)
#                 self._line_arc_length_objective = fm.createFieldMeshIntegral(weighted, coords, gmFaces)#mesh2d)
 
                integralSquares = fm.createFieldMeshIntegralSquares(du_dx_cat, ref_coords, gmFaces)
                integralSquares.setNumbersOfPoints([4])
                line_arc_length_objective = fm.createFieldMultiply(weight, integralSquares)
                
                self._opt.addObjectiveField(line_arc_length_objective)
                

#                 const = fm.createFieldConstant(1)
#                 weight = fm.createFieldConstant(alpha)
#                 
#                 ref_arc_length = fm.createFieldMeshIntegral(weight, ref_coords, gmLines)
#                 arc_length = fm.createFieldMeshIntegral(weight, coords, gmLines)
#                 arc_length.setNumbersOfPoints([4])
#                 print "arc_length.getNumbersOfPoints()", arc_length.getNumbersOfPoints(0)
#                 
#                 line_arc_length_objective = fm.createFieldSubtract(arc_length, ref_arc_length)
#                 self._opt.addObjectiveField(line_arc_length_objective)
# 
#                 ref_area = fm.createFieldMeshIntegral(weight, ref_coords, gmFaces)
#                 area = fm.createFieldMeshIntegral(weight, coords, gmFaces)
#                 
#                 face_area_objective = fm.createFieldSubtract(area, ref_area)
#                 self._opt.addObjectiveField(face_area_objective)
                
                

            if beta > 0:
                print "beta =", beta 
#                 ref_coords = fm.findFieldByName('reference_coordinates')                 
#                 displacement = fm.createFieldSubtract(coords, ref_coords)
#     
#                 displacementGradient = fm.createFieldGradient(displacement, ref_coords)
#                 const = fm.createFieldConstant(beta)
#                 weightedDisplacementGradient = fm.createFieldMultiply(const, displacementGradient)
#     
#                 mesh3d = fm.findMeshByDimension(3)
#                 smoothingObjective = fm.createFieldMeshIntegralSquares(weightedDisplacementGradient, ref_coords, mesh3d)
#                 self._opt.addObjectiveField(smoothingObjective)

#                 # try a face area restricting objective function
#                 ref_coords = fm.findFieldByName('reference_coordinates')                 
#                 const = fm.createFieldConstant(1)
#                 fitted_area = fm.createFieldMeshIntegral(const, coords, gmFaces)
#                 ref_area = fm.createFieldMeshIntegral(const, ref_coords, gmFaces)
#                 diff = fm.createFieldSubtract(fitted_area, ref_area)
#                 const = fm.createFieldConstant(beta)
#                 area_objective = fm.createFieldMultiply(diff, const)
#                 self._opt.addObjectiveField(area_objective)

            # create a curvature penalty function
            # FIXME: need basis_derivative to be put in the API to enable
            # second derivatives
            # The technique below of applying the derivative field twice will not work
#                 du2_dx2 = [fm.createFieldDerivative(du_dx[0], 1), fm.createFieldDerivative(du_dx[1], 2),
#                            fm.createFieldDerivative(du_dx[0], 2), fm.createFieldDerivative(du_dx[1], 1)]
#                 du_dx_cat = fm.createFieldConcatenate(du2_dx2)
#                 sumsq = fm.createFieldNodesetSumSquares(du_dx_cat, sNodes)
#                 const= fm.createFieldConstant(beta)
#                 weighted = fm.createFieldMultiply(const, sumsq)
#                 self._curvature_objective = fm.createFieldMeshIntegral(weighted, coords, mesh2d)
#                 self._opt.addObjectiveField(self._curvature_objective)
                
                # Try a strain penalty
                # u = x - X
#                 u = fm.createFieldSubtract(coords, ref_coords)
#                 # du_dxi1 = field derivative (u, 1)
#                 du_dxi1 = fm.createFieldDerivative(u, 1)
#                 du_dxi2 = fm.createFieldDerivative(u, 2)
#                 FT = fm.createFieldConcatenate([du_dxi1, du_dxi2])
#                 F = fm.createFieldTranspose(2, FT)
#                 E = fm.createFieldMatrixMultiply(2, FT, F)
#                                     
#                 weight = fm.createFieldConstant(beta)
#                 weighted = fm.createFieldMultiply(E, weight)
#                     
#                 strain_objective = fm.createFieldMeshIntegral(weighted, ref_coords, gmFaces)
#                 strain_objective.setNumbersOfPoints([4])
#                 self._opt.addObjectiveField(strain_objective)

                F = fm.createFieldGradient(coords, ref_coords)
                FT = fm.createFieldTranspose(3, F)
                  
                C = fm.createFieldMatrixMultiply(3, FT, F)
                weight = fm.createFieldConstant(beta*0.5)
                I = fm.createFieldConstant([1, 0, 0, 0, 1, 0, 0, 0, 1])
                #half = fm.createFieldConstant(0.5) # included in weight
                CmI = fm.createFieldSubtract(C, I)
                E = fm.createFieldMultiply(CmI, weight)
                    
                strain_objective = fm.createFieldMeshIntegral(E, ref_coords, gmFaces)
                strain_objective.setNumbersOfPoints([4])
                self._opt.addObjectiveField(strain_objective)
                

            self._opt.addIndependentField(coords)
            self._opt.setConditionalField(coords, gnfFaces)
            
            self._opt.setAttributeInteger(Optimisation.ATTRIBUTE_MAXIMUM_ITERATIONS, 200)
             
            import time
            start = time.time()
            print funcname(), "starting optimisation"
            self._opt.optimise()
            print funcname(), "finished optimisation in %s seconds" % (time.time() - start)
    
            # FIXME: generate an event here
            print self._opt.getSolutionReport()
    
#             # Diagnostics: compute RMS error
#             field = self._outside_surface_fit_objective
#             cache = fm.createFieldcache()
#             dp_iter = data_nodeset_group.createNodeiterator()
#             dp = dp_iter.next()
#             while dp.isValid():
#                 # cache.setMeshLocation(element, xi)
#                 cache.setNode(dp)
#                 # field.assignReal(cache, dp)
#                 result, outValues = field.evaluateReal(cache, 3)
#                 # Check result, use outValues
#                 print result, np.sum(outValues)
#                 dp = dp_iter.next()
                
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
        #ctxt = self.context()
        region = self.region().createChild("linear")
        self._region_linear = region

        self._coords_name = 'coordinates'
        self._ref_coords_name = 'reference_coordinates'
        self._data_coords_name = 'data_coordinates'
        
        # returns a python list
        datapoints = mesh.read_txtnode(record['data'])
        fm = region.getFieldmodule()
        nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        mesh.define_datapoints(nodeset, datapoints)
        self._data_graphics = self._create_graphics_data(region, self._coords_name)
        
        nodes = mesh.read_txtnode(record['nodes'])
        
        elems = mesh.read_txtelem(record['elems'])
        dimension = mesh._find_mesh_dimension(record["basis_order"], elems)
        
        self._elements_linear = elems

#         mymesh = fm.findMeshByDimension(dimension)
#         mesh.linear_mesh(mymesh, nodes, elems,
#                          coordinate_field_name=self._coords_name)

        # Load the mesh into a group named 'model'
        gfModel = fm.createFieldGroup()
        gfModel.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
        gfModel.setManaged(True) # prevent group from being destroyed when not in use
        gfModel.setName('model')
        meshModel = fm.findMeshByDimension(dimension)
        modelElemGroup = gfModel.createFieldElementGroup(meshModel)
        meshGroup = modelElemGroup.getMeshGroup()
        mesh.linear_mesh(meshGroup, nodes, elems, coordinate_field_name=self._coords_name)

        
        # Load the mesh again, this time merging with the previous mesh
        # and renaming the coordinate field to reference_coordinates.
        # This adds another set of coordinates at each node.
        mesh.linear_mesh(meshGroup, nodes, elems,
                         coordinate_field_name=self._ref_coords_name, merge=True)
            
        self._initial_graphics = self._create_graphics_mesh(region, self._coords_name, colour='white', sub_group_field=gfModel)

        self._initial_graphics_ref = self._create_graphics_mesh(region, self._ref_coords_name, colour="green", sub_group_field=gfModel)
        
        self.meshLoaded()
        
    def _create_graphics_data(self, region, coords_field, **kwargs):
        mygraphics = graphics.createDatapointGraphics(region, datapoints_name='data', datapoints_size=self._pointSize)
        return mygraphics
    
    def _create_graphics_nodes(self, region, coords_field, **kwargs):
        
        mygraphics = []
        
        #colour = kwargs.get("colour", "white")
        
        mygraphics.extend(graphics.createNodeGraphics(region,
                                        nodes_name='nodes',
                                        coordinate_field_name=coords_field,
                                        nodes_size=self._pointSize,
                                        **kwargs))
        return mygraphics
    
    def _create_graphics_lines(self, region, coords_field, **kwargs):
        
        mygraphics = []
        
        #colour = kwargs.get("colour", "white")
        
        mygraphics.extend(
            graphics.createLineGraphics(region,
                                           lines_name='lines',
                                           coordinate_field_name=coords_field,
                                           **kwargs))
                
        return mygraphics

    def _create_graphics_surfaces(self, region, coords_field, **kwargs):
        
        mygraphics = []
        
        #colour = kwargs.get("colour", "white")
        
        mygraphics.extend(
            graphics.createSurfaceGraphics(region,
                                           surfaces_name='surfaces',
                                           **kwargs))
                
        return mygraphics

    def _create_graphics_mesh(self, region, coords_field, **kwargs):
        
        mygraphics = []
        
#         colour = kwargs.get("colour", "white")
        
        # FIXME: this should call _create_graphics_nodes and _create_graphics_surfaces
        
        mygraphics.extend(graphics.createNodeGraphics(region,
                                                      nodes_name='nodes',
                                                      coordinate_field_name=coords_field,
                                                      nodes_size=self._pointSize,
                                                      **kwargs))
        
        mygraphics.extend(
            graphics.createLineGraphics(region,
                                        surfaces_name='surfaces',
                                        lines_name='lines',
                                        coordinate_field_name=coords_field,
                                        **kwargs))

        mygraphics.extend(
            graphics.createSurfaceGraphics(region,
                                           surfaces_name='surfaces',
                                           lines_name='lines',
                                           coordinate_field_name=coords_field,
                                           **kwargs))
        
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
        
