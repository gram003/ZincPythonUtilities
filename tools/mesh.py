import sys
import math

from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.element import Element, Elementbasis

_defaultGraphicsCreated = False

# for diagnostics
def funcname():
    return sys._getframe(1).f_code.co_name

def _coordinate_field(ctxt, coordinate_set, nodeset_type, coordinate_field_name, merge=False):
    '''
    Create a coordinate field given a coordinate list.
    Returns the nodeset
    '''

    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node list") 
    
    if not nodeset_type in ['nodes', 'datapoints']:
        raise RuntimeError("Invalid nodeset type") 

    coord_count = len(coordinate_set[0])
    
    default_region = ctxt.getDefaultRegion()
    
    # Get the field module for root region, with which we  shall create a 
    # finite element coordinate field.
    field_module = default_region.getFieldmodule()
    
    field_module.beginChange()

    finite_element_field = field_module.createFieldFiniteElement(coord_count)
    finite_element_field.setName(coordinate_field_name)
    
    # Find a special node set named 'nodes' or 'datapoints'
    nodeset = field_module.findNodesetByName(nodeset_type)
    node_template = nodeset.createNodetemplate()

    # Set the finite element coordinate field for the nodes to use
    node_template.defineField(finite_element_field)
    field_cache = field_module.createFieldcache()

    #node_identifiers = []
    
    node_id = 1
    # Create nodes and add to field cache
    for coords in coordinate_set:
        if not merge:
            node = nodeset.createNode(-1, node_template)
            #print node.getIdentifier(), node_coordinate 
            #node_identifiers.append(node.getIdentifier())
            # Set the node coordinates, first set the field cache to use the current node
            field_cache.setNode(node)
            # Pass in floats as an array
            finite_element_field.assignReal(field_cache, coords)
        else:
            node = nodeset.findNodeByIdentifier(node_id)
            field_cache.setNode(node)
            node.merge(node_template)
            finite_element_field.assignReal(field_cache, coords)
            node_id += 1
            
    finite_element_field.setTypeCoordinate(True)
    
    return nodeset

# map shape type to mesh order
_shape_type_map = {1: Element.SHAPE_TYPE_LINE,
                   2: Element.SHAPE_TYPE_SQUARE,
                   3: Element.SHAPE_TYPE_CUBE}


# findNodeByIdentifier
# node.merge(template)

def linear_mesh(ctxt, node_coordinate_set, element_set, **kwargs):
    '''
    Create linear finite elements given node and element lists
    '''

    if len(element_set) == 0:
        raise RuntimeError("Empty element list") 

    if len(node_coordinate_set) == 0:
        raise RuntimeError("Empty node list") 

    default_region = ctxt.getDefaultRegion()
    field_module = default_region.getFieldmodule()
    
    if 'coordinate_field_name' in kwargs:
        coordinate_field_name = kwargs['coordinate_field_name']
    else:
        coordinate_field_name = 'coordinates'

    nodeset = _coordinate_field(ctxt, node_coordinate_set, 'nodes', coordinate_field_name)

    # Create and configure an element template for the appropriate mesh type.
    element_node_count = len(element_set[0])

    order = int(math.log(element_node_count, 2))
    #if __debug__: print "mesh order", order        

    mesh = field_module.findMeshByDimension(order)
    element_template = mesh.createElementtemplate()
    
    
    element_template.setElementShapeType(_shape_type_map[order])
    element_template.setNumberOfNodes(element_node_count)
    
    # Specify the dimension and the interpolation function for the element basis function
    linear_basis = field_module.createElementbasis(
           order,
           Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
    
    # the indices of the nodes in the node template we want to use.
    local_indices = [x for x in xrange(1, element_node_count+1)]
    
    # Define a nodally interpolated element field or field component in the
    # element_template
    finite_element_field = field_module.findFieldByName(coordinate_field_name)
    element_template.defineFieldSimpleNodal(finite_element_field,
                                            -1,
                                            linear_basis,
                                            local_indices)

    # create the elements
    for node_indices in element_set:        
        for i, node_idx in enumerate(node_indices):
            node = nodeset.findNodeByIdentifier(node_idx)
            element_template.setNode(i + 1, node)
            
        mesh.defineElement(-1, element_template)

    finite_element_field.setTypeCoordinate(True) 
    field_module.defineAllFaces() 
    field_module.endChange()
    
def data_points(ctxt, coordinate_set, field_name='data_coordinates'):
    
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty datapoint coordinate list") 
                
    nodeset = _coordinate_field(ctxt, coordinate_set, 'datapoints', field_name)
    
    return nodeset

def nodes(ctxt, coordinate_set, field_name='coordinates', merge=False):
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node coordinate list") 

    nodeset = _coordinate_field(ctxt, coordinate_set, 'nodes', field_name, merge)
    
    return nodeset

def _createDefaultGraphics(ctxt):
    global _defaultGraphicsCreated
    if not _defaultGraphicsCreated:
        glyph_module = ctxt.getGlyphmodule()
        glyph_module.defineStandardGlyphs()
        _defaultGraphicsCreated = True

def createDatapointGraphics(ctxt, **kwargs):
    
    #_createDefaultGraphics(ctxt)
    glyph_module = ctxt.getGlyphmodule()
    glyph_module.defineStandardGlyphs()

    default_region = ctxt.getDefaultRegion()

    materials_module = ctxt.getMaterialmodule()
    materials_module.defineStandardMaterials()
    green = materials_module.findMaterialByName('green')

    field_module = default_region.getFieldmodule()

    scene = default_region.getScene()

    scene.beginChange()
                
    data_coordinates = field_module.findFieldByName('data_coordinates')
    diamond = scene.createGraphicsPoints()
    diamond.setCoordinateField(data_coordinates)
    diamond.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
    att = diamond.getGraphicspointattributes()
    att.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND)
    diamond.setMaterial(green)
    if 'datapoints_size' in kwargs:
        att.setBaseSize(kwargs['datapoints_size'])
    else:
        att.setBaseSize(1)
    if 'datapoints_label' in kwargs:
        label_field_name = kwargs['datapoints_label']
        if label_field_name == 'id':
            label_field_name = 'cmiss_number' 
        cmiss_number_field = field_module.findFieldByName(label_field_name)
        print funcname(), "cmiss_number_field.isValid()", cmiss_number_field.isValid()
        att.setLabelField(cmiss_number_field)

    if 'datapoints_name' in kwargs:
        diamond.setName(kwargs['datapoints_name'])
      
    scene.endChange()

