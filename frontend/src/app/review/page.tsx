"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useGet } from "@/lib/useApi";
import type {
  ExecutionRead,
  RecommendationListItem,
  ReviewStats,
  SimulationRead,
  SkipReason,
} from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

type StatusFilter = "" | "pending" | "executed" | "skipped" | "partial";
type ModalKind = "execute" | "skip" | "simulate" | null;

export default function ReviewPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <ReviewPageInner />
    </Suspense>
  );
}

function buildQS(params: Record<string, string>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v) qs.set(k, v);
  }
  return qs.toString() ? `?${qs.toString()}` : "";
}

function ReviewPageInner() {
  const searchParams = useSearchParams();
  const initialTicker = searchParams.get("ticker") ?? "";

  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [ticker, setTicker] = useState(initialTicker);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");

  const statsQS = buildQS({ from, to });
  const listQS = buildQS({ from, to, ticker: ticker.toUpperCase(), status: statusFilter });

  const stats = useGet<ReviewStats>(`/review/stats${statsQS}`, [from, to]);
  const list = useGet<RecommendationListItem[]>(`/recommendations${listQS}`, [from, to, ticker, statusFilter]);

  const [modal, setModal] = useState<{ kind: ModalKind; rec: RecommendationListItem | null }>({ kind: null, rec: null });
  const closeModal = () => setModal({ kind: null, rec: null });
  const onActionDone = () => { closeModal(); list.refetch(); stats.refetch(); };

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">Trade Review</h1>
        <Link href="/review/regrets" className="text-sm text-primary hover:underline">
          → Regrets list
        </Link>
      </div>

      <StatsCard stats={stats.data} loading={stats.loading} error={stats.error} />

      <FilterBar
        from={from} setFrom={setFrom}
        to={to} setTo={setTo}
        ticker={ticker} setTicker={setTicker}
        statusFilter={statusFilter} setStatusFilter={setStatusFilter}
      />

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold text-primary mb-3">
          Recommendations {list.data ? `(${list.data.length})` : ""}
        </h2>
        {list.loading ? <LoadingSpinner /> :
         list.error ? <ErrorAlert message={list.error} onRetry={list.refetch} /> :
         !list.data?.length ? <EmptyState message="No recommendations match the filters." /> :
          <RecsTable recs={list.data} onAction={(kind, rec) => setModal({ kind, rec })} />}
      </div>

      {modal.kind && modal.rec && (
        <ModalShell title={modalTitle(modal.kind, modal.rec)} onClose={closeModal}>
          {modal.kind === "execute" && <ExecuteForm rec={modal.rec} onDone={onActionDone} />}
          {modal.kind === "skip" && <SkipForm rec={modal.rec} onDone={onActionDone} />}
          {modal.kind === "simulate" && <SimulateForm rec={modal.rec} onDone={onActionDone} />}
        </ModalShell>
      )}
    </div>
  );
}

// ── Stats card ──

function StatsCard({ stats, loading, error }: { stats: ReviewStats | null; loading: boolean; error: string | null }) {
  if (loading) return <div className="bg-white rounded-lg shadow p-4"><LoadingSpinner /></div>;
  if (error) return <ErrorAlert message={error} />;
  if (!stats) return null;
  return (
    <div className="bg-white rounded-lg shadow p-4 grid grid-cols-2 md:grid-cols-6 gap-4 text-sm">
      <Stat label="Total" value={String(stats.total)} accent />
      <Stat label="Executed" value={String(stats.executed)} color="text-green-700" />
      <Stat label="Skipped" value={String(stats.skipped)} color="text-red-700" />
      <Stat label="Pending" value={String(stats.pending)} color="text-gray-500" />
      <Stat label="Execution rate" value={stats.execution_rate_pct != null ? `${stats.execution_rate_pct}%` : "—"} />
      <Stat label="Avg sim PnL" value={stats.avg_sim_pnl_pct != null ? `${stats.avg_sim_pnl_pct}%` : "—"}
            color={stats.avg_sim_pnl_pct != null && stats.avg_sim_pnl_pct > 0 ? "text-green-700" : "text-red-700"} />
    </div>
  );
}

function Stat({ label, value, color, accent }: { label: string; value: string; color?: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`font-semibold ${accent ? "text-primary text-lg" : color ?? "text-gray-800"}`}>{value}</div>
    </div>
  );
}

// ── Filter bar ──

