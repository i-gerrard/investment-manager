"use client";

import { api } from "@/lib/api";
import type { Portfolio, PortfolioComparison, SimulatedPortfolio } from "@/types";
import Link from "next/link";
import { useEffect, useState } from "react";

const SUB_NAV = [
  { href: "/simulation", label: "概览" },
  { href: "/simulation/positions", label: "持仓" },
  { href: "/simulation/trades", label: "交易" },
  { href: "/simulation/comparison", label: "对比实盘" },
  { href: "/simulation/review", label: "复盘" },
];

function fmt(n: number, d = 2) { return n.toFixed(d); }

function ReturnPill({ pct }: { pct: number }) {
  const pos = pct >= 0;
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${pos ? "bg-bull-bg text-bull-text" : "bg-bear-bg text-bear-text"}`}>
      {pos ? "+" : ""}{fmt(pct)}%
    </span>
  );
}

function AlphaBanner({ alpha }: { alpha: number }) {
  const pos = alpha >= 0;
  return (
    <div className={`rounded-lg p-4 text-center ${pos ? "bg-bull-bg" : "bg-bear-bg"}`}>
      <p className="text-xs text-gray-500 mb-1">模拟盘 Alpha（相对实盘超额收益）</p>
      <p className={`text-3xl font-bold ${pos ? "text-bull-text" : "text-bear-text"}`}>
        {pos ? "+" : ""}{fmt(alpha)}%
      </p>
    </div>
  );
}

export default function ComparisonPage() {
  const [simId, setSimId] = useState<string | null>(null);
  const [realPortfolios, setRealPortfolios] = useState<Portfolio[]>([]);
  const [selectedRealId, setSelectedRealId] = useState<string>("");
  const [comparison, setComparison] = useState<PortfolioComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<SimulatedPortfolio[]>("/simulation/portfolios"),
      api.get<Portfolio[]>("/portfolios"),
    ]).then(([sims, reals]) => {
      if (sims[0]) setSimId(sims[0].id);
      setRealPortfolios(reals);
      if (reals[0]) setSelectedRealId(reals[0].id);
    }).finally(() => setLoading(false));
  }, []);

  async function runComparison() {
    if (!simId) return;
    setComparing(true);
    const qs = selectedRealId ? `?real_portfolio_id=${selectedRealId}` : "";
    try {
      const data = await api.get<PortfolioComparison>(`/simulation/portfolios/${simId}/comparison${qs}`);
      setComparison(data);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setComparing(false);
    }
  }

  if (loading) return <p className="text-gray-400 text-sm">加载中...</p>;

  if (!simId) {
    return (
      <div className="text-center mt-20">
        <p className="text-gray-400 mb-4">未找到模拟账户</p>
        <Link href="/simulation" className="text-accent text-sm hover:underline">前往创建</Link>
      </div>
    );
  }

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
              n.href === "/simulation/comparison"
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-primary"
            }`}
          >
            {n.label}
          </Link>
        ))}
      </div>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-5 mb-5 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">选择对比实盘</label>
          <select
            className="border rounded-md px-3 py-2 text-sm min-w-48"
            value={selectedRealId}
            onChange={(e) => setSelectedRealId(e.target.value)}
          >
            <option value="">— 仅查看模拟盘 —</option>
            {realPortfolios.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <button
          onClick={runComparison}
          disabled={comparing}
          className="px-5 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-light disabled:opacity-50"
        >
          {comparing ? "计算中..." : "开始对比"}
        </button>
      </div>

      {comparison && (
        <div className="space-y-5">
          {/* Alpha banner */}
          {comparison.alpha_pct !== null && (
            <AlphaBanner alpha={comparison.alpha_pct} />
          )}

          {/* Side by side */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Sim side */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold text-primary mb-4">模拟盘：{comparison.sim_name}</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">初始资金</span>
                  <span>{fmt(comparison.sim_initial_capital)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">当前权益</span>
                  <span className="font-semibold">{fmt(comparison.sim_equity)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">未实现盈亏</span>
                  <span className={comparison.sim_unrealized_pnl >= 0 ? "text-bull-text" : "text-bear-text"}>
                    {comparison.sim_unrealized_pnl >= 0 ? "+" : ""}{fmt(comparison.sim_unrealized_pnl)}
                  </span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t">
                  <span className="text-gray-400">总收益率</span>
                  <ReturnPill pct={comparison.sim_return_pct} />
                </div>
              </div>

              {comparison.sim_positions.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs text-gray-400 uppercase mb-2">持仓</p>
                  <table className="w-full text-xs">
                    <thead className="text-gray-400">
                      <tr>
                        <th className="text-left pb-1">标的</th>
                        <th className="text-left pb-1">方向</th>
                        <th className="text-right pb-1">杠杆</th>
                        <th className="text-right pb-1">浮盈</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {comparison.sim_positions.map((pos) => (
                        <tr key={pos.id}>
                          <td className="py-1 font-medium">{pos.ticker}</td>
                          <td className="py-1">
                            <span className={pos.direction === "LONG" ? "text-bull-text" : "text-bear-text"}>
                              {pos.direction === "LONG" ? "多" : "空"}
                            </span>
                          </td>
                          <td className="py-1 text-right">{pos.leverage_ratio}x</td>
                          <td className={`py-1 text-right ${(pos.unrealized_pnl ?? 0) >= 0 ? "text-bull-text" : "text-bear-text"}`}>
                            {pos.unrealized_pnl !== null
                              ? `${pos.unrealized_pnl >= 0 ? "+" : ""}${fmt(pos.unrealized_pnl)}`
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Real side */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold text-primary mb-4">
                实盘：{comparison.real_portfolio_name ?? "未选择"}
              </h3>
              {comparison.real_portfolio_name ? (
                <>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between items-center pt-2 border-t">
                      <span className="text-gray-400">持仓收益率（加权）</span>
                      {comparison.real_return_pct !== null
                        ? <ReturnPill pct={comparison.real_return_pct} />
                        : <span className="text-gray-300">—</span>}
                    </div>
                  </div>

                  {comparison.real_holdings.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs text-gray-400 uppercase mb-2">持仓</p>
                      <table className="w-full text-xs">
                        <thead className="text-gray-400">
                          <tr>
                            <th className="text-left pb-1">标的</th>
                            <th className="text-right pb-1">仓位%</th>
                            <th className="text-right pb-1">成本</th>
                            <th className="text-right pb-1">现价</th>
                            <th className="text-right pb-1">涨跌%</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {comparison.real_holdings.map((h) => (
                            <tr key={h.ticker}>
                              <td className="py-1 font-medium">{h.ticker}</td>
                              <td className="py-1 text-right">{fmt(h.position_percent)}%</td>
                              <td className="py-1 text-right">{fmt(h.cost_basis)}</td>
                              <td className="py-1 text-right">
                                {h.current_price !== null ? fmt(h.current_price) : "—"}
                              </td>
                              <td className={`py-1 text-right ${(h.unrealized_pnl_pct ?? 0) >= 0 ? "text-bull-text" : "text-bear-text"}`}>
                                {h.unrealized_pnl_pct !== null
                                  ? `${h.unrealized_pnl_pct >= 0 ? "+" : ""}${fmt(h.unrealized_pnl_pct)}%`
                                  : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-gray-400">请在上方选择实盘组合进行对比</p>
              )}
            </div>
          </div>

          <p className="text-xs text-gray-400 text-right">
            数据时间：{new Date(comparison.comparison_date).toLocaleString("zh-CN")}
          </p>
        </div>
      )}
    </div>
  );
}
