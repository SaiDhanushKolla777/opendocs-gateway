'use client';

import { Suspense, useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { ask, ChatMsg } from '@/lib/api';
import DocumentSelector from '@/components/DocumentSelector';
import CitationCard from '@/components/CitationCard';

function stripChunkRefs(text: string): string {
  return text
    .replace(/\[Chunk\s*\d+\]/gi, '')
    .replace(/\(\s*(,\s*)*\)/g, '')       // empty parentheses: (, , ,)
    .replace(/\(\s*,/g, '(')              // leading comma in parens
    .replace(/,\s*\)/g, ')')              // trailing comma in parens
    .replace(/,(\s*,)+/g, ',')            // consecutive commas
    .replace(/\s{2,}/g, ' ')
    .trim();
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
  citations?: Array<{ snippet: string; page_number?: number | null; document_title?: string }>;
  insufficient?: boolean;
}

export default function AskPage() {
  return <Suspense><AskInner /></Suspense>;
}

function AskInner() {
  const params = useSearchParams();
  const [documentId, setDocumentId] = useState(params.get('document_id') || '');
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState('plain_english');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleAsk() {
    if (!documentId || !question.trim()) return;
    const q = question.trim();
    setQuestion('');
    setMessages((prev) => [...prev, { role: 'user', text: q }]);
    setLoading(true);
    try {
      const history: ChatMsg[] = messages.map((m) => ({ role: m.role, content: m.text }));
      const res = await ask(documentId, q, mode, history);
      const clean = stripChunkRefs(res.answer || '');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: clean, citations: res.citations, insufficient: res.insufficient_evidence },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', text: 'Something went wrong. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-in flex flex-col" style={{ height: 'calc(100vh - 7rem)' }}>
      {/* Header */}
      <div className="flex items-end gap-3 mb-5">
        <div className="flex-1">
          <DocumentSelector value={documentId} onChange={setDocumentId} label="" />
        </div>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-[13px] text-neutral-600 focus:border-neutral-400 focus:ring-0 focus:outline-none"
        >
          <option value="plain_english">Plain English</option>
          <option value="concise_bullets">Bullets</option>
          <option value="executive_summary">Executive</option>
          <option value="student_friendly">Simple</option>
        </select>
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full">
            <p className="text-[14px] text-neutral-300">Ask a question about your document.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className="animate-in">
            {m.role === 'user' ? (
              <div className="flex justify-end">
                <div className="max-w-[75%] rounded-2xl rounded-br-md bg-neutral-900 px-4 py-2.5 text-[14px] text-white leading-relaxed">
                  {m.text}
                </div>
              </div>
            ) : (
              <div className="max-w-[85%]">
                {m.insufficient && (
                  <p className="text-[12px] text-amber-600 mb-1">Limited evidence found</p>
                )}
                <div className="text-[14px] text-neutral-700 leading-[1.7] whitespace-pre-wrap">{m.text}</div>
                {m.citations && <CitationCard citations={m.citations} />}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-1 items-center pl-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-neutral-300"
                style={{ animation: `pulse-dot 1.4s ${i * 0.2}s infinite ease-in-out` }}
              />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 items-center">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAsk()}
          placeholder={documentId ? 'Ask about this document…' : 'Select a document first'}
          disabled={loading || !documentId}
          className="flex-1 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-[14px] placeholder:text-neutral-300 focus:bg-white focus:border-neutral-300 focus:ring-0 focus:outline-none disabled:opacity-40 transition-colors"
        />
        <button
          onClick={handleAsk}
          disabled={loading || !documentId || !question.trim()}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
