import { useState, useRef, useCallback, useEffect } from 'react';
import { View, Text, Pressable, TextInput, StyleSheet, Platform, ActivityIndicator } from 'react-native';
import { colors, fonts } from '../design/tokens';
import { logEvent } from '../data/logger';
import { RESEARCH_BASE, fetchWithTimeout } from '../lib/chat-api';
import { createAudioQueue } from '../lib/audio-upload-queue';

// Conditional native imports (not available on web)
let Audio: any = null;
let Haptics: any = null;
if (Platform.OS !== 'web') {
  try { Audio = require('expo-av').Audio; } catch {}
  try { Haptics = require('expo-haptics'); } catch {}
}

// Shared queue — all ExplorerCapture instances share one queue.
// Also registered in _layout.tsx for AppState-based retry.
export const exploreCaptureQueue = createAudioQueue('explore-captures');

export interface CaptureResult {
  status: 'completed' | 'error';
  transcript?: string;
  notes_saved: number;
  research_triggered: { card_id: string; query: string }[];
  entities_detected: string[];
  error?: string;
}

// --- Component ---

interface ExplorerCaptureProps {
  entityId?: string;
  entityName?: string;
  mode: 'entity' | 'general';
  placeholder?: string;
  onCaptureComplete?: (result: CaptureResult) => void;
}

type CaptureState = 'idle' | 'recording' | 'processing' | 'done' | 'saved_pending';

