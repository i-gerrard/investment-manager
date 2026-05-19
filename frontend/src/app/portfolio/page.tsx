"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useGet } from "@/lib/useApi";
import type {
  HoldingSnapshotRow,
  SnapshotDetail,
  SnapshotListItem,
} from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";
import TickerHistoryChart from "@/components/charts/TickerHistoryChart";

type AccountFilter = "all" | "etoro" | "tr";

export default function PortfolioPage() {
  const list = useGet<SnapshotListItem[]>("/snapshots?limit=1");

  if (list.loading) return <LoadingSpinner message="Loading latest snapshot..." />;
  if (list.error) return <ErrorAlert message={list.error} onRetry={list.refetch} />;
  if (!list.data || list.data.length === 0) {
    return (
      <EmptyState
        message="No snapshots yet. Upload a daily report on the Snapshots page to populate this view."
        cta={{ label: "Go to Snapshots", href: "/portfolio/snapshots" }}
      />
    );
  }

  return <LatestSnapshotView reportDate={list.data[0].report_date} />;
}

function LatestSnapshotView({ reportDate }: { reportDate: string }) {
  const [accountFilter, setAccountFilter] = useState<AccountFilter>("all");
  const [historyTicker, setHistoryTicker] = useState<string | null>(null);

  const detail = useGet<SnapshotDetail>(`/snapshots/${reportDate}`, [reportDate]);
  const holdingsPath = accountFilter === "all"
    ? `/snapshots/${reportDate}/holdings`
    : `/snapshots/${reportDate}/holdings?account=${accountFilter}`;
  const holdings = useGet<HoldingSnapshotRow[]>(holdingsPath, [reportDate, accountFilter]);

  // For totals we always want the full set, not the filtered slice.
  const allHoldings = useGet<HoldingSnapshotRow[]>(`/snapshots/${reportDate}/holdings`, [reportDate]);

  const totals = useMemo(() => deriveTotals(allHoldings.data), [allHoldings.data]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Portfolio</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Latest snapshot · {reportDate}
            {detail.data?.source && (
              <span className="text-gray-400"> · source {detail.data.source}</span>
            )}
          </p>
        </div>
        <div className="flex gap-3 text-sm">
          <Link href="/portfolio/snapshots" className="text-primary hover:underline">
            → All snapshots
          </Link>
          <Link href="/portfolio/snapshots/compare" className="text-primary hover:underline">
            → Compare dates
          </Link>
        </div>
      </header>

      <SummaryGrid detail={detail.data} totals={totals}
                   loading={detail.loading || allHoldings.loading}
                   error={detail.error ?? allHoldings.error} />

      <AccountStrip detail={detail.data} />

      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-primary">
            Holdings {holdings.data ? `(${holdings.data.length})` : ""}
          </h2>
          <div className="flex gap-1">
            {(["all", "etoro", "tr"] as AccountFilter[]).map((f) => (
              <button key={f} onClick={() => setAccountFilter(f)}
                      className={`px-3 py-1 text-xs rounded ${
                        accountFilter === f ? "bg-primary text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}>
                {f === "all" ? "All" : f === "etoro" ? "eToro" : "TR"}
              </button>
            ))}
          </div>
        </div>

        {holdings.loading ? <LoadingSpinner /> :
         holdings.error ? <ErrorAlert message={holdings.error} /> :
         !holdings.data?.length ? <EmptyState message="No holdings for this filter." /> : (
          <HoldingsTable holdings={holdings.data} onRowClick={(t) => setHistoryTicker(t)} />
        )}
      </div>

      {historyTicker && (
        <HistoryModal ticker={historyTicker} onClose={() => setHistoryTicker(null)} />
      )}
    </div>
  );
}

// ── Top metric grid: combined total / today P&L / total return / cash ──

function SummaryGrid({
  detail, totals, loading, error,
}: {
  detail: SnapshotDetail | null;
  totals: DerivedTotals;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!detail) return null;

  const todayPnlUsd = combinedTodayPnl(detail);

  return (
    <div className="bg-white rounded-lg shadow p-5 grid grid-cols-2 md:grid-cols-4 gap-5">
      <BigMetric label="总资产 (USD)"
                 value={fmtUsd(detail.combined_total_usd)}
                 accent />
      <BigMetric label="总收益（自买入）"
                 value={totals.totalCost > 0 ? fmtSignedUsd(totals.totalReturnUsd) : "—"}
                 subValue={totals.totalCost > 0 ? `${signedPct(totals.totalReturnPct)}` : null}
                 color={pnlColor(totals.totalReturnUsd)} />
      <BigMetric label="今日 P&L"
                 value={todayPnlUsd != null ? fmtSignedUsd(todayPnlUsd) : "—"}
                 subValue={todayPnlUsd != null && detail.combined_total_usd
                   ? `${signedPct((todayPnlUsd / (detail.combined_total_usd - todayPnlUsd)) * 100)}`
                   : null}
                 color={pnlColor(todayPnlUsd)} />
      <BigMetric label="现金"
                 value={fmtUsd(detail.combined_cash_usd)}
                 subValue={detail.cash_ratio_pct != null ? `${detail.cash_ratio_pct.toFixed(1)}% cash ratio` : null} />
    </div>
  );
}

function AccountStrip({ detail }: { detail: SnapshotDetail | null }) {
  if (!detail) return null;
  return (
    <div className="bg-white rounded-lg shadow p-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
      <AcctBox title="eToro" lines={[
        ["Total", fmtUsd(detail.etoro_total_usd)],
        ["Cash", fmtUsd(detail.etoro_cash_usd)],
        ["Invested", fmtUsd(detail.etoro_invested_usd)],
      ]} />
      <AcctBox title="Trade Republic" lines={[
        ["Total", fmtEur(detail.tr_total_eur)],
        ["Cash", fmtEur(detail.tr_cash_eur)],
        ["Invested", fmtEur(detail.tr_invested_eur)],
        ["Today's Δ", detail.tr_pnl_day_eur != null ? `${detail.tr_pnl_day_eur >= 0 ? "+" : ""}€${detail.tr_pnl_day_eur.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—",
          pnlColor(detail.tr_pnl_day_eur)],
      ]} />
      <AcctBox title="FX" lines={[
        ["EUR/USD", detail.eur_usd_rate != null ? detail.eur_usd_rate.toFixed(4) : "—"],
      ]} />
    </div>
  );
}

function AcctBox({ title, lines }: { title: string; lines: [string, string, string?][] }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-2">{title}</div>
      <table className="w-full text-sm">
        <tbody>
          {lines.map(([label, value, color]) => (
            <tr key={label}>
              <td className="text-gray-500 py-0.5 pr-3 w-1/2">{label}</td>
              <td className={`font-medium py-0.5 ${color ?? ""}`}>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Big metric card ──

function BigMetric({
  label, value, subValue, color, accent,
}: { label: string; value: string; subValue?: string | null; color?: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`font-bold ${accent ? "text-primary text-2xl" : `text-xl ${color ?? "text-gray-800"}`}`}>
        {value}
      </div>
      {subValue && (
        <div className={`text-xs mt-0.5 ${color ?? "text-gray-500"}`}>{subValue}</div>
      )}
    </div>
  );
}

// ── Holdings table (clickable row → history modal) ──

function HoldingsTable({
  holdings, onRowClick,
}: { holdings: HoldingSnapshotRow[]; onRowClick: (ticker: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b">
            <th className="py-2 pr-4">Ticker</th>
            <th className="py-2 pr-4">Acct</th>
            <th className="py-2 pr-4 text-right">Shares</th>
            <th className="py-2 pr-4 text-right">Avg</th>
            <th className="py-2 pr-4 text-right">Now</th>
            <th className="py-2 pr-4 text-right">MV (USD)</th>
            <th className="py-2 pr-4 text-right">Pos %</th>
            <th className="py-2 pr-4 text-right">PnL %</th>
            <th className="py-2 pr-4 text-right">Day %</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.id}
                onClick={() => onRowClick(h.ticker)}
                className="border-b border-gray-100 hover:bg-primary/5 cursor-pointer"
                title="Click to see this ticker's history">
              <td className="py-1.5 pr-4 font-medium text-primary">{h.ticker}</td>
              <td className="py-1.5 pr-4 text-gray-500">{h.account ?? "—"}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.shares, 3)}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.avg_cost)}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.current_price)}</td>
              <td className="py-1.5 pr-4 text-right">{fmtUsd(h.market_value_usd)}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.position_percent)}%</td>
              <td className={`py-1.5 pr-4 text-right ${pnlColor(h.pnl_total_pct)}`}>{fmtNum(h.pnl_total_pct)}%</td>
              <td className={`py-1.5 pr-4 text-right ${pnlColor(h.pnl_day_pct)}`}>{fmtNum(h.pnl_day_pct)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoryModal({ ticker, onClose }: { ticker: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-lg max-w-3xl w-full mx-4 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-primary">{ticker} — history</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        </div>
        <TickerHistoryChart ticker={ticker} />
      </div>
    </div>
  );
}

// ── Derived totals: total return from per-holding cost back-derivation ──

interface DerivedTotals {
  totalCost: number;
  totalMv: number;
  totalReturnUsd: number;
  totalReturnPct: number;
}

function deriveTotals(holdings: HoldingSnapshotRow[] | null): DerivedTotals {
  if (!holdings) return { totalCost: 0, totalMv: 0, totalReturnUsd: 0, totalReturnPct: 0 };
  let totalCost = 0;
  let totalMv = 0;
  for (const h of holdings) {
    if (h.market_value_usd == null) continue;
    totalMv += h.market_value_usd;
    if (h.pnl_total_pct != null && h.pnl_total_pct > -100) {
      // cost = mv / (1 + pct/100)
      const cost = h.market_value_usd / (1 + h.pnl_total_pct / 100);
      totalCost += cost;
    } else {
      // Treat as if return is unknown — contribute mv as cost so it nets to 0
      totalCost += h.market_value_usd;
    }
  }
  const totalReturnUsd = totalMv - totalCost;
  const totalReturnPct = totalCost > 0 ? (totalReturnUsd / totalCost) * 100 : 0;
  return { totalCost, totalMv, totalReturnUsd, totalReturnPct };
}

function combinedTodayPnl(detail: SnapshotDetail): number | null {
  const etoro = detail.etoro_pnl_day_usd;
  const tr = detail.tr_pnl_day_eur;
  const rate = detail.eur_usd_rate;
  if (etoro == null && tr == null) return null;
  let total = 0;
  if (etoro != null) total += etoro;
  if (tr != null && rate != null) total += tr * rate;
  else if (tr != null) total += tr; // can't convert; bail to native sum
  return total;
}

// ── Format / color helpers ──

function fmtUsd(v: number | null | undefined): string {
  if (v == null) return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtEur(v: number | null | undefined): string {
  if (v == null) return "—";
  return `€${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtSignedUsd(v: number | null | undefined): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function signedPct(v: number | null | undefined): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function pnlColor(v: number | null | undefined): string {
  if (v == null || v === 0) return "";
  return v > 0 ? "text-green-700" : "text-red-700";
}
