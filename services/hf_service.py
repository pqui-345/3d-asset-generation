"""
Hugging Face TripoSR Service - Free 3D generation via Gradio Space.
Uses stabilityai/TripoSR Space for image-to-3D reconstruction.
"""
import os
import time
import shutil

class HuggingFaceService:
    """Service to call Hugging Face TripoSR Space for image-to-3D."""
    
    def __init__(self):
        self.space_id = "stabilityai/TripoSR"
    
    def is_available(self):
        """Check if gradio_client is installed."""
        try:
            from gradio_client import Client
            return True
        except ImportError:
            return False
    
    def generate_3d(self, image_path, output_dir, asset_name):
        """
        Generate 3D model using TripoSR Space.
        Pipeline: preprocess (bg remove) → generate (3D mesh)
        Returns dict with model paths and metrics.
        """
        from gradio_client import Client
        
        start_time = time.time()
        
        print(f"[HF TripoSR] Connecting to {self.space_id}...")
        client = Client(self.space_id, verbose=False)
        
        # Step 1: Preprocess (remove background + foreground extraction)
        print("[HF TripoSR] Step 1/2: Preprocessing image (background removal)...")
        try:
            processed_image = client.predict(
                image_path,       # input image
                True,             # remove_background
                0.55,             # foreground_ratio
                api_name="/preprocess"
            )
            print(f"[HF TripoSR] Preprocessed: {processed_image}")
        except Exception as e:
            print(f"[HF TripoSR] Preprocess failed: {e}")
            raise
        
        # Step 2: Generate 3D mesh
        print("[HF TripoSR] Step 2/2: Generating 3D mesh (marching cubes)...")
        try:
            result = client.predict(
                processed_image,  # preprocessed image
                256,              # marching_cubes_resolution (32-320)
                api_name="/generate"
            )
            print(f"[HF TripoSR] Generation result: {result}")
        except Exception as e:
            print(f"[HF TripoSR] Generate failed: {e}")
            raise
        
        # Result is (obj_path, glb_path)
        obj_path = result[0] if isinstance(result, (tuple, list)) else None
        glb_path = result[1] if isinstance(result, (tuple, list)) and len(result) > 1 else None
        
        # Copy GLB to output directory
        glb_filename = f"{asset_name}.glb"
        obj_filename = f"{asset_name}.obj"
        final_glb = os.path.join(output_dir, glb_filename)
        final_obj = os.path.join(output_dir, obj_filename)
        
        if glb_path and os.path.exists(glb_path):
            shutil.copy2(glb_path, final_glb)
            print(f"[HF TripoSR] GLB saved: {final_glb}")
        else:
            raise Exception("No GLB output from TripoSR")
        
        if obj_path and os.path.exists(obj_path):
            shutil.copy2(obj_path, final_obj)
            print(f"[HF TripoSR] OBJ saved: {final_obj}")
        
        inference_time = round(time.time() - start_time, 3)
        file_size = os.path.getsize(final_glb)
        file_size_str = f"{file_size / (1024*1024):.2f} MB"
        
        return {
            "method": "huggingface_triposr",
            "name": asset_name,
            "glb_path": final_glb,
            "glb_url": f"/static/models/{glb_filename}",
            "obj_path": final_obj,
            "obj_url": f"/static/models/{obj_filename}",
            "ply_path": "",
            "vertices": 0,
            "faces": 0,
            "texture_size": "AI Generated",
            "file_size": file_size_str,
            "inference_time": inference_time
        }


# Singleton
hf_service = HuggingFaceService()
