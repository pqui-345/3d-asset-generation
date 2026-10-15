import os
import sys
sys.path.append(os.getcwd())

import numpy as np
import trimesh
import sqlite3
from PIL import Image
import cv2
from services.template_service import TemplateService

os.chdir('E:\\xampp\htdocs\\3DGame')

def create_dummy_assets(mesh, asset_slug):
    """
    Tạo ảnh và mask giả lập từ mesh để test pipeline.
    """
    # 1. Tạo mask silhouette đơn giản bằng cách project mesh
    # Giả lập ảnh 512x512
    res = 512
    mask = np.zeros((res, res), dtype=np.uint8)
    
    # Lấy bounds để vẽ một hình ellipse đại diện cho silhouette
    bounds = mesh.bounds
    center = (bounds[0] + bounds[1]) / 2
    extents = (bounds[1] - bounds[0]) / 2
    
    # Vẽ ellipse vào mask
    cv2.ellipse(mask, (res//2, res//2), 
                (int(extents[0]*res), int(extents[1]*res)), 
                0, 0, 360, 255, -1)
    
    # 2. Tạo ảnh giả (màu ngẫu nhiên cho dễ phân biệt)
    color = np.random.randint(0, 255, (3,)).tolist()
    img_rgb = np.full((res, res, 3), color, dtype=np.uint8)
    # Thêm chút gradient cho sinh động
    cv2.circle(img_rgb, (res//2, res//2), res//3, (
        int(color[0]*0.7), int(color[1]*0.7), int(color[2]*0.7)
    ), -1)
    
    img_pil = Image.fromarray(img_rgb).convert('RGBA')
    
    # Tạo đường dẫn lưu tạm
    os.makedirs('static/uploads/benchmark', exist_ok=True)
    img_path = f'static/uploads/benchmark/{asset_slug}.png'
    img_pil.save(img_path)
    
    return img_pil, mask, img_path

def main():
    # Khởi tạo TemplateService
    service = TemplateService(
        template_dir='static/templates/core_100',
        index_path='data/template_index.faiss',
        metadata_db='data/template_metadata.sqlite'
    )
    
    # Lấy 5 template ngẫu nhiên từ DB
    conn = sqlite3.connect('data/template_metadata.sqlite')
    cursor = conn.execute("SELECT uid, name FROM templates ORDER BY RANDOM() LIMIT 5")
    templates = cursor.fetchall()
    conn.close()
    
    models_dir = 'static/models'
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"Starting benchmark for {len(templates)} templates...\n")
    
    for uid, name in templates:
        print(f"Testing template: {name} ({uid})")
        try:
            # Load mesh template
            glb_path = f'static/templates/core_100/{uid}.glb'
            template_mesh = trimesh.load(glb_path, force='mesh', process=False)
            
            # Tạo assets giả lập
            asset_slug = f"benchmark_{uid}"
            img_pil, mask, img_path = create_dummy_assets(template_mesh, asset_slug)
            
            # Chạy pipeline (ép buộc dùng template này thay vì search)
            # Để làm điều này, ta gọi trực tiếp logic deformation và texture
            
            # 1. Deform
            deformed_mesh = service.deformation.deform(template_mesh, mask)
            
            # 2. Texture
            texture = service.texture_transfer.transfer(deformed_mesh, img_pil, mask)
            texture_path = os.path.join(models_dir, f"{asset_slug}_texture.png")
            Image.fromarray(texture).save(texture_path)
            
            # 3. Export
            glb_out = os.path.join(models_dir, f"{asset_slug}.glb")
            deformed_mesh.export(glb_out)
            
            print(f"   SUCCESS -> {glb_out}")
        except Exception as e:
            print(f"   FAIL: {e}")

    print("\nBenchmark complete! Check 'static/models' folder.")

if __name__ == "__main__":
    main()
