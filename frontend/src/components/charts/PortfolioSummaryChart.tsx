"use client";

import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { useGet } from "@/lib/useApi";
import type { PortfolioSummaryPoint } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";

export default function PortfolioSummaryChart({ days = 90 }: { days?: number }) {
  const { data, loading, error } = useGet<PortfolioSummaryPoint[]>(`/portfolio/summary?days=${days}`);

  if (loading) return <div className="h-64 flex items-center justify-center"><LoadingSpinner /></div>;
  if (error) return <ErrorAlert message={error} />;
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-sm text-gray-400">
        No snapshot history yet — upload a report on /portfolio/snapshots to start the curve.
      </div>
    );
  }

  // Single-point datasets aren't useful for a line chart; show the single value as text.
  if (data.length === 1) {
    const p = data[0];
    return (
      <div className="h-64 flex flex-col items-center justify-center space-y-1">
        <div className="text-xs text-gray-500">{p.report_date}</div>
        <div className="text-3xl font-semibold text-primary">${(p.combined_total_usd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
        <div className="text-xs text-gray-400">Only one snapshot recorded so far — upload another date to see the trend.</div>
      </div>
    );
  }

  const latest = data[data.length - 1];
  const earliest = data[0];
  const totalDelta = (latest.combined_total_usd ?? 0) - (earliest.combined_total_usd ?? 0);
  const totalDeltaPct = earliest.combined_total_usd
    ? (totalDelta / earliest.combined_total_usd) * 100
    : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-4 text-sm">
        <div>
          <span className="text-xs text-gray-500">Latest </span>
          <span className="font-semibold text-primary text-lg">
            ${(latest.combined_total_usd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
          <span className="ml-2 text-xs text-gray-400">on {latest.report_date}</span>
        </div>
        <div>
          <span className="text-xs text-gray-500">Cash </span>
          <span className="font-semibold">
            ${(latest.combined_cash_usd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
          {latest.cash_ratio_pct != null && (
            <span className="text-xs text-gray-400 ml-1">({latest.cash_ratio_pct.toFixed(1)}%)</span>
          )}
        </div>
        <div className={totalDelta >= 0 ? "text-green-700" : "text-red-700"}>
          <span className="text-xs">vs {earliest.report_date}: </span>
          <span className="font-semibold">
            {totalDelta >= 0 ? "+" : ""}${totalDelta.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            {totalDeltaPct != null && ` (${totalDeltaPct >= 0 ? "+" : ""}${totalDeltaPct.toFixed(2)}%)`}
          </span>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 24, bottom: 5, left: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="report_date" fontSize={11} tick={{ fill: "#888" }} />
            <YAxis fontSize={11} tick={{ fill: "#888" }}
                   tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip content={<SummaryTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="combined_total_usd" name="Combined total"
                  stroke="#0f3460" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="combined_cash_usd" name="Cash"
                  stroke="#16a34a" strokeWidth={2} dot={false} strokeDasharray="4 4" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

type TooltipProps = {
  active?: boolean;
  payload?: { dataKey: string; value: number; color: string }[];
  label?: string;
};

function SummaryTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-xs">
      <div className="font-medium text-gray-700 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-500">{p.dataKey === "combined_total_usd" ? "Total" : "Cash"}</span>
          <span className="font-medium">${(p.value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        </div>
      ))}
    </div>
  );
}
