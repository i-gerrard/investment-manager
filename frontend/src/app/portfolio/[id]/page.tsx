"use client";

import { useGet } from "@/lib/useApi";
import type { Holding, Portfolio } from "@/types";
import { useParams } from "next/navigation";
import { useMemo } from "react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";

interface PortfolioDetail extends Portfolio {
  holdings: Holding[];
}

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: portfolio, loading, error, refetch } = useGet<PortfolioDetail>(`/portfolios/${id}`, [id]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} onRetry={refetch} />;
  if (!portfolio) return <ErrorAlert message="Portfolio not found" />;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">{portfolio.name}</h1>
        {portfolio.description && <p className="text-gray-500 mt-1">{portfolio.description}</p>}
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Ticker</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Cost Basis</th>
              <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Position %</th>
              <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase">Entry Date</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {portfolio.holdings.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-400">No holdings yet</td>
              </tr>
            ) : (
              portfolio.holdings.map((h) => (
                <tr key={h.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium">{h.ticker}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{h.stock?.name ?? "-"}</td>
                  <td className="px-6 py-4 text-sm text-right">{Number(h.cost_basis).toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-right">{Number(h.position_percent).toFixed(1)}%</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-400">{h.entry_date ?? "-"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
