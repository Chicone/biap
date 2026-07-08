import { Button } from "@/components/ui/button";

function TexturePanel({
  foreground,
  setForeground,
  setAnalysis,
  setEvaluation,
  setOverlayMode,
  setSelectedObjectLabel,
  isAnalyzing,
  onRunTexture,
}) {
  return (
    <section className="analysis-module texture-module">
      <div className="section-label">Texture</div>

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

          <Button onClick={onRunTexture} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing..." : "Run Texture"}
          </Button>
        </div>
      </div>
    </section>
  );
}

export default TexturePanel;