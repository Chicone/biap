function AnalysisSelector({ analysisType, setAnalysisType }) {
  return (
    <section className="analysis-selector">
      <div className="section-label">Analysis</div>

      <label>
        Analysis type
        <select
          value={analysisType}
          onChange={(event) => setAnalysisType(event.target.value)}
        >
          <option value="segmentation">Segmentation</option>
          <option value="morphology">Morphology</option>
          <option value="intensity">Intensity</option>
          <option value="texture">Texture</option>
        </select>
      </label>
    </section>
  );
}

export default AnalysisSelector;