"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useGet } from "@/lib/useApi";
import type {
  HoldingSnapshotRow,
  ReportUploadResponse,
  SnapshotDetail,
  SnapshotListItem,
} from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

type AccountFilter = "all" | "etoro" | "tr";

export default function SnapshotsPage() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [accountFilter, setAccountFilter] = useState<AccountFilter>("all");
  const [uploadStatus, setUploadStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [html, setHtml] = useState("");
  const [uploading, setUploading] = useState(false);

  const { data: snapshots, loading: listLoading, error: listError, refetch: refetchList } =
    useGet<SnapshotListItem[]>("/snapshots");

  // Auto-select the newest snapshot once the list arrives
  const effectiveDate =
    selectedDate ?? (snapshots && snapshots.length > 0 ? snapshots[0].report_date : null);

  async function handleUpload() {
    if (!html.trim()) return;
    setUploading(true);
    setUploadStatus(null);
    try {
      const res = await api.post<ReportUploadResponse>("/reports/upload", { html });
      setUploadStatus({
        ok: true,
        msg: `Snapshot ${res.report_date}: ${res.holdings_count} holdings, ${res.recommendations_persisted}/${res.recommendations_parsed} recommendations persisted`,
      });
      setHtml("");
      setSelectedDate(res.report_date);
      refetchList();
    } catch (err) {
      setUploadStatus({
        ok: false,
        msg: err instanceof ApiError ? err.message : "Upload failed",
      });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Portfolio Snapshots</h1>

      <UploadCard
        html={html}
        setHtml={setHtml}
        uploading={uploading}
        onUpload={handleUpload}
        status={uploadStatus}
      />

      {listLoading ? (
        <LoadingSpinner message="Loading snapshots..." />
      ) : listError ? (
        <ErrorAlert message={listError} onRetry={refetchList} />
      ) : !snapshots || snapshots.length === 0 ? (
        <EmptyState message="No snapshots yet. Paste a report HTML above to ingest the first one." />
      ) : (
        <>
          <DateSelector
            snapshots={snapshots}
            value={effectiveDate}
            onChange={setSelectedDate}
          />
          {effectiveDate && (
            <SnapshotView date={effectiveDate} accountFilter={accountFilter} setAccountFilter={setAccountFilter} />
          )}
        </>
      )}
    </div>
  );
}

// ── Upload card ──

function UploadCard({
  html,
  setHtml,
  uploading,
  onUpload,
  status,
}: {
  html: string;
  setHtml: (v: string) => void;
  uploading: boolean;
  onUpload: () => void;
  status: { ok: boolean; msg: string } | null;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-primary">Upload report HTML</h2>
        <span className="text-xs text-gray-500">paste full HTML, POSTs to /reports/upload</span>
      </div>
      <textarea
        value={html}
        onChange={(e) => setHtml(e.target.value)}
        placeholder="<html>...</html>"
        rows={4}
        className="w-full font-mono text-xs px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
      />
      <div className="flex items-center gap-3">
        <button
          onClick={onUpload}
          disabled={uploading || !html.trim()}
          className="bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary-light disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload"}
        </button>
        {status && (
          <span className={`text-sm ${status.ok ? "text-green-700" : "text-red-700"}`}>
            {status.msg}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Date selector ──

function DateSelector({
  snapshots,
  value,
  onChange,
}: {
  snapshots: SnapshotListItem[];
  value: string | null;
  onChange: (date: string) => void;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4 flex items-center gap-4">
      <label className="text-sm text-gray-600">Snapshot date</label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {snapshots.map((s) => (
          <option key={s.id} value={s.report_date}>
            {s.report_date} · {s.source} · ${fmtMoney(s.combined_total_usd)} · {s.holdings_count} holdings
          </option>
        ))}
      </select>
    </div>
  );
}

// ── Snapshot view (summary + holdings) ──

function SnapshotView({
  date,
  accountFilter,
  setAccountFilter,
}: {
  date: string;
  accountFilter: AccountFilter;
  setAccountFilter: (f: AccountFilter) => void;
}) {
  const { data: detail, loading: dLoading, error: dError } =
    useGet<SnapshotDetail>(`/snapshots/${date}`, [date]);
  const holdingsPath =
    accountFilter === "all" ? `/snapshots/${date}/holdings` : `/snapshots/${date}/holdings?account=${accountFilter}`;
  const { data: holdings, loading: hLoading, error: hError } =
    useGet<HoldingSnapshotRow[]>(holdingsPath, [date, accountFilter]);

  return (
    <>
      <SummaryCard detail={detail} loading={dLoading} error={dError} />

      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-primary">
            Holdings {holdings ? `(${holdings.length})` : ""}
          </h2>
          <div className="flex gap-1">
            {(["all", "etoro", "tr"] as AccountFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setAccountFilter(f)}
                className={`px-3 py-1 text-xs rounded ${
                  accountFilter === f ? "bg-primary text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {f === "all" ? "All" : f === "etoro" ? "eToro" : "TR"}
              </button>
            ))}
          </div>
        </div>

        {hLoading ? <LoadingSpinner /> :
         hError ? <ErrorAlert message={hError} /> :
         !holdings?.length ? <EmptyState message="No holdings for this filter." /> : (
          <HoldingsTable holdings={holdings} />
        )}
      </div>
    </>
  );
}

function SummaryCard({
  detail,
  loading,
  error,
}: {
  detail: SnapshotDetail | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!detail) return null;
  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold text-primary">Account Summary</h2>
        <span className="text-xs text-gray-500">source: {detail.source}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <Metric label="Combined Total" value={`$${fmtMoney(detail.combined_total_usd)}`} accent />
        <Metric label="Combined Cash" value={`$${fmtMoney(detail.combined_cash_usd)}`} />
        <Metric label="Cash Ratio" value={detail.cash_ratio_pct != null ? `${detail.cash_ratio_pct}%` : "—"} />
        <Metric label="EUR/USD" value={detail.eur_usd_rate != null ? detail.eur_usd_rate.toFixed(4) : "—"} />
        <Metric label="eToro Total" value={`$${fmtMoney(detail.etoro_total_usd)}`} />
        <Metric label="eToro Cash" value={`$${fmtMoney(detail.etoro_cash_usd)}`} />
        <Metric label="TR Total" value={`€${fmtMoney(detail.tr_total_eur)}`} />
        <Metric label="TR Cash" value={`€${fmtMoney(detail.tr_cash_eur)}`} />
      </div>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`font-semibold ${accent ? "text-primary text-lg" : "text-gray-800"}`}>{value}</div>
    </div>
  );
}

function HoldingsTable({ holdings }: { holdings: HoldingSnapshotRow[] }) {
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
            <tr key={h.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-1.5 pr-4 font-medium">{h.ticker}</td>
              <td className="py-1.5 pr-4 text-gray-500">{h.account ?? "—"}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.shares, 3)}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.avg_cost)}</td>
              <td className="py-1.5 pr-4 text-right">{fmtNum(h.current_price)}</td>
              <td className="py-1.5 pr-4 text-right">${fmtMoney(h.market_value_usd)}</td>
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

// ── Format helpers ──

function fmtMoney(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function pnlColor(v: number | null | undefined): string {
  if (v == null) return "";
  if (v > 0) return "text-green-600";
  if (v < 0) return "text-red-600";
  return "";
}
