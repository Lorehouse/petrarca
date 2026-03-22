/**
 * API client for physical book server endpoints.
 * Follows the same FormData upload pattern as chat-api.ts.
 */

import { Platform } from 'react-native';
import { RESEARCH_BASE, fetchWithTimeout } from './chat-api';
import type {
  PhysicalBookChapter, BookResearch, ChapterInsights, StorySoFarBriefing,
} from '../data/types';

// --- Response types ---

export interface BookIdentifyResult {
  title: string;
  author: string;
  cover_url?: string;
  isbn?: string;
  publisher?: string;
  year?: number;
  page_count?: number;
  topics: string[];
  chapters?: PhysicalBookChapter[];
}

export interface TOCParseResult {
  chapters: PhysicalBookChapter[];
}

export interface PageOCRResult {
  text: string;
  detected_page_number?: number;
  extracted_ideas: string[];
  topics: string[];
}

export interface BookVoiceNoteResult {
  id: string;
  transcript: string;
  extracted_ideas: string[];
  topics: string[];
}

export interface PageOCRResultEnhanced extends PageOCRResult {
  key_passage?: string;
  elaborative_question?: string;
}

// --- Helper: create FormData with image ---

function appendImage(formData: FormData, fieldName: string, imageUri: string): void {
  if (Platform.OS === 'web' && imageUri.startsWith('data:')) {
    // Web: convert data URI to blob
    fetch(imageUri)
      .then(r => r.blob())
      .then(blob => formData.append(fieldName, blob, 'photo.jpg'));
  } else if (Platform.OS === 'web' && imageUri.startsWith('blob:')) {
    fetch(imageUri)
      .then(r => r.blob())
      .then(blob => formData.append(fieldName, blob, 'photo.jpg'));
  } else {
    // Native: use URI object
    const ext = imageUri.split('.').pop()?.toLowerCase() || 'jpg';
    const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg';
    formData.append(fieldName, {
      uri: imageUri,
      type: mimeType,
      name: `photo.${ext}`,
    } as any);
  }
}

// --- API functions ---

