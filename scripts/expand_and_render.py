"""
Fast-expand Objaverse to 500+ educational models + render multiview + build image-index.
"""
import os, sys, gc, json, time, sqlite3
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
OUT_DIR = "static/templates/objaverse_ext"
DB_PATH = "data/template_metadata.sqlite"
INDEX_PATH = "data/template_index.faiss"

EXTRA_KEYWORDS = [
    "sphere","cube","cylinder","cone","pyramid","torus","prism",
    "cell","dna","protein","virus","bacteria","heart","brain","lung",
    "skeleton","skull","eye","ear","neuron","chromosome","flower","leaf","tree",
    "molecule","atom","crystal","diamond","graphite","lattice",
    "gear","pulley","lever","spring","magnet","circuit","wheel","axle",
    "microscope","beaker","flask","test_tube","pendulum","lens","prism",
    "globe","earth","moon","planet","telescope","mountain","volcano",
    "fossil","dinosaur","rock","mineral","gemstone",
    "book","pencil","ruler","compass","protractor","globe","clock",
    "bottle","cup","glass","plate","bowl","fork","knife","spoon",
    "apple","banana","orange","lemon","strawberry","grape",
    "chair","table","desk","bed","cabinet","shelf","bookcase","sofa",
    "hammer","screwdriver","wrench","drill","saw","phone","laptop",
    "car","truck","bus","bicycle","train","airplane","boat","ship",
    "rocket","satellite","spacecraft","helmet","shoe","shirt","hat",
    "key","lock","chain","bell","button","plug","socket","pipe",
    "window","door","stairs","roof","bridge","fence","gate","tower",
    "castle","house","building","pyramid","temple","column",
    "fish","bird","dog","cat","horse","elephant","lion","tiger",
    "bear","rabbit","sheep","cow","duck","chicken","snake","turtle",
    "butterfly","beetle","ant","bee","spider","dragonfly",
    "star","moon_sun","cloud","rainbow","snowflake","triangle",
    "square","circle","rectangle","oval","pentagon","hexagon","octagon",
    "geometry","math","educational","school","classroom","teacher",
    "student","backpack","chalkboard","whiteboard","paint","brush",
    "color","puzzle","block","toy","game","dice","marble","ball",
]


