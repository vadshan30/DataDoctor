import { Database, FileText, FlaskConical } from "lucide-react";

export interface DashboardStat {
  label: string;
  value: number;
  icon: React.ReactNode;
  accent?: boolean;
  helper: string;
}

export interface DashboardStatsData {
  datasets: number;
  experiments: number;
  reports: number;
  totalRows: number;
  totalColumns: number;
  recentDatasets: { name: string; uploadedAt: string }[];
}

function formatNumber(value: number): string {
  if (value >= 1000) return value.toLocaleString();
  return String(value);
}

export function DashboardStats({ stats }: { stats: DashboardStatsData }) {
  const cards: DashboardStat[] = [
    {
      label: "Datasets",
      value: stats.datasets,
      icon: <Database size={20} />,
      accent: true,
      helper: stats.datasets > 0 ? `${formatNumber(stats.datasets)} source${stats.datasets === 1 ? "" : "s"}` : "Upload your first source",
    },
    {
      label: "Experiments",
      value: stats.experiments,
      icon: <FlaskConical size={20} />,
      helper: stats.experiments > 0 ? `${formatNumber(stats.experiments)} run${stats.experiments === 1 ? "" : "s"}` : "Runs will appear here",
    },
    {
      label: "Reports",
      value: stats.reports,
      icon: <FileText size={20} />,
      helper: stats.reports > 0 ? `${formatNumber(stats.reports)} insight${stats.reports === 1 ? "" : "s"}` : "Generated insights",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`flex flex-col p-6 rounded-2xl shadow-sm transition-transform hover:-translate-y-1 hover:shadow-md ${
            card.accent
              ? "bg-teal-50 border border-teal-100"
              : "bg-white border border-gray-200"
          }`}
        >
          <div className={`flex items-center gap-2 font-semibold mb-4 ${
            card.accent ? "text-teal-800" : "text-gray-600"
          }`}>
            {card.icon}
            <span>{card.label}</span>
          </div>
          <strong className="text-4xl font-bold text-gray-900 mb-2">
            {formatNumber(card.value)}
          </strong>
          <small className="text-sm text-gray-500 font-medium">{card.helper}</small>
        </div>
      ))}
    </div>
  );
}