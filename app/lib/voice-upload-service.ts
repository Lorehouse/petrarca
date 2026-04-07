/**
 * Background service for retrying failed voice elicitation uploads.
 *
 * Call `startVoiceUploadService()` once at app startup. It listens for
 * AppState "active" transitions and retries any pending uploads that were
 * saved to disk but never confirmed by the server.
 */

import { AppState, AppStateStatus, Platform } from 'react-native';
import {
  documentDirectory, readAsStringAsync, writeAsStringAsync, makeDirectoryAsync,
} from 'expo-file-system/legacy';
import { sendVoiceElicitation, checkVoiceElicitCache, ElicitationResult } from './review-api';
import { RESEARCH_BASE } from './chat-api';
import { logEvent } from '../data/logger';

const PENDING_DIR = `${documentDirectory}voice-elicitation/`;
const PENDING_META = `${documentDirectory}voice-elicitation/pending.json`;

interface PendingUpload {
  audioUri: string;
  nodeId: string;
  domainId: string;
  nodeTitle: string;
  recordedAt: number;
  requestId: string;
  lastRetryAt?: number;
  /** Set when server returns 422 — keeps audio but skips auto-retry */
  failedAt?: number;
  failReason?: string;
}

type UploadResultListener = (nodeTitle: string, success: boolean, result?: ElicitationResult) => void;
const listeners: Set<UploadResultListener> = new Set();

export function onVoiceUploadResult(fn: UploadResultListener): () => void {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

function notifyListeners(nodeTitle: string, success: boolean, result?: ElicitationResult) {
  for (const fn of listeners) {
    try { fn(nodeTitle, success, result); } catch { /* ignore */ }
  }
}

let serviceStarted = false;
let retrying = false;

export function startVoiceUploadService() {
  if (serviceStarted || Platform.OS === 'web') return;
  serviceStarted = true;

  // Retry on app foreground
  AppState.addEventListener('change', (state: AppStateStatus) => {
    if (state === 'active') {
      retryPendingUploads();
    }
  });

  // Also retry once at startup
  retryPendingUploads();
}

async function loadPending(): Promise<PendingUpload[]> {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

async function savePending(items: PendingUpload[]) {
  await makeDirectoryAsync(PENDING_DIR, { intermediates: true }).catch(() => {});
  await writeAsStringAsync(PENDING_META, JSON.stringify(items));
}

/** Remove a single entry by audioUri — reads fresh state to avoid race with savePendingUpload */
async function clearEntry(audioUri: string) {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    const pending: PendingUpload[] = JSON.parse(raw);
    const filtered = pending.filter(p => p.audioUri !== audioUri);
    await writeAsStringAsync(PENDING_META, JSON.stringify(filtered));
  } catch { /* ignore */ }
}

/** Update lastRetryAt on a single entry without rewriting the whole array from stale state */
async function updateLastRetry(audioUri: string, ts: number) {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    const pending: PendingUpload[] = JSON.parse(raw);
    const entry = pending.find(p => p.audioUri === audioUri);
    if (entry) {
      entry.lastRetryAt = ts;
      await writeAsStringAsync(PENDING_META, JSON.stringify(pending));
    }
  } catch { /* ignore */ }
}

/** Mark an entry as validation-failed — keeps audio, skips auto-retry */
async function markFailed(audioUri: string, reason: string) {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    const pending: PendingUpload[] = JSON.parse(raw);
    const entry = pending.find(p => p.audioUri === audioUri);
    if (entry) {
      entry.failedAt = Date.now();
      entry.failReason = reason;
      await writeAsStringAsync(PENDING_META, JSON.stringify(pending));
    }
  } catch { /* ignore */ }
}

/** Get failed uploads for UI display */
export async function getFailedUploads(): Promise<PendingUpload[]> {
  const pending = await loadPending();
  return pending.filter(p => p.failedAt);
}

/** Retry a specific failed upload — clears the failed flag so auto-retry picks it up */
export async function retryFailedUpload(audioUri: string) {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    const pending: PendingUpload[] = JSON.parse(raw);
    const entry = pending.find(p => p.audioUri === audioUri);
    if (entry) {
      delete entry.failedAt;
      delete entry.failReason;
      entry.lastRetryAt = undefined;
      await writeAsStringAsync(PENDING_META, JSON.stringify(pending));
    }
  } catch { /* ignore */ }
  // Trigger immediate retry
  retryPendingUploads();
}

