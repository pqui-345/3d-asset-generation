"""
Render multi-view images for core_100 templates and add to FAISS index + view_embeddings table.
"""
import os, sys, json, sqlite3
import numpy as np
import torch
import clip
import trimesh
import faiss
import cv2
from PIL import Image
from tqdm import tqdm

os.chdir('E:\\xampp\\htdocs\\3DGame')
sys.path.append(os.getcwd())

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
RENDER_SIZE = 512
RENDER_ANGLES = [
    ("front", 0, 0, 0), ("back", 0, 180, 0),
    ("left", 0, -90, 0), ("right", 0, 90, 0),
    ("top", -90, 0, 0), ("bottom", 90, 0, 0),
]
DB_PATH = "data/template_metadata.sqlite"
INDEX_PATH = "data/template_index.faiss"
META_FILE = INDEX_PATH.replace('.faiss', '_metadata.json')

def render_multiview(mesh, size=RENDER_SIZE):
    results = []
    vertices = mesh.vertices
    faces = mesh.faces
    for name, rx, ry, rz in RENDER_ANGLES:
        angles = np.radians([rx, ry, rz])
        Rx = np.array([[1,0,0],[0,np.cos(angles[0]),-np.sin(angles[0])],[0,np.sin(angles[0]),np.cos(angles[0])]])
        Ry = np.array([[np.cos(angles[1]),0,np.sin(angles[1])],[0,1,0],[-np.sin(angles[1]),0,np.cos(angles[1])]])
        Rz = np.array([[np.cos(angles[2]),-np.sin(angles[2]),0],[np.sin(angles[2]),np.cos(angles[2]),0],[0,0,1]])
        R = Rz @ Ry @ Rx
        v_rot = vertices @ R.T
        scale = min(size/max(abs(v_rot[:,0]).max(),1e-6), size/max(abs(v_rot[:,1]).max(),1e-6)) * 0.8
        px = (v_rot[:,0]*scale + size/2).astype(int)
        py = (v_rot[:,1]*scale + size/2).astype(int)
        img = np.full((size,size,4), [255,255,255,0], dtype=np.uint8)
        for tri in faces:
            pts = np.column_stack([px[tri], py[tri]])
            cv2.fillConvexPoly(img, pts, (200,200,200,255))
        z = v_rot[:,2]
        z_norm = (z-z.min())/max(z.max()-z.min(), 1e-6)
        for i in range(len(vertices)):
            if 0 <= px[i] < size and 0 <= py[i] < size:
                shade = int(60 + 140*(1-z_norm[i]))
                cv2.circle(img, (px[i],py[i]), 2, (shade,shade,shade,255), -1)
        for tri in faces:
            pts = np.column_stack([px[tri], py[tri]])
            cv2.fillConvexPoly(img, pts, (200,200,200,255))
        results.append((name, Image.fromarray(img, 'RGBA')))
    return results


def main():
    print("Loading CLIP...")
    clip_model, preprocess = clip.load("ViT-B/32", device=DEVICE)
    clip_model.eval()
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get core_100 templates (faiss_idx 0-99)
    cursor = conn.execute("SELECT * FROM templates WHERE faiss_idx < 100 ORDER BY faiss_idx")
    core_templates = []
    for row in cursor.fetchall():
        core_templates.append(dict(row) if hasattr(row, 'keys') else None)
    
    # Actually simpler to use the DB directly
    cursor = conn.execute("SELECT uid, faiss_idx, glb_path FROM templates WHERE dataset IS NULL OR dataset='objaverse' ORDER BY faiss_idx")
    rows = cursor.fetchall()
    print(f"Core templates to process: {len(rows)}")
    
    # Check which already have views
    already_done = set()
    for r in conn.execute("SELECT DISTINCT uid FROM view_embeddings"):
        already_done.add(r[0])
    print(f"Already have views: {len(already_done)}")
    
    # Load existing metadata
    meta = []
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            meta = json.load(f)
    
    new_embs = []
    new_meta = []
    total_done = 0
    
    for uid, faiss_idx, glb_path in rows:
        if uid in already_done:
            continue
        
        full_path = glb_path
        if not os.path.exists(full_path):
            # Try alternative paths
            alt = os.path.join("static/templates/core_100", os.path.basename(full_path))
            if os.path.exists(alt):
                full_path = alt
            else:
                continue
        
        try:
            mesh = trimesh.load(full_path, force='mesh', process=False)
            if len(mesh.vertices) < 5:
                continue
            
            views = render_multiview(mesh)
            
            for vname, vimg in views:
                image = preprocess(vimg).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    vfeat = clip_model.encode_image(image)
                    vfeat /= vfeat.norm(dim=-1, keepdim=True)
                vemb = vfeat[0].cpu().numpy().astype(np.float32)
                
                conn.execute("INSERT OR REPLACE INTO view_embeddings VALUES (?, ?, ?)",
                             (uid, vname, vemb.tobytes()))
                new_embs.append(vemb)
                new_meta.append([uid, vname, full_path])
            
            total_done += 1
            if total_done % 10 == 0:
                conn.commit()
                print(f"  Processed {total_done}...")
                
        except Exception as e:
            print(f"  Error {uid}: {e}")
    
    conn.commit()
    print(f"\nNew views rendered: {total_done} models")
    
    # Add to FAISS
    if new_embs:
        embs = np.array(new_embs).astype('float32')
        faiss.normalize_L2(embs)
        
        index = faiss.read_index(INDEX_PATH)
        prev_total = index.ntotal
        index.add(embs)
        faiss.write_index(index, INDEX_PATH)
        
        meta.extend(new_meta)
        with open(META_FILE, 'w') as f:
            json.dump(meta, f)
        
        print(f"FAISS: {prev_total} -> {index.ntotal} vectors")
    
    conn.close()
    print("Done!")


if __name__ == '__main__':
    main()
