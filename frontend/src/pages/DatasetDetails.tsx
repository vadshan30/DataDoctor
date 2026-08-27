import { ArrowLeft, BarChart3, CheckCircle2, Cpu, FileText, FlaskConical, Layers3, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDataset } from "../api/datasets";
import { getDatasetProfile } from "../api/profiling";
import { getDatasetQuality } from "../api/quality";
import { cleanDataset, getCleanedDatasets } from "../api/cleaning";
import { engineerFeatures, getEngineeredDatasets } from "../api/featureEngineering";
import { getPreparedDatasets, prepareMLDataset } from "../api/mlPreparation";
import { createExperiment, listExperiments } from "../api/experiments";
import { evaluateExperiment, getEvaluationSummary, getModelEvaluation, getModelComparison } from "../api/evaluation";
import { predictSingle, predictBatch, getModelPredictions, getExperimentPredictions } from "../api/prediction";
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
import { PreparationForm } from "../components/mlPreparation/PreparationForm";
import { PreparationSummary } from "../components/mlPreparation/PreparationSummary";
import { PreparationOperations } from "../components/mlPreparation/PreparationOperations";
import { PreparationHistory } from "../components/mlPreparation/PreparationHistory";
import { ExperimentForm } from "../components/experiments/ExperimentForm";
import { ExperimentSummary } from "../components/experiments/ExperimentSummary";
import { ModelComparison } from "../components/experiments/ModelComparison";
import { ExperimentHistory } from "../components/experiments/ExperimentHistory";
import { EvaluationAction } from "../components/evaluation/EvaluationAction";
import { EvaluationSummary } from "../components/evaluation/EvaluationSummary";
import { ModelEvaluationCard } from "../components/evaluation/ModelEvaluationCard";
import { ModelRanking } from "../components/evaluation/ModelRanking";
import { PredictionPanel } from "../components/prediction/PredictionPanel";
import { PredictionResult } from "../components/prediction/PredictionResult";
import { BatchPredictionPanel } from "../components/prediction/BatchPredictionPanel";
import { PredictionHistory } from "../components/prediction/PredictionHistory";
import { ReportGenerationPanel } from "../components/reports/ReportGenerationPanel";
import { formatBytes, formatNumber } from "../utils/helpers";
import type {
  CleaningResultResponse,
  Dataset,
  DatasetProfileResponse,
  DataQualityResponse,
  EngineeringResultResponse,
  ExperimentCreateRequest,
  ExperimentResponse,
  MLReadyDatasetResponse,
  PrepareRequest,
  EvaluationSummaryResponse,
  ModelComparisonResponse,
  ModelEvaluationResponse,
} from "../types/api";

type AsyncState<T> = { status: "loading" } | { status: "error"; error: string } | { status: "success"; data: T };

const initialLoading = { status: "loading" as const };

