import math

from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.status import OK

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
                   3: Element.SHAPE_TYPE_CUBE }

_basis_type_map = {1: Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE,
                   2: Elementbasis.FUNCTION_TYPE_QUADRATIC_LAGRANGE,
                   3: Elementbasis.FUNCTION_TYPE_CUBIC_LAGRANGE }

# findNodeByIdentifier
# node.merge(template)

def _lagrange_mesh(ctxt, region, basis_order, node_coordinate_set, element_set, **kwargs):
    '''
    Create linear finite elements given node and element lists
    param: ctxt xinc context
    param: region zinc region
    param: order order of Lagrange interpolation 1 = linear, 2 = quadratic, 3 = cubic
    '''
    # Parse kwargs    
    coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')
    merge = kwargs.get('merge', False)
    
    use_existing_nodes = kwargs.get('use_existing_nodes', False)

    if len(element_set) == 0:
        raise RuntimeError("Empty element list") 

    if len(node_coordinate_set) == 0:
            use_existing_nodes = True

    with get_field_module(region) as field_module:

        if use_existing_nodes:
            nodeset = field_module.findNodesetByName('nodes')
            if not nodeset.isValid():
                raise RuntimeError("The node list was empty and could not find a nodeset in the given region")
        else:
            nodeset = _coordinate_field(ctxt, region, node_coordinate_set, 'nodes', coordinate_field_name, merge)
    
        # Create and configure an element template for the appropriate mesh type.
        element_node_count = len(element_set[0])

        # Work out the mesh dimension from the number of nodes in the first element    
        float_dimension = math.log(element_node_count, basis_order+1)
        dimension = int(round(math.log(element_node_count, basis_order+1)))
        assert(float_dimension - dimension == 0.0)
        if float_dimension - dimension != 0.0:
            raise RuntimeError("Wrong number of nodes in element. Got %d expected %d." \
                               % (element_node_count, math.pow(basis_order+1, dimension)))
        #if __debug__: print "mesh basis_order", basis_order, "dimension", dimension    

        mesh = field_module.findMeshByDimension(dimension)
        element_template = mesh.createElementtemplate()
        
        element_template.setElementShapeType(_shape_type_map[dimension])
        element_template.setNumberOfNodes(element_node_count)
        
        # Specify the dimension and the interpolation function for the element basis function
        basis_type = _basis_type_map[basis_order]
        basis = field_module.createElementbasis(
               dimension,
               basis_type)
        
        # the indices of the nodes in the node template we want to use.
        local_indices = [x for x in xrange(1, element_node_count+1)]
        
        # Define a nodally interpolated element field or field component in the
        # element_template
        finite_element_field = field_module.findFieldByName(coordinate_field_name)
        element_template.defineFieldSimpleNodal(finite_element_field,
                                                -1,
                                                basis,
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

def linear_mesh(ctxt, region, node_coordinate_set, element_set, **kwargs):
    _lagrange_mesh(ctxt, region, 1, node_coordinate_set, element_set, **kwargs)

def quadratic_lagrange_mesh(ctxt, region, node_coordinate_set, element_set, **kwargs):
    _lagrange_mesh(ctxt, region, 2, node_coordinate_set, element_set, **kwargs)

def cubic_lagrange_mesh(ctxt, region, node_coordinate_set, element_set, **kwargs):
    _lagrange_mesh(ctxt, region, 3, node_coordinate_set, element_set, **kwargs)
    
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

def linear_to_cubic(ctxt, region_linear, region_cubic, nodes, elements, field_name='coordinates'):
    """
    Convert a 3D linear mesh to cubic Lagrange 
    """

    # Implementation notes:
    # Load the linear mesh into zinc as it will be need to interpolated
    # the positions of the internal nodes
    
    # Copy the linear mesh nodes into a new region
    # For each linear element
    #    get the location of xi=0,0,0
    #    search for an existing node at this location
    #    if not found:
    #        create a new node
    #    add the node to the element at the correct index

    import numpy as np
     
    # create a linear mesh in the given region
    linear_mesh(ctxt, region_linear, nodes, elements)

    with get_field_module(region_linear) as d_fm, \
                                get_field_module(region) as fm:
        d_coordinates = d_fm.findFieldByName(field_name)
        d_fc = d_fm.createFieldcache()
        
        # Copy the nodes from the linear mesh into the new region, these will
        # become the corner nodes of the cubic Lagrange mesh.
        nodes = nodes_to_list(ctxt, region_linear)
        create_nodes(ctxt, region_cubic, nodes)
                
        # precompute the xi coordinates
        xi = np.linspace(0, 1, 4)

        # iterate over the elements in the linear mesh
        mesh3d = d_fm.findMeshByDimension(3)
        
        # coords field and cache for the new field
        coordinates = fm.findFieldByName(field_name)
        fc = fm.createFieldcache()

        # Create a template for defining new nodes
        nodeset = fm.findNodesetByName('nodes')
        node_template = nodeset.createNodetemplate()
        node_template.defineField(coordinates)
        
        def find_node(coords):
            node_iter = nodeset.createNodeiterator()
            node = node_iter.next()
            found_node_id = None
            while node.isValid():
                fc.setNode(node)
                result, outValues = coordinates.evaluateReal(fc, 3)
                if result != OK:
                    raise RuntimeError("Failed evaluating node %d", node.getIdentifier())
                if np.allclose(np.array(outValues), np.array(coords)):
                    found_node_id = node.getIdentifier()
                    break
                node = node_iter.next()
            return found_node_id

        cubic_elements = []
        el_iter = mesh3d.createElementiterator()
        element = el_iter.next()
        while element.isValid():
            new_element = []
            elem_id = element.getIdentifier()
            #print "elem_id", elem_id

            for xi3 in xi:
                for xi2 in xi:
                    for xi1 in xi:
                        d_fc.setMeshLocation(element, [xi1, xi2, xi3])
                        result, outValues = d_coordinates.evaluateReal(d_fc, 3)
                        #print "xi", xi1, xi2, xi3, "location", outValues
                        
                        # try to find a node with these coordinates
                        node_id = find_node(outValues)
                        if node_id is None:
                            #create a new node
                            new_node = nodeset.createNode(-1, node_template)
                            fc.setNode(new_node)
                            # Pass in floats as an array
                            coordinates.assignReal(fc, outValues)
                            node_id = new_node.getIdentifier()
                    
                        new_element.append(node_id)
            
            element = el_iter.next()
            cubic_elements.append(new_element)           

        # The nodes have already been added to the region so use these existing nodes
        cubic_lagrange_mesh(ctxt, region_cubic, [], cubic_elements)
        

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

