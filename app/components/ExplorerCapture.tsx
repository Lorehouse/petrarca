import { useState, useRef, useCallback } from 'react';
import { View, Text, Pressable, TextInput, StyleSheet, Platform, ActivityIndicator } from 'react-native';
import { colors, fonts, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { RESEARCH_BASE } from '../lib/chat-api';

// Conditional expo-av import (not available on web)
let Audio: any = null;
let Haptics: any = null;
let FileSystem: any = null;
if (Platform.OS !== 'web') {
  try { Audio = require('expo-av').Audio; } catch {}
  try { Haptics = require('expo-haptics'); } catch {}
  try { FileSystem = require('expo-file-system/legacy'); } catch {}
}

export interface CaptureResult {
  status: 'completed' | 'error';
  transcript?: string;
  notes_saved: number;
  research_triggered: { card_id: string; query: string }[];
  entities_detected: string[];
  error?: string;
}

interface ExplorerCaptureProps {
  entityId?: string;
  entityName?: string;
  mode: 'entity' | 'general';
  placeholder?: string;
  onCaptureComplete?: (result: CaptureResult) => void;
}

type CaptureState = 'idle' | 'recording' | 'processing' | 'done';

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
    if (timerRef.current) clearInterval(timerRef.current);
    try {
      await recRef.current.stopAndUnloadAsync();
      const uri = recRef.current.getURI();
      recRef.current = null;
      setState('processing');
      setProcessingLabel('Transcribing…');
      if (Haptics) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

      if (!uri) { setState('idle'); setError('No audio file'); return; }

      // Save locally for resilience
      let localPath = uri;
      if (FileSystem && FileSystem.documentDirectory) {
        const filename = `explore_capture_${Date.now()}.m4a`;
        const dir = `${FileSystem.documentDirectory}explore-captures/`;
        await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
        localPath = `${dir}${filename}`;
        await FileSystem.copyAsync({ from: uri, to: localPath });
      }

      logEvent('explorer_capture_record_stop', { entity_id: entityId, duration, mode });

      // Upload as multipart
      await uploadAudio(localPath);
    } catch (e) {
      setState('idle');
      setError(`Recording error: ${e}`);
    }
  }, [entityId, entityName, duration, mode]);

  const uploadAudio = async (audioPath: string) => {
    setProcessingLabel('Transcribing…');
    try {
      const formData = new FormData();
      formData.append('audio', {
        uri: audioPath,
        type: 'audio/m4a',
        name: 'capture.m4a',
      } as any);
      if (entityId) formData.append('entity_id', entityId);
      if (entityName) formData.append('entity_name', entityName);
      formData.append('mode', mode);

      const resp = await fetch(`${RESEARCH_BASE}/explore/capture`, {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();
      handleResult(data);
    } catch (e) {
      setState('idle');
      setError(`Upload failed: ${e}`);
    }
  };

  const sendText = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setState('processing');
    setProcessingLabel('Analyzing…');
    setError('');
    logEvent('explorer_capture_text', { entity_id: entityId, mode, length: trimmed.length });

    try {
      const resp = await fetch(`${RESEARCH_BASE}/explore/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: trimmed,
          entity_id: entityId,
          entity_name: entityName,
          mode,
        }),
      });
      const data = await resp.json();
      handleResult(data);
      setText('');
    } catch (e) {
      setState('idle');
      setError(`Failed: ${e}`);
    }
  }, [text, entityId, entityName, mode]);

  const handleResult = (data: any) => {
    if (data.status === 'error') {
      setState('idle');
      setError(data.error || 'Unknown error');
      return;
    }
    setProcessingLabel('');
    const captureResult: CaptureResult = {
      status: 'completed',
      transcript: data.transcript,
      notes_saved: data.notes_saved || 0,
      research_triggered: data.research_triggered || [],
      entities_detected: data.entities_detected || [],
    };
    setResult(captureResult);
    setState('done');
    onCaptureComplete?.(captureResult);
    // Reset after showing result
    setTimeout(() => {
      setState('idle');
      setResult(null);
    }, 3000);
  };

  const fmt = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

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
        <Pressable onPress={() => {
          if (recRef.current) {
            recRef.current.stopAndUnloadAsync().catch(() => {});
            recRef.current = null;
          }
          if (timerRef.current) clearInterval(timerRef.current);
          setState('idle');
        }} style={cs.cancelBtn}>
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
  errorText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
    position: 'absolute',
    bottom: -14,
    left: 0,
  },
});
