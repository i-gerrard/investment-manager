"use client";

import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { useGet } from "@/lib/useApi";
import type { HoldingHistoryPoint } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";

type AccountOpt = "all" | "etoro" | "tr";

export default function TickerHistoryChart({
  ticker,
  account = "all",
}: { ticker: string; account?: AccountOpt }) {
  const path = account === "all" ? `/holdings/${ticker}/history` : `/holdings/${ticker}/history?account=${account}`;
  const { data, loading, error } = useGet<HoldingHistoryPoint[]>(path, [ticker, account]);

  if (loading) return <div className="h-64 flex items-center justify-center"><LoadingSpinner /></div>;
  if (error) return <ErrorAlert message={error} />;
  if (!data || data.length === 0) {
    return <div className="h-64 flex items-center justify-center text-sm text-gray-400">No history for {ticker}.</div>;
  }

  // When 'all', merge etoro+tr per date into a combined market_value_usd for the line.
  const merged = mergeByDate(data);

  if (merged.length === 1) {
    const p = merged[0];
    return (
      <div className="h-64 flex flex-col items-center justify-center space-y-1">
        <div className="text-xs text-gray-500">{p.report_date}</div>
        <div className="text-2xl font-semibold text-primary">
          ${(p.market_value_usd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
        <div className="text-xs text-gray-400">Only one snapshot — upload more dates to see the trend.</div>
      </div>
    );
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={merged} margin={{ top: 5, right: 24, bottom: 5, left: 12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="report_date" fontSize={11} tick={{ fill: "#888" }} />
          <YAxis yAxisId="left" fontSize={11} tick={{ fill: "#888" }}
                 tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`} />
          <YAxis yAxisId="right" orientation="right" fontSize={11} tick={{ fill: "#888" }}
                 tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip content={<TickerTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line yAxisId="left" type="monotone" dataKey="market_value_usd"
                name="Market value (USD)" stroke="#0f3460" strokeWidth={2} dot={false} />
          <Line yAxisId="right" type="monotone" dataKey="current_price"
                name="Price" stroke="#f97316" strokeWidth={2} dot={false} strokeDasharray="4 4" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Merge per-account rows on the same date into a single row with summed MV and
// last-seen price. With `account` filtering enabled in the API call, this is
// typically a no-op; with 'all' it combines etoro + tr.
function mergeByDate(points: HoldingHistoryPoint[]): HoldingHistoryPoint[] {
  const byDate = new Map<string, HoldingHistoryPoint>();
  for (const p of points) {
    const existing = byDate.get(p.report_date);
    if (!existing) {
      byDate.set(p.report_date, { ...p });
    } else {
      existing.market_value_usd =
        (existing.market_value_usd ?? 0) + (p.market_value_usd ?? 0);
      existing.shares = (existing.shares ?? 0) + (p.shares ?? 0);
      existing.current_price = p.current_price ?? existing.current_price;
    }
  }
  return Array.from(byDate.values()).sort((a, b) => a.report_date.localeCompare(b.report_date));
}

type TooltipProps = {
  active?: boolean;
  payload?: { dataKey: string; value: number; color: string }[];
  label?: string;
};

function TickerTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-xs">
      <div className="font-medium text-gray-700 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-500">
            {p.dataKey === "market_value_usd" ? "Market value" : "Price"}
          </span>
          <span className="font-medium">
            ${(p.value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </span>
        </div>
      ))}
    </div>
  );
}
