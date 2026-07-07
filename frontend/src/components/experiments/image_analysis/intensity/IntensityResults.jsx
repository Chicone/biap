import { useState } from "react";
import { Badge } from "@/components/ui/badge";


function IntensityResults({ analysis, analysisError, onSelectObject }) {
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
            <h4>Intensity Analysis</h4>
            <Badge>{analysis.num_objects} objects</Badge>
          </div>

          <div className="analysis-summary">
          <div>
            <span>Objects</span>
            <strong>{analysis.summary.num_objects}</strong>
          </div>

          <div>
            <span>Mean intensity</span>
            <strong>{analysis.summary.mean_intensity.toFixed(1)}</strong>
          </div>

          <div>
            <span>Median intensity</span>
            <strong>{analysis.summary.median_intensity.toFixed(1)}</strong>
          </div>

          <div>
            <span>Integrated</span>
            <strong>{analysis.summary.mean_integrated_intensity.toFixed(1)}</strong>
          </div>
        </div>
          <div className="intensity-table-container">
            <table className="intensity-table">
              <thead>
              <tr>
                <th>Object</th>
                <th>Mean</th>
                <th>Median</th>
                <th>Std</th>
                <th>Min</th>
                <th>Max</th>
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
                  <td>{object.mean_intensity.toFixed(1)}</td>
                  <td>{object.median_intensity.toFixed(1)}</td>
                  <td>{object.std_intensity.toFixed(1)}</td>
                  <td>{object.min_intensity.toFixed(1)}</td>
                  <td>{object.max_intensity.toFixed(1)}</td>
                </tr>
              ))}
              </tbody>
            </table>
          </div>
          {selectedObject && (
            <div className="object-details-panel">
              <h5>Object {selectedObject.label}</h5>

              <div className="object-details-grid">
                <span>Mean intensity</span>
                <strong>{selectedObject.mean_intensity.toFixed(1)}</strong>

                <span>Median intensity</span>
                <strong>{selectedObject.median_intensity.toFixed(1)}</strong>

                <span>Minimum intensity</span>
                <strong>{selectedObject.min_intensity.toFixed(1)}</strong>

                <span>Maximum intensity</span>
                <strong>{selectedObject.max_intensity.toFixed(1)}</strong>

                <span>Standard deviation</span>
                <strong>{selectedObject.std_intensity.toFixed(1)}</strong>

                <span>Integrated intensity</span>
                <strong>{selectedObject.integrated_intensity.toFixed(1)}</strong>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default IntensityResults;