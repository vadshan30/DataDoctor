import { useState } from "react";
import { evaluateExperiment } from "../../api/evaluation";
import { Button } from "../common/Button";

interface EvaluationActionProps {
  datasetId: number | string;
  experimentId: number | string;
  onEvaluationComplete: () => void;
  disabled?: boolean;
}

export function EvaluationAction({
  datasetId,
  experimentId,
  onEvaluationComplete,
  disabled = false,
}: EvaluationActionProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEvaluate = async () => {
    if (loading || disabled) return;

    setLoading(true);
    setError(null);

    try {
      await evaluateExperiment(datasetId, experimentId);
      onEvaluationComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="evaluation-action">
      <Button
        onClick={handleEvaluate}
        disabled={loading || disabled}
        loading={loading}
        className="evaluate-button"
      >
        {loading ? "Evaluating..." : "Evaluate Models"}
      </Button>

      {error && (
        <div className="error-message">
          <p>❌ {error}</p>
        </div>
      )}

      <div className="evaluation-info">
        <p className="muted">
          This will recompute metrics for all trained models in the experiment.
          Results will be saved and used for model comparison.
        </p>
      </div>
    </div>
  );
}