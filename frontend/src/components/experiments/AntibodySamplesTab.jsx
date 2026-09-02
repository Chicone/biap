import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const API_URL = "http://127.0.0.1:8002";

function AntibodySamplesTab({ activeDataset }) {
  const [samples, setSamples] = useState([]);
  const [error, setError] = useState(null);

  const [datasetPath, setDatasetPath] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);

  async function loadSamples() {
    if (!activeDataset) {
      setSamples([]);
      return;
    }

    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/antibodies`
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Failed to load antibody samples"
        );
      }

      setSamples(result);
    } catch (error) {
      setError(error.message);
      setSamples([]);
    }
  }

  useEffect(() => {
    loadSamples();
  }, [activeDataset]);

  async function handleImport() {
    if (!activeDataset || !datasetPath.trim()) {
      return;
    }

    setIsImporting(true);
    setError(null);
    setImportResult(null);

    try {
      const response = await fetch(
        `${API_URL}/datasets/${activeDataset.id}/import-antibodies`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            dataset_path: datasetPath.trim(),
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Antibody import failed"
        );
      }

      setImportResult(result);
      await loadSamples();
    } catch (error) {
      setError(error.message);
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <div className="workspace-content">
      <div className="workspace-header">
        <div>
          <h3>Antibody Samples</h3>
          <p>
            Browse antibody sequences and dataset metadata.
          </p>
        </div>

        <div className="antibody-import-controls">
          <input
            value={datasetPath}
            onChange={(event) =>
              setDatasetPath(event.target.value)
            }
            placeholder="Path to antibody dataset"
          />

          <Button
            onClick={handleImport}
            disabled={
              isImporting ||
              !datasetPath.trim()
            }
          >
            {isImporting
              ? "Importing..."
              : "Import Dataset"}
          </Button>
        </div>
      </div>

      {importResult && (
        <p>
          Imported {importResult.imported_samples} samples
          {" · "}
          Skipped {importResult.skipped_samples}
        </p>
      )}

      {error && (
        <p className="error-text">
          {error}
        </p>
      )}

      {samples.length === 0 ? (
        <p>No antibody samples available.</p>
      ) : (
        <table className="ml-results-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Heavy-chain length</th>
              <th>Light-chain length</th>
            </tr>
          </thead>

          <tbody>
            {samples.map((sample) => (
              <tr key={sample.id}>
                <td>{sample.sample_name}</td>
                <td>
                  {sample.heavy_chain_sequence?.length ?? 0}
                </td>
                <td>
                  {sample.light_chain_sequence?.length ?? 0}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default AntibodySamplesTab;