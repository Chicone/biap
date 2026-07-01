function OverviewTab({ experiment }) {
  return (
    <div className="workspace-content">
      <div className="summary-grid">

        <div className="summary-card">
          <span>Domain</span>
          <strong>{experiment.domain}</strong>
        </div>

        <div className="summary-card">
          <span>Status</span>
          <strong>{experiment.status}</strong>
        </div>

        <div className="summary-card">
          <span>Datasets</span>
          <strong>0</strong>
        </div>

        <div className="summary-card">
          <span>Models</span>
          <strong>0</strong>
        </div>

      </div>

      <div className="panel overview-description">
        <h3>Description</h3>

        <p>
          {experiment.description || "No description provided."}
        </p>

        <hr />

        <p>
          <strong>Last updated:</strong> {experiment.updated}
        </p>
      </div>
    </div>
  );
}

export default OverviewTab;