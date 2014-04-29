from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph

from tools.utilities import get_scene

#from tools.diagnostics import funcname

_defaultGraphicsCreated = False


def defineStandardGlyphs(self, context):
    '''
    Helper method to define the standard glyphs.
    '''
    glyph_module = context.getGlyphmodule()
    glyph_module.defineStandardGlyphs()


def defineStandardMaterials(self, context):
    '''
    Helper method to define the standard materials.
    '''
    material_module = context.getMaterialmodule()
    material_module.defineStandardMaterials()


def _createDefaultGraphics(context):
    global _defaultGraphicsCreated
    if not _defaultGraphicsCreated:
        glyph_module = context.getGlyphmodule()
        glyph_module.defineStandardGlyphs()
        _defaultGraphicsCreated = True
        material_module = context.getMaterialmodule()
        material_module.defineStandardMaterials()


def createDatapointGraphics(ctxt, **kwargs):
    
    #_createDefaultGraphics(ctxt)
    glyph_module = ctxt.getGlyphmodule()
    glyph_module.defineStandardGlyphs()

    default_region = ctxt.getDefaultRegion()

    materials_module = ctxt.getMaterialmodule()
    materials_module.defineStandardMaterials()
    green = materials_module.findMaterialByName('green')

    field_module = default_region.getFieldmodule()

    with get_scene(default_region) as scene:
                    
        data_coordinates = field_module.findFieldByName('data_coordinates')
        diamond = scene.createGraphicsPoints()
        diamond.setCoordinateField(data_coordinates)
        diamond.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        att = diamond.getGraphicspointattributes()
        att.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND)
        diamond.setMaterial(green)
        
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
            diamond.setName(datapoints_name)


def createNodeGraphics(ctxt, **kwargs):

    _createDefaultGraphics(ctxt)

    default_region = ctxt.getDefaultRegion()
    field_module = default_region.getFieldmodule()

    # Get the scene for the default region to create the visualisation in.
    with get_scene(default_region) as scene:

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
    field_module = default_region.getFieldmodule()
    # Get the scene for the default region to create the visualisation in.

    with get_scene(default_region) as scene:

        # createSurfaceGraphic graphic start
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
     