export async function identifyBookCover(
  photoUri: string,
): Promise<BookIdentifyResult> {
  const formData = new FormData();
  appendImage(formData, 'photo', photoUri);

  const resp = await fetch(`${RESEARCH_BASE}/book/identify`, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Book identify failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

export async function ocrTableOfContents(
  photoUri: string,
  bookId: string,
): Promise<TOCParseResult> {
  const formData = new FormData();
  appendImage(formData, 'photo', photoUri);
  formData.append('book_id', bookId);

  const resp = await fetch(`${RESEARCH_BASE}/book/ocr-toc`, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`TOC OCR failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

export async function ocrPage(
  photoUri: string,
  bookId: string,
  bookTitle: string,
  pageNumber?: number,
  chapter?: string,
): Promise<PageOCRResult> {
  const formData = new FormData();
  appendImage(formData, 'photo', photoUri);
  formData.append('book_id', bookId);
  formData.append('book_title', bookTitle);
  if (pageNumber !== undefined) formData.append('page_number', String(pageNumber));
  if (chapter) formData.append('chapter', chapter);

  const resp = await fetch(`${RESEARCH_BASE}/book/ocr-page`, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Page OCR failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

export async function uploadBookVoiceNote(
  audioUri: string,
  bookId: string,
  bookTitle: string,
  chapter?: string,
  pageNumber?: number,
): Promise<BookVoiceNoteResult> {
  const formData = new FormData();
  formData.append('audio', {
    uri: audioUri,
    type: 'audio/m4a',
    name: 'note.m4a',
  } as any);
  formData.append('book_id', bookId);
  formData.append('book_title', bookTitle);
  if (chapter) formData.append('chapter', chapter);
  if (pageNumber !== undefined) formData.append('page_number', String(pageNumber));

  const resp = await fetch(`${RESEARCH_BASE}/book/voice-note`, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Book voice note upload failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

// --- Book Research API ---

export async function researchBook(
  bookId: string,
  title: string,
  author: string,
  chapters: PhysicalBookChapter[],
  topics: string[],
  isbn?: string,
): Promise<void> {
  const resp = await fetchWithTimeout(`${RESEARCH_BASE}/book/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      book_id: bookId, title, author, isbn,
      chapters: chapters.map(ch => ({ number: ch.number, title: ch.title })),
      topics,
    }),
    timeout: 120000, // research spawns claude -p, can take a while
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Book research failed (${resp.status}): ${text}`);
  }
}

export async function getBookResearch(
  bookId: string,
): Promise<BookResearch | null> {
  const resp = await fetchWithTimeout(`${RESEARCH_BASE}/book/research/${bookId}`, { timeout: 8000 });
  if (resp.status === 404) return null;
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Get book research failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

export async function getChapterInsights(
  bookId: string,
  chapterNumber: number,
  chapterTitle: string,
  captures?: Array<{ text?: string; ocr_text?: string; transcript?: string; chapter?: string }>,
): Promise<ChapterInsights> {
  const resp = await fetch(`${RESEARCH_BASE}/book/chapter-insights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      book_id: bookId,
      chapter_number: chapterNumber,
      chapter_title: chapterTitle,
      captures: captures || [],
    }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Chapter insights failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

export async function getStorySoFar(
  bookId: string,
  title: string,
  author: string,
  currentChapter?: string,
  currentPage?: number,
  pageCount?: number,
  captures?: Array<{ text?: string; ocr_text?: string; transcript?: string; chapter?: string; page_number?: number; extracted_ideas?: string[] }>,
): Promise<StorySoFarBriefing> {
  const resp = await fetchWithTimeout(`${RESEARCH_BASE}/book/story-so-far`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      book_id: bookId, title, author,
      current_chapter: currentChapter,
      current_page: currentPage,
      page_count: pageCount,
      captures: captures || [],
    }),
    timeout: 30000,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Story so far failed (${resp.status}): ${text}`);
  }
  return resp.json();
}

// --- Curriculum context for books ---

export interface BookCurriculumMapping {
  node_id: string;
  node_title: string;
  coverage: 'surface' | 'moderate' | 'deep';
  evidence: string;
  knowledge: 'unknown' | 'mentioned' | 'engaged' | 'anchored';
  interest: string;
  confidence: number;
  description: string;
}

export interface CrossBookConnection {
  node_id: string;
  node_title: string;
  other_book_id: string;
  other_book_title: string;
  other_coverage: string;
}

export interface BookCurriculumDomain {
  domain_id: string;
  domain_title: string;
  node_count: number;
  mappings: BookCurriculumMapping[];
  cross_book_connections: CrossBookConnection[];
}

export interface BookCurriculumContext {
  domains: BookCurriculumDomain[];
}

export async function getBookCurriculumContext(
  bookId: string,
): Promise<BookCurriculumContext> {
  const resp = await fetch(`${RESEARCH_BASE}/curriculum/book-context/${bookId}`);
  if (!resp.ok) return { domains: [] };
  return resp.json();
}

// --- Book Sync API (server-authoritative persistence) ---

import type { PhysicalBook, BookCapture } from '../data/types';

export async function syncBooksToServer(
  books: PhysicalBook[],
  captures: BookCapture[],
): Promise<void> {
  try {
    // Strip local-only fields (photo URIs, audio URIs) that won't work on server
    const cleanBooks = books.map(b => ({
      ...b,
      cover_image_uri: undefined, // local file path, not useful on server
    }));
    const cleanCaptures = captures.map(c => ({
      ...c,
      photo_uri: undefined,
      audio_uri: undefined,
    }));

    await fetchWithTimeout(`${RESEARCH_BASE}/book/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ books: cleanBooks, captures: cleanCaptures }),
      timeout: 10000,
    });
  } catch {
    // Sync failure is non-critical — local data is preserved
  }
}

export async function loadBooksFromServer(): Promise<{
  books: PhysicalBook[];
  captures: BookCapture[];
}> {
  const resp = await fetchWithTimeout(`${RESEARCH_BASE}/book/sync`, { timeout: 8000 });
  if (!resp.ok) return { books: [], captures: [] };
  return resp.json();
}

// --- Resurfacing API ---

import type { ResurfacingSession } from '../data/types';

export async function generateResurfacingSession(
  includeDialogues: boolean = true,
): Promise<ResurfacingSession> {
  const resp = await fetch(`${RESEARCH_BASE}/book/resurfacing/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ include_dialogues: includeDialogues }),
  });
  if (!resp.ok) throw new Error(`Resurfacing generate failed (${resp.status})`);
  return resp.json();
}

export async function respondToResurfacing(
  captureId: string,
  responseText: string,
  responseType: 'text' | 'voice' = 'text',
): Promise<void> {
  await fetch(`${RESEARCH_BASE}/book/resurfacing/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capture_id: captureId, response_text: responseText, response_type: responseType }),
  });
}

export async function skipResurfacing(captureId: string): Promise<void> {
  await fetch(`${RESEARCH_BASE}/book/resurfacing/skip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capture_id: captureId }),
  });
}

export async function getResurfacingStatus(): Promise<Record<string, unknown>> {
  const resp = await fetch(`${RESEARCH_BASE}/book/resurfacing/status`);
  if (!resp.ok) return {};
  return resp.json();
}

export async function processKindleBooks(max: number = 10): Promise<void> {
  await fetch(`${RESEARCH_BASE}/book/process-kindle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max }),
  });
}

export async function includeKindleBook(key: string): Promise<{
  book: PhysicalBook;
  captures: BookCapture[];
  already_existed: boolean;
}> {
  const resp = await fetch(`${RESEARCH_BASE}/kindle/include`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Kindle include failed (${resp.status}): ${text}`);
  }
  return resp.json();
}
