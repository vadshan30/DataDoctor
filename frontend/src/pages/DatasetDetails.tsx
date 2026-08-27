import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Cpu,
  FlaskConical,
  Layers3,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDataset } from "../api/datasets";
import { getDatasetProfile } from "../api/profiling";
import { getDatasetQuality } from "../api/quality";
import { cleanDataset, getCleanedDatasets } from "../api/cleaning";
import { engineerFeatures, getEngineeredDatasets } from "../api/featureEngineering";
import { getPreparedDatasets, prepareMLDataset } from "../api/mlPreparation";
import { createExperiment, listExperiments } from "../api/experiments";
import {
  evaluateExperiment,
  getEvaluationSummary,
  getModelEvaluation,
  getModelComparison,
} from "../api/evaluation";
import {
  predictSingle,
  predictBatch,
  getModelPredictions,
  getExperimentPredictions,
} from "../api/prediction";
import { EmptyState, ErrorMessage, LoadingSpinner } from "../components/common/States";
import { DatasetOverview } from "../components/DatasetOverview";
import { DatasetStats } from "../components/DatasetStats";
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

type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: T };

const initialLoading = { status: "loading" as const };

type TabKey =
  | "all"
  | "profile"
  | "quality"
  | "cleaning"
  | "engineering"
  | "preparation"
  | "experiments"
  | "evaluation";

interface TabDef {
  key: TabKey;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { key: "all", label: "Overview", icon: <BarChart3 size={16} /> },
  { key: "profile", label: "Profile", icon: <BarChart3 size={16} /> },
  { key: "quality", label: "Quality", icon: <ShieldCheck size={16} /> },
  { key: "cleaning", label: "Clean", icon: <CheckCircle2 size={16} /> },
  { key: "engineering", label: "Features", icon: <Sparkles size={16} /> },
  { key: "preparation", label: "ML Prepare", icon: <Layers3 size={16} /> },
  { key: "experiments", label: "Experiments", icon: <FlaskConical size={16} /> },
  { key: "evaluation", label: "Evaluation & Predict", icon: <Cpu size={16} /> },
];

