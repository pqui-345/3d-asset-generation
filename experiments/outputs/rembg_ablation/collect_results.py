import os, csv, trimesh

objects = [
    "BAGEL_WITH_CHEESE",
    "Dog",
    "Racoon",
    "Razer_BlackWidow_Ultimate_2014_Mechanical_Gaming_Keyboard",
    "Hefty_Waste_Basket_Decorative_Bronze_85_liter",
]

rows = []
for obj in objects:
    row = {"object_id": obj}
    for mode in ["with_rembg", "without_rembg"]:
        prefix = mode
        glb_path = f"experiments/outputs/rembg_ablation/{mode}/{obj}/0/mesh.glb"
        success = os.path.exists(glb_path)
        row[f"{prefix}_success"] = str(success)
        if success:
            sz = os.path.getsize(glb_path)
            scene = trimesh.load(glb_path)
            if isinstance(scene, trimesh.Scene):
                mesh = trimesh.util.concatenate(scene.dump(concatenate=True))
            else:
                mesh = scene
            verts = len(mesh.vertices)
            faces = len(mesh.faces)
            row[f"{prefix}_verts"] = verts
            row[f"{prefix}_faces"] = faces
            row[f"{prefix}_size_mb"] = round(sz / (1024 * 1024), 2)
        else:
            row[f"{prefix}_verts"] = 0
            row[f"{prefix}_faces"] = 0
            row[f"{prefix}_size_mb"] = 0
    rows.append(row)

fieldnames = [
    "object_id",
    "with_rembg_success",
    "with_rembg_verts",
    "with_rembg_faces",
    "with_rembg_size_mb",
    "without_rembg_success",
    "without_rembg_verts",
    "without_rembg_faces",
    "without_rembg_size_mb",
]
csv_path = "experiments/outputs/rembg_ablation/ablation_results.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"Saved to {csv_path}")
print()
hdr = f"{'object_id':55s} | {'w_verts':>8s} | {'wo_verts':>8s} | {'w_faces':>8s} | {'wo_faces':>8s} | {'w_size':>7s} | {'wo_size':>7s}"
print(hdr)
print("-" * len(hdr))
for r in rows:
    oid = r["object_id"][:54]
    print(
        f"{oid:55s} | {r['with_rembg_verts']:8d} | {r['without_rembg_verts']:8d} | {r['with_rembg_faces']:8d} | {r['without_rembg_faces']:8d} | {r['with_rembg_size_mb']:7.2f} | {r['without_rembg_size_mb']:7.2f}"
    )
