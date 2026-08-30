"""
Prepare and inspect metadata for a small JUMP Cell Painting subset.

This script combines three different layers of JUMP metadata:

1. load_data_BR00116991.csv
   Tells us which plate/well/site each microscopy image belongs to
   and contains the S3 URLs for the different imaging channels.

2. JUMP-Target-1_compound_platemap.txt
   Maps each physical well (A01, A02, ...) to a Broad compound ID.

3. JUMP-Target-1_compound_metadata_targets.tsv
   Converts the Broad compound ID into biologically meaningful
   information such as compound name and molecular targets.

The goal is NOT to download images yet.

First, we identify target families represented by multiple compounds.
Those will be useful for constructing a small, biologically meaningful
Cell Painting experiment for BIAP.
"""

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

# __file__ is scripts/prepare_jump_subset.py.
# parents[1] therefore points to the BIAP project root.
ROOT = Path(__file__).resolve().parents[1]

METADATA_DIR = (
    ROOT
    / "data"
    / "external"
    / "JUMP_pilot_BIAP"
    / "metadata"
)

# Image-level metadata for plate BR00116991.
#
# There are 384 wells and 9 imaging sites per well:
#
#     384 × 9 = 3456 rows
#
# Each row also contains the S3 URLs for the DNA, Mito, AGP,
# ER and RNA images belonging to that site.
LOAD_DATA_PATH = (
    METADATA_DIR
    / "load_data_BR00116991.csv"
)

# Maps:
#
#     well_position -> broad_sample
#
# Example:
#
#     A01 -> BRD-A86665761-001-01-1
PLATEMAP_PATH = (
    METADATA_DIR
    / "JUMP-Target-1_compound_platemap.txt"
)

# Maps Broad compound IDs to biological annotations:
#
#     broad_sample
#         -> compound name
#         -> target
#         -> target list
#         -> perturbation type
COMPOUND_METADATA_PATH = (
    METADATA_DIR
    / "JUMP-Target-1_compound_metadata_targets.tsv"
)


