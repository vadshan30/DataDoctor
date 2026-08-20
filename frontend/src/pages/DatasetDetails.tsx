import { ArrowLeft, BarChart3, CheckCircle2, FileText, FlaskConical, Layers3, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDataset } from "../api/datasets";
import { getDatasetProfile } from "../api/profiling";
import { getDatasetQuality } from "../api/quality";
import { cleanDataset, getCleanedDatasets } from "../api/cleaning";
import { engineerFeatures, getEngineeredDatasets } from "../api/featureEngineering";
import { EmptyState, ErrorMessage, LoadingSpinner } from "../components/common/States";
import { ColumnProfileTable } from "../components/profiling/ColumnProfileTable";
import { QualityScoreCard } from "../components/quality/QualityScoreCard";
import { QualityIssues } from "../components/quality/QualityIssues";
import { QualityRecommendations } from "../components/quality/QualityRecommendations";
import { CleaningAction } from "../components/cleaning/CleaningAction";
import { CleaningSummary } from "../components/cleaning/CleaningSummary";
import { CleaningOperationList } from "../components/cleaning/CleaningOperationList";
import { CleaningHistory } from "../components/cleaning/CleaningHistory";
import { FeatureOperationSelector } from "../components/featureEngineering/FeatureOperationSelector";
import { FeatureEngineeringSummary } from "../components/featureEngineering/FeatureEngineeringSummary";
import { FeatureEngineeringOperationList } from "../components/featureEngineering/FeatureEngineeringOperationList";
import { FeatureEngineeringHistory } from "../components/featureEngineering/FeatureEngineeringHistory";
import { formatBytes, formatNumber } from "../utils/helpers";
import type {
  CleaningResultResponse,
  Dataset,
  DatasetProfileResponse,
  DataQualityResponse,
  EngineeringResultResponse,
} from "../types/api";

type AsyncState<T> = { status: "loading" } | { status: "error"; error: string } | { status: "success"; data: T };

const initialLoading = { status: "loading" as const };

