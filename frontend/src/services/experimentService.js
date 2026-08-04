const API_URL = "http://127.0.0.1:8002";

export async function getExperiments() {
  const response = await fetch(`${API_URL}/experiments`);

  if (!response.ok) {
    throw new Error("Failed to load experiments");
  }

  return response.json();
}

export async function createExperiment(experiment) {
  const response = await fetch(`${API_URL}/experiments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(experiment),
  });

  if (!response.ok) {
    throw new Error("Failed to create experiment");
  }

  return response.json();
}

export async function getExperimentById(experimentId) {
  const response = await fetch(`${API_URL}/experiments/${experimentId}`);

  if (!response.ok) {
    throw new Error("Failed to load experiment");
  }

  return response.json();
}