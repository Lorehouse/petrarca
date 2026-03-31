import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Animated, Platform, Pressable,
  ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { colors, fonts, layout } from '../design/tokens';
import { HamarquizenCard, getHamarquizenSession, getCrossBookHamarquizen, recordAnswer } from '../lib/review-api';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';
import DoubleRule from '../components/DoubleRule';

type Phase = 'loading' | 'prime' | 'read' | 'test' | 'revealed' | 'done';

export default function HamarquizenScreen() {
  const router = useRouter();
  const { book_id, mode } = useLocalSearchParams<{ book_id: string; mode?: string }>();
  const isCrossMode = mode === 'cross';
  const [cards, setCards] = useState<HamarquizenCard[]>([]);
  const [current, setCurrent] = useState(0);
  const [phase, setPhase] = useState<Phase>('loading');
  const [scores, setScores] = useState<Array<{ id: string; score: string }>>([]);
  const fadeAnim = useRef(new Animated.Value(1)).current;
  const sessionStartAt = useRef(Date.now());
  const phaseStartAt = useRef(Date.now());
  const sessionCompleteLogged = useRef(false);

  useEffect(() => {
    setFeedbackContext({ screen: 'hamarquizen', extra: { bookId: book_id, mode } });
    loadSession();
  }, [book_id, mode]);

  async function loadSession() {
    if (!isCrossMode && !book_id) { setPhase('done'); return; }
    setPhase('loading');
    setScores([]);
    setCurrent(0);
    sessionStartAt.current = Date.now();
    sessionCompleteLogged.current = false;
    try {
      const { cards: c } = isCrossMode
        ? await getCrossBookHamarquizen(5)
        : await getHamarquizenSession(book_id, 5);
      if (c.length === 0) { setPhase('done'); return; }
      setCards(c);
      phaseStartAt.current = Date.now();
      setPhase('prime');
      logEvent('hamarquizen_session_loaded', { book_id, mode: mode || 'book', card_count: c.length });
    } catch (e) {
      console.error('Hamarquizen load failed:', e);
      setPhase('done');
    }
  }

  function advancePhase() {
    const now = Date.now();
    if (phase === 'prime') {
      logEvent('hamarquizen_prime_read', {
        item_id: cards[current]?.item_id,
        time_ms: now - phaseStartAt.current,
      });
      phaseStartAt.current = now;
      setPhase('read');
    } else if (phase === 'read') {
      logEvent('hamarquizen_read_done', {
        item_id: cards[current]?.item_id,
        time_ms: now - phaseStartAt.current,
      });
      phaseStartAt.current = now;
      setPhase('test');
    } else if (phase === 'test') {
      logEvent('hamarquizen_test_revealed', {
        item_id: cards[current]?.item_id,
        time_ms: now - phaseStartAt.current,
      });
      phaseStartAt.current = now;
      setPhase('revealed');
    }
  }

  async function score(s: 'knew' | 'partly' | 'missed') {
    const card = cards[current];
    if (!card) return;
    logEvent('hamarquizen_scored', {
      item_id: card.item_id, score: s, node_title: card.node_title,
      book_id: card.book_id, card_index: current,
    });
    await recordAnswer(card.item_id, s).catch(() => {});
    const newScores = [...scores, { id: card.item_id, score: s }];
    setScores(newScores);

    Animated.timing(fadeAnim, { toValue: 0, duration: 150, useNativeDriver: true }).start(() => {
      const nextIdx = current + 1;
      if (nextIdx >= cards.length) {
        setPhase('done');
      } else {
        setCurrent(nextIdx);
        phaseStartAt.current = Date.now();
        setPhase('prime');
      }
      Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }).start();
    });
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (phase === 'loading') {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator color={colors.rubric} />
        <Text style={styles.loadingText}>Preparing micro-lessons...</Text>
      </View>
    );
  }

  if (phase === 'done') {
    const knew = scores.filter(s => s.score === 'knew').length;
    const partly = scores.filter(s => s.score === 'partly').length;
    const missed = scores.filter(s => s.score === 'missed').length;
    if (scores.length > 0 && !sessionCompleteLogged.current) {
      sessionCompleteLogged.current = true;
      logEvent('hamarquizen_session_complete', {
        book_id, card_count: scores.length, knew, partly, missed,
        session_duration_ms: Date.now() - sessionStartAt.current,
      });
    }
    return (
      <View style={styles.container}>
        <View style={styles.summaryHeader}>
          <Text style={styles.summaryTitle}>{'\u2726'} Session complete</Text>
          <DoubleRule />
          {scores.length > 0 ? (
            <Text style={styles.summaryStats}>
              {knew} knew {'\u00B7'} {partly} partly {'\u00B7'} {missed} missed
            </Text>
          ) : (
            <Text style={styles.summaryStats}>No review items found for this book.</Text>
          )}
        </View>
        <ScrollView style={styles.summaryList}>
          {scores.map(({ id, score: s }) => {
            const card = cards.find(c => c.item_id === id);
            return (
              <View key={id} style={styles.summaryRow}>
                <Text style={[styles.summaryIcon, {
                  color: s === 'knew' ? '#2a7a4a' : s === 'partly' ? '#c9a84c' : '#cc4444',
                }]}>
                  {s === 'knew' ? '\u2713' : s === 'partly' ? '~' : '\u2717'}
                </Text>
                <Text style={styles.summaryNodeTitle} numberOfLines={2}>
                  {card?.node_title || id}
                </Text>
              </View>
            );
          })}
        </ScrollView>
        <View style={styles.doneActions}>
          <Pressable style={styles.doneBtn} onPress={() => router.back()}>
            <Text style={styles.doneBtnText}>Done</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const card = cards[current];
  if (!card) return null;
  const progress = cards.length > 0 ? (current / cards.length) : 0;

  return (
    <View style={styles.container}>
      {/* Progress */}
      <View style={styles.progressOuter}>
        <View style={[styles.progressInner, { width: `${progress * 100}%` as any }]} />
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <Animated.View style={[styles.card, { opacity: fadeAnim }]}>
          {/* Meta */}
          <View style={styles.cardMeta}>
            <Text style={styles.cardBook} numberOfLines={1}>
              {isCrossMode && (card as any).book_b_title
                ? `${card.book_title} \u00D7 ${(card as any).book_b_title}`
                : card.book_title}
            </Text>
            <Text style={styles.cardNode} numberOfLines={1}>{card.node_title}</Text>
          </View>

          {/* PRIME */}
          {(phase === 'prime' || phase === 'read' || phase === 'test' || phase === 'revealed') && (
            <Pressable onPress={phase === 'prime' ? advancePhase : undefined}>
              <Text style={styles.primeText}>{card.prime}</Text>
              {phase === 'prime' && (
                <Text style={styles.tapHint}>tap to read</Text>
              )}
            </Pressable>
          )}

          {/* READ */}
          {(phase === 'read' || phase === 'test' || phase === 'revealed') && (
            <>
              <View style={styles.readDivider} />
              <Pressable
                style={styles.readSection}
                onPress={phase === 'read' ? advancePhase : undefined}
              >
                <Text style={styles.readText}>{card.read}</Text>
                {phase === 'read' && (
                  <Text style={styles.tapHint}>tap for the question</Text>
                )}
              </Pressable>
            </>
          )}

          {/* TEST */}
          {(phase === 'test' || phase === 'revealed') && (
            <>
              <View style={styles.answerDivider} />
              <Pressable onPress={phase === 'test' ? advancePhase : undefined}>
                <Text style={styles.testText}>{card.test}</Text>
                {phase === 'test' && (
                  <Text style={styles.tapHint}>tap to reveal answer</Text>
                )}
              </Pressable>
            </>
          )}

          {/* REVEALED: answer + scoring + temporal hook */}
          {phase === 'revealed' && (
            <>
              <View style={styles.answerDivider} />
              <Text style={styles.answerText}>{card.answer}</Text>

              {/* Self-assess */}
              <View style={styles.assessRow}>
                <Pressable style={[styles.assessBtn, styles.assessKnew]} onPress={() => score('knew')}>
                  <Text style={[styles.assessBtnText, { color: '#2a7a4a' }]}>{'\u2713'} Knew it</Text>
                </Pressable>
                <Pressable style={[styles.assessBtn, styles.assessPartly]} onPress={() => score('partly')}>
                  <Text style={[styles.assessBtnText, { color: '#8a6a00' }]}>~ Partly</Text>
                </Pressable>
                <Pressable style={[styles.assessBtn, styles.assessMissed]} onPress={() => score('missed')}>
                  <Text style={[styles.assessBtnText, { color: '#cc4444' }]}>{'\u2717'} Missed</Text>
                </Pressable>
              </View>

              {/* Temporal hook */}
              {card.temporal_hook ? (
                <View style={styles.temporalHook}>
                  <Text style={styles.temporalHookText}>{'\u2726'} {card.temporal_hook}</Text>
                </View>
              ) : null}
            </>
          )}
        </Animated.View>

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
    fontFamily: fonts.ui, fontSize: 13, color: colors.textMuted, marginTop: 12,
  },

  card: {
    backgroundColor: 'white', borderWidth: 1, borderColor: colors.rule,
    borderRadius: 4, padding: 20, marginBottom: 12,
  },
  cardMeta: { marginBottom: 14, gap: 2 },
  cardBook: {
    fontFamily: fonts.ui, fontSize: 11, color: colors.rubric,
    textTransform: 'uppercase', letterSpacing: 0.06, fontWeight: '500',
    ...(Platform.OS === 'web' ? {} : {}),
  },
  cardNode: {
    fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, letterSpacing: 0.04,
  },

  primeText: {
    fontFamily: fonts.readingItalic, fontSize: 17, lineHeight: 25, color: colors.ink,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  tapHint: {
    fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, marginTop: 16, textAlign: 'center',
  },

  readDivider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.rule, marginVertical: 14 },
  readSection: {
    borderLeftWidth: 2, borderLeftColor: colors.rubric,
    paddingLeft: 14, paddingVertical: 4,
  },
  readText: {
    fontFamily: fonts.reading, fontSize: 16, lineHeight: 25, color: colors.textBody,
  },

  answerDivider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.rule, marginVertical: 14 },
  testText: {
    fontFamily: fonts.body, fontSize: 20, lineHeight: 28, color: colors.ink,
  },

  answerText: {
    fontFamily: fonts.reading, fontSize: 16, lineHeight: 24, color: colors.textBody, marginBottom: 12,
  },

  assessRow: { flexDirection: 'row', gap: 8, marginTop: 4, marginBottom: 12 },
  assessBtn: { flex: 1, paddingVertical: 10, borderRadius: 3, borderWidth: 1, alignItems: 'center' },
  assessKnew: { borderColor: '#2a7a4a', backgroundColor: '#f0faf4' },
  assessPartly: { borderColor: '#c9a84c', backgroundColor: '#fffbee' },
  assessMissed: { borderColor: '#cc4444', backgroundColor: '#fff5f5' },
  assessBtnText: { fontFamily: fonts.ui, fontSize: 13, fontWeight: '500' },

  temporalHook: {
    borderLeftWidth: 2, borderLeftColor: colors.rubric,
    paddingLeft: 12, paddingVertical: 8, marginBottom: 4,
    backgroundColor: colors.parchment,
  },
  temporalHookText: {
    fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textSecondary,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },

  counter: {
    fontFamily: fonts.ui, fontSize: 12, color: colors.textMuted, textAlign: 'center', marginTop: 4,
  },

  // Summary
  summaryHeader: { paddingHorizontal: 16, paddingTop: Platform.OS === 'ios' ? 56 : 16 },
  summaryTitle: {
    fontFamily: fonts.displaySemiBold, fontSize: 22, color: colors.ink, marginBottom: 6,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  summaryStats: {
    fontFamily: fonts.ui, fontSize: 14, color: colors.textSecondary, marginTop: 10, marginBottom: 16,
  },
  summaryList: { flex: 1, paddingHorizontal: 16 },
  summaryRow: {
    flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule,
  },
  summaryIcon: { fontSize: 16, marginRight: 10, width: 20 },
  summaryNodeTitle: {
    fontFamily: fonts.body, fontSize: 15, color: colors.textBody, flex: 1,
  },
  doneActions: { paddingHorizontal: 16, paddingBottom: 16, gap: 8 },
  doneBtn: {
    paddingVertical: 12, borderRadius: 3,
    borderWidth: 1, borderColor: colors.rule, alignItems: 'center',
  },
  doneBtnText: {
    fontFamily: fonts.ui, fontSize: 14, color: colors.textMuted, fontWeight: '500',
  },
});
