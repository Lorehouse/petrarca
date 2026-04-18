import { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, ActivityIndicator,
  Platform, Linking,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { colors, fonts, type, layout } from '../../design/tokens';
import { logEvent } from '../../data/logger';
import { setFeedbackContext } from '../../lib/feedback-context';
import { getReviewStats } from '../../lib/review-api';
import { fetchReviewStream } from '../../lib/book-api';
import DoubleRule from '../../components/DoubleRule';

interface StatsData {
  due_today: number;
  due_this_week: number;
  total: number;
  by_source: Record<string, number>;
  total_candidates: number;
  due_count: number;
  domain_counts: Record<string, number>;
}

export default function StatsTab() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [reviewStats, stream] = await Promise.all([
        getReviewStats(),
        fetchReviewStream({ limit: 1, offset: 0 }),
      ]);
      setStats({
        ...reviewStats,
        total_candidates: stream.total_candidates,
        due_count: stream.due_count,
        domain_counts: stream.domain_counts,
      });
    } catch (e: any) {
      setError(e.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      logEvent('stats_tab_open');
      setFeedbackContext({ screen: 'stats-tab' });
      loadStats();
    }, [])
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>Statistics</Text>
        <Text style={styles.subtitle}>Your knowledge at a glance</Text>
      </View>

      <DoubleRule />

      {loading && (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="small" color={colors.rubric} />
        </View>
      )}

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {stats && !loading && (
        <>
          {/* Key numbers */}
          <View style={styles.statGrid}>
            <StatBox label="Due Today" value={stats.due_count} accent />
            <StatBox label="Due This Week" value={stats.due_this_week} />
            <StatBox label="Total Items" value={stats.total_candidates} />
            <StatBox label="Domains" value={Object.keys(stats.domain_counts).length} />
          </View>

          {/* Domain breakdown */}
          {Object.keys(stats.domain_counts).length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>Items by Domain</Text>
              {Object.entries(stats.domain_counts)
                .sort(([, a], [, b]) => b - a)
                .map(([domain, count]) => (
                  <View key={domain} style={styles.domainRow}>
                    <Text style={styles.domainName} numberOfLines={1}>{domain}</Text>
                    <Text style={styles.domainCount}>{count}</Text>
                  </View>
                ))}
            </View>
          )}

          {/* Source breakdown */}
          {stats.by_source && Object.keys(stats.by_source).length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionLabel}>Items by Source</Text>
              {Object.entries(stats.by_source)
                .sort(([, a], [, b]) => b - a)
                .map(([source, count]) => (
                  <View key={source} style={styles.domainRow}>
                    <Text style={styles.domainName}>{source}</Text>
                    <Text style={styles.domainCount}>{count}</Text>
                  </View>
                ))}
            </View>
          )}
        </>
      )}

      {/* Link to full dashboard */}
      <Pressable
        style={styles.dashboardLink}
        onPress={() => {
          logEvent('stats_full_dashboard_tap');
          Linking.openURL('http://localhost:8090/stats/dashboard');
        }}
      >
        <Text style={styles.dashboardText}>Open Full Dashboard {'\u203A'}</Text>
        <Text style={styles.dashboardHint}>Detailed charts, activity timeline, knowledge growth</Text>
      </Pressable>
    </ScrollView>
  );
}

function StatBox({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <View style={styles.statBox}>
      <Text style={[styles.statNumber, accent && { color: colors.rubric }]}>
        {value}
      </Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  content: {
    paddingBottom: 40,
  },
  header: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 12,
    paddingBottom: 8,
  },
  title: {
    ...type.screenTitle,
    color: colors.ink,
  },
  subtitle: {
    ...type.screenSubtitle,
    color: colors.textMuted,
    marginTop: 2,
  },
  loadingWrap: {
    paddingVertical: 32,
    alignItems: 'center',
  },
  errorText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.danger,
    paddingHorizontal: layout.screenPadding,
    paddingTop: 16,
  },
  statGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: layout.screenPadding,
    paddingTop: 20,
    gap: 12,
  },
  statBox: {
    flex: 1,
    minWidth: 140,
    backgroundColor: colors.parchmentDark,
    borderRadius: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.rule,
    padding: 16,
    alignItems: 'center',
  },
  statNumber: {
    ...type.statNumber,
    color: colors.ink,
  },
  statLabel: {
    ...type.statLabel,
    color: colors.textMuted,
    marginTop: 4,
  },
  section: {
    marginTop: 24,
    paddingHorizontal: layout.screenPadding,
  },
  sectionLabel: {
    ...type.sectionHead,
    color: colors.textMuted,
    marginBottom: 8,
  },
  domainRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  domainName: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
    flex: 1,
    marginRight: 12,
  },
  domainCount: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.textSecondary,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  dashboardLink: {
    marginHorizontal: layout.screenPadding,
    marginTop: 28,
    padding: 16,
    backgroundColor: colors.ink,
    borderRadius: 8,
    alignItems: 'center',
  },
  dashboardText: {
    fontFamily: fonts.bodyMedium,
    fontSize: 15,
    color: colors.parchment,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  dashboardHint: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: 'rgba(247, 244, 236, 0.5)',
    marginTop: 4,
  },
});
