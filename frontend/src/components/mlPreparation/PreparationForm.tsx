import { Layers3, RefreshCw, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { ErrorMessage } from "../common/States";
import type { ColumnProfile, PrepareRequest } from "../../types/api";

interface PreparationFormProps {
  columns: ColumnProfile[];
  onPrepare: (request: PrepareRequest) => void;
  loading: boolean;
  error?: string;
}

export function PreparationForm({ columns, onPrepare, loading, error }: PreparationFormProps) {
  const [targetColumn, setTargetColumn] = useState(columns.length > 0 ? columns[0].column_name : "");
  const [testSize, setTestSize] = useState(0.20);
  const [randomState, setRandomState] = useState(42);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetColumn.trim() || loading) return;
    onPrepare({
      target_column: targetColumn.trim(),
      test_size: Number(testSize),
      random_state: Number(randomState),
    });
  };

  return (
    <form className="preparation-form" onSubmit={handleSubmit}>
      <div className="safety-notice-banner">
        <div className="safety-icon">
          <ShieldCheck size={20} />
        </div>
        <div className="safety-content">
          <h4>Leakage Prevention Guarantee</h4>
          <p>
            ML preparation creates a train/test-ready split. Preprocessing scalers and encoders are fitted
            <strong> exclusively on the training split</strong> to prevent data leakage.
          </p>
        </div>
      </div>

      <div className="action-panel" style={{ flexDirection: "column", alignItems: "stretch", gap: 18 }}>
        <div className="action-info">
          <h3>Configure ML Data Preparation</h3>
          <p>Select your target label column and train/test split ratio.</p>
        </div>

        <div className="prep-form-grid">
          <div className="form-group">
            <label htmlFor="target-col-select">Target Column *</label>
            <select
              id="target-col-select"
              className="form-select"
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              required
            >
              {columns.length === 0 ? (
                <option value="">No columns available</option>
              ) : (
                columns.map((col) => (
                  <option key={col.column_name} value={col.column_name}>
                    {col.column_name} ({col.data_type})
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="test-size-input">Test Size Split ({Math.round(testSize * 100)}% test / {Math.round((1 - testSize) * 100)}% train)</label>
            <input
              id="test-size-input"
              type="range"
              min="0.10"
              max="0.50"
              step="0.05"
              value={testSize}
              onChange={(e) => setTestSize(parseFloat(e.target.value))}
              className="form-range"
            />
          </div>

          <div className="form-group">
            <label htmlFor="random-state-input">Random Seed (Reproducibility)</label>
            <input
              id="random-state-input"
              type="number"
              className="form-input"
              value={randomState}
              onChange={(e) => setRandomState(parseInt(e.target.value, 10) || 42)}
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            type="submit"
            className="button primary"
            disabled={loading || !targetColumn.trim()}
          >
            {loading ? (
              <>
                <RefreshCw size={16} className="spinner" />
                Preparing dataset...
              </>
            ) : (
              <>
                <Layers3 size={16} />
                Prepare Dataset
              </>
            )}
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}
    </form>
  );
}
