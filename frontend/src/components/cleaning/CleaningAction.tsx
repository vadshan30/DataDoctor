import { CheckCircle2, RefreshCw, ShieldCheck } from "lucide-react";
import { ErrorMessage } from "../common/States";

interface CleaningActionProps {
  onClean: () => void;
  loading: boolean;
  error?: string;
}

export function CleaningAction({ onClean, loading, error }: CleaningActionProps) {
  return (
    <div className="cleaning-action-container">
      <div className="safety-notice-banner">
        <div className="safety-icon">
          <ShieldCheck size={20} />
        </div>
        <div className="safety-content">
          <h4>Original Dataset Guarantee</h4>
          <p>
            Your original uploaded dataset will <strong>never</strong> be altered or overwritten.
            Running the cleaning pipeline creates a new versioned cleaned artifact.
          </p>
        </div>
      </div>

      <div className="action-panel">
        <div className="action-info">
          <h3>Automated Data Cleaning</h3>
          <p>
            Handles empty strings, median imputation for numeric features, mode imputation for categorical features, and removes duplicate rows.
          </p>
        </div>
        <button
          type="button"
          className="button primary"
          onClick={onClean}
          disabled={loading}
        >
          {loading ? (
            <>
              <RefreshCw size={16} className="spinner" />
              Cleaning dataset...
            </>
          ) : (
            <>
              <CheckCircle2 size={16} />
              Clean Dataset
            </>
          )}
        </button>
      </div>

      {error && <ErrorMessage message={error} />}
    </div>
  );
}
