from nose.tools import *
from numpy.testing import *
import numpy as np

from gallo.fe import FEGrid, setup_ang_quad

class TestFe:
    @classmethod
    def setup_class(cls):
        cls.nodefile = "test/test_inputs/test.node"
        cls.elefile = "test/test_inputs/test.ele"
        cls.fegrid = FEGrid(cls.nodefile, cls.elefile)

        cls.stdnode = "test/test_inputs/std.node"
        cls.stdele = "test/test_inputs/std.ele"
        cls.stdgrid = FEGrid(cls.stdnode, cls.stdele)

    def test_ang_quad(self):
        angs, weights = setup_ang_quad(2)
        s2_angs = np.array([[ 0.57735,  0.57735],
                            [-0.57735,  0.57735],
                            [-0.57735, -0.57735],
                            [ 0.57735, -0.57735]])
        s2_weights = np.array([np.pi, np.pi, np.pi, np.pi])
        assert_array_almost_equal(angs, s2_angs, 5)
        assert_array_equal(weights, s2_weights)
        angs, weights = setup_ang_quad(4)
        s4_angs = np.array([[ 0.86884614,  0.35988786],
                            [ 0.35988786,  0.86884614],
                            [-0.35988786,  0.86884614],
                            [-0.86884614,  0.35988786],
                            [-0.86884614, -0.35988786],
                            [-0.35988786, -0.86884614],
                            [ 0.35988786, -0.86884614],
                            [ 0.86884614, -0.35988786],
                            [ 0.35947479,  0.35947479],
                            [-0.35947479,  0.35947479],
                            [-0.35947479, -0.35947479],
                            [ 0.35947479, -0.35947479]])
        s4_weights = np.array([1.02438721, 1.02438721, 1.02438721,
                               1.02438721, 1.02438721, 1.02438721,
                               1.02438721, 1.02438721, 1.09281823,
                               1.09281823, 1.09281823, 1.09281823])
        assert_array_almost_equal(angs, s4_angs, 5)
        assert_array_almost_equal(weights, s4_weights, 5)


    def test_is_corner(self):
        eq_(self.fegrid.is_corner(0), True)
        eq_(self.fegrid.is_corner(1), True)
        eq_(self.fegrid.is_corner(2), True)
        eq_(self.fegrid.is_corner(3), True)
        eq_(self.fegrid.is_corner(4), False)
        eq_(self.fegrid.is_corner(5), False)
        eq_(self.fegrid.is_corner(6), False)
        eq_(self.fegrid.is_corner(7), False)
        eq_(self.fegrid.is_corner(8), False)
        eq_(self.fegrid.is_corner(9), False)
        eq_(self.fegrid.is_corner(10), False)
        eq_(self.fegrid.is_corner(11), False)
        eq_(self.fegrid.is_corner(12), False)
        eq_(self.fegrid.is_corner(13), False)
        eq_(self.fegrid.is_corner(14), False)
        eq_(self.fegrid.is_corner(15), False)
        eq_(self.fegrid.is_corner(16), False)
        eq_(self.fegrid.is_corner(17), False)
        eq_(self.fegrid.is_corner(18), False)

    def test_evaluate_basis_function(self):
        eq_(self.fegrid.evaluate_basis_function([1, 0, 0], [3, 2]), 1)
        eq_(self.fegrid.evaluate_basis_function([1, 1, 1], [4, 5]), 10)
        eq_(self.fegrid.evaluate_basis_function([2, 0, 2], [6, 1]), 4)
        eq_(self.fegrid.evaluate_basis_function([0, 1, 1], [0, 12]), 12)

    def test_gradient(self):
        num_ele = self.fegrid.num_elts
        for e in range(num_ele):
            coef = self.fegrid.basis(e)
            for n in range(3):
                bn = coef[:, n]
                grad = [bn[1], bn[2]]
                dx, dy = self.fegrid.gradient(e, n)
                assert_allclose(bn[1], dx)
                assert_allclose(bn[2], dy)

    def test_basis(self):
        V = np.array([[1, 0, 1],
                      [1, 0, 0],
                      [1, 1, 0]])
        C = np.linalg.inv(V)
        assert_array_equal(C, self.stdgrid.basis(0))

    def test_boundary_nonzero(self):
        ele14_nz = self.fegrid.boundary_nonzero(0, 14)
        eq_(ele14_nz, [0, 3])
        ele0_nz = self.stdgrid.boundary_nonzero(0, 0)
        eq_(ele0_nz, -1)
        ele7_nz = self.fegrid.boundary_nonzero(0, 7)
        eq_(ele7_nz, [0, 0])
        ele11_nz = self.fegrid.boundary_nonzero(4, 11)
        eq_(ele11_nz, [4, 4])

    def test_boundary_edges(self):
        ele14_nz = self.fegrid.boundary_edges([0, 3], 14)
        eq_(ele14_nz, (0.0, 1.0))
        ele7_nz = self.fegrid.boundary_edges([0, 0], 7)
        eq_(ele7_nz, (0.0, 0.0))

    def test_gauss_nodes1d(self):
        nodes05 = np.array([[(-(.5-0)/2*1/np.sqrt(3)+(.5+0)/2), 0], [((.5-0)/2*1/np.sqrt(3)+(.5+0)/2), 0]])
        nodes15 = np.array([[(-(1-.5)/2*1/np.sqrt(3)+(1+.5)/2), 0], [((1-.5)/2*1/np.sqrt(3)+(.5+1)/2), 0]])
        assert_array_equal(self.fegrid.gauss_nodes1d([0, 5], 9), nodes05)
        assert_array_equal(self.fegrid.gauss_nodes1d([1, 5], 6), nodes15)

    def test_gauss_nodes(self):
        C = self.stdgrid.gauss_nodes(0, ord=2)
        eq_(C[0, 0], 0, "node x1")
        eq_(C[0, 1], .5, "node y1")
        eq_(C[1, 0], .5, "node x2")
        eq_(C[1, 1], 0, "node y2")
        eq_(C[2, 0], .5, "node x3")
        eq_(C[2, 1], .5, "node y3")

    def test_area(self):
        eq_(self.stdgrid.element_area(0), .5, "element_area")
        eq_(self.stdgrid.element_area(1), .5, "element_area")

    def test_quad(self):
        fvals = np.array([1, 1, 1])
        fvals2 = np.array([2, 2, 2])
        eq_(self.stdgrid.gauss_quad(0, fvals, ord=2), .5)
        eq_(self.stdgrid.gauss_quad(1, fvals, ord=2), .5)
        eq_(self.stdgrid.gauss_quad(0, fvals2, ord=2), 1)

    def test_quad1d(self):
        fvals = [1, 1, 1]
        eq_(self.fegrid.gauss_quad1d(fvals, [1, 5], 6), .5)
        eq_(self.fegrid.gauss_quad1d(fvals, [0, 5], 9), .5)

    def test_centroid(self):
        eq_(self.stdgrid.centroid(0)[0], 1/3)
        eq_(self.stdgrid.centroid(0)[1], 1/3)

    def test_assign_normal(self):
        normal = self.fegrid.assign_normal(0, 3)
        assert_array_equal(normal, [-1, 0])
        normal = self.fegrid.assign_normal(0, 1)
        assert_array_equal(normal, [0, -1])
        normal = self.fegrid.assign_normal(4, 8)
        eq_(normal, -1)