export function DatasetDetails() {
  const { datasetId } = useParams();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [datasetError, setDatasetError] = useState("");
  const [profile, setProfile] = useState<AsyncState<DatasetProfileResponse>>(initialLoading);
  const [quality, setQuality] = useState<AsyncState<DataQualityResponse>>(initialLoading);

  const [activeTab, setActiveTab] = useState<TabKey>("all");

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
      .catch((err) =>
        setProfile({ status: "error", error: err instanceof Error ? err.message : "Unable to load profile." }),
      );
    void getDatasetQuality(datasetId)
      .then((data) => setQuality({ status: "success", data }))
      .catch((err) =>
        setQuality({
          status: "error",
          error: err instanceof Error ? err.message : "Unable to load quality report.",
        }),
      );
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  const handleCleanDataset = () => {
    if (!datasetId || cleaningLoading) return;
    setCleaningLoading(true);
    setCleaningError("");
    void cleanDataset(datasetId)
      .then((result) => {
        setCleaningRun(result);
        setCleaningHistory((prev) => [result, ...prev]);
        setCleaningLoading(false)
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
        <div className="back-link-row">
          <Link className="back-link" to="/datasets">
            <ArrowLeft size={15} />Back to datasets
          </Link>
        </div>
        <section className="analysis-section">
          <h2 className="subheading" style={{ margin: 0 }}>Couldn't load this dataset</h2>
          <p className="muted" style={{ marginTop: 12 }}>{datasetError}</p>
          <div style={{ marginTop: 18, display: "flex", gap: 12 }}>
            <button type="button" className="button primary" onClick={() => { setDatasetError(""); loadDataset(); }}>
              <RefreshCw size={15} />Retry
            </button>
            <Link className="button" to="/datasets" style={{ background: "#fff", color: "var(--ink)", border: "1px solid var(--line)" }}>
              Back to datasets
            </Link>
          </div>
        </section>
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="page">
        <div className="back-link-row">
          <Link className="back-link" to="/datasets">
            <ArrowLeft size={15} />Back to datasets
          </Link>
        </div>
        <LoadingSpinner />
      </div>
    );
  }

  const columnsList = profile.status === "success" ? profile.data.columns : [];

  return (
    <div className="page">
      <div className="back-link-row">
        <Link className="back-link" to="/datasets">
          <ArrowLeft size={15} />Back to datasets
        </Link>
      </div>

      <DatasetOverview
        dataset={dataset}
        profile={profile}
        onRefresh={() => void loadAnalysis()}
        toolbarAction={
          activeTab === "all" || activeTab === "profile" ? (
            <button
              type="button"
              className="button"
              onClick={() => setActiveTab("quality")}
              style={{
                background: "#fff",
                color: "var(--teal)",
                border: "1px solid var(--teal)",
                minHeight: 32,
                padding: "6px 12px",
                fontSize: 13,
              }}
            >
              Continue to Quality →
            </button>
          ) : null
        }
      />

      <div className="workspace-tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            className={`tab-button ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* ------- Profile (also shown in Overview) ------- */}
      {activeTab === "profile" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <BarChart3 size={20} /> Data profile
            </h2>
            <button type="button" className="text-button" onClick={() => void loadAnalysis()}>
              <RefreshCw size={15} />Refresh
            </button>
          </div>
          {profile.status === "loading" && <LoadingSpinner />}
          {profile.status === "error" && <ErrorMessage message={profile.error} />}
          {profile.status === "success" && (
            <DatasetProfileContent profile={profile.data} />
          )}
          <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="button primary" onClick={() => setActiveTab("quality")}>
              Continue to Data Quality →
            </button>
          </div>
        </section>
      )}

      {/* ------- Quality (also shown in Overview) ------- */}
      {activeTab === "quality" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <ShieldCheck size={20} /> Data quality
            </h2>
            <button type="button" className="text-button" onClick={() => void loadAnalysis()}>
              <RefreshCw size={15} />Refresh
            </button>
          </div>
          {quality.status === "loading" && <LoadingSpinner />}
          {quality.status === "error" && <ErrorMessage message={quality.error} />}
          {quality.status === "success" && <QualityContent quality={quality.data} />}
          <div style={{ marginTop: 32, display: "flex", justifyContent: "flex-end" }}>
            <button type="button" className="button primary" onClick={() => setActiveTab("cleaning")}>
              Continue to Data Cleaning →
            </button>
          </div>
        </section>
      )}

      {/* ------- Cleaning ------- */}
      {activeTab === "cleaning" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <CheckCircle2 size={20} /> Data Cleaning Workspace
            </h2>
          </div>

          <CleaningAction onClean={handleCleanDataset} loading={cleaningLoading} error={cleaningError} />

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
              Continue to Feature Engineering →
            </button>
          </div>
        </section>
      )}

      {/* ------- Feature Engineering ------- */}
      {activeTab === "engineering" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <Sparkles size={20} /> Feature Engineering Workspace
            </h2>
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
              Continue to ML Preparation →
            </button>
          </div>
        </section>
      )}

      {/* ------- ML Preparation ------- */}
      {activeTab === "preparation" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <Layers3 size={20} /> ML Data Preparation Workspace
            </h2>
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
              Continue to Experiments →
            </button>
          </div>
        </section>
      )}

      {/* ------- Experiments ------- */}
      {activeTab === "experiments" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <FlaskConical size={20} /> Model Training Experiments Workspace
            </h2>
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
              Continue to Evaluation →
            </button>
          </div>
        </section>
      )}

      {/* ------- Evaluation & Prediction ------- */}
      {activeTab === "evaluation" && (
        <section className="analysis-section">
          <div className="section-toolbar">
            <h2 className="subheading" style={{ margin: 0 }}>
              <Cpu size={20} /> Evaluation & Prediction Workspace
            </h2>
          </div>

          <div className="workspace-description">
            <p>Evaluate trained models, compare performance, and make predictions.</p>
          </div>

          {experimentHistory.length > 0 ? (
            <div className="experiment-selector">
              <h3>Select Experiment</h3>
              <select
                value={experimentRun?.experiment_id.toString() ?? ""}
                onChange={(e) => {
                  const selectedExperimentId = e.target.value;
                  const selected = experimentHistory.find(
                    (exp) => exp.experiment_id.toString() === selectedExperimentId,
                  );
                  if (selected) {
                    setExperimentRun(selected);
                    setSelectedModelId(
                      selected.models.find((model) => model.status === "trained")?.model_id ?? null,
                    );
                    loadEvaluationData(selected);
                  }
                }}
                className="experiment-select"
              >
                <option value="">Select an experiment…</option>
                {experimentHistory.map((exp) => (
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

              {evaluationSummary && modelComparison && (
                <div style={{ marginTop: 32 }}>
                  <h3 className="subheading">Evaluation Results</h3>
                  <EvaluationSummary summary={evaluationSummary} />

                  <h3 className="subheading" style={{ marginTop: 18 }}>
                    Model Rankings
                  </h3>
                  <ModelRanking comparison={modelComparison} onModelSelect={setSelectedModelId} />

                  <div style={{ marginTop: 24 }}>
                    <h3 className="subheading">Model Evaluations</h3>
                    <div className="model-evaluations-grid">
                      {evaluationSummary.evaluations.map((evaluation) => (
                        <ModelEvaluationCard
                          key={evaluation.evaluation_id}
                          evaluation={evaluation}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <ReportGenerationPanel datasetId={datasetId} experimentId={experimentRun.experiment_id} />

              <div style={{ marginTop: 32 }}>
                <h3 className="subheading">Prediction History</h3>
                <PredictionHistory datasetId={datasetId} experimentId={experimentRun.experiment_id} />
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Profile + Quality sub-views                                        */
/* ------------------------------------------------------------------ */

function DatasetProfileContent({ profile }: { profile: DatasetProfileResponse }) {
  return (
    <>
      <DatasetStats profile={profile} />
      {profile.columns.length === 0 ? (
        <EmptyState
          title="No columns profiled"
          body="The dataset has no columns to profile."
        />
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

      <h3 className="subheading" style={{ margin: "24px 0 14px" }}>
        Quality issues
      </h3>
      {hasIssues ? (
        <QualityIssues issues={quality.issues} />
      ) : (
        <div className="issues-empty">
          <CheckCircle2 size={16} />
          <span>No data quality issues detected.</span>
        </div>
      )}

      <h3 className="subheading" style={{ margin: "24px 0 14px" }}>
        Recommendations
      </h3>
      <QualityRecommendations recommendations={quality.recommendations} />
    </>
  );
}
