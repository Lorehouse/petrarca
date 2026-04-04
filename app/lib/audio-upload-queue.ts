/**
 * Resilient audio upload queue.
 *
 * Crash-safe, retry-able uploads for any feature that sends audio to the
 * server. Each feature creates a named queue; the queue handles local
 * persistence, idempotent request IDs, 48h TTL expiry, and automatic
 * retry on app foreground.
 *
 * Consolidates the resilience patterns previously duplicated across
 * voice-elicitation, VoiceFeedback, and ExplorerCapture:
 *   - Save audio to persistent dir BEFORE upload
 *   - Track pending items in JSON on disk
 *   - Idempotent request_id for server-side caching
 *   - fetchWithTimeout (90s for transcription-heavy endpoints)
 *   - Retry on mount + app foreground via AppState listener
 *   - 48h TTL — stale items are expired, not retried forever
 *   - Listener pattern for UI updates on background retry success
 *
 * Usage:
 *   import { createAudioQueue, startAudioRetryService } from './audio-upload-queue';
 *
 *   // Per-feature queue (module-level singleton)
 *   export const captureQueue = createAudioQueue('explore-captures');
 *
 *   // In component:
 *   const id = await captureQueue.enqueue(audioUri, '/explore/capture', { entity_id: 'plato' });
 *   try {
 *     const result = await captureQueue.upload(id);
 *     await captureQueue.dequeue(id);      // success — remove from queue
 *   } catch {
 *     // stays in queue for retry
 *   }
 *
 *   // At app startup (_layout.tsx):
 *   startAudioRetryService([captureQueue, elicitQueue, noteQueue]);
 */

import { AppState, AppStateStatus, Platform } from 'react-native';
import { RESEARCH_BASE, fetchWithTimeout } from './chat-api';
import { logEvent } from '../data/logger';

// Conditional file system (not available on web)
let FS: typeof import('expo-file-system/legacy') | null = null;
if (Platform.OS !== 'web') {
  try { FS = require('expo-file-system/legacy'); } catch {}
}

const MAX_AGE_HOURS = 48;
const UPLOAD_TIMEOUT_MS = 90_000;

// --- Types ---

export interface QueuedUpload {
  id: string;                              // request_id — server-side idempotency key
  audioUri: string;                        // local persistent path to .m4a
  endpoint: string;                        // server path, e.g. '/explore/capture'
  metadata: Record<string, string>;        // arbitrary string fields sent alongside audio
  createdAt: number;                       // Date.now() at enqueue time
}

export type UploadResultListener = (
  item: QueuedUpload,
  success: boolean,
  response?: any,
) => void;

export interface AudioQueue {
  readonly name: string;

  /** Persist audio to the queue directory. Returns the generated request ID. */
  enqueue(
    audioUri: string,
    endpoint: string,
    metadata: Record<string, string>,
  ): Promise<string>;

  /** Attempt to upload a queued item. Throws on failure (item stays queued). */
  upload(id: string): Promise<any>;

  /** Remove a successfully uploaded item and clean up its audio file. */
  dequeue(id: string): Promise<void>;

  /** Retry every pending item. Returns number of successes. */
  retryAll(): Promise<number>;

  /** Current number of pending items. */
  pendingCount(): Promise<number>;

  /** Subscribe to background retry results. Returns unsubscribe fn. */
  onResult(fn: UploadResultListener): () => void;
}

// --- File-system helpers ---

function queueDir(name: string): string {
  return FS ? `${FS.documentDirectory}upload-queues/${name}/` : '';
}

function pendingPath(name: string): string {
  return `${queueDir(name)}pending.json`;
}

async function loadItems(name: string): Promise<QueuedUpload[]> {
  if (!FS) return [];
  try {
    const raw = await FS.readAsStringAsync(pendingPath(name));
    return JSON.parse(raw);
  } catch { return []; }
}

async function saveItems(name: string, items: QueuedUpload[]): Promise<void> {
  if (!FS) return;
  const dir = queueDir(name);
  await FS.makeDirectoryAsync(dir, { intermediates: true }).catch(() => {});
  await FS.writeAsStringAsync(pendingPath(name), JSON.stringify(items));
}

/** Generic multipart upload: audio + request_id + all metadata string fields. */
async function uploadToServer(item: QueuedUpload): Promise<any> {
  const form = new FormData();
  form.append('audio', {
    uri: item.audioUri,
    type: 'audio/m4a',
    name: 'audio.m4a',
  } as any);
  form.append('request_id', item.id);
  for (const [key, value] of Object.entries(item.metadata)) {
    if (value != null) form.append(key, value);
  }
  const resp = await fetchWithTimeout(`${RESEARCH_BASE}${item.endpoint}`, {
    method: 'POST',
    body: form,
    timeout: UPLOAD_TIMEOUT_MS,
  });
  if (!resp.ok) throw new Error(`Upload ${item.id} failed: ${resp.status}`);
  return resp.json();
}

