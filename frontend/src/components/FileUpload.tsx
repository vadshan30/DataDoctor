import { CheckCircle2, FileSpreadsheet, UploadCloud, X } from "lucide-react";
import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { uploadDataset } from "../api/datasets";
import type { Dataset } from "../types/api";

const MAX_FILE_SIZE_MB = 100;
const ACCEPTED_TYPES = ".csv,.xls,.xlsx";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function FileUpload({
  onUploaded,
  onClose,
}: {
  onUploaded: (dataset: Dataset) => void;
  onClose: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);

  const selectFile = (next: File | undefined | null) => {
    if (!next) return;
    if (next.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`File is too large. Maximum allowed size is ${MAX_FILE_SIZE_MB} MB.`);
      return;
    }
    setError("");
    setFile(next);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    selectFile(event.target.files?.[0]);
  };

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files?.[0]);
  };

  const clearSelection = () => {
    setFile(null);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  };

  const submit = async () => {
    if (!file) {
      setError("Choose a CSV, XLS, or XLSX file first.");
      return;
    }
    setBusy(true);
    setError("");
    setProgress(0);
    try {
      const result = await uploadDataset(file, description, setProgress);
      onUploaded(result.dataset);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="w-full max-w-xl bg-white border border-gray-200 rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <header className="flex items-start justify-between gap-4 px-6 py-5 border-b border-gray-100">
          <div>
            <p className="text-[11px] font-bold text-teal-700 tracking-[0.14em] uppercase mb-1">
              New source
            </p>
            <h2 id="upload-title" className="text-xl font-bold text-gray-900">
              Upload a dataset
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Bring a spreadsheet into your workspace to start profiling.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close upload dialog"
            className="flex-shrink-0 inline-flex items-center justify-center w-9 h-9 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={18} />
          </button>
        </header>

        {/* Body */}
        <div className="px-6 py-6 space-y-5">
          {/* Drop zone */}
          {!file ? (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              className={`w-full flex flex-col items-center justify-center gap-3 px-6 py-10 border-2 border-dashed rounded-xl text-center transition-colors ${
                dragging
                  ? "border-teal-600 bg-teal-50"
                  : "border-gray-300 bg-gray-50 hover:border-teal-500 hover:bg-teal-50/50"
              }`}
            >
              <span className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-white text-teal-700 shadow-sm border border-teal-100">
                <UploadCloud size={28} />
              </span>
              <div>
                <p className="text-base font-semibold text-gray-900">
                  Drag and drop your file here
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  or <span className="font-semibold text-teal-700">browse from your device</span>
                </p>
              </div>
              <p className="text-xs text-gray-500">
                Supports <span className="font-semibold text-gray-700">CSV, XLS, XLSX</span>{" "}
                &middot; up to <span className="font-semibold text-gray-700">{MAX_FILE_SIZE_MB} MB</span>
              </p>
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED_TYPES}
                onChange={handleInputChange}
                className="hidden"
              />
            </button>
          ) : (
            <div className="flex items-center gap-4 p-4 bg-teal-50 border border-teal-200 rounded-xl">
              <span className="inline-flex items-center justify-center w-11 h-11 rounded-lg bg-white text-teal-700 border border-teal-100">
                <FileSpreadsheet size={22} />
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">{file.name}</p>
                <p className="text-xs text-gray-600 mt-0.5">
                  {formatBytes(file.size)} &middot; Ready to upload
                </p>
              </div>
              <button
                type="button"
                onClick={clearSelection}
                disabled={busy}
                className="inline-flex items-center justify-center w-8 h-8 text-gray-500 hover:text-red-600 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
                aria-label="Remove selected file"
              >
                <X size={16} />
              </button>
            </div>
          )}

          {/* Description */}
          <div>
            <label
              htmlFor="dataset-description"
              className="block text-sm font-semibold text-gray-700 mb-1.5"
            >
              Description <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <textarea
              id="dataset-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What is this dataset used for?"
              rows={3}
              disabled={busy}
              className="w-full px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-600 transition-colors resize-none disabled:bg-gray-50"
            />
          </div>

          {/* Status messages */}
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 px-4 py-3 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg"
            >
              <span className="font-bold leading-5">!</span>
              <span className="leading-5">{error}</span>
            </div>
          )}

          {busy && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-gray-600">
                <span>Uploading {file?.name}…</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-teal-600 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {!busy && !error && file && (
            <div className="flex items-center gap-2 text-xs font-medium text-teal-700">
              <CheckCircle2 size={14} />
              <span>File is ready to be uploaded.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="flex items-center justify-end gap-3 px-6 py-4 bg-gray-50 border-t border-gray-100">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="inline-flex items-center justify-center px-4 py-2.5 text-sm font-semibold text-gray-700 bg-white border border-gray-300 hover:bg-gray-100 rounded-xl transition-colors disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={busy || !file}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-xl shadow-sm transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <UploadCloud size={16} />
            {busy ? "Uploading…" : "Upload dataset"}
          </button>
        </footer>
      </section>
    </div>
  );
}
