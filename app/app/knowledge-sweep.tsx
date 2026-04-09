import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Platform, Pressable,
  ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { Audio } from 'expo-av';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { colors, fonts } from '../design/tokens';
import {
  getSweepPlan, getSweepDomains, transcribeSweepEra, submitSweep,
  SweepPlan, SweepEra, SweepResult,
} from '../lib/review-api';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';

type Phase =
  | 'domain_select'  // pick which domain to sweep
  | 'ready'          // show plan, ready to start
  | 'recording'      // recording an era
  | 'transcribing'   // transcribing current era
  | 'era_done'       // era finished, show next
  | 'scoring'        // all eras done, LLM scoring
  | 'results'        // show results
  | 'error';

interface EraRecording {
  era_id: string;
  transcript: string;
  duration_s: number;
  status: 'pending' | 'recording' | 'transcribing' | 'done' | 'skipped';
}

export default function KnowledgeSweep() {
  const router = useRouter();
  const params = useLocalSearchParams<{ domain_id?: string }>();
  const [phase, setPhase] = useState<Phase>(params.domain_id ? 'ready' : 'domain_select');
  const [plan, setPlan] = useState<SweepPlan | null>(null);
  const [domains, setDomains] = useState<any[]>([]);
  const [currentEra, setCurrentEra] = useState(0);
  const [eraRecordings, setEraRecordings] = useState<EraRecording[]>([]);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [duration, setDuration] = useState(0);
  const [result, setResult] = useState<SweepResult | null>(null);
  const [error, setError] = useState('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setFeedbackContext({ screen: 'knowledge-sweep' });
    if (params.domain_id) {
      loadPlan(params.domain_id);
    } else {
      loadDomains();
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  async function loadDomains() {
    try {
      const { domains: d } = await getSweepDomains();
      setDomains(d);
    } catch (e) {
      setError(String(e));
      setPhase('error');
    }
  }

  async function loadPlan(domainId: string) {
    try {
      const p = await getSweepPlan(domainId);
      setPlan(p);
      setEraRecordings(p.eras.map(e => ({
        era_id: e.era_id, transcript: '', duration_s: 0, status: 'pending',
      })));
      setPhase('ready');
    } catch (e) {
      setError(String(e));
      setPhase('error');
    }
  }

  async function startEra() {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      setRecording(rec);
      setDuration(0);
      setPhase('recording');
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000);
      updateEraStatus(currentEra, 'recording');
      logEvent('sweep_era_start', { era_id: plan?.eras[currentEra]?.era_id, era_index: currentEra });
    } catch (e) {
      console.error('Recording failed:', e);
    }
  }

  async function stopEra() {
    if (!recording) return;
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    const finalDuration = duration;
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) { skipEra(); return; }

      updateEraStatus(currentEra, 'transcribing');
      setPhase('transcribing');

      const era = plan!.eras[currentEra];
      logEvent('sweep_era_stop', { era_id: era.era_id, duration_s: finalDuration });

      const { transcript } = await transcribeSweepEra(uri, era.era_id);
      setEraRecordings(prev => {
        const next = [...prev];
        next[currentEra] = {
          ...next[currentEra],
          transcript: transcript || '',
          duration_s: finalDuration,
          status: transcript ? 'done' : 'skipped',
        };
        return next;
      });

      if (currentEra + 1 < plan!.eras.length) {
        setCurrentEra(currentEra + 1);
        setDuration(0);
        setPhase('era_done');
      } else {
        // All eras done — submit for scoring
        scoreAllEras(currentEra, transcript || '', finalDuration);
      }
    } catch (e) {
      console.error('Era stop failed:', e);
      // Still advance — don't block the sweep on one failed transcription
      updateEraStatus(currentEra, 'skipped');
      if (currentEra + 1 < plan!.eras.length) {
        setCurrentEra(currentEra + 1);
        setDuration(0);
        setPhase('era_done');
      } else {
        scoreAllEras(currentEra, '', finalDuration);
      }
    }
  }

  function skipEra() {
    updateEraStatus(currentEra, 'skipped');
    logEvent('sweep_era_skip', { era_id: plan?.eras[currentEra]?.era_id });
    if (currentEra + 1 < plan!.eras.length) {
      setCurrentEra(currentEra + 1);
      setDuration(0);
      setPhase('era_done');
    } else {
      scoreAllEras(currentEra, '', 0);
    }
  }

  async function scoreAllEras(lastIdx: number, lastTranscript: string, lastDuration: number) {
    setPhase('scoring');
    // Build final era list from state + the last era we just recorded
    const finalEras = eraRecordings.map((er, i) => {
      if (i === lastIdx && lastTranscript) {
        return { era_id: er.era_id, transcript: lastTranscript, duration_s: lastDuration };
      }
      return { era_id: er.era_id, transcript: er.transcript, duration_s: er.duration_s };
    }).filter(e => e.transcript);

    if (finalEras.length === 0) {
      setError('No transcripts to score — all eras were skipped or too short.');
      setPhase('error');
      return;
    }

    try {
      logEvent('sweep_scoring_start', { domain_id: plan!.domain_id, era_count: finalEras.length });
      const res = await submitSweep(plan!.domain_id, finalEras);
      setResult(res);
      setPhase('results');
      logEvent('sweep_complete', {
        domain_id: plan!.domain_id,
        coverage: res.total_coverage,
        composite: res.composite_score,
      });
    } catch (e) {
      setError(String(e));
      setPhase('error');
    }
  }

  function updateEraStatus(idx: number, status: EraRecording['status']) {
    setEraRecordings(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], status };
      return next;
    });
  }

  function formatTime(s: number) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }

  function pct(n: number) { return `${Math.round(n * 100)}%`; }

  // ── Domain Selection ──
  if (phase === 'domain_select') {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Knowledge Sweep</Text>
        <Text style={styles.subtitle}>Choose a domain to assess</Text>
        {domains.length === 0 ? (
          <ActivityIndicator color={colors.rubric} style={{ marginTop: 40 }} />
        ) : (
          <ScrollView style={styles.scroll} contentContainerStyle={{ paddingBottom: 40 }}>
            {domains.map(d => (
              <Pressable
                key={d.id}
                style={styles.domainCard}
                onPress={() => loadPlan(d.id)}
              >
                <Text style={styles.domainTitle}>{d.title}</Text>
                <Text style={styles.domainMeta}>
                  {d.node_count} nodes
                  {d.last_sweep
                    ? ` · Last sweep: ${pct(d.last_sweep.total_coverage)} coverage`
                    : ' · No sweeps yet'}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
      </View>
    );
  }

  // ── Ready to Start ──
  if (phase === 'ready' && plan) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>{plan.domain_title}</Text>
        <Text style={styles.subtitle}>Knowledge Sweep</Text>
        <Text style={styles.body}>
          You'll walk through {plan.eras.length} eras, speaking for ~30 seconds each about
          what you remember. Focus on key events, people, and turning points.
        </Text>
        <Text style={styles.bodyMuted}>
          System thinks you know {pct(plan.system_coverage)} of this curriculum.
          Let's see what you can actually recall.
        </Text>
        <View style={styles.eraList}>
          {plan.eras.map((e, i) => (
            <View key={e.era_id} style={styles.eraPreview}>
              <Text style={styles.eraNum}>{i + 1}</Text>
              <Text style={styles.eraPreviewTitle}>{e.title}</Text>
              <Text style={styles.eraChildCount}>{e.child_count} topics</Text>
            </View>
          ))}
        </View>
        <Pressable style={styles.startBtn} onPress={startEra}>
          <Text style={styles.startBtnText}>Begin Sweep</Text>
        </Pressable>
      </View>
    );
  }

  // ── Recording an Era ──
  if (phase === 'recording' && plan) {
    const era = plan.eras[currentEra];
    return (
      <View style={styles.container}>
        {/* Progress bar */}
        <View style={styles.progressBar}>
          {plan.eras.map((_, i) => (
            <View
              key={i}
              style={[
                styles.progressDot,
                i < currentEra && styles.progressDone,
                i === currentEra && styles.progressActive,
              ]}
            />
          ))}
        </View>

        <Text style={styles.eraLabel}>Era {currentEra + 1} of {plan.eras.length}</Text>
        <Text style={styles.eraTitle}>{era.title}</Text>
        <Text style={styles.eraPrompt}>{era.prompt}</Text>

        <Text style={styles.timer}>{formatTime(duration)}</Text>

        <View style={styles.recordingIndicator}>
          <View style={styles.recordingDot} />
          <Text style={styles.recordingText}>Recording</Text>
        </View>

        <View style={styles.btnRow}>
          <Pressable style={styles.skipBtn} onPress={skipEra}>
            <Text style={styles.skipBtnText}>Skip</Text>
          </Pressable>
          <Pressable style={styles.stopBtn} onPress={stopEra}>
            <Text style={styles.stopBtnText}>Done</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  // ── Transcribing ──
  if (phase === 'transcribing' && plan) {
    return (
      <View style={styles.container}>
        <Text style={styles.eraLabel}>Era {currentEra + 1} of {plan.eras.length}</Text>
        <Text style={styles.eraTitle}>{plan.eras[currentEra].title}</Text>
        <ActivityIndicator color={colors.rubric} size="large" style={{ marginTop: 30 }} />
        <Text style={styles.processingText}>Transcribing...</Text>
      </View>
    );
  }

  // ── Era Done — advance to next ──
  if (phase === 'era_done' && plan) {
    const nextEra = plan.eras[currentEra];
    const prevDone = eraRecordings.filter(e => e.status === 'done').length;
    return (
      <View style={styles.container}>
        <View style={styles.progressBar}>
          {plan.eras.map((_, i) => (
            <View
              key={i}
              style={[
                styles.progressDot,
                i < currentEra && styles.progressDone,
                i === currentEra && styles.progressActive,
              ]}
            />
          ))}
        </View>
        <Text style={styles.checkmark}>{'\u2713'}</Text>
        <Text style={styles.bodyMuted}>{prevDone} era{prevDone !== 1 ? 's' : ''} recorded</Text>
        <Text style={styles.eraLabel}>Next up:</Text>
        <Text style={styles.eraTitle}>{nextEra.title}</Text>
        <Pressable style={styles.startBtn} onPress={startEra}>
          <Text style={styles.startBtnText}>Record</Text>
        </Pressable>
        <Pressable style={[styles.skipBtn, { marginTop: 12 }]} onPress={skipEra}>
          <Text style={styles.skipBtnText}>Skip this era</Text>
        </Pressable>
      </View>
    );
  }

  // ── Scoring ──
  if (phase === 'scoring') {
    const doneCount = eraRecordings.filter(e => e.status === 'done').length;
    return (
      <View style={styles.container}>
        <ActivityIndicator color={colors.rubric} size="large" />
        <Text style={styles.processingText}>Scoring your sweep...</Text>
        <Text style={styles.bodyMuted}>
          Analyzing {doneCount} era transcripts against the curriculum.{'\n'}
          This takes 30-60 seconds.
        </Text>
      </View>
    );
  }

  // ── Results ──
  if (phase === 'results' && result) {
    const detail = result.scoring_detail;
    const mentioned = detail.nodes.filter(n => n.mentioned);
    const missed = detail.nodes.filter(n => !n.mentioned);
    return (
      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 60 }}>
        <Text style={styles.title}>{result.domain_title}</Text>
        <Text style={styles.subtitle}>Sweep Results</Text>

        {/* Headline metrics */}
        <View style={styles.metricsRow}>
          <MetricBox label="Coverage" value={pct(result.total_coverage)} />
          <MetricBox label="Accuracy" value={pct(result.total_accuracy)} />
          <MetricBox label="Connections" value={pct(result.connectivity_score)} />
          <MetricBox label="Composite" value={result.composite_score.toFixed(2)} />
        </View>

        {/* System vs self comparison */}
        <View style={styles.comparisonBox}>
          <Text style={styles.comparisonTitle}>System vs. Self</Text>
          <Text style={styles.comparisonText}>
            System estimated {pct(result.system_coverage)} coverage.{'\n'}
            You recalled {pct(result.total_coverage)}.
            {result.system_coverage > result.total_coverage + 0.1
              ? ' The system may be over-crediting — reading ≠ learning.'
              : result.total_coverage > result.system_coverage + 0.1
                ? ' You know more than the system tracks!'
                : ' Pretty close — the system tracks your knowledge well.'}
          </Text>
        </View>

        {/* LLM summary */}
        <Text style={styles.sectionHead}>Assessment</Text>
        <Text style={styles.body}>{detail.summary}</Text>

        {detail.strongest_area ? (
          <View style={styles.insightBox}>
            <Text style={styles.insightLabel}>Strongest</Text>
            <Text style={styles.insightText}>{detail.strongest_area}</Text>
          </View>
        ) : null}
        {detail.biggest_gap ? (
          <View style={[styles.insightBox, { borderLeftColor: colors.rubric }]}>
            <Text style={styles.insightLabel}>Biggest Gap</Text>
            <Text style={styles.insightText}>{detail.biggest_gap}</Text>
          </View>
        ) : null}

        {/* Mentioned nodes */}
        <Text style={styles.sectionHead}>
          Covered ({mentioned.length}/{detail.nodes.length})
        </Text>
        {mentioned.map(n => (
          <View key={n.node_id} style={styles.nodeRow}>
            <View style={[styles.depthDot, depthColor(n.depth)]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.nodeTitle}>{n.node_title}</Text>
              <Text style={styles.nodeMeta}>
                {n.depth} · {n.facts.length} fact{n.facts.length !== 1 ? 's' : ''}
                {n.facts.some(f => !f.correct) ? ' · has errors' : ''}
              </Text>
            </View>
          </View>
        ))}

        {/* Missed nodes */}
        {missed.length > 0 && (
          <>
            <Text style={styles.sectionHead}>Missed ({missed.length})</Text>
            {missed.map(n => (
              <View key={n.node_id} style={styles.nodeRow}>
                <View style={[styles.depthDot, { backgroundColor: colors.textMuted }]} />
                <Text style={[styles.nodeTitle, { opacity: 0.5 }]}>{n.node_title}</Text>
              </View>
            ))}
          </>
        )}

        {/* Errors */}
        {detail.errors && detail.errors.length > 0 && (
          <>
            <Text style={styles.sectionHead}>Factual Errors</Text>
            {detail.errors.map((e, i) => (
              <View key={i} style={styles.errorBox}>
                <Text style={styles.errorClaim}>{e.claim}</Text>
                <Text style={styles.errorCorrection}>{e.correction}</Text>
              </View>
            ))}
          </>
        )}

        {/* Organization */}
        <Text style={styles.sectionHead}>Organization</Text>
        <Text style={styles.body}>
          Pattern: {detail.organization.pattern} · {detail.organization.causal_count} causal connections
        </Text>

        <Pressable style={[styles.startBtn, { marginTop: 24 }]} onPress={() => router.back()}>
          <Text style={styles.startBtnText}>Done</Text>
        </Pressable>
      </ScrollView>
    );
  }

  // ── Error ──
  if (phase === 'error') {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Error</Text>
        <Text style={styles.body}>{error}</Text>
        <Pressable style={styles.startBtn} onPress={() => router.back()}>
          <Text style={styles.startBtnText}>Back</Text>
        </Pressable>
      </View>
    );
  }

  // Loading fallback
  return (
    <View style={styles.container}>
      <ActivityIndicator color={colors.rubric} size="large" />
    </View>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function depthColor(depth: string) {
  switch (depth) {
    case 'situation_model': return { backgroundColor: colors.success };
    case 'textbase': return { backgroundColor: colors.info };
    case 'surface': return { backgroundColor: colors.warning };
    default: return { backgroundColor: colors.textMuted };
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
    paddingHorizontal: 24,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
    alignItems: 'center',
  },
  scroll: { width: '100%' },
  title: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 26,
    color: colors.ink,
    textAlign: 'center',
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  subtitle: {
    fontFamily: fonts.displayItalic,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 4,
    marginBottom: 20,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  body: {
    fontFamily: fonts.reading,
    fontSize: 15,
    lineHeight: 22,
    color: colors.textBody,
    textAlign: 'center',
    marginBottom: 12,
  },
  bodyMuted: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 16,
  },
  sectionHead: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    letterSpacing: 1.4,
    textTransform: 'uppercase',
    color: colors.textSecondary,
    marginTop: 24,
    marginBottom: 8,
    alignSelf: 'flex-start',
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },

  // Domain selection
  domainCard: {
    backgroundColor: colors.parchmentDark,
    padding: 16,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  domainTitle: {
    fontFamily: fonts.bodyMedium,
    fontSize: 16,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  domainMeta: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 4,
  },

  // Era list in ready state
  eraList: { width: '100%', marginTop: 16, marginBottom: 20 },
  eraPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
  },
  eraNum: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
    width: 24,
  },
  eraPreviewTitle: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
    flex: 1,
  },
  eraChildCount: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },

  // Progress bar
  progressBar: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 24,
  },
  progressDot: {
    width: 28,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.rule,
  },
  progressDone: { backgroundColor: colors.success },
  progressActive: { backgroundColor: colors.rubric },

  // Recording state
  eraLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: colors.textMuted,
    marginBottom: 8,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  eraTitle: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 24,
    color: colors.ink,
    textAlign: 'center',
    marginBottom: 12,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  eraPrompt: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 24,
    paddingHorizontal: 16,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  timer: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 48,
    color: colors.ink,
    marginBottom: 16,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 32,
  },
  recordingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.rubric,
  },
  recordingText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
  },
  checkmark: {
    fontFamily: fonts.display,
    fontSize: 48,
    color: colors.success,
    marginBottom: 8,
  },

  // Buttons
  btnRow: { flexDirection: 'row', gap: 12 },
  startBtn: {
    backgroundColor: colors.ink,
    paddingVertical: 14,
    paddingHorizontal: 48,
    borderRadius: 8,
  },
  startBtnText: {
    fontFamily: fonts.uiMedium,
    fontSize: 14,
    color: colors.parchment,
    textAlign: 'center',
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  stopBtn: {
    backgroundColor: colors.rubric,
    paddingVertical: 14,
    paddingHorizontal: 36,
    borderRadius: 8,
  },
  stopBtnText: {
    fontFamily: fonts.uiMedium,
    fontSize: 14,
    color: colors.parchment,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  skipBtn: {
    paddingVertical: 10,
    paddingHorizontal: 24,
  },
  skipBtnText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.textMuted,
  },
  processingText: {
    fontFamily: fonts.body,
    fontSize: 16,
    color: colors.ink,
    marginTop: 16,
    textAlign: 'center',
  },

  // Results
  metricsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 20,
    width: '100%',
  },
  metricBox: {
    flex: 1,
    backgroundColor: colors.parchmentDark,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.rule,
  },
  metricValue: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 22,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  metricLabel: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginTop: 2,
  },
  comparisonBox: {
    backgroundColor: 'rgba(42, 74, 106, 0.06)',
    padding: 16,
    borderRadius: 8,
    width: '100%',
    marginBottom: 16,
    borderLeftWidth: 3,
    borderLeftColor: colors.info,
  },
  comparisonTitle: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.info,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 6,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  comparisonText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    lineHeight: 20,
    color: colors.textBody,
  },
  insightBox: {
    borderLeftWidth: 3,
    borderLeftColor: colors.success,
    paddingLeft: 12,
    paddingVertical: 6,
    marginBottom: 10,
    width: '100%',
  },
  insightLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 9,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: colors.textMuted,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  insightText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.textBody,
    marginTop: 2,
  },
  nodeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 6,
    width: '100%',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  depthDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  nodeTitle: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
  },
  nodeMeta: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 1,
  },
  errorBox: {
    backgroundColor: 'rgba(139, 37, 0, 0.05)',
    padding: 12,
    borderRadius: 6,
    marginBottom: 8,
    width: '100%',
    borderLeftWidth: 3,
    borderLeftColor: colors.rubric,
  },
  errorClaim: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.rubric,
    textDecorationLine: 'line-through',
  },
  errorCorrection: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textBody,
    marginTop: 4,
  },
});
