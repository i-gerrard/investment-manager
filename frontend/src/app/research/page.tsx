"use client";

import { api } from "@/lib/api";
import type { ResearchReport } from "@/types";
import { useEffect, useState } from "react";

export default function ResearchPage() {
  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ items: ResearchReport[] }>("/research/reports?limit=50").then(d => setReports(d.items)).finally(() => setLoading(false));
  }, []);

  const phaseLabels: Record<string, string> = {
    "0": "Exec Summary", "1": "Business", "2": "Industry", "3": "Breakdown",
    "4": "Financial", "5": "Governance", "6": "Sentiment", "7": "Valuation",
    "8": "Synthesis", "9": "Leverage", "synthesis": "Synthesis"
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Research Reports</h1>
      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
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
