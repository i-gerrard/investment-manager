"use client";

import { useGet } from "@/lib/useApi";
import type { Portfolio } from "@/types";
import Link from "next/link";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

export default function PortfolioListPage() {
  const { data: portfolios, loading, error, refetch } = useGet<Portfolio[]>("/portfolios");

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Portfolios</h1>
        <Link href="/portfolio/new" className="bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary-light">
          + New Portfolio
        </Link>
      </div>
      {loading ? <LoadingSpinner /> :
       error ? <ErrorAlert message={error} onRetry={refetch} /> :
       !portfolios?.length ? <EmptyState message="No portfolios yet. Create one to get started." /> : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {portfolios.map((p) => (
            <Link key={p.id} href={`/portfolio/${p.id}`} className="block bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow">
              <h3 className="text-lg font-semibold text-primary">{p.name}</h3>
              {p.description && <p className="text-sm text-gray-500 mt-1">{p.description}</p>}
              <p className="text-xs text-gray-400 mt-3">{p.holding_count ?? 0} holdings</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
