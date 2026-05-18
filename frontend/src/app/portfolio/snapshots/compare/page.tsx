"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useGet } from "@/lib/useApi";
import type { HoldingDiff, SnapshotCompare, SnapshotListItem } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

type AccountFilter = "all" | "etoro" | "tr";
type ChangeFilter = "all" | "changed" | "added" | "removed" | "unchanged";

export default function ComparePage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <CompareInner />
    </Suspense>
  );
}

function CompareInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const { data: snapshots, loading: listLoading, error: listError } =
    useGet<SnapshotListItem[]>("/snapshots?limit=180");

  const initialFrom = searchParams.get("from") ?? "";
  const initialTo = searchParams.get("to") ?? "";
  const [fromDate, setFromDate] = useState(initialFrom);
  const [toDate, setToDate] = useState(initialTo);
  const [accountFilter, setAccountFilter] = useState<AccountFilter>("all");
  const [changeFilter, setChangeFilter] = useState<ChangeFilter>("changed");

  // When snapshots load and no explicit selection, default to the two newest
  useEffect(() => {
    if (!snapshots || snapshots.length < 2) return;
    if (!fromDate && !toDate) {
      setToDate(snapshots[0].report_date);
      setFromDate(snapshots[1].report_date);
    } else if (!fromDate) {
      setFromDate(snapshots[1].report_date);
    } else if (!toDate) {
      setToDate(snapshots[0].report_date);
    }
  }, [snapshots, fromDate, toDate]);

  // Sync URL params so the comparison is shareable / refresh-safe
  useEffect(() => {
    const q = new URLSearchParams();
    if (fromDate) q.set("from", fromDate);
    if (toDate) q.set("to", toDate);
    const qs = q.toString();
    router.replace(qs ? `/portfolio/snapshots/compare?${qs}` : "/portfolio/snapshots/compare");
  }, [fromDate, toDate, router]);

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-bold">Compare Snapshots</h1>
          <p className="text-sm text-gray-500 mt-1">Holding-level diff between two days.</p>
        </div>
        <Link href="/portfolio/snapshots" className="text-sm text-primary hover:underline">
          ← Back to Snapshots
        </Link>
      </div>

      {listLoading ? <LoadingSpinner /> :
       listError ? <ErrorAlert message={listError} /> :
       !snapshots || snapshots.length < 2 ? (
        <EmptyState message="Need at least two snapshots to compare. Upload another report first." />
      ) : (
        <>
          <DateSelectorBar
            snapshots={snapshots}
            fromDate={fromDate} setFromDate={setFromDate}
            toDate={toDate} setToDate={setToDate}
          />
          {fromDate && toDate && fromDate !== toDate && (
            <DiffPanel
              fromDate={fromDate} toDate={toDate}
              accountFilter={accountFilter} setAccountFilter={setAccountFilter}
              changeFilter={changeFilter} setChangeFilter={setChangeFilter}
            />
          )}
          {fromDate && toDate && fromDate === toDate && (
            <ErrorAlert message="From and To dates must differ." />
          )}
        </>
      )}
    </div>
  );
}

function DateSelectorBar({
  snapshots, fromDate, setFromDate, toDate, setToDate,
}: {
  snapshots: SnapshotListItem[];
  fromDate: string; setFromDate: (v: string) => void;
  toDate: string; setToDate: (v: string) => void;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-6">
      <DateSelect label="From (earlier)" value={fromDate} setValue={setFromDate} snapshots={snapshots} />
      <span className="text-gray-300 text-2xl pb-1">→</span>
      <DateSelect label="To (later)" value={toDate} setValue={setToDate} snapshots={snapshots} />
    </div>
  );
}

function DateSelect({
  label, value, setValue, snapshots,
}: { label: string; value: string; setValue: (v: string) => void; snapshots: SnapshotListItem[] }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <select value={value} onChange={(e) => setValue(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
        <option value="">— pick date —</option>
        {snapshots.map((s) => (
          <option key={s.id} value={s.report_date}>
            {s.report_date} · ${(s.combined_total_usd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </option>
        ))}
      </select>
    </div>
  );
}

function DiffPanel({
  fromDate, toDate, accountFilter, setAccountFilter, changeFilter, setChangeFilter,
}: {
  fromDate: string; toDate: string;
  accountFilter: AccountFilter; setAccountFilter: (v: AccountFilter) => void;
  changeFilter: ChangeFilter; setChangeFilter: (v: ChangeFilter) => void;
}) {
  const { data, loading, error } = useGet<SnapshotCompare>(
    `/snapshots/compare?from=${fromDate}&to=${toDate}`, [fromDate, toDate]
  );

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.holdings.filter((d) => {
      if (accountFilter !== "all" && d.account !== accountFilter) return false;
      if (changeFilter !== "all" && d.change_type !== changeFilter) return false;
      return true;
    });
  }, [data, accountFilter, changeFilter]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!data) return null;

  const counts: Record<HoldingDiff["change_type"], number> = {
    added: 0, removed: 0, changed: 0, unchanged: 0,
  };
  for (const d of data.holdings) counts[d.change_type]++;

  return (
    <>
      <SummaryRow data={data} counts={counts} />

      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold text-primary">
            Holdings diff {filtered.length !== data.holdings.length ? `(${filtered.length} / ${data.holdings.length})` : `(${data.holdings.length})`}
          </h2>
          <div className="flex flex-wrap gap-3 items-center">
            <FilterPill label="Account" options={[
              { value: "all", label: "All" },
              { value: "etoro", label: "eToro" },
              { value: "tr", label: "TR" },
            ]} value={accountFilter} onChange={(v) => setAccountFilter(v as AccountFilter)} />
            <FilterPill label="Change" options={[
              { value: "all", label: `All (${data.holdings.length})` },
              { value: "changed", label: `Changed (${counts.changed})` },
              { value: "added", label: `Added (${counts.added})` },
              { value: "removed", label: `Removed (${counts.removed})` },
              { value: "unchanged", label: `Unchanged (${counts.unchanged})` },
            ]} value={changeFilter} onChange={(v) => setChangeFilter(v as ChangeFilter)} />
          </div>
        </div>
        {!filtered.length ? (
          <EmptyState message="No holdings match the current filter." />
        ) : (
          <DiffTable rows={filtered} />
        )}
      </div>
    </>
  );
}

function SummaryRow({ data, counts }: { data: SnapshotCompare; counts: Record<HoldingDiff["change_type"], number> }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
      <Metric label={`Total ${data.from_date}`} value={fmtUsd(data.from_total_usd)} />
      <Metric label={`Total ${data.to_date}`} value={fmtUsd(data.to_total_usd)} accent />
      <Metric label="Total Δ" value={fmtSignedUsd(data.total_delta_usd)}
              color={pnlColor(data.total_delta_usd)} />
      <Metric label="Cash Δ" value={fmtSignedUsd(data.cash_delta_usd)}
              color={pnlColor(data.cash_delta_usd)} />
      <Metric label="Position changes" value={`${counts.added}↑ ${counts.removed}↓ ${counts.changed}≠`} />
    </div>
  );
}

