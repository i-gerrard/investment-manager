"use client";

import { useGet } from "@/lib/useApi";
import Link from "next/link";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";

interface DashboardData {
  portfolios: { id: string; name: string; holding_count: number }[];
  recent_reports: { id: string; title: string; phase: string; signal_rating?: string; created_at: string }[];
  latest_morning_report: { id: string; report_date: string; headline?: string } | null;
}

export default function Dashboard() {
  const { data, loading, error, refetch } = useGet<DashboardData>("/dashboard");

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} onRetry={refetch} />;
  if (!data) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-primary mb-3">Portfolios</h2>
          {data.portfolios.length ? (
            <ul className="space-y-2">
              {data.portfolios.map((p) => (
                <li key={p.id}>
                  <Link href={`/portfolio/${p.id}`} className="text-sm hover:text-accent">
                    {p.name} <span className="text-gray-400">({p.holding_count} holdings)</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 text-sm">No portfolios yet</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-primary mb-3">Recent Research</h2>
          {data.recent_reports.length ? (
            <ul className="space-y-2">
              {data.recent_reports.map((r) => (
                <li key={r.id} className="text-sm">
                  <span className="text-xs px-1.5 py-0.5 bg-primary/10 rounded mr-2">P{r.phase}</span>
                  {r.title}
                  {r.signal_rating && <span className="ml-2">{r.signal_rating}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 text-sm">No research yet</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-primary mb-3">Latest Morning Report</h2>
          {data.latest_morning_report ? (
            <div>
              <p className="text-sm font-medium">{data.latest_morning_report.report_date}</p>
              <p className="text-xs text-gray-500 mt-1">{data.latest_morning_report.headline}</p>
              <Link href="/reports/morning" className="text-xs text-accent mt-2 inline-block">View all &rarr;</Link>
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No reports yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
