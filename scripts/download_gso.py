"""
Download Google Scanned Objects - subset of real scanned household items.
"""
import os, sys, gc, json, sqlite3
import numpy as np
import torch
import clip
import trimesh
import faiss
import cv2
import requests
from PIL import Image
from tqdm import tqdm

os.chdir('E:\\xampp\\htdocs\\3DGame')
sys.path.append(os.getcwd())

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUT_DIR = "static/templates/gso"
DB_PATH = "data/template_metadata.sqlite"
INDEX_PATH = "data/template_index.faiss"

# GSO manifest URL
MANIFEST_URL = "https://raw.githubusercontent.com/google-research/google-scanned-objects/master/manifest.txt"
BASE_URL = "https://storage.googleapis.com/google-scanned-objects/objects"

RENDER_SIZE = 512
RENDER_ANGLES = [
    ("front", 0, 0, 0), ("back", 0, 180, 0),
    ("left", 0, -90, 0), ("right", 0, 90, 0),
    ("top", -90, 0, 0), ("bottom", 90, 0, 0),
]


def normalize_mesh(mesh):
    center = mesh.vertices.mean(axis=0)
    mesh.vertices -= center
    max_dist = np.linalg.norm(mesh.vertices, axis=1).max()
    if max_dist > 0:
        mesh.vertices /= max_dist
    return mesh


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
        img = np.zeros((size,size,4), dtype=np.uint8)
        for tri in faces:
            pts = np.column_stack([px[tri], py[tri]])
            cv2.fillConvexPoly(img, pts, (200,200,200,255))
        z = v_rot[:,2]
        z_norm = (z-z.min())/max(z.max()-z.min(), 1e-6)
        for i in range(len(vertices)):
            if 0 <= px[i] < size and 0 <= py[i] < size:
                shade = int(60 + 140*(1-z_norm[i]))
                cv2.circle(img, (px[i],py[i]), 2, (shade,shade,shade,255), -1)
        results.append((name, Image.fromarray(img, 'RGBA')))
    return results


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Fetch manifest
    print("Fetching GSO manifest...")
    resp = requests.get(MANIFEST_URL, timeout=30)
    lines = [l.strip() for l in resp.text.strip().split('\n') if l.strip()]
    print(f"Manifest entries: {len(lines)}")
    
    # Filter to GLB files
    glb_paths = [l for l in lines if l.endswith('.glb')]
    print(f"GLB files: {len(glb_paths)}")
    
    if not glb_paths:
        print("No GLBs found in manifest. Trying alternative URL patterns...")
        # Try common GSO object names
        common = ["apple","chair","cup","bowl","plate","bottle","book","shoe","hat",
                   "ball","camera","cellphone","keyboard","mouse","lamp","clock",
                   "teacup","vase","candle","soap","spoon","fork","knife","mug",
                   "pan","pot","screwdriver","hammer","wrench","drill","scissors",
                   "backpack","purse","wallet","glasses","watch","ring","key",
                   "remote","controller","headphone","speaker","toy","doll",
                   "teddy","piggy","bank","globe","globe","helmet","shield",
                   "sword","box","basket","bag","sack","bottle","jar","can"]
        for i, obj in enumerate(common):
            glb_paths.append(f"{obj}/{obj}.glb")
        glb_paths = glb_paths[:200]
        print(f"Using fallback: {len(glb_paths)} objects")
    
    # Limit to 200 models
    glb_paths = glb_paths[:200]
    TARGET_COUNT = len(glb_paths)
    
    # Load CLIP
    print("Loading CLIP...")
    clip_model, preprocess = clip.load("ViT-B/32", device=DEVICE)
    clip_model.eval()
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get existing GSO UIDs
    existing = set()
    for f in os.listdir(OUT_DIR):
        if f.endswith('.glb'):
            existing.add(f.replace('.glb', ''))
    print(f"Already downloaded GSO: {len(existing)}")
    
    # Get max FAISS index
    cursor = conn.execute("SELECT MAX(faiss_idx) FROM templates")
    max_idx = cursor.fetchone()[0] or 0
    
    faiss_count = 0
    all_new_embs = []
    all_new_meta = []
    
    for path in tqdm(glb_paths, desc="Downloading GSO"):
        uid = path.replace('/', '_').replace('.glb', '')
        glb_file = os.path.join(OUT_DIR, f"{uid}.glb")
        if uid in existing or os.path.exists(glb_file):
            continue
        
        url = f"{BASE_URL}/{path}" if not path.startswith('/') else f"{BASE_URL}{path}"
        
        try:
            resp = requests.get(url, timeout=120)
            if resp.status_code != 200:
                continue
            
            with open(glb_file, 'wb') as f:
                f.write(resp.content)
            
            mesh = trimesh.load(glb_file, force='mesh', process=False)
            if len(mesh.vertices) < 20:
                os.remove(glb_file)
                continue
            
            mesh = normalize_mesh(mesh)
            vc = np.full((len(mesh.vertices), 4), [200,200,200,255], dtype=np.uint8)
            mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=vc)
            mesh.export(glb_file)
            
            name = uid.replace('_', ' ')
            
            # Text embedding
            with torch.no_grad():
                tokens = clip.tokenize([f"a {name}"]).to(DEVICE)
                text_feat = clip_model.encode_text(tokens)
                text_feat /= text_feat.norm(dim=-1, keepdim=True)
            text_emb = text_feat[0].cpu().numpy().astype(np.float32)
            
            conn.execute(
                "INSERT OR REPLACE INTO templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, name, 'household', 'gso', glb_file, text_emb.tobytes(),
                 json.dumps(mesh.bounds.tolist()), int(len(mesh.vertices)),
                 int(len(mesh.faces)), int(max_idx + 1 + faiss_count))
            )
            
            # Render views
            views = render_multiview(mesh)
            for vname, vimg in views:
                image = preprocess(vimg).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    vfeat = clip_model.encode_image(image)
                    vfeat /= vfeat.norm(dim=-1, keepdim=True)
                vemb = vfeat[0].cpu().numpy().astype(np.float32)
                conn.execute("INSERT OR REPLACE INTO view_embeddings VALUES (?, ?, ?)",
                             (uid, vname, vemb.tobytes()))
                all_new_embs.append(vemb)
                all_new_meta.append((uid, vname, glb_file))
            
            all_new_embs.append(text_emb)
            all_new_meta.append((uid, 'text', glb_file))
            
            faiss_count += 1
            
            if faiss_count % 10 == 0:
                conn.commit()
                
        except Exception as e:
            print(f"Error {path}: {e}")
            if os.path.exists(glb_file):
                os.remove(glb_file)
            continue
    
    conn.commit()
    print(f"Downloaded {faiss_count} new GSO models")
    
    # Update FAISS
    if all_new_embs:
        embs = np.array(all_new_embs).astype('float32')
        faiss.normalize_L2(embs)
        if os.path.exists(INDEX_PATH):
            index = faiss.read_index(INDEX_PATH)
            index.add(embs)
        else:
            index = faiss.IndexFlatIP(embs.shape[1])
            index.add(embs)
        faiss.write_index(index, INDEX_PATH)
        
        meta_file = INDEX_PATH.replace('.faiss', '_metadata.json')
        existing_meta = []
        if os.path.exists(meta_file):
            with open(meta_file) as f:
                existing_meta = json.load(f)
        existing_meta.extend(all_new_meta)
        with open(meta_file, 'w') as f:
            json.dump(existing_meta, f)
        print(f"FAISS index: {index.ntotal} vectors")
    
    conn.close()
    print("GSO download complete!")


if __name__ == '__main__':
    main()
