
import sys
sys.path.append("..")

import unittest
from opencmiss.zinc.context import Context
from tools import mesh

node_coordinate_set = [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [3.0, 2.0, 0.0],
                        [0.0, 0.0, 2.0], [3.0, 0.0, 2.0], [0.0, 4.0, 2.0], [3.0, 2.0, 2.0],
                        [5.0, 0.0, 0.0], [5.0, 2.0, 0.0], [5.0, 0.0, 2.0], [5.0, 2.0, 2.0]]

element_set_3d = [[1, 2, 3, 4, 5, 6, 7, 8],
               [2, 9, 4, 10, 6, 11, 8, 12]]

class TestMesh(unittest.TestCase):

    def setUp(self):
        
        pass

    def tearDown(self):
        pass

    #@unittest.skip("")
    def test_linear(self):
        c = Context("test_linear_to_cubic")
        region = c.createRegion()
        mesh.linear_mesh(c, region, node_coordinate_set, element_set_3d)
    
    #@unittest.skip("")
    def test_linear_to_cubic_small(self):
        c = Context("test_linear_to_cubic_small")
        region_linear = c.createRegion()
        region_linear.setName("linear")
        region_cubic = c.createRegion()
        region_cubic.setName("cubic_lagrange")
        mesh.linear_to_cubic(c, region_linear, region_cubic, node_coordinate_set, element_set_3d)
        
        region_cubic.writeFile("test_linear_to_cubic_small.exregi")
        
    #@unittest.skip("")
    def test_linear_to_cubic_medium(self):
        c = Context("test_linear_to_cubic_medium")
        region_linear = c.createRegion()
        region_linear.setName("linear")
        region_cubic = c.createRegion()
        region_cubic.setName("cubic_lagrange")

        nodes = mesh.read_txtnode("abi_femur_head.node.txt")
        elems = mesh.read_txtelem("abi_femur_head.elem.txt")

        mesh.linear_to_cubic(c, region_linear, region_cubic, nodes, elems)
        
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
            if len(found) == 0:
                node_id = None
            else:
                node_id = found[0]
                #print "found node", node_id
                num_found += 1

        self.assertEqual(num_found, len(nodes), "didn't find all nodes")

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
