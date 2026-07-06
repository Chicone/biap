import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "biap.sqlite"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(conn, table_name: str, column_name: str, column_sql: str):
  columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
  existing_columns = [column["name"] for column in columns]

  if column_name not in existing_columns:
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dataset_type TEXT NOT NULL,
                description TEXT,
                image_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Imported'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                modality TEXT,
                status TEXT DEFAULT 'Imported',
                url TEXT,
                FOREIGN KEY(dataset_id) REFERENCES datasets(id)
            )
        """)

        add_column_if_missing(
          conn,
          "images",
          "ground_truth_dir",
          "ground_truth_dir TEXT",
        )