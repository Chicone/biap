import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import ExperimentTable from "@/components/experiments/ExperimentTable";
import CreateExperimentModal from "@/components/experiments/CreateExperimentModal";
import { getExperiments, createExperiment } from "@/services/experimentService";
import { Button } from "@/components/ui/button";

function ExperimentsPage() {
  const [experiments, setExperiments] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    async function loadExperiments() {
      const data = await getExperiments();
      setExperiments(data);
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

  function handleSelectExperiment(experimentId) {
    navigate(`/experiments/${experimentId}`);
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h2>Experiments</h2>
          <p>Manage biomedical imaging experiments and AI analysis workflows.</p>
          <p className="api-status">
            Backend connected · {experiments.length} experiments loaded
          </p>
        </div>

        <Button onClick={() => setIsCreateModalOpen(true)}>
          New Experiment
        </Button>
      </header>

      <ExperimentTable
        experiments={experiments}
        onSelectExperiment={handleSelectExperiment}
      />

      {isCreateModalOpen && (
        <CreateExperimentModal
          onClose={() => setIsCreateModalOpen(false)}
          onCreate={handleCreateExperiment}
        />
      )}
    </>
  );
}

export default ExperimentsPage;