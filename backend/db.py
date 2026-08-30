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
              CREATE TABLE IF NOT EXISTS experiments (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  domain TEXT NOT NULL,
                  description TEXT,
                  status TEXT DEFAULT 'Draft',
                  updated TEXT DEFAULT CURRENT_TIMESTAMP
              )
          """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dataset_type TEXT NOT NULL DEFAULT 'image',
                description TEXT,
                image_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Imported'
            )
        """)

        add_column_if_missing(
          conn,
          "datasets",
          "experiment_id",
          "experiment_id INTEGER",
        )

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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS image_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                url TEXT NOT NULL,
                channel_order INTEGER,
                FOREIGN KEY(image_id) REFERENCES images(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS antibody_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                sample_name TEXT NOT NULL,
                heavy_chain_sequence TEXT,
                light_chain_sequence TEXT,
                metadata_json TEXT,
                targets_json TEXT,
                FOREIGN KEY(dataset_id) REFERENCES datasets(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS feature_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                configuration_json TEXT NOT NULL,
                feature_names_json TEXT NOT NULL,
                num_rows INTEGER NOT NULL DEFAULT 0,
                num_features INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dataset_id) REFERENCES datasets(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS feature_set_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_set_id INTEGER NOT NULL,
                image_id INTEGER NOT NULL,
                object_label INTEGER,
                features_json TEXT NOT NULL,
                FOREIGN KEY(feature_set_id) REFERENCES feature_sets(id),
                FOREIGN KEY(image_id) REFERENCES images(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS ml_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                feature_set_id INTEGER NOT NULL,

                target TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                cv_strategy TEXT NOT NULL,
                cv_folds INTEGER NOT NULL,
                random_seed INTEGER NOT NULL,

                num_samples INTEGER NOT NULL,
                num_features INTEGER NOT NULL,
                num_classes INTEGER NOT NULL,

                accuracy REAL NOT NULL,
                macro_f1 REAL,
                weighted_f1 REAL,

                result_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(dataset_id) REFERENCES datasets(id),
                FOREIGN KEY(feature_set_id) REFERENCES feature_sets(id)
            )
        """)

        add_column_if_missing(
          conn,
          "images",
          "ground_truth_dir",
          "ground_truth_dir TEXT",
        )

        add_column_if_missing(conn, "images", "plate", "plate TEXT")
        add_column_if_missing(conn, "images", "well", "well TEXT")
        add_column_if_missing(conn, "images", "replicate", "replicate INTEGER")

        add_column_if_missing(conn, "images", "compound", "compound TEXT")
        add_column_if_missing(conn, "images", "concentration", "concentration REAL")
        add_column_if_missing(conn, "images", "moa", "moa TEXT")
        add_column_if_missing(conn, "images", "smiles", "smiles TEXT")
        add_column_if_missing(conn, "images", "site", "site INTEGER")
        add_column_if_missing(conn, "images", "target", "target TEXT")
        add_column_if_missing(conn, "images", "broad_sample", "broad_sample TEXT")
