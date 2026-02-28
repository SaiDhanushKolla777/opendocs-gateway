'use client';

import { useState } from 'react';

interface Citation {
  snippet: string;
  page_number?: number | null;
  document_title?: string;
  chunk_id?: string;
}

export default function CitationCard({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);
  if (!citations?.length) return null;

  const shown = open ? citations : citations.slice(0, 3);

  return (
    <div className="mt-4 pt-3 border-t border-neutral-100">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[12px] text-neutral-400 hover:text-neutral-600 transition-colors mb-3"
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        {citations.length} source{citations.length !== 1 ? 's' : ''}
        {!open && citations.length > 3 ? ' — show all' : open && citations.length > 3 ? ' — collapse' : ''}
      </button>
      <div className="space-y-2">
        {shown.map((c, i) => (
          <div key={i} className="group pl-3 border-l-[2px] border-neutral-150 hover:border-neutral-300 transition-colors">
            <p className="text-[13px] text-neutral-500 leading-relaxed">{c.snippet}</p>
            <p className="text-[11px] text-neutral-300 mt-0.5">
              {c.document_title || 'Unknown source'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
