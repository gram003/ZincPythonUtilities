import math
import numpy as np

from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field

from tools.utilities import get_field_module

from tools.diagnostics import funcname

def _coordinate_field(nodeset,
                      coordinate_set,
                      coordinate_field_name=['coordinates'],
                      merge=False,
                      start_node_id=False):
    '''
    Create a coordinate field given a coordinate list.
    param: region the region
    param: coordinate_set a list of the nodal coordinates
    param: nodeset_type either 'nodes' or 'datapoints'
    param: coordinate_field_name the name or list of names of the coordinate field(s) 
    param: merge wether to merge this coordinate set into an existing node
    Returns the nodeset
    '''

    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node list") 
    
#     if not nodeset_type in [Field.DOMAIN_TYPE_NODES, Field.DOMAIN_TYPE_DATAPOINTS]:
#         raise RuntimeError("Invalid nodeset type %s, expected Field.DOMAIN_TYPE_NODES or Field.DOMAIN_TYPE_DATAPOINTS" % nodeset_type) 

    if isinstance(coordinate_field_name, list):
        coordinate_fields = coordinate_field_name
    else:
        coordinate_fields = [coordinate_field_name] 
        
    finite_element_fields = []
    
    coord_count = len(coordinate_set[0])
        
    # Get the field module for root region, with which we shall create a 
    # finite element coordinate field.
    with get_field_module(nodeset) as field_module:
        
        node_template = nodeset.createNodetemplate()

        for name in coordinate_fields:
            finite_element_field = field_module.findFieldByName(name)
            if not finite_element_field.isValid():
                finite_element_field = field_module.createFieldFiniteElement(coord_count)
                finite_element_field.setName(name)
            else:
                assert(finite_element_field.getNumberOfComponents() == coord_count)

            # Set the finite element coordinate field for the nodes to use
            node_template.defineField(finite_element_field)
            finite_element_fields.append(finite_element_field)
        
        field_cache = field_module.createFieldcache()
        
        node_id = start_node_id
        # Create nodes and add to field cache
        for coords in coordinate_set:
            if not merge:
                node = nodeset.createNode(-1, node_template)
                # Set the node coordinates, first set the field cache to use the current node
                field_cache.setNode(node)
                # Pass in floats as an array
                for finite_element_field in finite_element_fields:
                    finite_element_field.assignReal(field_cache, coords)
            else:
                node = nodeset.findNodeByIdentifier(node_id)
                if node.isValid():
                    field_cache.setNode(node)
                    node.merge(node_template)
                    for finite_element_field in finite_element_fields:
                        finite_element_field.assignReal(field_cache, coords)
                    node_id += 1
                else:
                    raise RuntimeError("Invalid node with id%d" % node_id)
                
        for finite_element_field in finite_element_fields:
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

def _find_mesh_dimension(basis_order, element_set):
    """
    Work out the dimension of the mesh by the number of nodes in the first element
    """
    element_node_count = len(element_set[0])
    float_dimension = math.log(element_node_count, basis_order+1)
    dimension = int(round(math.log(element_node_count, basis_order+1)))
    assert(float_dimension - dimension == 0.0)
    if float_dimension - dimension != 0.0:
        raise RuntimeError("Wrong number of nodes in element. Got %d expected %d." \
                           % (element_node_count, math.pow(basis_order+1, dimension)))
    #if __debug__: print "mesh basis_order", basis_order, "dimension", dimension
    return dimension

