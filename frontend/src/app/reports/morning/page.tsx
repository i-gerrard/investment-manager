"use client";

import { api } from "@/lib/api";
import { useGet } from "@/lib/useApi";
import type { MorningReport } from "@/types";
import { useState } from "react";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorAlert from "@/components/ui/ErrorAlert";
import EmptyState from "@/components/ui/EmptyState";

interface MorningListItem { id: string; report_date: string; headline?: string }

export default function MorningReportsPage() {
  const { data: reports, loading, error, refetch } = useGet<MorningListItem[]>("/reports/morning");
  const [selected, setSelected] = useState<MorningReport | null>(null);

  async function viewReport(id: string) {
    try {
      const data = await api.get<MorningReport>(`/reports/morning/${id}`);
      setSelected(data);
    } catch {}
  }

  if (selected) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Morning Reports</h1>
        <button onClick={() => setSelected(null)} className="text-primary text-sm mb-4 hover:underline">&larr; Back to list</button>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-2">{selected.headline || selected.report_date}</h2>
          <p className="text-xs text-gray-400 mb-4">{selected.report_date}</p>
          <iframe srcDoc={selected.html_content} className="w-full min-h-[600px] border rounded" sandbox="allow-scripts" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Morning Reports</h1>
      {loading ? <LoadingSpinner /> :
       error ? <ErrorAlert message={error} onRetry={refetch} /> :
       !reports?.length ? <EmptyState message="No morning reports yet" /> : (
        <div className="space-y-2">
          {reports.map((r) => (
            <button
              key={r.id}
              onClick={() => viewReport(r.id)}
              className="block w-full text-left bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
            >
              <span className="font-medium">{r.report_date}</span>
              {r.headline && <span className="text-sm text-gray-500 ml-3">{r.headline}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
