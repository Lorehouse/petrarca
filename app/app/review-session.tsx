import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, Animated, Platform, Pressable,
  ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { Audio } from 'expo-av';
import { useRouter } from 'expo-router';
import { colors } from '../design/tokens';
import { ReviewItem, ReviewQuestion } from '../data/types';
import {
  getReviewQueue, generateQuestion, recordAnswer,
  createExplorationItems, sendVoiceMemo, getReviewStats,
} from '../lib/review-api';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';

const LENS_COLORS: Record<string, [string, string]> = {
  CAUSAL:       ['#7a3000', '#fff0e8'],
  COMPARATIVE:  ['#1a4a7a', '#e8f0ff'],
  SIGNIFICANCE: ['#2a6a3a', '#e8f5ec'],
  TEMPORAL:     ['#5a3a7a', '#f0e8ff'],
  PATTERN:      ['#7a6a00', '#fff8e0'],
  CONSEQUENCE:  ['#5a0a0a', '#ffe8e8'],
};
const LENS_LABELS: Record<string, string> = {
  CAUSAL: 'Why?', COMPARATIVE: 'Compare', SIGNIFICANCE: 'Why it matters',
  TEMPORAL: 'Timing', PATTERN: 'Pattern', CONSEQUENCE: 'What followed',
};

type SessionState = 'loading' | 'question' | 'revealed' | 'done';

interface SessionCard {
  item: ReviewItem;
  question: ReviewQuestion | null;
}

