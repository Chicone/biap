"""
Build a balanced JUMP production compound subset for MOA prediction.

The script selects 30 distinct compounds from each of four MOA classes:

- cyclooxygenase inhibitor
- EGFR inhibitor
- HDAC inhibitor
- PI3K inhibitor

No microscopy images are downloaded yet.

Output:
    data/external/JUMP_moa_BIAP/metadata/
        jump_moa_compounds.csv
"""

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    ROOT
    / "data"
    / "external"
    / "JUMP_moa_BIAP"
    / "metadata"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


DATABASE_URL = (
    "https://imaging-platform.s3.amazonaws.com/"
    "projects/cpg0042-chandrasekaran-jump/"
    "workspace/publication_data/2025_Chandrasekaran/"
    "jump_production_datastore/interim/"
    "jump_metadata_augmented.duckdb"
)


SELECTED_MOAS = [
    "cyclooxygenase inhibitor",
    "EGFR inhibitor",
    "HDAC inhibitor",
    "PI3K inhibitor",
]

COMPOUNDS_PER_MOA = 30


def main():
    conn = duckdb.connect()

    conn.execute("INSTALL httpfs")
    conn.execute("LOAD httpfs")

    print("Connecting to JUMP production metadata...")

    conn.execute(
        f"""
        ATTACH '{DATABASE_URL}'
        AS meta (READ_ONLY)
        """
    )

    for table_name in [
      "compound",
      "compound_source",
      "perturbation",
      "well",
      "plate",
    ]:
      print(f"\n=== {table_name} ===")

      schema = conn.execute(
        f"DESCRIBE meta.{table_name}"
      ).fetchdf()

      print(
        schema[
          ["column_name", "column_type"]
        ].to_string(index=False)
      )

    print("\n=== Tables in JUMP production database ===")

    tables = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = 'meta'
        ORDER BY table_name
    """).fetchdf()

    print(tables.to_string(index=False))

    selected_frames = []

    for moa in SELECTED_MOAS:
        print(f"\nSelecting compounds for: {moa}")

        query = """
        SELECT DISTINCT
            Metadata_JCP2022 AS jump_id,
            Metadata_InChIKey AS inchikey,
            Metadata_SMILES AS smiles,
            Metadata_repurposing_name AS compound_name,
            Metadata_repurposing_target AS repurposing_target,
            Metadata_repurposing_moa AS moa
        FROM meta.compound_metadata
        WHERE ? IN (
            SELECT trim(x)
            FROM UNNEST(
                string_split(
                    Metadata_repurposing_moa,
                    '|'
                )
            ) AS t(x)
        )
          AND Metadata_JCP2022 IS NOT NULL
          AND Metadata_InChIKey IS NOT NULL
        ORDER BY Metadata_InChIKey
        """

        candidates = conn.execute(
            query,
            [moa],
        ).fetchdf()

        print(
            f"Available distinct compounds: "
            f"{len(candidates)}"
        )

        if len(candidates) < COMPOUNDS_PER_MOA:
            raise RuntimeError(
                f"{moa} has only {len(candidates)} "
                f"usable compounds."
            )

        # Fixed random seed makes the subset reproducible.
        selected = candidates.sample(
            n=COMPOUNDS_PER_MOA,
            random_state=42,
        ).copy()

        # Store one clean class label even if the source metadata
        # contains a pipe-delimited list of MOAs.
        selected["selected_moa"] = moa

        selected_frames.append(selected)

    subset = pd.concat(
        selected_frames,
        ignore_index=True,
    )

    # -------------------------------------------------------------
    # Map selected compounds to JUMP production wells
    # -------------------------------------------------------------

    conn.register(
      "selected_compounds",
      subset[
        [
          "jump_id",
          "compound_name",
          "selected_moa",
        ]
      ],
    )

    well_manifest = conn.execute(
      """
      SELECT
          selected.jump_id,
          selected.compound_name,
          selected.selected_moa,

          well.Metadata_Source AS source,
          well.Metadata_Plate AS plate,
          well.Metadata_Well AS well,

          plate.Metadata_Batch AS batch,
          plate.Metadata_PlateType AS plate_type

      FROM selected_compounds AS selected

      JOIN meta.well AS well
        ON well.Metadata_JCP2022 = selected.jump_id

      LEFT JOIN meta.plate AS plate
        ON plate.Metadata_Source = well.Metadata_Source
       AND plate.Metadata_Plate = well.Metadata_Plate

      ORDER BY
          selected.selected_moa,
          selected.jump_id,
          well.Metadata_Source,
          well.Metadata_Plate,
          well.Metadata_Well
      """
    ).fetchdf()

    well_manifest_path = (
      OUTPUT_DIR
      / "jump_moa_wells.csv"
    )

    well_manifest.to_csv(
      well_manifest_path,
      index=False,
    )

    print("\n--------------------------------")
    print("Well mapping")
    print("--------------------------------")

    print(
      f"Selected compounds: "
      f"{subset['jump_id'].nunique()}"
    )

    print(
      f"Compounds found in wells: "
      f"{well_manifest['jump_id'].nunique()}"
    )

    print(
      f"Total matching wells: "
      f"{len(well_manifest)}"
    )

    print(
      f"Sources: "
      f"{well_manifest['source'].nunique()}"
    )

    print(
      f"Plates: "
      f"{well_manifest['plate'].nunique()}"
    )

    print("\nWells per MOA:")
    print(
      well_manifest[
        "selected_moa"
      ].value_counts().to_string()
    )

    print(
      f"\nWell manifest saved to:\n"
      f"{well_manifest_path}"
    )

    # -------------------------------------------------------------
    # Check compound coverage by experimental source
    # -------------------------------------------------------------

    source_moa_coverage = (
      well_manifest
      .groupby(
        [
          "source",
          "selected_moa",
        ]
      )
      ["jump_id"]
      .nunique()
      .unstack(
        fill_value=0
      )
    )

    source_moa_coverage["total_unique_compounds"] = (
      source_moa_coverage.sum(axis=1)
    )

    source_moa_coverage = (
      source_moa_coverage
      .sort_values(
        "total_unique_compounds",
        ascending=False,
      )
    )

    print("\n--------------------------------")
    print("Unique compound coverage by source")
    print("--------------------------------")

    print(
      source_moa_coverage.to_string()
    )

    # -------------------------------------------------------------
    # Build a balanced single-source subset from source_7
    # -------------------------------------------------------------

    SELECTED_SOURCE = "source_7"
    COMPOUNDS_PER_MOA_FINAL = 26

    source_subset = well_manifest[
      well_manifest["source"] == SELECTED_SOURCE
      ].copy()

    # Keep one row per compound first, so compounds that occur in
    # multiple wells do not get overrepresented during selection.
    unique_compounds_in_source = (
      source_subset[
        [
          "jump_id",
          "compound_name",
          "selected_moa",
        ]
      ]
      .drop_duplicates()
    )

    selected_source_compounds = (
      unique_compounds_in_source
      .groupby("selected_moa")
      .sample(
        n=COMPOUNDS_PER_MOA_FINAL,
        random_state=42,
      )
      .reset_index(drop=True)
    )

    print("\n--------------------------------")
    print("Final balanced source subset")
    print("--------------------------------")

    print(
      selected_source_compounds[
        "selected_moa"
      ].value_counts().to_string()
    )

    print(
      f"\nTotal compounds: "
      f"{len(selected_source_compounds)}"
    )

    # Join the selected compounds back to their available wells.
    selected_wells = source_subset.merge(
      selected_source_compounds[
        [
          "jump_id",
          "selected_moa",
        ]
      ],
      on=[
        "jump_id",
        "selected_moa",
      ],
      how="inner",
    )

    # Pick one physical well per compound.
    #
    # Sorting first makes the choice reproducible.
    selected_wells = (
      selected_wells
      .sort_values(
        [
          "jump_id",
          "plate",
          "well",
        ]
      )
      .drop_duplicates(
        subset=["jump_id"],
        keep="first",
      )
      .reset_index(drop=True)
    )

    print(
      f"Selected wells: "
      f"{len(selected_wells)}"
    )

    final_manifest_path = (
      OUTPUT_DIR
      / "jump_moa_source7_manifest.csv"
    )

    selected_wells.to_csv(
      final_manifest_path,
      index=False,
    )

    print(
      f"\nFinal manifest saved to:\n"
      f"{final_manifest_path}"
    )

    # -------------------------------------------------------------
    # Build site-level image manifest
    # -------------------------------------------------------------

    import subprocess

    LOAD_DATA_DIR = (
      ROOT
      / "data"
      / "external"
      / "JUMP_moa_BIAP"
      / "metadata"
      / "load_data"
    )

    LOAD_DATA_DIR.mkdir(
      parents=True,
      exist_ok=True,
    )

    site_rows = []

    # Only download each plate's load_data.csv once.
    unique_plates = (
      selected_wells[
        [
          "source",
          "batch",
          "plate",
        ]
      ]
      .drop_duplicates()
    )

    print("\n--------------------------------")
    print("Building image manifest")
    print("--------------------------------")

    print(
      f"Unique plates required: "
      f"{len(unique_plates)}"
    )

    for _, plate_row in unique_plates.iterrows():

      source = plate_row["source"]
      batch = plate_row["batch"]
      plate = plate_row["plate"]

      local_load_data = (
        LOAD_DATA_DIR
        / f"{plate}_load_data.csv"
      )

      # Download the plate metadata only if we do not
      # already have it locally.
      if not local_load_data.exists():
        s3_path = (
          f"s3://cellpainting-gallery/"
          f"cpg0016-jump/"
          f"{source}/workspace/load_data_csv/"
          f"{batch}/{plate}/load_data.csv"
        )

        print(f"Downloading metadata for {plate}")

        subprocess.run(
          [
            "aws",
            "s3",
            "cp",
            s3_path,
            str(local_load_data),
            "--no-sign-request",
          ],
          check=True,
        )

      load_data = pd.read_csv(
        local_load_data
      )

      # Which of our selected compounds/wells are on this plate?
      selected_plate_wells = selected_wells[
        (selected_wells["source"] == source)
        & (selected_wells["batch"] == batch)
        & (selected_wells["plate"] == plate)
        ].copy()

      # Keep only the imaging rows belonging to those wells.
      plate_sites = load_data[
        load_data["Metadata_Well"].isin(
          selected_plate_wells["well"]
        )
      ].copy()

      # Attach our biological labels.
      plate_sites = plate_sites.merge(
        selected_plate_wells[
          [
            "well",
            "jump_id",
            "compound_name",
            "selected_moa",
          ]
        ],
        left_on="Metadata_Well",
        right_on="well",
        how="inner",
      )

      site_rows.append(
        plate_sites[
          [
            "Metadata_Source",
            "Metadata_Batch",
            "Metadata_Plate",
            "Metadata_Well",
            "Metadata_Site",
            "jump_id",
            "compound_name",
            "selected_moa",
            "URL_OrigDNA",
            "URL_OrigMito",
            "URL_OrigAGP",
            "URL_OrigER",
            "URL_OrigRNA",
          ]
        ]
      )

    image_manifest = pd.concat(
      site_rows,
      ignore_index=True,
    )

    image_manifest_path = (
      OUTPUT_DIR
      / "jump_moa_image_manifest.csv"
    )

    image_manifest.to_csv(
      image_manifest_path,
      index=False,
    )

    print("\n--------------------------------")
    print("Image manifest complete")
    print("--------------------------------")

    print(
      f"Sites: "
      f"{len(image_manifest)}"
    )

    num_physical_wells = (
      image_manifest[
        [
          "Metadata_Source",
          "Metadata_Batch",
          "Metadata_Plate",
          "Metadata_Well",
        ]
      ]
      .drop_duplicates()
      .shape[0]
    )

    print(
      f"Physical wells: "
      f"{num_physical_wells}"
    )

    print(
      f"Compounds: "
      f"{image_manifest['jump_id'].nunique()}"
    )

    print(
      f"MOAs: "
      f"{image_manifest['selected_moa'].nunique()}"
    )

    print(
      f"Expected TIFFs: "
      f"{len(image_manifest) * 5}"
    )

    print(
      f"\nSaved to:\n"
      f"{image_manifest_path}"
    )

    # -------------------------------------------------------------
    # Download microscopy images for the final MOA subset
    # -------------------------------------------------------------

    IMAGE_DIR = (
      ROOT
      / "data"
      / "external"
      / "JUMP_moa_BIAP"
      / "images"
    )

    IMAGE_DIR.mkdir(
      parents=True,
      exist_ok=True,
    )

    channel_columns = {
      "DNA": "URL_OrigDNA",
      "Mito": "URL_OrigMito",
      "AGP": "URL_OrigAGP",
      "ER": "URL_OrigER",
      "RNA": "URL_OrigRNA",
    }

    downloaded = 0
    skipped = 0

    print("\n--------------------------------")
    print("Downloading microscopy images")
    print("--------------------------------")

    for _, row in image_manifest.iterrows():

      plate = row["Metadata_Plate"]
      well = row["Metadata_Well"]
      site = int(row["Metadata_Site"])

      for channel_name, url_column in channel_columns.items():

        source_url = row[url_column]

        if pd.isna(source_url) or source_url == "":
          continue

        filename = (
          f"{plate}_{well}_s{site}_{channel_name}.tif"
        )

        destination = (
          IMAGE_DIR
          / filename
        )

        # Resumable:
        # if the file is already present, don't download it again.
        if destination.exists():
          skipped += 1
          continue

        subprocess.run(
          [
            "aws",
            "s3",
            "cp",
            source_url,
            str(destination),
            "--no-sign-request",
          ],
          check=True,
        )

        downloaded += 1

    print("\n--------------------------------")
    print("Image download complete")
    print("--------------------------------")

    print(
      f"Downloaded new TIFFs: {downloaded}"
    )

    print(
      f"Already existing TIFFs skipped: {skipped}"
    )

    print(
      f"Images stored in:\n{IMAGE_DIR}"
    )

if __name__ == "__main__":
    main()