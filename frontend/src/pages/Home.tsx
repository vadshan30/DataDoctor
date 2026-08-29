import { ArrowUpRight, Database, FileText, FlaskConical } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { DashboardStats } from "../components/DashboardStats";
import { useDashboardStats } from "../hooks/useDashboardStats";

export function Home() {
  const { session } = useAuth();
  const { data: stats, loading, error } = useDashboardStats();

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-teal-600 tracking-wider uppercase mb-1">Overview</p>
          <h1 className="text-3xl font-bold text-gray-900">
            Good to see you, {session?.email?.split("@")[0] || "User"}.
          </h1>
          <p className="text-gray-500 mt-1">Your data workspace, ready when you are.</p>
        </div>
        <Link
          to="/datasets"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-teal-700 hover:bg-teal-800 text-white font-semibold rounded-xl shadow-sm transition-all hover:shadow-md"
        >
          Open datasets <ArrowUpRight size={18} />
        </Link>
      </div>

      {/* Stats Cards Grid - 3 Column Layout */}
      {loading ? (
        <DashboardSkeleton />
      ) : error ? (
        <div className="p-6 bg-white border border-red-200 rounded-2xl shadow-sm">
          <p className="text-sm font-semibold text-red-700 mb-1">Failed to load dashboard</p>
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : (
        stats && (
          <DashboardStats
            stats={{
              datasets: stats.datasets,
              experiments: stats.experiments,
              reports: stats.reports,
              totalRows: stats.totalRows,
              totalColumns: stats.totalColumns,
              recentDatasets: stats.recentDatasets,
            }}
          />
        )
      )}

      {/* Recent Datasets + Quick Stats */}
      {!loading && !error && stats && (stats.datasets > 0 || stats.experiments > 0 || stats.reports > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2 bg-white border border-gray-200 rounded-2xl shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">Recent datasets</h2>
              <Link to="/datasets" className="text-sm font-semibold text-teal-700 hover:text-teal-800">
                View all →
              </Link>
            </div>
            <ul className="divide-y divide-gray-100">
              {stats.recentDatasets.map((dataset) => (
                <li key={dataset.name} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 bg-teal-50 text-teal-700 font-bold rounded-lg text-xs tracking-wider">
                      <Database size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{dataset.name}</p>
                      <p className="text-xs text-gray-500">Uploaded {dataset.uploadedAt}</p>
                    </div>
                  </div>
                  <Link
                    to="/datasets"
                    className="text-sm font-semibold text-teal-700 hover:text-teal-800 flex-shrink-0"
                  >
                    Open
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Quick stats</h2>
            <dl className="space-y-4">
              <div className="flex items-center justify-between">
                <dt className="text-sm text-gray-600">Total rows across all datasets</dt>
                <dd className="text-sm font-bold text-gray-900">{stats.totalRows.toLocaleString()}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-sm text-gray-600">Total columns</dt>
                <dd className="text-sm font-bold text-gray-900">{stats.totalColumns}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-sm text-gray-600">Active experiments</dt>
                <dd className="text-sm font-bold text-gray-900">{stats.experiments}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-sm text-gray-600">Generated reports</dt>
                <dd className="text-sm font-bold text-gray-900">{stats.reports}</dd>
              </div>
            </dl>
          </section>
        </div>
      )}

      {/* Welcome Panel */}
      <section className="flex flex-col sm:flex-row items-center justify-between gap-8 p-8 bg-white border border-gray-200 rounded-2xl shadow-sm mt-8 overflow-hidden relative">
        <div className="absolute top-0 right-0 w-64 h-64 bg-teal-50 rounded-full blur-3xl -mr-20 -mt-20 opacity-60"></div>
        <div className="flex-1 relative z-10">
          <p className="text-sm font-bold text-teal-600 tracking-wider uppercase mb-2">Start here</p>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Bring a dataset into focus.</h2>
          <p className="text-gray-600 max-w-xl text-base leading-relaxed">
            Upload a CSV or spreadsheet to begin profiling, quality checks, and preparation. Our automated pipelines will handle the rest.
          </p>
        </div>
        <div className="relative z-10 flex-shrink-0">
          <Link
            to="/datasets"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white border-2 border-teal-700 text-teal-700 hover:bg-teal-50 font-bold rounded-xl transition-colors whitespace-nowrap shadow-sm"
          >
            View datasets <ArrowUpRight size={18} />
          </Link>
        </div>
      </section>
    </div>
  );
}

function DashboardSkeleton() {
  const cards = [
    { accent: true, label: "Datasets" },
    { accent: false, label: "Experiments" },
    { accent: false, label: "Reports" },
  ];
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`flex flex-col p-6 rounded-2xl shadow-sm border ${
            card.accent ? "bg-teal-50 border-teal-100" : "bg-white border-gray-200"
          }`}
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="w-5 h-5 rounded bg-gray-200 animate-pulse" />
            <span className="text-sm font-semibold text-gray-400">{card.label}</span>
          </div>
          <div className="w-16 h-8 rounded bg-gray-200 animate-pulse mb-2" />
          <div className="w-32 h-4 rounded bg-gray-200 animate-pulse" />
        </div>
      ))}
    </div>
  );
}