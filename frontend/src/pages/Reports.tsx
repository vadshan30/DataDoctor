import { Download, FileText, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { listGlobalReports, type GlobalReportFilters } from "../api/reports";
import type { ReportResponse } from "../types/api";

type ReportTypeFilter = "all" | "dataset" | "experiment";

function StatusBadge({ status }: { status: string }) {
  const base = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold";
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    generating: "bg-blue-100 text-blue-800",
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

function ReportTypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
      {type.charAt(0).toUpperCase() + type.slice(1)} Report
    </span>
  );
}

function ReportCard({ report }: { report: ReportResponse }) {
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

  const handleDownload = async () => {
    try {
      const response = await fetch(`/api/v1/reports/${report.report_id}/download`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("datadoctor_token")}`,
        },
      });

      if (!response.ok) {
        throw new Error("Download failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report.name || `report_${report.report_id}`}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Download failed:", err);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-xl bg-teal-50 text-teal-600">
              <FileText size={24} />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-gray-900">
                {report.name || `${report.report_type} Report`}
              </h3>
              <div className="mt-1 flex items-center gap-3 flex-wrap">
                <ReportTypeBadge type={report.report_type} />
                <StatusBadge status={report.status} />
              </div>
            </div>
          </div>

          {report.status === "completed" && (
            <button
              type="button"
              onClick={handleDownload}
              className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Download size={16} />
              Download
            </button>
          )}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          {report.dataset_name && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Dataset</p>
              <p className="mt-0.5 text-gray-900 font-medium truncate">{report.dataset_name}</p>
            </div>
          )}
          {report.experiment_name && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Experiment</p>
              <p className="mt-0.5 text-gray-900 font-medium truncate">{report.experiment_name}</p>
            </div>
          )}
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Created</p>
            <p className="mt-0.5 text-gray-700">{formatDate(report.created_at)}</p>
          </div>
          {report.error_message && (
            <div className="col-span-2">
              <p className="text-xs font-medium text-red-500 uppercase tracking-wide">Error</p>
              <p className="mt-0.5 text-sm text-red-700 line-clamp-2">{report.error_message}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-white border border-gray-200 border-dashed rounded-2xl shadow-sm">
      <div className="w-16 h-16 mb-5 rounded-full bg-teal-50 flex items-center justify-center text-teal-600">
        <FileText size={32} />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">No Reports Yet</h3>
      <p className="text-gray-500 max-w-md mx-auto leading-relaxed mb-6">
        Generate reports from the evaluation workspace of a dataset to see them here.
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
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-gray-200 rounded-xl" />
            <div className="flex-1">
              <div className="h-5 bg-gray-200 rounded w-48 mb-2" />
              <div className="flex gap-2">
                <div className="h-5 bg-gray-100 rounded w-24" />
                <div className="h-5 bg-gray-100 rounded w-24" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function Reports() {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<ReportTypeFilter>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const loadReports = () => {
    setLoading(true);
    setError(null);

    const filters: GlobalReportFilters = {};
    if (typeFilter !== "all") filters.report_type = typeFilter;
    if (statusFilter !== "all") filters.status = statusFilter;

    listGlobalReports(filters)
      .then((response) => {
        setReports(response.reports);
        setTotal(response.total);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load reports");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadReports();
  }, []);

  const filteredReports = reports;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-teal-600 tracking-wider uppercase mb-1">Workspace</p>
          <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500 mt-1">
            {total > 0 ? `${total} report${total !== 1 ? "s" : ""} across all datasets` : "View insights and generated reports"}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex gap-2">
          {(["all", "dataset", "experiment"] as ReportTypeFilter[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => {
                setTypeFilter(type);
                setTimeout(loadReports, 0);
              }}
              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                typeFilter === type
                  ? "bg-teal-600 text-white"
                  : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          {(["all", "pending", "completed", "failed"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => {
                setStatusFilter(status);
                setTimeout(loadReports, 0);
              }}
              className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                statusFilter === status
                  ? "bg-gray-800 text-white"
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
          <p className="text-sm font-semibold text-red-700 mb-1">Error loading reports</p>
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={loadReports}
            className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && filteredReports.length === 0 && <EmptyState />}

      {!loading && !error && filteredReports.length > 0 && (
        <div className="space-y-4">
          {filteredReports.map((report) => (
            <ReportCard key={report.report_id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
}
