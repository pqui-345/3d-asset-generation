import numpy as np
import trimesh
import scipy.sparse as sp
from scipy.sparse.linalg import cg
import cv2
import math

class DeformationService:
    """
    Silhouette-driven Laplacian Mesh Deformation.
    Only deforms vertices near the silhouette boundary, keeping interior stable.
    """
    def __init__(self, device='cpu'):
        self.device = device

    def deform(self, template_mesh, silhouette_mask, camera_params=None, strength=1.0):
        """
        Main deformation pipeline.
        strength: 1.0 = normal deformation, <1.0 = gentler (for high-similarity matches)
        """
        V0 = template_mesh.vertices.copy().astype(np.float32)
        F = template_mesh.faces.astype(np.int32)
        N = V0.shape[0]
        
        # 1. Build Laplacian matrix L
        L = self._build_laplacian(V0, F)
        
        # 2. Extract target silhouette boundary from mask
        target_pts = self._extract_boundary(silhouette_mask)
        if len(target_pts) == 0:
            return template_mesh
            
        # 3. Estimate camera if not provided
        if camera_params is None:
            camera_params = self._estimate_camera(V0, target_pts)
            
        # 4. Find which vertices are near the boundary (only these get deformed)
        V_proj = self._project(V0, camera_params)
        bnd_indices, bnd_weights = self._find_boundary_vertices_weighted(
            V_proj, target_pts, sigma=0.15
        )
        
        if len(bnd_indices) == 0:
            return template_mesh
            
        print(f"[Deform] {len(bnd_indices)} boundary vertices out of {N} (strength={strength:.2f})")
        
        # 5. Iterative Optimization
        V = V0.copy()
        
        # Scale weights by strength - lower strength = less deformation
        w_sil = 50.0 * strength    # Silhouette constraint
        w_lap = 5.0                # Laplacian smoothness (keep constant)
        w_reg = 2.0 / max(strength, 0.1)  # Stronger regularization when strength is low
        max_iter = 20
        
        for iteration in range(max_iter):
            # Project current vertices to 2D
            V_proj = self._project(V, camera_params)
            
            # Silhouette energy: pull boundary vertices toward target contour
            grad_sil = np.zeros_like(V)
            for k, vi in enumerate(bnd_indices):
                proj_2d = V_proj[vi]
                dists = np.linalg.norm(target_pts - proj_2d, axis=1)
                closest = target_pts[dists.argmin()]
                w = bnd_weights[k]
                grad_sil[vi, 0] += w_sil * w * (proj_2d[0] - closest[0]) * camera_params['scale_x']
                grad_sil[vi, 1] += w_sil * w * (proj_2d[1] - closest[1]) * camera_params['scale_y']
            
            # Laplacian smoothness
            LV = L @ (V - V0)
            grad_lap = w_lap * (L.T @ LV)
            
            # Regularization: pull back toward original
            grad_reg = w_reg * (V - V0)
            
            # Only move boundary vertices significantly
            grad_total = grad_sil + grad_lap + grad_reg
            
            # Step size with damping
            step = 0.05 / (iteration + 1)
            dV = -grad_total * step
            
            # Clamp max displacement per iteration
            max_disp = np.abs(dV).max()
            if max_disp > 0.01 * strength:
                dV *= (0.01 * strength) / max_disp
            
            V += dV
            
            if np.linalg.norm(dV) < 1e-5:
                break
                
        # Create new mesh
        deformed = template_mesh.copy()
        deformed.vertices = V
        return deformed

    def _build_laplacian(self, V, F):
        """Compute Uniform Laplacian matrix with normalized weights."""
        N = V.shape[0]
        L = sp.lil_matrix((N, N))
        
        # Build adjacency
        neighbors = [set() for _ in range(N)]
        for f in F:
            for i in range(3):
                j = f[(i+1) % 3]
                k = f[(i+2) % 3]
                neighbors[f[i]].add(j)
                neighbors[f[i]].add(k)
        
        for i in range(N):
            nb = list(neighbors[i])
            if len(nb) == 0:
                continue
            weight = 1.0 / len(nb)
            L[i, i] = 1.0
            for j in nb:
                L[i, j] = -weight
                
        return L.tocsr()

    def _extract_boundary(self, mask):
        """Extract boundary points from binary mask using OpenCV contours."""
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return np.array([])
        
        longest = max(contours, key=lambda c: len(c))
        pts = longest.reshape(-1, 2).astype(np.float32)
        
        # Resample to 80 evenly-spaced points
        if len(pts) > 80:
            idx = np.linspace(0, len(pts)-1, 80).astype(int)
            pts = pts[idx]
        return pts

    def _project(self, V, camera):
        """Orthographic projection."""
        proj = np.zeros((V.shape[0], 2))
        proj[:, 0] = V[:, 0] * camera['scale_x'] + camera['tx']
        proj[:, 1] = V[:, 1] * camera['scale_y'] + camera['ty']
        return proj

    def _find_boundary_vertices_weighted(self, V_proj, target_pts, sigma=0.15):
        """
        Find vertices whose projection is near the target silhouette boundary.
        Returns (indices, weights) where weights fall off with distance.
        """
        # For each projected vertex, find distance to nearest boundary point
        dists = np.linalg.norm(V_proj[:, None, :] - target_pts[None, :, :], axis=2)
        min_dists = dists.min(axis=1)  # (N,)
        
        # Select vertices within a distance threshold
        threshold = sigma * max(target_pts.max(axis=0) - target_pts.min(axis=0)).max()
        mask = min_dists < threshold
        
        indices = np.where(mask)[0]
        weights = np.exp(-min_dists[indices] / (sigma + 1e-6))
        
        # Also add vertices that are extreme in the projection (corners of silhouette)
        if len(indices) > 0:
            proj_center = V_proj.mean(axis=0)
            proj_extent = V_proj.max(axis=0) - V_proj.min(axis=0)
            extreme_mask = np.zeros(len(V_proj), dtype=bool)
            for dim in range(2):
                lo = V_proj[:, dim] < V_proj[:, dim].min() + 0.1 * proj_extent[dim]
                hi = V_proj[:, dim] > V_proj[:, dim].max() - 0.1 * proj_extent[dim]
                extreme_mask |= lo | hi
            # Merge
            new_idx = np.where(extreme_mask & ~mask)[0]
            if len(new_idx) > 0:
                indices = np.concatenate([indices, new_idx])
                weights = np.concatenate([weights, np.ones(len(new_idx)) * 0.3])
        
        return indices, weights

    def _estimate_camera(self, V, target_pts):
        """Estimate orthographic camera from template bbox and target silhouette."""
        v_min, v_max = V.min(axis=0), V.max(axis=0)
        t_min, t_max = target_pts.min(axis=0), target_pts.max(axis=0)
        
        scale_x = (t_max[0] - t_min[0]) / max(v_max[0] - v_min[0], 1e-6)
        scale_y = (t_max[1] - t_min[1]) / max(v_max[1] - v_min[1], 1e-6)
        scale = min(scale_x, scale_y) * 0.85
        
        tx = (t_min[0] + t_max[0]) / 2 - scale * (v_min[0] + v_max[0]) / 2
        ty = (t_min[1] + t_max[1]) / 2 - scale * (v_min[1] + v_max[1]) / 2
        
        return {'scale_x': scale, 'scale_y': scale, 'tx': tx, 'ty': ty}
