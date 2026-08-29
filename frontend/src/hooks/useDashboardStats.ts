import { useEffect, useState } from "react";
import { listDatasets } from "../api/datasets";
import { listDatasetReports } from "../api/reports";
import { listExperiments } from "../api/experiments";
import type { Dataset } from "../types/api";

export interface DashboardStatsData {
  datasets: number;
  experiments: number;
  reports: number;
  totalRows: number;
  totalColumns: number;
  recentDatasets: { name: string; uploadedAt: string }[];
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function useDashboardStats() {
  const [data, setData] = useState<DashboardStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        // Datasets are the root resource — everything else is nested under them.
        const datasetsResponse = await listDatasets();
        const datasets: Dataset[] = datasetsResponse.datasets;

        let experimentsCount = 0;
        let reportsCount = 0;

        // Aggregate experiments and reports across every dataset. Each of these
        // endpoints is scoped to a single dataset, so we fan out and sum results.
        await Promise.all(
          datasets.map(async (dataset) => {
            try {
              const [experiments, reports] = await Promise.all([
                listExperiments(dataset.dataset_id),
                listDatasetReports(dataset.dataset_id),
              ]);
              experimentsCount += experiments.total ?? experiments.experiments.length;
              reportsCount += reports.total ?? reports.reports.length;
            } catch {
              // Per-dataset failures are non-fatal — we still surface the datasets
              // we could reach and keep the dashboard usable.
            }
          })
        );

        const recentDatasets = datasets.slice(0, 5).map((dataset) => ({
          name: dataset.name,
          uploadedAt: formatDate(dataset.created_at),
        }));

        if (!cancelled) {
          setData({
            datasets: datasets.length,
            experiments: experimentsCount,
            reports: reportsCount,
            totalRows: datasets.reduce((sum, d) => sum + (d.row_count ?? 0), 0),
            totalColumns: datasets.reduce((sum, d) => sum + (d.column_count ?? 0), 0),
            recentDatasets,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading, error };
}