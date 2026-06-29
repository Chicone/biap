import { Microscope, FlaskConical, Brain, Network, FileText } from "lucide-react";

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">B</div>
        <div>
          <h1>BIAP</h1>
          <p>Biomedical Intelligence Platform</p>
        </div>
      </div>

      <nav>
        <a className="active"><FlaskConical size={18} /> Experiments</a>
        <a><Microscope size={18} /> Image Explorer</a>
        <a><Brain size={18} /> Models</a>
        <a><Network size={18} /> GNN Analysis</a>
        <a><FileText size={18} /> Reports</a>
      </nav>
    </aside>
  );
}

export default Sidebar;