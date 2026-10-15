import os, sys
os.chdir('E:\\xampp\\htdocs\\3DGame')
sys.path.append('.')

from services.template_service import TemplateService
from PIL import Image
import numpy as np
import cv2

# Create a test image that should match something in the DB
res = 512
img = np.full((res, res, 3), (180, 100, 80), dtype=np.uint8)
cv2.ellipse(img, (res//2, res//2), (int(res*0.35), int(res*0.35)), 0, 0, 360, (150, 80, 60), -1)
mask = np.zeros((res, res), dtype=np.uint8)
cv2.ellipse(mask, (res//2, res//2), (int(res*0.35), int(res*0.35)), 0, 0, 360, 255, -1)

pil = Image.fromarray(img).convert('RGBA')
pil.putalpha(Image.fromarray(mask))
pil.save('static/uploads/test_chair.png')

service = TemplateService(
    template_dir='static/templates/core_100',
    index_path='data/template_index.faiss',
    metadata_db='data/template_metadata.sqlite'
)

# Test recognition
recog = service.recognition.recognize(pil)
cat = recog['category']
conf = recog['confidence']
print('Category: {} ({:.2f})'.format(cat, conf))

# Test retrieval
candidates = service.retrieval.search(recog['embedding'], k=3, category_filter=cat)
print('Found {} candidates:'.format(len(candidates)))
for c in candidates:
    print('  {} (sim={:.3f})'.format(c['name'], c['similarity']))

# Test full generate_3d (will use high-sim texture preservation if sim >= 0.85)
result = service.generate_3d(
    pil, 'static/uploads/test_chair.png', [], 'static/models', 'test_chair'
)
print('Result: {} sim={:.3f}'.format(result['method'], result['similarity']))
print('GLB: {}'.format(result['glb_path']))