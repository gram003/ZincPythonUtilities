
import sys
sys.path.append("..")
import os
import math

import unittest
from opencmiss.zinc.context import Context
from opencmiss.zinc.field import Field
from tools import mesh
from tools.utilities import get_field_module

import numpy as np

node_coordinate_set = [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [3.0, 2.0, 0.0],
                        [0.0, 0.0, 2.0], [3.0, 0.0, 2.0], [0.0, 4.0, 2.0], [3.0, 2.0, 2.0],
                        [5.0, 0.0, 0.0], [5.0, 2.0, 0.0], [5.0, 0.0, 2.0], [5.0, 2.0, 2.0]]

element_set_3d = [[1, 2, 3, 4, 5, 6, 7, 8],
               [2, 9, 4, 10, 6, 11, 8, 12]]

node_coordinate_set_2d = [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [3.0, 2.0, 0.0]]

element_set_2d = [[1, 2, 3, 4]]


import filecmp


def generate_fitting_data(fname):
    xmax = 10
    npoints = 10
    x = np.linspace(1, xmax-1, npoints, endpoint=True)
    print x
    coords = mesh.generate_xi_locations(x, 2)
    scale = 2*math.pi/xmax
    data = []
    for i, c in enumerate(coords.tolist()):
        #print i, c,
        #z = 1- 0.5*(math.cos(c[0]*scale) + math.cos(c[1]*scale))
        z = 1 - math.cos(c[0]*scale)
        z2 = 1 - math.sin(c[1]*scale)
        #print z, z2, z + z2 - 1
        data.append([c[0], c[1], z + z - 1])#z + z2 - 1])

    np.savetxt(fname, np.array(data))
    

class TestMesh(unittest.TestCase):

    def setUp(self):
        generate_fitting_data("test_2d_fit.data.txt")
        pass

    def tearDown(self):
        pass
    
    #@unittest.skip("")
    def test_coordinate_field(self):
        mergefile = "test_coordinate_field_merged.exregi"
        listfile = "test_coordinate_field_list.exregi"
        
        c = Context("test_coordinate_field")
        region = c.createRegion()
        # read nodes into a Python list
        nodes = mesh.read_txtnode("abi_femur_head.node.txt")

        # Create a nodeset
        with get_field_module(region) as fm:
            nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            mesh._coordinate_field(nodeset, nodes, 'coordinates')
            # Merge another field into the nodeset
            mesh._coordinate_field(nodeset, nodes, 'reference_coordinates', True)

        # save for later comparison
        region.writeFile(mergefile)
        del region

        # Do the same, but this time create the nodeset with both fields at once
        region = c.createRegion()
        with get_field_module(region) as fm:
            nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            mesh._coordinate_field(nodeset, nodes, ['coordinates', 'reference_coordinates'])
        
        region.writeFile(listfile)
        del region
        
        # Make sure that the result is the same
        self.assertTrue(filecmp.cmp(mergefile, listfile))
        
        # comment these to inspect the files manually
        os.unlink(mergefile)
        os.unlink(listfile)
        
    #@unittest.skip("")
    def test_linear(self):
        mergefile = "test_coordinate_field_merged.exregi"
        listfile = "test_coordinate_field_list.exregi"

        c = Context("test_linear_to_cubic")
        region = c.createRegion()
        with get_field_module(region) as fm:
            mesh3d = fm.findMeshByDimension(3)
            mesh.linear_mesh(mesh3d, node_coordinate_set, element_set_3d)
            mesh.linear_mesh(mesh3d, node_coordinate_set, element_set_3d,
                             coordinate_field_name='reference_coordinates', merge=True)
            region.writeFile(mergefile)
            del region

        region = c.createRegion()
        with get_field_module(region) as fm:
            mesh3d = fm.findMeshByDimension(3)
            mesh.linear_mesh(mesh3d, node_coordinate_set, element_set_3d,
                             coordinate_field_name=['coordinates', 'reference_coordinates'])
            region.writeFile(listfile)
            del region

        self.assertTrue(filecmp.cmp(mergefile, listfile))
        
        # comment these to inspect the files manually
        os.unlink(mergefile)
        os.unlink(listfile)
    
    #@unittest.skip("")
    def test_linear_to_cubic_small(self):
        fname = "test_linear_to_cubic_small.exregi"
        try:
            os.unlink(fname)
        except:
            pass
        
        c = Context("test_linear_to_cubic_small")
        region_linear = c.createRegion()
        region_linear.setName("linear")
        region_cubic = c.createRegion()
        region_cubic.setName("cubic_lagrange")
        mesh.linear_to_cubic(c, region_cubic, node_coordinate_set, element_set_3d,
                             coordinate_field_name=['coordinates', 'reference_coordinates'])
        
        region_cubic.writeFile(fname)
        # not sure how to test if it was successful, for now just manually inspect the exregi file

    #@unittest.skip("")
    def test_linear_to_cubic_small_2d(self):
        fname = "test_linear_to_cubic_small_2d.exregi"
        try:
            os.unlink(fname)
        except:
            pass
        
        c = Context("test_linear_to_cubic_small_2d")
        region_linear = c.createRegion()
        region_linear.setName("linear")
        region_cubic = c.createRegion()
        region_cubic.setName("cubic_lagrange")
        mesh.linear_to_cubic(c, region_cubic, node_coordinate_set_2d, element_set_2d,
                             coordinate_field_name=['coordinates', 'reference_coordinates'])
        
        region_cubic.writeFile(fname)

