'use client';

import { useState } from 'react';
import { compare } from '@/lib/api';
import DocumentSelector from '@/components/DocumentSelector';
import CitationCard from '@/components/CitationCard';

interface CompareResult {
  summary: string;
  structured_changes: {
    verdict?: string;
    additions?: string[];
    removals?: string[];
    modifications?: Array<{ section: string; change: string }>;
    key_differences?: string[];
    doc_a_about?: string;
    doc_b_about?: string;
    commonalities?: string[];
  };
  citations_old?: any[];
  citations_new?: any[];
}

const VERDICT_CONFIG: Record<string, { label: string; style: string }> = {
  identical:             { label: 'Identical',              style: 'bg-neutral-100 text-neutral-600' },
  minor_changes:         { label: 'Minor changes',          style: 'bg-amber-50 text-amber-700' },
  significant_changes:   { label: 'Significant changes',    style: 'bg-orange-50 text-orange-700' },
  completely_different:  { label: 'Different documents',    style: 'bg-blue-50 text-blue-700' },
};

function truncate(text: string, max = 200): string {
  if (!text) return '';
  const clean = text.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
  return clean.length <= max ? clean : clean.slice(0, max).trimEnd() + '…';
}

export default function ComparePage() {
  const [oldId, setOldId] = useState('');
  const [newId, setNewId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCompare() {
    if (!oldId || !newId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await compare(oldId, newId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
    } finally {
      setLoading(false);
    }
  }

  const sc = result?.structured_changes;
  const verdict = sc?.verdict && VERDICT_CONFIG[sc.verdict];
  const isDifferentDocs = sc?.verdict === 'completely_different';

  return (
    <div className="animate-in">
      <h1 className="text-lg font-semibold text-neutral-900 tracking-tight">Compare documents</h1>
      <p className="text-[14px] text-neutral-400 mt-1 mb-8">Compare versions or analyze differences between documents.</p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <DocumentSelector value={oldId} onChange={setOldId} label={isDifferentDocs ? 'Document A' : 'Old version'} />
        <DocumentSelector value={newId} onChange={setNewId} label={isDifferentDocs ? 'Document B' : 'New version'} />
      </div>

      <button
        onClick={handleCompare}
        disabled={loading || !oldId || !newId}
        className="rounded-lg bg-neutral-900 px-5 py-2.5 text-[14px] font-medium text-white hover:bg-neutral-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Analyzing…' : 'Compare'}
      </button>

      {error && <p className="mt-4 text-[13px] text-red-600">{error}</p>}

      {result && sc && (
        <div className="mt-8 animate-in space-y-5">
          {verdict && (
            <span className={`inline-block rounded-full px-3 py-1 text-[12px] font-medium ${verdict.style}`}>
              {verdict.label}
            </span>
          )}

          <p className="text-[14px] text-neutral-700 leading-[1.7]">{result.summary}</p>

          {/* Cross-document: show what each doc is about */}
          {isDifferentDocs && (sc.doc_a_about || sc.doc_b_about) && (
            <div className="grid grid-cols-2 gap-4">
              {sc.doc_a_about && (
                <div className="rounded-lg bg-neutral-50 p-3">
                  <h4 className="text-[11px] text-neutral-400 font-medium mb-1">Document A</h4>
                  <p className="text-[13px] text-neutral-600 leading-relaxed">{sc.doc_a_about}</p>
                </div>
              )}
              {sc.doc_b_about && (
                <div className="rounded-lg bg-neutral-50 p-3">
                  <h4 className="text-[11px] text-neutral-400 font-medium mb-1">Document B</h4>
                  <p className="text-[13px] text-neutral-600 leading-relaxed">{sc.doc_b_about}</p>
                </div>
              )}
            </div>
          )}

          <DiffSection title="Key differences" items={sc.key_differences} color="neutral" />

          {/* Version comparison sections */}
          {!isDifferentDocs && (
            <>
              <DiffSection title="Added" items={sc.additions} color="green" />
              <DiffSection title="Removed" items={sc.removals} color="red" />
              {sc.modifications && sc.modifications.length > 0 && (
                <div>
                  <h3 className="text-[12px] text-amber-600 font-medium mb-2">Modified</h3>
                  <div className="space-y-1.5">
                    {sc.modifications.map((m, i) => (
                      <div key={i} className="pl-3 border-l-2 border-amber-200">
                        <span className="text-[13px] font-medium text-neutral-700">{truncate(m.section, 80)}</span>
                        <span className="text-[13px] text-neutral-400 mx-1.5">—</span>
                        <span className="text-[13px] text-neutral-600">{truncate(m.change)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Cross-document: commonalities */}
          {isDifferentDocs && sc.commonalities && sc.commonalities.length > 0 && (
            <DiffSection title="Shared themes" items={sc.commonalities} color="blue" />
          )}

          {/* Citations */}
          <div className="grid grid-cols-2 gap-6 pt-3">
            <div>
              <h3 className="text-[12px] text-neutral-400 mb-2">{isDifferentDocs ? 'Document A' : 'Old document'}</h3>
              {result.citations_old && <CitationCard citations={result.citations_old} />}
            </div>
            <div>
              <h3 className="text-[12px] text-neutral-400 mb-2">{isDifferentDocs ? 'Document B' : 'New document'}</h3>
              {result.citations_new && <CitationCard citations={result.citations_new} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const BORDER_COLORS: Record<string, string> = {
  green: 'border-green-200',
  red: 'border-red-200',
  neutral: 'border-neutral-200',
  blue: 'border-blue-200',
};

const TITLE_COLORS: Record<string, string> = {
  green: 'text-green-600',
  red: 'text-red-600',
  neutral: 'text-neutral-500',
  blue: 'text-blue-600',
};

function DiffSection({ title, items, color }: { title: string; items?: string[]; color: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h3 className={`text-[12px] font-medium mb-2 ${TITLE_COLORS[color] || TITLE_COLORS.neutral}`}>{title}</h3>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <p key={i} className={`text-[13px] text-neutral-600 pl-3 border-l-2 leading-relaxed ${BORDER_COLORS[color] || BORDER_COLORS.neutral}`}>
            {truncate(item)}
          </p>
        ))}
      </div>
    </div>
  );
}