export default function ReviewSession() {
  const router = useRouter();
  const [cards, setCards] = useState<SessionCard[]>([]);
  const [current, setCurrent] = useState(0);
  const [state, setState] = useState<SessionState>('loading');
  const [scores, setScores] = useState<Array<{ id: string; score: string }>>([]);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [recordingItem, setRecordingItem] = useState<string | null>(null);
  const [processingVoice, setProcessingVoice] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [exploreItems, setExploreItems] = useState<string[]>([]);
  const [remainingDue, setRemainingDue] = useState<number>(0);
  const fadeAnim = useRef(new Animated.Value(1)).current;
  const cardShownAt = useRef<number>(0);
  const revealedAt = useRef<number>(0);
  const sessionStartAt = useRef<number>(Date.now());
  const sessionCompleteLogged = useRef(false);

  useEffect(() => {
    setFeedbackContext({ screen: 'review-session' });
    sessionStartAt.current = Date.now();
    loadSession();
  }, []);

  async function loadSession() {
    setState('loading');
    setScores([]);
    setCurrent(0);
    setExpandedItems(new Set());
    setExploreItems([]);
    sessionCompleteLogged.current = false;
    sessionStartAt.current = Date.now();
    try {
      const { items } = await getReviewQueue(10);
      if (items.length === 0) {
        setState('done');
        return;
      }
      getReviewStats().then(stats => setRemainingDue(stats.due_today ?? 0)).catch(() => {});
      logEvent('review_session_loaded', {
        items_total: items.length,
        lens_breakdown: items.reduce((acc, it) => {
          const l = it.lens || 'UNKNOWN'; acc[l] = (acc[l] || 0) + 1; return acc;
        }, {} as Record<string, number>),
        sources: [...new Set(items.map(i => i.item_type))],
      });
      // Show first card immediately — question loads async like all others
      const session: SessionCard[] = items.map(item => ({ item, question: null }));
      setCards(session);
      cardShownAt.current = Date.now();
      setState('question');
      // Fire all question generations in parallel
      items.forEach((item, idx) => {
        generateQuestion(item.id).then(q => {
          setCards(prev => {
            const updated = [...prev];
            if (updated[idx]) updated[idx] = { ...updated[idx], question: q };
            return updated;
          });
        });
      });
    } catch (e) {
      console.error('Session load failed:', e);
      setState('done');
    }
  }

  function reveal() {
    if (state !== 'question' || !cards[current]?.question) return;
    revealedAt.current = Date.now();
    setState('revealed');
    const card = cards[current];
    logEvent('review_card_revealed', {
      item_id: card?.item.id,
      lens: card?.item.lens,
      curriculum_node_id: card?.item.curriculum_node_id,
      curriculum_node_title: card?.item.curriculum_node_title,
      chapter: card?.item.source_chapter_title,
      review_count: card?.item.review_count,
      stability_days: card?.item.stability_days,
      time_to_reveal_ms: revealedAt.current - cardShownAt.current,
      card_index: current,
    });
  }

  async function score(s: 'knew' | 'partly' | 'missed') {
    const card = cards[current];
    if (!card) return;
    const nowMs = Date.now();
    logEvent('review_card_scored', {
      item_id: card.item.id,
      score: s,
      lens: card.item.lens,
      curriculum_node_id: card.item.curriculum_node_id,
      curriculum_node_title: card.item.curriculum_node_title,
      chapter: card.item.source_chapter_title,
      item_type: card.item.item_type,
      review_count: card.item.review_count,
      stability_days: card.item.stability_days,
      time_to_reveal_ms: revealedAt.current - cardShownAt.current,
      time_to_score_ms: nowMs - revealedAt.current,
      card_index: current,
      has_temporal_hook: !!card.question?.temporal_hook,
      has_curriculum_context: !!card.question?.curriculum_context,
    });
    await recordAnswer(card.item.id, s).catch(() => {});
    const newScores = [...scores, { id: card.item.id, score: s }];
    setScores(newScores);

    Animated.timing(fadeAnim, { toValue: 0, duration: 150, useNativeDriver: true }).start(() => {
      const nextIdx = current + 1;
      if (nextIdx >= cards.length) {
        setState('done');
      } else {
        setCurrent(nextIdx);
        cardShownAt.current = Date.now();
        const nextCard = cards[nextIdx];
        if (nextCard?.question) {
          setState('question');
        } else {
          setState('loading');
          const checkInterval = setInterval(() => {
            setCards(prev => {
              if (prev[nextIdx]?.question) {
                clearInterval(checkInterval);
                cardShownAt.current = Date.now();
                setState('question');
              }
              return prev;
            });
          }, 300);
        }
      }
      Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    });
  }

  function toggleExpanded(itemId: string) {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) { next.delete(itemId); } else { next.add(itemId); }
      return next;
    });
    logEvent('review_source_expanded', { item_id: itemId });
  }

  async function handleExploreQueue() {
    const card = cards[current];
    if (!card) return;
    const lastScore = scores.find(s => s.id === card.item.id)?.score;
    logEvent('review_explore_tapped', {
      item_id: card.item.id, lens: card.item.lens,
      curriculum_node_id: card.item.curriculum_node_id, after_score: lastScore,
    });
    try {
      const { items_created } = await createExplorationItems(card.item.id);
      const count = items_created?.length || 0;
      setExploreItems(prev => [...prev, card.item.id]);
      Alert.alert('✦ Added to queue', `${count} follow-up question${count !== 1 ? 's' : ''} queued for next session`);
    } catch (e) {
      console.error('Explore failed:', e);
    }
  }

  async function toggleRecording() {
    const card = cards[current];
    if (!card) return;
    if (recording) {
      try {
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();
        setRecording(null);
        setRecordingItem(null);
        if (uri) {
          setProcessingVoice(true);
          logEvent('review_voice_memo_sent', {
            item_id: card.item.id, lens: card.item.lens,
            curriculum_node_id: card.item.curriculum_node_id,
          });
          const result = await sendVoiceMemo(card.item.id, uri).catch(() => null);
          setProcessingVoice(false);
          if (result?.suggested_score) {
            Alert.alert(
              '◎ Voice memo processed',
              `Suggested: ${result.suggested_score}${result.follow_ups_created?.length ? ` · ${result.follow_ups_created.length} follow-ups added` : ''}`,
              [
                { text: `Use "${result.suggested_score}"`, onPress: () => score(result.suggested_score as any) },
                { text: 'Score manually' },
              ]
            );
          } else {
            Alert.alert('◎ Voice memo saved', 'Recorded and saved.');
          }
        }
      } catch (e) {
        setRecording(null);
        setRecordingItem(null);
        setProcessingVoice(false);
      }
    } else {
      try {
        await Audio.requestPermissionsAsync();
        await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
        const { recording: rec } = await Audio.Recording.createAsync(
          Audio.RecordingOptionsPresets.HIGH_QUALITY
        );
        setRecording(rec);
        setRecordingItem(card.item.id);
        logEvent('review_voice_memo_start', {
          item_id: card.item.id, lens: card.item.lens, state_at_record: state,
        });
      } catch (e) {
        console.error('Recording failed:', e);
      }
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (state === 'loading' && cards.length === 0) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator color={colors.rubric} />
        <Text style={styles.loadingText}>Preparing questions…</Text>
      </View>
    );
  }

  if (state === 'done') {
    const knew = scores.filter(s => s.score === 'knew').length;
    const partly = scores.filter(s => s.score === 'partly').length;
    const missed = scores.filter(s => s.score === 'missed').length;
    const sessionDurationMs = Date.now() - sessionStartAt.current;
    const lensScores = scores.reduce((acc, { id, score: s }) => {
      const card = cards.find(c => c.item.id === id);
      const lens = card?.item.lens || 'UNKNOWN';
      if (!acc[lens]) acc[lens] = { knew: 0, partly: 0, missed: 0 };
      acc[lens][s as 'knew' | 'partly' | 'missed']++;
      return acc;
    }, {} as Record<string, { knew: number; partly: number; missed: number }>);
    if (scores.length > 0 && !sessionCompleteLogged.current) {
      sessionCompleteLogged.current = true;
      logEvent('review_session_complete', {
        items_total: scores.length,
        knew,
        partly,
        missed,
        knew_pct: Math.round((knew / scores.length) * 100),
        session_duration_ms: sessionDurationMs,
        explore_tapped_count: exploreItems.length,
        lens_scores: lensScores,
        temporal_hook_cards: cards.filter(c => c.question?.temporal_hook).length,
      });
    }
    return (
      <View style={styles.container}>
        <View style={styles.summaryHeader}>
          <Text style={styles.summaryTitle}>✦ Session complete</Text>
          <View style={styles.doubleRule} />
          <Text style={styles.summaryStats}>
            {knew} knew · {partly} partly · {missed} missed
          </Text>
        </View>
        <ScrollView style={styles.summaryList}>
          {scores.map(({ id, score: s }) => {
            const card = cards.find(c => c.item.id === id);
            return (
              <View key={id} style={styles.summaryRow}>
                <Text style={[styles.summaryIcon, { color: s === 'knew' ? '#2a7a4a' : s === 'partly' ? '#c9a84c' : '#cc4444' }]}>
                  {s === 'knew' ? '✓' : s === 'partly' ? '~' : '✗'}
                </Text>
                <Text style={styles.summaryNodeTitle} numberOfLines={2}>
                  {card?.item.curriculum_node_title || card?.question?.question || id}
                </Text>
              </View>
            );
          })}
        </ScrollView>
        <View style={styles.doneActions}>
          {remainingDue > scores.length && (
            <Pressable style={styles.continueBtn} onPress={loadSession}>
              <Text style={styles.continueBtnText}>
                ✦ Continue · {remainingDue - scores.length} more due
              </Text>
            </Pressable>
          )}
          <Pressable style={styles.doneBtn} onPress={() => router.back()}>
            <Text style={styles.doneBtnText}>Done</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const card = cards[current];
  if (!card) return null;
  const lens = card.item.lens || 'SIGNIFICANCE';
  const [lensColor, lensBg] = LENS_COLORS[lens] || ['#666', '#f5f5f5'];
  const progress = cards.length > 0 ? (current / cards.length) : 0;

  return (
    <View style={styles.container}>
      {/* Progress */}
      <View style={styles.progressOuter}>
        <View style={[styles.progressInner, { width: `${progress * 100}%` as any }]} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        {/* Card */}
        <Animated.View style={[styles.card, { opacity: fadeAnim }]}>
          {/* Chapter + lens badge */}
          <View style={styles.cardMeta}>
            <Text style={styles.cardChapter} numberOfLines={1}>
              {card.item.source_chapter_title || 'Review'}
            </Text>
            <View style={[styles.lensBadge, { backgroundColor: lensBg }]}>
              <Text style={[styles.lensBadgeText, { color: lensColor }]}>
                {LENS_LABELS[lens] || lens}
              </Text>
            </View>
          </View>

          {/* Question */}
          <Pressable onPress={reveal} style={styles.questionArea}>
            {!card.question ? (
              <ActivityIndicator color={colors.textMuted} style={{ marginTop: 20 }} />
            ) : (
              <Text style={styles.questionText}>{card.question.question}</Text>
            )}
            {state === 'question' && card.question && (
              <Text style={styles.tapHint}>tap to reveal</Text>
            )}
          </Pressable>

          {/* Answer (revealed) */}
          {state === 'revealed' && card.question && (
            <>
              <View style={styles.answerDivider} />
              <Text style={styles.answerText}>{card.question.answer_guidance}</Text>

              {card.question.temporal_hook ? (
                <View style={styles.temporalHook}>
                  <Text style={styles.temporalHookText}>✦ {card.question.temporal_hook}</Text>
                </View>
              ) : null}

              {card.question.curriculum_context ? (
                <Text style={styles.curriculumContext}>{card.question.curriculum_context}</Text>
              ) : null}

              {/* Self-assess */}
              <View style={styles.assessRow}>
                <Pressable style={[styles.assessBtn, styles.assessKnew]} onPress={() => score('knew')}>
                  <Text style={[styles.assessBtnText, { color: '#2a7a4a' }]}>✓ Knew it</Text>
                </Pressable>
                <Pressable style={[styles.assessBtn, styles.assessPartly]} onPress={() => score('partly')}>
                  <Text style={[styles.assessBtnText, { color: '#8a6a00' }]}>~ Partly</Text>
                </Pressable>
                <Pressable style={[styles.assessBtn, styles.assessMissed]} onPress={() => score('missed')}>
                  <Text style={[styles.assessBtnText, { color: '#cc4444' }]}>✗ Missed</Text>
                </Pressable>
              </View>

              {/* Source expansion */}
              {card.item.source_text ? (
                <>
                  <Pressable style={styles.sourceToggle} onPress={() => toggleExpanded(card.item.id)}>
                    <Text style={styles.sourceToggleText}>
                      {expandedItems.has(card.item.id) ? '▲ Hide source' : '▼ From the book'}
                    </Text>
                  </Pressable>
                  {expandedItems.has(card.item.id) && (
                    <View style={styles.sourceExpanded}>
                      <Text style={styles.sourceText}>{card.item.source_text}</Text>
                      <Pressable
                        style={[styles.secondaryBtn, exploreItems.includes(card.item.id) && styles.secondaryBtnDone]}
                        onPress={handleExploreQueue}
                        disabled={exploreItems.includes(card.item.id)}
                      >
                        <Text style={styles.secondaryBtnText}>
                          {exploreItems.includes(card.item.id) ? '✦ Follow-ups queued' : '✦ Queue follow-up questions'}
                        </Text>
                      </Pressable>
                    </View>
                  )}
                </>
              ) : null}

              {/* Voice memo */}
              <View style={styles.secondaryRow}>
                <Pressable
                  style={[styles.secondaryBtn, styles.secondaryBtnFull,
                    (recording && recordingItem === card.item.id) && styles.secondaryBtnRecording,
                    processingVoice && styles.secondaryBtnProcessing]}
                  onPress={toggleRecording}
                  disabled={processingVoice}
                >
                  <Text style={styles.secondaryBtnText}>
                    {processingVoice ? '◎ Processing…'
                      : recording && recordingItem === card.item.id ? '◎ Tap to stop recording'
                      : '◎ Voice memo'}
                  </Text>
                </Pressable>
              </View>
            </>
          )}
        </Animated.View>

        {/* Counter */}
        <Text style={styles.counter}>{current + 1} / {cards.length}</Text>
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
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 13, color: colors.textMuted, marginTop: 12,
  },

  card: {
    backgroundColor: 'white', borderWidth: 1, borderColor: colors.rule,
    borderRadius: 4, padding: 20, marginBottom: 12,
  },
  cardMeta: { flexDirection: 'row', alignItems: 'center', marginBottom: 14, gap: 8 },
  cardChapter: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.06, flex: 1,
  },
  lensBadge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 2 },
  lensBadgeText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 10, fontWeight: '500', letterSpacing: 0.06, textTransform: 'uppercase',
  },
  questionArea: { minHeight: 80, paddingBottom: 12 },
  questionText: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 20, lineHeight: 28, color: colors.ink,
  },
  tapHint: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 11, color: colors.textMuted, marginTop: 16, textAlign: 'center',
  },

  answerDivider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.rule, marginVertical: 14 },
  answerText: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro_400Regular' }),
    fontSize: 16, lineHeight: 24, color: colors.textBody, marginBottom: 12,
  },
  temporalHook: {
    borderLeftWidth: 2, borderLeftColor: colors.rubric,
    paddingLeft: 12, paddingVertical: 8, marginBottom: 12,
    backgroundColor: colors.parchment,
  },
  temporalHookText: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro_400Regular' }),
    fontSize: 14, fontStyle: 'italic', color: colors.textSecondary,
  },
  curriculumContext: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 12, color: colors.textMuted, marginBottom: 12, fontStyle: 'italic',
  },

  assessRow: { flexDirection: 'row', gap: 8, marginTop: 4, marginBottom: 12 },
  assessBtn: { flex: 1, paddingVertical: 10, borderRadius: 3, borderWidth: 1, alignItems: 'center' },
  assessKnew: { borderColor: '#2a7a4a', backgroundColor: '#f0faf4' },
  assessPartly: { borderColor: '#c9a84c', backgroundColor: '#fffbee' },
  assessMissed: { borderColor: '#cc4444', backgroundColor: '#fff5f5' },
  assessBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 13, fontWeight: '500',
  },

  sourceToggle: { paddingVertical: 8, marginTop: 4 },
  sourceToggleText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 11, color: colors.textMuted, letterSpacing: 0.04,
  },
  sourceExpanded: {
    borderLeftWidth: 2, borderLeftColor: colors.rule,
    paddingLeft: 12, marginBottom: 12,
  },
  sourceText: {
    fontFamily: Platform.select({ web: "'Crimson Pro', Georgia, serif", default: 'CrimsonPro_400Regular' }),
    fontSize: 14, lineHeight: 21, color: colors.textSecondary, marginBottom: 10,
  },

  secondaryRow: { marginTop: 4 },
  secondaryBtn: {
    paddingVertical: 8, borderRadius: 3,
    borderWidth: 1, borderColor: colors.rule, alignItems: 'center',
    marginBottom: 6,
  },
  secondaryBtnFull: { width: '100%' },
  secondaryBtnDone: { borderColor: colors.rubric },
  secondaryBtnRecording: { borderColor: '#cc4444', backgroundColor: '#fff5f5' },
  secondaryBtnProcessing: { borderColor: colors.textMuted, backgroundColor: colors.parchment },
  secondaryBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 12, color: colors.textSecondary,
  },

  counter: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 12, color: colors.textMuted, textAlign: 'center', marginTop: 4,
  },

  // Summary
  summaryHeader: { paddingHorizontal: 16, paddingTop: Platform.OS === 'ios' ? 56 : 16 },
  summaryTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 22, fontWeight: '600', color: colors.ink, marginBottom: 6,
  },
  doubleRule: {
    height: 5, backgroundColor: 'transparent',
    borderTopWidth: 2, borderTopColor: colors.rubric,
    borderBottomWidth: 1, borderBottomColor: colors.rubric,
    marginBottom: 10,
  },
  summaryStats: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
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
  doneActions: { paddingHorizontal: 16, paddingBottom: 16, gap: 8 },
  continueBtn: {
    paddingVertical: 13, borderRadius: 3,
    backgroundColor: colors.rubric, alignItems: 'center',
  },
  continueBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 14, color: 'white', fontWeight: '500',
  },
  doneBtn: {
    paddingVertical: 12, borderRadius: 3,
    borderWidth: 1, borderColor: colors.rule, alignItems: 'center',
  },
  doneBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 14, color: colors.textMuted, fontWeight: '500',
  },
});
