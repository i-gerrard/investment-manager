"use client";

import { api } from "@/lib/api";
import type { SimulatedPortfolio } from "@/types";
import Link from "next/link";
import { useEffect, useState } from "react";

const SUB_NAV = [
  { href: "/simulation", label: "概览" },
  { href: "/simulation/positions", label: "持仓" },
  { href: "/simulation/trades", label: "交易" },
  { href: "/simulation/comparison", label: "对比实盘" },
  { href: "/simulation/review", label: "复盘" },
];

function fmt(n: number, decimals = 2) {
  return n.toFixed(decimals);
}

function pct(n: number) {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${fmt(n)}%`;
}

function PnlBadge({ value }: { value: number }) {
  const pos = value >= 0;
  return (
    <span className={`font-semibold ${pos ? "text-bull-text" : "text-bear-text"}`}>
      {pos ? "+" : ""}
      {fmt(value)}
    </span>
  );
}

function StatCard({ label, value, sub, warn }: { label: string; value: string; sub?: string; warn?: boolean }) {
  return (
    <div className={`bg-white rounded-lg shadow p-5 ${warn ? "ring-2 ring-accent" : ""}`}>
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${warn ? "text-accent" : "text-primary"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function CreateForm({ onCreate }: { onCreate: (p: SimulatedPortfolio) => void }) {
  const [name, setName] = useState("主模拟账户");
  const [capital, setCapital] = useState("100000");
  const [currency, setCurrency] = useState("USD");
  const [maxLev, setMaxLev] = useState("10");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const p = await api.post<SimulatedPortfolio>("/simulation/portfolios", {
        name,
        initial_capital: parseFloat(capital),
        currency,
        max_leverage: parseFloat(maxLev),
        maintenance_margin_rate: 0.5,
      });
      onCreate(p);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 bg-white rounded-lg shadow p-8">
      <h2 className="text-xl font-bold text-primary mb-6">创建模拟账户</h2>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">账户名称</label>
          <input
            className="w-full border rounded-md px-3 py-2 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">初始资金</label>
            <input
              type="number"
              className="w-full border rounded-md px-3 py-2 text-sm"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              min="1000"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">货币</label>
            <select
              className="w-full border rounded-md px-3 py-2 text-sm"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option>USD</option>
              <option>CNY</option>
              <option>HKD</option>
              <option>EUR</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">最大杠杆倍数</label>
          <input
            type="number"
            className="w-full border rounded-md px-3 py-2 text-sm"
            value={maxLev}
            onChange={(e) => setMaxLev(e.target.value)}
            min="1"
            max="100"
            required
          />
          <p className="text-xs text-gray-400 mt-1">CFD 保证金率 = 1 / 杠杆，维持保证金率 50%</p>
        </div>
        {error && <p className="text-sm text-bear-text">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-white py-2 rounded-md text-sm hover:bg-primary-light disabled:opacity-50"
        >
          {loading ? "创建中..." : "创建账户"}
        </button>
      </form>
    </div>
  );
}

export default function SimulationPage() {
  const [portfolio, setPortfolio] = useState<SimulatedPortfolio | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<SimulatedPortfolio[]>("/simulation/portfolios")
      .then((list) => setPortfolio(list[0] ?? null))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-gray-400 text-sm">加载中...</p>;
  }

  if (!portfolio) {
    return <CreateForm onCreate={setPortfolio} />;
  }

  const p = portfolio;
  const marginLevelPct = p.margin_level !== null ? p.margin_level * 100 : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">模拟盘</h1>
        <span className="text-sm text-gray-500">{p.name} · {p.currency}</span>
      </div>

      {/* Sub nav */}
      <div className="flex gap-1 mb-6 border-b">
        {SUB_NAV.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            className="px-4 py-2 text-sm font-medium text-primary border-b-2 border-primary -mb-px"
          >
            {n.label}
          </Link>
        ))}
      </div>

      {/* Margin call banner */}
      {p.margin_call && (
        <div className="mb-5 bg-accent/10 border border-accent text-accent rounded-lg px-4 py-3 text-sm font-medium">
          ⚠️ 爆仓预警：保证金水平过低，请立即平仓或补充资金
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="账户权益"
          value={`${p.currency} ${fmt(p.equity)}`}
          sub={`初始 ${fmt(p.initial_capital)}`}
        />
        <StatCard
          label="总收益率"
          value={pct(p.total_return_pct)}
          sub={`浮盈 ${p.unrealized_pnl >= 0 ? "+" : ""}${fmt(p.unrealized_pnl)}`}
        />
        <StatCard
          label="可用现金"
          value={`${p.currency} ${fmt(p.cash_balance)}`}
          sub={`占用保证金 ${fmt(p.total_margin_used)}`}
        />
        <StatCard
          label="保证金水平"
          value={marginLevelPct !== null ? `${fmt(marginLevelPct)}%` : "无持仓"}
          sub={`维持要求 ${fmt(p.maintenance_margin_rate * 100)}%`}
          warn={p.margin_call}
        />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/simulation/trades", label: "下单交易", desc: "买多 / 卖空 / 平仓" },
          { href: "/simulation/positions", label: "查看持仓", desc: "实时浮盈浮亏" },
          { href: "/simulation/comparison", label: "与实盘对比", desc: "模拟 alpha" },
          { href: "/simulation/review", label: "操作复盘", desc: "记录交易逻辑" },
        ].map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="bg-white rounded-lg shadow p-5 hover:shadow-md transition-shadow"
          >
            <p className="font-semibold text-primary text-sm">{card.label}</p>
            <p className="text-xs text-gray-400 mt-1">{card.desc}</p>
          </Link>
        ))}
      </div>

      {/* Return summary */}
      <div className="mt-6 bg-white rounded-lg shadow p-6">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">账户摘要</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-y-3 text-sm">
          <div>
            <span className="text-gray-400">初始资金</span>
            <span className="ml-3 font-medium">{fmt(p.initial_capital)}</span>
          </div>
          <div>
            <span className="text-gray-400">当前权益</span>
            <span className="ml-3 font-medium">{fmt(p.equity)}</span>
          </div>
          <div>
            <span className="text-gray-400">未实现盈亏</span>
            <span className="ml-3">
              <PnlBadge value={p.unrealized_pnl} />
            </span>
          </div>
          <div>
            <span className="text-gray-400">占用保证金</span>
            <span className="ml-3 font-medium">{fmt(p.total_margin_used)}</span>
          </div>
          <div>
            <span className="text-gray-400">最大杠杆</span>
            <span className="ml-3 font-medium">{p.max_leverage}x</span>
          </div>
          <div>
            <span className="text-gray-400">总收益率</span>
            <span className={`ml-3 font-semibold ${p.total_return_pct >= 0 ? "text-bull-text" : "text-bear-text"}`}>
              {pct(p.total_return_pct)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
