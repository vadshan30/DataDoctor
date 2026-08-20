import { Lightbulb } from "lucide-react";
import type { QualityRecommendation } from "../../types/api";

export function QualityRecommendations({ recommendations }: { recommendations: QualityRecommendation[] }) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="recommendations-empty">
        <Lightbulb size={16} />
        <span>No specific recommendations. Data looks healthy.</span>
      </div>
    );
  }

  return (
    <div className="quality-recommendations">
      <div className="recommendations-list">
        {recommendations.map((rec, idx) => (
          <div className="recommendation-item" key={`${rec.issue_type}-${idx}`}>
            <div className="rec-icon">
              <Lightbulb size={16} />
            </div>
            <div className="rec-content">
              <span className="rec-source muted">{issueTypeLabel(rec.issue_type)}</span>
              <p className="rec-text">{rec.recommendation_text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function issueTypeLabel(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bOf\b/g, "of");
}
