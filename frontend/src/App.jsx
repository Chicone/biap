import DashboardLayout from "./components/layout/DashboardLayout";
import ExperimentTable from "./components/ExperimentTable";
import { useEffect, useState } from "react";
import "./App.css";
import { getExperiments , createExperiment } from "./services/experimentService";
import CreateExperimentModal from "./components/experiments/CreateExperimentModal";

function App() {
  const [experiments, setExperiments] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

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

      <ExperimentTable experiments={experiments} />

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