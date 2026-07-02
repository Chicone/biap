import { NavLink } from "react-router-dom";

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
        <NavLink
          to="/dashboard"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          🏠 Dashboard
        </NavLink>

        <NavLink
          to="/experiments"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          🧪 Experiments
        </NavLink>

        <NavLink
          to="/settings"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          ⚙ Settings
        </NavLink>
      </nav>
    </aside>
  );
}

export default Sidebar;