export function DatasetDetails() {
  const { datasetId } = useParams();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [datasetError, setDatasetError] = useState("");
  const [profile, setProfile] = useState<AsyncState<DatasetProfileResponse>>(initialLoading);
  const [quality, setQuality] = useState<AsyncState<DataQualityResponse>>(initialLoading);

  const [activeTab, setActiveTab] = useState<"all" | "profile" | "quality" | "cleaning" | "engineering">("all");

  // Data Cleaning state
  const [cleaningRun, setCleaningRun] = useState<CleaningResultResponse | null>(null);
  const [cleaningHistory, setCleaningHistory] = useState<CleaningResultResponse[]>([]);
  const [cleaningLoading, setCleaningLoading] = useState(false);
  const [cleaningError, setCleaningError] = useState("");

  // Feature Engineering state
  const [engineeringRun, setEngineeringRun] = useState<EngineeringResultResponse | null>(null);
  const [engineeringHistory, setEngineeringHistory] = useState<EngineeringResultResponse[]>([]);
  const [engineeringLoading, setEngineeringLoading] = useState(false);
  const [engineeringError, setEngineeringError] = useState("");

  const loadDataset = () => {
    if (!datasetId) return;
    void getDataset(datasetId)
      .then(setDataset)
      .catch((err) => setDatasetError(err instanceof Error ? err.message : "Unable to load dataset."));
  };

  const loadAnalysis = () => {
    if (!datasetId) return;
    setProfile({ status: "loading" });
    setQuality({ status: "loading" });
    void getDatasetProfile(datasetId)
      .then((data) => setProfile({ status: "success", data }))
      .catch((err) => setProfile({ status: "error", error: err instanceof Error ? err.message : "Unable to load profile." }));
    void getDatasetQuality(datasetId)
      .then((data) => setQuality({ status: "success", data }))
      .catch((err) => setQuality({ status: "error", error: err instanceof Error ? err.message : "Unable to load quality report." }));
  };

  const loadCleaningHistory = () => {
    if (!datasetId) return;
    void getCleanedDatasets(datasetId)
      .then((res) => {
        setCleaningHistory(res.cleaned_datasets);
        if (res.cleaned_datasets.length > 0 && !cleaningRun) {
          setCleaningRun(res.cleaned_datasets[0]);
        }
      })
      .catch(() => {
        // Silently handle list fetch fallback
      });
  };

  const loadEngineeringHistory = () => {
    if (!datasetId) return;
    void getEngineeredDatasets(datasetId)
      .then((res) => {
        setEngineeringHistory(res.engineered_datasets);
        if (res.engineered_datasets.length > 0 && !engineeringRun) {
          setEngineeringRun(res.engineered_datasets[0]);
        }
      })
      .catch(() => {
        // Silently handle list fetch fallback
      });
  };

  useEffect(() => {
    loadDataset();
    loadAnalysis();
    loadCleaningHistory();
    loadEngineeringHistory();
  }, [datasetId]);

  const handleCleanDataset = () => {
    if (!datasetId || cleaningLoading) return;
    setCleaningLoading(true);
    setCleaningError("");
    void cleanDataset(datasetId)
      .then((result) => {
        setCleaningRun(result);
        setCleaningHistory((prev) => [result, ...prev]);
        setCleaningLoading(false);
      })
      .catch((err) => {
        setCleaningError(err instanceof Error ? err.message : "Cleaning failed.");
        setCleaningLoading(false);
      });
  };

  const handleEngineerFeatures = () => {
    if (!datasetId || engineeringLoading) return;
    setEngineeringLoading(true);
    setEngineeringError("");
    void engineerFeatures(datasetId)
      .then((result) => {
        setEngineeringRun(result);
        setEngineeringHistory((prev) => [result, ...prev]);
        setEngineeringLoading(false);
      })
      .catch((err) => {
        setEngineeringError(err instanceof Error ? err.message : "Feature engineering failed.");
        setEngineeringLoading(false);
      });
  };

  if (datasetError) {
    return (
      <div className="page">
        <Link className="back-link" to="/datasets"><ArrowLeft size={15} />Back to datasets</Link>
        <ErrorMessage message={datasetError} />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="page">
        <Link className="back-link" to="/datasets"><ArrowLeft size={15} />Back to datasets</Link>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="page">
      <Link className="back-link" to="/datasets"><ArrowLeft size={15} />Back to datasets</Link>

      <div className="detail-heading">
        <div>
          <p className="eyebrow">Dataset #{dataset.dataset_id}</p>
          <h1>{dataset.name}</h1>
          <p className="muted">{dataset.description || "No description provided."}</p>
        </div>
        <span className="status-pill large">{dataset.status}</span>
      </div>

      <div className="detail-stats">
        <div><span>Rows</span><strong>{dataset.row_count.toLocaleString()}</strong></div>
        <div><span>Columns</span><strong>{dataset.column_count}</strong></div>
        <div><span>Format</span><strong>{dataset.file_type.toUpperCase()}</strong></div>
        <div><span>Version</span><strong>v{dataset.version}</strong></div>
      </div>

      <div className="workspace-tabs">
        <button
          type="button"
          className={`tab-button ${activeTab === "all" ? "active" : ""}`}
          onClick={() => setActiveTab("all")}
        >
          Overview & Analysis
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === "profile" ? "active" : ""}`}
          onClick={() => setActiveTab("profile")}
        >
          <BarChart3 size={16} />
          Data Profile
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === "quality" ? "active" : ""}`}
          onClick={() => setActiveTab("quality")}
        >
          <ShieldCheck size={16} />
          Data Quality
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === "cleaning" ? "active" : ""}`}
          onClick={() => setActiveTab("cleaning")}
        >
          <CheckCircle2 size={16} />
          Data Cleaning
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === "engineering" ? "active" : ""}`}
          onClick={() => setActiveTab("engineering")}
        >
          <Sparkles size={16} />
          Feature Engineering
        </button>
      </div>

      {(activeTab === "all" || activeTab === "profile") && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><BarChart3 size={20} /> Data profile</h2>
            <button type="button" className="text-button" onClick={() => void loadAnalysis()}>
              <RefreshCw size={15} />Refresh
            </button>
          </div>
          {profile.status === "loading" && <LoadingSpinner />}
          {profile.status === "error" && <ErrorMessage message={profile.error} />}
          {profile.status === "success" && (
            <ProfileContent profile={profile.data} />
          )}
        </section>
      )}

      {(activeTab === "all" || activeTab === "quality") && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><ShieldCheck size={20} /> Data quality</h2>
            <button type="button" className="text-button" onClick={() => void loadAnalysis()}>
              <RefreshCw size={15} />Refresh
            </button>
          </div>
          {quality.status === "loading" && <LoadingSpinner />}
          {quality.status === "error" && <ErrorMessage message={quality.error} />}
          {quality.status === "success" && (
            <QualityContent quality={quality.data} />
          )}
        </section>
      )}

      {activeTab === "cleaning" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><CheckCircle2 size={20} /> Data Cleaning Workspace</h2>
          </div>

          <CleaningAction
            onClean={handleCleanDataset}
            loading={cleaningLoading}
            error={cleaningError}
          />

          {cleaningRun && (
            <div style={{ marginTop: 24 }}>
              <CleaningSummary result={cleaningRun} />
              <h3 className="subheading" style={{ margin: "24px 0 12px" }}>
                Cleaning Operations Performed ({cleaningRun.cleaning_operations.length})
              </h3>
              <CleaningOperationList operations={cleaningRun.cleaning_operations} />
            </div>
          )}

          <CleaningHistory runs={cleaningHistory} />
        </section>
      )}

      {activeTab === "engineering" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><Sparkles size={20} /> Feature Engineering Workspace</h2>
          </div>

          <FeatureOperationSelector
            onEngineer={handleEngineerFeatures}
            loading={engineeringLoading}
            error={engineeringError}
          />

          {engineeringRun && (
            <div style={{ marginTop: 24 }}>
              <FeatureEngineeringSummary result={engineeringRun} />
              <h3 className="subheading" style={{ margin: "24px 0 12px" }}>
                Engineering Operations Performed ({engineeringRun.feature_engineering_operations.length})
              </h3>
              <FeatureEngineeringOperationList operations={engineeringRun.feature_engineering_operations} />
            </div>
          )}

          <FeatureEngineeringHistory runs={engineeringHistory} />
        </section>
      )}
    </div>
  );
}

