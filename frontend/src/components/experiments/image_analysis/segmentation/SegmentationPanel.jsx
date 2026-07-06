import { Button } from "@/components/ui/button";

function SegmentationPanel({
  foreground,
  setForeground,
  overlayMode,
  setOverlayMode,
  setAnalysis,
  setEvaluation,
  isAnalyzing,
  onRunSegmentation,
}) {
  return (
    <section className="analysis-module segmentation-module">
      <div className="section-label">
        Segmentation
      </div>
      <div className="segmentation-module-header">
        <div className="segmentation-inline-controls">
          <label>
            Foreground
            <select
              value={foreground}
              onChange={(event) => {
                setForeground(event.target.value);
                setOverlayMode("original");
                setAnalysis(null);
                setEvaluation(null);
              }}
            >
              <option value="bright">Bright objects</option>
              <option value="dark">Dark objects</option>
            </select>
          </label>

          <div className="segmentation-view-controls">
            <Button
              onClick={() => setOverlayMode("original")}
              variant={overlayMode === "original" ? "default" : "secondary"}
            >
              Original
            </Button>

            <Button
              onClick={() => setOverlayMode("prediction")}
              variant={overlayMode === "prediction" ? "default" : "secondary"}
            >
              Prediction
            </Button>

            <Button
              onClick={() => setOverlayMode("groundTruth")}
              variant={overlayMode === "groundTruth" ? "default" : "secondary"}
            >
              Ground Truth
            </Button>
          </div>

          <Button onClick={onRunSegmentation} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing..." : "Run Segmentation"}
          </Button>
        </div>
      </div>
    </section>
  );
}

export default SegmentationPanel;