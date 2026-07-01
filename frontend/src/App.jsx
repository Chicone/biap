import DashboardLayout from "./components/layout/DashboardLayout";
import ExperimentTable from "./components/experiments/ExperimentTable";
import { useEffect, useState } from "react";
import "./App.css";
import CreateExperimentModal from "./components/experiments/CreateExperimentModal";
import ExperimentWorkspace from "./components/experiments/ExperimentWorkspace";
import {
  getExperiments,
  createExperiment,
  getExperimentById,
} from "./services/experimentService";


function App() {
  const [experiments, setExperiments] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedExperiment, setSelectedExperiment] = useState(null);

  useEffect(() => {
    async function loadExperiments() {
      try {
        const data = await getExperiments();
        setExperiments(data);
      } catch (error) {
        console.error(error);
      }
    }

    loadExperiments();
  }, []);

  async function handleCreateExperiment(formData) {
    const createdExperiment = await createExperiment(formData);

    setExperiments((currentExperiments) => [
      ...currentExperiments,
      createdExperiment,
    ]);

    setIsCreateModalOpen(false);
  }

  async function handleSelectExperiment(experimentId) {
    try {
      const experiment = await getExperimentById(experimentId);
      setSelectedExperiment(experiment);
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <DashboardLayout>
      <header className="topbar">
        <div>
          <h2>Experiment Workspace</h2>
          <p>Manage biomedical imaging experiments and AI analysis workflows.</p>
          <p className="api-status">
            Backend connected · {experiments.length} experiments loaded
          </p>
        </div>

        <button onClick={() => setIsCreateModalOpen(true)}>
          New Experiment
        </button>
      </header>

      <section className="cards">
        <div className="card">
          <span>Active Experiments</span>
          <strong>3</strong>
        </div>
        <div className="card">
          <span>Images Loaded</span>
          <strong>128</strong>
        </div>
        <div className="card">
          <span>Models Available</span>
          <strong>5</strong>
        </div>
        <div className="card">
          <span>Reports Generated</span>
          <strong>12</strong>
        </div>
      </section>

      {selectedExperiment ? (
        <ExperimentWorkspace
          experiment={selectedExperiment}
          onBack={() => setSelectedExperiment(null)}
        />
      ) : (
        <ExperimentTable
          experiments={experiments}
          onSelectExperiment={handleSelectExperiment}
        />
      )}

      {isCreateModalOpen && (
        <CreateExperimentModal
          onClose={() => setIsCreateModalOpen(false)}
          onCreate={handleCreateExperiment}
        />
      )}
    </DashboardLayout>
  );
}
export default App;