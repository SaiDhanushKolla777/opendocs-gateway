'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { extract } from '@/lib/api';
import DocumentSelector from '@/components/DocumentSelector';
import CitationCard from '@/components/CitationCard';

export default function ExtractPage() {
  return <Suspense><ExtractInner /></Suspense>;
}

function ExtractInner() {
  const params = useSearchParams();
  const [documentId, setDocumentId] = useState(params.get('document_id') || '');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ data: Record<string, unknown>; validation_status: string; citations?: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleExtract() {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await extract(documentId, 'default');
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed');
    } finally {
      setLoading(false);
    }
  }

  function copyJson() {
    if (!result) return;
    navigator.clipboard.writeText(JSON.stringify(result.data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="animate-in">
      <h1 className="text-lg font-semibold text-neutral-900 tracking-tight">Extract structured data</h1>
      <p className="text-[14px] text-neutral-400 mt-1 mb-8">Automatically detects document type and extracts the most relevant fields as JSON.</p>

      <div className="max-w-sm space-y-3 mb-8">
        <DocumentSelector value={documentId} onChange={setDocumentId} />
        <button
          onClick={handleExtract}
          disabled={loading || !documentId}
          className="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-[14px] font-medium text-white hover:bg-neutral-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Extracting…' : 'Extract'}
        </button>
      </div>

      {error && <p className="text-[13px] text-red-600">{error}</p>}

      {result && (
        <div className="animate-in">
          <div className="flex items-center gap-3 mb-3">
            <span className={`text-[12px] font-medium ${
              result.validation_status === 'valid' ? 'text-green-600' : 'text-amber-600'
            }`}>
              {result.validation_status === 'valid' ? 'Valid JSON' : 'Invalid JSON'}
            </span>
            <button
              onClick={copyJson}
              className="text-[12px] text-neutral-400 hover:text-neutral-600 transition-colors"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>

          <div className="rounded-lg bg-neutral-900 p-5 overflow-auto max-h-[420px]">
            <pre className="text-[12px] text-neutral-300 leading-relaxed font-mono">{JSON.stringify(result.data, null, 2)}</pre>
          </div>

          {result.citations && <CitationCard citations={result.citations} />}
        </div>
      )}
    </div>
  );
}
