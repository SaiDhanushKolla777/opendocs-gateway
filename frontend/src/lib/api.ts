const API = process.env.NEXT_PUBLIC_API_URL || '';

export async function getHealth(): Promise<{ status: string }> {
  const r = await fetch(API ? `${API}/health` : '/api/health');
  if (!r.ok) throw new Error('Health check failed');
  return r.json();
}

export async function listDocuments(): Promise<Array<{
  document_id: string;
  title: string;
  filename: string;
  page_count: number | null;
  upload_timestamp: string;
}>> {
  const r = await fetch(API ? `${API}/documents` : '/api/documents');
  if (!r.ok) throw new Error('Failed to list documents');
  return r.json();
}

export async function uploadDocument(file: File): Promise<{
  document_id: string;
  title: string;
  filename: string;
  page_count: number | null;
  upload_timestamp: string;
}> {
  const form = new FormData();
  form.append('file', file);
  const r = await fetch(API ? `${API}/documents/upload` : '/api/documents/upload', {
    method: 'POST',
    body: form,
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || 'Upload failed');
  }
  return r.json();
}

export interface ChatMsg {
  role: 'user' | 'assistant';
  content: string;
}

export async function ask(
  documentId: string,
  question: string,
  answerMode = 'plain_english',
  history: ChatMsg[] = [],
) {
  const r = await fetch(
    API ? `${API}/documents/${documentId}/ask` : `/api/documents/${documentId}/ask`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, answer_mode: answerMode, history }),
    }
  );
  if (!r.ok) throw new Error('Ask failed');
  return r.json();
}

export async function askMulti(
  documentIds: string[],
  question: string,
  answerMode = 'plain_english',
  history: ChatMsg[] = [],
) {
  const r = await fetch(API ? `${API}/documents/ask-multi` : '/api/documents/ask-multi', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds, question, answer_mode: answerMode, history }),
  });
  if (!r.ok) throw new Error('Multi-doc ask failed');
  return r.json();
}

export async function extract(documentId: string, extractionType = 'default') {
  const r = await fetch(
    API ? `${API}/documents/${documentId}/extract` : `/api/documents/${documentId}/extract`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ extraction_type: extractionType }),
    }
  );
  if (!r.ok) throw new Error('Extract failed');
  return r.json();
}

export async function compare(oldId: string, newId: string) {
  const r = await fetch(API ? `${API}/compare` : '/api/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ old_document_id: oldId, new_document_id: newId }),
  });
  if (!r.ok) throw new Error('Compare failed');
  return r.json();
}

export async function getDocument(id: string) {
  const r = await fetch(API ? `${API}/documents/${id}` : `/api/documents/${id}`);
  if (!r.ok) throw new Error('Document not found');
  return r.json();
}

export async function getMetrics(): Promise<Record<string, number>> {
  const r = await fetch(API ? `${API}/metrics` : '/api/metrics');
  if (!r.ok) throw new Error('Metrics failed');
  return r.json();
}

export async function generateReport(): Promise<{ report: string }> {
  const r = await fetch(API ? `${API}/reports` : '/api/reports', { method: 'POST' });
  if (!r.ok) throw new Error('Report generation failed');
  return r.json();
}
