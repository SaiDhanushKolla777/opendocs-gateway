'use client';

import { useEffect, useState, useRef } from 'react';
import { listDocuments } from '@/lib/api';

interface Doc {
  document_id: string;
  title: string;
  filename: string;
  upload_timestamp: string;
}

interface Props {
  value: string;
  onChange: (id: string) => void;
  label?: string;
}

export default function DocumentSelector({ value, onChange, label }: Props) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDocuments().then(setDocs).catch(() => {});
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  useEffect(() => {
    if (open) {
      setSearch('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const selected = docs.find((d) => d.document_id === value);
  const filtered = docs.filter(
    (d) => !search || d.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div ref={ref} className="relative">
      {label && <label className="block text-[13px] text-neutral-500 mb-1.5">{label}</label>}

      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-2 rounded-xl border px-4 py-2.5 text-left transition-colors ${
          open
            ? 'border-neutral-400 bg-white'
            : 'border-neutral-200 bg-neutral-50 hover:bg-white hover:border-neutral-300'
        }`}
      >
        {selected ? (
          <div className="flex-1 min-w-0">
            <span className="text-[14px] text-neutral-800 truncate block">{selected.title}</span>
          </div>
        ) : (
          <span className="flex-1 text-[14px] text-neutral-400">Select a document</span>
        )}
        <svg
          className={`w-4 h-4 text-neutral-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1.5 w-full rounded-xl border border-neutral-200 bg-white shadow-lg shadow-neutral-200/50 overflow-hidden animate-in">
          {/* Search */}
          <div className="p-2 border-b border-neutral-100">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search documents…"
              className="w-full rounded-lg bg-neutral-50 px-3 py-2 text-[13px] text-neutral-800 placeholder:text-neutral-300 focus:outline-none focus:bg-neutral-100 transition-colors"
            />
          </div>

          {/* Options */}
          <div className="max-h-60 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-4 py-6 text-center text-[13px] text-neutral-400">
                {docs.length === 0 ? 'No documents uploaded' : 'No matches'}
              </div>
            ) : (
              filtered.map((d) => (
                <button
                  key={d.document_id}
                  type="button"
                  onClick={() => { onChange(d.document_id); setOpen(false); }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                    d.document_id === value
                      ? 'bg-neutral-100'
                      : 'hover:bg-neutral-50'
                  }`}
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-neutral-100">
                    <svg className="w-4 h-4 text-neutral-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] text-neutral-800 truncate">{d.title}</p>
                    <p className="text-[11px] text-neutral-400">{d.filename}</p>
                  </div>
                  {d.document_id === value && (
                    <svg className="w-4 h-4 text-neutral-800 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function MultiDocumentSelector({
  value,
  onChange,
}: {
  value: string[];
  onChange: (ids: string[]) => void;
}) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDocuments().then(setDocs).catch(() => {});
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  useEffect(() => {
    if (open) {
      setSearch('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  function toggle(id: string) {
    onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);
  }

  const selectedDocs = docs.filter((d) => value.includes(d.document_id));
  const filtered = docs.filter(
    (d) => !search || d.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center gap-2 rounded-xl border px-4 py-2.5 text-left transition-colors ${
          open
            ? 'border-neutral-400 bg-white'
            : 'border-neutral-200 bg-neutral-50 hover:bg-white hover:border-neutral-300'
        }`}
      >
        {selectedDocs.length > 0 ? (
          <div className="flex-1 min-w-0 flex flex-wrap gap-1.5">
            {selectedDocs.map((d) => (
              <span
                key={d.document_id}
                className="inline-flex items-center gap-1 rounded-md bg-neutral-200/60 px-2 py-0.5 text-[12px] text-neutral-700"
              >
                {d.title.length > 20 ? d.title.slice(0, 20) + '…' : d.title}
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); toggle(d.document_id); }}
                  className="text-neutral-400 hover:text-neutral-600"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        ) : (
          <span className="flex-1 text-[14px] text-neutral-400">Select documents</span>
        )}
        <svg
          className={`w-4 h-4 text-neutral-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1.5 w-full rounded-xl border border-neutral-200 bg-white shadow-lg shadow-neutral-200/50 overflow-hidden animate-in">
          <div className="p-2 border-b border-neutral-100">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search documents…"
              className="w-full rounded-lg bg-neutral-50 px-3 py-2 text-[13px] text-neutral-800 placeholder:text-neutral-300 focus:outline-none focus:bg-neutral-100 transition-colors"
            />
          </div>
          <div className="max-h-60 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-4 py-6 text-center text-[13px] text-neutral-400">
                {docs.length === 0 ? 'No documents uploaded' : 'No matches'}
              </div>
            ) : (
              filtered.map((d) => {
                const checked = value.includes(d.document_id);
                return (
                  <button
                    key={d.document_id}
                    type="button"
                    onClick={() => toggle(d.document_id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                      checked ? 'bg-neutral-100' : 'hover:bg-neutral-50'
                    }`}
                  >
                    <div className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                      checked ? 'bg-neutral-800 border-neutral-800' : 'border-neutral-300'
                    }`}>
                      {checked && (
                        <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] text-neutral-800 truncate">{d.title}</p>
                      <p className="text-[11px] text-neutral-400">{d.filename}</p>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
