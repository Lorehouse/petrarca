/**
 * Persistent background upload queue for book page photos.
 *
 * Uploads start immediately when enqueued, run concurrently (up to 2),
 * retry with exponential backoff, and survive app restarts via AsyncStorage.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { RESEARCH_BASE } from './chat-api';
import { updateBookCapture } from '../data/book-store';
import { logEvent } from '../data/logger';

const QUEUE_KEY = '@petrarca/photo_upload_queue';
const MAX_CONCURRENT = 2;
const MAX_RETRIES = 10;
const BASE_DELAY_MS = 2000;

export interface UploadItem {
  captureId: string;
  photoUri: string;
  bookId: string;
  bookTitle: string;
  chapter?: string;
  pageNumber?: number;
  retryCount: number;
  nextRetryAt: number; // timestamp
}

let queue: UploadItem[] = [];
let activeUploads = 0;
let initialized = false;

// Capture IDs we're waiting on OCR results for (uploaded but not yet processed)
let pendingOcrIds: Set<string> = new Set();
const PENDING_OCR_KEY = '@petrarca/pending_ocr_ids';

type QueueListener = (queue: UploadItem[]) => void;
const listeners: Set<QueueListener> = new Set();

export function onUploadQueueChange(fn: QueueListener): () => void {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

function notifyListeners() {
  for (const fn of listeners) {
    try { fn([...queue]); } catch { /* ignore */ }
  }
}

export async function initUploadQueue(): Promise<void> {
  if (initialized) return;
  initialized = true;

  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    if (raw) queue = JSON.parse(raw);
  } catch { /* start fresh */ }

  try {
    const raw = await AsyncStorage.getItem(PENDING_OCR_KEY);
    if (raw) pendingOcrIds = new Set(JSON.parse(raw));
  } catch { /* start fresh */ }

  // Start processing immediately
  processQueue();
}

export function getUploadQueueStatus(): { queued: number; uploading: number; pendingOcr: number } {
  return {
    queued: queue.length,
    uploading: activeUploads,
    pendingOcr: pendingOcrIds.size,
  };
}

export async function enqueuePhotoUpload(item: Omit<UploadItem, 'retryCount' | 'nextRetryAt'>): Promise<void> {
  const uploadItem: UploadItem = {
    ...item,
    retryCount: 0,
    nextRetryAt: 0,
  };

  queue.push(uploadItem);
  await persistQueue();
  notifyListeners();
  logEvent('photo_upload_enqueued', { capture_id: item.captureId });

  // Kick the processor
  processQueue();
}

async function persistQueue(): Promise<void> {
  try {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  } catch { /* best effort */ }
}

async function persistPendingOcr(): Promise<void> {
  try {
    await AsyncStorage.setItem(PENDING_OCR_KEY, JSON.stringify([...pendingOcrIds]));
  } catch { /* best effort */ }
}

function processQueue() {
  while (activeUploads < MAX_CONCURRENT) {
    const now = Date.now();
    const idx = queue.findIndex(item => item.nextRetryAt <= now);
    if (idx === -1) break;

    const item = queue[idx];
    activeUploads++;
    notifyListeners();

    uploadOne(item).finally(() => {
      activeUploads--;
      notifyListeners();
      // Keep processing
      processQueue();
    });
  }

  // If there are items with future retry times, schedule a wake-up
  const nextRetry = queue
    .filter(item => item.nextRetryAt > Date.now())
    .reduce((min, item) => Math.min(min, item.nextRetryAt), Infinity);

  if (nextRetry < Infinity) {
    const delay = Math.max(nextRetry - Date.now(), 500);
    setTimeout(() => processQueue(), delay);
  }
}

async function uploadOne(item: UploadItem): Promise<void> {
  try {
    const formData = new FormData();

    // Append the image
    if (Platform.OS === 'web') {
      const resp = await fetch(item.photoUri);
      const blob = await resp.blob();
      formData.append('photo', blob, 'photo.jpg');
    } else {
      const ext = item.photoUri.split('.').pop()?.toLowerCase() || 'jpg';
      const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg';
      formData.append('photo', {
        uri: item.photoUri,
        type: mimeType,
        name: `photo.${ext}`,
      } as any);
    }

    formData.append('capture_id', item.captureId);
    formData.append('book_id', item.bookId);
    formData.append('book_title', item.bookTitle);
    if (item.pageNumber !== undefined) formData.append('page_number', String(item.pageNumber));
    if (item.chapter) formData.append('chapter', item.chapter);

    const resp = await fetch(`${RESEARCH_BASE}/book/upload-photo`, {
      method: 'POST',
      body: formData,
    });

    if (!resp.ok) {
      throw new Error(`Upload failed (${resp.status})`);
    }

    // Upload succeeded — remove from queue, add to pending OCR
    queue = queue.filter(q => q.captureId !== item.captureId);
    await persistQueue();

    await updateBookCapture(item.captureId, { upload_status: 'uploaded', ocr_status: 'processing' });

    pendingOcrIds.add(item.captureId);
    await persistPendingOcr();

    logEvent('photo_upload_success', { capture_id: item.captureId, retries: item.retryCount });
  } catch (e) {
    item.retryCount++;
    if (item.retryCount >= MAX_RETRIES) {
      // Give up
      queue = queue.filter(q => q.captureId !== item.captureId);
      await persistQueue();
      await updateBookCapture(item.captureId, { upload_status: 'failed', ocr_status: 'failed' });
      logEvent('photo_upload_give_up', { capture_id: item.captureId, retries: item.retryCount });
    } else {
      // Exponential backoff: 2s, 4s, 8s, 16s, 32s, 64s, 128s, 256s, 512s
      const delay = BASE_DELAY_MS * Math.pow(2, item.retryCount - 1);
      item.nextRetryAt = Date.now() + delay;
      await persistQueue();
      logEvent('photo_upload_retry_scheduled', {
        capture_id: item.captureId,
        retry: item.retryCount,
        delay_ms: delay,
      });
    }
  }
}

/**
 * Poll the server for completed OCR results.
 * Call this on screen focus or periodically.
 */
export async function pollPhotoResults(): Promise<number> {
  if (pendingOcrIds.size === 0) return 0;

  const captureIds = [...pendingOcrIds];

  try {
    const resp = await fetch(`${RESEARCH_BASE}/book/photo-results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capture_ids: captureIds }),
    });

    if (!resp.ok) return 0;

    const data = await resp.json();
    const results: Record<string, any> = data.results || {};
    let completed = 0;

    for (const [captureId, result] of Object.entries(results)) {
      const r = result as any;
      if (r.status === 'completed') {
        await updateBookCapture(captureId, {
          ocr_text: r.text,
          extracted_ideas: r.extracted_ideas,
          topics: r.topics,
          ocr_status: 'completed',
          page_number: r.detected_page_number || undefined,
        });
        completed++;
      } else if (r.status === 'failed') {
        await updateBookCapture(captureId, { ocr_status: 'failed' });
      }
      pendingOcrIds.delete(captureId);
    }

    // Also remove any IDs the server doesn't know about (stale)
    const pendingOnServer = new Set(data.pending || []);
    for (const cid of captureIds) {
      if (!(cid in results) && !pendingOnServer.has(cid)) {
        // Server doesn't know about it — maybe it was processed before a restart
        // Check if capture already has OCR text (from a prior session)
        pendingOcrIds.delete(cid);
      }
    }

    await persistPendingOcr();
    if (completed > 0) {
      logEvent('photo_ocr_results_received', { count: completed });
    }
    return completed;
  } catch {
    return 0;
  }
}
