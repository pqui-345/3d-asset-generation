import numpy as np
import cv2
from PIL import Image

class TextureTransferService:
    """
    Projects input image texture onto deformed template mesh.
    """
    def transfer(self, template_mesh, input_image, input_mask):
        """
        template_mesh: trimesh.Trimesh with UVs
        input_image: PIL Image (RGBA)
        input_mask: binary mask (H, W)
        
        Returns: final_texture (H, W, 3) as numpy array
        """
        res = 1024
        
        # Convert input to numpy
        img_rgb = np.array(input_image.convert('RGB'))
        img_mask = np.array(input_mask)
        h, w = img_rgb.shape[:2]
        
        # 1. Fill transparent background with edge-sampled colors
        # Find the contour of the mask, sample colors from just outside the contour
        filled_img = self._fill_transparent_background(img_rgb, img_mask)
        
        # 2. Place filled image into 1024x1024 texture
        scale = min(res / h, res / w)
        nh, nw = int(h * scale), int(w * scale)
        
        resized_img = cv2.resize(filled_img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        resized_mask = cv2.resize(img_mask.astype(np.uint8), (nw, nh), interpolation=cv2.INTER_NEAREST)
        
        off_x = (res - nw) // 2
        off_y = (res - nh) // 2
        
        # 3. Create a soft-blended texture (no hard edges)
        mask_soft = cv2.GaussianBlur(resized_mask.astype(np.float32) / 255.0, (31, 31), 0)
        mask_soft = np.clip(mask_soft, 0, 1)
        
        # Use the filled image color everywhere, blend with edge colors at boundary
        final_texture = np.zeros((res, res, 3), dtype=np.uint8)
        final_texture[:] = resized_img.mean(axis=(0,1)).astype(np.uint8)  # base fill with avg color
        
        final_texture[off_y:off_y+nh, off_x:off_x+nw] = (
            resized_img * mask_soft[:, :, None] + 
            final_texture[off_y:off_y+nh, off_x:off_x+nw] * (1 - mask_soft[:, :, None])
        ).astype(np.uint8)
        
        # 4. Inpaint any remaining black/zero pixels with nearest color
        black_mask = (final_texture.sum(axis=2) < 10).astype(np.uint8) * 255
        if black_mask.any():
            final_texture = cv2.inpaint(final_texture, black_mask, inpaintRadius=20, flags=cv2.INPAINT_TELEA)
        
        return final_texture

    def transfer_hybrid(self, deformed_mesh, input_image, input_mask, template_visual):
        """
        Hybrid texture: template texture as base + photo overlay on visible region.
        
        template_visual: original template mesh's visual (TextureVisuals with UV, material, texture)
        """
        res = 1024
        
        # 1. Extract template's baseColorTexture if available
        base_tex = self._extract_template_texture(template_visual, (res, res))
        
        if base_tex is None:
            # Fallback: no template texture, use original transfer
            return self.transfer(deformed_mesh, input_image, input_mask)
        
        # 2. Prepare input photo
        img_rgb = np.array(input_image.convert('RGB'))
        img_mask = np.array(input_mask)
        h, w = img_rgb.shape[:2]
        
        filled_img = self._fill_transparent_background(img_rgb, img_mask)
        
        scale = min(res / h, res / w)
        nh, nw = int(h * scale), int(w * scale)
        
        resized_img = cv2.resize(filled_img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        resized_mask = cv2.resize(img_mask.astype(np.uint8), (nw, nh), interpolation=cv2.INTER_NEAREST)
        
        off_x = (res - nw) // 2
        off_y = (res - nh) // 2
        
        # 3. Soft mask for blending
        mask_soft = cv2.GaussianBlur(resized_mask.astype(np.float32) / 255.0, (31, 31), 0)
        mask_soft = np.clip(mask_soft, 0, 1)
        
        # 4. Blend: template texture everywhere, photo only on masked region
        # Photo gets 70% weight on masked area for color accuracy, template fills sides/back
        blend_weight = 0.7
        
        final_texture = base_tex.copy()
        
        roi = final_texture[off_y:off_y+nh, off_x:off_x+nw]
        roi[:] = (
            roi * (1 - mask_soft[:, :, None] * blend_weight) + 
            resized_img * (mask_soft[:, :, None] * blend_weight)
        ).astype(np.uint8)
        
        # 5. Inpaint any issues
        black_mask = (final_texture.sum(axis=2) < 10).astype(np.uint8) * 255
        if black_mask.any():
            final_texture = cv2.inpaint(final_texture, black_mask, inpaintRadius=20, flags=cv2.INPAINT_TELEA)
        
        return final_texture

    def _extract_template_texture(self, visual, target_size):
        """
        Extract baseColorTexture from template's visual as numpy array.
        Returns (H, W, 3) or None if not available.
        """
        try:
            if visual is None:
                return None
            # Handle different visual types
            if hasattr(visual, 'material') and visual.material is not None:
                mat = visual.material
                if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture is not None:
                    tex = mat.baseColorTexture
                    if hasattr(tex, 'convert'):
                        tex = tex.convert('RGB')
                        tex = tex.resize(target_size, Image.LANCZOS)
                        return np.array(tex)
        except Exception as e:
            print(f"[TextureTransfer] Could not extract template texture: {e}")
        return None

    def _fill_transparent_background(self, img_rgb, img_mask):
        """
        Fill transparent/background areas with colors extrapolated from object edges.
        Uses iterative dilate-and-sample to propagate colors outward.
        """
        h, w = img_rgb.shape[:2]
        result = img_rgb.copy()
        binary = (img_mask > 128).astype(np.uint8)
        
        # Iteratively fill from edges using distance transform + color propagation
        for iteration in range(50):
            # Dilate the mask by 1 pixel
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(binary, kernel, iterations=1)
            
            # Find newly added pixels
            new_pixels = (dilated - binary) > 0
            if not new_pixels.any():
                break
            
            # For each new pixel, average of its already-filled neighbors
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    shifted_mask = np.roll(np.roll(binary, -dy, axis=0), -dx, axis=1)
                    fillable = new_pixels & (shifted_mask > 0)
                    if fillable.any():
                        shifted_img = np.roll(np.roll(result, -dy, axis=0), -dx, axis=1)
                        result[fillable] = shifted_img[fillable]
            
            binary = dilated
        
        # Final blur for smooth transition
        result = cv2.GaussianBlur(result, (5, 5), 0)
        return result
