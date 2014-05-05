'''
ZLab testa
@author: glenn
'''
import unittest

import zlab

class ZlabTest(unittest.TestCase):

    node_coordinate_set = [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [3.0, 2.0, 0.0],
                            [0.0, 0.0, 2.0], [3.0, 0.0, 2.0], [0.0, 4.0, 2.0], [3.0, 2.0, 2.0],
                            [5.0, 0.0, 0.0], [5.0, 2.0, 0.0], [5.0, 0.0, 2.0], [5.0, 2.0, 2.0]]
    
    element_set_3d = [[1, 2, 3, 4, 5, 6, 7, 8],
                   [2, 9, 4, 10, 6, 11, 8, 12]]
    
    element_set_2d = [[1, 2, 3, 4],
                   [5, 6, 7, 8],
                   [2, 9, 4, 10],
                   [6, 11, 8, 12]]
    
    element_set_1d = [[1, 2],
                   [3, 4],
                   [5, 6],
                   [7, 8],
                   [2, 9],
                   [4, 10],
                   [6, 11],
                   [8, 12]]

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @unittest.skip("")
    def testData(self):
        zlab.data_points(ZlabTest.node_coordinate_set)
        zlab.show()
        import time
        time.sleep(2)
        zlab.close()

    @unittest.skip("")
    def testNodes(self):
        zlab.nodes(ZlabTest.node_coordinate_set)
        zlab.show()
        import time
        time.sleep(2)
        zlab.close()

    @unittest.skip("")
    def testMesh3D(self):
        zlab.linear_mesh(ZlabTest.node_coordinate_set, ZlabTest.element_set_3d)
        zlab.show()
        import time
        time.sleep(2)
        zlab.close()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
