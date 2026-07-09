import { Button } from "@/components/ui/button";

function FeatureSetCard({
  featureSet,
  showMatrix,
  onToggleMatrix,
}) {
  const removedFeatureCount =
    (featureSet.removed_features?.constant?.length || 0) +
    (featureSet.removed_features?.correlated?.length || 0);

  return (
    <div className="analysis-panel">
      <div className="analysis-header">
        <h4>{featureSet.name}</h4>
      </div>

      <div className="analysis-summary">
        <div>
          <span>Status</span>
          <strong className="feature-summary-value">{featureSet.status}</strong>
        </div>

        <div>
          <span>Images</span>
          <strong className="feature-summary-value">
            {featureSet.images_processed}
          </strong>
        </div>

        <div>
          <span>Objects</span>
          <strong className="feature-summary-value">
            {featureSet.num_objects}
          </strong>
        </div>

        <div>
          <span>Features</span>
          <strong className="feature-summary-value">
            {featureSet.num_features}
          </strong>
        </div>

        <div>
          <span>Scaling</span>
          <strong className="feature-summary-value feature-summary-text-value">
            {featureSet.scaling}
          </strong>
        </div>

        {removedFeatureCount > 0 && (
          <div>
            <span>Removed features</span>
            <strong className="feature-summary-value">
              {removedFeatureCount}
            </strong>
          </div>
        )}

        {featureSet.pca && (
          <div>
            <span>PCA total</span>
            <strong className="feature-summary-value">
              {(featureSet.pca.total_explained_variance * 100).toFixed(1)}%
            </strong>
          </div>
        )}

        {featureSet.umap && (
          <div>
            <span>UMAP</span>
            <strong className="feature-summary-value">
              {featureSet.umap.components}D
            </strong>
          </div>
        )}
      </div>

      {featureSet.pca && (
        <div className="feature-breakdown feature-pca-breakdown">
          <div className="feature-breakdown-heading">
            PCA
          </div>

          <div>
            <span>Mode</span>
            <strong>{featureSet.pca.mode}</strong>
          </div>

          <div>
            <span>Components</span>
            <strong>{featureSet.pca.components}</strong>
          </div>

          <div className="feature-breakdown-heading">
            Explained variance
          </div>

          {featureSet.pca.explained_variance_ratio.map((value, index) => (
            <div key={index}>
              <span>PC{index + 1}</span>
              <strong>{(value * 100).toFixed(1)}%</strong>
            </div>
          ))}

          <div>
            <span>Total</span>
            <strong>
              {(featureSet.pca.total_explained_variance * 100).toFixed(1)}%
            </strong>
          </div>
        </div>
      )}

      {featureSet.umap && (
        <div className="feature-breakdown feature-pca-breakdown">
          <div className="feature-breakdown-heading">
            UMAP
          </div>

          <div>
            <span>Mode</span>
            <strong>{featureSet.umap.mode}</strong>
          </div>

          <div>
            <span>Components</span>
            <strong>{featureSet.umap.components}</strong>
          </div>
        </div>
      )}

      {removedFeatureCount > 0 && (
        <div className="feature-breakdown">
          {featureSet.removed_features?.constant?.length > 0 && (
            <div>
              <span>Constant</span>
              <strong>{featureSet.removed_features.constant.join(", ")}</strong>
            </div>
          )}

          {featureSet.removed_features?.correlated?.length > 0 && (
            <div>
              <span>Correlated</span>
              <strong>{featureSet.removed_features.correlated.join(", ")}</strong>
            </div>
          )}
        </div>
      )}

      {featureSet.scaled_features?.length > 0 && (
        <div className="feature-breakdown">
          <div>
            <span>Scaled features</span>
            <strong>{featureSet.scaled_features.length}</strong>
          </div>
        </div>
      )}

      <Button className="feature-set-action-button" onClick={onToggleMatrix}>
        {showMatrix ? "Hide Feature Matrix" : "View Feature Matrix"}
      </Button>
    </div>
  );
}

export default FeatureSetCard;