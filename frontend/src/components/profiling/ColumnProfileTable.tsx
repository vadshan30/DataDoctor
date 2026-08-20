import { useState } from "react";
import { ArrowDownUp } from "lucide-react";
import { formatNumber, formatPercentage } from "../../utils/helpers";
import type { ColumnProfile } from "../../types/api";

type SortKey = "column_name" | "null_percentage" | "unique_count" | "mean" | "median" | "min" | "max" | "standard_deviation";
type SortDir = "asc" | "desc";

const NUMERIC_HEADERS: { key: SortKey; label: string }[] = [
  { key: "column_name", label: "Column" },
  { key: "null_percentage", label: "Missing %" },
  { key: "unique_count", label: "Unique" },
  { key: "mean", label: "Mean" },
  { key: "median", label: "Median" },
  { key: "min", label: "Min" },
  { key: "max", label: "Max" },
  { key: "standard_deviation", label: "Std Dev" },
];

export function ColumnProfileTable({ columns }: { columns: ColumnProfile[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("column_name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const resolveValue = (col: ColumnProfile, key: SortKey): number | string | null => {
    switch (key) {
      case "column_name":
        return col.column_name;
      case "null_percentage":
        return col.null_percentage;
      case "unique_count":
        return col.unique_count;
      case "mean":
        return col.numeric_stats?.mean ?? null;
      case "median":
        return col.numeric_stats?.median ?? null;
      case "min":
        return col.numeric_stats?.min ?? null;
      case "max":
        return col.numeric_stats?.max ?? null;
      case "standard_deviation":
        return col.numeric_stats?.standard_deviation ?? null;
      default:
        return null;
    }
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sorted = [...columns].sort((a, b) => {
    const va = resolveValue(a, sortKey);
    const vb = resolveValue(b, sortKey);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "number" && typeof vb === "number") {
      return sortDir === "asc" ? va - vb : vb - va;
    }
    const sa = String(va).toLowerCase();
    const sb = String(vb).toLowerCase();
    return sortDir === "asc" ? sa.localeCompare(sb) : sb.localeCompare(sa);
  });

  if (!columns || columns.length === 0) {
    return (
      <div className="table-empty">
        <p className="muted">No column profiles available.</p>
      </div>
    );
  }

  const renderSortableHeader = (key: SortKey, label: string) => {
    const isSorted = sortKey === key;
    return (
      <th key={key}>
        <button type="button" className="sort-button" onClick={() => handleSort(key)}>
          {label}
          <ArrowDownUp size={12} style={{ opacity: isSorted ? 1 : 0.4 }} />
        </button>
      </th>
    );
  };

  return (
    <div className="table-wrapper">
      <table className="profile-table">
        <thead>
          <tr>
            {renderSortableHeader("column_name", "Column")}
            <th>Type</th>
            <th>Missing</th>
            {renderSortableHeader("null_percentage", "Missing %")}
            {renderSortableHeader("unique_count", "Unique")}
            {renderSortableHeader("mean", "Mean")}
            {renderSortableHeader("median", "Median")}
            {renderSortableHeader("min", "Min")}
            {renderSortableHeader("max", "Max")}
            {renderSortableHeader("standard_deviation", "Std Dev")}
            <th>Details / Date</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((col) => {
            const numeric = col.numeric_stats;
            const datetime = col.datetime_stats;
            const categorical = col.categorical_stats;

            return (
              <tr key={col.column_name}>
                <td className="col-name" title={col.column_name}>{col.column_name}</td>
                <td className="col-type">
                  <span className={`type-badge type-${col.data_type}`}>{col.data_type}</span>
                  <span className="muted" title={col.pandas_dtype}>{col.pandas_dtype}</span>
                </td>
                <td className="col-missing">{col.null_count}</td>
                <td className="col-pct">
                  <div className="cell-with-bar">
                    <span>{formatPercentage(col.null_percentage)}</span>
                    <MissingBar percentage={col.null_percentage} />
                  </div>
                </td>
                <td className="col-unique">{col.unique_count}</td>
                <td className="col-mean">{formatNumber(numeric?.mean)}</td>
                <td className="col-median">{formatNumber(numeric?.median)}</td>
                <td className="col-min">{formatNumber(numeric?.min)}</td>
                <td className="col-max">{formatNumber(numeric?.max)}</td>
                <td className="col-std">{formatNumber(numeric?.standard_deviation)}</td>
                <td className="col-date">
                  {datetime ? (
                    <span title={`Range: ${datetime.min_date} to ${datetime.max_date}`}>
                      {datetime.min_date ?? "—"} ~ {datetime.max_date ?? "—"}
                    </span>
                  ) : categorical && categorical.top_values.length > 0 ? (
                    <span title={`Top values: ${categorical.top_values.slice(0, 3).join(", ")}`}>
                      Top: {categorical.top_values.slice(0, 2).join(", ")}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function MissingBar({ percentage }: { percentage: number }) {
  const width = Math.min(percentage, 100);
  const color = percentage > 20 ? "var(--danger)" : percentage > 5 ? "var(--warning)" : "var(--teal)";
  return (
    <div className="missing-bar" title={`${percentage}%`}>
      <span className="missing-bar-fill" style={{ width: `${width}%`, backgroundColor: color }} />
    </div>
  );
}
