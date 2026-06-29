import { useState } from "react";

function CreateExperimentModal({ onClose, onCreate }) {
  const [formData, setFormData] = useState({
    name: "",
    domain: "Microscopy",
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
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-header">
          <h3>Create Experiment</h3>
          <button className="secondary-button" onClick={onClose}>
            Cancel
          </button>
        </div>

        <form onSubmit={handleSubmit} className="experiment-form">
          <label>
            Name
            <input
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Cell morphology pilot"
              required
            />
          </label>

          <label>
            Domain
            <select
              name="domain"
              value={formData.domain}
              onChange={handleChange}
            >
              <option>Microscopy</option>
              <option>Histology</option>
              <option>GNN</option>
              <option>Deep Learning</option>
              <option>LLM</option>
            </select>
          </label>

          <label>
            Description
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              placeholder="Brief description of the experiment"
            />
          </label>

          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit">Create Experiment</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateExperimentModal;