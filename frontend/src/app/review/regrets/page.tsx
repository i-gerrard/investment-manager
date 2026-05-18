"use client";

import Link from "next/link";
import { useGet } from "@/lib/useApi";
import type { RegretItem } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

export default function RegretsPage() {
  const { data, loading, error, refetch } = useGet<RegretItem[]>("/review/regrets");

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-bold">Regrets</h1>
          <p className="text-sm text-gray-500 mt-1">
            Skipped recommendations sorted by absolute regret amount (largest first).
          </p>
        </div>
        <Link href="/review" className="text-sm text-primary hover:underline">← Back to Review</Link>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        {loading ? <LoadingSpinner /> :
         error ? <ErrorAlert message={error} onRetry={refetch} /> :
         !data?.length ? (
          <EmptyState message="No regrets recorded yet. Run a simulation on a skipped recommendation in /review to populate this list." />
        ) : <RegretsTable items={data} />}
      </div>
    </div>
  );
}

function RegretsTable({ items }: { items: RegretItem[] }) {
  const totalRegret = items.reduce((sum, i) => sum + (i.regret_usd ?? 0), 0);

  return (
    <div>
      <div className="text-sm text-gray-500 mb-3">
        Total absolute regret across {items.length} simulation{items.length === 1 ? "" : "s"}:
        <span className={`ml-1 font-semibold ${totalRegret > 0 ? "text-orange-700" : "text-green-700"}`}>
          ${totalRegret.toFixed(2)}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b">
              <th className="py-2 pr-3">Ticker</th>
              <th className="py-2 pr-3">Report date</th>
              <th className="py-2 pr-3">Skip reason</th>
              <th className="py-2 pr-3 text-right">Sim PnL</th>
              <th className="py-2 pr-3 text-right">Sim PnL %</th>
              <th className="py-2 pr-3 text-right">Regret</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.recommendation_id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-1.5 pr-3 font-medium">
                  <Link href={`/review?ticker=${encodeURIComponent(i.ticker)}`} className="hover:underline">
                    {i.ticker}
                  </Link>
                </td>
                <td className="py-1.5 pr-3 text-gray-500">{i.report_date ?? "—"}</td>
                <td className="py-1.5 pr-3">
                  <ReasonBadge reason={i.skip_reason} />
                </td>
                <td className={`py-1.5 pr-3 text-right ${pnlColor(i.sim_pnl_usd)}`}>
                  {i.sim_pnl_usd != null ? `$${i.sim_pnl_usd.toFixed(2)}` : "—"}
                </td>
                <td className={`py-1.5 pr-3 text-right ${pnlColor(i.sim_pnl_pct)}`}>
                  {i.sim_pnl_pct != null ? `${i.sim_pnl_pct.toFixed(2)}%` : "—"}
                </td>
                <td className={`py-1.5 pr-3 text-right font-semibold ${regretColor(i.regret_usd)}`}>
                  {i.regret_usd != null ? `$${i.regret_usd.toFixed(2)}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReasonBadge({ reason }: { reason: string | null }) {
  if (!reason) return <span className="text-xs text-gray-400">—</span>;
  const cls: Record<string, string> = {
    forgot: "bg-yellow-100 text-yellow-800",
    disagreed: "bg-blue-100 text-blue-800",
    no_cash: "bg-red-100 text-red-800",
    waiting_better_price: "bg-orange-100 text-orange-800",
    other: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs ${cls[reason] ?? "bg-gray-100 text-gray-700"}`}>
      {reason.replace(/_/g, " ")}
    </span>
  );
}

function pnlColor(v: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-green-700" : v < 0 ? "text-red-700" : "";
}

function regretColor(v: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-orange-700" : v < 0 ? "text-blue-700" : "";
}