export default function ExplorerCapture({
  entityId, entityName, mode, placeholder, onCaptureComplete,
}: ExplorerCaptureProps) {
  const [state, setState] = useState<CaptureState>('idle');
  const [text, setText] = useState('');
  const [duration, setDuration] = useState(0);
  const [processingLabel, setProcessingLabel] = useState('');
  const [result, setResult] = useState<CaptureResult | null>(null);
  const [error, setError] = useState('');
  const recRef = useRef<any>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const defaultPlaceholder = mode === 'entity'
    ? `What do I know about ${entityName || 'this'}…`
    : 'Capture a note or question…';

  // Retry any pending uploads on mount; notify parent if background retries succeed
  useEffect(() => {
    const unsub = exploreCaptureQueue.onResult((_item, success, response) => {
      if (success && response) onCaptureComplete?.(response as CaptureResult);
    });
    exploreCaptureQueue.retryAll().catch(() => {});
    return unsub;
  }, []);

  const startRecording = useCallback(async () => {
    if (!Audio) { setError('Recording not available on web'); return; }
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) { setError('Mic permission needed'); return; }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      recRef.current = rec;
      setState('recording');
      setDuration(0);
      setError('');
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000);
      if (Haptics) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      logEvent('explorer_capture_record_start', { entity_id: entityId, mode });
    } catch (e) {
      setError(`Recording failed: ${e}`);
    }
  }, [entityId, mode]);

  const stopAndSend = useCallback(async () => {
    if (!recRef.current) return;
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    try {
      await recRef.current.stopAndUnloadAsync();
      const tempUri = recRef.current.getURI();
      recRef.current = null;

      if (!tempUri) { setState('idle'); setError('No audio file'); return; }
      if (Haptics) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

      logEvent('explorer_capture_record_stop', { entity_id: entityId, duration, mode });

      // Enqueue: copies audio to persistent dir, saves to pending.json
      const metadata: Record<string, string> = { mode };
      if (entityId) metadata.entity_id = entityId;
      if (entityName) metadata.entity_name = entityName;
      const requestId = await exploreCaptureQueue.enqueue(tempUri, '/explore/capture', metadata);

      // Attempt upload (blocking — user sees "Transcribing…")
      setState('processing');
      setProcessingLabel('Transcribing…');

      try {
        const data = await exploreCaptureQueue.upload(requestId);
        await exploreCaptureQueue.dequeue(requestId);
        handleResult(data);
      } catch (e) {
        // Upload failed — audio is safely queued for automatic retry
        console.warn('[ExplorerCapture] upload failed, queued for retry:', e);
        logEvent('explorer_capture_upload_failed', { request_id: requestId, error: String(e) });
        setState('saved_pending');
        setTimeout(() => setState('idle'), 2500);
      }
    } catch (e) {
      console.error('[ExplorerCapture] recording save failed:', e);
      setState('idle');
      setError(`Recording error: ${e}`);
    }
  }, [entityId, entityName, duration, mode]);

  const sendText = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setState('processing');
    setProcessingLabel('Analyzing…');
    setError('');
    logEvent('explorer_capture_text', { entity_id: entityId, mode, length: trimmed.length });

    try {
      const resp = await fetchWithTimeout(`${RESEARCH_BASE}/explore/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed, entity_id: entityId, entity_name: entityName, mode }),
        timeout: 30000,
      });
      if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
      const data = await resp.json();
      handleResult(data);
      setText('');
    } catch (e) {
      setState('idle');
      setError(`Failed: ${e}`);
    }
  }, [text, entityId, entityName, mode]);

  const handleResult = (data: CaptureResult) => {
    if (data.status === 'error') {
      setState('idle');
      setError(data.error || 'Unknown error');
      return;
    }
    setProcessingLabel('');
    setResult(data);
    setState('done');
    onCaptureComplete?.(data);
    setTimeout(() => { setState('idle'); setResult(null); }, 3000);
  };

  const cancelRecording = useCallback(() => {
    if (recRef.current) {
      recRef.current.stopAndUnloadAsync().catch(() => {});
      recRef.current = null;
    }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setDuration(0);
    setState('idle');
    logEvent('explorer_capture_cancelled', { entity_id: entityId, duration });
  }, [entityId, duration]);

  const fmt = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  // --- Saved pending (upload failed, will retry) ---
  if (state === 'saved_pending') {
    return (
      <View style={cs.doneRow}>
        <Text style={cs.pendingText}>Saved — will retry upload ⟳</Text>
      </View>
    );
  }

  // --- Done state ---
  if (state === 'done' && result) {
    const parts: string[] = [];
    if (result.notes_saved > 0) parts.push(`${result.notes_saved} note${result.notes_saved > 1 ? 's' : ''} saved`);
    if (result.research_triggered.length > 0) parts.push(`${result.research_triggered.length} research queued`);
    if (result.entities_detected.length > 0 && mode === 'general') {
      parts.push(`→ ${result.entities_detected.join(', ')}`);
    }
    return (
      <View style={cs.doneRow}>
        <Text style={cs.doneText}>{parts.join(' · ') || 'Captured'} ✓</Text>
      </View>
    );
  }

  // --- Processing state ---
  if (state === 'processing') {
    return (
      <View style={cs.processingRow}>
        <ActivityIndicator size="small" color={colors.rubric} />
        <Text style={cs.processingText}>{processingLabel}</Text>
      </View>
    );
  }

  // --- Recording state ---
  if (state === 'recording') {
    return (
      <View style={cs.recordingRow}>
        <View style={cs.pulseDot} />
        <Text style={cs.timer}>{fmt(duration)}</Text>
        <View style={{ flex: 1 }} />
        <Pressable onPress={stopAndSend} style={cs.sendBtn}>
          <Text style={cs.sendBtnText}>Send</Text>
        </Pressable>
        <Pressable onPress={cancelRecording} style={cs.cancelBtn}>
          <Text style={cs.cancelText}>✕</Text>
        </Pressable>
      </View>
    );
  }

  // --- Idle state ---
  return (
    <View style={cs.idleRow}>
      <TextInput
        style={cs.textInput}
        placeholder={placeholder || defaultPlaceholder}
        placeholderTextColor={colors.textMuted}
        value={text}
        onChangeText={setText}
        multiline
        maxLength={1000}
        onSubmitEditing={sendText}
      />
      {text.trim().length > 0 ? (
        <Pressable onPress={sendText} style={cs.sendBtn}>
          <Text style={cs.sendBtnText}>Send</Text>
        </Pressable>
      ) : Audio ? (
        <Pressable onPress={startRecording} style={cs.micBtn}>
          <View style={cs.micDot} />
        </Pressable>
      ) : null}
      {error ? <Text style={cs.errorText}>{error}</Text> : null}
    </View>
  );
}

const cs = StyleSheet.create({
  idleRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
  },
  textInput: {
    flex: 1,
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textBody,
    borderWidth: 1,
    borderColor: colors.rule,
    borderRadius: 2,
    paddingHorizontal: 8,
    paddingVertical: 6,
    minHeight: 36,
    maxHeight: 80,
  },
  micBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.ink,
    justifyContent: 'center',
    alignItems: 'center',
  },
  micDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.rubric,
  },
  recordingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 4,
  },
  pulseDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.rubric,
  },
  timer: {
    fontFamily: fonts.display,
    fontSize: 20,
    color: colors.ink,
  },
  sendBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: colors.rubric,
    borderRadius: 2,
  },
  sendBtnText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.parchment,
  },
  cancelBtn: {
    padding: 6,
    minWidth: 36,
    minHeight: 36,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelText: {
    fontSize: 16,
    color: colors.textMuted,
  },
  processingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  processingText: {
    fontFamily: fonts.readingItalic,
    fontSize: 13,
    color: colors.textMuted,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  doneRow: {
    paddingVertical: 8,
  },
  doneText: {
    fontFamily: fonts.readingItalic,
    fontSize: 13,
    color: colors.claimNew,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  pendingText: {
    fontFamily: fonts.readingItalic,
    fontSize: 13,
    color: colors.textMuted,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  errorText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
    position: 'absolute',
    bottom: -14,
    left: 0,
  },
});
