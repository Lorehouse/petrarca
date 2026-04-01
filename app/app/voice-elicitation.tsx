import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Animated, Platform, Pressable,
  ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { Audio } from 'expo-av';
import { documentDirectory, makeDirectoryAsync, copyAsync } from 'expo-file-system/legacy';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { colors } from '../design/tokens';
import {
  getElicitationCandidates, sendVoiceElicitation,
  ElicitationCandidate, ElicitationResult,
} from '../lib/review-api';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';

type Phase = 'loading' | 'prompt' | 'recording' | 'processing' | 'feedback' | 'retry' | 'done';

export default function VoiceElicitation() {
  const router = useRouter();
  const params = useLocalSearchParams<{ domain_id?: string }>();
  const [candidates, setCandidates] = useState<ElicitationCandidate[]>([]);
  const [current, setCurrent] = useState(0);
  const [phase, setPhase] = useState<Phase>('loading');
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [result, setResult] = useState<ElicitationResult | null>(null);
  const [results, setResults] = useState<Array<{ node: string; score: string }>>([]);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [retryError, setRetryError] = useState('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const savedUriRef = useRef<string | null>(null);
  const fadeAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    setFeedbackContext({ screen: 'voice-elicitation' });
    loadCandidates();
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  async function loadCandidates() {
    setPhase('loading');
    try {
      const domainId = params.domain_id || undefined;
      const { candidates: cands } = await getElicitationCandidates(domainId, 5);
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
      const persistDir = `${documentDirectory}voice-elicitation/`;
      await makeDirectoryAsync(persistDir, { intermediates: true }).catch(() => {});
      const savedPath = `${persistDir}elicit_${ts}.m4a`;
      await copyAsync({ from: tempUri, to: savedPath });
      savedUriRef.current = savedPath;

      await uploadElicitation(savedPath);
    } catch (e) {
      console.error('Recording save/upload failed:', e);
      setRetryError(String(e));
      setPhase('retry');
    }
  }

  async function uploadElicitation(uri: string) {
    setPhase('processing');
    setRetryError('');
    try {
      const cand = candidates[current];
      logEvent('voice_elicitation_submitted', {
        node_id: cand.node_id, duration_s: recordingDuration,
      });
      const res = await sendVoiceElicitation(cand.node_id, cand.domain_id, uri);
      setResult(res);
      setPhase('feedback');
      logEvent('voice_elicitation_result', {
        node_id: cand.node_id, coverage_pct: res.coverage_pct,
        captured_count: res.captured?.length || 0,
        missed_count: res.missed?.length || 0,
        interesting_count: res.interesting?.length || 0,
        wonderings_count: res.wonderings?.length || 0,
      });
    } catch (e) {
      console.error('Upload failed:', e);
      setRetryError(String(e));
      setPhase('retry');
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

  return (
    <View style={styles.container}>
      {/* Progress */}
      <View style={styles.progressOuter}>
        <View style={[styles.progressInner, { width: `${((current) / candidates.length) * 100}%` as any }]} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <Animated.View style={{ opacity: fadeAnim }}>
          {/* Prompt card */}
          <View style={styles.card}>
            <Text style={styles.domainLabel}>
              {cand.type === 'chapter_recall' && cand.book_title
                ? cand.book_title.slice(0, 40)
                : cand.domain_id?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()).slice(0, 30) || 'Review'}
            </Text>

            <Text style={styles.promptLabel}>
              {cand.type === 'chapter_recall'
                ? 'What do you remember from…'
                : 'Tell me what you remember about…'}
            </Text>
            <Text style={styles.nodeTitle}>{cand.node_title}</Text>

            {phase === 'prompt' && (
              <Text style={styles.nodeDesc}>{cand.node_description}</Text>
            )}

            {/* Recording state */}
            {phase === 'prompt' && (
              <Pressable style={styles.recordBtn} onPress={startRecording}>
                <Text style={styles.recordBtnIcon}>{'\u25CE'}</Text>
                <Text style={styles.recordBtnText}>Start speaking</Text>
              </Pressable>
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

                {/* Next button */}
                <Pressable style={styles.nextBtn} onPress={nextNode}>
                  <Text style={styles.nextBtnText}>
                    {current + 1 < candidates.length ? '\u2726 Next topic' : '\u2726 Finish'}
                  </Text>
                </Pressable>
              </View>
            )}
          </View>

          <Text style={styles.counter}>{current + 1} / {candidates.length}</Text>
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  centered: { alignItems: 'center', justifyContent: 'center' },
  progressOuter: { height: 3, backgroundColor: colors.rule },
  progressInner: { height: 3, backgroundColor: colors.rubric },
  scroll: { flex: 1 },
  scrollContent: { padding: 16, paddingTop: Platform.OS === 'ios' ? 60 : 20 },

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
    fontSize: 12, color: colors.textMuted, textAlign: 'center', marginTop: 4,
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