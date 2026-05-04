"use client";

import { api } from "@/lib/api";
import type { SimulatedPortfolio, SimulatedPosition } from "@/types";
import Link from "next/link";
import { useEffect, useState } from "react";

const SUB_NAV = [
  { href: "/simulation", label: "概览" },
  { href: "/simulation/positions", label: "持仓" },
  { href: "/simulation/trades", label: "交易" },
  { href: "/simulation/comparison", label: "对比实盘" },
  { href: "/simulation/review", label: "复盘" },
];

function fmt(n: number, d = 2) {
  return n.toFixed(d);
}

function PnlCell({ value, pct }: { value: number | null; pct: number | null }) {
  if (value === null) return <span className="text-gray-300">—</span>;
  const pos = value >= 0;
  return (
    <span className={pos ? "text-bull-text" : "text-bear-text"}>
      {pos ? "+" : ""}
      {fmt(value)} {pct !== null ? `(${pos ? "+" : ""}${fmt(pct)}%)` : ""}
    </span>
  );
}

function DirectionBadge({ direction }: { direction: string }) {
  const isLong = direction === "LONG";
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${
        isLong ? "bg-bull-bg text-bull-text" : "bg-bear-bg text-bear-text"
      }`}
    >
      {isLong ? "做多" : "做空"}
    </span>
  );
}

export default function PositionsPage() {
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [positions, setPositions] = useState<SimulatedPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function load(pid: string, quiet = false) {
    if (!quiet) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await api.get<SimulatedPosition[]>(`/simulation/portfolios/${pid}/positions`);
      setPositions(data);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    api.get<SimulatedPortfolio[]>("/simulation/portfolios").then((list) => {
      if (list[0]) {
        setPortfolioId(list[0].id);
        load(list[0].id);
      } else {
        setLoading(false);
      }
    });
  }, []);

  if (loading) return <p className="text-gray-400 text-sm">加载中...</p>;

  if (!portfolioId) {
    return (
      <div className="text-center mt-20">
        <p className="text-gray-400 mb-4">未找到模拟账户</p>
        <Link href="/simulation" className="text-accent text-sm hover:underline">
          前往创建
        </Link>
      </div>
    );
  }

  const totalPnl = positions.reduce((s, p) => s + (p.unrealized_pnl ?? 0), 0);
  const totalMargin = positions.reduce((s, p) => s + p.margin_used, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">模拟盘</h1>
      </div>

      {/* Sub nav */}
      <div className="flex gap-1 mb-6 border-b">
        {SUB_NAV.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              n.href === "/simulation/positions"
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-primary"
            }`}
          >
            {n.label}
          </Link>
        ))}
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-6 text-sm">
          <span>
            <span className="text-gray-400">持仓数</span>
            <span className="ml-2 font-semibold">{positions.length}</span>
          </span>
          <span>
            <span className="text-gray-400">合计浮盈</span>
            <span className={`ml-2 font-semibold ${totalPnl >= 0 ? "text-bull-text" : "text-bear-text"}`}>
              {totalPnl >= 0 ? "+" : ""}
              {fmt(totalPnl)}
            </span>
          </span>
          <span>
            <span className="text-gray-400">合计保证金</span>
            <span className="ml-2 font-medium">{fmt(totalMargin)}</span>
          </span>
        </div>
        <button
          onClick={() => load(portfolioId, true)}
          disabled={refreshing}
          className="text-xs text-accent hover:underline disabled:opacity-50"
        >
          {refreshing ? "刷新中..." : "刷新行情"}
        </button>
      </div>

      {positions.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-10 text-center text-gray-400">
          <p>当前无持仓</p>
          <Link href="/simulation/trades" className="text-accent text-sm mt-2 inline-block hover:underline">
            去下单
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">标的</th>
                <th className="px-4 py-3 text-left">方向</th>
                <th className="px-4 py-3 text-right">数量</th>
                <th className="px-4 py-3 text-right">开仓均价</th>
                <th className="px-4 py-3 text-right">最新价</th>
                <th className="px-4 py-3 text-right">杠杆</th>
                <th className="px-4 py-3 text-right">保证金</th>
                <th className="px-4 py-3 text-right">未实现盈亏</th>
                <th className="px-4 py-3 text-right">止损</th>
                <th className="px-4 py-3 text-right">止盈</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {positions.map((pos) => (
                <tr key={pos.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-primary">{pos.ticker}</td>
                  <td className="px-4 py-3">
                    <DirectionBadge direction={pos.direction} />
                  </td>
                  <td className="px-4 py-3 text-right">{pos.quantity}</td>
                  <td className="px-4 py-3 text-right">{fmt(pos.avg_entry_price)}</td>
                  <td className="px-4 py-3 text-right">
                    {pos.current_price !== null ? fmt(pos.current_price) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right">{pos.leverage_ratio}x</td>
                  <td className="px-4 py-3 text-right">{fmt(pos.margin_used)}</td>
                  <td className="px-4 py-3 text-right">
                    <PnlCell value={pos.unrealized_pnl} pct={pos.unrealized_pnl_pct} />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400">
                    {pos.stop_loss !== null ? fmt(pos.stop_loss) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400">
                    {pos.take_profit !== null ? fmt(pos.take_profit) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
