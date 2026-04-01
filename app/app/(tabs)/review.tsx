import React, { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator, Animated, Platform, Pressable, ScrollView,
  StyleSheet, Text, View,
} from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { colors, fonts, layout } from '../../design/tokens';
import { EntitySpan, ResurfacingItem, ReviewStreamResponse } from '../../data/types';
import {
  fetchReviewStream, recordReviewResult, recordEntityTap,
} from '../../lib/book-api';
import { logEvent } from '../../data/logger';
import { setFeedbackContext } from '../../lib/feedback-context';
import PetrarcaDrawer from '../../components/PetrarcaDrawer';
import DoubleRule from '../../components/DoubleRule';
import EntitySheet from '../../components/EntitySheet';
import AncientMap from '../../components/AncientMap';

// ── Annotated Text (tappable entity spans) ──────────────────────────

function AnnotatedText({
  text,
  spans,
  style,
  onEntityTap,
}: {
  text: string;
  spans?: EntitySpan[];
  style: any;
  onEntityTap: (entityId: string) => void;
}) {
  if (!spans || spans.length === 0) {
    return <Text style={style}>{text}</Text>;
  }

  const parts: React.ReactNode[] = [];
  let cursor = 0;

  for (const span of spans) {
    if (span.start > cursor) {
      parts.push(<Text key={`t-${cursor}`}>{text.slice(cursor, span.start)}</Text>);
    }
    parts.push(
      <Text
        key={`e-${span.start}`}
        style={entityStyle.tappable}
        onPress={() => onEntityTap(span.entity_id)}
      >
        {text.slice(span.start, span.end)}
      </Text>
    );
    cursor = span.end;
  }
  if (cursor < text.length) {
    parts.push(<Text key={`t-${cursor}`}>{text.slice(cursor)}</Text>);
  }

  return <Text style={style}>{parts}</Text>;
}

const entityStyle = StyleSheet.create({
  tappable: {
    textDecorationLine: 'underline',
    textDecorationStyle: 'dotted',
    textDecorationColor: colors.textMuted,
  },
});

// ── Review Card ─────────────────────────────────────────────────────

