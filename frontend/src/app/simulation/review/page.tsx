"use client";

import { api } from "@/lib/api";
import type { SimulatedPortfolio, SimulatedTrade, TradeReview } from "@/types";
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

function StarRating({ rating }: { rating: number }) {
  return (
    <span>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < rating ? "text-yellow-400" : "text-gray-200"}>★</span>
      ))}
    </span>
  );
}

function PnlBadge({ value }: { value: number }) {
  const pos = value >= 0;
  return (
    <span className={`font-semibold text-sm ${pos ? "text-bull-text" : "text-bear-text"}`}>
      {pos ? "+" : ""}{fmt(value)}
    </span>
  );
}

export default function ReviewPage() {
  const [portfolioId, setPortfolioId] = useState<string | null>(null);
  const [reviews, setReviews] = useState<TradeReview[]>([]);
  const [trades, setTrades] = useState<SimulatedTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [selectedTradeId, setSelectedTradeId] = useState<string>("");
  const [ticker, setTicker] = useState("");
  const [entryRationale, setEntryRationale] = useState("");
  const [actualOutcome, setActualOutcome] = useState("");
  const [pnlRealized, setPnlRealized] = useState("0");
  const [lessonsLearned, setLessonsLearned] = useState("");
  const [rating, setRating] = useState(3);

  async function load(pid: string) {
    const [rv, tr] = await Promise.all([
      api.get<TradeReview[]>(`/simulation/portfolios/${pid}/reviews`),
      api.get<SimulatedTrade[]>(`/simulation/portfolios/${pid}/trades`),
    ]);
    setReviews(rv);
    setTrades(tr);
  }

  useEffect(() => {
    api.get<SimulatedPortfolio[]>("/simulation/portfolios").then((list) => {
      if (list[0]) {
        setPortfolioId(list[0].id);
        load(list[0].id).finally(() => setLoading(false));
      } else {
        setLoading(false);
      }
    });
  }, []);

  function prefillFromTrade(tradeId: string) {
    const t = trades.find((x) => x.id === tradeId);
    if (!t) return;
    setTicker(t.ticker);
    setEntryRationale(t.rationale);
    setPnlRealized(t.realized_pnl !== null ? String(t.realized_pnl) : "0");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!portfolioId) return;
    setError("");
    setSubmitting(true);
    try {
      await api.post<TradeReview>(`/simulation/portfolios/${portfolioId}/reviews`, {
        trade_id: selectedTradeId || undefined,
        ticker: ticker.trim().toUpperCase(),
        entry_rationale: entryRationale.trim(),
        actual_outcome: actualOutcome.trim(),
        pnl_realized: parseFloat(pnlRealized),
        lessons_learned: lessonsLearned.trim() || undefined,
        rating,
      });
      // Reset form
      setSelectedTradeId("");
      setTicker("");
      setEntryRationale("");
      setActualOutcome("");
      setPnlRealized("0");
      setLessonsLearned("");
      setRating(3);
      setShowForm(false);
      await load(portfolioId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "提交失败");
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

  const totalPnl = reviews.reduce((s, r) => s + r.pnl_realized, 0);
  const avgRating = reviews.length
    ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length
    : null;

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
              n.href === "/simulation/review"
                ? "border-primary text-primary"
                : "border-transparent text-gray-500 hover:text-primary"
            }`}
          >
            {n.label}
          </Link>
        ))}
      </div>

      {/* Stats bar */}
      {reviews.length > 0 && (
        <div className="flex gap-6 text-sm mb-5 bg-white rounded-lg shadow px-6 py-4">
          <span>
            <span className="text-gray-400">复盘数</span>
            <span className="ml-2 font-semibold">{reviews.length}</span>
          </span>
          <span>
            <span className="text-gray-400">累计实现盈亏</span>
            <span className="ml-2"><PnlBadge value={totalPnl} /></span>
          </span>
          {avgRating !== null && (
            <span>
              <span className="text-gray-400">平均评分</span>
              <span className="ml-2 font-semibold">{fmt(avgRating, 1)} / 5</span>
            </span>
          )}
        </div>
      )}

      <div className="flex justify-end mb-4">
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary-light"
        >
          {showForm ? "收起" : "+ 新增复盘"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-primary mb-5">新增复盘</h2>
          <form onSubmit={submit} className="space-y-4">
            {/* Link to trade */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">关联交易（选填）</label>
              <select
                className="w-full border rounded-md px-3 py-2 text-sm"
                value={selectedTradeId}
                onChange={(e) => { setSelectedTradeId(e.target.value); prefillFromTrade(e.target.value); }}
              >
                <option value="">— 不关联具体交易 —</option>
                {trades.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.ticker} {t.action} @{fmt(t.price)} — {new Date(t.executed_at).toLocaleDateString("zh-CN")}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">股票代码</label>
                <input
                  className="w-full border rounded-md px-3 py-2 text-sm uppercase"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">实现盈亏</label>
                <input
                  type="number"
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  value={pnlRealized}
                  onChange={(e) => setPnlRealized(e.target.value)}
                  step="any"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">原始买入理由</label>
              <textarea
                className="w-full border rounded-md px-3 py-2 text-sm resize-none"
                rows={3}
                placeholder="当时的入场逻辑是什么？"
                value={entryRationale}
                onChange={(e) => setEntryRationale(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">实际结果</label>
              <textarea
                className="w-full border rounded-md px-3 py-2 text-sm resize-none"
                rows={3}
                placeholder="实际发生了什么？价格走势如何？"
                value={actualOutcome}
                onChange={(e) => setActualOutcome(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">经验教训（选填）</label>
              <textarea
                className="w-full border rounded-md px-3 py-2 text-sm resize-none"
                rows={2}
                placeholder="这次操作最大的收获或教训是什么？"
                value={lessonsLearned}
                onChange={(e) => setLessonsLearned(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-2">操作自评（1-5）</label>
              <div className="flex gap-3">
                {[1, 2, 3, 4, 5].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setRating(v)}
                    className={`text-2xl transition-transform hover:scale-110 ${v <= rating ? "text-yellow-400" : "text-gray-200"}`}
                  >
                    ★
                  </button>
                ))}
                <span className="ml-2 text-sm text-gray-400 self-center">{rating} / 5</span>
              </div>
            </div>

            {error && <p className="text-xs text-bear-text">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-primary text-white py-2.5 rounded-md text-sm font-medium hover:bg-primary-light disabled:opacity-50"
            >
              {submitting ? "提交中..." : "保存复盘"}
            </button>
          </form>
        </div>
      )}

      {/* Timeline */}
      {reviews.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-10 text-center text-gray-400">
          <p>暂无复盘记录</p>
          <p className="text-xs mt-1">点击「新增复盘」开始记录你的交易心得</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((r) => (
            <div key={r.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-primary text-lg">{r.ticker}</span>
                  <PnlBadge value={r.pnl_realized} />
                  <StarRating rating={r.rating} />
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(r.reviewed_at).toLocaleString("zh-CN")}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-gray-400 uppercase mb-1">原始入场理由</p>
                  <p className="text-gray-700 bg-gray-50 rounded px-3 py-2 leading-relaxed">{r.entry_rationale}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase mb-1">实际结果</p>
                  <p className="text-gray-700 bg-gray-50 rounded px-3 py-2 leading-relaxed">{r.actual_outcome}</p>
                </div>
              </div>

              {r.lessons_learned && (
                <div className="mt-3">
                  <p className="text-xs text-gray-400 uppercase mb-1">经验教训</p>
                  <p className="text-sm text-primary font-medium bg-primary/5 rounded px-3 py-2 leading-relaxed">
                    {r.lessons_learned}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
