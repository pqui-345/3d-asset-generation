import sqlite3
import numpy as np
import os

class TemplateDatabase:
    """
    SQLite-based metadata store for 3D templates.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    uid TEXT PRIMARY KEY,
                    faiss_idx INTEGER,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    glb_path TEXT NOT NULL,
                    obj_path TEXT,
                    mtl_path TEXT,
                    texture_path TEXT,
                    vertices INTEGER NOT NULL,
                    faces INTEGER NOT NULL,
                    bounds_min_x REAL, bounds_min_y REAL, bounds_min_z REAL,
                    bounds_max_x REAL, bounds_max_y REAL, bounds_max_z REAL,
                    license TEXT DEFAULT 'CC-BY-4.0',
                    source_url TEXT,
                    tags TEXT,
                    clip_embedding BLOB,
                    quality_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON templates(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_faiss ON templates(faiss_idx)")
            conn.commit()


    def add_template(self, metadata):
        """
        Adds or updates a template in the database.
        metadata: dict containing template info.
        """
        with sqlite3.connect(self.db_path) as conn:
            sql = """
                INSERT OR REPLACE INTO templates 
                (uid, name, category, subcategory, glb_path, obj_path, mtl_path, texture_path, 
                 vertices, faces, bounds_min_x, bounds_min_y, bounds_min_z, 
                 bounds_max_x, bounds_max_y, bounds_max_z, license, source_url, tags, 
                 clip_embedding, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                metadata['uid'], metadata['name'], metadata['category'], metadata.get('subcategory'),
                metadata['glb_path'], metadata.get('obj_path'), metadata.get('mtl_path'), metadata.get('texture_path'),
                metadata['vertices'], metadata['faces'],
                metadata['bounds'][0], metadata['bounds'][1], metadata['bounds'][2],
                metadata['bounds'][3], metadata['bounds'][4], metadata['bounds'][5],
                metadata.get('license', 'CC-BY-4.0'), metadata.get('source_url'), 
                metadata.get('tags', '[]'),
                metadata['clip_embedding'].tobytes(),
                metadata.get('quality_score', 1.0)
            )
            conn.execute(sql, params)
            conn.commit()

    def get_template(self, uid):
        """Fetches template metadata by UID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            res = conn.execute("SELECT * FROM templates WHERE uid = ?", (uid,)).fetchone()
            if res:
                d = dict(res)
                d['clip_embedding'] = np.frombuffer(d['clip_embedding'], dtype=np.float32)
                d['bounds'] = [d['bounds_min_x'], d['bounds_min_y'], d['bounds_min_z'], 
                               d['bounds_max_x'], d['bounds_max_y'], d['bounds_max_z']]
                return d
            return None

    def get_template_by_index(self, faiss_idx):
        """Fetches template metadata by FAISS index."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            res = conn.execute("SELECT * FROM templates WHERE faiss_idx = ?", (faiss_idx,)).fetchone()
            if res:
                d = dict(res)
                d['clip_embedding'] = np.frombuffer(d['clip_embedding'], dtype=np.float32)
                d['bounds'] = [d['bounds_min_x'], d['bounds_min_y'], d['bounds_min_z'], 
                               d['bounds_max_x'], d['bounds_max_y'], d['bounds_max_z']]
                return d
            return None

    def list_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            results = []
            for r in conn.execute("SELECT * FROM templates").fetchall():
                d = dict(r)
                if d.get('clip_embedding'):
                    d['clip_embedding'] = np.frombuffer(d['clip_embedding'], dtype=np.float32)
                d['bounds'] = [d.get('bounds_min_x', 0), d.get('bounds_min_y', 0), d.get('bounds_min_z', 0),
                               d.get('bounds_max_x', 0), d.get('bounds_max_y', 0), d.get('bounds_max_z', 0)]
                results.append(d)
            return results

    def get_template_count(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
