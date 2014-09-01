from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph

from tools.utilities import get_scene

#from tools.diagnostics import funcname

_defaultGraphicsCreated = False


def defineStandardGlyphs(context):
    '''
    Helper method to define the standard glyphs.
    '''
    glyph_module = context.getGlyphmodule()
    glyph_module.defineStandardGlyphs()


def defineStandardMaterials(context):
    '''
    Helper method to define the standard materials.
    '''
    material_module = context.getMaterialmodule()
    material_module.defineStandardMaterials()


def _createDefaultGraphics(scene):
    global _defaultGraphicsCreated
    if not _defaultGraphicsCreated:
        glyph_module = scene.getGlyphmodule()
        glyph_module.defineStandardGlyphs()
        _defaultGraphicsCreated = True
        material_module = scene.getMaterialmodule()
        material_module.defineStandardMaterials()


def createDatapointGraphics(region, **kwargs):
    
    with get_scene(region) as scene:
        #_createDefaultGraphics(ctxt)
        glyph_module = scene.getGlyphmodule()
        glyph_module.defineStandardGlyphs()
    
        materials_module = scene.getMaterialmodule()
        materials_module.defineStandardMaterials()
    
        colour = kwargs.get('colour', 'green')
        materials_module = scene.getMaterialmodule()
        mat = materials_module.findMaterialByName(colour)
    
        field_module = region.getFieldmodule()

        coordinate_field_name = kwargs.get('coordinate_field_name', 'data_coordinates')
                    
        data_coordinates = field_module.findFieldByName(coordinate_field_name)
        diamonds = scene.createGraphicsPoints()
        diamonds.setCoordinateField(data_coordinates)
        diamonds.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        att = diamonds.getGraphicspointattributes()
        att.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND)
        diamonds.setMaterial(mat)
        
        base_size = kwargs.get('datapoints_size', 1)
        att.setBaseSize(base_size)
        
        label_field_name = kwargs.get('datapoints_label')
        if label_field_name:
            if label_field_name == 'id':
                label_field_name = 'cmiss_number' 
            cmiss_number_field = field_module.findFieldByName(label_field_name)
            #print funcname(), "cmiss_number_field.isValid()", cmiss_number_field.isValid()
            att.setLabelField(cmiss_number_field)
    
        datapoints_name = kwargs.get('datapoints_name')
        if datapoints_name:
            diamonds.setName(datapoints_name)
    # returning a tuple to make it consistent with createSurfaceGraphics
    return (diamonds, )


def createNodeGraphics(region, **kwargs):

    _createDefaultGraphics(region.getScene())

    field_module = region.getFieldmodule()

    # Get the scene for the default region to create the visualisation in.
    with get_scene(region) as scene:

        coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')
        finite_element_field = field_module.findFieldByName(coordinate_field_name)
    
        colour = kwargs.get('colour', 'white')
        materials_module = scene.getMaterialmodule()
        mat = materials_module.findMaterialByName(colour)

    #     # Diagnositics    
    #     fm = field_module
    #     sNodes = fm.findNodesetByName('nodes')
    #     print "sNodes.getSize()", sNodes.getSize()
         
        spheres = scene.createGraphicsPoints()
        spheres.setCoordinateField(finite_element_field)
        subGroupField = kwargs.get("sub_group_field", None)
        if subGroupField:
            spheres.setSubgroupField(subGroupField)

        spheres.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        att = spheres.getGraphicspointattributes()
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
            
            #print "cmiss_number_field.isValid()", cmiss_number_field.isValid()
            att.setLabelField(cmiss_number_field)
    
        if 'nodes_name' in kwargs:
            spheres.setName(kwargs['nodes_name'])
        
        spheres.setMaterial(mat)
            
    # returning a tuple to make it consistent with createSurfaceGraphics
    return (spheres, )  


def createLineGraphics(region, **kwargs):
    '''
    Create graphics for the default region.
    Keyword arguments that are currently supported:
    node_size
    node_label
    datapoint_size
    datapoint_label
    '''

    _createDefaultGraphics(region.getScene())

    field_module = region.getFieldmodule()
    # Get the scene for the default region to create the visualisation in.

    with get_scene(region) as scene:

        coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')
        finite_element_field = field_module.findFieldByName(coordinate_field_name)

        colour = kwargs.get('colour', 'white')
        materials_module = scene.getMaterialmodule()
        mat = materials_module.findMaterialByName(colour)
        
         
        # Create line graphics
        lines = scene.createGraphicsLines()
        lines.setCoordinateField(finite_element_field)
        if 'lines_name' in kwargs:
            lines.setName(kwargs['lines_name'])
        lines.setMaterial(mat)
        
        att = lines.getGraphicslineattributes()
        att.setBaseSize([1,1,1])

        subGroupField = kwargs.get("sub_group_field", None)
        if subGroupField:
            lines.setSubgroupField(subGroupField)

    return (lines,)


def createSurfaceGraphics(region, **kwargs):
    '''
    Create graphics for the default region.
    Keyword arguments that are currently supported:
    node_size
    node_label
    datapoint_size
    datapoint_label
    '''

    _createDefaultGraphics(region.getScene())

    field_module = region.getFieldmodule()
    # Get the scene for the default region to create the visualisation in.

    with get_scene(region) as scene:

        coordinate_field_name = kwargs.get('coordinate_field_name', 'coordinates')
        finite_element_field = field_module.findFieldByName(coordinate_field_name)

        colour = kwargs.get('colour', 'white')
        materials_module = scene.getMaterialmodule()
        mat = materials_module.findMaterialByName(colour)
         
        surfaces = scene.createGraphicsSurfaces()
        surfaces.setCoordinateField(finite_element_field)
        if 'surfaces_name' in kwargs:
            surfaces.setName(kwargs['surfaces_name'])
     
        surfaces.setName(kwargs['surfaces_name'])
        surfaces.setMaterial(mat)
        subGroupField = kwargs.get("sub_group_field", None)
        if subGroupField:
            surfaces.setSubgroupField(subGroupField)
        
        ext = kwargs.get('exterior', False)
        if ext:
            surfaces.setExterior(True)
            
    return (surfaces,)
