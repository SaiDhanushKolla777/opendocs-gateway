'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { listDocuments, getMetrics } from '@/lib/api';

export default function Home() {
  const [docCount, setDocCount] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    listDocuments().then((d) => setDocCount(d.length)).catch(() => {});
    getMetrics().then(setMetrics).catch(() => {});
  }, []);

  return (
    <div className="animate-in">
      {/* Hero — centered like OpenWebUI */}
      <div className="flex flex-col items-center pt-16 pb-12">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-900 text-white text-lg font-semibold mb-5">
          OD
        </div>
        <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight mb-2">
          OpenDocs Gateway
        </h1>
        <p className="text-[15px] text-neutral-400 text-center max-w-md">
          Document intelligence powered by vLLM on AMD MI300X.
          Upload, ask, extract, compare.
        </p>
      </div>

      {/* Quick stats */}
      <div className="flex items-center justify-center gap-8 text-center mb-14">
        <div>
          <div className="text-2xl font-semibold text-neutral-900 tabular-nums">{docCount ?? '–'}</div>
          <div className="text-[12px] text-neutral-400 mt-0.5">documents</div>
        </div>
        <div className="w-px h-8 bg-neutral-200" />
        <div>
          <div className="text-2xl font-semibold text-neutral-900 tabular-nums">{metrics?.request_count ?? '–'}</div>
          <div className="text-[12px] text-neutral-400 mt-0.5">requests</div>
        </div>
        <div className="w-px h-8 bg-neutral-200" />
        <div>
          <div className="text-2xl font-semibold text-neutral-900 tabular-nums">
            {metrics?.p50_latency_sec != null ? `${metrics.p50_latency_sec}s` : '–'}
          </div>
          <div className="text-[12px] text-neutral-400 mt-0.5">p50 latency</div>
        </div>
      </div>

      {/* Actions — clean list, not rainbow cards */}
      <div className="space-y-1">
        {[
          { href: '/upload', label: 'Upload a document', sub: 'PDF or plain text' },
          { href: '/ask', label: 'Ask a question', sub: 'Grounded Q&A with citations' },
          { href: '/extract', label: 'Extract structured data', sub: 'JSON from any document' },
          { href: '/compare', label: 'Compare two documents', sub: 'Track changes across versions' },
          { href: '/multi', label: 'Multi-document analysis', sub: 'Query across your library' },
          { href: '/benchmark', label: 'View metrics', sub: 'Latency, throughput, token usage' },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="group flex items-center justify-between rounded-lg px-4 py-3 -mx-4 transition-colors hover:bg-neutral-50"
          >
            <div>
              <span className="text-[14px] text-neutral-800 group-hover:text-neutral-900">
                {item.label}
              </span>
              <span className="text-[13px] text-neutral-400 ml-2">
                {item.sub}
              </span>
            </div>
            <svg className="w-4 h-4 text-neutral-300 group-hover:text-neutral-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </Link>
        ))}
      </div>
    </div>
  );
}
