import faiss
import numpy as np
import os
import json
from collections import defaultdict

class RetrievalService:
    """
    FAISS-based template retrieval using CLIP image embeddings.
    Unified index: first 100 indices are core_100 text embeddings (faiss_idx mapping),
    remaining indices map via metadata file.
    """
    def __init__(self, index_path, metadata_db):
        self.index_path = index_path
        self.metadata_db = metadata_db
        self.index = None
        self.metadata = []
        self.core_count = self.metadata_db.get_template_count()  # first N indices are text embeddings (no metadata entry)
        self._load_index()
        self._load_metadata()

    def _load_index(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = None

    def _load_metadata(self):
        meta_file = self.index_path.replace('.faiss', '_metadata.json')
        if os.path.exists(meta_file):
            with open(meta_file, 'r') as f:
                self.metadata = json.load(f)

    def build_index(self, templates):
        embeddings = np.array([t['clip_embedding'] for t in templates]).astype('float32')
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)
        faiss.write_index(self.index, self.index_path)
        return True

    def search(self, query_embedding, k=5, category_filter=None):
        if self.index is None:
            return []

        q = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(q)

        distances, indices = self.index.search(q, k * 10)

        uid_scores = defaultdict(list)
        uid_views = defaultdict(list)

        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            idx = int(idx)
            similarity = float(1.0 - dist / 2.0)

            if idx < self.core_count:
                # Core text embedding - look up by faiss_idx in DB
                template = self.metadata_db.get_template_by_index(idx)
                if template:
                    uid_scores[template['uid']].append(similarity)
                    uid_views[template['uid']].append('text')
            else:
                # Has metadata entry
                meta_idx = idx - self.core_count
                if meta_idx < len(self.metadata):
                    entry = self.metadata[meta_idx]
                    uid = entry[0]
                    view_name = entry[1]
                    uid_scores[uid].append(similarity)
                    uid_views[uid].append(view_name)

        if not uid_scores:
            return []

        scored = []
        for uid, scores in uid_scores.items():
            best_score = max(scores)
            if category_filter:
                template = self.metadata_db.get_template(uid)
                if template and template['category'] != category_filter:
                    continue
            scored.append((best_score, uid))

        scored.sort(key=lambda x: -x[0])

        results = []
        for score, uid in scored[:k]:
            template = self.metadata_db.get_template(uid)
            if template:
                template['similarity'] = score
                template['best_view'] = uid_views[uid][uid_scores[uid].index(max(uid_scores[uid]))]
                results.append(template)

        return results
