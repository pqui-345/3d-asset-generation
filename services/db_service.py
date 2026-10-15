import os
import sqlite3

class DBService:
    def __init__(self):
        self.sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "3dgame.db")
        self._init_db()

    def _init_db(self):
        """Initializes database schema."""
        print(f"[DB] Using SQLite database at: {self.sqlite_path}")
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                original_image TEXT NOT NULL,
                additional_images TEXT DEFAULT '[]',
                no_bg_image TEXT,
                model_glb TEXT,
                model_obj TEXT,
                model_ply TEXT,
                vertices INTEGER DEFAULT 0,
                faces INTEGER DEFAULT 0,
                texture_size TEXT DEFAULT '1024x1024',
                file_size TEXT DEFAULT '0 MB',
                inference_time REAL DEFAULT 0.0,
                style TEXT DEFAULT 'template_retrieval',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            cursor.execute("ALTER TABLE assets ADD COLUMN style TEXT DEFAULT 'template_retrieval'")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE assets ADD COLUMN editor_state TEXT")
        except Exception:
            pass
        conn.commit()
        conn.close()

    def get_connection(self):
        """Returns a connection (SQLite)."""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def query(self, sql, params=None, fetchall=True, fetchone=False):
        """Helper to run queries on SQLite."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # SQLite uses ? instead of %s
        sql = sql.replace("%s", "?")

        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            if fetchone:
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return row
            elif fetchall:
                rows = cursor.fetchall()
                return [dict(r) for r in rows]

            conn.commit()
            # If insert, return lastrowid
            if "INSERT" in sql.upper():
                return cursor.lastrowid
        except Exception as e:
            print(f"[DB Error] Query failed: {e}")
            raise e
        finally:
            conn.close()

    def execute(self, sql, params=None):
        """Helper to execute INSERT, UPDATE, DELETE queries."""
        conn = self.get_connection()
        cursor = conn.cursor()

        sql = sql.replace("%s", "?")

        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()

            # Return lastrowid for INSERT
            if "INSERT" in sql.upper():
                return cursor.lastrowid
            return cursor.rowcount
        except Exception as e:
            print(f"[DB Error] Execution failed: {e}")
            raise e
        finally:
            conn.close()

# Singleton instance
db_service = DBService()
