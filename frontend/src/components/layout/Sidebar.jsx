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
        <a className="active">🏠 Dashboard</a>
        <a>🧪 Experiments</a>
        <a>⚙ Settings</a>
      </nav>
    </aside>
  );
}

export default Sidebar;