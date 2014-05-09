
import sys
sys.path.append("..")
import os

import unittest
from opencmiss.zinc.context import Context
from tools import mesh

node_coordinate_set = [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [3.0, 2.0, 0.0],
                        [0.0, 0.0, 2.0], [3.0, 0.0, 2.0], [0.0, 4.0, 2.0], [3.0, 2.0, 2.0],
                        [5.0, 0.0, 0.0], [5.0, 2.0, 0.0], [5.0, 0.0, 2.0], [5.0, 2.0, 2.0]]

element_set_3d = [[1, 2, 3, 4, 5, 6, 7, 8],
               [2, 9, 4, 10, 6, 11, 8, 12]]

import filecmp

class TestMesh(unittest.TestCase):

    def setUp(self):
        
        pass

    def tearDown(self):
        pass
    
    @unittest.skip("")
    def test_coordinate_field(self):
        mergefile = "test_coordinate_field_merged.exregi"
        listfile = "test_coordinate_field_list.exregi"
        
        c = Context("test_coordinate_field")
        region = c.createRegion()
        nodes = mesh.read_txtnode("abi_femur_head.node.txt")

        # Create a nodeset
        mesh._coordinate_field(c, region, nodes, 'nodes', 'coordinates')
        
        # Merge another field into the nodeset
        mesh._coordinate_field(c, region, nodes, 'nodes', 'reference_coordinates', True)
        # save for later comparision
        region.writeFile(mergefile)
        del region

        # Do the same, but this time create the nodeset with both fields
        region = c.createRegion()
        mesh._coordinate_field(c, region, nodes, 'nodes', ['coordinates', 'reference_coordinates'])
        region.writeFile(listfile)
        del region
        
        # Make sure that the result is the same
        self.assertTrue(filecmp.cmp(mergefile, listfile))
        
        # comment these to inspect the files manually
        os.unlink(mergefile)
        os.unlink(listfile)
        
    @unittest.skip("")
    def test_linear(self):
        mergefile = "test_coordinate_field_merged.exregi"
        listfile = "test_coordinate_field_list.exregi"

        c = Context("test_linear_to_cubic")
        region = c.createRegion()
        mesh.linear_mesh(c, region, node_coordinate_set, element_set_3d)
        mesh.linear_mesh(c, region, node_coordinate_set, element_set_3d,
                         coordinate_field_name='reference_coordinates', merge=True)
        region.writeFile(mergefile)
        del region

        region = c.createRegion()
        mesh.linear_mesh(c, region, node_coordinate_set, element_set_3d,
                         coordinate_field_name=['coordinates', 'reference_coordinates'])
        region.writeFile(listfile)
        del region

        self.assertTrue(filecmp.cmp(mergefile, listfile))
        
        # comment these to inspect the files manually
        os.unlink(mergefile)
        os.unlink(listfile)
    
    @unittest.skip("")
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

    @unittest.skip("")
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
