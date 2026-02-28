'use client';

import { useState, useRef, useEffect } from 'react';
import { askMulti, ChatMsg } from '@/lib/api';
import { MultiDocumentSelector } from '@/components/DocumentSelector';
import CitationCard from '@/components/CitationCard';

function stripChunkRefs(text: string): string {
  return text
    .replace(/\[Chunk\s*\d+\]/gi, '')
    .replace(/\(\s*(,\s*)*\)/g, '')
    .replace(/\(\s*,/g, '(')
    .replace(/,\s*\)/g, ')')
    .replace(/,(\s*,)+/g, ',')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
  citations?: any[];
  insufficient?: boolean;
}

export default function MultiPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleAsk() {
    if (selectedIds.length === 0 || !question.trim()) return;
    const q = question.trim();
    setQuestion('');
    setMessages((prev) => [...prev, { role: 'user', text: q }]);
    setLoading(true);
    try {
      const history: ChatMsg[] = messages.map((m) => ({ role: m.role, content: m.text }));
      const res = await askMulti(selectedIds, q, 'plain_english', history);
      const clean = stripChunkRefs(res.answer || '');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: clean, citations: res.citations, insufficient: res.insufficient_evidence },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', text: 'Request failed. Try again.' }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-in flex flex-col" style={{ height: 'calc(100vh - 7rem)' }}>
      {/* Document picker */}
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-neutral-900 tracking-tight mb-1">Multi-document analysis</h1>
        <p className="text-[14px] text-neutral-400 mb-4">Ask questions across multiple documents.</p>
        <MultiDocumentSelector value={selectedIds} onChange={setSelectedIds} />
        {selectedIds.length > 0 && (
          <p className="text-[12px] text-neutral-500 mt-2">{selectedIds.length} selected</p>
        )}
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto space-y-6 mb-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-32">
            <p className="text-[14px] text-neutral-300">Select documents and ask a question.</p>
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
                  <p className="text-[12px] text-amber-600 mb-1">Limited evidence</p>
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
              <span key={i} className="w-1.5 h-1.5 rounded-full bg-neutral-300" style={{ animation: `pulse-dot 1.4s ${i * 0.2}s infinite ease-in-out` }} />
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
          placeholder={selectedIds.length > 0 ? 'Ask across selected documents…' : 'Select documents first'}
          disabled={loading || selectedIds.length === 0}
          className="flex-1 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-[14px] placeholder:text-neutral-300 focus:bg-white focus:border-neutral-300 focus:ring-0 focus:outline-none disabled:opacity-40 transition-colors"
        />
        <button
          onClick={handleAsk}
          disabled={loading || selectedIds.length === 0 || !question.trim()}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-20 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
