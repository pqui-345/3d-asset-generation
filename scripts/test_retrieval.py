import os, sys
os.chdir('E:\\xampp\\htdocs\\3DGame')
sys.path.append('.')
from services.template_database import TemplateDatabase
import numpy as np

db = TemplateDatabase('data/template_metadata.sqlite')

# Test get_template_by_index for a few indices
for idx in [0, 1, 5, 10, 50, 99]:
    t = db.get_template_by_index(idx)
    if t:
        print('idx={}: {} (uid={}...)'.format(idx, t['name'], t['uid'][:12]))
    else:
        print('idx={}: NOT FOUND'.format(idx))

# Test the retrieval service directly
from services.retrieval_service import RetrievalService
ret = RetrievalService('data/template_index.faiss', db)

# Test with a query from the index itself (should match perfectly)
t0 = db.get_template_by_index(0)
emb = t0['clip_embedding']
print('\nSearching with template 0 embedding...')
results = ret.search(emb, k=5)
print('Results:', len(results))
for r in results:
    print('  {} sim={:.4f}'.format(r['name'], r['similarity']))