'''
Created on 2/05/2014

@author: glenn
'''
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

    @unittest.skip("")
    def test_linear(self):
        c = Context("test_linear_to_cubic")
        region = c.createRegion()
        mesh.linear_mesh(c, region, node_coordinate_set, element_set_3d)
    
    #@unittest.skip("")
    def test_linear_to_cubic(self):
        c = Context("test_linear_to_cubic")
        region_linear = c.createRegion()
        region_linear.setName("linear")
        region_cubic = c.createRegion()
        region_cubic.setName("cubic_lagrange")
        mesh.linear_to_cubic(c, region_linear, region_cubic, node_coordinate_set, element_set_3d)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()