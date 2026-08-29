import { ChevronDown, ChevronUp, FlaskConical, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { listGlobalExperiments, type GlobalExperimentFilters } from "../api/experiments";
import type { ExperimentResponse } from "../types/api";

type StatusFilter = "all" | "pending" | "running" | "completed" | "failed";

function StatusBadge({ status }: { status: string }) {
  const base = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold";
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    running: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    error: "bg-red-100 text-red-800",
  };
  return (
    <span className={`${base} ${styles[status.toLowerCase()] || "bg-gray-100 text-gray-800"}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function ProblemTypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-50 text-teal-700">
      {type.toUpperCase()}
    </span>
  );
}

function ExperimentCard({ experiment }: { experiment: ExperimentResponse }) {
  const [expanded, setExpanded] = useState(false);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const bestModelName =
    experiment.best_model_id != null && experiment.models[experiment.best_model_id]
      ? experiment.models[experiment.best_model_id].model_name
      : null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h3 className="text-base font-semibold text-gray-900 truncate">
                {experiment.name}
              </h3>
              <ProblemTypeBadge type={experiment.problem_type} />
              <StatusBadge status={experiment.status} />
            </div>
            <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
              {experiment.dataset_name && (
                <span>
                  Dataset: <span className="font-medium text-gray-700">{experiment.dataset_name}</span>
                </span>
              )}
              <span>{formatDate(experiment.created_at)}</span>
            </div>
          </div>
        </div>

        {experiment.best_metric && experiment.best_score != null && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Best Model</p>
                <p className="text-sm font-semibold text-gray-900">
                  {bestModelName || "Model selected"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{experiment.best_metric}</p>
                <p className="text-lg font-bold text-teal-700">{experiment.best_score.toFixed(4)}</p>
              </div>
            </div>
          </div>
        )}

        {experiment.error_message && (
          <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
            <p className="text-xs font-medium text-red-600 uppercase tracking-wide mb-1">Error</p>
            <p className="text-sm text-red-700 line-clamp-2">{experiment.error_message}</p>
          </div>
        )}
      </div>

      <div className="border-t border-gray-100 px-5 py-3 flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {experiment.models?.length || 0} model{experiment.models?.length !== 1 ? "s" : ""} trained
        </span>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-sm font-medium text-teal-700 hover:text-teal-800 transition-colors"
        >
          {expanded ? (
            <>
              Hide models <ChevronUp size={14} />
            </>
          ) : (
            <>
              View models <ChevronDown size={14} />
            </>
          )}
        </button>
      </div>

      {expanded && experiment.models && experiment.models.length > 0 && (
        <div className="border-t border-gray-100 p-5 bg-gray-50/50">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Trained Models</h4>
          <div className="space-y-2">
            {experiment.models.map((model, idx) => (
              <div
                key={model.model_id}
                className={`flex items-center justify-between p-3 bg-white rounded-lg border ${
                  idx === experiment.best_model_id ? "border-teal-300 bg-teal-50/30" : "border-gray-200"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-teal-100 text-teal-700 text-xs font-bold">
                    {model.algorithm.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{model.model_name}</p>
                    <p className="text-xs text-gray-500">{model.algorithm} · {model.status}</p>
                  </div>
                </div>
                {model.metrics && Object.keys(model.metrics).length > 0 && (
                  <div className="flex items-center gap-4">
                    {Object.entries(model.metrics)
                      .slice(0, 2)
                      .map(([key, value]) => (
                        <div key={key} className="text-right">
                          <p className="text-xs text-gray-500">{key}</p>
                          <p className="text-sm font-semibold text-gray-900">
                            {typeof value === "number" ? value.toFixed(4) : String(value)}
                          </p>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-white border border-gray-200 border-dashed rounded-2xl shadow-sm">
      <div className="w-16 h-16 mb-5 rounded-full bg-teal-50 flex items-center justify-center text-teal-600">
        <FlaskConical size={32} />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">No Experiments Yet</h3>
      <p className="text-gray-500 max-w-md mx-auto leading-relaxed mb-6">
        Train your first machine learning model by opening a dataset and running an experiment.
      </p>
      <a
        href="/datasets"
        className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg shadow-sm transition-colors duration-200"
      >
        Go to Datasets
      </a>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-5 bg-gray-200 rounded w-48" />
            <div className="h-5 bg-gray-100 rounded w-20" />
            <div className="h-5 bg-gray-100 rounded w-20" />
          </div>
          <div className="h-4 bg-gray-100 rounded w-64" />
        </div>
      ))}
    </div>
  );
}

export function Experiments() {
  const [experiments, setExperiments] = useState<ExperimentResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const loadExperiments = () => {
    setLoading(true);
    setError(null);

    // Always fetch the full list from the backend; do client-side filtering
    // so the UI is responsive and doesn't depend on the backend's exact
    // status matching behavior.
    const filters: GlobalExperimentFilters = {};
    if (searchQuery) filters.q = searchQuery;

    listGlobalExperiments(filters)
      .then((response) => {
        setExperiments(response.experiments);
        setTotal(response.total);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load experiments");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadExperiments();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadExperiments();
  };

  // Client-side filter: filter by status first, then by search term.
  // Both filters are case-insensitive to be robust against backend values.
  const filteredExperiments = experiments.filter((exp) => {
    const expStatus = (exp.status ?? "").toLowerCase();
    if (statusFilter !== "all" && expStatus !== statusFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const term = searchQuery.toLowerCase();
      if (!exp.name.toLowerCase().includes(term)) {
        return false;
      }
    }
    return true;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-teal-600 tracking-wider uppercase mb-1">Workspace</p>
          <h1 className="text-3xl font-bold text-gray-900">Experiments</h1>
          <p className="text-gray-500 mt-1">
            {total > 0 ? `${total} experiment${total !== 1 ? "s" : ""} across all datasets` : "Track and manage your ML experiments"}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search experiments..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition-shadow"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex gap-2">
          {(["all", "pending", "running", "completed", "failed"] as StatusFilter[]).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                statusFilter === status
                  ? "bg-teal-600 text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading && <LoadingSkeleton />}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-sm font-semibold text-red-700 mb-1">Error loading experiments</p>
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={loadExperiments}
            className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && filteredExperiments.length === 0 && <EmptyState />}

      {!loading && !error && filteredExperiments.length > 0 && (
        <div className="space-y-4">
          {filteredExperiments.map((experiment) => (
            <ExperimentCard key={experiment.experiment_id} experiment={experiment} />
          ))}
        </div>
      )}
    </div>
  );
}
