import { useEffect, useState, useMemo } from 'react';
import { View, Text, Pressable, StyleSheet, Platform, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { getBookCurriculumContext } from '../lib/book-api';
import type { BookCurriculumContext as CurriculumContextType, BookCurriculumMapping, CrossBookConnection } from '../lib/book-api';

const LEVEL_CONFIG = {
  anchored: { label: 'Know well', color: colors.claimNew, dot: colors.claimNew },
  engaged: { label: 'Partial', color: '#6a8a4a', dot: '#6a8a4a' },
  mentioned: { label: 'Heard of', color: colors.warning, dot: colors.warning },
  unknown: { label: 'New', color: colors.textMuted, dot: colors.rule },
} as const;

const COVERAGE_LABEL = { deep: 'Deep', moderate: 'Moderate', surface: 'Surface' } as const;

interface Props {
  bookId: string;
  bookTitle: string;
  currentChapter?: string;
}

export default function BookCurriculumContext({ bookId, bookTitle, currentChapter }: Props) {
  const router = useRouter();
  const [context, setContext] = useState<CurriculumContextType | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getBookCurriculumContext(bookId)
      .then(data => { if (!cancelled) { setContext(data); setLoading(false); } })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [bookId]);

  const primaryDomain = context?.domains?.[0];
  const mappings = primaryDomain?.mappings || [];
  const crossBooks = primaryDomain?.cross_book_connections || [];

  // Group cross-book connections by other book
  const crossBookGroups = useMemo(() => {
    const groups: Record<string, { title: string; id: string; nodes: CrossBookConnection[] }> = {};
    for (const cb of crossBooks) {
      if (!groups[cb.other_book_id]) {
        groups[cb.other_book_id] = { title: cb.other_book_title, id: cb.other_book_id, nodes: [] };
      }
      groups[cb.other_book_id].nodes.push(cb);
    }
    return Object.values(groups);
  }, [crossBooks]);

  // Coverage summary
  const summary = useMemo(() => {
    if (!mappings.length) return null;
    const byKnowledge = { anchored: 0, engaged: 0, mentioned: 0, unknown: 0 };
    for (const m of mappings) {
      byKnowledge[m.knowledge] = (byKnowledge[m.knowledge] || 0) + 1;
    }
    const newToYou = byKnowledge.unknown + byKnowledge.mentioned;
    const familiar = byKnowledge.engaged + byKnowledge.anchored;
    return { total: mappings.length, newToYou, familiar, byKnowledge, domainTotal: primaryDomain?.node_count || 0 };
  }, [mappings, primaryDomain]);

  if (loading) return null; // Don't show loading state — silent fetch
  if (!mappings.length) return null; // No curriculum data for this book

  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel}>✦ Knowledge context</Text>

      {/* Summary line */}
      {summary && (
        <Pressable onPress={() => { setExpanded(!expanded); logEvent('book_curriculum_toggle', { bookId, expanded: !expanded }); }}>
          <Text style={styles.summaryText}>
            This book covers <Text style={styles.bold}>{summary.total}</Text> of {summary.domainTotal} topics in{' '}
            <Text style={styles.domainName}>{primaryDomain?.domain_title}</Text>
          </Text>
          <View style={styles.miniBar}>
            {summary.byKnowledge.anchored > 0 && <View style={[styles.miniSeg, { flex: summary.byKnowledge.anchored, backgroundColor: LEVEL_CONFIG.anchored.dot }]} />}
            {summary.byKnowledge.engaged > 0 && <View style={[styles.miniSeg, { flex: summary.byKnowledge.engaged, backgroundColor: LEVEL_CONFIG.engaged.dot }]} />}
            {summary.byKnowledge.mentioned > 0 && <View style={[styles.miniSeg, { flex: summary.byKnowledge.mentioned, backgroundColor: LEVEL_CONFIG.mentioned.dot }]} />}
            {summary.byKnowledge.unknown > 0 && <View style={[styles.miniSeg, { flex: summary.byKnowledge.unknown, backgroundColor: LEVEL_CONFIG.unknown.dot }]} />}
          </View>
          <Text style={styles.summaryDetail}>
            {summary.newToYou > 0 ? `${summary.newToYou} new to you` : ''}
            {summary.newToYou > 0 && summary.familiar > 0 ? ' · ' : ''}
            {summary.familiar > 0 ? `${summary.familiar} you already know` : ''}
            {' · '}
            <Text style={styles.expandHint}>{expanded ? 'tap to collapse' : 'tap to see topics'}</Text>
          </Text>
        </Pressable>
      )}

      {/* Expanded: topic list */}
      {expanded && (
        <View style={styles.topicList}>
          {mappings.map(m => {
            const config = LEVEL_CONFIG[m.knowledge];
            const isSelected = selectedNode === m.node_id;
            return (
              <View key={m.node_id}>
                <Pressable
                  style={styles.topicRow}
                  onPress={() => setSelectedNode(isSelected ? null : m.node_id)}
                >
                  <View style={[styles.knowledgeDot, { backgroundColor: config.dot }]} />
                  <Text style={styles.topicTitle} numberOfLines={1}>{m.node_title}</Text>
                  <Text style={[styles.coverageLabel, m.coverage === 'deep' && styles.coverageDeep]}>
                    {COVERAGE_LABEL[m.coverage]}
                  </Text>
                </Pressable>
                {isSelected && (
                  <View style={styles.topicDetail}>
                    <Text style={styles.topicDesc}>{m.description}</Text>
                    {m.evidence ? <Text style={styles.topicEvidence}>Book covers: {m.evidence}</Text> : null}
                    <View style={styles.topicMeta}>
                      <Text style={[styles.knowledgeLabel, { color: config.color }]}>{config.label}</Text>
                      {m.knowledge !== 'unknown' && (
                        <Text style={styles.confidenceText}>confidence: {Math.round(m.confidence * 100)}%</Text>
                      )}
                    </View>
                  </View>
                )}
              </View>
            );
          })}
        </View>
      )}

      {/* Cross-book connections */}
      {crossBookGroups.length > 0 && (
        <View style={styles.crossSection}>
          <Text style={styles.crossLabel}>Also covered by:</Text>
          {crossBookGroups.map(group => (
            <Pressable
              key={group.id}
              style={styles.crossBookRow}
              onPress={() => {
                logEvent('book_curriculum_cross_tap', { from: bookId, to: group.id });
                router.push({ pathname: '/book-detail', params: { id: group.id } } as any);
              }}
            >
              <Text style={styles.crossBookTitle}>{group.title}</Text>
              <Text style={styles.crossBookCount}>{group.nodes.length} shared topics</Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 18,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  sectionLabel: {
    fontFamily: fonts.bodyItalic,
    fontSize: 12,
    color: colors.rubric,
    marginBottom: 12,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  summaryText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    lineHeight: 20,
    color: colors.textBody,
    marginBottom: 8,
  },
  bold: {
    fontFamily: fonts.readingMedium,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  domainName: {
    fontFamily: fonts.bodyItalic,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  miniBar: {
    flexDirection: 'row',
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
    backgroundColor: colors.rule,
    marginBottom: 6,
  },
  miniSeg: { height: '100%' },
  summaryDetail: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  expandHint: {
    color: colors.rubric,
  },
  topicList: {
    marginTop: 12,
  },
  topicRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 7,
    gap: 8,
  },
  knowledgeDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    flexShrink: 0,
  },
  topicTitle: {
    flex: 1,
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textBody,
  },
  coverageLabel: {
    fontFamily: fonts.ui,
    fontSize: 9,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
    color: colors.textMuted,
  },
  coverageDeep: {
    color: colors.rubric,
  },
  topicDetail: {
    marginLeft: 15,
    paddingLeft: 12,
    borderLeftWidth: 2,
    borderLeftColor: colors.rule,
    marginBottom: 8,
  },
  topicDesc: {
    fontFamily: fonts.reading,
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  topicEvidence: {
    fontFamily: fonts.readingItalic,
    fontSize: 12,
    lineHeight: 17,
    color: colors.textMuted,
    marginBottom: 4,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  topicMeta: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 2,
  },
  knowledgeLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  confidenceText: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  crossSection: {
    marginTop: 14,
    paddingTop: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.rule,
  },
  crossLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    color: colors.textMuted,
    marginBottom: 6,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  crossBookRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  crossBookTitle: {
    fontFamily: fonts.bodyItalic,
    fontSize: 13,
    color: colors.rubric,
    flex: 1,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  crossBookCount: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
});
