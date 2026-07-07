import { Button } from "@/components/ui/button";

function IntensityPanel({
  foreground,
  setForeground,
  setAnalysis,
  setEvaluation,
  setOverlayMode,
  setSelectedObjectLabel,
  isAnalyzing,
  onRunIntensity,
}) {
  return (
    <section className="analysis-module intensity-module">
      <div className="section-label">Intensity</div>

      <div className="segmentation-module-header">
        <div className="segmentation-inline-controls">
          <label>
            Foreground
            <select
              value={foreground}
              onChange={(event) => {
                setForeground(event.target.value);
                setAnalysis(null);
                setEvaluation(null);
                setSelectedObjectLabel(null);
                setOverlayMode("original");
              }}
            >
              <option value="bright">Bright objects</option>
              <option value="dark">Dark objects</option>
            </select>
          </label>

          <Button onClick={onRunIntensity} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing..." : "Run Intensity"}
          </Button>
        </div>
      </div>
    </section>
  );
}

export default IntensityPanel;