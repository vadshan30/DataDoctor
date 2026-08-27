import { CheckCircle2, RefreshCw, Upload, Database } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDatasets } from "../api/datasets";
import { FileUpload } from "../components/FileUpload";
import { ErrorMessage, LoadingSpinner } from "../components/common/States";
import { useAuth } from "../contexts/AuthContext";
import type { Dataset } from "../types/api";

function isGuestSession(email: string | undefined): boolean {
  return !!email && email.startsWith("guest-");
}

export function Datasets() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const { session } = useAuth();
  const guest = isGuestSession(session?.email);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setDatasets((await listDatasets()).datasets);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load datasets.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(""), 4000);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-teal-600 tracking-wider uppercase mb-1">
            Workspace library
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-bold text-gray-900">Datasets</h1>
            {guest && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-amber-800 bg-amber-50 border border-amber-200 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                Guest session
              </span>
            )}
          </div>
          <p className="text-gray-500 mt-1">
            Your owned sources and their current preparation status.
          </p>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-teal-700 hover:bg-teal-800 text-white font-semibold rounded-xl shadow-sm transition-all hover:shadow-md disabled:opacity-60"
          onClick={() => setUploading(true)}
          disabled={loading && datasets.length === 0}
        >
          <Upload size={18} />
          Upload dataset
        </button>
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between gap-3 pb-4 border-b border-gray-200">
        <span className="text-sm font-medium text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
          {datasets.length} {datasets.length === 1 ? "dataset" : "datasets"} total
        </span>
        <button
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-semibold text-teal-700 hover:bg-teal-50 rounded-lg transition-colors"
          onClick={() => void load()}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Success banner */}
      {successMessage && (
        <div
          role="status"
          className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-teal-800 bg-teal-50 border border-teal-200 rounded-xl"
        >
          <CheckCircle2 size={18} className="text-teal-700 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Main content */}
      <div className="min-h-[400px] flex flex-col">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : error ? (
          <ErrorMessage message={error} />
        ) : datasets.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-white border border-gray-200 border-dashed rounded-2xl shadow-sm">
            <div className="w-16 h-16 mb-5 rounded-full bg-teal-50 flex items-center justify-center text-teal-600">
              <Database size={32} />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No datasets yet</h3>
            <p className="text-gray-500 max-w-sm mx-auto mb-6 leading-relaxed">
              Upload a CSV or spreadsheet to start exploring your data and running quality
              checks.
            </p>
            <button
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white border-2 border-teal-700 text-teal-700 hover:bg-teal-50 font-bold rounded-xl transition-colors shadow-sm"
              onClick={() => setUploading(true)}
            >
              <Upload size={18} />
              Upload your first dataset
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {datasets.map((dataset) => (
              <Link
                className="flex flex-col sm:flex-row sm:items-center gap-5 p-5 bg-white border border-gray-200 rounded-xl hover:shadow-md hover:border-teal-300 transition-all group"
                to={`/datasets/${dataset.dataset_id}`}
                key={dataset.dataset_id}
              >
                <div className="flex-shrink-0 flex items-center justify-center w-14 h-14 bg-teal-50 text-teal-700 font-bold rounded-xl text-sm tracking-wider group-hover:bg-teal-100 transition-colors">
                  {dataset.file_type.toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-lg font-bold text-gray-900 truncate mb-1 group-hover:text-teal-700 transition-colors">
                    {dataset.name}
                  </h4>
                  <p className="text-sm text-gray-500 truncate">
                    {dataset.description || "No description provided"}
                  </p>
                </div>
                <div className="flex items-center gap-8 text-sm text-gray-600 px-4">
                  <div className="flex flex-col items-center">
                    <span className="font-bold text-gray-900 text-base">
                      {dataset.row_count.toLocaleString()}
                    </span>
                    <span className="text-xs uppercase tracking-wider text-gray-500 font-semibold mt-0.5">
                      Rows
                    </span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="font-bold text-gray-900 text-base">
                      {dataset.column_count}
                    </span>
                    <span className="text-xs uppercase tracking-wider text-gray-500 font-semibold mt-0.5">
                      Columns
                    </span>
                  </div>
                </div>
                <div className="flex-shrink-0 ml-2">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-green-100 text-green-800 border border-green-200">
                    {dataset.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {uploading && (
        <FileUpload
          onClose={() => setUploading(false)}
          onUploaded={(dataset) => {
            setDatasets((current) => [dataset, ...current]);
            setSuccessMessage(`"${dataset.name}" uploaded successfully.`);
            setUploading(false);
          }}
        />
      )}
    </div>
  );
}
