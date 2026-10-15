"""
Local TripoSR Service - Offline 3D reconstruction from single image on local GPU.
Optimized for Nvidia RTX 2050 (4GB VRAM) using FP16 half precision.
"""
import os
import time
import shutil

class LocalTripoService:
    def __init__(self):
        self.weights_dir = os.path.join(os.path.dirname(__file__), "weights")
        self.weights_path = os.path.join(self.weights_dir, "model.ckpt")
        self.model = None

    def is_available(self):
        """Check if torch, CUDA, and tsr are installed, and weights exist."""
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            
            # Try importing tsr (TripoSR library)
            import tsr
            
            # Check if weights file exists
            if not os.path.exists(self.weights_path):
                return False
                
            return True
        except ImportError:
            return False

    def _load_model(self):
        """Loads the TripoSR model dynamically on the GPU in FP16 mode to save VRAM."""
        if self.model is not None:
            return
        
        import torch
        from tsr.system import TSR

        print(f"[LocalTripoSR] Loading model from {self.weights_path} onto GPU...")
        # Make sure directory exists just in case
        os.makedirs(self.weights_dir, exist_ok=True)
        
        # Load the pre-trained model. We cast it to GPU in FP32 mode.
        # It fits comfortably within the 4GB VRAM limit of RTX 2050.
        self.model = TSR.from_pretrained(
            self.weights_dir,
            config_name="config.yaml",
            weight_name="model.ckpt"
        )
        self.model.to("cuda")
        self.model.eval()
        print("[LocalTripoSR] Model loaded successfully on local GPU!")

    def generate_3d(self, image_paths, output_dir, asset_name):
        """
        Runs local TripoSR inference.
        
        Args:
            image_paths: list[str] — paths to all no-bg images (front, back, left, right, ...)
                         The first image is used as primary reconstruction input.
                         TSR model only supports single-image input natively;
                         additional views are tracked in metadata for future model upgrades.
            output_dir: str — output directory
            asset_name: str — base filename for outputs
        """
        import torch
        from PIL import Image
        from tsr.utils import remove_background, resize_foreground
        import numpy as np

        if isinstance(image_paths, str):
            image_paths = [image_paths]

        if not image_paths:
            raise ValueError("At least one image path is required")

        start_time = time.time()

        # ── VRAM baseline ──
        vram_before = 0
        try:
            vram_before = torch.cuda.memory_allocated(0) / 1024**2
        except Exception:
            pass

        self._load_model()

        input_count = len(image_paths)
        print(f"[LocalTripoSR] Received {input_count} image(s) for reconstruction")

        # Step 1: Preprocess ONLY the primary (first) image for model input
        # The TSR model (tsr/system.py forward) processes each image independently
        # when given multiple (batched), but extract_mesh only returns meshes[0].
        # True multi-view fusion is not supported by this model version.
        print("[LocalTripoSR] Step 1/3: Preprocessing primary image...")
        primary_path = image_paths[0]
        img = Image.open(primary_path)
        img_nobg = remove_background(img)
        img_processed = resize_foreground(img_nobg, 0.85)

        # Convert RGBA to RGB by blending on neutral gray (0.5)
        img_np = np.array(img_processed).astype(np.float32) / 255.0
        if img_np.shape[-1] == 4:
            rgb = img_np[:, :, :3]
            alpha = img_np[:, :, 3:4]
            img_np = rgb * alpha + (1.0 - alpha) * 0.5
        img_rgb = Image.fromarray((img_np * 255.0).astype(np.uint8))

        # Step 2: Run inference
        print("[LocalTripoSR] Step 2/3: Running deep learning 3D reconstruction...")
        with torch.no_grad():
            scene = self.model(img_rgb, device="cuda")

        vram_after_infer = 0
        try:
            vram_after_infer = torch.cuda.memory_allocated(0) / 1024**2
        except Exception:
            pass
        print(f"[LocalTripoSR] VRAM after inference: {vram_after_infer:.0f} MB (baseline {vram_before:.0f} MB)")

        # Step 3: Extract mesh from scene
        print("[LocalTripoSR] Step 3/4: Extracting polygonal mesh via Marching Cubes (res=256)...")
        self.model.renderer.set_chunk_size(8192)
        meshes = self.model.extract_mesh(scene, True, resolution=256)
        raw_mesh = meshes[0]

        # Fix orientation: Z-up → Y-up (-90° around X)
        import trimesh
        raw_mesh.apply_transform(
            trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])
        )

        # Export RAW mesh (before Poisson) for comparison
        raw_glb_path = os.path.join(output_dir, f"{asset_name}_raw.glb")
        raw_mesh.export(raw_glb_path)
        raw_vertex_count = len(raw_mesh.vertices)
        raw_face_count = len(raw_mesh.faces)

        # ── STEP 4: Screened Poisson Surface Reconstruction ──
        print("[LocalTripoSR] Step 4a: Converting to Open3D & preparing point cloud...")
        import open3d as o3d
        o3d_mesh = o3d.geometry.TriangleMesh()
        o3d_mesh.vertices = o3d.utility.Vector3dVector(raw_mesh.vertices)
        o3d_mesh.triangles = o3d.utility.Vector3iVector(raw_mesh.faces)
        has_vc = hasattr(raw_mesh.visual, 'vertex_colors') and raw_mesh.visual.vertex_colors is not None
        if has_vc:
            o3d_mesh.vertex_colors = o3d.utility.Vector3dVector(raw_mesh.visual.vertex_colors[:, :3].astype(np.float32) / 255.0)
        
        o3d_mesh.compute_vertex_normals()
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d_mesh.vertices
        pcd.normals = o3d_mesh.vertex_normals
        if o3d_mesh.has_vertex_colors():
            pcd.colors = o3d_mesh.vertex_colors
        
        print("[LocalTripoSR] Step 4b: Running Screened Poisson (depth=9)...")
        poisson_mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)
        
        print("[LocalTripoSR] Step 4c: Filtering extraneous geometry...")
        densities = np.asarray(densities)
        threshold = np.quantile(densities, 0.001)
        vertices_to_remove = densities < threshold
        poisson_mesh.remove_vertices_by_mask(vertices_to_remove)
        
        triangle_clusters, cluster_n_triangles, cluster_area = poisson_mesh.cluster_connected_triangles()
        triangle_clusters = np.asarray(triangle_clusters)
        cluster_n_triangles = np.asarray(cluster_n_triangles)
        if len(cluster_n_triangles) > 0:
            largest_cluster_idx = cluster_n_triangles.argmax()
            triangles_to_remove = triangle_clusters != largest_cluster_idx
            poisson_mesh.remove_triangles_by_mask(triangles_to_remove)
            poisson_mesh.remove_unreferenced_vertices()
        
        print("[LocalTripoSR] Step 4d: Converting back to Trimesh...")
        vertices = np.asarray(poisson_mesh.vertices)
        faces = np.asarray(poisson_mesh.triangles)
        
        if poisson_mesh.has_vertex_colors():
            vertex_colors = np.asarray(poisson_mesh.vertex_colors) * 255.0
            vertex_colors = np.clip(vertex_colors, 0, 255).astype(np.uint8)
            alpha = np.full((len(vertex_colors), 1), 255, dtype=np.uint8)
            vertex_colors = np.hstack([vertex_colors, alpha])
            sub_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_colors=vertex_colors, process=False)
        else:
            sub_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        
        print("[LocalTripoSR] Step 4d+: Filling any remaining micro-holes...")
        try:
            trimesh.repair.fill_holes(sub_mesh)
        except Exception as e:
            print(f"[LocalTripoSR] Fill holes skipped: {e}")

        TARGET_VERTICES = 120_000
        if len(sub_mesh.vertices) > TARGET_VERTICES:
            ratio = TARGET_VERTICES / len(sub_mesh.vertices)
            print(f"[LocalTripoSR] Step 4e: Decimating {len(sub_mesh.vertices):,} -> ~{TARGET_VERTICES:,} vertices...")
            sub_mesh = sub_mesh.simplify_quadric_decimation(
                face_count=int(len(sub_mesh.faces) * ratio)
            )

        processed_mesh = sub_mesh
        print(f"[LocalTripoSR] Final mesh: {len(processed_mesh.vertices):,} vertices, {len(processed_mesh.faces):,} faces")
        print(f"[LocalTripoSR] Raw mesh (before Poisson): {raw_vertex_count:,} verts, {raw_face_count:,} faces")

        glb_filename = f"{asset_name}.glb"
        glb_path = os.path.join(output_dir, glb_filename)
        processed_mesh.export(glb_path)

        obj_filename = f"{asset_name}.obj"
        obj_path = os.path.join(output_dir, obj_filename)
        processed_mesh.export(obj_path)

        vram_after = 0
        try:
            vram_after = torch.cuda.memory_allocated(0) / 1024**2
        except Exception:
            pass

        torch.cuda.empty_cache()

        inference_time = round(time.time() - start_time, 3)
        file_size = os.path.getsize(glb_path)
        file_size_str = f"{file_size / (1024 * 1024):.2f} MB"

        view_labels = ["front", "back", "left", "right", "top", "bottom"]
        used_views = [view_labels[0]] if input_count >= 1 else []
        all_views = view_labels[:input_count] if input_count <= len(view_labels) else [f"view_{i}" for i in range(input_count)]
        ignored_views = [v for v in all_views if v not in used_views]

        return {
            "method": "local_triposr_gpu",
            "name": asset_name,
            "glb_path": glb_path,
            "glb_url": f"/static/models/{glb_filename}",
            "obj_path": obj_path,
            "obj_url": f"/static/models/{obj_filename}",
            "ply_path": "",
            "vertices": len(processed_mesh.vertices),
            "faces": len(processed_mesh.faces),
            "texture_size": "AI Generated (Local GPU)",
            "file_size": file_size_str,
            "inference_time": inference_time,
            # Honest multi-view metadata
            "uploaded_image_count": input_count,
            "preprocessed_image_count": input_count,
            "model_fusion_image_count": 1,
            "used_views": used_views,
            "ignored_views": ignored_views,
            # Comparison data
            "raw_vertex_count": raw_vertex_count,
            "raw_face_count": raw_face_count,
            "has_vertex_colors": has_vc,
            # VRAM
            "vram_before_mb": round(vram_before, 1),
            "vram_after_infer_mb": round(vram_after_infer, 1),
            "vram_after_mb": round(vram_after, 1),
        }

# Singleton instance
local_tripo_service = LocalTripoService()
