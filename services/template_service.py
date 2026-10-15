import os
import time
import trimesh
import numpy as np
from PIL import Image
from .recognition_service import RecognitionService
from .retrieval_service import RetrievalService
from .template_database import TemplateDatabase
from .deformation_service import DeformationService
from .texture_transfer_service import TextureTransferService

class TemplateService:
    """
    Orchestrator for Template Retrieval + Adaptive Deformation pipeline.
    """
    # Override: force specific labels to retrieve a different template (for testing/customization)
    # Key = user-facing label, Value = target template name substring to search
    # Force a specific template UID regardless of recognition (for testing)
    # Set to None or empty string to disable
    FORCE_TEMPLATE_UID = ""

    CATEGORY_REDIRECTS = {
        "apple": "chair",
        "banana": "table",
        "orange": "chair",
    }

    def __init__(self, template_dir, index_path, metadata_db, device='cuda'):
        self.template_dir = template_dir
        self.index_path = index_path
        self.metadata_db = TemplateDatabase(metadata_db)
        self.recognition = RecognitionService(device=device)
        self.retrieval = RetrievalService(index_path, self.metadata_db)
        self.deformation = DeformationService(device=device)
        self.texture_transfer = TextureTransferService()
        
    def is_available(self):
        return os.path.exists(self.index_path) and os.path.exists(self.metadata_db.db_path)
        
    def _resolve_redirect(self, recog):
        """
        Check if recognized label should redirect to a different template.
        Matches against top-5 category names + keywords from user's image.
        """
        labels = [recog['category'].lower()] + [c.lower() for c, _ in recog.get('top5', [])]
        for src, dst in self.CATEGORY_REDIRECTS.items():
            if any(src in lbl or lbl in src for lbl in labels):
                print(f"[Template] REDIRECT: {labels[0]} -> {dst} (matched: {src})")
                all_templates = self.metadata_db.list_all()
                matches = [t for t in all_templates if dst.lower() in t.get('name', '').lower()]
                if matches:
                    candidate = matches[0]
                    emb = candidate.get('clip_embedding')
                    if emb is not None:
                        recog['embedding'] = emb
                        recog['redirect_to'] = candidate['name']
                        recog['redirect_uid'] = candidate['uid']
                        safe = candidate['name'].encode('ascii', errors='replace').decode()
                        print(f"[Template] Redirect to template: {safe} ({candidate['uid']})")
            break
        return recog
        
    def generate_3d(self, no_bg_image, no_bg_path, additional_views, models_dir, asset_slug):
        start = time.time()
        
        # 1. RECOGNITION
        recog = self.recognition.recognize(no_bg_image)
        print(f"[Template] Category: {recog['category']} ({recog['confidence']:.2f})")
        
        # 1b. CATEGORY REDIRECT
        recog = self._resolve_redirect(recog)
        
        # 1c. FORCE TEMPLATE OVERRIDE (for testing specific templates)
        if self.FORCE_TEMPLATE_UID:
            t = self.metadata_db.get_template(self.FORCE_TEMPLATE_UID)
            if t:
                emb = t.get('clip_embedding')
                if emb is not None:
                    recog['embedding'] = emb
                    recog['redirect_to'] = t['name']
                    recog['redirect_uid'] = t['uid']
                    safe = t['name'].encode('ascii', errors='replace').decode()
                    print(f"[Template] FORCE template: {safe} ({t['uid']})")
            else:
                print(f"[Template] WARNING: FORCE_TEMPLATE_UID '{self.FORCE_TEMPLATE_UID}' not found")

