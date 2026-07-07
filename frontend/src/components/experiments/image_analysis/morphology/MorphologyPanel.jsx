import { Button } from "@/components/ui/button";

function MorphologyPanel({
  foreground,
  setForeground,
  setAnalysis,
  setEvaluation,
  setOverlayMode,
  setSelectedObjectLabel,
  isAnalyzing,
  onRunMorphology,
}) {
  return (
    <section className="analysis-module morphology-module">
      <div className="section-label">Morphology</div>

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

          <Button onClick={onRunMorphology} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing..." : "Run Morphology"}
          </Button>
        </div>
      </div>
    </section>
  );
}

export default MorphologyPanel;