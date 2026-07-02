import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import ExperimentWorkspace from "@/components/experiments/ExperimentWorkspace";
import { getExperimentById } from "@/services/experimentService";

function ExperimentWorkspacePage() {
  const [experiment, setExperiment] = useState(null);

  const { experimentId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    async function loadExperiment() {
      const data = await getExperimentById(experimentId);
      setExperiment(data);
    }

    loadExperiment();
  }, [experimentId]);

  if (!experiment) {
    return <p>Loading experiment...</p>;
  }

  return (
    <ExperimentWorkspace
      experiment={experiment}
      onBack={() => navigate("/experiments")}
    />
  );
}

export default ExperimentWorkspacePage;