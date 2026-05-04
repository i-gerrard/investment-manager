"use client";

import { api } from "@/lib/api";
import type { Portfolio } from "@/types";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function PortfolioListPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Portfolio[]>("/portfolios").then(setPortfolios).finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Portfolios</h1>
        <Link href="/portfolio/new" className="bg-primary text-white px-4 py-2 rounded-md text-sm hover:bg-primary-light">
          + New Portfolio
        </Link>
      </div>
      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : portfolios.length === 0 ? (
        <p className="text-gray-400">No portfolios yet. Create one to get started.</p>
      ) : (
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
