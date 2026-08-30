"""
Find well-represented compound targets in the full JUMP production dataset.

This queries the public JUMP augmented metadata database remotely.
No microscopy images are downloaded.

Goal:
    Find biological targets represented by many distinct compounds,
    so we can build a stronger target-prediction Cell Painting dataset.
"""

import duckdb


DATABASE_URL = (
    "https://imaging-platform.s3.amazonaws.com/"
    "projects/cpg0042-chandrasekaran-jump/"
    "workspace/publication_data/2025_Chandrasekaran/"
    "jump_production_datastore/interim/"
    "jump_metadata_augmented.duckdb"
)


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

    # First inspect the available columns.
    columns = conn.execute(
        """
        DESCRIBE meta.compound_metadata
        """
    ).fetchdf()

    print("\nCompound metadata columns:")
    print(columns[["column_name", "column_type"]].to_string(index=False))

    TARGET_COLUMNS = [
      "Metadata_repurposing_target",
      "Metadata_Uniprot_target",
      "Metadata_chmprb_target_genes",
    ]

    MIN_COMPOUNDS = 20

    for column in TARGET_COLUMNS:
      print(f"\n=== {column} ===")

      query = f"""
        SELECT
            {column} AS target,
            COUNT(DISTINCT Metadata_InChIKey) AS compounds
        FROM meta.compound_metadata
        WHERE {column} IS NOT NULL
          AND {column} != ''
        GROUP BY {column}
        HAVING COUNT(DISTINCT Metadata_InChIKey) >= {MIN_COMPOUNDS}
        ORDER BY compounds DESC
        LIMIT 50
        """

      result = conn.execute(query).fetchdf()

      if result.empty:
        print(
          f"No targets with at least "
          f"{MIN_COMPOUNDS} distinct compounds."
        )
      else:
        print(result.to_string(index=False))

      # -------------------------------------------------------------
      # Select well-represented SINGLE targets
      # -------------------------------------------------------------

      query = """
      SELECT
          Metadata_Uniprot_target AS target,
          COUNT(DISTINCT Metadata_InChIKey) AS compounds
      FROM meta.compound_metadata
      WHERE Metadata_Uniprot_target IS NOT NULL
        AND Metadata_Uniprot_target != ''
        AND Metadata_Uniprot_target NOT LIKE '%|%'
      GROUP BY Metadata_Uniprot_target
      HAVING COUNT(DISTINCT Metadata_InChIKey) >= 30
      ORDER BY compounds DESC
      """

      single_targets = conn.execute(query).fetchdf()

      print("\n=== Single UniProt targets with >= 30 compounds ===")
      print(single_targets.to_string(index=False))

      SELECTED_TARGETS = [
        "P04637",  # TP53
        "P28482",  # MAPK1 / ERK2
        "P00533",  # EGFR
      ]

      for target in SELECTED_TARGETS:
        print(f"\n=== Compounds annotated to {target} ===")

        query = f"""
          SELECT DISTINCT
              Metadata_InChIKey,
              Metadata_SMILES,
              Metadata_repurposing_name,
              Metadata_repurposing_target,
              Metadata_repurposing_moa,
              Metadata_Uniprot_target
          FROM meta.compound_metadata
          WHERE Metadata_Uniprot_target = '{target}'
          LIMIT 40
          """

        result = conn.execute(query).fetchdf()
        print(result.to_string(index=False))

      # -------------------------------------------------------------
      # Look for targets supported by BOTH annotation systems
      # -------------------------------------------------------------

      query = """
      SELECT
          Metadata_repurposing_target AS repurposing_target,
          Metadata_Uniprot_target AS uniprot_target,
          COUNT(DISTINCT Metadata_InChIKey) AS compounds
      FROM meta.compound_metadata
      WHERE Metadata_repurposing_target IS NOT NULL
        AND Metadata_repurposing_target != ''
        AND Metadata_Uniprot_target IS NOT NULL
        AND Metadata_Uniprot_target != ''
        AND Metadata_repurposing_target NOT LIKE '%|%'
        AND Metadata_Uniprot_target NOT LIKE '%|%'
      GROUP BY
          Metadata_repurposing_target,
          Metadata_Uniprot_target
      HAVING COUNT(DISTINCT Metadata_InChIKey) >= 5
      ORDER BY compounds DESC
      LIMIT 50
      """

      result = conn.execute(query).fetchdf()

      print("\n=== Target pairs supported by both annotations ===")
      print(result.to_string(index=False))

      # -------------------------------------------------------------
      # Find well-represented mechanisms of action (MOAs)
      # -------------------------------------------------------------

      query = """
      SELECT
          Metadata_repurposing_moa AS moa,
          COUNT(DISTINCT Metadata_InChIKey) AS compounds
      FROM meta.compound_metadata
      WHERE Metadata_repurposing_moa IS NOT NULL
        AND Metadata_repurposing_moa != ''
      GROUP BY Metadata_repurposing_moa
      HAVING COUNT(DISTINCT Metadata_InChIKey) >= 10
      ORDER BY compounds DESC
      LIMIT 50
      """

      result = conn.execute(query).fetchdf()

      print("\n=== MOAs with at least 10 distinct compounds ===")
      print(result.to_string(index=False))


if __name__ == "__main__":
    main()