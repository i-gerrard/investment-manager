"use client";

import { api } from "@/lib/api";
import type { SimulatedPortfolio, SimulatedTrade, TradeAction, TriggerSource } from "@/types";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const SUB_NAV = [
  { href: "/simulation", label: "概览" },
  { href: "/simulation/positions", label: "持仓" },
  { href: "/simulation/trades", label: "交易" },
  { href: "/simulation/comparison", label: "对比实盘" },
  { href: "/simulation/review", label: "复盘" },
];

const ACTION_LABELS: Record<TradeAction, string> = {
  BUY_LONG: "买多（开多）",
  SELL_LONG: "卖出（平多）",
  SELL_SHORT: "卖空（开空）",
  BUY_SHORT: "买入平空",
};

const ACTION_COLORS: Record<TradeAction, string> = {
  BUY_LONG: "text-bull-text",
  SELL_LONG: "text-gray-600",
  SELL_SHORT: "text-bear-text",
  BUY_SHORT: "text-gray-600",
};

function fmt(n: number, d = 2) {
  return n.toFixed(d);
}

function ActionBadge({ action }: { action: TradeAction }) {
  return <span className={`font-semibold text-xs ${ACTION_COLORS[action]}`}>{ACTION_LABELS[action]}</span>;
}

export default function TradesPage() {
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [trades, setTrades] = useState<SimulatedTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [fetchingPrice, setFetchingPrice] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Form state
  const [ticker, setTicker] = useState("");
  const [action, setAction] = useState<TradeAction>("BUY_LONG");
  const [quantity, setQuantity] = useState("1");
  const [leverage, setLeverage] = useState("1");
  const [useMarket, setUseMarket] = useState(true);
  const [customPrice, setCustomPrice] = useState("");
  const [fetchedPrice, setFetchedPrice] = useState<number | null>(null);
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [rationale, setRationale] = useState("");
  const [triggeredBy, setTriggeredBy] = useState<TriggerSource>("MANUAL");

  const successTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function loadTrades(pid: string) {
    const data = await api.get<SimulatedTrade[]>(`/simulation/portfolios/${pid}/trades`);
    setTrades(data);
  }

  useEffect(() => {
    api.get<SimulatedPortfolio[]>("/simulation/portfolios").then((list) => {
      if (list[0]) {
        setPortfolioId(list[0].id);
        loadTrades(list[0].id).finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    });
  }, []);

  async function fetchPrice() {
    if (!ticker.trim()) return;
    setFetchingPrice(true);
    setFetchedPrice(null);
    try {
      const res = await api.get<{ ticker: string; price: number }>(`/simulation/price/${ticker.trim().toUpperCase()}`);
      setFetchedPrice(res.price);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "行情获取失败");
    } finally {
      setFetchingPrice(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!portfolioId) return;
    if (rationale.trim().length < 10) {
      setError("交易理由至少10个字符");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await api.post<SimulatedTrade>(`/simulation/portfolios/${portfolioId}/trades`, {
        ticker: ticker.trim().toUpperCase(),
        action,
        quantity: parseFloat(quantity),
        leverage_ratio: parseFloat(leverage),
        rationale: rationale.trim(),
        triggered_by: triggeredBy,
        use_market_price: useMarket,
        custom_price: useMarket ? undefined : parseFloat(customPrice),
        stop_loss: stopLoss ? parseFloat(stopLoss) : undefined,
        take_profit: takeProfit ? parseFloat(takeProfit) : undefined,
      });
      // Reset form
      setRationale("");
      setStopLoss("");
      setTakeProfit("");
      setFetchedPrice(null);
      setSuccess("交易执行成功");
      if (successTimer.current) clearTimeout(successTimer.current);
      successTimer.current = setTimeout(() => setSuccess(""), 4000);
      await loadTrades(portfolioId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "交易失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p className="text-gray-400 text-sm">加载中...</p>;

  if (!portfolioId) {
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
              n.href === "/simulation/trades"
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-primary"
            }`}
          >
            {n.label}
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Trade form */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-primary mb-5">下单</h2>
            <form onSubmit={submit} className="space-y-4">
              {/* Ticker + price */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">股票代码</label>
                <div className="flex gap-2">
                  <input
                    className="flex-1 border rounded-md px-3 py-2 text-sm uppercase"
                    placeholder="AAPL / 600519"
                    value={ticker}
                    onChange={(e) => { setTicker(e.target.value); setFetchedPrice(null); }}
                    required
                  />
                  <button
                    type="button"
                    onClick={fetchPrice}
                    disabled={fetchingPrice || !ticker.trim()}
                    className="px-3 py-2 text-xs bg-primary text-white rounded-md hover:bg-primary-light disabled:opacity-50"
                  >
                    {fetchingPrice ? "..." : "取价"}
                  </button>
                </div>
                {fetchedPrice !== null && (
                  <p className="text-xs text-bull-text mt-1">实时价格：{fmt(fetchedPrice)}</p>
                )}
              </div>

              {/* Action */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">操作方向</label>
                <select
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  value={action}
                  onChange={(e) => setAction(e.target.value as TradeAction)}
                >
                  {(Object.keys(ACTION_LABELS) as TradeAction[]).map((a) => (
                    <option key={a} value={a}>{ACTION_LABELS[a]}</option>
                  ))}
                </select>
              </div>

              {/* Qty + Leverage */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">数量（股）</label>
                  <input
                    type="number"
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    min="0.01"
                    step="any"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">杠杆倍数</label>
                  <input
                    type="number"
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    value={leverage}
                    onChange={(e) => setLeverage(e.target.value)}
                    min="1"
                    step="0.1"
                    required
                  />
                </div>
              </div>

              {/* Price mode */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">价格方式</label>
                <div className="flex gap-4 text-sm">
                  <label className="flex items-center gap-1.5">
                    <input type="radio" checked={useMarket} onChange={() => setUseMarket(true)} />
                    实时行情
                  </label>
                  <label className="flex items-center gap-1.5">
                    <input type="radio" checked={!useMarket} onChange={() => setUseMarket(false)} />
                    自定义价格
                  </label>
                </div>
                {!useMarket && (
                  <input
                    type="number"
                    className="mt-2 w-full border rounded-md px-3 py-2 text-sm"
                    placeholder="输入执行价格"
                    value={customPrice}
                    onChange={(e) => setCustomPrice(e.target.value)}
                    min="0.01"
                    step="any"
                    required
                  />
                )}
              </div>

              {/* Stop / TP */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">止损价（选填）</label>
                  <input
                    type="number"
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    placeholder="—"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value)}
                    step="any"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">止盈价（选填）</label>
                  <input
                    type="number"
                    className="w-full border rounded-md px-3 py-2 text-sm"
                    placeholder="—"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value)}
                    step="any"
                  />
                </div>
              </div>

              {/* Trigger source */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">信号来源</label>
                <select
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  value={triggeredBy}
                  onChange={(e) => setTriggeredBy(e.target.value as TriggerSource)}
                >
                  <option value="MANUAL">手动判断</option>
                  <option value="AI_SIGNAL">AI 信号</option>
                  <option value="RESEARCH">研报依据</option>
                </select>
              </div>

              {/* Rationale */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  交易理由 <span className="text-gray-400">（至少10字）</span>
                </label>
                <textarea
                  className="w-full border rounded-md px-3 py-2 text-sm resize-none"
                  rows={4}
                  placeholder="说明本次操作的核心逻辑、催化剂、风险点..."
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  required
                />
              </div>

              {error && <p className="text-xs text-bear-text">{error}</p>}
              {success && <p className="text-xs text-bull-text">{success}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-primary text-white py-2.5 rounded-md text-sm font-medium hover:bg-primary-light disabled:opacity-50"
              >
                {submitting ? "执行中..." : "确认下单"}
              </button>
            </form>
          </div>
        </div>

        {/* Trade history */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold text-primary">交易记录</h2>
            </div>
            {trades.length === 0 ? (
              <p className="text-gray-400 text-sm p-6">暂无交易记录</p>
            ) : (
              <div className="divide-y divide-gray-100 max-h-[720px] overflow-y-auto">
                {trades.map((t) => (
                  <div key={t.id} className="px-6 py-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-primary">{t.ticker}</span>
                        <ActionBadge action={t.action} />
                        <span className="text-xs text-gray-400">{t.leverage_ratio}x</span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {new Date(t.executed_at).toLocaleString("zh-CN")}
                      </span>
                    </div>
                    <div className="mt-1.5 flex gap-4 text-xs text-gray-500">
                      <span>成交价 <strong className="text-gray-700">{fmt(t.price)}</strong></span>
                      <span>数量 <strong className="text-gray-700">{t.quantity}</strong></span>
                      <span>保证金 <strong className="text-gray-700">{fmt(t.margin_used)}</strong></span>
                      {t.realized_pnl !== null && (
                        <span>
                          实现盈亏{" "}
                          <strong className={t.realized_pnl >= 0 ? "text-bull-text" : "text-bear-text"}>
                            {t.realized_pnl >= 0 ? "+" : ""}
                            {fmt(t.realized_pnl)}
                          </strong>
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-xs text-gray-600 bg-gray-50 rounded px-3 py-2 leading-relaxed">
                      {t.rationale}
                    </p>
                    <div className="mt-1.5 flex gap-3 text-xs text-gray-400">
                      {t.stop_loss && <span>止损 {fmt(t.stop_loss)}</span>}
                      {t.take_profit && <span>止盈 {fmt(t.take_profit)}</span>}
                      <span className="ml-auto capitalize">{t.triggered_by.toLowerCase().replace("_", " ")}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