function ProfileContent({ profile }: { profile: DatasetProfileResponse }) {
  const totalIssues = profile.duplicate_row_count;
  const totalMissing = profile.columns.reduce((sum, c) => sum + c.null_count, 0);

  return (
    <>
      <div className="metric-grid">
        <div className="metric-card">
          <span>Rows</span>
          <strong>{formatNumber(profile.row_count, 0)}</strong>
        </div>
        <div className="metric-card">
          <span>Columns</span>
          <strong>{formatNumber(profile.column_count, 0)}</strong>
        </div>
        <div className="metric-card accent">
          <span>Dataset size</span>
          <strong>{formatBytes(profile.memory_usage)}</strong>
        </div>
        <div className="metric-card">
          <span>Numeric columns</span>
          <strong>{profile.numerical_column_count}</strong>
        </div>
        <div className="metric-card">
          <span>Categorical columns</span>
          <strong>{profile.categorical_column_count}</strong>
        </div>
        <div className="metric-card">
          <span>Datetime columns</span>
          <strong>{profile.datetime_column_count}</strong>
        </div>
        <div className="metric-card">
          <span>Boolean columns</span>
          <strong>{profile.boolean_column_count}</strong>
        </div>
        <div className="metric-card">
          <span>Missing values</span>
          <strong>{formatNumber(totalMissing, 0)}</strong>
        </div>
        <div className="metric-card">
          <span>Duplicate rows</span>
          <strong>{formatNumber(totalIssues, 0)}</strong>
        </div>
      </div>

      {profile.columns.length === 0 ? (
        <EmptyState title="No columns profiled" body="The dataset has no columns to profile." />
      ) : (
        <ColumnProfileTable columns={profile.columns} />
      )}
    </>
  );
}

function QualityContent({ quality }: { quality: DataQualityResponse }) {
  const hasIssues = quality.issues.length > 0;

  return (
    <>
      <QualityScoreCard quality={quality} />

      <h3 className="quality-subheading">Quality issues</h3>
      {hasIssues ? (
        <QualityIssues issues={quality.issues} />
      ) : (
        <div className="issues-empty">
          <CheckCircle2 size={16} />
          <span>No data quality issues detected.</span>
        </div>
      )}

      <h3 className="quality-subheading">Recommendations</h3>
      <QualityRecommendations recommendations={quality.recommendations} />
    </>
  );
}