def _lagrange_mesh(mymesh, basis_order, node_coordinate_set, element_set, **kwargs):
    '''
    Create linear finite elements given node and element lists
    param: mesh a mesh or meshGroup
    param: order order of Lagrange interpolation 1 = linear, 2 = quadratic, 3 = cubic
    '''
    # Parse kwargs    
    coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')
    merge = kwargs.get('merge', False)
    start_node_id = kwargs.get('start_node_id', 1)
    start_element_id = kwargs.get('start_element_id', 1)

    if isinstance(coordinate_field_name, list):
        coordinate_fields = coordinate_field_name
    else:
        coordinate_fields = [coordinate_field_name] 

    use_existing_nodes = kwargs.get('use_existing_nodes', False)

    #coord_fields = kwargs.get('coordinate_field_list', [])
    
    if len(element_set) == 0:
        raise RuntimeError("Empty element list") 

    if len(node_coordinate_set) == 0:
            use_existing_nodes = True

    with get_field_module(mymesh) as fm:

        nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        if use_existing_nodes:
            if not nodeset.isValid():
                raise RuntimeError("The node list was empty and could not find a nodeset for the given mesh")
        else:
            _coordinate_field(nodeset, node_coordinate_set, coordinate_fields, merge, start_node_id)
    
        # Create and configure an element template for the appropriate mesh type.
        element_node_count = len(element_set[0])

        dimension = _find_mesh_dimension(basis_order, element_set)
        assert(dimension == mymesh.getDimension())

        #mesh = fm.findMeshByDimension(dimension)
        element_template = mymesh.createElementtemplate()
        
        element_template.setElementShapeType(_shape_type_map[dimension])
        element_template.setNumberOfNodes(element_node_count)
        
        # Specify the dimension and the interpolation function for the element basis function
        basis_type = _basis_type_map[basis_order]
        basis = fm.createElementbasis(
               dimension,
               basis_type)
        
        # the indices of the nodes in the node template we want to use.
        local_indices = [x for x in xrange(1, element_node_count+1)]
        
        # Define a nodally interpolated element field or field component in the
        # element_template
        for coordinate_field_name in coordinate_fields:
            finite_element_field = fm.findFieldByName(coordinate_field_name)
            element_template.defineFieldSimpleNodal(finite_element_field,
                                                    -1,
                                                    basis,
                                                    local_indices)

        # create the elements
        new_elems = []
        element_id = start_element_id
        for node_indices in element_set:
            #print funcname(), "element_id", element_id
            def _populateTemplate():
                for i, node_idx in enumerate(node_indices):
                    node = nodeset.findNodeByIdentifier(node_idx)
                    element_template.setNode(i + 1, node)
                
            if not merge:
                _populateTemplate()
                element = mymesh.createElement(-1, element_template)
            else:
                element = mymesh.findElementByIdentifier(element_id)
                _populateTemplate()
                 
                element.merge(element_template)
                
            new_elems.append(element)

            element_id += 1

        fm.defineAllFaces()
        
        # workaround to ensure elements get added to group, if mymesh is a MeshGroup
        grp = mymesh.castGroup()
        if grp.isValid():
            for elem in new_elems:
                mymesh.addElement(elem)


def linear_mesh(mesh, node_coordinate_set, element_set, **kwargs):
    _lagrange_mesh(mesh, 1, node_coordinate_set, element_set, **kwargs)


def quadratic_lagrange_mesh(ctxt, region, node_coordinate_set, element_set, **kwargs):
    _lagrange_mesh(ctxt, region, 2, node_coordinate_set, element_set, **kwargs)


def cubic_lagrange_mesh(themesh, node_coordinate_set, element_set, **kwargs):
    _lagrange_mesh(themesh, 3, node_coordinate_set, element_set, **kwargs)
    

def define_datapoints(nodeset, coordinate_set, field_name='data_coordinates', merge=False):
     
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty datapoint coordinate list") 
                 
    _coordinate_field(nodeset, coordinate_set, field_name, merge)
    

def define_nodes(nodeset, coordinate_set, field_name='coordinates', merge=False):
    if len(coordinate_set) == 0:
        raise RuntimeError("Empty node coordinate list") 

    _coordinate_field(nodeset, coordinate_set, field_name, merge)


