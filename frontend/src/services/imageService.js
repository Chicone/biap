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
  datasetName = "",
  datasetType = ""
) {
  const normalizedDatasetName =
    datasetName.trim().toUpperCase();

  const normalizedDatasetType =
    datasetType.trim().toUpperCase();

  let importerEndpoint = "import-folder";

  if (
    normalizedDatasetName === "BBBC021"
  ) {
    importerEndpoint = "import-bbbc021";
  }

  if (
    normalizedDatasetName.includes("JUMP") ||
    normalizedDatasetType.includes("JUMP")
  ) {
    importerEndpoint = "import-jump";
  }

  const body = {
    folder_path: folderPath,
  };

  if (
    importerEndpoint === "import-folder"
  ) {
    body.max_images = 20;
  }

  if (
    importerEndpoint === "import-bbbc021"
  ) {
    body.max_images = null;
  }

  const response = await fetch(
    `${API_URL}/datasets/${datasetId}/${importerEndpoint}`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }
  );

  if (!response.ok) {
    const error =
      await response.json().catch(() => null);

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

export async function deleteFeatureSet(featureSetId) {
  const response = await fetch(
    `${API_URL}/feature-sets/${featureSetId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);

    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : "Failed to delete feature set"
    );
  }

  return response.json();
}