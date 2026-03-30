import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator, Platform, Pressable, ScrollView,
  StyleSheet, Text, View,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { colors, fonts, layout } from '../../design/tokens';
import { EntitySpan, ResurfacingItem, ResurfacingSession } from '../../data/types';
import {
  generateCurriculumReview, recordReviewResult, recordEntityTap,
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
  onEntityTap,
}: {
  item: ResurfacingItem;
  onResult: (result: string) => void;
  onEntityTap: (entityId: string) => void;
}) {
  const [revealed, setRevealed] = useState(false);
  const [graded, setGraded] = useState(false);

  const answerType = item.answer_type || 'concept';
  const typeLabel = answerType === 'date' ? 'Date'
    : answerType === 'name' ? 'Identity'
    : answerType === 'sequence' ? 'Timeline'
    : 'Concept';

  const gradingButtons = answerType === 'date' ? [
    { value: 'exact_year', label: 'Exact year', style: 'correct' as const },
    { value: 'right_decade', label: 'Right decade', style: 'partial' as const },
    { value: 'right_century', label: 'Right century', style: 'weak' as const },
    { value: 'missed', label: 'Missed', style: 'wrong' as const },
  ] : answerType === 'name' ? [
    { value: 'correct', label: 'Knew it', style: 'correct' as const },
    { value: 'wrong', label: 'Didn\'t know', style: 'wrong' as const },
  ] : answerType === 'sequence' ? [
    { value: 'all_correct', label: 'All correct', style: 'correct' as const },
    { value: 'mostly_right', label: 'Mostly right', style: 'partial' as const },
    { value: 'wrong', label: 'Wrong order', style: 'wrong' as const },
  ] : [
    { value: 'correct', label: 'Knew it', style: 'correct' as const },
    { value: 'partial', label: 'Partly', style: 'partial' as const },
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
      {/* Header: type badge (node title shown only after reveal to avoid spoilers) */}
      <View style={cs.headerRow}>
        <View style={cs.typeBadge}>
          <Text style={cs.typeBadgeText}>{typeLabel}</Text>
        </View>
        {revealed && (item.node_title || item.cluster_label) ? (
          <Text style={cs.nodeTitle}>{item.node_title || item.cluster_label}</Text>
        ) : null}
      </View>

      {/* Question */}
      <Text style={cs.question}>{item.question}</Text>

      {/* Reveal / Answer */}
      {!revealed ? (
        <Pressable style={cs.revealButton} onPress={() => setRevealed(true)}>
          <Text style={cs.revealText}>Show answer</Text>
        </Pressable>
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

          {/* Place entities — map link */}
          {(() => {
            const allSpans = Object.values(item.entity_spans || {}).flat();
            const places = allSpans.filter(sp => sp.entity_type === 'place');
            // Deduplicate by entity_id
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
                    <Text style={cs.mapLinkText}>{'\u{1F4CD}'} {sp.name}</Text>
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
                : btn.style === 'weak' ? cs.gradeWeak
                : cs.gradeWrong;
              const txtStyle = btn.style === 'correct' ? cs.gradeCorrectText
                : btn.style === 'partial' ? cs.gradePartialText
                : btn.style === 'weak' ? cs.gradeWeakText
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
  place: '\u{1F4CD} Place',
  person: '\u{1F464} Person',
  event: '\u26A1 Event',
  period: '\u{1F551} Period',
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
      {/* Header: type badge */}
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

      {/* Name */}
      <Text style={ic.entityName}>{item.entity_name}</Text>
      {item.modern_name && item.modern_name !== item.entity_name ? (
        <Text style={ic.modernName}>Modern: {item.modern_name}</Text>
      ) : null}

      {/* Mini map for places */}
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
            showControls={false}
            showTimeline={false}
            showFilters={false}
            showLegend={false}
            showEntitySheet={false}
            style={{ height: 140 }}
          />
        </View>
      ) : null}

      {/* Description */}
      {item.description ? (
        <Text style={ic.description}>{item.description}</Text>
      ) : null}

      {/* Date facts */}
      {dateStr ? (
        <Text style={ic.dateFact}>{'\u2022'} {dateStr}</Text>
      ) : null}

      {/* Continue button */}
      <Pressable style={ic.continueBtn} onPress={handleContinue}>
        <Text style={ic.continueText}>Continue {'\u2192'}</Text>
      </Pressable>
    </View>
  );
}

// ── Main Screen ─────────────────────────────────────────────────────

export default function ReviewScreen() {
  const [session, setSession] = useState<ResurfacingSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeEntityId, setActiveEntityId] = useState<string | null>(null);

  const loadSession = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const s = await generateCurriculumReview();
      setSession(s);
      logEvent('review_session_loaded', {
        session_id: s.id,
        item_count: s.items?.length ?? 0,
      });
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => {
    setFeedbackContext({ screen: 'review' });
    loadSession();
  }, []));

  const [currentIndex, setCurrentIndex] = useState(0);

  const handleResult = async (item: ResurfacingItem, result: string) => {
    if (item.question_id) {
      await recordReviewResult(item.question_id, result);
      logEvent('review_result', {
        question_id: item.question_id,
        result,
        answer_type: item.answer_type,
        domain: item.domain,
      });
    }
    // Advance to next question after a brief delay
    setTimeout(() => {
      setCurrentIndex(i => i + 1);
    }, 600);
  };

  const handleNewSession = () => {
    setCurrentIndex(0);
    loadSession();
  };

  const items = session?.items || [];
  const currentItem = items[currentIndex];
  const isDone = session && currentIndex >= items.length && !loading;

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
          {session && (
            <Text style={s.statsLine}>
              {currentIndex < items.length
                ? `${currentIndex + 1} / ${items.length}`
                : `${items.length} / ${items.length}`}
              {session.total_questions_in_pool ? `  ·  ${session.total_questions_in_pool} in pool` : ''}
            </Text>
          )}
        </View>

        {/* Loading */}
        {loading && (
          <View style={s.loadingContainer}>
            <ActivityIndicator size="small" color={colors.rubric} />
            <Text style={s.loadingText}>Loading review...</Text>
          </View>
        )}

        {/* Error */}
        {error ? <Text style={s.errorText}>{error}</Text> : null}

        {/* Empty session */}
        {session && items.length === 0 && !loading && (
          <View style={s.emptyState}>
            <Text style={s.emptyTitle}>{'\u2726'} All caught up</Text>
            <Text style={s.emptySubtitle}>No questions due right now. Come back later or read more!</Text>
          </View>
        )}

        {/* Current card — dispatch by type */}
        {currentItem && currentItem.type === 'entity_intro' ? (
          <EntityIntroCard
            key={`intro-${currentItem.entity_id || currentIndex}`}
            item={currentItem}
            onContinue={() => setCurrentIndex(i => i + 1)}
          />
        ) : currentItem ? (
          <ReviewCard
            key={currentItem.question_id || `q-${currentIndex}`}
            item={currentItem}
            onResult={(result) => handleResult(currentItem, result)}
            onEntityTap={setActiveEntityId}
          />
        ) : null}

        {/* Session complete */}
        {isDone && (
          <View style={s.emptyState}>
            <Text style={s.emptyTitle}>{'\u2726'} Session complete</Text>
            <Text style={s.emptySubtitle}>{items.length} questions reviewed</Text>
            <Pressable style={s.newSessionBtn} onPress={handleNewSession}>
              <Text style={s.newSessionText}>New session</Text>
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
  nodeTitle: { fontFamily: fonts.bodyItalic, fontSize: 12, color: colors.textSecondary, flex: 1, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  question: { fontFamily: fonts.reading, fontSize: 18, lineHeight: 26, color: colors.ink, marginBottom: 16 },
  revealButton: { borderWidth: 1, borderColor: colors.rubric, borderRadius: 4, paddingVertical: 12, alignItems: 'center' },
  revealText: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  answerBox: { borderLeftWidth: 3, borderLeftColor: colors.claimNew, paddingLeft: 14, marginBottom: 14 },
  answerText: { fontFamily: fonts.reading, fontSize: 15, lineHeight: 22, color: colors.textBody },
  hookBox: { backgroundColor: 'rgba(139,37,0,0.04)', borderLeftWidth: 2, borderLeftColor: colors.rubric, paddingLeft: 12, paddingVertical: 8, marginBottom: 12, borderRadius: 2 },
  hookLabel: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.rubric, letterSpacing: 0.3, marginBottom: 4, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  hookText: { fontFamily: fonts.readingItalic, fontSize: 14, lineHeight: 20, color: colors.textBody, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  anchorBox: { marginBottom: 14 },
  anchorText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary, lineHeight: 18, marginBottom: 2 },
  mapLinkRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 14 },
  mapLinkText: { fontFamily: fonts.ui, fontSize: 13, color: colors.info, textDecorationLine: 'underline' },
  gradeRow: { flexDirection: 'row', gap: 8 },
  gradeButton: { flex: 1, paddingVertical: 10, borderRadius: 4, alignItems: 'center', borderWidth: 1 },
  gradeCorrect: { borderColor: colors.claimNew, backgroundColor: 'rgba(42,122,74,0.05)' },
  gradeCorrectText: { fontFamily: fonts.ui, fontSize: 12, color: colors.claimNew },
  gradePartial: { borderColor: colors.textMuted, backgroundColor: 'rgba(176,168,152,0.08)' },
  gradePartialText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary },
  gradeWeak: { borderColor: '#b8860b', backgroundColor: 'rgba(184,134,11,0.06)' },
  gradeWeakText: { fontFamily: fonts.ui, fontSize: 12, color: '#b8860b' },
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
  statsLine: { fontFamily: fonts.ui, fontSize: 13, color: colors.textSecondary, marginTop: 4 },
  loadingContainer: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  loadingText: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  errorText: { fontFamily: fonts.reading, fontSize: 14, color: colors.rubric, textAlign: 'center', paddingVertical: 20, paddingHorizontal: layout.screenPadding },
  emptyState: { alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyTitle: { fontFamily: fonts.displaySemiBold, fontSize: 20, color: colors.ink, marginBottom: 12, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  emptySubtitle: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textSecondary, textAlign: 'center', lineHeight: 20, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  newSessionBtn: { marginHorizontal: layout.screenPadding, marginTop: 8, marginBottom: 24, paddingVertical: 12, borderWidth: 1, borderColor: colors.rule, borderRadius: 4, alignItems: 'center' },
  newSessionText: { fontFamily: fonts.body, fontSize: 14, color: colors.textSecondary },
});
