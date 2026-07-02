import { useEffect, useState } from "react";
import CreateDatasetModal from "./CreateDatasetModal";
import { getDatasets, createDataset } from "@/services/datasetService";
import { Button } from "@/components/ui/button";
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

function DatasetsTab({ experimentId }) {
  const [datasets, setDatasets] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

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

    setIsCreateModalOpen(false);
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
            <TableRow key={dataset.id}>
              <TableCell className="pl-4">{dataset.name}</TableCell>
              <TableCell>{dataset.dataset_type}</TableCell>
              <TableCell>{dataset.image_count}</TableCell>
              <TableCell>{dataset.status}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <CreateDatasetModal
          open={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onCreate={handleCreateDataset}
      />
    </div>
  );
}

export default DatasetsTab;