function FilterBar(props: {
  from: string; setFrom: (v: string) => void;
  to: string; setTo: (v: string) => void;
  ticker: string; setTicker: (v: string) => void;
  statusFilter: StatusFilter; setStatusFilter: (v: StatusFilter) => void;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-4">
      <FilterField label="From">
        <input type="date" value={props.from} onChange={(e) => props.setFrom(e.target.value)}
               className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
      </FilterField>
      <FilterField label="To">
        <input type="date" value={props.to} onChange={(e) => props.setTo(e.target.value)}
               className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
      </FilterField>
      <FilterField label="Ticker">
        <input type="text" value={props.ticker} onChange={(e) => props.setTicker(e.target.value)}
               placeholder="NVDA" className="border rounded px-2 py-1 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-primary" />
      </FilterField>
      <FilterField label="Status">
        <select value={props.statusFilter} onChange={(e) => props.setStatusFilter(e.target.value as StatusFilter)}
                className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="executed">Executed</option>
          <option value="skipped">Skipped</option>
          <option value="partial">Partial</option>
        </select>
      </FilterField>
      {(props.from || props.to || props.ticker || props.statusFilter) && (
        <button onClick={() => { props.setFrom(""); props.setTo(""); props.setTicker(""); props.setStatusFilter(""); }}
                className="text-xs text-gray-500 hover:text-gray-700 underline">
          Clear
        </button>
      )}
    </div>
  );
}

function FilterField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      {children}
    </div>
  );
}

// ── Recs table ──

function RecsTable({
  recs,
  onAction,
}: {
  recs: RecommendationListItem[];
  onAction: (kind: Exclude<ModalKind, null>, rec: RecommendationListItem) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b">
            <th className="py-2 pr-3">Date</th>
            <th className="py-2 pr-3">Ticker</th>
            <th className="py-2 pr-3">Direction</th>
            <th className="py-2 pr-3">Priority</th>
            <th className="py-2 pr-3">Acct</th>
            <th className="py-2 pr-3 text-right">Ref price</th>
            <th className="py-2 pr-3">Status</th>
            <th className="py-2 pr-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {recs.map((r) => (
            <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-1.5 pr-3 text-gray-500">{r.report_date ?? "—"}</td>
              <td className="py-1.5 pr-3 font-medium">{r.ticker}</td>
              <td className="py-1.5 pr-3">{r.direction}</td>
              <td className="py-1.5 pr-3 text-gray-500 max-w-[180px] truncate" title={r.priority ?? ""}>
                {r.priority ?? "—"}
              </td>
              <td className="py-1.5 pr-3 text-gray-500">{r.account ?? "—"}</td>
              <td className="py-1.5 pr-3 text-right">{r.reference_price != null ? r.reference_price.toFixed(2) : "—"}</td>
              <td className="py-1.5 pr-3"><StatusBadge status={r.execution_status} /></td>
              <td className="py-1.5 pr-3 space-x-1 whitespace-nowrap">
                {!r.has_execution && (
                  <>
                    <ActionButton onClick={() => onAction("execute", r)}>Exec</ActionButton>
                    <ActionButton onClick={() => onAction("skip", r)}>Skip</ActionButton>
                  </>
                )}
                <ActionButton onClick={() => onAction("simulate", r)}>Sim</ActionButton>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: string | null }) {
  const map: Record<string, { label: string; cls: string }> = {
    executed: { label: "✓ executed", cls: "bg-green-100 text-green-800" },
    skipped: { label: "✗ skipped", cls: "bg-red-100 text-red-800" },
    partial: { label: "◐ partial", cls: "bg-yellow-100 text-yellow-800" },
  };
  if (!status) return <span className="text-xs text-gray-400">pending</span>;
  const entry = map[status] ?? { label: status, cls: "bg-gray-100 text-gray-700" };
  return <span className={`inline-block px-2 py-0.5 rounded text-xs ${entry.cls}`}>{entry.label}</span>;
}

function ActionButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
            className="px-2 py-0.5 text-xs rounded border border-gray-300 hover:bg-primary hover:text-white hover:border-primary">
      {children}
    </button>
  );
}

// ── Modal shell ──

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-primary">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function modalTitle(kind: ModalKind, rec: RecommendationListItem): string {
  const base = `${rec.ticker} · ${rec.direction}`;
  if (kind === "execute") return `Execute — ${base}`;
  if (kind === "skip") return `Skip — ${base}`;
  if (kind === "simulate") return `Simulate — ${base}`;
  return base;
}

// ── Forms ──

function ExecuteForm({ rec, onDone }: { rec: RecommendationListItem; onDone: () => void }) {
  const [actualPrice, setActualPrice] = useState(rec.reference_price?.toString() ?? "");
  const [actualShares, setActualShares] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<"executed" | "partial">("executed");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true); setError(null);
    try {
      await api.post<ExecutionRead>(`/recommendations/${rec.id}/execute`, {
        status,
        actual_price: parseFloat(actualPrice),
        actual_shares: parseFloat(actualShares),
        execution_date: date,
      });
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Execute failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <Field label="Status">
        <select value={status} onChange={(e) => setStatus(e.target.value as "executed" | "partial")} className={inputCls}>
          <option value="executed">Executed</option>
          <option value="partial">Partial</option>
        </select>
      </Field>
      <Field label="Actual price ($)">
        <input type="number" step="0.01" value={actualPrice} onChange={(e) => setActualPrice(e.target.value)} className={inputCls} />
      </Field>
      <Field label="Actual shares">
        <input type="number" step="0.001" value={actualShares} onChange={(e) => setActualShares(e.target.value)} className={inputCls} />
      </Field>
      <Field label="Execution date">
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputCls} />
      </Field>
      {error && <p className="text-red-600">{error}</p>}
      <SubmitBar busy={busy} disabled={!actualPrice || !actualShares} onClick={submit} label="Record" />
    </div>
  );
}

