import os
import csv
import trimesh
import numpy as np

objects = ["Dog", "AMBERLIGHT_UP_W", "Razer_BlackWidow_Ultimate_2014_Mechanical_Gaming_Keyboard"]
views = ["front", "left", "back", "right"]
base = "experiments/outputs/multiview"

rows = []
for obj in objects:
    for view in views:
        glb_path = os.path.join(base, obj, view, "0", "mesh.glb")
        success = os.path.exists(glb_path)
        vertices = 0
        faces = 0
        size_bytes = 0
        if success:
            mesh = trimesh.load(glb_path)
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)
            vertices = int(mesh.vertices.shape[0])
            faces = int(mesh.faces.shape[0])
            size_bytes = os.path.getsize(glb_path)
        rows.append({
            "object_id": obj,
            "view": view,
            "success": str(success),
            "vertices": vertices,
            "faces": faces,
            "size_bytes": size_bytes
        })

out_csv = os.path.join(base, "multiview_results.csv")
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["object_id", "view", "success", "vertices", "faces", "size_bytes"])
    w.writeheader()
    w.writerows(rows)

print(f"Written {len(rows)} rows to {out_csv}")
print()
print(f"{'object_id':<55} {'view':<8} {'success':<8} {'vertices':<10} {'faces':<10} {'size_bytes':<12}")
print("-" * 105)
for r in rows:
    print(f"{r['object_id']:<55} {r['view']:<8} {r['success']:<8} {r['vertices']:<10} {r['faces']:<10} {r['size_bytes']:<12}")