def main():

    # -------------------------------------------------------------
    # 1. Load the three metadata sources
    # -------------------------------------------------------------

    load_data = pd.read_csv(LOAD_DATA_PATH)

    platemap = pd.read_csv(
        PLATEMAP_PATH,
        sep="\t",
    )

    compounds = pd.read_csv(
        COMPOUND_METADATA_PATH,
        sep="\t",
    )

    print(f"Image/site rows: {len(load_data)}")
    print(f"Platemap wells:   {len(platemap)}")
    print(f"Compounds:        {len(compounds)}")

    # -------------------------------------------------------------
    # 2. Build one row per WELL
    # -------------------------------------------------------------
    #
    # load_data contains one row per imaging SITE.
    #
    # Therefore the same well appears nine times:
    #
    #     A01 site 1
    #     A01 site 2
    #     ...
    #     A01 site 9
    #
    # At this stage we only want to understand the biological
    # conditions, so collapse this to one row per well.

    wells = (
        load_data[
            [
                "Metadata_Plate",
                "Metadata_Well",
            ]
        ]
        .drop_duplicates()
        .rename(
            columns={
                "Metadata_Plate": "plate",
                "Metadata_Well": "well_position",
            }
        )
    )

    # -------------------------------------------------------------
    # 3. Add the Broad compound ID
    # -------------------------------------------------------------
    #
    # We now join using well_position:
    #
    #     A01
    #       ↓
    #     BRD-A86665761-001-01-1

    wells = wells.merge(
        platemap[
            [
                "well_position",
                "broad_sample",
                "solvent",
            ]
        ],
        on="well_position",
        how="left",
    )

    # -------------------------------------------------------------
    # 4. Add biological compound annotations
    # -------------------------------------------------------------
    #
    # Now join using broad_sample:
    #
    #     BRD-A86665761-001-01-1
    #              ↓
    #     gabapentin-enacarbil
    #              ↓
    #     CACNB4 / calcium-channel targets

    wells = wells.merge(
        compounds[
            [
                "broad_sample",
                "pert_iname",
                "target",
                "target_list",
                "pert_type",
                "control_type",
            ]
        ],
        on="broad_sample",
        how="left",
    )

    # At this point each row describes the biological condition
    # associated with one physical well.

    print("\nJoined wells:")
    print(
        wells.head(20).to_string(index=False)
    )

    # -------------------------------------------------------------
    # 5. Count how well each target is represented
    # -------------------------------------------------------------
    #
    # We are particularly interested in targets hit by MULTIPLE
    # different compounds.
    #
    # Example:
    #
    #     NTRK1
    #       ├── LOXO-101
    #       └── GNF-5837
    #
    # This allows us to ask whether two chemically different
    # perturbations of related biology produce similar cellular
    # phenotypes.

    target_counts = (
        wells
        .dropna(subset=["target"])
        .groupby("target")
        .agg(
            # Number of wells associated with this target.
            wells=("well_position", "count"),

            # Number of different compounds associated with it.
            compounds=("pert_iname", "nunique"),
        )
        .sort_values(
            ["compounds", "wells"],
            ascending=False,
        )
    )

    print("\nTarget counts:")
    print(
        target_counts.head(30).to_string()
    )

    # -------------------------------------------------------------
    # 6. Find candidate target families for our BIAP subset
    # -------------------------------------------------------------
    #
    # Require at least two different compounds for the same target.
    # These are much more interesting than targets represented by
    # only one compound.

    repeated_targets = target_counts[
        target_counts["compounds"] >= 2
    ]

    print(
        "\nTargets represented by at least "
        "2 different compounds:"
    )

    print(
        repeated_targets.to_string()
    )

    # -------------------------------------------------------------
    # 7. Show the actual compounds for candidate targets
    # -------------------------------------------------------------

    candidate_targets = [
        "TUBB3",
        "AURKB",
        "HDAC6",
        "BRAF",
    ]

    candidates = (
        wells[
            wells["target"].isin(candidate_targets)
        ]
        [
            [
                "target",
                "well_position",
                "pert_iname",
                "broad_sample",
            ]
        ]
        .sort_values(
            ["target", "pert_iname"]
        )
    )

    print("\nCandidate compounds:")
    print(candidates.to_string(index=False))

    # -------------------------------------------------------------
    # 8. Build the image manifest for the selected subset
    # -------------------------------------------------------------

    selected_wells = candidates["well_position"].tolist()

    # Return to load_data because this contains one row per SITE
    # and the actual S3 image URLs.
    subset = load_data[
      load_data["Metadata_Well"].isin(selected_wells)
    ].copy()

    # Add the biological labels to every site.
    subset = subset.merge(
      candidates[
        [
          "well_position",
          "target",
          "pert_iname",
          "broad_sample",
        ]
      ],
      left_on="Metadata_Well",
      right_on="well_position",
      how="left",
    )

    # Keep only what we actually need for the BIAP dataset.
    manifest = subset[
      [
        "Metadata_Plate",
        "Metadata_Well",
        "Metadata_Site",
        "target",
        "pert_iname",
        "broad_sample",
        "URL_OrigDNA",
        "URL_OrigMito",
        "URL_OrigAGP",
        "URL_OrigER",
        "URL_OrigRNA",
      ]
    ].copy()

    manifest_path = (
      METADATA_DIR
      / "jump_biap_subset_manifest.csv"
    )

    manifest.to_csv(
      manifest_path,
      index=False,
    )

    print("\nSubset manifest:")
    print(f"Fields: {len(manifest)}")
    print(
      f"Wells: {manifest['Metadata_Well'].nunique()}"
    )
    print(
      f"Targets: {manifest['target'].nunique()}"
    )
    print(
      f"Compounds: {manifest['pert_iname'].nunique()}"
    )
    print(f"Saved to: {manifest_path}")

    # -------------------------------------------------------------
    # 9. Download selected microscopy images
    # -------------------------------------------------------------

    import subprocess

    IMAGE_DIR = (
      ROOT
      / "data"
      / "external"
      / "JUMP_pilot_BIAP"
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

    print("\nDownloading selected images...")

    download_count = 0

    for _, row in manifest.iterrows():

      well = row["Metadata_Well"]
      site = int(row["Metadata_Site"])

      for channel_name, url_column in channel_columns.items():

        source_url = row[url_column]

        if pd.isna(source_url):
          continue

        # Give every local image a simple, predictable BIAP filename.
        #
        # Example:
        #
        # BR00116991_A01_s1_DNA.tif
        destination = (
          IMAGE_DIR
          / f"{row['Metadata_Plate']}_{well}_s{site}_{channel_name}.tif"
        )

        # If the file already exists, skip it.
        # This makes the downloader safe to restart.
        if destination.exists():
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

        download_count += 1

    print(
      f"\nDownloaded {download_count} new images."
    )

    print(
      f"Images stored in: {IMAGE_DIR}"
    )

    # -------------------------------------------------------------
    # 10. Find targets represented by many distinct compounds
    # -------------------------------------------------------------

    target_compound_counts = (
      compounds
      .dropna(subset=["target", "pert_iname"])
      .groupby("target")
      .agg(
        compounds=("pert_iname", "nunique")
      )
      .sort_values(
        "compounds",
        ascending=False,
      )
    )

    print("\nTargets with the most distinct compounds:")
    print(
      target_compound_counts
      .head(30)
      .to_string()
    )


if __name__ == "__main__":
    main()