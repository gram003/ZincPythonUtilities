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
from opencmiss.zinc.field import Field
from tools.utilities import get_scene, get_field_module

import tools.mesh as mesh
import numpy as np

class TestFitter(unittest.TestCase):

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


    #@unittest.skip("")
    def testRegisterAutomatic(self):
        # for a directory context manager see
        # http://stackoverflow.com/questions/431684/how-do-i-cd-in-python
        f = self.fitter
        f.load_problem("abi_femur.json")
        region = f._region_linear
        fm = region.getFieldmodule()
        nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)

        initial = mesh.nodes_to_list(nodeset)
        f.register_automatic()
        registered = mesh.nodes_to_list(nodeset)
        print initial[0][0], registered[0][0]
        a = np.array(initial)
        b = np.array(registered)
        self.assertFalse(np.allclose(a,b), "Initial and registered arrays are equal")
        

    #@unittest.skip("")
    def testMirror(self):
        f = self.fitter
        f.load_problem("abi_femur.json")
        
        region = f._region_linear
        fm = region.getFieldmodule()
        nodeset = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)

        # Get the list of nodes        
        initial = mesh.data_to_list(nodeset)
        f.data_mirror(0) # mirror in x axis
        mirrored = mesh.data_to_list(nodeset)
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
        
    #@unittest.skip("")
    def testCreateHostMesh(self):
        f = self.fitter
        f.load_problem("abi_femur.json")
        
        with get_field_module(f._region_linear) as fm:
            sNodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            gfModel = fm.findFieldByName('model').castGroup()
            assert(gfModel.isValid())
            gsModel = gfModel.getFieldNodeGroup(sNodes).getNodesetGroup()
            assert(gsModel.isValid())

            f._createBoundingBoxMesh(gsModel, "coordinates")
        
        



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()