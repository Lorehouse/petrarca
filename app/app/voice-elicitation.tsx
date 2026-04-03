import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Animated, Platform, Pressable,
  ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { Audio } from 'expo-av';
import {
  documentDirectory, makeDirectoryAsync, copyAsync,
  readDirectoryAsync, deleteAsync, readAsStringAsync, writeAsStringAsync,
} from 'expo-file-system/legacy';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { colors, fonts } from '../design/tokens';
import {
  getElicitationCandidates, sendVoiceElicitation,
  ElicitationCandidate, ElicitationResult,
} from '../lib/review-api';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';

type Phase = 'loading' | 'prompt' | 'recording' | 'processing' | 'feedback' | 'retry' | 'pending_retry' | 'done';

interface PendingUpload {
  audioUri: string;
  nodeId: string;
  domainId: string;
  nodeTitle: string;
  recordedAt: number;
}

const PENDING_DIR = `${documentDirectory}voice-elicitation/`;
const PENDING_META = `${documentDirectory}voice-elicitation/pending.json`;

async function savePendingUpload(upload: PendingUpload) {
  await makeDirectoryAsync(PENDING_DIR, { intermediates: true }).catch(() => {});
  let pending: PendingUpload[] = [];
  try {
    const raw = await readAsStringAsync(PENDING_META);
    pending = JSON.parse(raw);
  } catch { /* no file yet */ }
  pending.push(upload);
  await writeAsStringAsync(PENDING_META, JSON.stringify(pending));
}

async function clearPendingUpload(audioUri: string) {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    const pending: PendingUpload[] = JSON.parse(raw);
    const filtered = pending.filter(p => p.audioUri !== audioUri);
    await writeAsStringAsync(PENDING_META, JSON.stringify(filtered));
  } catch { /* ignore */ }
}

