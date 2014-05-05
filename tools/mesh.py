import math

from opencmiss.zinc.element import Element, Elementbasis

from tools.utilities import get_field_module

from tools.diagnostics import funcname

def _coordinate_field(ctxt, region, coordinate_set, nodeset_type, coordinate_field_name, merge=False):
    '''
    Create a coordinate field given a coordinate list.
    Returns the nodeset
    '''

    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node list") 
    
    if not nodeset_type in ['nodes', 'datapoints']:
        raise RuntimeError("Invalid nodeset type") 

    coord_count = len(coordinate_set[0])
        
    # Get the field module for root region, with which we  shall create a 
    # finite element coordinate field.
    with get_field_module(region) as field_module:
    
        finite_element_field = field_module.createFieldFiniteElement(coord_count)
        finite_element_field.setName(coordinate_field_name)
        
        # Find a special node set named 'nodes' or 'datapoints'
        nodeset = field_module.findNodesetByName(nodeset_type)
        node_template = nodeset.createNodetemplate()
    
        # Set the finite element coordinate field for the nodes to use
        node_template.defineField(finite_element_field)
        field_cache = field_module.createFieldcache()
        
        node_id = 1
        # Create nodes and add to field cache
        for coords in coordinate_set:
            if not merge:
                node = nodeset.createNode(-1, node_template)
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
    with get_field_module(default_region) as field_module:

        # Parse kwargs    
        coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')
        merge = kwargs.get('merge', False)
    
        nodeset = _coordinate_field(ctxt, node_coordinate_set, 'nodes', coordinate_field_name, merge)
    
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
        element_id = 1
        for node_indices in element_set:
            def _populateTemplate():
                for i, node_idx in enumerate(node_indices):
                    node = nodeset.findNodeByIdentifier(node_idx)
                    element_template.setNode(i + 1, node)
                
            if not merge:
                _populateTemplate()
                mesh.defineElement(-1, element_template)
            else:
                element = mesh.findElementByIdentifier(element_id)
                _populateTemplate()
                
                element.merge(element_template)
                element_id += 1
                
    
        finite_element_field.setTypeCoordinate(True) 
        field_module.defineAllFaces() 
    
def create_data_points(ctxt, region, coordinate_set, field_name='data_coordinates'):
    
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty datapoint coordinate list") 
                
    nodeset = _coordinate_field(ctxt, region, coordinate_set, 'datapoints', field_name)
    
    return nodeset

def create_nodes(ctxt, region, coordinate_set, field_name='coordinates', merge=False):
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node coordinate list") 

    nodeset = _coordinate_field(ctxt, region, coordinate_set, 'nodes', field_name, merge)
    
    return nodeset

def linear_to_cubic(ctxt, nodes, elements):
# Do we create linear elements in zinc first? I guess that we need those
# in order to interpolate the positions of the internal nodes.
# Is it better to create new elements or get the existing elements?
# Answer - load linear mesh into one region and create the cubic mesh in another region
# Having the corner nodes of the cubic mesh match the linear mesh nodes is optional (but probably desirable)
    pass
def _nodes_to_list(ctxt, region, nodesetName, numValues=3, coordFieldName='coordinates'):
    """
    Extract nodes into a Python list
    """
    fm = region.getFieldmodule()
    sNodes = fm.findNodesetByName(nodesetName)
    field = fm.findFieldByName(coordFieldName)

    # extract the list of nodes 
    node_list = []
    node_iter = sNodes.createNodeiterator()
    cache = fm.createFieldcache()
    count = 0
    node = node_iter.next()
    while node.isValid():
        #node_id = node.getIdentifier()
        cache.setNode(node)
        result, outValues = field.evaluateReal(cache, numValues)
        node_list.append(outValues)
        node = node_iter.next()
        count += 1

    return node_list

def _update_nodes(ctxt, region, coordinate_set, nodesetName, coordFieldName='coordinates'):
    """
    Update nodes with the coordinates in the given coordinate_set.
    """
    fm = region.getFieldmodule()
    sNodes = fm.findNodesetByName(nodesetName)
    field = fm.findFieldByName(coordFieldName)
    
    # Update nodes with new coordinates 
    with get_field_module(region) as fm:
    
        cache = fm.createFieldcache()
        node_id = 1
        for coords in coordinate_set:
            node = sNodes.findNodeByIdentifier(node_id)
            cache.setNode(node)
            result = field.assignReal(cache, coords)
            node_id += 1
            
    
def nodes_to_list(ctxt, region, numValues=3, coordFieldName='coordinates'):
    """
    Return all nodes as a Python list
    """
    return _nodes_to_list(ctxt, region, 'nodes', numValues, coordFieldName)

def update_nodes(ctxt, region, node_list, coordFieldName='coordinates'):
    """
    Update nodes from a list of coordinates
    """
    _update_nodes(ctxt, region, node_list, 'nodes', coordFieldName)

def data_to_list(ctxt, region, numValues=3, coordFieldName='data_coordinates'):
    """
    Return all datapoints as a Python list
    """
    return _nodes_to_list(ctxt, region, 'datapoints', numValues, coordFieldName)

def update_data(ctxt, region, node_list, coordFieldName='data_coordinates'):
    """
    Generate datapoints from a list of coordinates
    """
    _update_nodes(ctxt, region, node_list, 'datapoints', coordFieldName)

    
def read_txtelem(filename):
    '''
    Read element definitions from a text file. Elements are specified
    one per line as a list of the nodes in cmiss order.
    Returns a Python list of lists
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
    Returns a Python list of lists 
    '''
    import numpy as np
    nodes = np.loadtxt(filename)
    return nodes.tolist()

