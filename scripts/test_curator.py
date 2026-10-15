import os
import numpy as np
import torch
import clip
import objaverse
import trimesh
import faiss
import sqlite3
from PIL import Image

def normalize_mesh(mesh):
    center = mesh.vertices.mean(axis=0)
    mesh.vertices -= center
    max_dist = np.linalg.norm(mesh.vertices, axis=1).max()
    if max_dist > 0:
        mesh.vertices /= max_dist
    bounds = mesh.bounds
    mesh.vertices[:, 0] -= (bounds[1,0] + bounds[0,0]) / 2
    mesh.vertices[:, 2] -= (bounds[1,2] + bounds[0,2]) / 2
    mesh.vertices[:, 1] -= bounds[0,1]
    return mesh

def main():
    os.makedirs("static/templates/core_100", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Test with just 1 object
    uid = "8476c4170df24cf5bbe6967222d1a42d" # from objaverse docs
    print(f"Testing download for {uid}...")
    try:
        objects = objaverse.load_objects([uid])
        path = objects[uid]
        print(f"Downloaded to {path}")
        
        mesh = trimesh.load(path, force='mesh')
        mesh = normalize_mesh(mesh)
        local_path = f"static/templates/core_100/{uid}.glb"
        mesh.export(local_path)
        print(f"Saved to {local_path}")
        
        # DB
        conn = sqlite3.connect("data/template_metadata.sqlite")
        conn.execute("CREATE TABLE IF NOT EXISTS templates (uid TEXT PRIMARY KEY, faiss_idx INTEGER, name TEXT, category TEXT, glb_path TEXT, vertices INTEGER, faces INTEGER, bounds_min_x REAL, bounds_min_y REAL, bounds_min_z REAL, bounds_max_x REAL, bounds_max_y REAL, bounds_max_z REAL, clip_embedding BLOB)")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        text = clip.tokenize("a 3d model of a chair").to(device)
        with torch.no_grad():
            emb = model.encode_text(text).cpu().numpy()[0].astype(np.float32)
            emb /= np.linalg.norm(emb)
            
        bounds = mesh.bounds
        conn.execute("INSERT OR REPLACE INTO templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (uid, 0, "chair", "furniture", local_path, len(mesh.vertices), len(mesh.faces),
                      bounds[0,0], bounds[0,1], bounds[0,2], bounds[1,0], bounds[1,1], bounds[1,2], emb.tobytes()))
        conn.commit()
        conn.close()
        
        # Index
        index = faiss.IndexFlatL2(512)
        index.add(emb.reshape(1, -1))
        faiss.write_index(index, "data/template_index.faiss")
        print("DB and Index created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
