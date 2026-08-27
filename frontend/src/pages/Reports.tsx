import { FileText } from "lucide-react";

export function Reports() {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-teal-600 tracking-wider uppercase mb-1">Workspace</p>
          <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500 mt-1">View insights and generated reports.</p>
        </div>
      </div>
      
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-white border border-gray-200 border-dashed rounded-2xl shadow-sm min-h-[400px]">
        <div className="w-16 h-16 mb-5 rounded-full bg-teal-50 flex items-center justify-center text-teal-600">
          <FileText size={32} />
        </div>
        <h3 className="text-xl font-bold text-gray-900 mb-2">No reports yet</h3>
        <p className="text-gray-500 max-w-sm mx-auto leading-relaxed">
          Run quality checks or profiling on a dataset to generate reports here.
        </p>
      </div>
    </div>
  );
}
