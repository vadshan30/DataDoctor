import { AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { formatPercentage } from "../../utils/helpers";
import type { QualityIssue, QualitySeverity } from "../../types/api";

const SEVERITY_ORDER: QualitySeverity[] = ["high", "medium", "low"];

const SEVERITY_LABEL: Record<QualitySeverity, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function QualityIssues({ issues }: { issues: QualityIssue[] }) {
  if (!issues || issues.length === 0) {
    return (
      <div className="issues-empty">
        <AlertCircle size={16} />
        <span>No data quality issues detected.</span>
      </div>
    );
  }

  const sorted = [...issues].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
  );

  const counts = SEVERITY_ORDER.reduce<Record<QualitySeverity, number>>(
    (acc, sev) => {
      acc[sev] = sorted.filter((i) => i.severity === sev).length;
      return acc;
    },
    { high: 0, medium: 0, low: 0 }
  );

  return (
    <div className="quality-issues">
      <div className="severity-legend">
        <SeverityDot severity="high" label={`High (${counts.high})`} />
        <SeverityDot severity="medium" label={`Medium (${counts.medium})`} />
        <SeverityDot severity="low" label={`Low (${counts.low})`} />
      </div>
      <div className="issues-list">
        {sorted.map((issue, idx) => (
          <IssueItem key={`${issue.issue_type}-${issue.column_name ?? "x"}-${idx}`} issue={issue} />
        ))}
      </div>
    </div>
  );
}

function SeverityDot({ severity, label }: { severity: QualitySeverity; label: string }) {
  return (
    <span className={`severity-dot severity-${severity}`}>
      <span className="dot" />
      <span className="muted">{label}</span>
    </span>
  );
}

function IssueItem({ issue }: { issue: QualityIssue }) {
  const [open, setOpen] = useState(issue.severity === "high");

  const columnLabel = issue.column_name ? (
    <strong className="issue-column">{issue.column_name}</strong>
  ) : null;

  return (
    <div className={`issue-item issue-${issue.severity}`}>
      <div className="issue-head" onClick={() => setOpen((v) => !v)}>
        <span className={`severity-badge severity-${issue.severity}`}>{SEVERITY_LABEL[issue.severity]}</span>
        <span className="issue-type">{issueTypeLabel(issue.issue_type)}</span>
        {columnLabel}
        <button
          type="button"
          className="text-button"
          style={{ marginLeft: "auto" }}
          onClick={(e) => {
            e.stopPropagation();
            setOpen((v) => !v);
          }}
          aria-label="Toggle issue"
        >
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>
      {open && (
        <div className="issue-detail">
          <p className="issue-description">{issue.description}</p>
          {issue.metric_value != null && (
            <span className="issue-metric">Value: {formatMetric(issue.metric_value)}</span>
          )}
        </div>
      )}
    </div>
  );
}

function issueTypeLabel(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bOf\b/g, "of");
}

function formatMetric(value: number | string): string {
  if (typeof value === "number") {
    if (value <= 1 && value >= 0) return formatPercentage(value * 100);
    return formatPercentage(value);
  }
  return String(value);
}
