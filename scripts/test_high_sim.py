import os
import sys
sys.path.append(os.getcwd())
os.chdir('E:\\xampp\\htdocs\\3DGame')

import numpy as np
import trimesh
from PIL import Image
import cv2

from services.template_service import TemplateService

# Create a test with a template that matches perfectly (screenshot scenario)
# Load the first template from DB
import sqlite3
conn = sqlite3.connect('data/template_metadata.sqlite')
cursor = conn.execute("SELECT uid, name, glb_path FROM templates LIMIT 1")
row = cursor.fetchone()
conn.close()

uid, name, glb_path = row
print(f"Testing template: {name} ({uid})")

# Load template mesh
template_mesh = trimesh.load(glb_path, force='mesh', process=False)
print(f"Template: verts={len(template_mesh.vertices)}, has_visual={template_mesh.visual is not None}")

# Check if template has texture
has_tex = False
if hasattr(template_mesh.visual, 'material') and template_mesh.visual.material:
    mat = template_mesh.visual.material
    if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture:
        has_tex = True
        print(f"  Template HAS baseColorTexture: {type(mat.baseColorTexture)}")
    else:
        print(f"  Template NO baseColorTexture")

# Create a perfect-match image from the template itself
# Render a simple silhouette
res = 512
mask = np.zeros((res, res), dtype=np.uint8)
bounds = template_mesh.bounds
center = (bounds[0] + bounds[1]) / 2
extent = bounds[1] - bounds[0]
# Draw ellipse representing the object
cv2.ellipse(mask, (res//2, res//2), (int(res*0.3), int(res*0.35)), 0, 0, 360, 255, -1)

# Create a colored image (simulating screenshot)
img_rgb = np.full((res, res, 3), (180, 100, 80), dtype=np.uint8)  # brownish
cv2.ellipse(img_rgb, (res//2, res//2), (int(res*0.3), int(res*0.35)), 0, 0, 360, (150, 80, 60), -1)

img_pil = Image.fromarray(img_rgb).convert('RGBA')
# Add alpha from mask
img_pil.putalpha(Image.fromarray(mask))

# Test TemplateService
service = TemplateService(
    template_dir='static/templates/core_100',
    index_path='data/template_index.faiss',
    metadata_db='data/template_metadata.sqlite'
)

# We need to bypass the recognition/retrieval and directly test the deformation + texture
# For a real test, we'd need to feed an image that retrieves this exact template
# But we can at least test the deformation

from services.deformation_service import DeformationService
deform = DeformationService()

print("\n--- Testing Deformation (strength=0.3 for high sim) ---")
deformed = deform.deform(template_mesh, mask, strength=0.3)
print(f"Deformed: verts={len(deformed.vertices)}, has_visual={deformed.visual is not None}")
print(f"  Visual type: {type(deformed.visual)}")

# Check if visual/texture preserved
if hasattr(deformed.visual, 'material') and deformed.visual.material:
    mat = deformed.visual.material
    if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture:
        print("  SUCCESS: baseColorTexture PRESERVED after deformation!")
    else:
        print("  WARNING: baseColorTexture lost after deformation")

# Export
deformed.export('static/models/test_high_sim.glb')
print("\nExported to static/models/test_high_sim.glb")
print("Open in 3D viewer to check texture quality")