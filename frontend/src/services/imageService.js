const API_URL = "http://127.0.0.1:8002";

export async function getImages(datasetId) {
  const response = await fetch(`${API_URL}/datasets/${datasetId}/images`);

  if (!response.ok) {
    throw new Error("Failed to load images");
  }

  return response.json();
}

export async function createImage(datasetId, image) {
  const response = await fetch(`${API_URL}/datasets/${datasetId}/images`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(image),
  });

  if (!response.ok) {
    throw new Error("Failed to create image");
  }

  return response.json();
}

export async function uploadImage(datasetId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_URL}/datasets/${datasetId}/upload`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error("Failed to upload image");
  }

  return response.json();
}

export async function importFolder(
  datasetId,
  folderPath,
  datasetName = ""
) {
  const normalizedDatasetName = datasetName.trim().toUpperCase();

  const importerEndpoint =
    normalizedDatasetName === "BBBC021"
      ? "import-bbbc021"
      : "import-folder";

  const requestBody = {
    folder_path: folderPath,
  };

  if (normalizedDatasetName === "BBBC021") {
    requestBody.max_images = null;
  }

  const response = await fetch(
    `${API_URL}/datasets/${datasetId}/${importerEndpoint}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : "Failed to import folder"
    );
  }

  return response.json();
}

export async function analyzeImage(datasetId, imageId) {
  const response = await fetch(
    `${API_URL}/datasets/${datasetId}/images/${imageId}/analysis`
  );

  if (!response.ok) {
    throw new Error("Failed to analyze image");
  }

  return response.json();
}

export async function evaluateImage(datasetId, imageId, foreground = "bright") {
  const response = await fetch(
    `${API_URL}/datasets/${datasetId}/images/${imageId}/evaluate?foreground=${foreground}`
  );

  if (!response.ok) {
    throw new Error("Failed to evaluate image");
  }

  return response.json();
}