'use client';

import { useState, useEffect } from 'react';
import { getMetrics, generateReport } from '@/lib/api';

export default function BenchmarkPage() {
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getMetrics().then(setMetrics).catch(() => {});
  }, []);

  async function handleReport() {
    setLoading(true);
    try {
      const res = await generateReport();
      setReport(res.report);
    } catch {
      setReport('Failed to generate report.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-in">
      <h1 className="text-lg font-semibold text-neutral-900 tracking-tight">Metrics</h1>
      <p className="text-[14px] text-neutral-400 mt-1 mb-8">Inference latency, throughput, and token usage.</p>

      {/* Grid */}
      {metrics ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-neutral-200 rounded-lg overflow-hidden mb-8">
          <Metric label="Requests" value={metrics.request_count} />
          <Metric label="P50" value={metrics.p50_latency_sec != null ? `${metrics.p50_latency_sec}s` : '–'} />
          <Metric label="P95" value={metrics.p95_latency_sec != null ? `${metrics.p95_latency_sec}s` : '–'} />
          <Metric label="P99" value={metrics.p99_latency_sec != null ? `${metrics.p99_latency_sec}s` : '–'} />
          <Metric label="Avg input tok" value={metrics.avg_input_tokens ?? '–'} />
          <Metric label="Avg output tok" value={metrics.avg_output_tokens ?? '–'} />
          <Metric label="Total tokens" value={metrics.total_tokens ?? '–'} />
          <Metric label="Error rate" value={metrics.error_rate != null ? `${(metrics.error_rate * 100).toFixed(1)}%` : '–'} />
        </div>
      ) : (
        <div className="h-32 rounded-lg bg-neutral-50 mb-8" />
      )}

      <div className="flex gap-3 mb-8">
        <button
          onClick={() => getMetrics().then(setMetrics).catch(() => {})}
          className="rounded-lg border border-neutral-200 px-4 py-2 text-[13px] font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >
          Refresh
        </button>
        <button
          onClick={handleReport}
          disabled={loading}
          className="rounded-lg bg-neutral-900 px-4 py-2 text-[13px] font-medium text-white hover:bg-neutral-800 disabled:opacity-30 transition-colors"
        >
          {loading ? 'Generating…' : 'Generate report'}
        </button>
      </div>

      {report && (
        <div className="animate-in mb-8">
          <h3 className="text-[12px] text-neutral-400 mb-2">Report</h3>
          <pre className="text-[13px] text-neutral-600 leading-relaxed whitespace-pre-wrap">{report}</pre>
        </div>
      )}

      {metrics && (
        <details>
          <summary className="text-[12px] text-neutral-400 cursor-pointer hover:text-neutral-600 transition-colors">
            Raw JSON
          </summary>
          <div className="mt-2 rounded-lg bg-neutral-900 p-4 overflow-auto max-h-64">
            <pre className="text-[12px] text-neutral-400 font-mono leading-relaxed">{JSON.stringify(metrics, null, 2)}</pre>
          </div>
        </details>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white p-4">
      <div className="text-[11px] text-neutral-400 mb-1">{label}</div>
      <div className="text-xl font-semibold text-neutral-900 tabular-nums">{value}</div>
    </div>
  );
}
