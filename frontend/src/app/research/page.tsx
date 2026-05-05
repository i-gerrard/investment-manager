"use client";

import { useGet } from "@/lib/useApi";
import type { ResearchReport } from "@/types";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

export default function ResearchPage() {
  const { data, loading, error, refetch } = useGet<{ items: ResearchReport[] }>("/research/reports?limit=50");
  const reports = data?.items ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Research Reports</h1>
      {loading ? <LoadingSpinner /> :
       error ? <ErrorAlert message={error} onRetry={refetch} /> :
       reports.length === 0 ? <EmptyState message="No research reports yet" /> : (
        <div className="space-y-3">
          {reports.map((r) => (
            <div key={r.id} className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                  P{r.phase}
                </span>
                <span className="text-sm font-medium text-gray-500">{r.stock?.ticker ?? "—"}</span>
                {r.signal_rating && <span className="text-sm">{r.signal_rating}</span>}
              </div>
              <h3 className="font-semibold">{r.title}</h3>
              {r.core_thesis && <p className="text-sm text-gray-500 mt-1 line-clamp-2">{r.core_thesis}</p>}
              <p className="text-xs text-gray-400 mt-2">{new Date(r.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
