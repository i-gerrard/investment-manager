"use client";

import { useState } from "react";
import { useGet } from "@/lib/useApi";
import { api, ApiError } from "@/lib/api";
import Link from "next/link";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import PortfolioSummaryChart from "@/components/charts/PortfolioSummaryChart";
import type { BulkLoadResponse } from "@/types";

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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-lg font-semibold text-primary">Net value trend</h2>
          <Link href="/portfolio/snapshots" className="text-xs text-primary hover:underline">
            → Snapshots
          </Link>
        </div>
        <PortfolioSummaryChart days={90} />
      </div>

      <BulkLoadCard />


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

// ── Bulk load card ──

function BulkLoadCard() {
  const [path, setPath] = useState("~/Desktop/claude");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BulkLoadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setBusy(true); setError(null); setResult(null);
    try {
      const res = await api.post<BulkLoadResponse>("/reports/bulk-load", { path });
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Bulk load failed");
    } finally {
      setBusy(false);
    }
  }

  const failed = result?.files.filter((f) => f.error) ?? [];
  const succeeded = result?.files.filter((f) => !f.error) ?? [];

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-primary">Load all reports</h2>
        <span className="text-xs text-gray-500">
          server scans <code className="font-mono bg-gray-100 px-1">**/report-*.html</code>
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="~/Desktop/claude"
          className="flex-1 min-w-[260px] font-mono text-sm px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button onClick={load} disabled={busy || !path.trim()}
                className="bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary-light disabled:opacity-50">
          {busy ? "Loading..." : "Load all"}
        </button>
      </div>
      {error && <p className="text-red-700 text-sm">{error}</p>}
      {result && (
        <div className="text-sm space-y-2">
          <p>
            Found <span className="font-semibold">{result.found}</span> files ·
            <span className="text-green-700 font-semibold"> {result.loaded} loaded</span>
            {result.failed > 0 && <span className="text-red-700 font-semibold"> · {result.failed} failed</span>}
            <span className="text-gray-400"> · {result.path}</span>
          </p>
          {succeeded.length > 0 && (
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer hover:text-gray-800">Show loaded ({succeeded.length})</summary>
              <ul className="mt-2 space-y-0.5 pl-4 max-h-60 overflow-auto">
                {succeeded.map((f) => (
                  <li key={f.file} className="font-mono">
                    {f.report_date} · {f.holdings ?? "?"} holdings · {f.recommendations ?? "?"} recs
                    <span className="text-gray-400 ml-2">{f.file}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          {failed.length > 0 && (
            <details className="text-xs text-red-700" open>
              <summary className="cursor-pointer hover:text-red-900">Show errors ({failed.length})</summary>
              <ul className="mt-2 space-y-0.5 pl-4 max-h-60 overflow-auto">
                {failed.map((f) => (
                  <li key={f.file} className="font-mono">
                    {f.file}: <span className="text-red-600">{f.error}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

