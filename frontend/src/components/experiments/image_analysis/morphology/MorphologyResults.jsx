import { useState } from "react";
import { Badge } from "@/components/ui/badge";

function MorphologyResults({ analysis, analysisError, onSelectObject, }) {
  const [selectedObject, setSelectedObject] = useState(null);
  if (!analysis && !analysisError) {
    return null;
  }

  return (
    <div className="analysis-panels">
      {analysisError && <p className="error-text">{analysisError}</p>}

      {analysis && (
        <div className="analysis-panel">
          <div className="analysis-header">
            <h4>Morphology Analysis</h4>
            <Badge>{analysis.num_objects} objects</Badge>
          </div>

          <div className="analysis-summary">
            <div>
              <span>Objects</span>
              <strong>{analysis.summary.num_objects}</strong>
            </div>

            <div>
              <span>Mean area</span>
              <strong>{analysis.summary.mean_area.toFixed(1)}</strong>
            </div>

            <div>
              <span>Mean circularity</span>
              <strong>{analysis.summary.mean_circularity.toFixed(3)}</strong>
            </div>

            <div>
              <span>Mean solidity</span>
              <strong>{analysis.summary.mean_solidity.toFixed(3)}</strong>
            </div>
          </div>
          <div className="morphology-table-container">
            <table className="morphology-table">
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Area</th>
                  <th>Circularity</th>
                  <th>Solidity</th>
                  <th>Eccentricity</th>
                  <th>Perimeter</th>
                </tr>
              </thead>
              <tbody>

                {analysis.objects.map((object) => (
                  <tr
                    key={object.label}
                    className={
                      selectedObject?.label === object.label
                        ? "morphology-selected-row"
                        : ""
                    }
                      onClick={() => {
                          setSelectedObject(object);
                          onSelectObject(object.label);
                      }}
                  >
                    <td>{object.label}</td>
                    <td>{object.area.toFixed(1)}</td>
                    <td>{object.circularity.toFixed(3)}</td>
                    <td>{object.solidity.toFixed(3)}</td>
                    <td>{object.eccentricity.toFixed(3)}</td>
                    <td>{object.perimeter.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedObject && (
            <div className="object-details-panel">
              <h5>Object {selectedObject.label}</h5>

              <div className="object-details-grid">
                <span>Area</span>
                <strong>{selectedObject.area.toFixed(1)}</strong>

                <span>Perimeter</span>
                <strong>{selectedObject.perimeter.toFixed(1)}</strong>

                <span>Circularity</span>
                <strong>{selectedObject.circularity.toFixed(3)}</strong>

                <span>Solidity</span>
                <strong>{selectedObject.solidity.toFixed(3)}</strong>

                <span>Eccentricity</span>
                <strong>{selectedObject.eccentricity.toFixed(3)}</strong>

                <span>Major axis</span>
                <strong>{selectedObject.major_axis_length.toFixed(1)}</strong>

                <span>Minor axis</span>
                <strong>{selectedObject.minor_axis_length.toFixed(1)}</strong>

                <span>Equivalent diameter</span>
                <strong>{selectedObject.equivalent_diameter.toFixed(1)}</strong>

                <span>Orientation</span>
                <strong>{selectedObject.orientation.toFixed(3)}</strong>

                <span>Convex area</span>
                <strong>{selectedObject.convex_area.toFixed(1)}</strong>

                <span>Centroid</span>
                <strong>
                  ({selectedObject.centroid.row.toFixed(1)},{" "}
                  {selectedObject.centroid.col.toFixed(1)})
                </strong>

                <span>Bounding box</span>
                <strong>
                  {selectedObject.bbox.min_row}, {selectedObject.bbox.min_col} →{" "}
                  {selectedObject.bbox.max_row}, {selectedObject.bbox.max_col}
                </strong>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MorphologyResults;