import os, sys, cv2, numpy as np
from PIL import Image
os.chdir('E:\\xampp\\htdocs\\3DGame')
sys.path.append(os.getcwd())

from services.recognition_service import RecognitionService
from services.retrieval_service import RetrievalService
from services.template_database import TemplateDatabase

recog = RecognitionService()
retrieval = RetrievalService('data/template_index.faiss', TemplateDatabase('data/template_metadata.sqlite'))

# Test with a simple image
img = np.zeros((512, 512, 4), dtype=np.uint8)
cv2.circle(img, (256, 256), 200, (200, 50, 50, 255), -1)
pil_img = Image.fromarray(img, 'RGBA')

result = recog.recognize(pil_img)
print('Category:', result['category'], 'confidence:', result['confidence'])
print('Embedding shape:', result['embedding'].shape)

candidates = retrieval.search(result['embedding'], k=5, category_filter=None)
print('Candidates found:', len(candidates))
for c in candidates:
    print('  ', c['name'], 'sim=', c['similarity'], 'cat=', c.get('category'))