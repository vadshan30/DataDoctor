import { formatPercentage } from "../../utils/helpers";
import type { DataQualityResponse } from "../../types/api";

export function QualityScoreCard({ quality }: { quality: DataQualityResponse }) {
  const score = quality.quality_score;
  const { severity, label } = scoreToSeverity(score);
  const summary = quality.summary;

  return (
    <div className="quality-score-card">
      <div className="score-gauge-container">
        <div className="score-gauge" data-severity={severity} style={{ "--score": score } as React.CSSProperties}>
          <div className="score-ring-inner">
            <span className="score-value">{score}</span>
            <span className="score-max">/ 100</span>
          </div>
        </div>
        <span className={`severity-badge severity-${severity}`}>{label}</span>
      </div>
      <div>
        <p className="score-explanation">{scoreExplanation(severity, summary)}</p>
        <div className="quality-summary-grid">
          <SummaryItem label="Missing" value={formatPercentage(summary.missing_percentage)} />
          <SummaryItem label="Duplicates" value={formatPercentage(summary.duplicate_percentage)} />
          <SummaryItem label="Constant" value={String(summary.constant_columns)} />
          <SummaryItem label="High cardinality" value={String(summary.high_cardinality_columns)} />
          <SummaryItem label="Outlier columns" value={String(summary.outlier_columns)} />
          <SummaryItem label="Identifiers" value={String(summary.potential_identifiers)} />
        </div>
      </div>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="summary-item">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function scoreToSeverity(score: number): { severity: "high" | "medium" | "low"; label: string } {
  if (score >= 80) return { severity: "low", label: "Good" };
  if (score >= 50) return { severity: "medium", label: "Needs attention" };
  return { severity: "high", label: "Poor" };
}

function scoreExplanation(
  severity: "high" | "medium" | "low",
  summary: DataQualityResponse["summary"]
): string {
  if (severity === "low") {
    return `Dataset is in good shape (${summary.duplicate_percentage}% duplicates, ${formatPercentage(summary.missing_percentage)} missing).`;
  }
  if (severity === "medium") {
    return `Dataset needs some cleanup before modeling. ${summary.constant_columns} constant or suspicious column(s) detected.`;
  }
  return "Dataset has significant quality issues. Review the detected issues before use.";
}
