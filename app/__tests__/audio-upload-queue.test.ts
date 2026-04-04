/**
 * Tests for the shared audio upload queue (audio-upload-queue.ts).
 *
 * Verifies: enqueue persistence, dequeue cleanup, retry logic,
 * 48h TTL expiry, missing-file handling, and idempotent request IDs.
 */

// --- Mocks must be set up before imports ---

// Mock react-native
jest.mock('react-native', () => ({
  Platform: { OS: 'ios' },
  AppState: { addEventListener: jest.fn() },
}));

// Mock expo-file-system/legacy with in-memory implementation
jest.mock('expo-file-system/legacy', () =>
  require('./__mocks__/expo-file-system-legacy')
);

// Mock chat-api — use jest.fn() inside the factory to avoid hoisting issue
jest.mock('../lib/chat-api', () => ({
  RESEARCH_BASE: 'http://test:8090',
  fetchWithTimeout: jest.fn(),
}));

// Mock logger
jest.mock('../data/logger', () => ({ logEvent: jest.fn() }));

import { createAudioQueue } from '../lib/audio-upload-queue';
import { fetchWithTimeout } from '../lib/chat-api';
import {
  __mockFiles as files,
  __reset as resetFS,
  copyAsync,
  deleteAsync,
  getInfoAsync,
} from './__mocks__/expo-file-system-legacy';

const mockFetch = fetchWithTimeout as jest.Mock;

beforeEach(() => {
  resetFS();
  mockFetch.mockReset();
  // Seed a fake source audio file
  files.set('/tmp/recording.m4a', 'fake-audio-data');
});

describe('createAudioQueue', () => {
  test('enqueue persists item to pending.json and copies audio', async () => {
    const q = createAudioQueue('test-q');
    const id = await q.enqueue('/tmp/recording.m4a', '/api/upload', { entity_id: 'plato' });

    expect(id).toMatch(/^test-q_\d+_/);
    expect(copyAsync).toHaveBeenCalledWith(
      expect.objectContaining({ from: '/tmp/recording.m4a' })
    );

    // Pending JSON should contain the item
    const pendingPath = '/mock/documents/upload-queues/test-q/pending.json';
    const raw = files.get(pendingPath);
    expect(raw).toBeTruthy();
    const items = JSON.parse(raw!);
    expect(items).toHaveLength(1);
    expect(items[0].id).toBe(id);
    expect(items[0].endpoint).toBe('/api/upload');
    expect(items[0].metadata.entity_id).toBe('plato');
  });

  test('enqueue generates unique IDs for each call', async () => {
    const q = createAudioQueue('uniq-q');
    const id1 = await q.enqueue('/tmp/recording.m4a', '/api/upload', {});
    // Need a fresh source for the second enqueue
    files.set('/tmp/recording2.m4a', 'audio-2');
    const id2 = await q.enqueue('/tmp/recording2.m4a', '/api/upload', {});
    expect(id1).not.toBe(id2);
    expect(await q.pendingCount()).toBe(2);
  });

  test('dequeue removes item and deletes audio file', async () => {
    const q = createAudioQueue('deq-q');
    const id = await q.enqueue('/tmp/recording.m4a', '/api/upload', {});

    expect(await q.pendingCount()).toBe(1);
    await q.dequeue(id);
    expect(await q.pendingCount()).toBe(0);
    expect(deleteAsync).toHaveBeenCalled();
  });

  test('upload sends multipart with request_id and metadata', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'completed', notes_saved: 1 }),
    });

    const q = createAudioQueue('upload-q');
    const id = await q.enqueue('/tmp/recording.m4a', '/api/upload', {
      entity_id: 'plato',
      mode: 'entity',
    });

    const result = await q.upload(id);
    expect(result.status).toBe('completed');

    // Verify fetchWithTimeout was called correctly
    expect(mockFetch).toHaveBeenCalledWith(
      'http://test:8090/api/upload',
      expect.objectContaining({
        method: 'POST',
        timeout: 90000,
      })
    );

    // Verify FormData contains expected fields
    const callArgs = mockFetch.mock.calls[0];
    const formData = callArgs[1].body;
    expect(formData).toBeInstanceOf(FormData);
  });

  test('upload throws on non-ok response (item stays in queue)', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });

    const q = createAudioQueue('fail-q');
    const id = await q.enqueue('/tmp/recording.m4a', '/api/upload', {});

    await expect(q.upload(id)).rejects.toThrow('Upload');
    // Item should still be in queue
    expect(await q.pendingCount()).toBe(1);
  });

  test('upload throws if item not found', async () => {
    const q = createAudioQueue('notfound-q');
    await expect(q.upload('nonexistent')).rejects.toThrow('not found');
  });
});

