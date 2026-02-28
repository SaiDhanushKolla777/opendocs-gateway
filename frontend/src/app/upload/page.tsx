'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { uploadDocument } from '@/lib/api';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ document_id: string; title: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadDocument(file);
      setResult({ document_id: res.document_id, title: res.title });
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  return (
    <div className="animate-in">
      <h1 className="text-lg font-semibold text-neutral-900 tracking-tight">Upload document</h1>
      <p className="text-[14px] text-neutral-400 mt-1 mb-8">Add a PDF or text file for analysis.</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`rounded-xl border-2 border-dashed p-16 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-neutral-400 bg-neutral-50' :
          file ? 'border-neutral-300 bg-neutral-50' :
          'border-neutral-200 hover:border-neutral-300'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="hidden"
        />
        {file ? (
          <>
            <p className="text-[14px] font-medium text-neutral-800">{file.name}</p>
            <p className="text-[12px] text-neutral-400 mt-1">{(file.size / 1024).toFixed(0)} KB · Click to change</p>
          </>
        ) : (
          <>
            <p className="text-[14px] text-neutral-500">
              Drop a file here or <span className="text-neutral-800 font-medium">browse</span>
            </p>
            <p className="text-[12px] text-neutral-400 mt-1">.pdf or .txt</p>
          </>
        )}
      </div>

      <button
        onClick={handleSubmit}
        disabled={!file || loading}
        className="mt-4 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-[14px] font-medium text-white hover:bg-neutral-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Uploading…' : 'Upload & ingest'}
      </button>

      {error && (
        <p className="mt-4 text-[13px] text-red-600">{error}</p>
      )}

      {result && (
        <div className="mt-6 animate-in">
          <p className="text-[14px] text-neutral-800">
            <span className="font-medium">{result.title}</span> is ready.
          </p>
          <div className="flex gap-3 mt-3">
            <Link
              href={`/ask?document_id=${result.document_id}`}
              className="rounded-lg bg-neutral-900 px-4 py-2 text-[13px] font-medium text-white hover:bg-neutral-800 transition-colors"
            >
              Ask a question
            </Link>
            <Link
              href={`/extract?document_id=${result.document_id}`}
              className="rounded-lg border border-neutral-200 px-4 py-2 text-[13px] font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Extract data
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
