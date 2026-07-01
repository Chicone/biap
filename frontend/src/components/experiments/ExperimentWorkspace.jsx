import { useState } from "react";
import OverviewTab from "./OverviewTab";

function ExperimentWorkspace({ experiment, onBack }) {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <section className="panel experiment-workspace">
      <button className="secondary-button back-button" onClick={onBack}>
        ← Back to Experiments
      </button>
      <div className="workspace-header">
        <div>
          <h3>{experiment.name}</h3>
          <p>{experiment.description || "No description provided."}</p>
        </div>

        <span className="badge ready">{experiment.status}</span>
      </div>

      <div className="workspace-tabs">
        <button
          className={activeTab === "overview" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>

        <button
          className={activeTab === "datasets" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("datasets")}
        >
          Datasets
        </button>

        <button
          className={activeTab === "images" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("images")}
        >
          Images
        </button>

        <button
          className={activeTab === "annotations" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("annotations")}
        >
          Annotations
        </button>

        <button
          className={activeTab === "models" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("models")}
        >
          Models
        </button>

       <button
          className={activeTab === "results" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("results")}
        >
          Results
        </button>

        <button
          className={activeTab === "reports" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("reports")}
        >
          Reports
        </button>

      </div>

      <div className="workspace-content">
        {activeTab === "overview" && (
          <OverviewTab experiment={experiment} />
        )}

        {activeTab === "datasets" && (
          <p>Datasets module coming soon.</p>
        )}

        {activeTab === "images" && (
          <p>Image explorer coming soon.</p>
        )}

        {activeTab === "annotations" && (
          <p>Annotation tools coming soon.</p>
        )}

        {activeTab === "models" && (
          <p>Model workspace coming soon.</p>
        )}

        {activeTab === "results" && (
          <p>Results dashboard coming soon.</p>
        )}

        {activeTab === "reports" && (
          <p>Scientific reports coming soon.</p>
        )}
      </div>
    </section>
  );
}

export default ExperimentWorkspace;