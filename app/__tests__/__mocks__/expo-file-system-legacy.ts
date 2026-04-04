/**
 * In-memory mock for expo-file-system/legacy.
 * Supports the operations used by audio-upload-queue.ts.
 */

const files = new Map<string, string>();

export const documentDirectory = '/mock/documents/';

export const makeDirectoryAsync = jest.fn(async () => {});

export const readAsStringAsync = jest.fn(async (path: string) => {
  const content = files.get(path);
  if (content === undefined) throw new Error(`File not found: ${path}`);
  return content;
});

export const writeAsStringAsync = jest.fn(async (path: string, content: string) => {
  files.set(path, content);
});

export const copyAsync = jest.fn(async ({ from, to }: { from: string; to: string }) => {
  const content = files.get(from) ?? `audio-data-from-${from}`;
  files.set(to, content);
});

export const deleteAsync = jest.fn(async (path: string) => {
  files.delete(path);
});

export const getInfoAsync = jest.fn(async (path: string) => {
  return { exists: files.has(path), isDirectory: false, uri: path, size: 1024 };
});

// Test helpers — not part of the real API
export const __mockFiles = files;
export const __reset = () => {
  files.clear();
  jest.clearAllMocks();
};
