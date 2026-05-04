"use client";

import { api } from "@/lib/api";
import type { Broker, BrokerPortfolioMapping, BrokerSyncLog, BrokerSyncStatus, Portfolio } from "@/types";
import { useEffect, useRef, useState } from "react";

const BROKER_LABELS: Record<Broker, string> = { etoro: "eToro", tr: "Trade Republic" };
const BROKER_COLORS: Record<Broker, string> = {
  etoro: "bg-emerald-50 border-emerald-200",
  tr: "bg-blue-50 border-blue-200",
};

function StatusDot({ status }: { status: BrokerSyncLog["status"] | "none" }) {
  const map = {
    running: "bg-yellow-400 animate-pulse",
    success: "bg-bull-text",
    failed: "bg-bear-text",
    partial: "bg-yellow-500",
    none: "bg-gray-300",
  };
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${map[status]}`} />;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "刚刚";
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  return `${Math.floor(h / 24)} 天前`;
}

function BrokerCard({
  broker,
  log,
  mapping,
  portfolios,
  onMapChange,
  onSync,
  syncing,
}: {
  broker: Broker;
  log: BrokerSyncLog | null;
  mapping: BrokerPortfolioMapping | null;
  portfolios: Portfolio[];
  onMapChange: (broker: Broker, portfolioId: string) => void;
  onSync: (broker: Broker) => void;
  syncing: boolean;
}) {
  const status = log?.status ?? "none";
  return (
    <div className={`rounded-lg border p-6 ${BROKER_COLORS[broker]}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <StatusDot status={status} />
          <h2 className="font-bold text-primary text-lg">{BROKER_LABELS[broker]}</h2>
        </div>
        <button
          onClick={() => onSync(broker)}
          disabled={syncing}
          className="px-4 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary-light disabled:opacity-50"
        >
          {syncing ? "同步中..." : "立即同步"}
        </button>
      </div>

      {/* Last sync info */}
      <div className="grid grid-cols-3 gap-3 text-sm mb-4">
        <div>
          <p className="text-xs text-gray-400">上次同步</p>
          <p className="font-medium mt-0.5">
            {log?.finished_at ? timeAgo(log.finished_at) : "从未"}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400">读取持仓</p>
          <p className="font-medium mt-0.5">{log?.positions_read ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400">同步成功</p>
          <p className={`font-medium mt-0.5 ${status === "failed" ? "text-bear-text" : ""}`}>
            {status === "failed" ? "失败" : (log?.positions_synced ?? "—")}
          </p>
        </div>
      </div>

      {status === "failed" && log?.error_msg && (
        <p className="text-xs text-bear-text bg-bear-bg rounded px-3 py-2 mb-3">
          {log.error_msg}
        </p>
      )}

      {/* Portfolio mapping */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">同步到持仓组合</label>
        <select
          className="w-full border rounded-md px-3 py-2 text-sm bg-white"
          value={mapping?.portfolio_id ?? ""}
          onChange={(e) => { if (e.target.value) onMapChange(broker, e.target.value); }}
        >
          <option value="">— 未配置 —</option>
          {portfolios.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        {mapping && (
          <p className="text-xs text-gray-400 mt-1">
            当前映射：<span className="font-medium text-gray-600">{mapping.portfolio_name}</span>
          </p>
        )}
      </div>
    </div>
  );
}

function LogRow({ log }: { log: BrokerSyncLog }) {
  const statusColors = {
    success: "text-bull-text",
    failed: "text-bear-text",
    partial: "text-yellow-600",
    running: "text-yellow-500",
  };
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-2.5 text-sm font-medium">{BROKER_LABELS[log.broker as Broker] ?? log.broker}</td>
      <td className={`px-4 py-2.5 text-sm font-semibold ${statusColors[log.status] ?? ""}`}>
        {log.status}
      </td>
      <td className="px-4 py-2.5 text-sm">{log.positions_read}</td>
      <td className="px-4 py-2.5 text-sm">{log.positions_synced}</td>
      <td className="px-4 py-2.5 text-sm text-gray-400">
        {new Date(log.started_at).toLocaleString("zh-CN")}
      </td>
      <td className="px-4 py-2.5 text-xs text-gray-400 max-w-48 truncate">
        {log.error_msg ?? "—"}
      </td>
    </tr>
  );
}

export default function BrokerSyncPage() {
  const [status, setStatus] = useState<BrokerSyncStatus | null>(null);
  const [logs, setLogs] = useState<BrokerSyncLog[]>([]);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingBroker, setSyncingBroker] = useState<Broker | "all" | null>(null);
  const [syncMsg, setSyncMsg] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refresh() {
    const [s, l] = await Promise.all([
      api.get<BrokerSyncStatus>("/broker-sync/status"),
      api.get<BrokerSyncLog[]>("/broker-sync/logs"),
    ]);
    setStatus(s);
    setLogs(l);
  }

  useEffect(() => {
    Promise.all([
      api.get<BrokerSyncStatus>("/broker-sync/status"),
      api.get<BrokerSyncLog[]>("/broker-sync/logs"),
      api.get<Portfolio[]>("/portfolios"),
    ]).then(([s, l, p]) => {
      setStatus(s);
      setLogs(l);
      setPortfolios(p);
    }).finally(() => setLoading(false));
  }, []);

  // Poll while a sync is running
  useEffect(() => {
    if (syncingBroker) {
      pollRef.current = setInterval(async () => {
        await refresh();
        const s = await api.get<BrokerSyncStatus>("/broker-sync/status");
        const running =
          s.etoro_last_sync?.status === "running" ||
          s.tr_last_sync?.status === "running";
        if (!running) {
          setSyncingBroker(null);
          clearInterval(pollRef.current!);
        }
      }, 3000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [syncingBroker]);

  async function handleSync(broker: Broker | "all") {
    setSyncingBroker(broker);
    setSyncMsg("");
    try {
      const res = await api.post<{ message: string }>(`/broker-sync/trigger?broker=${broker}`);
      setSyncMsg(res.message);
    } catch (err: unknown) {
      setSyncMsg(err instanceof Error ? err.message : "触发失败");
      setSyncingBroker(null);
    }
  }

  async function handleMapChange(broker: Broker, portfolioId: string) {
    await api.post("/broker-sync/mappings", { broker, portfolio_id: portfolioId });
    await refresh();
  }

  if (loading) return <p className="text-gray-400 text-sm">加载中...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Broker Sync</h1>
          <p className="text-sm text-gray-400 mt-0.5">从 eToro 和 Trade Republic 读取实时持仓并同步到投资组合</p>
        </div>
        <button
          onClick={() => handleSync("all")}
          disabled={syncingBroker !== null}
          className="px-5 py-2 bg-accent text-white text-sm font-medium rounded-md hover:opacity-90 disabled:opacity-50"
        >
          {syncingBroker ? "同步中..." : "全部同步"}
        </button>
      </div>

      {syncMsg && (
        <div className="mb-4 bg-primary/5 border border-primary/20 rounded-lg px-4 py-3 text-sm text-primary">
          {syncMsg}
        </div>
      )}

      {/* Broker cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
        {(["etoro", "tr"] as Broker[]).map((broker) => (
          <BrokerCard
            key={broker}
            broker={broker}
            log={broker === "etoro" ? status?.etoro_last_sync ?? null : status?.tr_last_sync ?? null}
            mapping={broker === "etoro" ? status?.etoro_mapping ?? null : status?.tr_mapping ?? null}
            portfolios={portfolios}
            onMapChange={handleMapChange}
            onSync={handleSync}
            syncing={syncingBroker === broker || syncingBroker === "all"}
          />
        ))}
      </div>

      {/* How it works */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-semibold text-primary mb-3">使用说明</h2>
        <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
          <li>在上方为 eToro 和 TR 各选择一个对应的投资组合（用于存储同步的持仓）</li>
          <li>点击「立即同步」或「全部同步」，系统会打开浏览器自动读取持仓</li>
          <li>若浏览器要求登录，请在弹出窗口中完成登录后按 Enter（首次使用需要，之后会记住 Session）</li>
          <li>同步成功后，持仓数据会自动写入对应组合，可在「Portfolios」中查看</li>
        </ol>
        <div className="mt-4 bg-gray-50 rounded px-4 py-3 text-xs text-gray-500 font-mono">
          # 也可手动运行同步脚本<br />
          python scripts/sync_brokers.py --broker all --token &lt;your-jwt-token&gt;
        </div>
      </div>

      {/* Sync history */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-primary">同步历史</h2>
          <button onClick={refresh} className="text-xs text-accent hover:underline">刷新</button>
        </div>
        {logs.length === 0 ? (
          <p className="text-gray-400 text-sm p-6">暂无同步记录</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">平台</th>
                <th className="px-4 py-3 text-left">状态</th>
                <th className="px-4 py-3 text-left">读取</th>
                <th className="px-4 py-3 text-left">同步</th>
                <th className="px-4 py-3 text-left">时间</th>
                <th className="px-4 py-3 text-left">错误</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log) => <LogRow key={log.id} log={log} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
