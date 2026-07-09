import { useMemo, useState } from "react";
import Plot from "react-plotly.js";

const ID_COLUMNS = new Set([
  "dataset_id",
  "image_id",
  "filename",
  "label",
]);

function formatLabel(columnName) {
  return columnName
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function FeatureScatterPlot({ features }) {
  const [colorBy, setColorBy] = useState("none");

  if (!features || features.length === 0) {
    return null;
  }

  const hasPca = "pca_1" in features[0] && "pca_2" in features[0];
  const hasUmap = "umap_1" in features[0] && "umap_2" in features[0];

  if (!hasPca && !hasUmap) {
    return null;
  }

  const xKey = hasUmap ? "umap_1" : "pca_1";
  const yKey = hasUmap ? "umap_2" : "pca_2";
  const title = hasUmap ? "UMAP Projection" : "PCA Projection";

  const numericFeatureColumns = useMemo(() => {
    return Object.keys(features[0]).filter((columnName) => {
      if (ID_COLUMNS.has(columnName)) {
        return false;
      }

      if (columnName === xKey || columnName === yKey) {
        return false;
      }

      return features.every(
        (row) => typeof row[columnName] === "number"
      );
    });
  }, [features, xKey, yKey]);

  const colorOptions = [
    { value: "none", label: "None" },
    { value: "filename", label: "Image" },
    ...numericFeatureColumns.map((columnName) => ({
      value: columnName,
      label: formatLabel(columnName),
    })),
  ];

  const isNumericColor =
    colorBy !== "none" &&
    features.every((row) => typeof row[colorBy] === "number");

  const markerColor = useMemo(() => {
    if (colorBy === "none") {
      return undefined;
    }

    return features.map((row) => row[colorBy]);
  }, [features, colorBy]);

  return (
    <section className="feature-plot-panel">
      <div className="analysis-header">
        <div>
          <h4>{title}</h4>
          <p>
            {features.length} objects projected onto {xKey} and {yKey}.
          </p>
        </div>

        <label className="feature-plot-control">
          Color by
          <select
            value={colorBy}
            onChange={(event) => setColorBy(event.target.value)}
          >
            {colorOptions.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <Plot
        data={[
          {
            x: features.map((row) => row[xKey]),
            y: features.map((row) => row[yKey]),
            mode: "markers",
            type: "scattergl",
            text: features.map(
              (row) =>
                `Image: ${row.filename}<br>` +
                `Object: ${row.label}<br>` +
                `Color: ${
                  colorBy === "none"
                    ? "none"
                    : `${formatLabel(colorBy)} = ${row[colorBy]}`
                }`
            ),
            hoverinfo: "text",
            marker: {
              size: 6,
              opacity: 0.75,
              color: markerColor,
              colorscale: isNumericColor ? "Viridis" : undefined,
              showscale: isNumericColor,
              colorbar: isNumericColor
                ? {
                    title: formatLabel(colorBy),
                  }
                : undefined,
            },
          },
        ]}
        layout={{
          autosize: true,
          height: 520,
          margin: {
            l: 60,
            r: 30,
            t: 30,
            b: 60,
          },
          xaxis: {
            title: xKey,
          },
          yaxis: {
            title: yKey,
          },
        }}
        config={{
          responsive: true,
          displaylogo: false,
        }}
        style={{
          width: "100%",
        }}
      />
    </section>
  );
}

export default FeatureScatterPlot;