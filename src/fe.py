import os

import numpy as np
import matplotlib.tri as tri

class Element():
    def __init__(self, el_id, vertices, mat_id):
        """ Constructor for a triangular element in 2D """
        self.el_id = el_id
        self.vertices = vertices
        self.mat_id = mat_id

    def __getitem__(self, index):
        return self.vertices[index]

    def get_el_id(self):
        return self.el_id

    def get_vertices(self):
        return self.vertices

    def get_mat_id(self):
        return self.mat_id


class Node():
    def __init__(self, position, node_id, interior_node_id, isinterior):
        self.position = position
        self.id = node_id
        self.isinterior = isinterior
        self.interior_node_id = interior_node_id

    def get_position(self):
        return self.position

    def get_node_id(self):
        return self.id

    def get_interior_node_id(self):
        return self.interior_node_id

    def is_interior(self):
        return self.isinterior


class FEGrid():
    def __init__(self, node_file, ele_file):
        # verify files exists
        assert os.path.exists(node_file), "Node file: " + node_file\
            + " does not exist"
        assert os.path.exists(ele_file), "Ele file: " + ele_file\
            + " does not exist"

        # Discretization Orders
        self.num_gauss_nodes = 4
        with open(node_file) as nf:
            line = nf.readline()
            data = line.split(" ")
            self.num_nodes = int(data[0])
            self.nodes = []
            self.interior_nodes = []
            self.num_interior_nodes = 0
            for i in range(self.num_nodes):
                line = nf.readline()
                #remove extra whitespace
                line = ' '.join(line.split())
                data = line.split(" ")
                node_id, x, y, boundary = data
                x = float(x)
                y = float(y)
                # Set boundary data
                if i == 0:
                    self.xmin = x
                    self.ymin = y
                    self.xmax = x
                    self.ymax = y
                else:
                    if x < self.xmin:
                        self.xmin = x
                    if y < self.ymin:
                        self.ymin = y
                    if x > self.xmax:
                        self.xmax = x
                    if y > self.ymax:
                        self.ymax = y
                is_interior = not int(boundary)
                interior_node_id = -1
                if is_interior:
                    interior_node_id = self.num_interior_nodes
                    self.num_interior_nodes += 1
                    self.interior_nodes.append(
                        Node([x, y], int(node_id), interior_node_id,
                             is_interior))
                self.nodes.append(
                    Node([x, y], int(node_id), interior_node_id, is_interior))

        with open(ele_file) as ef:
            line = ef.readline()
            data = line.split(" ")
            self.num_ele = int(data[0])
            self.elts_list = []
            for i in range(self.num_ele):
                line = ef.readline()
                #remove extra whitespace
                line = ' '.join(line.split())
                data = line.split(" ")
                el_id, *vertices, mat_id = data
                vertices = [int(vert) for vert in vertices]
                self.elts_list.append(Element(int(el_id), vertices, int(mat_id)))
            self.num_elts = np.size(self.elts_list)

    def get_boundary(self, which_boundary):
        if which_boundary == "xmin":
            return self.xmin
        elif which_boundary == "ymin":
            return self.ymin
        elif which_boundary == "xmax":
            return self.xmax
        elif which_boundary == "ymax":
            return self.ymax
        else:
            raise RuntimeError("Boundary must be xmin, ymin, xmax, or ymax")

    def is_corner(self, node_number):
        x, y = self.node(node_number).get_position()
        on_xboundary = (x == self.xmax or x == self.xmin)
        on_yboundary = (y == self.ymax or y == self.ymin)
        if on_xboundary and on_yboundary:
            return True
        else:
            return False

    def get_node(self, elt_number, local_node_number):
        return self.nodes[self.elts_list[elt_number][local_node_number]]

    def get_num_elts(self):
        return self.num_elts

    def get_num_nodes(self):
        return np.size(self.nodes)

    def get_num_interior_nodes(self):
        return self.num_interior_nodes

    def element(self, elt_number):
        return self.elts_list[elt_number]

    def node(self, node_number):
        return self.nodes[node_number]

    def get_mat_id(self, elt_number):
        return self.element(elt_number).get_mat_id()

    def evaluate_basis_function(self, coefficients, point):
        # Evaluates linear basis functions of the form c1 + c2x + c3y at the point x, y
        if len(coefficients) != 3:
            raise RuntimeError(
                "Must be linear basis function with 3 coefficients")
        if len(point) != 2:
            raise RuntimeError("Must be 2D point, (x,y)")
        return coefficients[0] + coefficients[1] * point[0] + coefficients[2] * point[1]

    def gradient(self, elt_number, local_node_number):
        # WARNING: The following only works for 2D triangular elements
        element = self.elts_list[elt_number].get_vertices()
        xbase = self.get_node(elt_number, local_node_number).get_position()
        dx = np.zeros((2, 2))
        for ivert in range(2):
            other_node_number = element[(local_node_number + ivert + 1) % 3]
            dx[ivert] = self.nodes[other_node_number].get_position()
            dx[ivert] -= xbase
        det = dx[0, 0] * dx[1, 1] - dx[1, 0] * dx[0, 1]
        retval = np.zeros(2)
        retval[0] = (-(dx[1, 1] - dx[0, 1]) / det)
        retval[1] = ((dx[1, 0] - dx[0, 0]) / det)
        return retval

    def basis(self, elt_number):
        vandermonde = np.zeros((3, 3))
        for i in range(3):
            vandermonde[i, 0] = 1
            vandermonde[i, 1] = self.get_node(elt_number, i).get_position()[0]
            vandermonde[i, 2] = self.get_node(elt_number, i).get_position()[1]
        coefficients = np.linalg.inv(vandermonde)
        return coefficients

    def boundary_nonzero(self, current_vert, e):
        # returns the points on the boundary where the basis function is non zero
        all_verts = np.array(self.element(e).get_vertices())
        vert_local_idx = np.where(all_verts == current_vert)[0][0]
        other_verts = np.delete(all_verts, vert_local_idx)

        # Get position of vertices
        posa = self.node(current_vert).get_position()
        posb = self.node(other_verts[0]).get_position()
        posc = self.node(other_verts[1]).get_position()

        ab_boundary = (((posa[0] == posb[0]) and
                        (posb[0] == self.xmin or posb[0] == self.xmax))
                       or ((posa[1] == posb[1]) and
                           (posb[1] == self.ymin or posb[1] == self.ymax)))
        ac_boundary = (((posa[0] == posc[0]) and
                        (posc[0] == self.xmin or posc[0] == self.xmax))
                       or ((posa[1] == posc[1]) and
                           (posc[1] == self.ymin or posc[1] == self.ymax)))

        if ab_boundary and ac_boundary:
            return -1
        elif ab_boundary:
            verts = [current_vert, other_verts[0]]
        elif ac_boundary:
            verts = [current_vert, other_verts[1]]
        else:
            verts = [current_vert, current_vert]
        return verts

    def boundary_edges(self, boundary_vertices, e):
        # Computes the length along boundary where the basis functions are non-zero
        if boundary_vertices[0] == boundary_vertices[1]:
            verts = self.boundary_nonzero(boundary_vertices[0], e)
        else:
            verts = boundary_vertices
        points = np.zeros((2, 2))
        for i, n in enumerate(verts):
            node = self.node(n)
            points[i] = node.get_position()
        a = None
        b = None
        if points[0, 0] == points[1, 0]:
            if points[0, 1] > points[1, 1]:
                a = points[1, 1]
                b = points[0, 1]
            elif points[0, 1] < points[1, 1] or points[0, 1] == points[1, 1]:
                a = points[0, 1]
                b = points[1, 1]
        elif points[0, 1] == points[1, 1]:
            if points[0, 0] > points[1, 0]:
                a = points[1, 0]
                b = points[0, 0]
            elif points[0, 0] < points[1, 0]:
                a = points[0, 0]
                b = points[1, 0]
        if a is None and b is None:
            raise RuntimeError("Boundary Edge Error")
        else:
            return a, b

    def gauss_nodes1d(self, boundary_vertices, e):
        # Gauss nodes for 2 point quadrature on boundary
        # multiplying by the same basis function
        # Find position of boundary vertices
        a, b = self.boundary_edges(boundary_vertices, e)
        xi = 1 / np.sqrt(3)
        nodes = np.array(
            [-(b - a) / 2 * xi + (b + a) / 2, (b - a) / 2 * xi + (b + a) / 2])
        pos_n = self.node(boundary_vertices[0]).get_position()
        pos_ns = self.node(boundary_vertices[1]).get_position()
        gauss_nodes = np.zeros((2, 2))
        if (pos_n[0] == self.xmax and pos_ns[0] == self.xmax):
            gauss_nodes[0] = [self.xmax, nodes[0]]
            gauss_nodes[1] = [self.xmax, nodes[1]]
        elif (pos_n[0] == self.xmin and pos_ns[0] == self.xmin):
            gauss_nodes[0] = [self.xmin, nodes[0]]
            gauss_nodes[1] = [self.xmin, nodes[1]]
        elif (pos_n[1] == self.ymax and pos_ns[1] == self.ymax):
            gauss_nodes[0] = [nodes[0], self.ymax]
            gauss_nodes[1] = [nodes[1], self.ymax]
        elif (pos_n[1] == self.ymin and pos_ns[1] == self.ymin):
            gauss_nodes[0] = [nodes[0], self.ymin]
            gauss_nodes[1] = [nodes[1], self.ymin]
        return gauss_nodes

    def gauss_nodes(self, elt_number):
        # WARNING only works for 2D triangular elements
        # Using third order Gaussian Quadrature nodes (1/3, 1/3), (1/5, 1/5), (1/5, 3/5), (3/5, 1/5)
        # http://math2.uncc.edu/~shaodeng/TEACHING/math5172/Lectures/Lect_15.PDF
        # Transform the nodes on the standard triangle to the given element

        # Set Number of Gauss Nodes
        num_gnodes = 4
        # Set Standard Nodes
        std_nodes = np.array([[1/3, 1/3], [1/5, 1/5], [1/5, 3/5], [3/5, 1/5]])
        # Get nodes of element
        el_nodes = np.array([self.get_node(elt_number, i) for i in [1, 2, 0]])
        pos = np.array([el_nodes[i].get_position() for i in range(3)])
        area = self.element_area(elt_number)
        # Transformation Function
        # x(u, v) = alpha + u(beta - alpha) + v(gamma - alpha)
        trans_nodes = np.zeros((num_gnodes, 2))
        for i in range(num_gnodes):
            stdnode = std_nodes[i]
            N = np.array([[1 - stdnode[0] - stdnode[1]], [stdnode[0]], [stdnode[1]]])
            for j in range(2):
                trans_nodes[i, j] = np.sum(np.array([pos[k, j]*N[k] for k in range(3)]))
        return trans_nodes

    def element_area(self, elt_number):
        e = self.elts_list[elt_number]
        n = self.nodes[e[0]]
        xbase = n.get_position()
        dx = np.zeros((2, 2))
        for ivert in [1, 2]:
            other_node_number = e[ivert]
            dx[ivert - 1, :] = self.nodes[other_node_number].get_position()
            for idir in range(2):
                dx[ivert - 1, idir] -= xbase[idir]
        # WARNING: the following calculation is correct for triangles in 2D *only*.
        area = np.abs(dx[0, 0] * dx[1, 1] - dx[1, 0] * dx[0, 1]) / 2
        return area

    def gauss_quad(self, elt_number, f_values):
        # Using thirdorder Gaussian Quadrature formula
        # 2*Area*(-27/96*f(1/3, 1/3)+25/96*(f(1/5, 1/5) + f(1/5, 3/5) + f(3/5, 1/5)))
        area = self.element_area(elt_number)
        integral = area*(-27/48*f_values[0]+25/48*np.sum(f_values[1:]))
        return integral

    def gauss_quad1d(self, f_values, boundary_vertices, e):
        # Two point Gaussian Quadrature in one dimension
        # Find length of element on boundary
        # length/2(f(-1/sqrt(3)) + f(1/sqrt(3)))
        a, b = self.boundary_edges(boundary_vertices, e)
        integral = (b - a) / 2 * (f_values[0] + f_values[1])
        return integral

    def centroid(self, elt_number):
        e = self.elts_list[elt_number]
        retval = np.zeros(2)
        for i in range(2):
            retval[i] = 0.0
        for ivert in range(3):
            n = self.nodes[e[ivert]]
            x = n.get_position()
            for idir in range(2):
                retval[idir] += x[idir]
        for idir in range(2):
            retval[idir] /= 3
        return retval

    def assign_normal(self, nid, bid):
        pos_n = self.node(nid).get_position()
        pos_ns = self.node(bid).get_position()
        if (pos_n[0] == self.xmax and pos_ns[0] == self.xmax):
            normal = np.array([1, 0])
        elif (pos_n[0] == self.xmin and pos_ns[0] == self.xmin):
            normal = np.array([-1, 0])
        elif (pos_n[1] == self.ymax and pos_ns[1] == self.ymax):
            normal = np.array([0, 1])
        elif (pos_n[1] == self.ymin and pos_ns[1] == self.ymin):
            normal = np.array([0, -1])
        else:
            return -1
        return normal

    def boundary_basis_product(self, nid, bid, gauss_nodes, bn, bns, e):
        pos_n = self.node(nid).get_position()
        pos_ns = self.node(bid).get_position()
        if not ((pos_n[0] == self.xmax and pos_ns[0] == self.xmax)
                or (pos_n[0] == self.xmin and pos_ns[0] == self.xmin)
                or (pos_n[1] == self.ymax and pos_ns[1] == self.ymax)
                or (pos_n[1] == self.ymin and pos_ns[1] == self.ymin)):
            boundary_integral = 0
            return boundary_integral
        # Value of first basis function at boundary gauss nodes
        gn_vals = np.zeros(2)
        gn_vals[0] = self.evaluate_basis_function(bn, gauss_nodes[0])
        gn_vals[1] = self.evaluate_basis_function(bn, gauss_nodes[1])
        # Values of second basis function at boundary gauss nodes
        gns_vals = np.zeros(2)
        gns_vals[0] = self.evaluate_basis_function(bns, gauss_nodes[0])
        gns_vals[1] = self.evaluate_basis_function(bns, gauss_nodes[1])
        # Multiply basis functions together
        g_vals = gn_vals * gns_vals
        return g_vals

    def setup_triangulation(self):
        x = np.zeros(self.num_nodes)
        y = np.zeros(self.num_nodes)
        positions = (self.node(i).get_position() for i in range(self.num_nodes))
        for i, pos in enumerate(positions):
            x[i], y[i] = pos
        # Setup triangles
        triangles = np.array([self.element(i).get_vertices() for i in range(self.num_elts)])
        triang = tri.Triangulation(x, y, triangles=triangles)
        return triang

    def phi_at_gauss_nodes(self, triang, phi_prev, g_nodes):
        num_groups = np.shape(phi_prev)[0]
        num_nodes = np.shape(g_nodes)[0]
        phi_vals = np.zeros((num_groups, num_nodes))
        for g in range(num_groups):
            interp = tri.LinearTriInterpolator(triang, phi_prev[g])
            for i in range(num_nodes):
                phi_vals[g, i] = interp(g_nodes[i, 0], g_nodes[i, 1])
        return phi_vals
