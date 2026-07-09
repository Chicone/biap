function FeatureBuilderSection({ title, children, defaultOpen = false }) {
  return (
    <details className="feature-builder-section" open={defaultOpen}>
      <summary>{title}</summary>

      <div className="feature-builder-section-content">
        {children}
      </div>
    </details>
  );
}

export default FeatureBuilderSection;