import { ChevronDown, ChevronUp, History } from "lucide-react";
import { useState } from "react";
import { formatNumber } from "../../utils/helpers";
import { CleaningOperationList } from "./CleaningOperationList";
import type { CleaningResultResponse } from "../../types/api";

export function CleaningHistory({ runs }: { runs: CleaningResultResponse[] }) {
  if (!runs || runs.length === 0) {
    return null;
  }

  return (
    <div className="history-section">
      <h3 className="subheading" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <History size={18} /> Cleaning Run History ({runs.length})
      </h3>
      <div className="history-list">
        {runs.map((run) => (
          <HistoryRunCard key={run.cleaned_dataset_id} run={run} />
        ))}
      </div>
    </div>
  );
}

function HistoryRunCard({ run }: { run: CleaningResultResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="history-card">
      <div className="history-header">
        <div className="history-meta">
          <strong>Run #{run.cleaned_dataset_id}</strong>
          <span className="status-pill">{run.cleaning_status}</span>
          <span className="muted">{new Date(run.created_at).toLocaleString()}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 13 }}>
            Rows: <strong>{formatNumber(run.rows_before, 0)}</strong> → <strong>{formatNumber(run.rows_after, 0)}</strong>
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
                Show operations ({run.cleaning_operations.length}) <ChevronDown size={14} />
              </>
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 12 }}>
          <CleaningOperationList operations={run.cleaning_operations} />
        </div>
      )}
    </div>
  );
}
