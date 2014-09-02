'''
Created on 1/09/2014

@author: glenn
'''

from opencmiss.zinc.field import Field, FieldGroup

from tools import mesh
from tools.utilities import get_field_module

class FitProject(object):
    '''
    A class to contain information about a fitting project
    '''

    def __init__(self, project_path, root_region):
        self._project_path = project_path
        self._root_region = root_region
        self._coords_name = 'coordinates'
        self._ref_coords_name = 'reference_coordinates'
        self._data_coords_name = 'data_coordinates'
        
        self._nodes = None
        self._elements = None
        self._basis_order = 1
    
    def save_project(self):
        with open(self._project_path, 'w') as f:
            out = self._serialise()
            f.write(out)
    
    def import_data(self, data_path, region=None):
        # FIXME: make this relative to the project file
        self._data_path = data_path
        
        # returns a python list
        datapoints = mesh.read_txtnode(data_path)
        
        if region is None:
            region = self._root_region 

        fm = region.getFieldmodule()
        sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        mesh.define_datapoints(sNodes, datapoints)        
    
    def import_nodes(self, nodes_path, region=None):
        self._nodes_path = nodes_path
        
        # returns a python list
        self._nodes = mesh.read_txtnode(nodes_path)

        if region is None:
            region = self._root_region 

        with get_field_module(region) as fm:
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

        mesh.define_nodes(sNodes, self._nodes, self._coords_name, merge=False)
        
        # load the nodes again as reference coordinates
        mesh.define_nodes(sNodes, self._nodes, self._ref_coords_name, merge=True)
        
        return self._define_mesh(region)
        
    def import_elements(self, element_path, region=None):
        self._elements = mesh.read_txtelem(element_path)

        if region is None:
            region = self._root_region 
        
        return self._define_mesh(region)
    
    def import_mesh(self, node_path, element_path, region):
        self.import_nodes(node_path, region)        
        self.import_elements(element_path, region)
    
    def _define_mesh(self, region):
        gfModel = None
        if self._nodes and self._elements:
            dimension = mesh.find_mesh_dimension(self._basis_order, self._elements)
            
            with get_field_module(region) as fm:
                # Load the mesh into a group named 'model'
                gfModel = fm.createFieldGroup()
                gfModel.setSubelementHandlingMode(FieldGroup.SUBELEMENT_HANDLING_MODE_FULL)
                gfModel.setManaged(True) # prevent group from being destroyed when not in use
                gfModel.setName('model')
                meshModel = fm.findMeshByDimension(dimension)
                modelElemGroup = gfModel.createFieldElementGroup(meshModel)
                meshGroup = modelElemGroup.getMeshGroup()
                sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
                if sNodes.getSize() > 0:
                    nodes = []
                    use_existing_nodes = True
                else:
                    nodes = self._nodes
                    use_existing_nodes = False
                        
                mesh.linear_mesh(meshGroup, nodes, self._elements,
                                 coordinate_field_name=self._coords_name,
                                 use_existing_nodes=use_existing_nodes)

                # Load the mesh again, this time merging with the previous mesh
                # and renaming the coordinate field to reference_coordinates.
                # This adds another set of coordinates at each node.
                mesh.linear_mesh(meshGroup, self._nodes, self._elements,
                                 coordinate_field_name=self._ref_coords_name, merge=True)
            
        return gfModel
        

    def _serialise(self):
        import jsonpickle
        #out = json.dumps(self.__dict__)
        out = jsonpickle.encode(self)
        
        if __debug__:
            import json # use this to pretty print the json
            print json.dumps(json.loads(out), indent=4)
        
        return out
    
    @staticmethod
    def deserialise(project_path):
        import jsonpickle
        with open(project_path, 'r') as f: 
            project = jsonpickle.decode(f.read())
        
        return project
    