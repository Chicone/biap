const API_URL = "http://127.0.0.1:8000";

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