def createNodeGraphics(ctxt, **kwargs):

    _createDefaultGraphics(ctxt)

    default_region = ctxt.getDefaultRegion()
    # Get the scene for the default region to create the visualisation in.
    scene = default_region.getScene()
    
    # We use the beginChange and endChange to wrap any immediate changes and will
    # streamline the rendering of the scene.
    scene.beginChange()
            
    field_module = default_region.getFieldmodule()
    if 'coordinate_field_name' in kwargs:
        coordinate_field_name = kwargs['coordinate_field_name']
    else:
        coordinate_field_name = 'coordinates'
    finite_element_field = field_module.findFieldByName(coordinate_field_name)

#     # Diagnositics    
#     fm = field_module
#     sNodes = fm.findNodesetByName('nodes')
#     print "sNodes.getSize()", sNodes.getSize()
     
    sphere = scene.createGraphicsPoints()
    sphere.setCoordinateField(finite_element_field)
    sphere.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
    att = sphere.getGraphicspointattributes()
    att.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
    if 'nodes_size' in kwargs:
        att.setBaseSize(kwargs['nodes_size'])
    else:
        att.setBaseSize([1])
    if 'nodes_label' in kwargs:
        label_field_name = kwargs['nodes_label']
        if label_field_name == 'id':
            label_field_name = 'cmiss_number' 
        cmiss_number_field = field_module.findFieldByName(label_field_name)
        
        print "cmiss_number_field.isValid()", cmiss_number_field.isValid()
        att.setLabelField(cmiss_number_field)

    if 'nodes_name' in kwargs:
        sphere.setName(kwargs['nodes_name'])
      
    scene.endChange()
    

def createSurfaceGraphics(ctxt, **kwargs):
    '''
    Create graphics for the default region.
    Keyword arguments that are currently supported:
    node_size
    node_label
    datapoint_size
    datapoint_label
    '''

    _createDefaultGraphics(ctxt)

    default_region = ctxt.getDefaultRegion()
    # Get the scene for the default region to create the visualisation in.
    scene = default_region.getScene()
    
    # We use the beginChange and endChange to wrap any immediate changes and will
    # streamline the rendering of the scene.
    scene.beginChange()
            
    # createSurfaceGraphic graphic start
    field_module = default_region.getFieldmodule()
    if 'coordinate_field_name' in kwargs:
        coordinate_field_name = kwargs['coordinate_field_name']
    else:
        coordinate_field_name = 'coordinates'
    finite_element_field = field_module.findFieldByName(coordinate_field_name)
     
    # Create line graphics
    lines = scene.createGraphicsLines()
    lines.setCoordinateField(finite_element_field)
    if 'lines_name' in kwargs:
        lines.setName(kwargs['lines_name'])
     
    surfaces = scene.createGraphicsSurfaces()
    surfaces.setCoordinateField(finite_element_field)
    if 'surfaces_name' in kwargs:
        surfaces.setName(kwargs['surfaces_name'])
     
    scene.endChange()
        
    
def read_txtelem(filename):
    '''
    Read element definitions from a text file. One elements is specified
    on each line as a list of the nodes in cmiss order. 
    
    '''
    elemnum = 0
    elem = []
    with open(filename, 'r') as f:
        for line in iter(f):
            elemnum += 1
            vertices = line.split()
            nodes = []
            # a vertex may have a version specified, which we do not want yet
            for vert in vertices:
                n = vert.split(':')
                nodes.append(int(n[0]))
            elem.append(nodes)
    return elem

def read_txtnode(filename):
    '''
    Read a list of coordinates from a file. One coordinate set per line.
    '''
    import numpy as np
    nodes = np.loadtxt(filename)
    return nodes.tolist()
    
    