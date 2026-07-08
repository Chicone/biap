import { useState } from "react";
import { Badge } from "@/components/ui/badge";

function SegmentationResults({
  analysis,
  analysisError,
  evaluation,
  evaluationError,
  onSelectObject,
}) {
  const [selectedObject, setSelectedObject] = useState(null);

  if (!analysis && !evaluation && !analysisError && !evaluationError) {
    return null;
  }

  return (
    <div className="analysis-panels">
      {analysisError && <p className="error-text">{analysisError}</p>}

      {analysis && (
        <div className="analysis-panel">
          <div className="analysis-header">
            <h4>Segmentation Analysis</h4>
            <Badge>{analysis.num_objects} objects</Badge>
          </div>

          <div className="analysis-summary">
            <div>
              <span>Method</span>
              <strong>Otsu</strong>
            </div>

            <div>
              <span>Threshold</span>
              <strong>{analysis.threshold}</strong>
            </div>

            <div>
              <span>Detected objects</span>
              <strong>{analysis.num_objects}</strong>
            </div>
          </div>

          <h5>Detected objects</h5>

          <div className="morphology-table-container">
            <table className="morphology-table">
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Area</th>
                  <th>Centroid row</th>
                  <th>Centroid col</th>
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
                    <td>{object.area.toFixed(1)}</td>
                    <td>{object.centroid.row.toFixed(1)}</td>
                    <td>{object.centroid.col.toFixed(1)}</td>
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

      {evaluationError && <p className="error-text">{evaluationError}</p>}

      {evaluation && (
        <div className="analysis-panel">
          <div className="analysis-header">
            <h4>Ground-truth Evaluation</h4>
            <Badge>{evaluation.foreground}</Badge>
          </div>

          <div className="analysis-summary">
            <div>
              <span>IoU</span>
              <strong>{evaluation.iou.toFixed(3)}</strong>
            </div>

            <div>
              <span>Dice</span>
              <strong>{evaluation.dice.toFixed(3)}</strong>
            </div>

            <div>
              <span>Precision</span>
              <strong>{evaluation.precision.toFixed(3)}</strong>
            </div>

            <div>
              <span>Recall</span>
              <strong>{evaluation.recall.toFixed(3)}</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SegmentationResults;