def generate_xi_locations(xi, ndim):
    """
    @param xi: list of the 1D xi coords
    @param ndim: number of coordinates  
    """
    assert(1 <= ndim <= 3)
    n = ndim
    # generate indices
    idx = np.indices([len(xi)] * n)
    # get xi coord values from indices
    # iterate from 2 to 0 so that xi1 changes fastest
    v = [xi[idx[i]] for i in xrange(n-1, -1, -1)]
    # reshape
    coords = np.hstack([v[i].reshape(-1,1) for i in xrange(n)])
    return coords


def linear_to_cubic(mesh_cubic, nodes, elements, tol=1e-4, **kwargs):
    """
    Convert a 3D linear mesh to cubic Lagrange 
    """

    # Implementation notes:
    # Load the linear mesh into zinc as it will be need to interpolate
    # the positions of the internal nodes
    
    # Copy the linear mesh nodes into a new region
    # For each linear element
    #    get the location of xi=0,0,0
    #    search for an existing node at this location
    #    if not found:
    #        create a new node
    #    add the node to the element at the correct index
    
    # Use rtree for finding already created nodes. This is about 300 times
    # faster than a linear search.
    # http://toblerity.org/rtree/
    from rtree import index
    
    coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')

    if isinstance(coordinate_field_name, list):
        coordinate_fields = coordinate_field_name
    else:
        coordinate_fields = [coordinate_field_name] 

    #merge = kwargs.get('merge', False)
    region_cubic = mesh_cubic.getFieldmodule().getRegion()
    
    # Create a linear mesh in a temporary region for interpolating the nodal positions
    region_linear = region_cubic.createChild("temporary")
    dimension = _find_mesh_dimension(basis_order=1, element_set=elements)
    
    with get_field_module(region_linear) as fm:
        mymesh = fm.findMeshByDimension(dimension)
    
    linear_mesh(mymesh, nodes, elements, coordinate_field_name=coordinate_fields[0])
    
    with get_field_module(region_linear) as d_fm, \
                                get_field_module(region_cubic) as fm:
        lin_coordinates = d_fm.findFieldByName(coordinate_fields[0])
        d_fc = d_fm.createFieldcache()
        
        # Copy the nodes from the linear mesh into the new region, these will
        # become the corner nodes of the cubic Lagrange mesh.
        nodeset = d_fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodes = nodes_to_list(nodeset)
        
        nodeset_cubic = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        define_nodes(nodeset_cubic, nodes, coordinate_fields)
                
        # precompute the xi coordinates
        xi = np.linspace(0, 1, 4)
        xi_coords = generate_xi_locations(xi, ndim=dimension)
            
        # iterate over the elements in the temporary linear mesh
        initial_mesh = d_fm.findMeshByDimension(dimension)
        
        # coords field and cache for the new field
        #coordinates = fm.findFieldByName(coordinate_fields[0])
        fc = fm.createFieldcache()

        # Create a 3D Rtree
        p = index.Property()
        p.dimension = 3
        idx3d = index.Index(properties=p)

        for i, n in enumerate(nodes):
            # add 1 to index because zinc counts nodes starting at 1
            idx3d.insert(i+1, n + n)
            #print "added node", i+1, n

        finite_element_fields = []

        # Create a template for defining new nodes
        nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        node_template = nodeset.createNodetemplate()
        for field_name in coordinate_fields:
            finite_element_field = fm.findFieldByName(field_name)
            node_template.defineField(finite_element_field)
            finite_element_fields.append(finite_element_field)

        ele_count = 0
        cubic_elements = []
        el_iter = initial_mesh.createElementiterator()
        element = el_iter.next()
        while element.isValid():
            #print "element", elements[ele_count]
            ele_count += 1
            new_element = []
#             if __debug__:
#                 elem_id = element.getIdentifier()
#                 print  funcname(), "elem_id", elem_id

            for xi in xi_coords:
                # print "xi", xi1, xi2, xi3
