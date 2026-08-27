import { ArrowUpRight, Database, FileText, FlaskConical } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Home() { 
  const { session } = useAuth(); 
  
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="flex flex-col p-6 bg-teal-50 border border-teal-100 rounded-2xl shadow-sm transition-transform hover:-translate-y-1 hover:shadow-md">
          <div className="flex items-center gap-2 text-teal-800 font-semibold mb-4">
            <Database size={20} />
            <span>Datasets</span>
          </div>
          <strong className="text-4xl font-bold text-gray-900 mb-2">—</strong>
          <small className="text-sm text-teal-700 font-medium">Upload your first source</small>
        </div>
        
        <div className="flex flex-col p-6 bg-white border border-gray-200 rounded-2xl shadow-sm transition-transform hover:-translate-y-1 hover:shadow-md">
          <div className="flex items-center gap-2 text-gray-600 font-semibold mb-4">
            <FlaskConical size={20} />
            <span>Experiments</span>
          </div>
          <strong className="text-4xl font-bold text-gray-900 mb-2">—</strong>
          <small className="text-sm text-gray-500 font-medium">Runs will appear here</small>
        </div>
        
        <div className="flex flex-col p-6 bg-white border border-gray-200 rounded-2xl shadow-sm transition-transform hover:-translate-y-1 hover:shadow-md">
          <div className="flex items-center gap-2 text-gray-600 font-semibold mb-4">
            <FileText size={20} />
            <span>Reports</span>
          </div>
          <strong className="text-4xl font-bold text-gray-900 mb-2">—</strong>
          <small className="text-sm text-gray-500 font-medium">Generated insights</small>
        </div>
      </div>

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
