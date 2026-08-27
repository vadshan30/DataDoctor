import { AlertTriangle, BarChart3, CalendarClock, Copy, Database, Hash, Layers3, ToggleLeft, Type } from "lucide-react";
import { formatBytes, formatNumber } from "../utils/helpers";
import type { DatasetProfileResponse } from "../types/api";

/**
 * Profile statistics card grid for the dataset overview.
 * Pure presentation: takes a `DatasetProfileResponse` and renders
 * the 9-cell metric grid (Rows, Columns, Size, Numeric, Categorical,
 * Datetime, Boolean, Missing, Duplicates) using the DataDoctor
 * design system.
 */
export function DatasetStats({ profile }: { profile: DatasetProfileResponse }) {
  const totalMissing = profile.columns.reduce((sum, c) => sum + c.null_count, 0);

  const tiles: { label: string; value: string; icon: React.ReactNode; accent?: boolean }[] = [
    { label: "Rows", value: formatNumber(profile.row_count, 0), icon: <Database size={18} /> },
    { label: "Columns", value: formatNumber(profile.column_count, 0), icon: <Layers3 size={18} /> },
    { label: "Dataset size", value: formatBytes(profile.memory_usage), icon: <BarChart3 size={18} />, accent: true },
    { label: "Numeric columns", value: formatNumber(profile.numerical_column_count, 0), icon: <Hash size={18} /> },
    { label: "Categorical columns", value: formatNumber(profile.categorical_column_count, 0), icon: <Type size={18} /> },
    { label: "Datetime columns", value: formatNumber(profile.datetime_column_count, 0), icon: <CalendarClock size={18} /> },
    { label: "Boolean columns", value: formatNumber(profile.boolean_column_count, 0), icon: <ToggleLeft size={18} /> },
    { label: "Missing values", value: formatNumber(totalMissing, 0), icon: <AlertTriangle size={18} /> },
    { label: "Duplicate rows", value: formatNumber(profile.duplicate_row_count, 0), icon: <Copy size={18} /> },
  ];

  return (
    <div className="metric-grid">
      {tiles.map((tile) => (
        <div key={tile.label} className={`metric-card ${tile.accent ? "accent" : ""}`}>
          <span>{tile.icon}{tile.label}</span>
          <strong>{tile.value}</strong>
        </div>
      ))}
    </div>
  );
}
