import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import ExperimentWorkspace from "@/components/experiments/ExperimentWorkspace";
import { getExperimentById } from "@/services/experimentService";
import { useSearchParams } from "react-router-dom";

function ExperimentWorkspacePage() {
  const [experiment, setExperiment] = useState(null);

  const { experimentId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || "overview";

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
      initialTab={initialTab}
      onBack={() => navigate("/experiments")}
    />
  );
}

export default ExperimentWorkspacePage;