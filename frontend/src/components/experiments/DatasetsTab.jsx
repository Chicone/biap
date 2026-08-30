import { useEffect, useState } from "react";
import CreateDatasetModal from "./CreateDatasetModal";
import { getDatasets, createDataset } from "@/services/datasetService";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

function DatasetsTab({
  experimentId,
  activeDataset,
  onSelectDataset,
}) {
  const [datasets, setDatasets] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
 const [antibodyCsvPath, setAntibodyCsvPath] = useState("");
  const [isImportingAntibodies, setIsImportingAntibodies] = useState(false);
  const [antibodyImportError, setAntibodyImportError] = useState(null);
  const [antibodyImportResult, setAntibodyImportResult] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    async function loadDatasets() {
      const data = await getDatasets(experimentId);
      setDatasets(data);
    }

    loadDatasets();
  }, [experimentId]);

  async function handleCreateDataset(formData) {
    const createdDataset = await createDataset(experimentId, formData);

    setDatasets((currentDatasets) => [
      ...currentDatasets,
      createdDataset,
    ]);

    onSelectDataset(createdDataset);

    setIsCreateModalOpen(false);
  }

  async function handleImportAntibodies() {
    if (!activeDataset || !antibodyCsvPath.trim()) {
      return;
    }

    setIsImportingAntibodies(true);
    setAntibodyImportError(null);
    setAntibodyImportResult(null);

    try {
      const response = await fetch(
        `http://127.0.0.1:8002/datasets/${activeDataset.id}/import-antibodies`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            csv_path: antibodyCsvPath.trim(),
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

      setAntibodyImportResult(result);
    } catch (error) {
      setAntibodyImportError(error.message);
    } finally {
      setIsImportingAntibodies(false);
    }
  }

  return (
    <div className="workspace-content">
      <div className="dataset-header">
        <div>
          <h3>Datasets</h3>
          <p>Manage datasets associated with this experiment.</p>
        </div>

        <Button onClick={() => setIsCreateModalOpen(true)}>
          + Import Dataset
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-4">Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Images</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>

        <TableBody>
          {datasets.map((dataset) => (
            <TableRow
              key={dataset.id}
              onClick={() => {
                onSelectDataset(dataset);
                navigate(`/experiments/${experimentId}/datasets/${dataset.id}`);
              }}
              className={
                activeDataset?.id === dataset.id ? "selected-row" : ""
              }
              style={{ cursor: "pointer" }}
            >
              <TableCell className="pl-4">{dataset.name}</TableCell>
              <TableCell>{dataset.dataset_type}</TableCell>
              <TableCell>{dataset.image_count}</TableCell>
              <TableCell>{dataset.status}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {activeDataset?.dataset_type?.toLowerCase() === "antibody" && (
        <section className="feature-builder-panel">
          <div className="section-label">
            Import Antibody Samples
          </div>

          <label className="feature-builder-field">
            CSV path

            <input
              value={antibodyCsvPath}
              onChange={(event) =>
                setAntibodyCsvPath(event.target.value)
              }
              placeholder="/path/to/antibodies.csv"
              disabled={isImportingAntibodies}
            />
          </label>

          <Button
            type="button"
            onClick={handleImportAntibodies}
            disabled={
              isImportingAntibodies ||
              !antibodyCsvPath.trim()
            }
          >
            {isImportingAntibodies
              ? "Importing..."
              : "Import Antibodies"}
          </Button>

          {antibodyImportError && (
            <p className="error-text">
              {antibodyImportError}
            </p>
          )}

          {antibodyImportResult && (
            <p>
              Imported {antibodyImportResult.imported_samples} antibodies.
              {" "}
              Skipped {antibodyImportResult.skipped_samples}.
            </p>
          )}
        </section>
      )}

      <CreateDatasetModal
          open={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onCreate={handleCreateDataset}
      />
    </div>
  );
}

export default DatasetsTab;