/** Retry all failed uploads */
export async function retryAllFailed() {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    const pending: PendingUpload[] = JSON.parse(raw);
    for (const p of pending) {
      if (p.failedAt) {
        delete p.failedAt;
        delete p.failReason;
        p.lastRetryAt = undefined;
      }
    }
    await writeAsStringAsync(PENDING_META, JSON.stringify(pending));
  } catch { /* ignore */ }
  retryPendingUploads();
}

async function isServerReachable(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(`${RESEARCH_BASE}/health`, { signal: controller.signal });
    clearTimeout(timer);
    return res.ok;
  } catch {
    return false;
  }
}

async function retryPendingUploads() {
  if (retrying) return;
  retrying = true;

  try {
    const pending = await loadPending();
    if (pending.length === 0) return;

    // Skip retry if server unreachable — saves 90s timeout per item
    if (!(await isServerReachable())) {
      console.log('[voice-upload-service] Server unreachable, skipping retry');
      return;
    }

    // Backfill requestId for old entries
    for (const p of pending) {
      if (!p.requestId) p.requestId = `elicit_${p.recordedAt}_${p.nodeId.slice(0, 40)}`;
    }

    console.log(`[voice-upload-service] Retrying ${pending.length} pending upload(s)`);
    let cleared = 0;

    for (const p of pending) {
      // Skip validation-failed entries — kept for manual retry only
      if (p.failedAt) continue;

      // Skip items retried very recently (another retry loop may be handling them)
      if (p.lastRetryAt && (Date.now() - p.lastRetryAt) < 30_000) {
        continue;
      }

      try {
        // Check cache first — avoids re-uploading 3MB+ audio on flaky connections
        if (p.requestId) {
          const cached = await checkVoiceElicitCache(p.requestId);
          if (cached && !cached.error && (cached.captured?.length || cached.missed?.length || cached.feedback_summary)) {
            console.log(`[voice-upload-service] Cache hit for ${p.nodeTitle}, no re-upload needed`);
            logEvent('voice_upload_auto_retry_success', {
              node_id: p.nodeId, request_id: p.requestId, from_cache: true,
            });
            notifyListeners(p.nodeTitle, true, cached);
            await clearEntry(p.audioUri);
            cleared++;
            continue;
          }
        }

        p.lastRetryAt = Date.now();
        await updateLastRetry(p.audioUri, p.lastRetryAt);
        const res = await sendVoiceElicitation(p.nodeId, p.domainId, p.audioUri, p.requestId);
        // 422 responses come back as data with error field — mark as failed, keep audio
        if (res?.error) {
          console.log(`[voice-upload-service] Validation error for ${p.nodeTitle}: ${res.error}`);
          await markFailed(p.audioUri, res.error);
          continue;
        }
        if (res && (res.captured?.length || res.missed?.length || res.feedback_summary)) {
          logEvent('voice_upload_auto_retry_success', {
            node_id: p.nodeId, request_id: p.requestId,
          });
          notifyListeners(p.nodeTitle, true, res);
          await clearEntry(p.audioUri);
          cleared++;
        }
      } catch (e: any) {
        console.log(`[voice-upload-service] Retry failed for ${p.nodeTitle}: ${e}`);
        // Don't retry permanent client errors (400, 404)
        const status = e?.status;
        if (status && status >= 400 && status < 500) {
          logEvent('voice_upload_permanent_fail', { node_id: p.nodeId, status });
          await markFailed(p.audioUri, `HTTP ${status}`);
          continue;
        }
        // Expire entries older than 48h
        const ageHours = (Date.now() - p.recordedAt) / (1000 * 3600);
        if (ageHours >= 48) {
          logEvent('voice_upload_expired', { node_id: p.nodeId, age_hours: Math.round(ageHours) });
          notifyListeners(p.nodeTitle, false);
          await clearEntry(p.audioUri);
          cleared++;
        }
      }
    }

    if (cleared > 0) {
      console.log(`[voice-upload-service] ${cleared} upload(s) resolved, ${pending.length - cleared} remaining`);
    }
  } catch (e) {
    console.error('[voice-upload-service] Error:', e);
  } finally {
    retrying = false;
  }
}
