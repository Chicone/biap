from pathlib import Path
import shutil
import pandas as pd
from PIL import Image


class BBBC021Importer:
    CHANNELS = {
        "dapi": "DAPI",
        "tubulin": "Tubulin",
        "actin": "Actin",
    }

    def __init__(self, dataset_folder):
        self.dataset_folder = Path(dataset_folder)

    def validate(self):
        required_files = [
            "BBBC021_v1_image.csv",
            "BBBC021_v1_compound.csv",
            "BBBC021_v1_moa.csv",
        ]

        for filename in required_files:
            if not (self.dataset_folder / filename).exists():
                raise FileNotFoundError(f"{filename} not found.")

    def load_metadata(self):
        images = pd.read_csv(self.dataset_folder / "BBBC021_v1_image.csv")
        compounds = pd.read_csv(self.dataset_folder / "BBBC021_v1_compound.csv")
        moa = pd.read_csv(self.dataset_folder / "BBBC021_v1_moa.csv")

        return images, compounds, moa

    def _first_existing_column(self, dataframe, candidates):
        for column in candidates:
            if column in dataframe.columns:
                return column

        return None

    def _clean_value(self, value):
        if pd.isna(value):
            return None

        return str(value)

    def _resolve_image_path(self, pathname, filename):
        filename = self._clean_value(filename)

        if not filename:
            return None

        pathname = self._clean_value(pathname)

        candidates = []

        if pathname:
            candidates.extend(
                [
                    self.dataset_folder / pathname / filename,
                    self.dataset_folder / "images" / pathname / filename,
                    self.dataset_folder / pathname.replace("\\", "/") / filename,
                ]
            )

        candidates.extend(
            [
                self.dataset_folder / filename,
                self.dataset_folder / "images" / filename,
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return candidate

        matches = list(self.dataset_folder.rglob(filename))

        if matches:
            return matches[0]

        return None

    def build_metadata_table(self):
        self.validate()

        images, compounds, moa = self.load_metadata()

        images = images.copy()
        compounds = compounds.copy()
        moa = moa.copy()

        compound_column = self._first_existing_column(
            images,
            [
                "Image_Metadata_Compound",
                "Metadata_Compound",
            ],
        )

        concentration_column = self._first_existing_column(
            images,
            [
                "Image_Metadata_Concentration",
                "Metadata_Concentration",
            ],
        )

        if compound_column is None:
            raise ValueError("Compound column not found in BBBC021 image metadata.")

        if concentration_column is None:
            raise ValueError("Concentration column not found in BBBC021 image metadata.")

        images[compound_column] = images[compound_column].astype(str)
        images[concentration_column] = images[concentration_column].astype(float)

        compounds["compound"] = compounds["compound"].astype(str)
        moa["compound"] = moa["compound"].astype(str)
        moa["concentration"] = moa["concentration"].astype(float)

        metadata = images.merge(
            compounds,
            left_on=compound_column,
            right_on="compound",
            how="left",
        )

        moa = moa.rename(
            columns={
                "compound": "moa_compound",
                "concentration": "moa_concentration",
            }
        )

        metadata = metadata.merge(
            moa,
            left_on=[
                compound_column,
                concentration_column,
            ],
            right_on=[
                "moa_compound",
                "moa_concentration",
            ],
            how="left",
        )

        return metadata

    def _extract_record(self, row):
        plate_column = self._first_existing_column(
            row.to_frame().T,
            [
                "Image_Metadata_Plate",
                "Metadata_Plate",
                "Image_Metadata_Plate_DAPI",
            ],
        )

        well_column = self._first_existing_column(
            row.to_frame().T,
            [
                "Image_Metadata_Well",
                "Metadata_Well",
            ],
        )

        replicate_column = self._first_existing_column(
            row.to_frame().T,
            [
                "Image_Metadata_Replicate",
                "Metadata_Replicate",
                "Image_Metadata_Site",
                "Metadata_Site",
            ],
        )

        compound_column = self._first_existing_column(
            row.to_frame().T,
            [
                "Image_Metadata_Compound",
                "Metadata_Compound",
            ],
        )

        concentration_column = self._first_existing_column(
            row.to_frame().T,
            [
                "Image_Metadata_Concentration",
                "Metadata_Concentration",
            ],
        )

        smiles_column = self._first_existing_column(
            row.to_frame().T,
            [
                "smiles",
                "SMILES",
            ],
        )

        return {
            "plate": self._clean_value(row.get(plate_column)) if plate_column else None,
            "well": self._clean_value(row.get(well_column)) if well_column else None,
            "replicate": int(row.get(replicate_column)) if replicate_column and not pd.isna(row.get(replicate_column)) else None,
            "compound": self._clean_value(row.get(compound_column)) if compound_column else None,
            "concentration": float(row.get(concentration_column)) if concentration_column and not pd.isna(row.get(concentration_column)) else None,
            "moa": self._clean_value(row.get("moa")),
            "smiles": self._clean_value(row.get(smiles_column)) if smiles_column else None,
        }

    def _copy_channel(self, row, channel_key, dataset_dir):
        channel_name = self.CHANNELS[channel_key]

        filename_column = self._first_existing_column(
            row.to_frame().T,
            [
                f"Image_FileName_{channel_name}",
                f"FileName_{channel_name}",
            ],
        )

        pathname_column = self._first_existing_column(
            row.to_frame().T,
            [
                f"Image_PathName_{channel_name}",
                f"PathName_{channel_name}",
            ],
        )

        if filename_column is None:
            raise ValueError(f"{channel_name} filename column not found.")

        source_filename = self._clean_value(row.get(filename_column))
        source_pathname = self._clean_value(row.get(pathname_column)) if pathname_column else None

        source_image = self._resolve_image_path(source_pathname, source_filename)

        if source_image is None:
            raise FileNotFoundError(f"Image file not found: {source_filename}")

        plate = (
            self._clean_value(row.get("Image_Metadata_Plate_DAPI"))
            or self._clean_value(row.get("Image_Metadata_Plate"))
            or self._clean_value(row.get("Metadata_Plate"))
            or "unknown_plate"
        )
        destination_dir = dataset_dir / "bbbc021" / plate
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / source_image.name
        shutil.copy2(source_image, destination)

        relative_path = destination.relative_to(dataset_dir.parent)

        return {
            "filename": str(relative_path),
            "url": f"/data/raw/{relative_path}",
            "path": destination,
        }

    def import_to_database(self, dataset_id, data_root, conn, max_images=None):
        metadata = self.build_metadata_table()

        dataset_dir = Path(data_root) / f"dataset_{dataset_id}"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        imported = 0
        skipped = 0
        missing_files = []

        for _, row in metadata.iterrows():
            if max_images is not None and imported >= max_images:
                break

            try:
                dapi = self._copy_channel(row, "dapi", dataset_dir)
                tubulin = self._copy_channel(row, "tubulin", dataset_dir)
                actin = self._copy_channel(row, "actin", dataset_dir)

                with Image.open(dapi["path"]) as img:
                    width, height = img.size

                record = self._extract_record(row)

                cursor = conn.execute(
                    """
                    INSERT INTO images
                    (
                        dataset_id,
                        filename,
                        width,
                        height,
                        modality,
                        status,
                        url,                    
                        plate,
                        well,
                        replicate,
                        compound,
                        concentration,
                        moa,
                        smiles
                    )
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)                    """,
                    (
                        dataset_id,
                        dapi["filename"],
                        width,
                        height,
                        "BBBC021 multi-channel microscopy",
                        "Imported",
                        dapi["url"],
                        record["plate"],
                        record["well"],
                        record["replicate"],
                        record["compound"],
                        record["concentration"],
                        record["moa"],
                        record["smiles"],
                    ),
                )

                image_id = cursor.lastrowid

                channel_records = [
                    ("DAPI", dapi, 1),
                    ("Tubulin", tubulin, 2),
                    ("Actin", actin, 3),
                ]

                for channel_name, channel_data, channel_order in channel_records:
                    conn.execute(
                        """
                        INSERT INTO image_channels
                        (
                            image_id,
                            channel_name,
                            filename,
                            url,
                            channel_order
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            image_id,
                            channel_name,
                            channel_data["filename"],
                            channel_data["url"],
                            channel_order,
                        ),
                    )

                imported += 1

            except FileNotFoundError as error:
              skipped += 1

              if len(missing_files) < 10:
                missing_files.append(str(error))

              continue

        conn.execute(
            """
            UPDATE datasets
            SET image_count = ?
            WHERE id = ?
            """,
            (
                imported,
                dataset_id,
            ),
        )

        return {
          "dataset_id": dataset_id,
          "imported": imported,
          "unavailable_metadata_rows_scanned": skipped,
          "metadata_rows": len(metadata),
          "moa_classes": int(metadata["moa"].nunique()),
          "missing_files_sample": missing_files,
          "status": "Imported",
        }

    def import_dataset(self):
        metadata = self.build_metadata_table()

        return {
            "metadata": metadata,
            "num_images": len(metadata),
            "num_compounds": metadata["Image_Metadata_Compound"].nunique()
            if "Image_Metadata_Compound" in metadata.columns
            else metadata["Metadata_Compound"].nunique(),
            "num_moa": metadata["moa"].nunique(),
        }