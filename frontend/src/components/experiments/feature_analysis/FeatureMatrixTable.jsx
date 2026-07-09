function FeatureMatrixTable({ features }) {
  if (!features || features.length === 0) {
    return null;
  }

  const preferredOrder = [
    "dataset_id",
    "image_id",
    "filename",
    "label",

    "area",
    "perimeter",
    "circularity",
    "solidity",
    "convex_area",
    "equivalent_diameter",

    "major_axis_length",
    "minor_axis_length",
    "eccentricity",
    "orientation",

    "centroid_row",
    "centroid_col",

    "bbox_min_row",
    "bbox_min_col",
    "bbox_max_row",
    "bbox_max_col",

    "mean_intensity",
    "median_intensity",
    "min_intensity",
    "max_intensity",
    "std_intensity",
    "integrated_intensity",

    "contrast",
    "dissimilarity",
    "homogeneity",
    "asm",
    "energy",
    "correlation",
  ];

  const existingColumns = Object.keys(features[0]);

  const columns = [
    ...preferredOrder.filter((column) => existingColumns.includes(column)),
    ...existingColumns.filter((column) => !preferredOrder.includes(column)),
  ];
  return (
    <section className="feature-matrix-panel">
      <div className="section-label">Feature Matrix</div>

      <p className="feature-matrix-info">
        {features.length} objects · {columns.length} columns
      </p>

      <div className="feature-matrix-container">
        <table className="feature-matrix-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {features.map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td key={column}>
                    {typeof row[column] === "number"
                      ? Number(row[column]).toFixed(3)
                      : typeof row[column] === "object" && row[column] !== null
                        ? JSON.stringify(row[column])
                        : String(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default FeatureMatrixTable;