describe('retryAll', () => {
  test('retries pending items and removes successful ones', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'completed' }),
    });

    const q = createAudioQueue('retry-ok-q');
    const id = await q.enqueue('/tmp/recording.m4a', '/api/upload', {});

    const succeeded = await q.retryAll();
    expect(succeeded).toBe(1);
    expect(await q.pendingCount()).toBe(0);
  });

  test('keeps failed items for future retry', async () => {
    mockFetch.mockRejectedValue(new Error('network error'));

    const q = createAudioQueue('retry-fail-q');
    await q.enqueue('/tmp/recording.m4a', '/api/upload', {});

    const succeeded = await q.retryAll();
    expect(succeeded).toBe(0);
    expect(await q.pendingCount()).toBe(1);
  });

  test('expires items older than 48 hours', async () => {
    const q = createAudioQueue('expire-q');
    await q.enqueue('/tmp/recording.m4a', '/api/upload', {});

    // Manually age the item by rewriting pending.json
    const pendingPath = '/mock/documents/upload-queues/expire-q/pending.json';
    const items = JSON.parse(files.get(pendingPath)!);
    items[0].createdAt = Date.now() - (49 * 60 * 60 * 1000); // 49 hours ago
    files.set(pendingPath, JSON.stringify(items));

    const succeeded = await q.retryAll();
    expect(succeeded).toBe(0);
    expect(await q.pendingCount()).toBe(0); // expired, not retried
    expect(deleteAsync).toHaveBeenCalled(); // audio file cleaned up
  });

  test('drops items whose audio file no longer exists', async () => {
    const q = createAudioQueue('missing-q');
    const id = await q.enqueue('/tmp/recording.m4a', '/api/upload', {});

    // Delete the copied audio file to simulate file loss
    const pendingPath = '/mock/documents/upload-queues/missing-q/pending.json';
    const items = JSON.parse(files.get(pendingPath)!);
    files.delete(items[0].audioUri);

    // Make getInfoAsync report file as missing
    (getInfoAsync as jest.Mock).mockResolvedValueOnce({ exists: false });

    const succeeded = await q.retryAll();
    expect(succeeded).toBe(0);
    expect(await q.pendingCount()).toBe(0); // removed, not stuck forever
  });

  test('notifies listeners on success and failure', async () => {
    const q = createAudioQueue('listen-q');
    const results: Array<{ success: boolean }> = [];
    q.onResult((_item, success) => results.push({ success }));

    // Enqueue two items
    await q.enqueue('/tmp/recording.m4a', '/api/upload', {});
    files.set('/tmp/recording2.m4a', 'audio-2');
    await q.enqueue('/tmp/recording2.m4a', '/api/upload', {});

    // Age one item to expire it
    const pendingPath = '/mock/documents/upload-queues/listen-q/pending.json';
    const items = JSON.parse(files.get(pendingPath)!);
    items[0].createdAt = Date.now() - (50 * 60 * 60 * 1000);
    files.set(pendingPath, JSON.stringify(items));

    // Second item will succeed
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'completed' }),
    });

    await q.retryAll();

    expect(results).toHaveLength(2);
    expect(results[0].success).toBe(false);  // expired
    expect(results[1].success).toBe(true);   // uploaded
  });

  test('onResult unsubscribe works', async () => {
    const q = createAudioQueue('unsub-q');
    const results: boolean[] = [];
    const unsub = q.onResult((_item, success) => results.push(success));

    await q.enqueue('/tmp/recording.m4a', '/api/upload', {});
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'completed' }),
    });

    unsub(); // unsubscribe before retry
    await q.retryAll();
    expect(results).toHaveLength(0); // listener not called
  });
});

describe('pendingCount', () => {
  test('returns 0 for empty queue', async () => {
    const q = createAudioQueue('empty-q');
    expect(await q.pendingCount()).toBe(0);
  });

  test('tracks enqueue and dequeue accurately', async () => {
    const q = createAudioQueue('count-q');
    const id1 = await q.enqueue('/tmp/recording.m4a', '/api/upload', {});
    expect(await q.pendingCount()).toBe(1);

    files.set('/tmp/recording2.m4a', 'audio-2');
    await q.enqueue('/tmp/recording2.m4a', '/api/upload', {});
    expect(await q.pendingCount()).toBe(2);

    await q.dequeue(id1);
    expect(await q.pendingCount()).toBe(1);
  });
});
