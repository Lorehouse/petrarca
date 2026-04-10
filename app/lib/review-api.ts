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

export interface CurriculumNodeDetail {
  node_id: string;
  node_title: string;
  domain_id: string;
  domain_title: string;
}

export async function notifyArticleRead(
  articleId: string
): Promise<{
  nodes_found: number;
  items_surfaced: number;
  nodes: string[];
  curriculum_nodes_updated: number;
  curriculum_node_details: CurriculumNodeDetail[];
}> {
  return post('/review/article-read', { article_id: articleId });
}

export async function sendVoiceMemo(itemId: string, audioUri: string): Promise<{
  transcript: string;
  suggested_score: string;
  follow_ups_created: Array<{ id: string; question: string }>;
  microlearning_triggered?: Array<{ id: string; query: string }>;
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

// ── Chapter context (preview / review) ───────────────────────────────────────

export interface ChapterContextNode {
  node_id: string;
  node_title: string;
  description: string;
  knowledge: string;
  confidence: number;
  source_text: string;
  lens: string;
  temporal_hook?: string;
  is_new?: boolean;
  shaky_prerequisites?: Array<{
    node_id: string;
    node_title: string;
    description: string;
    knowledge: string;
  }>;
}

export interface ChapterContextResult {
  mode: 'preview' | 'review';
  domain_id: string;
  chapter_number: number;
  chapter_title: string;
  nodes: ChapterContextNode[];
  assessment_question?: { node_id: string; node_title: string; question: string };
  summary: { total: number; known: number; new: number };
  message?: string;
}

export async function getChapterContext(
  bookId: string, chapterNumber: number, chapterTitle: string, mode: 'preview' | 'review'
): Promise<ChapterContextResult> {
  return post('/review/chapter-context', { book_id: bookId, chapter_number: chapterNumber, chapter_title: chapterTitle, mode });
}

// ── Hamarquizen (PRIME→READ→TEST) ────────────────────────────────────────────

export interface HamarquizenCard {
  item_id: string;
  node_id: string;
  domain_id: string;
  node_title: string;
  book_id: string;
  book_title: string;
  prime: string;
  read: string;
  test: string;
  answer: string;
  temporal_hook: string;
  knowledge: string;
  confidence: number;
}

export async function getHamarquizenSession(
  bookId: string, limit = 5
): Promise<{ cards: HamarquizenCard[]; count: number }> {
  return post('/review/hamarquizen', { book_id: bookId, limit });
}

export async function getCrossBookHamarquizen(
  limit = 5
): Promise<{ cards: HamarquizenCard[]; count: number }> {
  return post('/review/hamarquizen-cross', { limit });
}

// ── Voice elicitation (free recall) ─────────────────────────────────────────

export interface ElicitationCandidate {
  type?: 'chapter_recall' | 'book_recall' | 'era_sweep';  // absent for standard curriculum nodes
  node_id: string;
  node_title: string;
  node_description: string;
  domain_id: string;
  domain_title?: string;
  knowledge: string;
  confidence: number;
  elicitation_score: number;
  book_id?: string;
  book_title?: string;
  chapter_number?: number;
  chapter_title?: string;
}

export interface ElicitationResult {
  captured: string[];
  missed: string[];
  interesting: string[];
  wonderings: string[];
  coverage_pct: number;
  suggested_score: string;
  feedback_summary: string;
  temporal_hook: string;
  node_title: string;
  node_description: string;
  transcript: string;
  research_triggers: Array<{ id: string; question: string }>;
  microlearning_triggered?: Array<{ id: string; query: string }>;
  /** Set on validation errors (422) — e.g. 'too_short', 'Transcription failed' */
  error?: string;
}

export async function getElicitationCandidates(
  domainId?: string, limit = 5
): Promise<{ candidates: ElicitationCandidate[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (domainId) params.append('domain_id', domainId);
  return get(`/review/elicit-candidates?${params}`);
}

export async function reportKnowNothing(
  nodeId: string, domainId: string
): Promise<{ ok: boolean }> {
  return post('/review/elicit-know-nothing', { node_id: nodeId, domain_id: domainId });
}

/**
 * Lightweight check: does a cached result already exist for this request_id?
 * Returns the cached result or null. Never throws — returns null on any error.
 */
export async function checkVoiceElicitCache(requestId: string): Promise<ElicitationResult | null> {
  try {
    const res = await fetchWithTimeout(
      `${RESEARCH_BASE}/review/voice-elicit-check?request_id=${encodeURIComponent(requestId)}`,
      { timeout: 5000 },
    );
    if (res.ok) return res.json();
    return null;
  } catch {
    return null;
  }
}

export async function sendVoiceElicitation(
  nodeId: string, domainId: string, audioUri: string, requestId?: string
): Promise<ElicitationResult> {
  const form = new FormData();
  form.append('node_id', nodeId);
  form.append('domain_id', domainId);
  if (requestId) form.append('request_id', requestId);
  form.append('audio', { uri: audioUri, type: 'audio/m4a', name: 'elicit.m4a' } as any);
  const headers: Record<string, string> = {};
  if (requestId) headers['X-Request-ID'] = requestId;
  const res = await fetchWithTimeout(`${RESEARCH_BASE}/review/voice-elicit`, {
    method: 'POST',
    headers,
    body: form,
    timeout: 90000,
  });
  // 422 = validation error (too_short, transcription_failed) — return the body
  // which contains feedback_summary. Don't throw — let caller show the feedback.
  if (res.status === 422) {
    return res.json();
  }
  if (!res.ok) {
    const err = new Error(`voice-elicit failed: ${res.status}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// ── Knowledge Sweep API ──────────────────────────────────────────────

export interface SweepPlan {
  domain_id: string;
  domain_title: string;
  system_coverage: number;
  eras: SweepEra[];
  total_l2_nodes: number;
  sweep_type: string;
}

export interface SweepEra {
  era_id: string;
  title: string;
  prompt: string;
  children: { id: string; title: string }[];
  child_count: number;
}

export interface SweepResult {
  id: string;
  domain_id: string;
  domain_title: string;
  total_coverage: number;
  total_accuracy: number;
  connectivity_score: number;
  organization_score: number;
  composite_score: number;
  total_nodes_mentioned: number;
  nodes_total: number;
  system_coverage: number;
  delta_coverage: number | null;
  delta_composite: number | null;
  scoring_detail: {
    nodes: { node_id: string; node_title: string; mentioned: boolean; depth: string; facts: any[] }[];
    connections: any[];
    organization: { pattern: string; causal_count: number };
    errors: any[];
    strongest_area: string;
    biggest_gap: string;
    summary: string;
  };
}

export interface SweepGap {
  era_id: string;
  era_title: string;
  prompt: string;
  missed_nodes: { id: string; title: string }[];
}

export async function getSweepPlan(domainId: string): Promise<SweepPlan> {
  return get(`/knowledge/sweep/plan/${domainId}`);
}

export async function getSweepDomains(): Promise<{
  domains: { id: string; title: string; node_count: number; last_sweep: any }[];
}> {
  return get('/knowledge/sweep/domains');
}

export async function transcribeSweepEra(
  audioUri: string,
  eraId: string,
): Promise<{ transcript: string; era_id: string; too_short?: boolean }> {
  const form = new FormData();
  form.append('era_id', eraId);
  form.append('audio', { uri: audioUri, type: 'audio/m4a', name: 'sweep.m4a' } as any);
  const res = await fetchWithTimeout(`${RESEARCH_BASE}/knowledge/sweep/transcribe`, {
    method: 'POST',
    body: form,
    timeout: 60000,
  });
  if (!res.ok) throw new Error(`transcribe failed: ${res.status}`);
  return res.json();
}

export async function submitSweep(
  domainId: string,
  phase1Eras: { era_id: string; transcript: string; duration_s: number }[],
  phase2Transcript?: string,
): Promise<SweepResult> {
  const res = await fetchWithTimeout(`${RESEARCH_BASE}/knowledge/sweep/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      domain_id: domainId,
      phase1_eras: phase1Eras,
      phase2_transcript: phase2Transcript,
    }),
    timeout: 300000, // 5 min — LLM scoring is slow
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.error || `submit failed: ${res.status}`);
  }
  return res.json();
}

export async function getSweepGaps(
  domainId: string,
  scoringResult: any,
): Promise<{ gaps: SweepGap[]; gap_count: number }> {
  return post('/knowledge/sweep/gaps', { domain_id: domainId, scoring_result: scoringResult });
}

export async function getSweepHistory(
  domainId: string,
): Promise<{ sweeps: any[]; domain_id: string }> {
  return get(`/knowledge/sweep/history/${domainId}`);
}
