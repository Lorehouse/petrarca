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
    const remaining: PendingUpload[] = [];

    for (const p of pending) {
      // Skip items retried very recently (another retry loop may be handling them)
      if (p.lastRetryAt && (Date.now() - p.lastRetryAt) < 30_000) {
        remaining.push(p);
        continue;
      }

      try {
        // Check cache first — avoids re-uploading 3MB+ audio on flaky connections
        if (p.requestId) {
          const cached = await checkVoiceElicitCache(p.requestId);
          if (cached && (cached.captured?.length || cached.missed?.length || cached.feedback_summary)) {
            console.log(`[voice-upload-service] Cache hit for ${p.nodeTitle}, no re-upload needed`);
            logEvent('voice_upload_auto_retry_success', {
              node_id: p.nodeId, request_id: p.requestId, from_cache: true,
            });
            notifyListeners(p.nodeTitle, true, cached);
            continue;
          }
        }

        p.lastRetryAt = Date.now();
        const res = await sendVoiceElicitation(p.nodeId, p.domainId, p.audioUri, p.requestId);
        if (res && (res.captured?.length || res.missed?.length || res.feedback_summary)) {
          logEvent('voice_upload_auto_retry_success', {
            node_id: p.nodeId, request_id: p.requestId,
          });
          notifyListeners(p.nodeTitle, true, res);
        } else {
          remaining.push(p);
        }
      } catch (e: any) {
        console.log(`[voice-upload-service] Retry failed for ${p.nodeTitle}: ${e}`);
        // Don't retry permanent client errors (400, 404, 422)
        const status = e?.status;
        if (status && status >= 400 && status < 500) {
          logEvent('voice_upload_permanent_fail', { node_id: p.nodeId, status });
          notifyListeners(p.nodeTitle, false);
          continue;
        }
        // Keep entries less than 48h old for future retry
        const ageHours = (Date.now() - p.recordedAt) / (1000 * 3600);
        if (ageHours < 48) {
          remaining.push(p);
        } else {
          logEvent('voice_upload_expired', { node_id: p.nodeId, age_hours: Math.round(ageHours) });
          notifyListeners(p.nodeTitle, false);
        }
      }
    }

    await savePending(remaining);
    if (remaining.length < pending.length) {
      console.log(`[voice-upload-service] ${pending.length - remaining.length} upload(s) succeeded, ${remaining.length} remaining`);
    }
  } catch (e) {
    console.error('[voice-upload-service] Error:', e);
  } finally {
    retrying = false;
  }
}
