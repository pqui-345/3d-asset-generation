"""
Tripo AI API Service - Cloud-based 3D model generation from single image.
Uses Tripo AI's free tier API for realistic 3D reconstruction.
Docs: https://platform.tripo3d.ai/docs/api-reference
"""
import os
import time
import requests
import json

TRIPO_API_BASE = "https://api.tripo3d.ai/v2/openapi"
TRIPO_API_KEY = os.environ.get("TRIPO_API_KEY", "")

class TripoService:
    """Service to interact with Tripo AI API for image-to-3D generation."""
    
    def __init__(self):
        self.api_key = TRIPO_API_KEY
        self.base_url = TRIPO_API_BASE
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def is_available(self):
        """Check if API key is configured."""
        return bool(self.api_key and self.api_key.strip())
    
    def _upload_image(self, image_path):
        """Upload image to Tripo and get file_id."""
        url = f"{self.base_url}/upload"
        
        with open(image_path, "rb") as f:
            files = {
                "file": (os.path.basename(image_path), f, "image/png")
            }
            response = requests.post(url, headers=self.headers, files=files, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")
        
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Upload error: {data.get('message', 'Unknown error')}")
        
        return data["data"]["image_token"]
    
    def _create_task(self, image_token):
        """Create an image-to-model task."""
        url = f"{self.base_url}/task"
        
        payload = {
            "type": "image_to_model",
            "file": {
                "type": "png",
                "file_token": image_token
            }
        }
        
        response = requests.post(url, headers=self.headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Task creation failed: {response.status_code} - {response.text}")
        
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Task error: {data.get('message', 'Unknown error')}")
        
        return data["data"]["task_id"]
    
    def _poll_task(self, task_id, max_wait=180):
        """Poll task status until completion."""
        url = f"{self.base_url}/task/{task_id}"
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            data = response.json()
            if data.get("code") != 0:
                time.sleep(2)
                continue
            
            task_data = data.get("data", {})
            status = task_data.get("status", "")
            
            if status == "success":
                # Get the model output URL
                output = task_data.get("output", {})
                model_url = output.get("model", "")
                rendered_images = output.get("rendered_images", [])
                return {
                    "model_url": model_url,
                    "rendered_images": rendered_images
                }
            elif status == "failed":
                raise Exception(f"Task failed: {task_data.get('error', 'Unknown error')}")
            
            # Still processing, wait and retry
            time.sleep(3)
        
        raise Exception(f"Task timed out after {max_wait} seconds")
    
    def _download_model(self, model_url, output_path):
        """Download the generated GLB model."""
        response = requests.get(model_url, timeout=120)
        
        if response.status_code != 200:
            raise Exception(f"Download failed: {response.status_code}")
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return output_path
    
    def generate_3d(self, image_path, output_dir, asset_name):
        """
        Full pipeline: Upload → Create Task → Poll → Download.
        Returns dict with model paths and metrics.
        """
        start_time = time.time()
        
        if not self.is_available():
            raise Exception("Tripo API key not configured. Set TRIPO_API_KEY environment variable.")
        
        print(f"[Tripo AI] Starting 3D generation for: {image_path}")
        
        # Step 1: Upload image
        print("[Tripo AI] Step 1/4: Uploading image...")
        image_token = self._upload_image(image_path)
        print(f"[Tripo AI] Upload complete. Token: {image_token}")
        
        # Step 2: Create task
        print("[Tripo AI] Step 2/4: Creating 3D generation task...")
        task_id = self._create_task(image_token)
        print(f"[Tripo AI] Task created: {task_id}")
        
        # Step 3: Poll for completion
        print("[Tripo AI] Step 3/4: Generating 3D model (this may take 30-120 seconds)...")
        result = self._poll_task(task_id)
        print(f"[Tripo AI] Generation complete!")
        
        # Step 4: Download model
        glb_filename = f"{asset_name}.glb"
        glb_path = os.path.join(output_dir, glb_filename)
        
        print(f"[Tripo AI] Step 4/4: Downloading GLB model...")
        self._download_model(result["model_url"], glb_path)
        print(f"[Tripo AI] Download complete: {glb_path}")
        
        inference_time = round(time.time() - start_time, 3)
        file_size = os.path.getsize(glb_path)
        file_size_str = f"{file_size / (1024 * 1024):.2f} MB"
        
        return {
            "method": "tripo_ai",
            "name": asset_name,
            "glb_path": glb_path,
            "glb_url": f"/static/models/{glb_filename}",
            "vertices": 0,
            "faces": 0,
            "texture_size": "AI Generated",
            "file_size": file_size_str,
            "inference_time": inference_time,
            "rendered_images": result.get("rendered_images", [])
        }

    def _create_multiview_task(self, image_tokens):
        """Create a multiview-to-model task."""
        url = f"{self.base_url}/task"

        files_param = []
        for i, token in enumerate(image_tokens):
            files_param.append({
                "type": "png",
                "file_token": token
            })

        payload = {
            "type": "multiview_to_model",
            "files": files_param
        }

        response = requests.post(url, headers=self.headers, json=payload, timeout=60)

        if response.status_code != 200:
            raise Exception(f"Multiview task creation failed: {response.status_code} - {response.text}")

        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Multiview task error: {data.get('message', 'Unknown error')}")

        return data["data"]["task_id"]

    def generate_3d_multiview(self, primary_image, additional_images, output_dir, asset_name):
        """
        Multi-view 3D generation pipeline:
        Upload all images → Create multiview task → Poll → Download.
        """
        start_time = time.time()

        if not self.is_available():
            raise Exception("Tripo API key not configured.")

        print(f"[Tripo AI] Starting MULTI-VIEW 3D generation ({1 + len(additional_images)} images)...")

        # Step 1: Upload all images
        print("[Tripo AI] Step 1/4: Uploading images...")
        tokens = []
        tokens.append(self._upload_image(primary_image))
        for img_path in additional_images:
            tokens.append(self._upload_image(img_path))
        print(f"[Tripo AI] Uploaded {len(tokens)} images.")

        # Step 2: Create multiview task
        print("[Tripo AI] Step 2/4: Creating multiview 3D task...")
        task_id = self._create_multiview_task(tokens)
        print(f"[Tripo AI] Task created: {task_id}")

        # Step 3: Poll
        print("[Tripo AI] Step 3/4: Generating 3D model (multiview, may take longer)...")
        result = self._poll_task(task_id, max_wait=300)

        # Step 4: Download
        glb_filename = f"{asset_name}.glb"
        glb_path = os.path.join(output_dir, glb_filename)

        print("[Tripo AI] Step 4/4: Downloading GLB model...")
        self._download_model(result["model_url"], glb_path)

        inference_time = round(time.time() - start_time, 3)
        file_size = os.path.getsize(glb_path)

        return {
            "method": "tripo_ai_multiview",
            "name": asset_name,
            "glb_path": glb_path,
            "glb_url": f"/static/models/{glb_filename}",
            "vertices": 0,
            "faces": 0,
            "texture_size": "AI Multiview Generated",
            "file_size": f"{file_size / (1024 * 1024):.2f} MB",
            "inference_time": inference_time,
            "rendered_images": result.get("rendered_images", [])
        }


# Singleton
tripo_service = TripoService()