# 2. RETRIEVAL
        candidates = self.retrieval.search(
            recog['embedding'], 
            k=5
            # category_filter removed: DB uses 'educational', CLIP uses different labels
        )
        
        if not candidates:
            raise Exception("No matching template found in database")
            
        best = candidates[0]
        sim = best['similarity']
        safe_name = best['name'].encode('ascii', errors='replace').decode()
        print(f"[Template] Best match: {safe_name} (sim={sim:.3f})")
        
        # 3. THRESHOLD CHECK - soft: proceed with best match, never fail the demo
        if sim < 0.75:
            print(f"[Template] WARNING: low similarity ({sim:.3f}) - proceeding with best match")
        
        # 4. LOAD TEMPLATE (preserve visual/texture)
        # best['glb_path'] already contains the full relative path from build script
        template_path = best['glb_path']
        template_mesh = trimesh.load(template_path, force='mesh', process=False)
        
        # 5. DEFORMATION - reduce strength for high similarity
        mask = np.array(no_bg_image)[:, :, 3] > 128
        deform_strength = 1.0 if sim < 0.85 else 0.3  # light deform for confident match
        deformed_mesh = self.deformation.deform(template_mesh, mask, strength=deform_strength)
        
        # 6. TEXTURE STRATEGY based on similarity
        texture_path = os.path.join(models_dir, f"{asset_slug}_texture.png")
        
        if sim >= 0.85:
            # HIGH CONFIDENCE: Keep template's original texture (realistic PBR)
            # deformed_mesh.visual already has the template's TextureVisuals (UV + material + texture)
            print(f"[Template] High sim ({sim:.3f}) >= 0.85: KEEPING template texture")
            # No texture_transfer call - template texture preserved in deformed_mesh.visual
            texture = self._extract_template_texture(deformed_mesh, texture_path)
            
        elif sim >= 0.75:
            # MEDIUM CONFIDENCE: Hybrid - template base + photo overlay on visible region
            print(f"[Template] Medium sim ({sim:.3f}): HYBRID texture transfer")
            texture = self.texture_transfer.transfer_hybrid(
                deformed_mesh, no_bg_image, mask, template_mesh.visual
            )
            Image.fromarray(texture).save(texture_path)
            
        else:
            # Should not reach here due to threshold check above
            texture = self.texture_transfer.transfer(deformed_mesh, no_bg_image, mask)
            Image.fromarray(texture).save(texture_path)
        
        # 7. EXPORT (deformed_mesh.visual preserves template texture for high-sim case)
        glb_path = os.path.join(models_dir, f"{asset_slug}.glb")
        obj_path = os.path.join(models_dir, f"{asset_slug}.obj")
        mtl_path = os.path.join(models_dir, f"{asset_slug}.mtl")
        
        deformed_mesh.export(glb_path)
        deformed_mesh.export(obj_path)
        
        # Calculate metrics
        file_size = os.path.getsize(glb_path) if os.path.exists(glb_path) else 0
        
        return {
            'method': 'template_retrieval',
            'name': best['name'],
            'glb_path': glb_path,
            'obj_path': obj_path,
            'mtl_path': mtl_path,
            'texture_path': texture_path,
            'vertices': len(deformed_mesh.vertices),
            'faces': len(deformed_mesh.faces),
            'texture_size': f"{texture.shape[1]}x{texture.shape[0]}",
            'file_size': f"{file_size / (1024*1024):.2f} MB",
            'inference_time': round(time.time() - start, 3),
            'template_uid': best['uid'],
            'similarity': best['similarity'],
            'category': recog['category']
        }
    
    def _extract_template_texture(self, mesh, save_path):
        """Extract and save template's baseColorTexture as PNG for reference."""
        try:
            visual = mesh.visual
            if hasattr(visual, 'material') and visual.material is not None:
                mat = visual.material
                if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture is not None:
                    # PIL Image from trimesh texture
                    tex_img = mat.baseColorTexture
                    if hasattr(tex_img, 'save'):
                        tex_img.save(save_path)
                        return np.array(tex_img.convert('RGB'))
        except Exception as e:
            print(f"[Template] Could not extract template texture: {e}")
        
        # Fallback: create a simple placeholder
        placeholder = np.full((1024, 1024, 3), 200, dtype=np.uint8)
        Image.fromarray(placeholder).save(save_path)
        return placeholder
