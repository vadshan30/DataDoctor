import { useState } from "react";
import { generateReport } from "../../api/reports";
import { ReportGenerationRequest } from "../../types/api";
import { Button } from "../common/Button";

interface ReportGenerationPanelProps {
  datasetId: number | string;
  experimentId?: number | string;
}

export function ReportGenerationPanel({
  datasetId,
  experimentId,
}: ReportGenerationPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [reportType, setReportType] = useState("model_performance");

  const handleGenerateReport = async () => {
    if (loading) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const request: ReportGenerationRequest = {
        dataset_id: datasetId,
        experiment_id: experimentId,
        report_type: reportType,
      };

      const result = await generateReport(request);
      setSuccess(result.message || "Report generated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="report-generation-panel card" style={{ marginTop: 24 }}>
      <div className="card-header">
        <h3 className="card-title">Generate Report</h3>
      </div>
      
      <div className="card-body">
        <p className="muted">
          Generate comprehensive PDF or HTML reports summarizing your dataset analysis, feature engineering, and model training results.
        </p>
        
        <div className="form-group" style={{ marginTop: 16 }}>
          <label htmlFor="report-type">Report Type</label>
          <select 
            id="report-type"
            className="form-select"
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
          >
            <option value="model_performance">Model Performance Report</option>
            <option value="data_quality">Data Quality & Profiling Report</option>
            <option value="full_experiment">Full Experiment Report</option>
          </select>
        </div>

        <div className="action-panel" style={{ marginTop: 16 }}>
          <Button
            onClick={handleGenerateReport}
            disabled={loading}
            loading={loading}
            className="primary"
          >
            {loading ? "Generating..." : "Generate Report"}
          </Button>
        </div>

        {error && (
          <div className="error-message" style={{ marginTop: 16 }}>
            <p>❌ {error}</p>
          </div>
        )}

        {success && (
          <div className="success-banner" style={{ marginTop: 16, padding: 12, backgroundColor: "var(--teal-light)", color: "var(--teal-dark)", borderRadius: 4 }}>
            <p>✅ {success}</p>
          </div>
        )}
      </div>
    </div>
  );
}
