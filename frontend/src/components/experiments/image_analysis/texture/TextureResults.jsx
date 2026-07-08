import { useState } from "react";
import { Badge } from "@/components/ui/badge";

function TextureResults({ analysis, analysisError, onSelectObject }) {
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
            <h4>Texture Analysis</h4>
            <Badge>{analysis.num_objects} objects</Badge>
          </div>

          <div className="analysis-summary">
            <div>
              <span>Objects</span>
              <strong>{analysis.summary.num_objects}</strong>
            </div>

            <div>
              <span>Contrast</span>
              <strong>{analysis.summary.mean_contrast.toFixed(2)}</strong>
            </div>

            <div>
              <span>Homogeneity</span>
              <strong>{analysis.summary.mean_homogeneity.toFixed(3)}</strong>
            </div>

            <div>
              <span>Energy</span>
              <strong>{analysis.summary.mean_energy.toFixed(3)}</strong>
            </div>
          </div>

          <div
            className="morphology-table-container"
            style={{
              width: "100%",
              maxWidth: "100%",
              overflowX: "auto",
            }}
          >
            <table
              className="morphology-table"
              style={{
                minWidth: "900px",
                width: "max-content",
              }}
            >
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Contrast</th>
                  <th>Dissimilarity</th>
                  <th>Homogeneity</th>
                  <th>ASM</th>
                  <th>Energy</th>
                  <th>Correlation</th>
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
                      if (onSelectObject) {
                        onSelectObject(object.label);
                      }
                    }}
                  >
                    <td>{object.label}</td>
                    <td>{object.contrast.toFixed(2)}</td>
                    <td>{object.dissimilarity.toFixed(2)}</td>
                    <td>{object.homogeneity.toFixed(3)}</td>
                    <td>{object.asm.toFixed(3)}</td>
                    <td>{object.energy.toFixed(3)}</td>
                    <td>{object.correlation.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedObject && (
            <div className="object-details-panel">
              <h5>Object {selectedObject.label}</h5>

              <div className="object-details-grid">
                <span>Contrast</span>
                  <strong>{selectedObject.contrast.toFixed(2)}</strong>

                  <span>Dissimilarity</span>
                  <strong>{selectedObject.dissimilarity.toFixed(2)}</strong>

                  <span>Homogeneity</span>
                  <strong>{selectedObject.homogeneity.toFixed(3)}</strong>

                  <span>ASM</span>
                  <strong>{selectedObject.asm.toFixed(3)}</strong>

                  <span>Energy</span>
                  <strong>{selectedObject.energy.toFixed(3)}</strong>

                  <span>Correlation</span>
                  <strong>{selectedObject.correlation.toFixed(3)}</strong>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default TextureResults;