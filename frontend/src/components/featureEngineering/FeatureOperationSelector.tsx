import { Calendar, Code2, Filter, Hash, RefreshCw, ShieldCheck, Sparkles, Type } from "lucide-react";
import { ErrorMessage } from "../common/States";

interface FeatureOperationSelectorProps {
  onEngineer: () => void;
  loading: boolean;
  error?: string;
}

export function FeatureOperationSelector({ onEngineer, loading, error }: FeatureOperationSelectorProps) {
  return (
    <div className="feature-engineering-selector">
      <div className="safety-notice-banner">
        <div className="safety-icon">
          <ShieldCheck size={20} />
        </div>
        <div className="safety-content">
          <h4>Automated Feature Engineering Pipeline</h4>
          <p>
            Feature engineering analyzes your dataset structure and generates model-ready features.
            The original uploaded data remains <strong>completely unchanged</strong>, creating a new engineered artifact.
          </p>
        </div>
      </div>

      <div className="feature-showcase-grid">
        <div className="feature-category-card">
          <div className="feature-category-header">
            <Calendar size={18} />
            <h4>Date Extraction</h4>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "2px 0 8px" }}>
            Extracts components from detected date/timestamp columns.
          </p>
          <div className="feature-tag-list">
            <span className="feature-tag">Year</span>
            <span className="feature-tag">Month</span>
            <span className="feature-tag">Day</span>
            <span className="feature-tag">Day of Week</span>
            <span className="feature-tag">Quarter</span>
            <span className="feature-tag">Is Weekend</span>
            <span className="feature-tag">Days Ref</span>
          </div>
        </div>

        <div className="feature-category-card">
          <div className="feature-category-header">
            <Type size={18} />
            <h4>Text Features</h4>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "2px 0 8px" }}>
            Calculates text metrics for unstructured string columns.
          </p>
          <div className="feature-tag-list">
            <span className="feature-tag">Word Count</span>
            <span className="feature-tag">Character Count</span>
            <span className="feature-tag">Avg Word Length</span>
            <span className="feature-tag">Uppercase Count</span>
            <span className="feature-tag">Lowercase Count</span>
            <span className="feature-tag">Punctuation</span>
          </div>
        </div>

        <div className="feature-category-card">
          <div className="feature-category-header">
            <Hash size={18} />
            <h4>Numeric Transformations</h4>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "2px 0 8px" }}>
            Applies non-linear mathematical transformations to numeric features.
          </p>
          <div className="feature-tag-list">
            <span className="feature-tag">Square (x²)</span>
            <span className="feature-tag">Cube (x³)</span>
            <span className="feature-tag">Log (log1p)</span>
            <span className="feature-tag">Square Root (√x)</span>
          </div>
        </div>

        <div className="feature-category-card">
          <div className="feature-category-header">
            <Code2 size={18} />
            <h4>Interaction & Encoding</h4>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "2px 0 8px" }}>
            Pairs correlated features and encodes categorical values.
          </p>
          <div className="feature-tag-list">
            <span className="feature-tag">Product (x1 × x2)</span>
            <span className="feature-tag">Ratio (x1 ÷ x2)</span>
            <span className="feature-tag">Frequency Encoding</span>
            <span className="feature-tag">Label Encoding</span>
          </div>
        </div>

        <div className="feature-category-card" style={{ gridColumn: "1 / -1" }}>
          <div className="feature-category-header">
            <Filter size={18} />
            <h4>Feature Selection & Quality Filters</h4>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "2px 0 8px" }}>
            Automatically prunes low-quality generated features to prevent overfitting.
          </p>
          <div className="feature-tag-list">
            <span className="feature-tag">Missing Filter (&gt; 50%)</span>
            <span className="feature-tag">Variance Threshold (&lt; 0.01)</span>
            <span className="feature-tag">Collinearity Filter (&gt; 0.95)</span>
          </div>
        </div>
      </div>

      <div className="action-panel">
        <div className="action-info">
          <h3>Run Feature Engineering Pipeline</h3>
          <p>
            Transforms your dataset features and creates a new versioned engineered dataset.
          </p>
        </div>
        <button
          type="button"
          className="button primary"
          onClick={onEngineer}
          disabled={loading}
        >
          {loading ? (
            <>
              <RefreshCw size={16} className="spinner" />
              Engineering features...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Engineer Features
            </>
          )}
        </button>
      </div>

      {error && <ErrorMessage message={error} />}
    </div>
  );
}
