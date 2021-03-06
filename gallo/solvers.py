import itertools as itr
import time

import numpy as np
import scipy.sparse as sps
import scipy.sparse.linalg as linalg
import scipy.linalg as dense_linalg
import matplotlib.tri as tri

from gallo.formulations.diffusion import Diffusion
from gallo.formulations.nda import NDA
from gallo.formulations.saaf import SAAF
from gallo.upscatter_acceleration import UA
from gallo.helpers import Helper

class Solver():
    def __init__(self, operator):
        self.op = operator
        self.ua_bool = False
        if isinstance(self.op, NDA):
            self.ho_op = SAAF(self.op.fegrid, self.op.mat_data)
        self.mat_data = self.op.mat_data
        self.num_groups = self.op.num_groups
        self.num_nodes = self.op.num_nodes
        self.num_elts = self.op.num_elts
        self.num_mats = self.mat_data.get_num_mats()
        self.num_angs = self.op.fegrid.num_angs
        self.angs = self.op.fegrid.angs
        self.weights = self.op.fegrid.weights
        self.helper = Helper(self.op.fegrid, self.mat_data)

    def get_ang_flux(self, group_id, source, ang, angle_id, phi_prev):
        lhs = self.op.make_lhs(ang, group_id).todense()
        rhs = self.op.make_rhs(group_id, source, ang, angle_id, phi_prev)
        ang_flux = dense_linalg.solve(lhs, rhs)[0]
        return ang_flux

    def get_scalar_flux(self, group_id, source, phi_prev, ho_sols=None):
        scalar_flux = 0
        if isinstance(self.op, Diffusion) or isinstance(self.op, NDA):
            lhs = self.op.make_lhs(group_id, ho_sols=ho_sols).todense()
            rhs = self.op.make_rhs(group_id, source, phi_prev)
            scalar_flux = dense_linalg.solve(lhs, rhs)
            return {"Phi": scalar_flux, "Psi": None}
        else:
            ang_fluxes = np.zeros((self.num_angs, self.num_nodes))
            # Iterate over all angle possibilities
            for i, ang in enumerate(self.angs):
                ang = np.array(ang)
                ang_fluxes[i] = self.get_ang_flux(group_id, source, ang, i, phi_prev)
                scalar_flux += self.weights[i] * ang_fluxes[i]
            return {"Phi": scalar_flux, "Psi": ang_fluxes}

    def solve_in_group(self, source, group_id, phi_prev, max_iter=1000,
                       tol=1e-8, verbose=True):
        num_mats = self.mat_data.get_num_mats()
        for mat in range(num_mats):
            scatmat = self.mat_data.get_sigs(mat)
            if np.count_nonzero(scatmat) == 0:
                scattering = False
            else:
                scattering = True
        if self.num_groups > 1 and verbose:
            print("Starting Group ", group_id)
        if isinstance(self.op, NDA):
            # Run preliminary solve on low-order system
            ho_sols = 0
            fluxes = self.get_scalar_flux(group_id, source, phi_prev, ho_sols=ho_sols)
            phi_prev[group_id] = fluxes['Phi']
        for i in range(1, max_iter):
            if scattering and verbose:
                print("Within-Group Iteration: ", i)
            if isinstance(self.op, NDA):
                ho_solver = Solver(self.ho_op)
                fluxes_ho = ho_solver.get_scalar_flux(group_id, source, phi_prev)
                ho_phis, ho_psis = fluxes_ho['Phi'], fluxes_ho['Psi']
                fluxes = self.get_scalar_flux(group_id, source, phi_prev, ho_sols=[ho_phis, ho_psis])
            else:
                fluxes = self.get_scalar_flux(group_id, source, phi_prev)
            phi = fluxes['Phi']
            if not scattering:
                break
            norm = np.linalg.norm(phi - phi_prev[group_id], float('inf'))/np.linalg.norm(phi, float('inf'))
            if verbose: print("Norm: ", norm)
            if norm < tol:
                break
            phi_prev[group_id] = np.copy(phi)
        if i == max_iter:
            print("Warning: maximum number of iterations reached in solver")
        if self.num_groups > 1 and verbose:
            print("Finished Group ", group_id)
        if scattering and verbose:
            print("Number of Within-Group Iterations: ", i + 1)
            print("Final Phi Norm: ", norm)
        if isinstance(self.op, NDA):
            return {"Phi": phi, "Psi": None, "HO": [ho_phis, ho_psis]}
        else:
            return {"Phi": phi, "Psi": fluxes['Psi'], "HO": None}

    def solve_outer(self, source, phis, verbose=True, max_iter=50, tol=1e-6):
        ang_fluxes = np.zeros((self.num_groups, self.num_angs, self.num_nodes))
        for it_count in range(1, max_iter):
            if self.num_groups != 1 and verbose:
                print("Gauss-Seidel Iteration: ", it_count)
            phis_prev = np.copy(phis)
            if isinstance(self.op, NDA):
                all_ho_sols = []
            for g in range(self.num_groups):
                if isinstance(self.op, NDA):
                    fluxes = self.solve_in_group(source, g, phis, verbose=verbose)
                    all_ho_sols.append(fluxes['HO'])
                else:
                    fluxes = self.solve_in_group(source, g, phis)
                    ang_fluxes[g] = fluxes['Psi']
                phis[g] = fluxes['Phi']
            if self.num_groups == 1:
                break
            else:
                if self.ua_bool:
                    # Calculate Correction Term
                    print("Calculating Upscatter Acceleration Term")
                    upscatter_accelerator = UA(self.op)
                    # Calculate eigenfunctions
                    eig_for_mat = np.zeros((self.num_mats, self.num_groups))
                    for midx in range(self.num_mats):
                        eig_for_mat[midx] = upscatter_accelerator.compute_eigenfunction(midx)
                    eigs = np.zeros((self.num_groups, self.num_nodes))
                    for g in range(self.num_groups):
                        for elt in range(self.num_elts):
                            e = self.op.fegrid.element(elt)
                            midx = e.mat_id
                            for n in range(3):
                                n_global = self.op.fegrid.node(elt, n)
                                nid = n_global.id
                                eigs[g, nid] += eig_for_mat[midx, g]*1/3
                    epsilon = upscatter_accelerator.calculate_correction(phis, phis_prev, all_ho_sols)
                    phis += epsilon*eigs
                res = np.linalg.norm(phis - phis_prev, float('inf'))/np.linalg.norm(phis, float('inf'))
                if verbose:
                    print("GS Norm: ", res)
            if res < tol:
                break
        return {"Phi": phis, "Psi": ang_fluxes}

    def power_iteration(self, source, tol=1e-4):
        k = 1
        phi = np.ones((self.num_groups, self.num_nodes))
        fiss_source = self.helper.make_full_fission_source(phi)
        int_fiss = self.helper.integrate_flux(fiss_source)
        err = 1
        it = 0
        while err > tol:
            it += 1
            print("Power Iteration ", it)
            fluxes = self.solve_outer(fiss_source, (1/k)*phi)
            phi_new = fluxes['Phi']
            fiss_source_new = self.helper.make_full_fission_source(phi_new)
            int_fiss_new = self.helper.integrate_flux(fiss_source_new)  # Integrate Fission Source
            k_new = k*(int_fiss_new/int_fiss)
            err_k = np.linalg.norm((k_new - k)/k_new)
            err_phi = np.linalg.norm((phi_new - phi)/phi_new)
            err = max(err_k, err_phi)
            print("PI Norm: ", err)
            int_fiss = np.copy(int_fiss_new)
            phi = np.copy(phi_new)
            k = np.copy(k_new)
        return {"Phi": phi, "Psi": fluxes['Psi'], "k": k}

    def solve(self, source, ua_bool=False, eigenvalue=False):
        start = time.time()
        phis = np.ones((self.num_groups, self.num_nodes))
        if ua_bool:
            self.ua_bool = True
        if eigenvalue:
            fluxes = self.power_iteration(source)
        else:
            fluxes = self.solve_outer(source, phis)
        end = time.time()
        print("Runtime:", np.round(end - start, 5), "seconds")
        return fluxes
