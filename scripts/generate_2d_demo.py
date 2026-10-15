import os, sys
import numpy as np
import trimesh
import cv2
from PIL import Image

os.chdir('E:\\xampp\\htdocs\\3DGame')
sys.path.append(os.getcwd())

RENDER_SIZE = 512
RENDER_ANGLES = [
    ("front", 0, 0, 0),
    ("back", 0, 180, 0),
    ("left", 0, -90, 0),
    ("right", 0, 90, 0),
    ("top", -90, 0, 0),
    ("bottom", 90, 0, 0),
]

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
    models_dir = 'static/models'
    output_dir = 'static/demo_2d'
    os.makedirs(output_dir, exist_ok=True)
    
    files = [f for f in os.listdir(models_dir) if f.endswith(('.glb', '.obj', '.ply'))]
    print(f"Found {len(files)} 3D models in {models_dir}")
    
    for f in files:
        file_path = os.path.join(models_dir, f)
        base_name = os.path.splitext(f)[0]
        try:
            print(f"Processing {f}...")
            mesh = trimesh.load(file_path, force='mesh', process=False)
            if isinstance(mesh, trimesh.Scene):
                geom = list(mesh.geometry.values())
                if not geom:
                    print(f"  Empty geometry in {f}, skipping.")
                    continue
                mesh = trimesh.util.concatenate(geom)
                
            if len(mesh.vertices) < 5:
                print(f"  Too few vertices in {f}, skipping.")
                continue
                
            # Normalize mesh
            center = mesh.vertices.mean(axis=0)
            mesh.vertices -= center
            max_dist = np.linalg.norm(mesh.vertices, axis=1).max()
            if max_dist > 0:
                mesh.vertices /= max_dist
            mesh.vertices -= mesh.vertices.mean(axis=0)
            
            views = render_multiview(mesh)
            
            # Save views
            for vname, vimg in views:
                out_path = os.path.join(output_dir, f"{base_name}_{vname}.png")
                vimg.save(out_path)
            print(f"  Saved {len(views)} views for {f}")
            
        except Exception as e:
            print(f"  Error processing {f}: {e}")
            
if __name__ == '__main__':
    main()