function SkipForm({ rec, onDone }: { rec: RecommendationListItem; onDone: () => void }) {
  const [reason, setReason] = useState<SkipReason>("forgot");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true); setError(null);
    try {
      await api.post<ExecutionRead>(`/recommendations/${rec.id}/skip`, {
        skip_reason: reason,
        skip_note: note || null,
      });
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Skip failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <Field label="Reason">
        <select value={reason} onChange={(e) => setReason(e.target.value as SkipReason)} className={inputCls}>
          <option value="forgot">Forgot</option>
          <option value="disagreed">Disagreed</option>
          <option value="no_cash">No cash</option>
          <option value="waiting_better_price">Waiting for better price</option>
          <option value="other">Other</option>
        </select>
      </Field>
      <Field label="Note (optional)">
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className={inputCls} />
      </Field>
      {error && <p className="text-red-600">{error}</p>}
      <SubmitBar busy={busy} disabled={false} onClick={submit} label="Record skip" />
    </div>
  );
}

function SimulateForm({ rec, onDone }: { rec: RecommendationListItem; onDone: () => void }) {
  const [entryPrice, setEntryPrice] = useState(rec.reference_price?.toString() ?? "");
  const [entryDate, setEntryDate] = useState(rec.report_date ?? new Date().toISOString().slice(0, 10));
  const [entryShares, setEntryShares] = useState("");
  const [exitPrice, setExitPrice] = useState("");
  const [exitDate, setExitDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SimulationRead | null>(null);

  async function submit() {
    setBusy(true); setError(null);
    try {
      const sim = await api.post<SimulationRead>("/simulations", {
        recommendation_id: rec.id,
        sim_entry_price: parseFloat(entryPrice),
        sim_entry_date: entryDate,
        sim_entry_shares: parseFloat(entryShares),
        sim_exit_price: exitPrice ? parseFloat(exitPrice) : null,
        sim_exit_date: exitDate || null,
      });
      setResult(sim);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Simulation failed");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    const pnlColor = result.sim_pnl_usd != null && result.sim_pnl_usd >= 0 ? "text-green-700" : "text-red-700";
    return (
      <div className="space-y-3 text-sm">
        <div className="bg-gray-50 rounded p-3 space-y-1">
          <div><span className="text-gray-500">Entry:</span> {result.sim_entry_shares} shares × ${result.sim_entry_price.toFixed(2)} on {result.sim_entry_date}</div>
          {result.sim_exit_price != null && (
            <div><span className="text-gray-500">Exit:</span> ${result.sim_exit_price.toFixed(2)} on {result.sim_exit_date ?? "—"}</div>
          )}
          <div className={`font-semibold ${pnlColor}`}>
            Theoretical PnL: {result.sim_pnl_usd != null ? `$${result.sim_pnl_usd.toFixed(2)}` : "—"}
            {result.sim_pnl_pct != null && ` (${result.sim_pnl_pct.toFixed(2)}%)`}
          </div>
          {result.regret_usd != null && (
            <div className="text-orange-700">Regret vs actual: ${result.regret_usd.toFixed(2)}</div>
          )}
          {result.sim_exit_price == null && (
            <div className="text-xs text-gray-500">Open simulation — set an exit price later to compute PnL.</div>
          )}
        </div>
        <SubmitBar busy={false} disabled={false} onClick={onDone} label="Done" />
      </div>
    );
  }

  return (
    <div className="space-y-3 text-sm">
      <Field label="Entry price ($)">
        <input type="number" step="0.01" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} className={inputCls} />
      </Field>
      <Field label="Entry date">
        <input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} className={inputCls} />
      </Field>
      <Field label="Shares">
        <input type="number" step="0.001" value={entryShares} onChange={(e) => setEntryShares(e.target.value)} className={inputCls} />
      </Field>
      <Field label="Exit price ($) — leave blank to keep open">
        <input type="number" step="0.01" value={exitPrice} onChange={(e) => setExitPrice(e.target.value)} className={inputCls} />
      </Field>
      <Field label="Exit date (optional)">
        <input type="date" value={exitDate} onChange={(e) => setExitDate(e.target.value)} className={inputCls} />
      </Field>
      {error && <p className="text-red-600">{error}</p>}
      <SubmitBar busy={busy} disabled={!entryPrice || !entryShares || !entryDate} onClick={submit} label="Run" />
    </div>
  );
}

const inputCls = "w-full border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-0.5">{label}</label>
      {children}
    </div>
  );
}

function SubmitBar({ busy, disabled, onClick, label }: { busy: boolean; disabled: boolean; onClick: () => void; label: string }) {
  return (
    <button onClick={onClick} disabled={busy || disabled}
            className="w-full bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary-light disabled:opacity-50">
      {busy ? "Working..." : label}
    </button>
  );
}
