'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getDocument } from '@/lib/api';

interface DocDetail {
  document_id: string;
  title: string;
  filename: string;
  page_count: number | null;
  upload_timestamp: string;
}

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [doc, setDoc] = useState<DocDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) getDocument(id).then(setDoc).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="h-40 rounded-lg bg-neutral-50" />;
  if (!doc) return <p className="text-[14px] text-neutral-400">Document not found.</p>;

  return (
    <div className="animate-in">
      <Link href="/documents" className="text-[13px] text-neutral-400 hover:text-neutral-600 transition-colors mb-6 inline-block">
        &larr; Documents
      </Link>

      <h1 className="text-lg font-semibold text-neutral-900 tracking-tight">{doc.title}</h1>
      <div className="flex items-center gap-3 mt-2 mb-8">
        <span className="text-[12px] text-neutral-400">{doc.filename}</span>
        {doc.page_count != null && (
          <>
            <span className="text-neutral-200">·</span>
            <span className="text-[12px] text-neutral-400">{doc.page_count} chunks</span>
          </>
        )}
        <span className="text-neutral-200">·</span>
        <span className="text-[12px] text-neutral-400">{new Date(doc.upload_timestamp).toLocaleString()}</span>
      </div>

      <div className="space-y-1">
        <Link
          href={`/ask?document_id=${doc.document_id}`}
          className="group flex items-center justify-between rounded-lg px-4 py-3 -mx-4 hover:bg-neutral-50 transition-colors"
        >
          <div>
            <span className="text-[14px] text-neutral-800">Ask a question</span>
            <span className="text-[13px] text-neutral-400 ml-2">Grounded Q&A with citations</span>
          </div>
          <svg className="w-4 h-4 text-neutral-300 group-hover:text-neutral-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </Link>
        <Link
          href={`/extract?document_id=${doc.document_id}`}
          className="group flex items-center justify-between rounded-lg px-4 py-3 -mx-4 hover:bg-neutral-50 transition-colors"
        >
          <div>
            <span className="text-[14px] text-neutral-800">Extract data</span>
            <span className="text-[13px] text-neutral-400 ml-2">Structured JSON output</span>
          </div>
          <svg className="w-4 h-4 text-neutral-300 group-hover:text-neutral-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
