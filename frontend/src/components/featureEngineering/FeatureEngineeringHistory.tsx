import { ChevronDown, ChevronUp, History } from "lucide-react";
import { useState } from "react";
import { FeatureEngineeringOperationList } from "./FeatureEngineeringOperationList";
import type { EngineeringResultResponse } from "../../types/api";

export function FeatureEngineeringHistory({ runs }: { runs: EngineeringResultResponse[] }) {
  if (!runs || runs.length === 0) {
    return null;
  }

  return (
    <div className="history-section">
      <h3 className="subheading" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <History size={18} /> Feature Engineering History ({runs.length})
      </h3>
      <div className="history-list">
        {runs.map((run) => (
          <HistoryEngineeringCard key={run.engineered_dataset_id} run={run} />
        ))}
      </div>
    </div>
  );
}

function HistoryEngineeringCard({ run }: { run: EngineeringResultResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="history-card">
      <div className="history-header">
        <div className="history-meta">
          <strong>Run #{run.engineered_dataset_id}</strong>
          <span className="status-pill">{run.engineering_status}</span>
          <span className="muted">{new Date(run.created_at).toLocaleString()}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 13 }}>
            Features Added: <strong style={{ color: "var(--teal)" }}>+{run.features_added}</strong> | Pruned: <strong>-{run.features_removed}</strong>
          </span>
          <button
            type="button"
            className="text-button"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? (
              <>
                Hide details <ChevronUp size={14} />
              </>
            ) : (
              <>
                Show operations ({run.feature_engineering_operations.length}) <ChevronDown size={14} />
              </>
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 12 }}>
          <FeatureEngineeringOperationList operations={run.feature_engineering_operations} />
        </div>
      )}
    </div>
  );
}
