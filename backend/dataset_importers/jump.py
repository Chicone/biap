import csv
import shutil
from pathlib import Path

from PIL import Image


class JUMPImporter:
    """
    Import a prepared JUMP Cell Painting subset into BIAP.

    One BIAP image record represents one microscopy SITE.

    Each site has five associated image_channels:
      DNA
      Mito
      AGP
      ER
      RNA

    Expected source structure:

    JUMP_pilot_BIAP/
        metadata/
            jump_biap_subset_manifest.csv

        images/
            BR00116991_A01_s1_DNA.tif
            BR00116991_A01_s1_Mito.tif
            ...
    """

    CHANNELS = [
        "DNA",
        "Mito",
        "AGP",
        "ER",
        "RNA",
    ]

    def __init__(self, source_folder: Path):
        self.source_folder = Path(source_folder)

        metadata_dir = self.source_folder / "metadata"

        pilot_manifest = metadata_dir / "jump_biap_subset_manifest.csv"
        moa_manifest = metadata_dir / "jump_moa_image_manifest.csv"

        if pilot_manifest.exists():
          self.manifest_path = pilot_manifest
        elif moa_manifest.exists():
          self.manifest_path = moa_manifest
        else:
          self.manifest_path = pilot_manifest
        self.images_folder = (
            self.source_folder
            / "images"
        )

    def import_to_database(
        self,
        dataset_id: int,
        data_root: Path,
        conn,
    ):
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"JUMP manifest not found: {self.manifest_path}"
            )

        if not self.images_folder.exists():
            raise FileNotFoundError(
                f"JUMP image folder not found: {self.images_folder}"
            )

        dataset_dir = data_root / f"dataset_{dataset_id}"
        dataset_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        imported_sites = 0
        skipped_sites = 0
        imported_channels = 0

        with self.manifest_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                plate = row["Metadata_Plate"]
                well = row["Metadata_Well"]
                site = int(row["Metadata_Site"])

                compound = row.get("pert_iname") or row.get("compound_name")
                target = row.get("target") or row.get("selected_moa")
                broad_sample = row.get("broad_sample") or row.get("jump_id")

                # Do not import the same site twice.
                existing = conn.execute(
                    """
                    SELECT id
                    FROM images
                    WHERE dataset_id = ?
                    AND plate = ?
                    AND well = ?
                    AND site = ?
                    """,
                    (
                        dataset_id,
                        plate,
                        well,
                        site,
                    ),
                ).fetchone()

                if existing is not None:
                    skipped_sites += 1
                    continue

                site_dir = (
                    dataset_dir
                    / plate
                    / well
                    / f"site_{site}"
                )

                site_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                channel_records = []

                for channel_order, channel_name in enumerate(
                    self.CHANNELS,
                    start=1,
                ):
                    source_filename = (
                        f"{plate}_{well}_s{site}_{channel_name}.tif"
                    )

                    source_path = (
                        self.images_folder
                        / source_filename
                    )

                    if not source_path.exists():
                        raise FileNotFoundError(
                            f"Missing JUMP image: {source_path}"
                        )

                    destination_path = (
                        site_dir
                        / source_filename
                    )

                    shutil.copy2(
                        source_path,
                        destination_path,
                    )

                    relative_path = (
                        destination_path
                        .relative_to(data_root)
                        .as_posix()
                    )

                    url = (
                        f"/data/raw/{relative_path}"
                    )

                    channel_records.append(
                        {
                            "channel_name": channel_name,
                            "filename": relative_path,
                            "url": url,
                            "channel_order": channel_order,
                        }
                    )

                # DNA becomes the default image displayed when
                # no explicit channel has been selected.
                default_channel = channel_records[0]

                default_path = (
                    data_root
                    / default_channel["filename"]
                )

                with Image.open(default_path) as image:
                    width, height = image.size

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
                        site,
                        compound,
                        target,
                        broad_sample
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_id,
                        default_channel["filename"],
                        width,
                        height,
                        "Cell Painting",
                        "Imported",
                        default_channel["url"],
                        plate,
                        well,
                        site,
                        compound,
                        target,
                        broad_sample,
                    ),
                )

                image_id = cursor.lastrowid

                for channel in channel_records:
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
                            channel["channel_name"],
                            channel["filename"],
                            channel["url"],
                            channel["channel_order"],
                        ),
                    )

                    imported_channels += 1

                imported_sites += 1

        conn.execute(
            """
            UPDATE datasets
            SET image_count = (
                SELECT COUNT(*)
                FROM images
                WHERE dataset_id = ?
            )
            WHERE id = ?
            """,
            (
                dataset_id,
                dataset_id,
            ),
        )

        return {
            "dataset_id": dataset_id,
            "imported_sites": imported_sites,
            "skipped_sites": skipped_sites,
            "imported_channels": imported_channels,
        }