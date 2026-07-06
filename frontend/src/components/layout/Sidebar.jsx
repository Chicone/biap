import { NavLink } from "react-router-dom";

function Sidebar({ collapsed, onToggle }) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <button
        className="sidebar-toggle"
        onClick={onToggle}
      >
        {collapsed ? "➡" : "⬅"}
      </button>

      <div className="brand">
        <div className="brand-icon">B</div>

        {!collapsed && (
          <div>
            <h1>BIAP</h1>
            <p>Biomedical Intelligence Platform</p>
          </div>
        )}
      </div>

      <nav>
        <NavLink
          to="/dashboard"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          <span>🏠</span>
          {!collapsed && <span>Dashboard</span>}
        </NavLink>

        <NavLink
          to="/experiments"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          <span>🧪</span>
          {!collapsed && <span>Experiments</span>}
        </NavLink>

        <NavLink
          to="/settings"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          <span>⚙</span>
          {!collapsed && <span>Settings</span>}
        </NavLink>
      </nav>
    </aside>
  );
}

export default Sidebar;