#                 print "xi", xi
                d_fc.setMeshLocation(element, xi.tolist())#[xi1, xi2, xi3])
                result, outValues = lin_coordinates.evaluateReal(d_fc, 3)
                # add a tolerance to the search area
                bb = np.array(outValues)
                bb_min = bb - tol
                bb_max = bb + tol
                #print bb, bb_min, bb_max
                # Find the node in the kDtree
                found = list(idx3d.intersection(bb_min.tolist() + bb_max.tolist()))
                # print "found", found, "at", outValues
                if len(found) == 0:
                    node_id = None
                else:
                    node_id = found[0]
                    #print "found node", node_id
                    
                if node_id == None:
                    #create a new node
                    new_node = nodeset.createNode(-1, node_template)
                    fc.setNode(new_node)
                    # Pass in floats as an array
                    for finite_element_field in finite_element_fields:
                        finite_element_field.assignReal(fc, outValues)
                    
                    node_id = new_node.getIdentifier()
                    idx3d.insert(node_id, outValues + outValues)
                    # print "created node", node_id  

                new_element.append(node_id)

            element = el_iter.next()
            cubic_elements.append(new_element)

        region_cubic.removeChild(region_linear)

        # The nodes have already been added to the region so use these existing nodes
        mymesh = fm.findMeshByDimension(dimension)
        cubic_lagrange_mesh(mymesh, [], cubic_elements, coordinate_field_name=coordinate_fields, merge=False)


def _nodes_to_list(nodeset, numValues=3, coordFieldName='coordinates'):
    """
    Extract nodes into a Python list
    """
    fm = nodeset.getFieldmodule()
    field = fm.findFieldByName(coordFieldName)

    # extract the list of nodes 
    node_list = []
    node_iter = nodeset.createNodeiterator()
    cache = fm.createFieldcache()
    count = 0
    node = node_iter.next()
    while node.isValid():
        cache.setNode(node)
        result, outValues = field.evaluateReal(cache, numValues)
        node_list.append(outValues)
        node = node_iter.next()
        count += 1

    return node_list

def _update_nodes(nodeset, coordinate_set, nodesetName, coordFieldName='coordinates'):
    """
    Update nodes with the coordinates in the given coordinate_set (as a Python List).
    """
    
    # Update nodes with new coordinates 
    with get_field_module(nodeset) as fm:
        field = fm.findFieldByName(coordFieldName)
        
        num_nodes = nodeset.getSize()
        if num_nodes != len(coordinate_set):
            raise RuntimeError("Update list must have the same number of nodes as the nodeset. Got %d nodeset has %d."
                               % (len(coordinate_set), num_nodes))

        cache = fm.createFieldcache()
        node_id = 1
        for coords in coordinate_set:
            node = nodeset.findNodeByIdentifier(node_id)
            cache.setNode(node)
            result = field.assignReal(cache, coords)
            node_id += 1
            
    
def nodes_to_list(nodeset, numValues=3, coordFieldName='coordinates'):
    """
    Return all nodes as a Python list
    """
    return _nodes_to_list(nodeset, numValues, coordFieldName)

def update_nodes(nodeset, node_list, coordFieldName='coordinates'):
    """
    Update nodes from a list of coordinates
    """
    _update_nodes(nodeset, node_list, Field.DOMAIN_TYPE_NODES, coordFieldName)

def data_to_list(nodeset, numValues=3, coordFieldName='data_coordinates'):
    """
    Return all datapoints as a Python list
    """
    return _nodes_to_list(nodeset, numValues, coordFieldName)

def update_data(nodeset, node_list, coordFieldName='data_coordinates'):
    """
    Generate datapoints from a list of coordinates
    """
    _update_nodes(nodeset, node_list, Field.DOMAIN_TYPE_NODES, coordFieldName)

    
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
    nodes = np.loadtxt(filename)
    return nodes.tolist()