function FilterPill({
  label, options, value, onChange,
}: { label: string; options: { value: string; label: string }[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-500">{label}</span>
      <div className="flex gap-1">
        {options.map((o) => (
          <button key={o.value} onClick={() => onChange(o.value)}
                  className={`px-2.5 py-1 rounded ${value === o.value ? "bg-primary text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function DiffTable({ rows }: { rows: HoldingDiff[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b">
            <th className="py-2 pr-3">Ticker</th>
            <th className="py-2 pr-3">Acct</th>
            <th className="py-2 pr-3">Change</th>
            <th className="py-2 pr-3 text-right">From shares</th>
            <th className="py-2 pr-3 text-right">To shares</th>
            <th className="py-2 pr-3 text-right">Δ shares</th>
            <th className="py-2 pr-3 text-right">From MV</th>
            <th className="py-2 pr-3 text-right">To MV</th>
            <th className="py-2 pr-3 text-right">Δ MV</th>
            <th className="py-2 pr-3 text-right">From PnL%</th>
            <th className="py-2 pr-3 text-right">To PnL%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d, i) => (
            <tr key={`${d.account}-${d.ticker}-${i}`} className={`border-b border-gray-100 ${rowBgForChange(d.change_type)}`}>
              <td className="py-1.5 pr-3 font-medium">{d.ticker}</td>
              <td className="py-1.5 pr-3 text-gray-500">{d.account ?? "—"}</td>
              <td className="py-1.5 pr-3"><ChangeBadge t={d.change_type} /></td>
              <td className="py-1.5 pr-3 text-right">{fmtNum(d.from_shares, 3)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtNum(d.to_shares, 3)}</td>
              <td className={`py-1.5 pr-3 text-right ${pnlColor(d.shares_delta)}`}>{fmtSigned(d.shares_delta, 3)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtUsd(d.from_market_value_usd)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtUsd(d.to_market_value_usd)}</td>
              <td className={`py-1.5 pr-3 text-right ${pnlColor(d.value_delta_usd)}`}>{fmtSignedUsd(d.value_delta_usd)}</td>
              <td className={`py-1.5 pr-3 text-right ${pnlColor(d.from_pnl_pct)}`}>{fmtNum(d.from_pnl_pct)}%</td>
              <td className={`py-1.5 pr-3 text-right ${pnlColor(d.to_pnl_pct)}`}>{fmtNum(d.to_pnl_pct)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChangeBadge({ t }: { t: HoldingDiff["change_type"] }) {
  const map = {
    added: { label: "+ added", cls: "bg-green-100 text-green-800" },
    removed: { label: "− removed", cls: "bg-red-100 text-red-800" },
    changed: { label: "Δ changed", cls: "bg-yellow-100 text-yellow-800" },
    unchanged: { label: "— same", cls: "bg-gray-100 text-gray-600" },
  } as const;
  const entry = map[t];
  return <span className={`inline-block px-2 py-0.5 rounded text-xs ${entry.cls}`}>{entry.label}</span>;
}

function rowBgForChange(t: HoldingDiff["change_type"]): string {
  switch (t) {
    case "added": return "bg-green-50";
    case "removed": return "bg-red-50";
    case "changed": return "bg-yellow-50";
    default: return "";
  }
}

// ── Format / color helpers ──

function Metric({ label, value, accent, color }: { label: string; value: string; accent?: boolean; color?: string }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`font-semibold ${accent ? "text-primary text-lg" : color ?? "text-gray-800"}`}>{value}</div>
    </div>
  );
}

function fmtUsd(v: number | null | undefined): string {
  if (v == null) return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtSignedUsd(v: number | null | undefined): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function fmtSigned(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(decimals)}`;
}

function pnlColor(v: number | null | undefined): string {
  if (v == null || v === 0) return "";
  return v > 0 ? "text-green-700" : "text-red-700";
}
