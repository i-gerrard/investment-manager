"use client";

import { api } from "@/lib/api";
import type { Stock } from "@/types";
import { useEffect, useState } from "react";

export default function StocksPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("");
  const [loading, setLoading] = useState(true);

  async function fetchStocks() {
    setLoading(true);
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (market) params.set("market", market);
    const data = await api.get<{ items: Stock[]; total: number }>(`/stocks?${params}`);
    setStocks(data.items);
    setTotal(data.total);
    setLoading(false);
  }

  useEffect(() => {
    fetchStocks();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Stocks</h1>
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Search ticker or name..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && fetchStocks()}
          className="px-3 py-2 border rounded-md text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <select value={market} onChange={(e) => { setMarket(e.target.value); }} className="px-3 py-2 border rounded-md text-sm">
          <option value="">All Markets</option>
          <option value="A-share">A-share</option>
          <option value="US">US</option>
          <option value="HK">HK</option>
        </select>
        <button onClick={fetchStocks} className="bg-primary text-white px-4 py-2 rounded-md text-sm">Search</button>
      </div>
      <p className="text-xs text-gray-400 mb-4">{total} stocks</p>

      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Ticker</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Market</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Sector</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {stocks.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 cursor-pointer">
                  <td className="px-6 py-4 text-sm font-medium">{s.ticker}</td>
                  <td className="px-6 py-4 text-sm">{s.name}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      s.market === "US" ? "bg-blue-100 text-blue-700" :
                      s.market === "A-share" ? "bg-red-100 text-red-700" :
                      "bg-green-100 text-green-700"
                    }`}>{s.market}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{s.sector ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
