const API_URL = "http://127.0.0.1:8000";

export async function getDatasets(experimentId) {
  const response = await fetch(`${API_URL}/experiments/${experimentId}/datasets`);

  if (!response.ok) {
    throw new Error("Failed to load datasets");
  }

  return response.json();
}

export async function createDataset(experimentId, dataset) {
  const response = await fetch(`${API_URL}/experiments/${experimentId}/datasets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(dataset),
  });

  if (!response.ok) {
    throw new Error("Failed to create dataset");
  }

  return response.json();
}