// --- Queue factory ---

export function createAudioQueue(name: string): AudioQueue {
  const listeners = new Set<UploadResultListener>();
  let retrying = false;

  function notify(item: QueuedUpload, success: boolean, response?: any) {
    for (const fn of listeners) {
      try { fn(item, success, response); } catch {}
    }
  }

  const queue: AudioQueue = {
    name,

    async enqueue(audioUri, endpoint, metadata) {
      const ts = Date.now();
      const id = `${name}_${ts}_${Math.random().toString(36).slice(2, 6)}`;

      // Copy audio into the queue's own directory so the source can be deleted
      let savedUri = audioUri;
      if (FS) {
        const dir = queueDir(name);
        await FS.makeDirectoryAsync(dir, { intermediates: true }).catch(() => {});
        savedUri = `${dir}${id}.m4a`;
        await FS.copyAsync({ from: audioUri, to: savedUri });
      }

      const item: QueuedUpload = {
        id, audioUri: savedUri, endpoint, metadata, createdAt: ts,
      };
      const items = await loadItems(name);
      items.push(item);
      await saveItems(name, items);

      logEvent('audio_queue_enqueue', { queue: name, id, endpoint });
      return id;
    },

    async upload(id) {
      const items = await loadItems(name);
      const item = items.find(i => i.id === id);
      if (!item) throw new Error(`Item ${id} not found in queue ${name}`);
      return uploadToServer(item);
    },

    async dequeue(id) {
      const items = await loadItems(name);
      const item = items.find(i => i.id === id);
      await saveItems(name, items.filter(i => i.id !== id));
      if (item && FS) {
        FS.deleteAsync(item.audioUri, { idempotent: true }).catch(() => {});
      }
    },

    async retryAll() {
      if (retrying || !FS) return 0;
      retrying = true;
      let succeeded = 0;

      try {
        const items = await loadItems(name);
        if (items.length === 0) return 0;

        console.log(`[audio-queue:${name}] Retrying ${items.length} pending upload(s)`);
        const remaining: QueuedUpload[] = [];

        for (const item of items) {
          const ageHours = (Date.now() - item.createdAt) / (1000 * 3600);

          // Expire stale items
          if (ageHours > MAX_AGE_HOURS) {
            logEvent('audio_queue_expired', {
              queue: name, id: item.id, age_hours: Math.round(ageHours),
            });
            FS!.deleteAsync(item.audioUri, { idempotent: true }).catch(() => {});
            notify(item, false);
            continue;
          }

          // Verify file still exists
          try {
            const info = await FS!.getInfoAsync(item.audioUri);
            if (!info.exists) {
              logEvent('audio_queue_file_missing', { queue: name, id: item.id });
              notify(item, false);
              continue;
            }
          } catch {
            remaining.push(item);
            continue;
          }

          // Attempt upload (server returns cached result if request_id matches)
          try {
            const response = await uploadToServer(item);
            succeeded++;
            logEvent('audio_queue_retry_ok', { queue: name, id: item.id });
            notify(item, true, response);
            FS!.deleteAsync(item.audioUri, { idempotent: true }).catch(() => {});
          } catch (e) {
            logEvent('audio_queue_retry_fail', {
              queue: name, id: item.id, error: String(e),
            });
            remaining.push(item);
          }
        }

        await saveItems(name, remaining);
        if (succeeded > 0 || remaining.length > 0) {
          console.log(
            `[audio-queue:${name}] ${succeeded} ok, ${remaining.length} remaining`,
          );
        }
      } catch (e) {
        console.warn(`[audio-queue:${name}] retryAll error:`, e);
      } finally {
        retrying = false;
      }
      return succeeded;
    },

    async pendingCount() {
      return (await loadItems(name)).length;
    },

    onResult(fn) {
      listeners.add(fn);
      return () => { listeners.delete(fn); };
    },
  };

  return queue;
}

// --- Global retry service ---

let serviceStarted = false;

/**
 * Start a background service that retries all queued audio uploads when
 * the app returns to the foreground. Call once at app startup.
 */
export function startAudioRetryService(queues: AudioQueue[]): void {
  if (serviceStarted || Platform.OS === 'web' || queues.length === 0) return;
  serviceStarted = true;

  const retryAll = () => {
    for (const q of queues) {
      q.retryAll().catch(() => {});
    }
  };

  AppState.addEventListener('change', (state: AppStateStatus) => {
    if (state === 'active') retryAll();
  });

  // Also retry once at service start
  retryAll();
}
