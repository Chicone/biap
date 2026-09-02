import csv
import json
from pathlib import Path

import pandas as pd


class AntibodyImporter:
    """
    Import antibody datasets into BIAP.

    Supported formats:
      - Generic BIAP antibody CSV
      - Ginkgo GDPa1 Excel workbook
    """

    GDP_TARGET_COLUMNS = {
        "HIC": "hic_rt_avg",
        "Tm2": "tm2_nanodsf_avg",
        "AC-SINS": "acsins_dLmax_ph7.4_avg",
        "CHO": "polyreactivity_prscore_cho_avg",
        "Titer": "normalized_titer_productionbatch1_avg",
    }

    def __init__(self, dataset_path: Path):
        self.dataset_path = Path(dataset_path)

    def import_to_database(
        self,
        dataset_id: int,
        data_root: Path,
        conn,
    ):
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Antibody dataset not found: {self.dataset_path}"
            )

        suffix = self.dataset_path.suffix.lower()

        if suffix in {".xlsx", ".xls"}:
            return self._import_gdpa1(
                dataset_id=dataset_id,
                conn=conn,
            )

        if suffix == ".csv":
            return self._import_csv(
                dataset_id=dataset_id,
                conn=conn,
            )

        raise ValueError(
            f"Unsupported antibody dataset format: {suffix}"
        )

    def _import_gdpa1(
        self,
        dataset_id: int,
        conn,
    ):
        sequences = pd.read_excel(
            self.dataset_path,
            sheet_name="Sequences",
        )

        assays = pd.read_excel(
            self.dataset_path,
            sheet_name="Assay Data - average",
        )

        merged = sequences.merge(
            assays[
                [
                    "antibody_id",
                    *self.GDP_TARGET_COLUMNS.values(),
                ]
            ],
            on="antibody_id",
            how="left",
        )

        imported_samples = 0
        skipped_samples = 0

        for _, row in merged.iterrows():
            antibody_id = str(row["antibody_id"]).strip()

            if not antibody_id:
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
                    antibody_id,
                ),
            ).fetchone()

            if existing is not None:
                skipped_samples += 1
                continue

            heavy_chain = self._clean_value(
                row.get("vh_protein_sequence")
            )

            light_chain = self._clean_value(
                row.get("vl_protein_sequence")
            )

            metadata = {
                "antibody_name": self._clean_value(
                    row.get("antibody_name")
                ),
                "hc_subtype": self._clean_value(
                    row.get("hc_subtype")
                ),
                "lc_subtype": self._clean_value(
                    row.get("lc_subtype")
                ),
                "target": self._clean_value(
                    row.get("target")
                ),
            }

            metadata = {
                key: value
                for key, value in metadata.items()
                if value is not None
            }

            targets = {}

            for target_name, column_name in (
                self.GDP_TARGET_COLUMNS.items()
            ):
                value = row.get(column_name)

                if pd.isna(value):
                    continue

                targets[target_name] = float(value)

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
                    antibody_id,
                    heavy_chain,
                    light_chain,
                    json.dumps(metadata),
                    json.dumps(targets),
                ),
            )

            imported_samples += 1

        return {
            "dataset_id": dataset_id,
            "imported_samples": imported_samples,
            "skipped_samples": skipped_samples,
        }

    def _import_csv(
        self,
        dataset_id: int,
        conn,
    ):
        imported_samples = 0
        skipped_samples = 0

        with self.dataset_path.open(
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
                sample_name = row["sample_name"].strip()

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

    @staticmethod
    def _clean_value(value):
        if pd.isna(value):
            return None

        value = str(value).strip()

        return value or None