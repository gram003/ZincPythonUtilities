import math

from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.element import Element, Elementbasis


def _coordinate_field(ctxt, coordinate_set, nodeset_type, field_name):
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
    finite_element_field.setName(field_name)
    
    # Find a special node set named 'nodes' or 'datapoints'
    nodeset = field_module.findNodesetByName(nodeset_type)
    node_template = nodeset.createNodetemplate()

    # Set the finite element coordinate field for the nodes to use
    node_template.defineField(finite_element_field)
    field_cache = field_module.createFieldcache()

    node_identifiers = []
    
    # Create nodes and add to field cache
    for point in coordinate_set:
        node = nodeset.createNode(-1, node_template)
        
        #print node.getIdentifier(), node_coordinate 
        node_identifiers.append(node.getIdentifier())
        # Set the node coordinates, first set the field cache to use the current node
        field_cache.setNode(node)
        # Pass in floats as an array
        finite_element_field.assignReal(field_cache, point)
        
    return nodeset

# map shape type to mesh order
_shape_type_map = {1: Element.SHAPE_TYPE_LINE,
                   2: Element.SHAPE_TYPE_SQUARE,
                   3: Element.SHAPE_TYPE_CUBE}


def linear_mesh(ctxt, node_coordinate_set, element_set):
    '''
    Create linear finite elements given node and element lists
    '''

    if len(element_set) == 0:
        raise RuntimeError("Empty element list") 

    if len(node_coordinate_set) == 0:
        raise RuntimeError("Empty node list") 

    default_region = ctxt.getDefaultRegion()
    field_module = default_region.getFieldmodule()

    nodeset = _coordinate_field(ctxt, node_coordinate_set, 'nodes', 'coordinates')

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
    finite_element_field = field_module.findFieldByName('coordinates')
    element_template.defineFieldSimpleNodal(finite_element_field,
                                            -1,
                                            linear_basis, local_indices)

    # create the elements
    for node_indices in element_set:        
        for i, node_idx in enumerate(node_indices):
            node = nodeset.findNodeByIdentifier(node_idx)
            element_template.setNode(i + 1, node)
            
        mesh.defineElement(-1, element_template)

    finite_element_field.setTypeCoordinate(True) 
    field_module.defineAllFaces() 
    field_module.endChange()
    
def data_points(ctxt, coordinate_set):
    
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty datapoint coordinate list") 
                
    nodeset = _coordinate_field(ctxt, coordinate_set, 'datapoints', 'data_coordinates')
    
    return nodeset

def nodes(ctxt, coordinate_set):
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node coordinate list") 

    nodeset = _coordinate_field(ctxt, coordinate_set, 'nodes', 'coordinates')
    
    return nodeset

def createGraphics(ctxt):
    
    # FIXME: the graphics that are created need to be controlled by arguments
    # probably kwargs would be suitable for this
    
    materials_module = ctxt.getMaterialmodule()
    materials_module.defineStandardMaterials()
    green = materials_module.findMaterialByName('green')

    glyph_module = ctxt.getGlyphmodule()
    glyph_module.defineStandardGlyphs()

    default_region = ctxt.getDefaultRegion()
    # Get the scene for the default region to create the visualisation in.
    scene = default_region.getScene()
    
    # We use the beginChange and endChange to wrap any immediate changes and will
    # streamline the rendering of the scene.
    scene.beginChange()
            
    # createSurfaceGraphic graphic start
    field_module = default_region.getFieldmodule()
    finite_element_field = field_module.findFieldByName('coordinates')
 
    # Create line graphics
    lines = scene.createGraphicsLines()
    lines.setCoordinateField(finite_element_field)
     
    # Create a surface graphic and set it's coordinate field to the finite element coordinate field
    # named coordinates
    surface = scene.createGraphicsSurfaces()
    surface.setCoordinateField(finite_element_field)
    surface.setName("surface")
     
    # Create point graphics and set the coordinate field to the finite element coordinate field
    # named coordinates
    sphere = scene.createGraphicsPoints()
    sphere.setCoordinateField(finite_element_field)
    sphere.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
    att = sphere.getGraphicspointattributes()
    att.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
    att.setBaseSize([1])

    data_coordinates = field_module.findFieldByName('data_coordinates')
    diamond = scene.createGraphicsPoints()
    diamond.setCoordinateField(data_coordinates)
    diamond.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
    att = diamond.getGraphicspointattributes()
    att.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND)
    diamond.setMaterial(green)
    att.setBaseSize([1.5]) # FIXME: need to be able to set this from the API
 
    #cmiss_number_field = field_module.findFieldByName('cmiss_number')
    #att.setLabelField(cmiss_number_field)
      
    # Let the scene render the scene.
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
    