#     @unittest.skip("")
#     def test_linear_to_cubic_small_merge(self):
#         before = "test_linear_to_cubic_small_before_merge.exregi"
#         after = "test_linear_to_cubic_small_after_merge.exregi"
#         os.unlink(before)
#         os.unlink(after)
#         c = Context("test_linear_to_cubic_small")
#         region_linear = c.createRegion()
#         region_linear.setName("linear")
#         region_cubic = c.createRegion()
#         region_cubic.setName("cubic_lagrange")
#         
#         mesh.linear_to_cubic(c, region_linear, region_cubic,
#                              node_coordinate_set, element_set_3d,
#                              coordinate_field_name='coordinates')
#         region_cubic.writeFile(before)
        
#         region_linear = c.createRegion()
#         region_linear.setName("linear")
#         mesh.linear_to_cubic(c, region_linear, region_cubic,
#                              node_coordinate_set, element_set_3d,
#                              coordinate_field_name='reference_coordinates', merge=True)
#         
#         region_cubic.writeFile(after)

        
    #@unittest.skip("")
    def test_linear_to_cubic_medium(self):
        c = Context("test_linear_to_cubic_medium")

        region_cubic = c.createRegion()
        region_cubic.setName("cubic_lagrange")

        nodes = mesh.read_txtnode("abi_femur_head.node.txt")
        elems = mesh.read_txtelem("abi_femur_head.elem.txt")

        mesh.linear_to_cubic(c, region_cubic, nodes, elems,
                             coordinate_field_name=['coordinates', 'reference_coordinates'])
        
        region_cubic.writeFile("test_linear_to_cubic_medium.exregi")

    #@unittest.skip("")
    def test_rtree(self):
        from rtree import index
        nodes = mesh.read_txtnode("abi_femur_head.node.txt")
        
        # Create a kDTree 
        p = index.Property()
        p.dimension = 3
        idx3d = index.Index(properties=p)

        for i, n in enumerate(nodes):
            # add 1 to index because zinc counts nodes starting at 1
            idx3d.insert(i+1, n + n)
            #print "added node", i+1, n
            
        num_found = 0
        for i, n in enumerate(nodes):
            found = list(idx3d.intersection(n + n))
            #print "found", found, "at", n
            if len(found) > 0:
                #print "found node", found[0]
                num_found += 1

        self.assertEqual(num_found, len(nodes), "didn't find all nodes")

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
