import csv
import json
from pathlib import Path


class AntibodyImporter:
    """
    Import an antibody dataset into BIAP.

    One antibody_samples row represents one antibody.

    Expected CSV columns for the first implementation:

        sample_name
        heavy_chain_sequence
        light_chain_sequence

    Additional metadata and experimental targets can be
    stored as JSON once dataset-specific column mappings
    are defined.
    """

    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)

    def import_to_database(
        self,
        dataset_id: int,
        data_root: Path,
        conn,
    ):
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Antibody dataset not found: {self.csv_path}"
            )

        imported_samples = 0
        skipped_samples = 0

        with self.csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            required_columns = {
                "sample_name",
                "heavy_chain_sequence",
                "light_chain_sequence",
            }

            missing_columns = (
                required_columns
                - set(reader.fieldnames or [])
            )

            if missing_columns:
                raise ValueError(
                    "Missing required antibody columns: "
                    + ", ".join(sorted(missing_columns))
                )

            for row in reader:
                sample_name = (
                    row["sample_name"].strip()
                )

                if not sample_name:
                    continue

                existing = conn.execute(
                    """
                    SELECT id
                    FROM antibody_samples
                    WHERE dataset_id = ?
                      AND sample_name = ?
                    """,
                    (
                        dataset_id,
                        sample_name,
                    ),
                ).fetchone()

                if existing is not None:
                    skipped_samples += 1
                    continue

                heavy_chain = (
                    row["heavy_chain_sequence"].strip()
                    or None
                )

                light_chain = (
                    row["light_chain_sequence"].strip()
                    or None
                )

                conn.execute(
                    """
                    INSERT INTO antibody_samples
                    (
                        dataset_id,
                        sample_name,
                        heavy_chain_sequence,
                        light_chain_sequence,
                        metadata_json,
                        targets_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_id,
                        sample_name,
                        heavy_chain,
                        light_chain,
                        json.dumps({}),
                        json.dumps({}),
                    ),
                )

                imported_samples += 1

        return {
            "dataset_id": dataset_id,
            "imported_samples": imported_samples,
            "skipped_samples": skipped_samples,
        }