function ReviewCard({
  item,
  onResult,
  onSkip,
  onEntityTap,
}: {
  item: ResurfacingItem;
  onResult: (result: string) => void;
  onSkip: () => void;
  onEntityTap: (entityId: string) => void;
}) {
  const [revealed, setRevealed] = useState(false);
  const [graded, setGraded] = useState(false);

  const answerType = item.answer_type || 'concept';
  const typeLabel = answerType === 'date' ? 'Date'
    : answerType === 'name' ? 'Identity'
    : answerType === 'sequence' ? 'Timeline'
    : 'Concept';

  // Domain label — short readable name
  const domainLabel = (item.domain || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .slice(0, 40);

  const gradingButtons = [
    { value: 'knew', label: 'Knew it', style: 'correct' as const },
    { value: 'partly', label: 'Partly', style: 'partial' as const },
    { value: 'missed', label: 'Missed', style: 'wrong' as const },
  ];

  const handleGrade = (result: string) => {
    onResult(result);
    setGraded(true);
  };

  if (graded) {
    return (
      <View style={cs.card}>
        <Text style={cs.responded}>Recorded {'\u2713'}</Text>
      </View>
    );
  }

  const displayAnswer = item.rich_answer || item.answer || '';
  const anchors = item.anchors || [];

  return (
    <View style={cs.card}>
      {/* Header: type badge + domain */}
      <View style={cs.headerRow}>
        <View style={cs.typeBadge}>
          <Text style={cs.typeBadgeText}>{typeLabel}</Text>
        </View>
        <Text style={cs.domainLabel} numberOfLines={1}>{domainLabel}</Text>
      </View>

      {/* Node title (context) */}
      {revealed && item.node_title ? (
        <Text style={cs.nodeTitle}>{item.node_title}</Text>
      ) : null}

      {/* Question */}
      <Text style={cs.question}>{item.question}</Text>

      {/* Reveal / Answer */}
      {!revealed ? (
        <View style={cs.actionRow}>
          <Pressable style={cs.revealButton} onPress={() => setRevealed(true)}>
            <Text style={cs.revealText}>Show answer</Text>
          </Pressable>
          <Pressable style={cs.skipButton} onPress={onSkip}>
            <Text style={cs.skipText}>Skip {'\u2192'}</Text>
          </Pressable>
        </View>
      ) : (
        <View>
          {/* Rich answer */}
          <View style={cs.answerBox}>
            <AnnotatedText
              text={displayAnswer}
              spans={item.entity_spans?.rich_answer}
              style={cs.answerText}
              onEntityTap={onEntityTap}
            />
          </View>

          {/* Memory hook */}
          {item.memory_hook ? (
            <View style={cs.hookBox}>
              <Text style={cs.hookLabel}>{'\u2726'} Memory hook</Text>
              <AnnotatedText
                text={item.memory_hook}
                spans={item.entity_spans?.memory_hook}
                style={cs.hookText}
                onEntityTap={onEntityTap}
              />
            </View>
          ) : null}

          {/* Temporal anchors */}
          {anchors.length > 0 ? (
            <View style={cs.anchorBox}>
              {anchors.map((a, i) => (
                <Text key={i} style={cs.anchorText}>{'\u2022'} {a}</Text>
              ))}
            </View>
          ) : null}

          {/* Curriculum context */}
          {item.curriculum_context ? (
            <Text style={cs.contextText}>{item.curriculum_context}</Text>
          ) : null}

          {/* Place entity map links */}
          {(() => {
            const allSpans = Object.values(item.entity_spans || {}).flat();
            const places = allSpans.filter(sp => sp.entity_type === 'place');
            const seen = new Set<string>();
            const unique = places.filter(sp => {
              if (seen.has(sp.entity_id)) return false;
              seen.add(sp.entity_id);
              return true;
            });
            if (unique.length === 0) return null;
            return (
              <View style={cs.mapLinkRow}>
                {unique.map(sp => (
                  <Pressable key={sp.entity_id} onPress={() => onEntityTap(sp.entity_id)}>
                    <Text style={cs.mapLinkText}>{'\uD83D\uDCCD'} {sp.name}</Text>
                  </Pressable>
                ))}
              </View>
            );
          })()}

          {/* Grading buttons */}
          <View style={cs.gradeRow}>
            {gradingButtons.map(btn => {
              const btnStyle = btn.style === 'correct' ? cs.gradeCorrect
                : btn.style === 'partial' ? cs.gradePartial
                : cs.gradeWrong;
              const txtStyle = btn.style === 'correct' ? cs.gradeCorrectText
                : btn.style === 'partial' ? cs.gradePartialText
                : cs.gradeWrongText;
              return (
                <Pressable
                  key={btn.value}
                  style={[cs.gradeButton, btnStyle]}
                  onPress={() => handleGrade(btn.value)}
                >
                  <Text style={txtStyle}>{btn.label}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>
      )}
    </View>
  );
}

// ── Entity Intro Card ────────────────────────────────────────────────

const INTRO_TYPE_LABELS: Record<string, string> = {
  place: '\uD83D\uDCCD Place',
  person: '\uD83D\uDC64 Person',
  event: '\u26A1 Event',
  period: '\uD83D\uDD51 Period',
};

function EntityIntroCard({
  item,
  onContinue,
}: {
  item: ResurfacingItem;
  onContinue: () => void;
}) {
  const [continued, setContinued] = useState(false);

  const formatYear = (y: number | null | undefined) => {
    if (y == null) return '';
    return y < 0 ? `${Math.abs(y)} BC` : `${y} AD`;
  };

  const handleContinue = () => {
    setContinued(true);
    if (item.entity_id) {
      recordEntityTap(item.entity_id, 'encountered').catch(() => {});
      logEvent('entity_intro_seen', { entity_id: item.entity_id });
    }
    setTimeout(onContinue, 400);
  };

  if (continued) {
    return (
      <View style={cs.card}>
        <Text style={cs.responded}>Noted {'\u2713'}</Text>
      </View>
    );
  }

  const dateStr = item.date_start != null
    ? `${formatYear(item.date_start)}${item.date_end != null ? ` \u2013 ${formatYear(item.date_end)}` : ''}`
    : null;

  return (
    <View style={cs.card}>
      <View style={cs.headerRow}>
        {item.entity_type && (
          <View style={ic.introBadge}>
            <Text style={ic.introBadgeText}>
              {INTRO_TYPE_LABELS[item.entity_type] || item.entity_type}
            </Text>
          </View>
        )}
        <Text style={ic.introLabel}>Entity briefing</Text>
      </View>

      <Text style={ic.entityName}>{item.entity_name}</Text>
      {item.modern_name && item.modern_name !== item.entity_name ? (
        <Text style={ic.modernName}>Modern: {item.modern_name}</Text>
      ) : null}

      {item.entity_type === 'place' && item.latitude != null && item.longitude != null ? (
        <View style={ic.miniMapWrap}>
          <AncientMap
            entities={[{
              entity_id: item.entity_id || '',
              name: item.entity_name || '',
              entity_type: 'place',
              latitude: item.latitude,
              longitude: item.longitude,
              aliases: [],
              nexus_score: 0,
              curriculum_links: [],
            }]}
            center={[item.latitude, item.longitude]}
            zoom={7}
            tileLayer="clean"
            showControls={false}
            showTimeline={false}
            showFilters={false}
            showLegend={false}
            showEntitySheet={false}
            style={{ height: 140 }}
          />
        </View>
      ) : null}

      {item.description ? (
        <Text style={ic.description}>{item.description}</Text>
      ) : null}

      {dateStr ? (
        <Text style={ic.dateFact}>{'\u2022'} {dateStr}</Text>
      ) : null}

      <Pressable style={ic.continueBtn} onPress={handleContinue}>
        <Text style={ic.continueText}>Continue {'\u2192'}</Text>
      </Pressable>
    </View>
  );
}

// ── Main Screen ─────────────────────────────────────────────────────

type Tab = 'cards' | 'voice';

export default function ReviewScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>('cards');
  const [items, setItems] = useState<ResurfacingItem[]>([]);
  const [streamMeta, setStreamMeta] = useState<Partial<ReviewStreamResponse>>({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeEntityId, setActiveEntityId] = useState<string | null>(null);
  const offsetRef = useRef(0);
  const fadeAnim = useRef(new Animated.Value(1)).current;

  const loadStream = useCallback(async (reset = true) => {
    if (reset) {
      setLoading(true);
      setError('');
      offsetRef.current = 0;
    } else {
      setLoadingMore(true);
    }
    try {
      const result = await fetchReviewStream({
        limit: 20,
        offset: offsetRef.current,
      });
      if (reset) {
        setItems(result.items);
        setCurrentIndex(0);
      } else {
        setItems(prev => [...prev, ...result.items]);
      }
      setStreamMeta(result);
      offsetRef.current += result.items.length;
      logEvent('review_stream_loaded', {
        item_count: result.items.length,
        total_candidates: result.total_candidates,
        due_count: result.due_count,
        offset: offsetRef.current,
      });
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useFocusEffect(useCallback(() => {
    setFeedbackContext({ screen: 'review' });
    if (tab === 'cards') loadStream(true);
  }, [tab]));

  // Auto-load more when nearing end of items
  const maybeLoadMore = useCallback(() => {
    if (currentIndex >= items.length - 3 && streamMeta.has_more && !loadingMore) {
      loadStream(false);
    }
  }, [currentIndex, items.length, streamMeta.has_more, loadingMore]);

  const animateTransition = useCallback((callback: () => void) => {
    Animated.timing(fadeAnim, {
      toValue: 0,
      duration: 150,
      useNativeDriver: true,
    }).start(() => {
      callback();
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
    });
  }, [fadeAnim]);

  const handleResult = async (item: ResurfacingItem, result: string) => {
    if (item.question_id) {
      recordReviewResult(item.question_id, result).catch(e =>
        console.warn('[review] score failed:', e));
      logEvent('review_result', {
        question_id: item.question_id,
        result,
        answer_type: item.answer_type,
        domain: item.domain,
        node_title: item.node_title,
        review_count: item.review_count,
      });
    }
    setTimeout(() => {
      animateTransition(() => {
        setCurrentIndex(i => i + 1);
        maybeLoadMore();
      });
    }, 500);
  };

  const handleSkip = (item: ResurfacingItem) => {
    logEvent('review_skip', {
      question_id: item.question_id,
      domain: item.domain,
      node_title: item.node_title,
    });
    animateTransition(() => {
      setCurrentIndex(i => i + 1);
      maybeLoadMore();
    });
  };

  const handleEntityIntroContinue = () => {
    animateTransition(() => {
      setCurrentIndex(i => i + 1);
      maybeLoadMore();
    });
  };

  const currentItem = items[currentIndex];
  const reviewedCount = currentIndex;
  const dueCount = streamMeta.due_count ?? 0;
  const totalCandidates = streamMeta.total_candidates ?? 0;
  const domainCount = Object.keys(streamMeta.domain_counts || {}).length;

  return (
    <View style={s.container}>
      <ScrollView contentContainerStyle={s.content}>
        {/* Header */}
        <View style={s.header}>
          <View style={s.titleRow}>
            <Text style={s.screenTitle}>Review</Text>
            <Pressable onPress={() => setDrawerOpen(true)} style={s.drawerBtn}>
              <Text style={s.drawerBtnText}>{'\u2726'}</Text>
            </Pressable>
          </View>
          <DoubleRule />

          {/* Tab switcher */}
          <View style={s.tabRow}>
            <Pressable
              style={[s.tabBtn, tab === 'cards' && s.tabBtnActive]}
              onPress={() => setTab('cards')}
            >
              <Text style={[s.tabText, tab === 'cards' && s.tabTextActive]}>Cards</Text>
            </Pressable>
            <Pressable
              style={[s.tabBtn, tab === 'voice' && s.tabBtnActive]}
              onPress={() => setTab('voice')}
            >
              <Text style={[s.tabText, tab === 'voice' && s.tabTextActive]}>Voice</Text>
            </Pressable>
          </View>

          {tab === 'cards' && !loading && (
            <Text style={s.statsLine}>
              {reviewedCount > 0 ? `${reviewedCount} reviewed  \u00b7  ` : ''}
              {dueCount} due  \u00b7  {totalCandidates} in pool  \u00b7  {domainCount} curricula
            </Text>
          )}
        </View>

        {/* ── Cards tab ────────────────────────────────────────── */}
        {tab === 'cards' && (
          <>
            {loading && (
              <View style={s.loadingContainer}>
                <ActivityIndicator size="small" color={colors.rubric} />
                <Text style={s.loadingText}>Loading review...</Text>
              </View>
            )}

            {error ? <Text style={s.errorText}>{error}</Text> : null}

            {!loading && items.length === 0 && (
              <View style={s.emptyState}>
                <Text style={s.emptyTitle}>{'\u2726'} All caught up</Text>
                <Text style={s.emptySubtitle}>
                  No review items yet. Read more books and articles to build your review pool!
                </Text>
              </View>
            )}

            {currentItem && (
              <Animated.View style={{ opacity: fadeAnim }}>
                {currentItem.type === 'entity_intro' ? (
                  <EntityIntroCard
                    key={`intro-${currentItem.entity_id || currentIndex}`}
                    item={currentItem}
                    onContinue={handleEntityIntroContinue}
                  />
                ) : (
                  <ReviewCard
                    key={currentItem.question_id || `q-${currentIndex}`}
                    item={currentItem}
                    onResult={(result) => handleResult(currentItem, result)}
                    onSkip={() => handleSkip(currentItem)}
                    onEntityTap={setActiveEntityId}
                  />
                )}
              </Animated.View>
            )}

            {!loading && !currentItem && items.length > 0 && (
              <View style={s.emptyState}>
                <Text style={s.emptyTitle}>{'\u2726'} End of stream</Text>
                <Text style={s.emptySubtitle}>{reviewedCount} cards reviewed</Text>
                <Pressable style={s.newSessionBtn} onPress={() => loadStream(true)}>
                  <Text style={s.newSessionText}>Refresh</Text>
                </Pressable>
              </View>
            )}

            {loadingMore && (
              <View style={s.loadingMoreRow}>
                <ActivityIndicator size="small" color={colors.textMuted} />
              </View>
            )}
          </>
        )}

        {/* ── Voice tab ────────────────────────────────────────── */}
        {tab === 'voice' && (
          <View style={s.voiceSection}>
            <Text style={s.voiceTitle}>{'\u2726'} Voice Recall</Text>
            <Text style={s.voiceDesc}>
              Speak freely about a curriculum topic. The system will analyze what you
              remembered, identify gaps, and capture any questions for research.
            </Text>
            <Pressable
              style={s.voiceLaunchBtn}
              onPress={() => router.push('/voice-elicitation')}
            >
              <Text style={s.voiceLaunchText}>Start free recall {'\u2192'}</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>

      <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <EntitySheet entityId={activeEntityId} onClose={() => setActiveEntityId(null)} />
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────────

const cs = StyleSheet.create({
  card: {
    marginHorizontal: layout.screenPadding, marginBottom: 20, paddingVertical: 16,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule,
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  typeBadge: { backgroundColor: colors.ink, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 2 },
  typeBadgeText: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.parchment, textTransform: 'uppercase', letterSpacing: 0.5, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  domainLabel: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, flex: 1 },
  nodeTitle: { fontFamily: fonts.bodyItalic, fontSize: 12, color: colors.textSecondary, marginBottom: 8, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  question: { fontFamily: fonts.reading, fontSize: 18, lineHeight: 26, color: colors.ink, marginBottom: 16 },
  actionRow: { flexDirection: 'row', gap: 10 },
  revealButton: { flex: 1, borderWidth: 1, borderColor: colors.rubric, borderRadius: 4, paddingVertical: 12, alignItems: 'center' },
  revealText: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  skipButton: { paddingHorizontal: 16, paddingVertical: 12, borderRadius: 4, alignItems: 'center', justifyContent: 'center' },
  skipText: { fontFamily: fonts.ui, fontSize: 13, color: colors.textMuted },
  answerBox: { borderLeftWidth: 3, borderLeftColor: colors.claimNew, paddingLeft: 14, marginBottom: 14 },
  answerText: { fontFamily: fonts.reading, fontSize: 15, lineHeight: 22, color: colors.textBody },
  hookBox: { backgroundColor: 'rgba(139,37,0,0.04)', borderLeftWidth: 2, borderLeftColor: colors.rubric, paddingLeft: 12, paddingVertical: 8, marginBottom: 12, borderRadius: 2 },
  hookLabel: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.rubric, letterSpacing: 0.3, marginBottom: 4, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  hookText: { fontFamily: fonts.readingItalic, fontSize: 14, lineHeight: 20, color: colors.textBody, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  anchorBox: { marginBottom: 14 },
  anchorText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary, lineHeight: 18, marginBottom: 2 },
  contextText: { fontFamily: fonts.readingItalic, fontSize: 12, lineHeight: 18, color: colors.textMuted, marginBottom: 14, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  mapLinkRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 14 },
  mapLinkText: { fontFamily: fonts.ui, fontSize: 13, color: colors.info, textDecorationLine: 'underline' },
  gradeRow: { flexDirection: 'row', gap: 8 },
  gradeButton: { flex: 1, paddingVertical: 10, borderRadius: 4, alignItems: 'center', borderWidth: 1 },
  gradeCorrect: { borderColor: colors.claimNew, backgroundColor: 'rgba(42,122,74,0.05)' },
  gradeCorrectText: { fontFamily: fonts.ui, fontSize: 12, color: colors.claimNew },
  gradePartial: { borderColor: colors.textMuted, backgroundColor: 'rgba(176,168,152,0.08)' },
  gradePartialText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary },
  gradeWrong: { borderColor: colors.rubric, backgroundColor: 'rgba(139,37,0,0.05)' },
  gradeWrongText: { fontFamily: fonts.ui, fontSize: 12, color: colors.rubric },
  responded: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.claimNew, textAlign: 'center', paddingVertical: 12, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
});

const ic = StyleSheet.create({
  introBadge: { backgroundColor: '#b8860b', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 2 },
  introBadgeText: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.parchment, textTransform: 'uppercase', letterSpacing: 0.5, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  introLabel: { fontFamily: fonts.readingItalic, fontSize: 11, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  entityName: { fontFamily: fonts.displaySemiBold, fontSize: 24, color: colors.ink, marginBottom: 2, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  modernName: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textSecondary, marginBottom: 8, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  miniMapWrap: { height: 140, borderRadius: 8, overflow: 'hidden', marginBottom: 14, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.rule },
  description: { fontFamily: fonts.reading, fontSize: 15, lineHeight: 22, color: colors.textBody, marginBottom: 12 },
  dateFact: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary, lineHeight: 18, marginBottom: 10 },
  continueBtn: { borderWidth: 1, borderColor: '#b8860b', borderRadius: 4, paddingVertical: 12, alignItems: 'center', backgroundColor: 'rgba(184,134,11,0.04)' },
  continueText: { fontFamily: fonts.body, fontSize: 14, color: '#b8860b' },
});

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  content: {
    paddingBottom: 60,
    ...(Platform.OS === 'web' ? { maxWidth: layout.readingMeasure + 2 * layout.screenPadding, width: '100%', alignSelf: 'center' as const } : {}),
  },
  header: { paddingHorizontal: layout.screenPadding, paddingTop: Platform.OS === 'ios' ? 56 : 16, paddingBottom: 8 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  screenTitle: { fontFamily: fonts.displaySemiBold, fontSize: 28, color: colors.ink, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  drawerBtn: { padding: 8 },
  drawerBtnText: { fontSize: 18, color: colors.rubric },
  tabRow: { flexDirection: 'row', gap: 0, marginTop: 12, marginBottom: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule },
  tabBtn: { paddingVertical: 8, paddingHorizontal: 20, borderBottomWidth: 2, borderBottomColor: 'transparent' },
  tabBtnActive: { borderBottomColor: colors.rubric },
  tabText: { fontFamily: fonts.body, fontSize: 14, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.8 },
  tabTextActive: { color: colors.ink },
  statsLine: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary, marginTop: 4 },
  loadingContainer: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  loadingText: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  errorText: { fontFamily: fonts.reading, fontSize: 14, color: colors.rubric, textAlign: 'center', paddingVertical: 20, paddingHorizontal: layout.screenPadding },
  emptyState: { alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyTitle: { fontFamily: fonts.displaySemiBold, fontSize: 20, color: colors.ink, marginBottom: 12, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  emptySubtitle: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textSecondary, textAlign: 'center', lineHeight: 20, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  newSessionBtn: { marginHorizontal: layout.screenPadding, marginTop: 8, marginBottom: 24, paddingVertical: 12, borderWidth: 1, borderColor: colors.rule, borderRadius: 4, alignItems: 'center' },
  newSessionText: { fontFamily: fonts.body, fontSize: 14, color: colors.textSecondary },
  loadingMoreRow: { alignItems: 'center', paddingVertical: 16 },
  // Voice tab
  voiceSection: { paddingHorizontal: layout.screenPadding, paddingTop: 20 },
  voiceTitle: { fontFamily: fonts.displaySemiBold, fontSize: 20, color: colors.ink, marginBottom: 12, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  voiceDesc: { fontFamily: fonts.reading, fontSize: 15, lineHeight: 22, color: colors.textBody, marginBottom: 20 },
  voiceLaunchBtn: { borderWidth: 1, borderColor: colors.rubric, borderRadius: 4, paddingVertical: 14, alignItems: 'center', backgroundColor: 'rgba(139,37,0,0.03)' },
  voiceLaunchText: { fontFamily: fonts.body, fontSize: 15, color: colors.rubric },
});