async function loadPendingUploads(): Promise<PendingUpload[]> {
  try {
    const raw = await readAsStringAsync(PENDING_META);
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export default function VoiceElicitation() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    domain_id?: string;
    chapter_recall?: string;
    book_id?: string;
    book_title?: string;
    chapter_number?: string;
    chapter_title?: string;
  }>();
  const [candidates, setCandidates] = useState<ElicitationCandidate[]>([]);
  const [current, setCurrent] = useState(0);
  const [phase, setPhase] = useState<Phase>('loading');
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [result, setResult] = useState<ElicitationResult | null>(null);
  const [results, setResults] = useState<Array<{ node: string; score: string }>>([]);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [retryError, setRetryError] = useState('');
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const [processingCount, setProcessingCount] = useState(0);
  const [completedResults, setCompletedResults] = useState<Array<{ node: string; result: ElicitationResult }>>([]);
  const [expandedResultIdx, setExpandedResultIdx] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const savedUriRef = useRef<string | null>(null);
  const fadeAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    setFeedbackContext({ screen: 'voice-elicitation' });
    checkPendingThenLoad();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  async function checkPendingThenLoad() {
    // Direct chapter recall from book detail
    if (params.chapter_recall === '1' && params.book_id && params.chapter_number) {
      const chNum = params.chapter_number;
      const chTitle = params.chapter_title || '';
      const bookTitle = params.book_title || '';
      const cand: ElicitationCandidate = {
        type: 'chapter_recall',
        node_id: `chapter:${params.book_id}:${chNum}`,
        node_title: `Chapter ${chNum}: ${chTitle}`,
        node_description: `What do you remember from Chapter ${chNum} of ${bookTitle}? Speak freely about the key ideas, people, and events.`,
        domain_id: params.domain_id || '',
        knowledge: 'engaged',
        confidence: 0.5,
        elicitation_score: 0,
        book_id: params.book_id,
        book_title: bookTitle,
        chapter_number: parseInt(chNum, 10),
        chapter_title: chTitle,
      };
      setCandidates([cand]);
      setPhase('prompt');
      return;
    }

    const pending = await loadPendingUploads();
    if (pending.length > 0) {
      setPendingUploads(pending);
      setPhase('pending_retry');
    } else {
      loadCandidates();
    }
  }

  async function loadCandidates() {
    setPhase('loading');
    try {
      const domainId = params.domain_id || undefined;
      const { candidates: cands } = await getElicitationCandidates(domainId, 10);
      if (cands.length === 0) {
        setPhase('done');
        return;
      }
      setCandidates(cands);
      setPhase('prompt');
      logEvent('voice_elicitation_loaded', { domain: domainId || 'all', candidate_count: cands.length });
    } catch (e) {
      console.error('Failed to load candidates:', e);
      setPhase('done');
    }
  }

  async function startRecording() {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(rec);
      setPhase('recording');
      setRecordingDuration(0);
      timerRef.current = setInterval(() => setRecordingDuration(d => d + 1), 1000);
      logEvent('voice_elicitation_recording_start', {
        node_id: candidates[current]?.node_id,
        node_title: candidates[current]?.node_title,
      });
    } catch (e) {
      console.error('Recording failed:', e);
    }
  }

  async function stopAndProcess() {
    if (!recording) return;
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    try {
      await recording.stopAndUnloadAsync();
      const tempUri = recording.getURI();
      setRecording(null);

      if (!tempUri) return;

      // Save to persistent location before uploading
      const ts = Date.now();
      await makeDirectoryAsync(PENDING_DIR, { intermediates: true }).catch(() => {});
      const savedPath = `${PENDING_DIR}elicit_${ts}.m4a`;
      await copyAsync({ from: tempUri, to: savedPath });
      savedUriRef.current = savedPath;

      // Track as pending before upload attempt
      const cand = candidates[current];
      await savePendingUpload({
        audioUri: savedPath,
        nodeId: cand.node_id,
        domainId: cand.domain_id,
        nodeTitle: cand.node_title,
        recordedAt: ts,
      });

      // Upload in background — don't block, move to next topic immediately
      const candTitle = cand.node_title;
      setProcessingCount(c => c + 1);
      uploadElicitation(savedPath).then(async () => {
        await clearPendingUpload(savedPath);
      }).catch(() => {
        // Stays in pending for retry next time
        setProcessingCount(c => Math.max(0, c - 1));
      });

      // Immediately advance to next topic
      setRecordingDuration(0);
      nextNode();
    } catch (e) {
      console.error('Recording save/upload failed:', e);
      setRetryError(String(e));
      setPhase('retry');
    }
  }

  async function uploadElicitation(uri: string, overrideCand?: ElicitationCandidate) {
    const cand = overrideCand || candidates[current];
    if (!cand?.node_id) {
      throw new Error('No candidate context for upload');
    }
    const nodeTitle = cand.node_title || 'Unknown';
    try {
      logEvent('voice_elicitation_submitted', {
        node_id: cand.node_id, duration_s: recordingDuration,
      });
      const res = await sendVoiceElicitation(cand.node_id, cand.domain_id, uri);
      if (!res || (!res.captured?.length && !res.missed?.length && !res.feedback_summary)) {
        throw new Error('Server returned empty analysis');
      }
      setProcessingCount(c => Math.max(0, c - 1));
      setCompletedResults(prev => [...prev, { node: nodeTitle, result: res }]);
      logEvent('voice_elicitation_result', {
        node_id: cand?.node_id, coverage_pct: res.coverage_pct,
        captured_count: res.captured?.length || 0,
        missed_count: res.missed?.length || 0,
      });
    } catch (e) {
      console.error('Upload failed:', e);
      setProcessingCount(c => Math.max(0, c - 1));
      // Don't change phase — stays in pending.json for retry
      throw e;
    }
  }

  function nextNode() {
    const cand = candidates[current];
    setResults(prev => [...prev, {
      node: cand?.node_title || '',
      score: result?.suggested_score || 'missed'
    }]);

    Animated.timing(fadeAnim, { toValue: 0, duration: 150, useNativeDriver: true }).start(() => {
      const nextIdx = current + 1;
      if (nextIdx >= candidates.length) {
        setPhase('done');
      } else {
        setCurrent(nextIdx);
        setResult(null);
        setPhase('prompt');
      }
      Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    });
  }

  // ── Render ──

  if (phase === 'loading') {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator color={colors.rubric} />
        <Text style={styles.loadingText}>Finding topics for recall…</Text>
      </View>
    );
  }

  if (phase === 'pending_retry' && pendingUploads.length === 0) {
    // All retried — move to normal flow
    loadCandidates();
  }

  if (phase === 'pending_retry') {
    return (
      <View style={styles.container}>
        <View style={[styles.header, { paddingBottom: 16 }]}>
          <Text style={styles.headerTitle}>{'\u2726'} Unsent Recordings</Text>
          <Text style={[styles.loadingText, { marginTop: 8 }]}>
            {pendingUploads.length} recording{pendingUploads.length > 1 ? 's' : ''} saved but not uploaded.
          </Text>
        </View>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 20, gap: 12 }}>
          {pendingUploads.map((p, i) => (
            <View key={p.audioUri} style={{ backgroundColor: '#fff', borderRadius: 10, padding: 16, borderWidth: 1, borderColor: colors.rule }}>
              <Text style={{ fontFamily: fonts.display, fontSize: 18, color: colors.ink, marginBottom: 4 }}>{p.nodeTitle}</Text>
              <Text style={{ fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, marginBottom: 12 }}>
                Recorded {new Date(p.recordedAt).toLocaleString()}
              </Text>
              <View style={{ flexDirection: 'row', gap: 10 }}>
                <Pressable
                  style={[styles.recordBtn, { flex: 1 }]}
                  onPress={async () => {
                    // Set up context for upload
                    savedUriRef.current = p.audioUri;
                    const fakeCand: ElicitationCandidate = {
                      node_id: p.nodeId,
                      node_title: p.nodeTitle,
                      node_description: '',
                      domain_id: p.domainId,
                      knowledge: 'engaged',
                      confidence: 0.5,
                      elicitation_score: 0,
                    };
                    setProcessingCount(c => c + 1);
                    // Remove from pending list immediately and show processing
                    setPendingUploads(prev => prev.filter(u => u.audioUri !== p.audioUri));
                    uploadElicitation(p.audioUri, fakeCand).then(async () => {
                      await clearPendingUpload(p.audioUri);
                    }).catch(() => {
                      setProcessingCount(c => Math.max(0, c - 1));
                    });
                  }}
                >
                  <Text style={styles.recordBtnText}>Retry upload</Text>
                </Pressable>
                <Pressable
                  style={{ paddingVertical: 12, paddingHorizontal: 16 }}
                  onPress={async () => {
                    await clearPendingUpload(p.audioUri);
                    const remaining = pendingUploads.filter(u => u.audioUri !== p.audioUri);
                    setPendingUploads(remaining);
                    if (remaining.length === 0) loadCandidates();
                  }}
                >
                  <Text style={{ fontFamily: fonts.ui, fontSize: 13, color: colors.textMuted, textDecorationLine: 'underline' }}>Discard</Text>
                </Pressable>
              </View>
            </View>
          ))}
          <Pressable
            style={[styles.recordBtn, { marginHorizontal: 0 }]}
            onPress={async () => {
              // Retry all sequentially to avoid lock contention
              const items = [...pendingUploads];
              for (const p of items) {
                const fakeCand: ElicitationCandidate = {
                  node_id: p.nodeId, node_title: p.nodeTitle, node_description: '',
                  domain_id: p.domainId, knowledge: 'engaged', confidence: 0.5, elicitation_score: 0,
                };
                setProcessingCount(c => c + 1);
                setPendingUploads(prev => prev.filter(u => u.audioUri !== p.audioUri));
                try {
                  await uploadElicitation(p.audioUri, fakeCand);
                  await clearPendingUpload(p.audioUri);
                } catch {
                  setProcessingCount(c => Math.max(0, c - 1));
                }
              }
            }}
          >
            <Text style={styles.recordBtnText}>Retry all ({pendingUploads.length})</Text>
          </Pressable>
          <Pressable
            style={{ paddingVertical: 16, alignItems: 'center' }}
            onPress={() => { setPendingUploads([]); loadCandidates(); }}
          >
            <Text style={{ fontFamily: fonts.ui, fontSize: 13, color: colors.rubric }}>Skip to new topics</Text>
          </Pressable>
        </ScrollView>
      </View>
    );
  }

  if (phase === 'retry') {
    return (
      <View style={[styles.container, styles.centered]}>
        <Text style={styles.headerTitle}>{'\u2726'} Upload Failed</Text>
        <Text style={[styles.loadingText, { marginBottom: 12, textAlign: 'center', paddingHorizontal: 20 }]}>
          Your recording is saved locally. You can retry the upload.
        </Text>
        {retryError ? (
          <Text style={{ fontFamily: 'CrimsonPro_400Regular', fontSize: 12, color: '#cc4444', marginBottom: 16, paddingHorizontal: 20, textAlign: 'center' }}>
            {retryError.slice(0, 120)}
          </Text>
        ) : null}
        <Pressable
          style={[styles.recordBtn, { marginBottom: 12 }]}
          onPress={() => savedUriRef.current && uploadElicitation(savedUriRef.current)}
        >
          <Text style={styles.recordBtnText}>Retry upload</Text>
        </Pressable>
        <Pressable onPress={nextNode}>
          <Text style={[styles.loadingText, { textDecorationLine: 'underline' }]}>Skip to next</Text>
        </Pressable>
      </View>
    );
  }

  if (phase === 'done') {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{'\u2726'} Voice Recall Complete</Text>
          <View style={styles.doubleRule} />
          <Text style={styles.headerSubtext}>{results.length} topics recalled</Text>
        </View>
        <ScrollView style={styles.summaryList}>
          {results.map((r, i) => (
            <View key={i} style={styles.summaryRow}>
              <Text style={[styles.summaryIcon, {
                color: r.score === 'knew' ? '#2a7a4a' : r.score === 'partly' ? '#c9a84c' : '#cc4444'
              }]}>
                {r.score === 'knew' ? '\u2713' : r.score === 'partly' ? '~' : '\u2717'}
              </Text>
              <Text style={styles.summaryNodeTitle}>{r.node}</Text>
            </View>
          ))}
        </ScrollView>
        <View style={styles.doneActions}>
          <Pressable style={styles.doneBtn} onPress={() => router.back()}>
            <Text style={styles.doneBtnText}>Done</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const cand = candidates[current];

  function skipNode() {
    logEvent('voice_elicitation_skipped', { node_id: cand?.node_id, node_title: cand?.node_title });
    Animated.timing(fadeAnim, { toValue: 0, duration: 150, useNativeDriver: true }).start(() => {
      const nextIdx = current + 1;
      if (nextIdx >= candidates.length) {
        setPhase('done');
      } else {
        setCurrent(nextIdx);
        setResult(null);
        setPhase('prompt');
      }
      Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    });
  }

  return (
    <View style={styles.container}>
      {/* Top bar: back + progress */}
      <View style={styles.topBar}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>{'\u2190'} Back</Text>
        </Pressable>
        <Text style={styles.counter}>{current + 1} / {candidates.length}</Text>
      </View>

      <View style={styles.progressOuter}>
        <View style={[styles.progressInner, { width: `${((current) / candidates.length) * 100}%` as any }]} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* Background processing indicator */}
        {(processingCount > 0 || completedResults.length > 0) && (
          <View style={{ paddingHorizontal: 4, paddingBottom: 10, gap: 4 }}>
            {processingCount > 0 && (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <ActivityIndicator size="small" color={colors.rubric} />
                <Text style={{ fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted }}>
                  Processing {processingCount} recording{processingCount > 1 ? 's' : ''}...
                </Text>
              </View>
            )}
            {completedResults.slice(-3).map((cr, i) => {
              const idx = completedResults.length - 3 + i;
              const realIdx = Math.max(0, idx);
              const expanded = expandedResultIdx === realIdx;
              const r = cr.result;
              return (
                <View key={i}>
                  <Pressable
                    onPress={() => setExpandedResultIdx(expanded ? null : realIdx)}
                    style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}
                  >
                    <Text style={{ fontFamily: fonts.ui, fontSize: 11, color: colors.claimNew }}>
                      {'\u2713'} {cr.node}: {r.coverage_pct}% coverage
                      {r.microlearning_triggered?.length ? ` + ${r.microlearning_triggered.length} research` : ''}
                    </Text>
                    <Text style={{ fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted }}>
                      {expanded ? '\u25B4' : '\u25BE'}
                    </Text>
                  </Pressable>
                  {expanded && (
                    <View style={{ paddingLeft: 12, paddingTop: 6, paddingBottom: 8, gap: 6 }}>
                      {r.captured?.length > 0 && (
                        <View>
                          <Text style={{ fontFamily: fonts.ui, fontSize: 10, fontWeight: '600', color: colors.claimNew, marginBottom: 2 }}>CAPTURED</Text>
                          {r.captured.map((c: string, ci: number) => (
                            <Text key={ci} style={{ fontFamily: fonts.reading, fontSize: 12, color: colors.textBody, lineHeight: 17 }}>{'\u2022'} {c}</Text>
                          ))}
                        </View>
                      )}
                      {r.missed?.length > 0 && (
                        <View>
                          <Text style={{ fontFamily: fonts.ui, fontSize: 10, fontWeight: '600', color: colors.rubric, marginBottom: 2 }}>MISSED</Text>
                          {r.missed.map((m: string, mi: number) => (
                            <Text key={mi} style={{ fontFamily: fonts.reading, fontSize: 12, color: colors.textSecondary, lineHeight: 17 }}>{'\u2022'} {m}</Text>
                          ))}
                        </View>
                      )}
                      {r.interesting?.length > 0 && (
                        <View>
                          <Text style={{ fontFamily: fonts.ui, fontSize: 10, fontWeight: '600', color: '#1e5f8a', marginBottom: 2 }}>INTERESTING</Text>
                          {r.interesting.map((x: string, xi: number) => (
                            <Text key={xi} style={{ fontFamily: fonts.reading, fontSize: 12, color: colors.textSecondary, lineHeight: 17 }}>{'\u2022'} {x}</Text>
                          ))}
                        </View>
                      )}
                      {(r.microlearning_triggered ?? []).length > 0 && (
                        <View>
                          <Text style={{ fontFamily: fonts.ui, fontSize: 10, fontWeight: '600', color: colors.rubric, marginBottom: 2 }}>{'\u2726'} RESEARCHING</Text>
                          {(r.microlearning_triggered ?? []).map((m: { id: string; query: string }, mi: number) => (
                            <Text key={mi} style={{ fontFamily: fonts.reading, fontSize: 12, color: colors.textSecondary, lineHeight: 17, fontStyle: 'italic' }}>{'\u21BB'} {m.query}</Text>
                          ))}
                        </View>
                      )}
                      {r.feedback_summary && (
                        <Text style={{ fontFamily: fonts.readingItalic, fontSize: 12, color: colors.textMuted, marginTop: 2, fontStyle: 'italic' }}>
                          {r.feedback_summary}
                        </Text>
                      )}
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        )}

        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Prompt card */}
          <View style={styles.card}>
            <Text style={styles.domainLabel}>
              {cand.type === 'chapter_recall' && cand.book_title
                ? cand.book_title.slice(0, 40)
                : cand.domain_title || 'Review'}
            </Text>

            <Text style={styles.promptLabel}>
              {cand.type === 'chapter_recall'
                ? 'What do you remember from…'
                : 'Tell me what you remember about…'}
            </Text>
            <Text style={styles.nodeTitle}>{cand.node_title}</Text>

            {phase === 'prompt' && cand.type === 'chapter_recall' && (
              <Text style={styles.nodeDesc}>{cand.node_description}</Text>
            )}

            {/* Recording state */}
            {phase === 'prompt' && (
              <View>
                <Pressable style={styles.recordBtn} onPress={startRecording}>
                  <Text style={styles.recordBtnIcon}>{'\u25CE'}</Text>
                  <Text style={styles.recordBtnText}>Start speaking</Text>
                </Pressable>
                <Pressable style={styles.skipBtn} onPress={skipNode}>
                  <Text style={styles.skipBtnText}>Skip {'\u2192'}</Text>
                </Pressable>
              </View>
            )}

            {phase === 'recording' && (
              <View style={styles.recordingArea}>
                <Text style={styles.recordingTimer}>
                  {Math.floor(recordingDuration / 60)}:{(recordingDuration % 60).toString().padStart(2, '0')}
                </Text>
                <Text style={styles.recordingHint}>Speak freely — what do you remember?</Text>
                <Pressable style={styles.stopBtn} onPress={stopAndProcess}>
                  <Text style={styles.stopBtnText}>{'\u25A0'} Done speaking</Text>
                </Pressable>
              </View>
            )}

            {phase === 'processing' && (
              <View style={styles.processingArea}>
                <ActivityIndicator color={colors.rubric} />
                <Text style={styles.processingText}>Transcribing and analyzing…</Text>
              </View>
            )}

            {/* Feedback */}
            {phase === 'feedback' && result && (
              <View style={styles.feedbackArea}>
                <View style={styles.feedbackDivider} />

                {/* Feedback summary */}
                <Text style={styles.feedbackSummary}>{result.feedback_summary}</Text>

                {/* Coverage indicator */}
                <View style={styles.coverageRow}>
                  <View style={styles.coverageBar}>
                    <View style={[styles.coverageFill, { width: `${result.coverage_pct || 0}%` as any }]} />
                  </View>
                  <Text style={styles.coveragePct}>{result.coverage_pct || 0}%</Text>
                </View>

                {/* Captured */}
                {result.captured && result.captured.length > 0 && (
                  <View style={styles.feedbackSection}>
                    <Text style={styles.feedbackLabel}>{'\u2713'} YOU CAPTURED</Text>
                    {result.captured.map((c, i) => (
                      <Text key={i} style={[styles.feedbackItem, styles.feedbackCaptured]}>{'\u2022'} {c}</Text>
                    ))}
                  </View>
                )}

                {/* Missed */}
                {result.missed && result.missed.length > 0 && (
                  <View style={styles.feedbackSection}>
                    <Text style={[styles.feedbackLabel, { color: colors.rubric }]}>KEY THINGS MISSED</Text>
                    {result.missed.map((m, i) => (
                      <Text key={i} style={[styles.feedbackItem, styles.feedbackMissed]}>{'\u2022'} {m}</Text>
                    ))}
                  </View>
                )}

                {/* Interesting additions */}
                {result.interesting && result.interesting.length > 0 && (
                  <View style={styles.feedbackSection}>
                    <Text style={[styles.feedbackLabel, { color: '#2a4a6a' }]}>INTERESTING ADDITIONS</Text>
                    {result.interesting.map((x, i) => (
                      <Text key={i} style={[styles.feedbackItem, { color: '#2a4a6a' }]}>{'\u2726'} {x}</Text>
                    ))}
                  </View>
                )}

                {/* Temporal hook */}
                {result.temporal_hook ? (
                  <View style={styles.temporalHook}>
                    <Text style={styles.temporalHookText}>{'\u2726'} {result.temporal_hook}</Text>
                  </View>
                ) : null}

                {/* Wonderings / research triggers */}
                {result.research_triggers && result.research_triggers.length > 0 && (
                  <View style={styles.feedbackSection}>
                    <Text style={[styles.feedbackLabel, { color: '#5a3a7a' }]}>RESEARCH QUEUED</Text>
                    {result.research_triggers.map((r, i) => (
                      <Text key={i} style={[styles.feedbackItem, { color: '#5a3a7a' }]}>{'\u2192'} {r.question}</Text>
                    ))}
                  </View>
                )}

                {result.microlearning_triggered && result.microlearning_triggered.length > 0 && (
                  <View style={styles.feedbackSection}>
                    <Text style={[styles.feedbackLabel, { color: colors.rubric }]}>{'\u2726'} RESEARCHING NOW</Text>
                    {result.microlearning_triggered.map((m, i) => (
                      <Text key={i} style={[styles.feedbackItem, { color: colors.textSecondary, fontStyle: 'italic' }]}>{'\u21BB'} {m.query}</Text>
                    ))}
                    <Text style={{ fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, marginTop: 6 }}>
                      These will appear as research cards in your review stream.
                    </Text>
                  </View>
                )}

                {/* Next button */}
                <Pressable style={styles.nextBtn} onPress={nextNode}>
                  <Text style={styles.nextBtnText}>
                    {current + 1 < candidates.length ? '\u2726 Next topic' : '\u2726 Finish'}
                  </Text>
                </Pressable>
              </View>
            )}
          </View>

        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  centered: { alignItems: 'center', justifyContent: 'center' },
  topBar: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 16, paddingTop: Platform.OS === 'ios' ? 56 : 12, paddingBottom: 8,
  },
  backBtn: { padding: 4 },
  backBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 14, color: colors.rubric,
  },
  progressOuter: { height: 3, backgroundColor: colors.rule },
  progressInner: { height: 3, backgroundColor: colors.rubric },
  scroll: { flex: 1 },
  scrollContent: { padding: 16, paddingTop: 12 },

  loadingText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 13, color: colors.textMuted, marginTop: 12,
  },

  card: {
    backgroundColor: 'white', borderWidth: 1, borderColor: colors.rule,
    borderRadius: 4, padding: 24, marginBottom: 12,
  },
  domainLabel: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 11, color: colors.rubric, textTransform: 'uppercase',
    letterSpacing: 0.8, fontWeight: '500', marginBottom: 16,
  },
  promptLabel: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro' }),
    fontSize: 15, color: colors.textSecondary, fontStyle: 'italic', marginBottom: 4,
  },
  nodeTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 24, fontWeight: '500', color: colors.ink, lineHeight: 32, marginBottom: 12,
  },
  nodeDesc: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro' }),
    fontSize: 15, color: colors.textSecondary, lineHeight: 22, marginBottom: 20,
  },

  recordBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 16, borderRadius: 4,
    backgroundColor: colors.rubric, gap: 8,
  },
  recordBtnIcon: { fontSize: 20, color: 'white' },
  recordBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 15, color: 'white', fontWeight: '600',
  },

  recordingArea: { alignItems: 'center', paddingVertical: 20 },
  recordingTimer: {
    fontFamily: Platform.select({ web: "'Cormorant Garamond', Georgia, serif", default: 'CormorantGaramond' }),
    fontSize: 48, fontWeight: '600', color: '#cc4444',
  },
  recordingHint: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro' }),
    fontSize: 14, color: colors.textMuted, marginTop: 4, marginBottom: 20,
  },
  stopBtn: {
    paddingHorizontal: 24, paddingVertical: 12, borderRadius: 4,
    borderWidth: 1, borderColor: '#cc4444', backgroundColor: '#fff5f5',
  },
  stopBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 14, color: '#cc4444', fontWeight: '500',
  },

  processingArea: { alignItems: 'center', paddingVertical: 30 },
  processingText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 13, color: colors.textMuted, marginTop: 10,
  },

  feedbackArea: { marginTop: 4 },
  feedbackDivider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.rule, marginBottom: 16 },
  feedbackSummary: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro' }),
    fontSize: 16, lineHeight: 24, color: colors.textBody, marginBottom: 16,
  },

  coverageRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 16 },
  coverageBar: { flex: 1, height: 6, backgroundColor: colors.rule, borderRadius: 3 },
  coverageFill: { height: 6, backgroundColor: colors.rubric, borderRadius: 3 },
  coveragePct: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 12, fontWeight: '600', color: colors.textSecondary, width: 36,
  },

  feedbackSection: { marginBottom: 14 },
  feedbackLabel: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 10, fontWeight: '600', letterSpacing: 0.8, textTransform: 'uppercase',
    color: '#2a7a4a', marginBottom: 4,
  },
  feedbackItem: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro' }),
    fontSize: 14.5, lineHeight: 21, marginBottom: 2,
  },
  feedbackCaptured: { color: '#2a7a4a' },
  feedbackMissed: { color: colors.rubric },

  temporalHook: {
    borderLeftWidth: 2, borderLeftColor: colors.rubric,
    paddingLeft: 12, paddingVertical: 8, marginVertical: 10,
    backgroundColor: colors.parchment,
  },
  temporalHookText: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro' }),
    fontSize: 14, fontStyle: 'italic', color: colors.textSecondary,
  },

  nextBtn: {
    paddingVertical: 14, borderRadius: 4, marginTop: 16,
    backgroundColor: colors.rubric, alignItems: 'center',
  },
  nextBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 14, color: 'white', fontWeight: '600',
  },

  counter: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 12, color: colors.textMuted, textAlign: 'center',
  },
  skipBtn: { alignItems: 'center', paddingVertical: 12, marginTop: 8 },
  skipBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 13, color: colors.textMuted,
  },

  // Summary screen
  header: { paddingHorizontal: 16, paddingTop: Platform.OS === 'ios' ? 56 : 16 },
  headerTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 22, fontWeight: '600', color: colors.ink, marginBottom: 6,
  },
  doubleRule: {
    height: 5, backgroundColor: 'transparent',
    borderTopWidth: 2, borderTopColor: colors.rubric,
    borderBottomWidth: 1, borderBottomColor: colors.rubric,
    marginBottom: 10,
  },
  headerSubtext: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 14, color: colors.textSecondary, marginBottom: 16,
  },
  summaryList: { flex: 1, paddingHorizontal: 16 },
  summaryRow: {
    flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule,
  },
  summaryIcon: { fontSize: 16, marginRight: 10, width: 20 },
  summaryNodeTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 15, color: colors.textBody, flex: 1,
  },
  doneActions: { paddingHorizontal: 16, paddingBottom: 16 },
  doneBtn: {
    paddingVertical: 12, borderRadius: 3,
    borderWidth: 1, borderColor: colors.rule, alignItems: 'center',
  },
  doneBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans' }),
    fontSize: 14, color: colors.textMuted, fontWeight: '500',
  },
});