export function DatasetDetails() {
  const { datasetId } = useParams();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [datasetError, setDatasetError] = useState("");
  const [profile, setProfile] = useState<AsyncState<DatasetProfileResponse>>(initialLoading);
  const [quality, setQuality] = useState<AsyncState<DataQualityResponse>>(initialLoading);

  const [activeTab, setActiveTab] = useState<
    "all" | "profile" | "quality" | "cleaning" | "engineering" | "preparation" | "experiments" | "evaluation"
  >("all");

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

  // ML Preparation state
  const [preparedRun, setPreparedRun] = useState<MLReadyDatasetResponse | null>(null);
  const [preparedHistory, setPreparedHistory] = useState<MLReadyDatasetResponse[]>([]);
  const [prepLoading, setPrepLoading] = useState(false);
  const [prepError, setPrepError] = useState("");

  // Experiments / Model Training state
  const [experimentRun, setExperimentRun] = useState<ExperimentResponse | null>(null);
  const [experimentHistory, setExperimentHistory] = useState<ExperimentResponse[]>([]);
  const [expLoading, setExpLoading] = useState(false);
  const [expError, setExpError] = useState("");
  const [evaluationSummary, setEvaluationSummary] = useState<EvaluationSummaryResponse | null>(null);
  const [modelComparison, setModelComparison] = useState<ModelComparisonResponse | null>(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [evaluationError, setEvaluationError] = useState("");
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);

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
      .catch(() => {});
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
      .catch(() => {});
  };

  const loadPreparedHistory = () => {
    if (!datasetId) return;
    void getPreparedDatasets(datasetId)
      .then((res) => {
        setPreparedHistory(res.prepared_datasets);
        if (res.prepared_datasets.length > 0 && !preparedRun) {
          setPreparedRun(res.prepared_datasets[0]);
        }
      })
      .catch(() => {});
  };

  const loadExperimentHistory = () => {
    if (!datasetId) return;
    void listExperiments(datasetId)
      .then((res) => {
        setExperimentHistory(res.experiments);
        if (res.experiments.length > 0 && !experimentRun) {
          setExperimentRun(res.experiments[0]);
        }
      })
      .catch(() => {});
  };

  const loadEvaluationData = (experiment: ExperimentResponse) => {
    if (!datasetId) return;
    setEvaluationLoading(true);
    setEvaluationError("");
    void Promise.all([
      getEvaluationSummary(datasetId, experiment.experiment_id),
      getModelComparison(datasetId, experiment.experiment_id),
    ])
      .then(([summary, comparison]) => {
        setEvaluationSummary(summary);
        setModelComparison(comparison);
        setSelectedModelId(comparison.ranked_models[0]?.model_id ?? null);
      })
      .catch((err) => {
        setEvaluationSummary(null);
        setModelComparison(null);
        setEvaluationError(err instanceof Error ? err.message : "Evaluation results are not available yet.");
      })
      .finally(() => setEvaluationLoading(false));
  };

  useEffect(() => {
    loadDataset();
    loadAnalysis();
    loadCleaningHistory();
    loadEngineeringHistory();
    loadPreparedHistory();
    loadExperimentHistory();
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

  const handlePrepareMLDataset = (req: PrepareRequest) => {
    if (!datasetId || prepLoading) return;
    setPrepLoading(true);
    setPrepError("");
    void prepareMLDataset(datasetId, req)
      .then((result) => {
        setPreparedRun(result);
        setPreparedHistory((prev) => [result, ...prev]);
        setPrepLoading(false);
      })
      .catch((err) => {
        setPrepError(err instanceof Error ? err.message : "ML preparation failed.");
        setPrepLoading(false);
      });
  };

  const handleTrainExperiment = (req: ExperimentCreateRequest) => {
    if (!datasetId || expLoading) return;
    setExpLoading(true);
    setExpError("");
    void createExperiment(datasetId, req)
      .then((result) => {
        setExperimentRun(result);
        setExperimentHistory((prev) => [result, ...prev]);
        setExpLoading(false);
      })
      .catch((err) => {
        setExpError(err instanceof Error ? err.message : "Experiment training failed.");
        setExpLoading(false);
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

  const columnsList = profile.status === "success" ? profile.data.columns : [];

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
        <button
          type="button"
          className={`tab-button ${activeTab === "preparation" ? "active" : ""}`}
          onClick={() => setActiveTab("preparation")}
        >
          <Layers3 size={16} />
          ML Preparation
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === "experiments" ? "active" : ""}`}
          onClick={() => setActiveTab("experiments")}
        >
          <FlaskConical size={16} />
          Experiments
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === "evaluation" ? "active" : ""}`}
          onClick={() => setActiveTab("evaluation")}
        >
          <Cpu size={16} />
          Evaluation & Prediction
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
            <>
              <ProfileContent profile={profile.data} />
              <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
                <button type="button" className="button primary" onClick={() => setActiveTab("quality")}>
                  Continue to Data Quality &rarr;
                </button>
              </div>
            </>
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
            <>
              <QualityContent quality={quality.data} />
              <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
                <button type="button" className="button primary" onClick={() => setActiveTab("cleaning")}>
                  Continue to Data Cleaning &rarr;
                </button>
              </div>
            </>
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

          <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="button primary" onClick={() => setActiveTab("engineering")}>
              Continue to Feature Engineering &rarr;
            </button>
          </div>
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

          <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="button primary" onClick={() => setActiveTab("preparation")}>
              Continue to ML Preparation &rarr;
            </button>
          </div>
        </section>
      )}

      {activeTab === "preparation" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><Layers3 size={20} /> ML Data Preparation Workspace</h2>
          </div>

          <PreparationForm
            columns={columnsList}
            onPrepare={handlePrepareMLDataset}
            loading={prepLoading}
            error={prepError}
          />

          {preparedRun && (
            <div style={{ marginTop: 24 }}>
              <PreparationSummary result={preparedRun} />
              <h3 className="subheading" style={{ margin: "24px 0 12px" }}>
                Preprocessing Operations ({preparedRun.preprocessing_operations.length})
              </h3>
              <PreparationOperations operations={preparedRun.preprocessing_operations} />
            </div>
          )}

          <PreparationHistory runs={preparedHistory} />

          <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="button primary" onClick={() => setActiveTab("experiments")}>
              Continue to Experiments &rarr;
            </button>
          </div>
        </section>
      )}

      {activeTab === "experiments" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><FlaskConical size={20} /> Model Training Experiments Workspace</h2>
          </div>

          <ExperimentForm
            preparedRuns={preparedHistory}
            onTrain={handleTrainExperiment}
            loading={expLoading}
            error={expError}
          />

          {experimentRun && (
            <div style={{ marginTop: 24 }}>
              <ExperimentSummary experiment={experimentRun} />
              <ModelComparison
                models={experimentRun.models}
                bestModelId={experimentRun.best_model_id}
                problemType={experimentRun.problem_type}
              />
            </div>
          )}

          <ExperimentHistory experiments={experimentHistory} />

          <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="button primary" onClick={() => setActiveTab("evaluation")}>
              Continue to Evaluation &rarr;
            </button>
          </div>
        </section>
      )}

      {activeTab === "evaluation" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}><Cpu size={20} /> Evaluation & Prediction Workspace</h2>
          </div>

          <div className="workspace-description">
            <p>Evaluate trained models, compare performance, and make predictions.</p>
          </div>

          {experimentHistory.length > 0 ? (
            <div className="experiment-selector">
              <h3>Select Experiment</h3>
              <select
                onChange={(e) => {
                  const selectedExperimentId = e.target.value;
                  const selected = experimentHistory.find(exp => exp.experiment_id.toString() === selectedExperimentId);
                  if (selected) {
                    setExperimentRun(selected);
                    setSelectedModelId(selected.models.find((model) => model.status === "trained")?.model_id ?? null);
                    loadEvaluationData(selected);
                  }
                }}
                className="experiment-select"
              >
                <option value="">Select an experiment...</option>
                {experimentHistory.map(exp => (
                  <option key={exp.experiment_id} value={exp.experiment_id.toString()}>
                    {exp.name} ({exp.problem_type})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <EmptyState
              title="No Experiments Available"
              body="Create an experiment first to access evaluation and prediction features."
            />
          )}

          {experimentRun && datasetId && (
            <div style={{ marginTop: 24 }}>
              <EvaluationAction
                datasetId={datasetId}
                experimentId={experimentRun.experiment_id}
                onEvaluationComplete={() => {
                  loadEvaluationData(experimentRun);
                }}
                disabled={expLoading}
              />

              {evaluationLoading && <LoadingSpinner />}
              {evaluationError && <ErrorMessage message={evaluationError} />}

              {selectedModelId !== null && (
                <PredictionPanel
                  datasetId={datasetId}
                  experimentId={experimentRun.experiment_id}
                  modelId={selectedModelId}
                />
              )}

              {selectedModelId !== null && (
                <BatchPredictionPanel
                  datasetId={datasetId}
                  experimentId={experimentRun.experiment_id}
                  modelId={selectedModelId}
                />
              )}

              {evaluationSummary && modelComparison && <div style={{ marginTop: 32 }}>
                <h3>Evaluation Results</h3>
                <EvaluationSummary summary={evaluationSummary} />

                <h3>Model Rankings</h3>
                <ModelRanking
                  comparison={modelComparison}
                  onModelSelect={setSelectedModelId}
                />

                <div style={{ marginTop: 32 }}>
                <h3>Model Evaluations</h3>
                <div className="model-evaluations-grid">
                  {evaluationSummary.evaluations.map((evaluation) => (
                    <ModelEvaluationCard
                      key={evaluation.evaluation_id}
                      evaluation={evaluation}
                    />
                  ))}
                </div>
                </div>
              </div>}

              <ReportGenerationPanel datasetId={datasetId} experimentId={experimentRun.experiment_id} />

              <div style={{ marginTop: 32 }}>
                <h3>Prediction History</h3>
                <PredictionHistory
                  datasetId={datasetId}
                  experimentId={experimentRun.experiment_id}
                />
              </div>
            </div>
          )}
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

