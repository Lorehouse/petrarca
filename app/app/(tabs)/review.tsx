import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator, FlatList, Platform, Pressable,
  StyleSheet, Text, View,
} from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { colors } from '../../design/tokens';
import { ReviewItem, ReviewStats } from '../../data/types';
import { getReviewQueue, getReviewStats } from '../../lib/review-api';
import { logEvent } from '../../data/logger';
import { setFeedbackContext } from '../../lib/feedback-context';
import PetrarcaDrawer from '../../components/PetrarcaDrawer';

const LENS_LABELS: Record<string, string> = {
  CAUSAL: 'Why?', COMPARATIVE: 'Compare', SIGNIFICANCE: 'Why it matters',
  TEMPORAL: 'Timing', PATTERN: 'Pattern', CONSEQUENCE: 'What followed',
};
const LENS_COLORS: Record<string, string> = {
  CAUSAL: '#7a3000', COMPARATIVE: '#1a4a7a', SIGNIFICANCE: '#2a6a3a',
  TEMPORAL: '#5a3a7a', PATTERN: '#7a6a00', CONSEQUENCE: '#5a0a0a',
};

const TYPE_LABELS: Record<string, string> = {
  book_chapter: '📖', exploration: '✦', voice_followup: '◎',
};

export default function ReviewScreen() {
  const router = useRouter();
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useFocusEffect(useCallback(() => {
    setFeedbackContext({ screen: 'review' });
    loadData();
    logEvent('review_tab_open', { has_stats: !!stats });
  }, []));

  async function loadData() {
    setLoading(true);
    try {
      const [statsData, queueData] = await Promise.all([
        getReviewStats(),
        getReviewQueue(30),
      ]);
      setStats(statsData);
      setItems(queueData.items);
      logEvent('review_queue_loaded', {
        due_today: statsData.due_today,
        due_this_week: statsData.due_this_week,
        total: statsData.total,
        overdue: queueData.items.filter((i: any) => i.due_at <= Date.now()).length,
        lens_breakdown: queueData.items.reduce((acc: Record<string, number>, i: any) => {
          const l = i.lens || 'UNKNOWN';
          acc[l] = (acc[l] || 0) + 1;
          return acc;
        }, {}),
      });
    } catch (e) {
      console.error('Review load failed:', e);
    } finally {
      setLoading(false);
    }
  }

  function startReview() {
    logEvent('review_session_start', { count: items.length });
    router.push('/review-session');
  }

  const dueNow = items.filter(i => i.due_at <= Date.now());

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Text style={styles.screenTitle}>Review</Text>
          <Pressable onPress={() => setDrawerOpen(true)} style={styles.drawerBtn}>
            <Text style={styles.drawerBtnText}>✦</Text>
          </Pressable>
        </View>
        <View style={styles.doubleRule} />
        {stats && (
          <Text style={styles.statsLine}>
            <Text style={styles.statsBold}>{stats.due_today}</Text>
            {' due today · '}
            <Text style={styles.statsBold}>{stats.due_this_week}</Text>
            {' this week · '}
            {stats.total} total
          </Text>
        )}
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.rubric} />
      ) : dueNow.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>✦ All caught up</Text>
          <Text style={styles.emptySubtitle}>
            {stats?.due_this_week
              ? `${stats.due_this_week} item${stats.due_this_week !== 1 ? 's' : ''} coming up this week`
              : 'Finish a book chapter to schedule your first review'}
          </Text>
        </View>
      ) : (
        <>
          {/* Start button */}
          <Pressable style={styles.startBtn} onPress={startReview}>
            <Text style={styles.startBtnText}>
              Start Review — {dueNow.length} item{dueNow.length !== 1 ? 's' : ''}
            </Text>
          </Pressable>

          {/* Queue preview */}
          <FlatList
            data={dueNow}
            keyExtractor={i => i.id}
            style={styles.list}
            renderItem={({ item }) => <ReviewQueueRow item={item} />}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        </>
      )}

      <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </View>
  );
}

function ReviewQueueRow({ item }: { item: ReviewItem }) {
  const lens = item.lens || 'SIGNIFICANCE';
  const color = LENS_COLORS[lens] || colors.textSecondary;
  const overdue = item.due_at < Date.now();

  return (
    <View style={styles.queueRow}>
      <View style={styles.queueRowLeft}>
        <Text style={styles.queueRowType}>{TYPE_LABELS[item.item_type] || '◦'}</Text>
        <View style={styles.queueRowContent}>
          <Text style={styles.queueNodeTitle} numberOfLines={1}>
            {item.curriculum_node_title || item.source_chapter_title || 'Review item'}
          </Text>
          {item.source_chapter_title && (
            <Text style={styles.queueChapter} numberOfLines={1}>
              {item.source_chapter_title}
            </Text>
          )}
        </View>
      </View>
      <View style={styles.queueRowRight}>
        <Text style={[styles.lensBadge, { color }]}>{LENS_LABELS[lens] || lens}</Text>
        {overdue && <Text style={styles.overdueTag}>due</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  header: { paddingHorizontal: 16, paddingTop: Platform.OS === 'ios' ? 56 : 16, paddingBottom: 8 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  screenTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 22, fontWeight: '600', color: colors.ink,
  },
  drawerBtn: { padding: 8 },
  drawerBtnText: { fontSize: 18, color: colors.rubric },
  doubleRule: {
    height: 5,
    backgroundColor: 'transparent',
    borderTopWidth: 2, borderTopColor: colors.rubric,
    borderBottomWidth: 1, borderBottomColor: colors.rubric,
    marginTop: 4, marginBottom: 10,
  },
  statsLine: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 13, color: colors.textSecondary, marginBottom: 4,
  },
  statsBold: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontWeight: '600', color: colors.ink,
  },
  emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 20, color: colors.ink, marginBottom: 12,
  },
  emptySubtitle: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 14, color: colors.textSecondary, textAlign: 'center', lineHeight: 20,
  },
  startBtn: {
    marginHorizontal: 16, marginTop: 8, marginBottom: 16,
    paddingVertical: 12, paddingHorizontal: 24,
    borderWidth: 1, borderColor: colors.rubric,
    borderRadius: 3, alignItems: 'center',
  },
  startBtnText: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 14, fontWeight: '500', color: colors.rubric, letterSpacing: 0.4,
  },
  list: { flex: 1 },
  separator: { height: StyleSheet.hairlineWidth, backgroundColor: colors.rule, marginHorizontal: 16 },
  queueRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 12,
  },
  queueRowLeft: { flexDirection: 'row', alignItems: 'center', flex: 1, marginRight: 12 },
  queueRowType: { fontSize: 16, marginRight: 10, color: colors.textMuted },
  queueRowContent: { flex: 1 },
  queueNodeTitle: {
    fontFamily: Platform.select({ web: "'EB Garamond', Georgia, serif", default: 'EBGaramond' }),
    fontSize: 15, color: colors.ink,
  },
  queueChapter: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 11, color: colors.textMuted, marginTop: 1,
  },
  queueRowRight: { alignItems: 'flex-end', gap: 4 },
  lensBadge: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 10, letterSpacing: 0.06, textTransform: 'uppercase', fontWeight: '500',
  },
  overdueTag: {
    fontFamily: Platform.select({ web: "'DM Sans', sans-serif", default: 'DMSans_400Regular' }),
    fontSize: 9, color: colors.rubric, letterSpacing: 0.04,
  },
});
