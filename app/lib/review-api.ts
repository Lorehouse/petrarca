import { RESEARCH_BASE, fetchWithTimeout } from './chat-api';
import type { ReviewItem, ReviewQuestion, ReviewStats, ChapterCompleteResult } from '../data/types';

async function post<T>(path: string, body: object): Promise<T> {
  const res = await fetchWithTimeout(`${RESEARCH_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    timeout: 60000,
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetchWithTimeout(`${RESEARCH_BASE}${path}`, { timeout: 15000 });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export async function notifyChapterComplete(
  bookId: string, chapterNumber: number, chapterTitle: string
): Promise<ChapterCompleteResult> {
  return post('/review/chapter-complete', { book_id: bookId, chapter_number: chapterNumber, chapter_title: chapterTitle });
}

export async function getReviewQueue(limit = 20, bookId?: string): Promise<{ items: ReviewItem[]; count: number }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (bookId) params.append('book_id', bookId);
  return get(`/review/queue?${params}`);
}

export async function getReviewStats(): Promise<ReviewStats> {
  return get('/review/stats');
}

export async function generateQuestion(itemId: string): Promise<ReviewQuestion> {
  return post('/review/generate-question', { item_id: itemId });
}

export async function recordAnswer(
  itemId: string, score: 'knew' | 'partly' | 'missed'
): Promise<{ next_due_at: number; new_stability_days: number }> {
  return post('/review/answer', { item_id: itemId, score });
}

export async function createExplorationItems(
  itemId: string
): Promise<{ items_created: Array<{ id: string; question: string; lens: string }> }> {
  return post('/review/explore', { item_id: itemId });
}

export async function sendVoiceMemo(itemId: string, audioUri: string): Promise<{
  transcript: string;
  suggested_score: string;
  follow_ups_created: Array<{ id: string; question: string }>;
}> {
  const form = new FormData();
  form.append('item_id', itemId);
  form.append('audio', { uri: audioUri, type: 'audio/m4a', name: 'memo.m4a' } as any);
  const res = await fetchWithTimeout(`${RESEARCH_BASE}/review/voice-memo`, {
    method: 'POST',
    body: form,
    timeout: 60000,
  });
  if (!res.ok) throw new Error(`voice-memo failed: ${res.status}`);
  return res.json();
}
