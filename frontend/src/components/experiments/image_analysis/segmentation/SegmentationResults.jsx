import { Badge } from "@/components/ui/badge";

function SegmentationResults({
  analysis,
  analysisError,
  evaluation,
  evaluationError,
}) {
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

          <h5>First detected objects</h5>

          <div className="analysis-table">
            <div className="analysis-row analysis-row-header">
              <span>Object</span>
              <span>Area</span>
              <span>Centroid</span>
            </div>

            {analysis.objects.slice(0, 5).map((object) => (
              <div className="analysis-row" key={object.label}>
                <span>{object.label}</span>
                <span>{object.area}</span>
                <span>
                  ({object.centroid[0].toFixed(1)},{" "}
                  {object.centroid[1].toFixed(1)})
                </span>
              </div>
            ))}
          </div>
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