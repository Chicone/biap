import { Routes, Route, Navigate } from "react-router-dom";

import DashboardLayout from "@/components/layout/DashboardLayout";
import ExperimentsPage from "@/pages/ExperimentsPage";
import ExperimentWorkspacePage from "@/pages/ExperimentWorkspacePage";
import DatasetWorkspacePage from "@/pages/DatasetWorkspacePage";

function DashboardPage() {
  return (
    <section className="panel">
      <h2>Dashboard</h2>
      <p>Dashboard under construction.</p>
    </section>
  );
}

function SettingsPage() {
  return (
    <section className="panel">
      <h2>Settings</h2>
      <p>Settings under construction.</p>
    </section>
  );
}

function App() {
  return (
    <DashboardLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/experiments" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/experiments/:experimentId"
          element={<ExperimentWorkspacePage />}
        />
        <Route path="/experiments/:experimentId/datasets/:datasetId"
          element={<DatasetWorkspacePage />}
        />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </DashboardLayout>
  );
}

export default App;