def normalize_mesh(mesh):
    center = mesh.vertices.mean(axis=0)
    mesh.vertices -= center
    max_dist = np.linalg.norm(mesh.vertices, axis=1).max()
    if max_dist > 0:
        mesh.vertices /= max_dist
    center = mesh.vertices.mean(axis=0)
    mesh.vertices -= center
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
    import objaverse
    
    os.makedirs(OUT_DIR, exist_ok=True)
    
    print("Loading CLIP...")
    clip_model, preprocess = clip.load("ViT-B/32", device=DEVICE)
    clip_model.eval()
    
    conn = sqlite3.connect(DB_PATH)
    
    # Ensure extra columns exist
    for col in ['dataset', 'bounds']:
        try:
            conn.execute(f'ALTER TABLE templates ADD COLUMN {col} TEXT')
        except:
            pass
    
    conn.execute('''CREATE TABLE IF NOT EXISTS view_embeddings (
        uid TEXT, view_name TEXT, embedding BLOB,
        PRIMARY KEY (uid, view_name)
    )''')
    conn.commit()
    
    # Get existing UIDs across all datasets
    existing_uids = set()
    cursor = conn.execute("SELECT uid FROM templates")
    for row in cursor:
        existing_uids.add(row[0])
    for f in os.listdir("static/templates/core_100"):
        if f.endswith('.glb'):
            existing_uids.add(f.replace('.glb', ''))
    for f in os.listdir(OUT_DIR):
        if f.endswith('.glb'):
            existing_uids.add(f.replace('.glb', ''))
    print(f"Existing UIDs: {len(existing_uids)}")
    
    # Load annotations
    print("Loading Objaverse annotations...")
    annotations = objaverse.load_annotations()
    
    # Find educational models
    edu_uids = []
    for uid, ann in tqdm(annotations.items(), desc="Filtering educational"):
        text = f"{ann.get('name','')} {ann.get('description','')} {' '.join(t.get('name','') for t in ann.get('tags',[]))}".lower()
        if any(kw.lower() in text for kw in EXTRA_KEYWORDS):
            if uid not in existing_uids:
                edu_uids.append(uid)
    
    print(f"New educational UIDs found: {len(edu_uids)}")
    
    TARGET = min(30, len(edu_uids))
    selected_uids = edu_uids[:TARGET]
    print(f"Target: {TARGET} models")
    
    BATCH_SIZE = 50
    cursor = conn.execute("SELECT MAX(faiss_idx) FROM templates")
    max_idx = cursor.fetchone()[0]
    faiss_idx_offset = (max_idx if max_idx is not None else -1) + 1
    
    all_new_embeddings = []
    all_new_metadata = []
    total_processed = 0
    
    for batch_start in range(0, len(selected_uids), BATCH_SIZE):
        batch_uids = selected_uids[batch_start:batch_start+BATCH_SIZE]
        
        try:
            objects = objaverse.load_objects(uids=batch_uids)
        except Exception as e:
            print(f"Download batch error: {e}, trying smaller...")
            try:
                objects = objaverse.load_objects(uids=batch_uids[:10])
            except:
                continue
        
        for uid, path in tqdm(objects.items(), desc=f"Batch {batch_start//BATCH_SIZE+1}"):
            try:
                glb_file = os.path.join(OUT_DIR, f"{uid}.glb")
                
                mesh = trimesh.load(path, force='mesh', process=False)
                
                if isinstance(mesh, trimesh.Scene):
                    geom = list(mesh.geometry.values())
                    if not geom:
                        continue
                    mesh = trimesh.util.concatenate(geom)

                if len(mesh.vertices) < 20 or len(mesh.vertices) > 500000:
                    continue
                
                mesh = normalize_mesh(mesh)
                vc = np.full((len(mesh.vertices), 4), [200,200,200,255], dtype=np.uint8)
                mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=vc)
                mesh.export(glb_file)
                
                name = annotations.get(uid, {}).get('name', '')
                bounds = mesh.bounds
                b = bounds.tolist()
                
                # Text embedding
                with torch.no_grad():
                    tokens = clip.tokenize([name or uid]).to(DEVICE)
                    text_feat = clip_model.encode_text(tokens)
                    text_feat /= text_feat.norm(dim=-1, keepdim=True)
                text_emb = text_feat[0].cpu().numpy().astype(np.float32)
                
                # Insert using original column schema
                conn.execute(
                    "INSERT OR REPLACE INTO templates "
                    "(uid, faiss_idx, name, category, glb_path, vertices, faces, "
                    "bounds_min_x, bounds_min_y, bounds_min_z, bounds_max_x, bounds_max_y, bounds_max_z, "
                    "clip_embedding, dataset, bounds) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid, int(faiss_idx_offset + total_processed),
                     name, 'educational', glb_file,
                     int(len(mesh.vertices)), int(len(mesh.faces)),
                     float(b[0][0]), float(b[0][1]), float(b[0][2]),
                     float(b[1][0]), float(b[1][1]), float(b[1][2]),
                     text_emb.tobytes(), 'objaverse_ext', json.dumps(b))
                )
                
                # Render views + image embeddings
                views = render_multiview(mesh)
                for vname, vimg in views:
                    image = preprocess(vimg).unsqueeze(0).to(DEVICE)
                    with torch.no_grad():
                        vfeat = clip_model.encode_image(image)
                        vfeat /= vfeat.norm(dim=-1, keepdim=True)
                    vemb = vfeat[0].cpu().numpy().astype(np.float32)
                    conn.execute("INSERT OR REPLACE INTO view_embeddings VALUES (?, ?, ?)",
                                 (uid, vname, vemb.tobytes()))
                    all_new_embeddings.append(vemb)
                    all_new_metadata.append((uid, vname, glb_file))
                
                all_new_embeddings.append(text_emb)
                all_new_metadata.append((uid, 'text', glb_file))
                
                total_processed += 1
                
                if total_processed % 10 == 0:
                    conn.commit()
                    
            except Exception as e:
                print(f"  Error {uid}: {e}")
                continue
        
        conn.commit()
        gc.collect()
        print(f"  Batch done. Total processed: {total_processed}")
    
    print(f"\nTotal new models processed: {total_processed}")
    
    # Update FAISS
    if all_new_embeddings:
        embs = np.array(all_new_embeddings).astype('float32')
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
        existing_meta.extend(all_new_metadata)
        with open(meta_file, 'w') as f:
            json.dump(existing_meta, f)
        
        print(f"FAISS index: {index.ntotal} vectors total")
    
    conn.close()
    print("Done!")


if __name__ == '__main__':
    main()
