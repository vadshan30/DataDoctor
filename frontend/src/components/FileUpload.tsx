import { UploadCloud, X } from "lucide-react";
import { useRef, useState } from "react";
import { uploadDataset } from "../api/datasets";
import type { Dataset } from "../types/api";

export function FileUpload({ onUploaded, onClose }: { onUploaded: (dataset: Dataset) => void; onClose: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null); const [description, setDescription] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [progress, setProgress] = useState(0);
  const submit = async () => { if (!file) { setError("Choose a CSV, XLS, or XLSX file first."); return; } setBusy(true); setError(""); try { const result = await uploadDataset(file, description, setProgress); onUploaded(result.dataset); onClose(); } catch (err) { setError(err instanceof Error ? err.message : "Upload failed."); } finally { setBusy(false); } };
  return <div className="modal-backdrop"><section className="modal" aria-labelledby="upload-title"><div className="modal-header"><div><p className="eyebrow">New source</p><h2 id="upload-title">Upload a dataset</h2></div><button className="icon-button" onClick={onClose} aria-label="Close upload dialog"><X size={18} /></button></div><button className="dropzone" onClick={() => inputRef.current?.click()}><UploadCloud size={28} /><strong>{file ? file.name : "Choose a data file"}</strong><span>CSV, XLS, and XLSX up to the backend limit</span><input ref={inputRef} type="file" accept=".csv,.xls,.xlsx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></button><label>Description <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What is this dataset used for?" rows={3} /></label>{error && <div className="error-message">{error}</div>}{busy && <div className="progress"><span style={{ width: `${progress}%` }} /></div>}<div className="modal-actions"><button className="button secondary" onClick={onClose}>Cancel</button><button className="button primary" disabled={busy} onClick={submit}>{busy ? "Uploading…" : "Upload dataset"}</button></div></section></div>;
}
