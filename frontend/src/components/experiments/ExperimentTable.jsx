function ExperimentTable({ experiments, onSelectExperiment }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h3>Recent Experiments</h3>
        <p>Prototype experiment layer for BIAP.</p>
      </div>

      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Domain</th>
            <th>Status</th>
            <th>Last Updated</th>
          </tr>
        </thead>

        <tbody>
          {experiments.map((exp) => (
            <tr key={exp.id} onClick={() => onSelectExperiment(exp.id)}>
              <td>{exp.name}</td>
              <td>{exp.domain}</td>
              <td>{exp.status}</td>
              <td>{exp.updated}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default ExperimentTable;