"use client";

import { useGet } from "@/lib/useApi";
import type { Stock } from "@/types";
import { useCallback, useEffect, useState } from "react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";

export default function StocksPage() {
  const [q, setQ] = useState("");
  const [market, setMarket] = useState("");
  const [query, setQuery] = useState("");

  const buildPath = useCallback(() => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (market) params.set("market", market);
    const qs = params.toString();
    return `/stocks${qs ? "?" + qs : ""}`;
  }, [query, market]);

  const { data, loading, error, refetch } = useGet<{ items: Stock[]; total: number }>(buildPath(), [buildPath]);
  const stocks = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Stocks</h1>
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Search ticker or name..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && setQuery(q)}
          className="px-3 py-2 border rounded-md text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <select value={market} onChange={(e) => setMarket(e.target.value)} className="px-3 py-2 border rounded-md text-sm">
          <option value="">All Markets</option>
          <option value="A-share">A-share</option>
          <option value="US">US</option>
          <option value="HK">HK</option>
        </select>
        <button onClick={() => setQuery(q)} className="bg-primary text-white px-4 py-2 rounded-md text-sm">Search</button>
      </div>
      <p className="text-xs text-gray-400 mb-4">{total} stocks</p>

      {loading ? <LoadingSpinner /> :
       error ? <ErrorAlert message={error} onRetry={refetch} /> : (
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
