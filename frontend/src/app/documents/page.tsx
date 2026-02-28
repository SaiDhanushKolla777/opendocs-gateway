'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { listDocuments } from '@/lib/api';

interface Doc {
  document_id: string;
  title: string;
  filename: string;
  page_count: number | null;
  upload_timestamp: string;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDocuments().then(setDocs).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-lg font-semibold text-neutral-900 tracking-tight">Documents</h1>
          <p className="text-[14px] text-neutral-400 mt-0.5">{docs.length} uploaded</p>
        </div>
        <Link
          href="/upload"
          className="rounded-lg bg-neutral-900 px-4 py-2 text-[13px] font-medium text-white hover:bg-neutral-800 transition-colors"
        >
          Upload
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-14 rounded-lg bg-neutral-50" />)}
        </div>
      ) : docs.length === 0 ? (
        <div className="py-20 text-center">
          <p className="text-[14px] text-neutral-400">No documents yet.</p>
          <Link href="/upload" className="text-[14px] text-neutral-800 font-medium hover:underline mt-1 inline-block">
            Upload your first
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-neutral-100">
          {docs.map((d) => (
            <Link
              key={d.document_id}
              href={`/documents/${d.document_id}`}
              className="group flex items-center justify-between py-3 -mx-2 px-2 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-[14px] text-neutral-800 truncate">{d.title}</p>
                <p className="text-[12px] text-neutral-400 mt-0.5">{d.filename}</p>
              </div>
              <div className="flex items-center gap-4 shrink-0 ml-4">
                {d.page_count != null && (
                  <span className="text-[12px] text-neutral-400">{d.page_count} chunks</span>
                )}
                <span className="text-[12px] text-neutral-300">{new Date(d.upload_timestamp).toLocaleDateString()}</span>
                <svg className="w-4 h-4 text-neutral-300 group-hover:text-neutral-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
