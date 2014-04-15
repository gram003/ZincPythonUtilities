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
        self.fitter.load_problem("abi_femur.json")

    def tearDown(self):
        pass

    @unittest.skip("")
    def testRegisterAutomatic(self):
        # for a directory context manager see
        # http://stackoverflow.com/questions/431684/how-do-i-cd-in-python
        f = self.fitter
        f.register_automatic()

    def testMirror(self):
        f = self.fitter
        # Get the list of nodes
        initial = mesh.data_to_list(self.context)
        f.data_mirror(0) # mirror in x axis
        mirrored = mesh.data_to_list(self.context)
        #print initial[0][0], mirrored[0][0]
        self.assertTrue(initial[0][0] == -mirrored[0][0])
        a = np.array(initial)
        b = np.array(mirrored)
        #print a
        #print b
        self.assertFalse(np.allclose(a,b), "Initial and mirrored arrays are equal")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()