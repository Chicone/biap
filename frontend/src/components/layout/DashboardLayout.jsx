import Sidebar from "./Sidebar";

function DashboardLayout({ children }) {
  return (
    <div className="app">
      <Sidebar />

      <main className="main">
        {children}
      </main>
    </div>
  );
}

export default DashboardLayout;