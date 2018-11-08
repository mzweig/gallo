from nose.tools import *
from numpy.testing import *
import numpy as np
import scipy.sparse as sps
import scipy.sparse.linalg as linalg

from gallo.formulations.diffusion import Diffusion
from gallo.fe import FEGrid
from gallo.materials import Materials
from gallo.plot import plot

class TestDiffusion():
    @classmethod
    def setup_class(cls):
        cls.nodefile = "test/test_inputs/box_source.node"
        cls.elefile = "test/test_inputs/box_source.ele"
        cls.matfile = "test/test_inputs/box_source.mat"
        cls.fegrid = FEGrid(cls.nodefile, cls.elefile)
        cls.materials = Materials(cls.matfile)
        cls.operator = Diffusion(cls.fegrid, cls.materials)
        cls.stdnode = "test/test_inputs/std.node"
        cls.stdele = "test/test_inputs/std.ele"
        cls.stdgrid = FEGrid(cls.stdnode, cls.stdele)
        cls.fissionfile = "test/test_inputs/fissiontest.mat"
        cls.fissionmat = Materials(cls.fissionfile)
        cls.fissop = Diffusion(cls.stdgrid, cls.fissionmat)

    def test_matrix(self):
        A = self.operator.make_lhs(0)
        assert (A!=A.transpose()).nnz==0
        assert (A.diagonal() >= 0).all()

    def test_fission_source(self):
        A = self.fissop.compute_fission_source(0, np.array([1]), 0)
        assert (A == 1)

    def test_fiss_rhs(self):
        rhs = self.fissop.make_rhs(0, np.array([[0, 0, 0, 0]]), np.array([[1, 1, 1, 1]]))
        assert_array_almost_equal(rhs, np.array([1/6, 1/3, 1/6, 1/3]), 10)
