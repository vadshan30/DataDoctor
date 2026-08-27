import { BarChart3, Database, FileSpreadsheet, FileText, Folder, Layers3, RefreshCw } from "lucide-react";
import { useState, type ReactNode } from "react";
import { ColumnProfileTable } from "./profiling/ColumnProfileTable";
import { DatasetStats } from "./DatasetStats";
import { EmptyState, ErrorMessage, LoadingSpinner } from "./common/States";
import { formatBytes, formatNumber } from "../utils/helpers";
import type { Dataset, DatasetProfileResponse } from "../types/api";

type ProfileState =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: DatasetProfileResponse };

interface DatasetOverviewProps {
  dataset: Dataset;
  profile: ProfileState;
  onRefresh: () => void;
  /** Optional inline action to render at the right of the section toolbar. */
  toolbarAction?: ReactNode;
}

/**
 * Renders the boxed dataset header card (name, status, version,
 * description, four header stat tiles) and the Data Profile section
 * (9-tile metric grid + column profile table).
 *
 * Loading and error states for the profile are handled internally.
 */
export function DatasetOverview({ dataset, profile, onRefresh, toolbarAction }: DatasetOverviewProps) {
  return (
    <>
      <DatasetHeaderCard dataset={dataset} />

      <section className="analysis-section">
        <div className="section-toolbar">
          <h2 className="subheading" style={{ margin: 0 }}>
            <BarChart3 size={20} /> Data profile
          </h2>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {toolbarAction}
            <button type="button" className="text-button" onClick={onRefresh}>
              <RefreshCw size={15} />Refresh
            </button>
          </div>
        </div>

        {profile.status === "loading" && <LoadingSpinner />}
        {profile.status === "error" && <ErrorMessage message={profile.error} />}
        {profile.status === "success" && (
          <DatasetProfileContent profile={profile.data} />
        )}
      </section>
    </>
  );
}

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

/* ------------------------------------------------------------------ */
/* Dataset Header Card                                                */
/* ------------------------------------------------------------------ */

function DatasetHeaderCard({ dataset }: { dataset: Dataset }) {
  const statusClass = `status-pill status-${dataset.status || "uploaded"}`;

  const tiles: { label: string; value: string; icon: ReactNode }[] = [
    { label: "Rows", value: formatNumber(dataset.row_count, 0), icon: <Database size={18} /> },
    { label: "Columns", value: formatNumber(dataset.column_count, 0), icon: <LayersIcon /> },
    { label: "Format", value: (dataset.file_type || "—").toUpperCase(), icon: <FileSpreadsheet size={18} /> },
    { label: "Size", value: formatBytes(dataset.file_size), icon: <Folder size={18} /> },
  ];

  return (
    <div className="detail-header-card">
      <div className="detail-header-top">
        <div className="detail-header-title">
          <div className="detail-header-icon">
            <FileText size={20} />
          </div>
          <div>
            <p className="eyebrow">Dataset #{dataset.dataset_id}</p>
            <h1 className="detail-header-name">{dataset.name}</h1>
            <p className="detail-header-sub">
              {dataset.description?.trim() || "No description provided."}
            </p>
          </div>
        </div>
        <div className="detail-header-meta">
          <span className={statusClass}>{dataset.status || "uploaded"}</span>
          <span className="version-chip">Version v{dataset.version}</span>
        </div>
      </div>

      <div className="detail-stats">
        {tiles.map((tile) => (
          <div key={tile.label} className="detail-stats-tile">
            <div className="detail-stats-tile-icon">{tile.icon}</div>
            <div className="detail-stats-tile-text">
              <span className="detail-stats-tile-label">{tile.label}</span>
              <span className="detail-stats-tile-value">{tile.value}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LayersIcon() {
  // Simple icon wrapper that matches the lucide-react stroke style.
  return <Layers3 size={18} />;
}
