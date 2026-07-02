import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

function CreateDatasetModal({ open, onClose, onCreate }) {
  const [formData, setFormData] = useState({
    name: "",
    dataset_type: "Microscopy",
    description: "",
  });

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((currentData) => ({
      ...currentData,
      [name]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onCreate(formData);
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Dataset</DialogTitle>
          <DialogDescription>
            Register a dataset inside the current experiment.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="experiment-form">
          <label>
            Dataset name
            <Input
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Histology batch 01"
              required
            />
          </label>

          <label>
            Dataset type
            <select
              name="dataset_type"
              value={formData.dataset_type}
              onChange={handleChange}
            >
              <option>Microscopy</option>
              <option>Histology</option>
              <option>MRI</option>
              <option>CT</option>
              <option>Pathology</option>
            </select>
          </label>

          <label>
            Description
            <Textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Brief description of the dataset"
            />
          </label>

          <div className="modal-actions">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Import Dataset</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default CreateDatasetModal;