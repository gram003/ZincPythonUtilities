
# removed from ZincWidget
def create3DFiniteElement(self, field_module, finite_element_field, node_coordinate_set):
    '''
    Create finite element from a template
    '''
    # Find a special node set named 'nodes'
    nodeset = field_module.findNodesetByName('nodes')
    node_template = nodeset.createNodetemplate()

    # Set the finite element coordinate field for the nodes to use
    node_template.defineField(finite_element_field)
    field_cache = field_module.createFieldcache()

    node_identifiers = []
    # Create eight nodes to define a cube finite element
    for node_coordinate in node_coordinate_set:
        node = nodeset.createNode(-1, node_template)
        node_identifiers.append(node.getIdentifier())
        # Set the node coordinates, first set the field cache to use the current node
        field_cache.setNode(node)
        # Pass in floats as an array
        finite_element_field.assignReal(field_cache, node_coordinate)

    # Use a 3D mesh to to create the 3D finite element.
    mesh = field_module.findMeshByDimension(3)
    element_template = mesh.createElementtemplate()
    element_template.setElementShapeType(Element.SHAPE_TYPE_CUBE)
    element_node_count = 8
    element_template.setNumberOfNodes(element_node_count)
    # Specify the dimension and the interpolation function for the element basis function
    linear_basis = field_module.createElementbasis(3, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
    # the indicies of the nodes in the node template we want to use.
    node_indexes = [1, 2, 3, 4, 5, 6, 7, 8]


    # Define a nodally interpolated element field or field component in the
    # element_template
    element_template.defineFieldSimpleNodal(finite_element_field, -1, linear_basis, node_indexes)

    for i, node_identifier in enumerate(node_identifiers):
        node = nodeset.findNodeByIdentifier(node_identifier)
        element_template.setNode(i + 1, node)

    mesh.defineElement(-1, element_template)


# Diagnostics for data points    
#         region = self.context().getDefaultRegion()
#         scene = region.getScene()
# #         dp = scene.createGraphicsPoints()
# #         dp.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
#         fm = region.getFieldmodule()
# #         for i in xrange(10):
# #             fm.endChange()
#         coordinateField = fm.findFieldByName('data_coordinates')
# #         dp.setCoordinateField(coordinateField)
# #         gr = scene.getFirstGraphics()
# #         while gr.isValid():
# #             name = gr.getName()
# #             if name == 'data':
# #                 gr.setCoordinateField(Field())
# #                 gr.setCoordinateField(coordinateField)
# #             dt = gr.getFieldDomainType()
# #             print(name, dt, gr.getCoordinateField().getName())
# #             gr = scene.getNextGraphics(gr)
