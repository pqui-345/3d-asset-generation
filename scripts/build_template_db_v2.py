import os
import sys
import traceback
import numpy as np
import torch
import clip
import objaverse
import trimesh
import faiss
import sqlite3
import json
from PIL import Image
from tqdm import tqdm

os.chdir('E:\\xampp\\htdocs\\3DGame')

TEMPLATE_DIR = "static/templates/core_100"
DB_PATH = "data/template_metadata.sqlite"
INDEX_PATH = "data/template_index.faiss"
TARGET_COUNT = 100

EDU_KEYWORDS = [
    "sphere", "cube", "cylinder", "cone", "pyramid", "torus", "polyhedron",
    "cell", "dna", "rna", "protein", "virus", "bacteria", "organ", "heart",
    "brain", "lung", "kidney", "skeleton", "skull", "eye", "ear", "tooth",
    "molecule", "atom", "water", "methane", "ethanol", "benzene", "crystal",
    "gear", "pulley", "lever", "spring", "magnet", "circuit", "engine",
    "microscope", "beaker", "flask", "test_tube", "bunsen", "centrifuge",
    "book", "pencil", "ruler", "calculator", "compass", "notebook",
    "globe", "earth", "moon", "mars", "planet", "telescope", "map",
    "leaf", "flower", "root", "seed", "photosynthesis",
    "fossil", "dinosaur", "artifact", "ancient", "pottery"
]

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
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    print("[Curator] Loading Objaverse annotations...", flush=True)
    try:
        annotations = objaverse.load_annotations()
        print(f"[Curator] Loaded {len(annotations)} annotations", flush=True)
    except Exception as e:
        print(f"[Curator] FAIL load_annotations: {e}", flush=True)
        traceback.print_exc()
        return
    
    edu_uids = []
    for uid, ann in annotations.items():
        text = f"{ann.get('name','')} {ann.get('description','')} {' '.join([t['name'] for t in ann.get('tags',[])])}".lower()
        if any(kw in text for kw in EDU_KEYWORDS):
            edu_uids.append(uid)
    
    print(f"[Curator] Found {len(edu_uids)} educational models.", flush=True)
    sample_uids = edu_uids[:TARGET_COUNT]
    print(f"[Curator] Will try to download {len(sample_uids)} models.", flush=True)

    print("[Curator] Downloading models...", flush=True)
    try:
        objects = objaverse.load_objects(uids=sample_uids)
        print(f"[Curator] Downloaded {len(objects)} objects successfully.", flush=True)
    except Exception as e:
        print(f"[Curator] FAIL load_objects: {e}", flush=True)
        traceback.print_exc()
        return

    if len(objects) == 0:
        print("[Curator] No objects downloaded. Exiting.", flush=True)
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            uid TEXT PRIMARY KEY, faiss_idx INTEGER, name TEXT NOT NULL, category TEXT NOT NULL, 
            subcategory TEXT, glb_path TEXT NOT NULL, obj_path TEXT, mtl_path TEXT, texture_path TEXT, 
            vertices INTEGER NOT NULL, faces INTEGER NOT NULL, bounds_min_x REAL, bounds_min_y REAL, 
            bounds_min_z REAL, bounds_max_x REAL, bounds_max_y REAL, bounds_max_z REAL, 
            license TEXT DEFAULT 'CC-BY-4.0', source_url TEXT, tags TEXT, clip_embedding BLOB, 
            quality_score REAL DEFAULT 1.0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Curator] Loading CLIP on {device}...", flush=True)
    try:
        clip_model, preprocess = clip.load("ViT-B/32", device=device)
        clip_model.eval()
        print("[Curator] CLIP loaded.", flush=True)
    except Exception as e:
        print(f"[Curator] FAIL load CLIP: {e}", flush=True)
        traceback.print_exc()
        conn.close()
        return

    embeddings = []
    processed_uids = []

    for i, (uid, path) in enumerate(tqdm(objects.items(), desc="Processing")):
        try:
            mesh = trimesh.load(path, force='mesh')
            mesh = normalize_mesh(mesh)
            
            local_path = os.path.join(TEMPLATE_DIR, f"{uid}.glb")
            mesh.export(local_path)
            
            with torch.no_grad():
                name = annotations.get(uid, {}).get('name', 'object')
                text = clip.tokenize(name).to(device)
                emb = clip_model.encode_text(text).cpu().numpy()[0].astype(np.float32)
                emb /= np.linalg.norm(emb)
            
            bounds = mesh.bounds
            conn.execute("""
                INSERT OR REPLACE INTO templates 
                (uid, name, category, glb_path, vertices, faces, 
                 bounds_min_x, bounds_min_y, bounds_min_z, 
                 bounds_max_x, bounds_max_y, bounds_max_z, clip_embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, annotations.get(uid, {}).get('name', 'unnamed'), "educational", 
                  f"static/templates/core_100/{uid}.glb", len(mesh.vertices), len(mesh.faces),
                  bounds[0,0], bounds[0,1], bounds[0,2], bounds[1,0], bounds[1,1], bounds[1,2],
                  emb.tobytes()))
            
            if (i + 1) % 10 == 0:
                conn.commit()
                print(f"\n[Curator] Progress: {i+1}/{len(objects)} committed.", flush=True)
                
            embeddings.append(emb)
            processed_uids.append(uid)
        except Exception as e:
            print(f"\n[Curator] Error processing {uid}: {e}", flush=True)

    conn.commit()

    if embeddings:
        embeddings_np = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings_np)
        index = faiss.IndexFlatL2(embeddings_np.shape[1])
        index.add(embeddings_np)
        faiss.write_index(index, INDEX_PATH)
        for idx, uid in enumerate(processed_uids):
            conn.execute("UPDATE templates SET faiss_idx = ? WHERE uid = ?", (idx, uid))
        conn.commit()
        print(f"[Curator] FAISS index built with {len(embeddings)} vectors.", flush=True)
    else:
        print("[Curator] No embeddings generated!", flush=True)

    conn.close()
    print(f"[Curator] Done! Successfully curated {len(processed_uids)} templates.", flush=True)

if __name__ == "__main__":
    main()
