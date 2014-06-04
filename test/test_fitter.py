'''
Created on 15/04/2014

@author: glenn
'''
import os
import sys
sys.path.append("..")

import unittest

from fitter import Fitter
from opencmiss.zinc.context import Context
import tools.mesh as mesh
import numpy as np

class Test(unittest.TestCase):

    def setUp(self):
        self.context = Context("TestContext")
        self.fitter = Fitter(self.context)
        self.savedDir = os.getcwd()

    def tearDown(self):
        pass
    
    def register(self):
        f = self.fitter
        f.register_automatic(translate=True, rotate=False, scale=False)
        f.mirror_data(1) # mirror in y axis
        f.register_automatic(translate=True, rotate=True)
        
        

    @unittest.skip("")
    def testRegisterAutomatic(self):
        # for a directory context manager see
        # http://stackoverflow.com/questions/431684/how-do-i-cd-in-python
        f = self.fitter
        f.load_problem("abi_femur.json")
        initial = mesh.nodes_to_list(self.context)
        f.register_automatic()
        registered = mesh.nodes_to_list(self.context)
        print initial[0][0], registered[0][0]
        a = np.array(initial)
        b = np.array(registered)
        self.assertFalse(np.allclose(a,b), "Initial and registered arrays are equal")
        

    @unittest.skip("")
    def testMirror(self):
        f = self.fitter
        f.load_problem("abi_femur.json")
        # Get the list of nodes
        initial = mesh.data_to_list(self.context)
        f.data_mirror(0) # mirror in x axis
        mirrored = mesh.data_to_list(self.context)
        #print initial[0][0], mirrored[0][0]
        # can't do this because it now mirrors about a plane through the centroid
        #self.assertTrue(initial[0][0] == -mirrored[0][0])
        a = np.array(initial)
        b = np.array(mirrored)
        print a
        print b
        self.assertFalse(np.allclose(a,b), "Initial and mirrored arrays are equal")

    #@unittest.skip("")
    def testConvertToCubic(self):
        f = self.fitter
        path = "test_2d_fit.json"
        f.load_problem(path)
        
        # convert to cubic
        f.convert_to_cubic()
        
        # FIXME: how to know that it worked? It didn't throw an exception?
        



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()