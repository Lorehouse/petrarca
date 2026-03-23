import { useState, useMemo, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Platform,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { getArticles, getArticleById, getReadingState, getSyntheses, isSynthesisCompleted } from '../../data/store';
import { ArticleMeta, TopicSynthesis } from '../../data/types';
import { logEvent } from '../../data/logger';
import { getDisplayTitle, normalizeTopic, displayTopic } from '../../lib/display-utils';
import { colors, fonts, type, layout } from '../../design/tokens';
import { setFeedbackContext } from '../../lib/feedback-context';
import DoubleRule from '../../components/DoubleRule';
import PetrarcaDrawer from '../../components/PetrarcaDrawer';

// --- Extract first prose paragraph from synthesis markdown ---

function extractPreview(markdown: string, maxLen = 200): string {
  const lines = markdown.split('\n');
  for (const line of lines) {
    const t = line.trim();
    if (t && !t.startsWith('#') && !t.startsWith('>') && !t.startsWith('<!--') && !t.startsWith('- ') && !t.startsWith('*') && t.length > 40) {
      const clean = t.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/\*\*/g, '');
      return clean.length > maxLen ? clean.slice(0, maxLen).replace(/\s\S*$/, '') + '\u2026' : clean;
    }
  }
  return '';
}

function extractTensionLabels(tensions: TopicSynthesis['tensions']): string[] {
  return tensions.slice(0, 3).map(t => {
    if (typeof t === 'string') return t.length > 60 ? t.slice(0, 60) + '\u2026' : t;
    return t.label;
  });
}

// --- Synthesis Card (used on both mobile and web) ---

function SynthesisCard({ synthesis, compact }: { synthesis: TopicSynthesis; compact?: boolean }) {
  const router = useRouter();
  const completed = isSynthesisCompleted(synthesis.cluster_id);
  const [hovered, setHovered] = useState(false);

  const preview = useMemo(() => extractPreview(synthesis.synthesis_markdown, compact ? 140 : 220), [synthesis, compact]);
  const tensionLabels = useMemo(() => extractTensionLabels(synthesis.tensions), [synthesis]);

  const articleTitles = useMemo(() => {
    return synthesis.article_ids.slice(0, compact ? 3 : 4).map(id => {
      const a = getArticleById(id);
      return a ? getDisplayTitle(a) : null;
    }).filter(Boolean) as string[];
  }, [synthesis, compact]);

  const remaining = synthesis.article_ids.length - articleTitles.length;

  return (
    <Pressable
      style={[
        cardStyles.card,
        completed && cardStyles.cardCompleted,
        hovered && cardStyles.cardHovered,
      ] as any}
      onPress={() => {
        logEvent('synthesis_card_tap', { cluster_id: synthesis.cluster_id, label: synthesis.label });
        if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        router.push({ pathname: '/synthesis-reader', params: { clusterId: synthesis.cluster_id } });
      }}
      {...(Platform.OS === 'web' ? {
        onMouseEnter: () => setHovered(true),
        onMouseLeave: () => setHovered(false),
      } as any : {})}
    >
      <Text style={cardStyles.title} numberOfLines={2}>{synthesis.label}</Text>

      {preview ? (
        <Text style={cardStyles.preview} numberOfLines={compact ? 2 : 3}>{preview}</Text>
      ) : null}

      {tensionLabels.length > 0 && (
        <View style={cardStyles.tensionRow}>
          <Text style={cardStyles.tensionIcon}>{'\u26A1'}</Text>
          <Text style={cardStyles.tensionText} numberOfLines={2}>
            {tensionLabels.join(' \u00b7 ')}
          </Text>
        </View>
      )}

      {!compact && articleTitles.length > 0 && (
        <View style={cardStyles.sourcesSection}>
          {articleTitles.map((title, i) => (
            <Text key={i} style={cardStyles.sourceTitle} numberOfLines={1}>
              {'\u00b7'} {title}
            </Text>
          ))}
          {remaining > 0 && (
            <Text style={cardStyles.sourceMore}>+{remaining} more</Text>
          )}
        </View>
      )}

      <View style={cardStyles.footer}>
        {completed ? (
          <Text style={cardStyles.completedBadge}>{'\u2713'} Read</Text>
        ) : (
          <Text style={cardStyles.readLink}>Read {'\u2192'}</Text>
        )}
        <Text style={cardStyles.articleCount}>{synthesis.total_articles} articles</Text>
      </View>
    </Pressable>
  );
}

// --- Uncovered Topic Row (expandable) ---

function UncoveredTopicRow({ topic, articles }: { topic: string; articles: ArticleMeta[] }) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const label = displayTopic(topic);
  const readCount = articles.filter(a => getReadingState(a.id).status === 'read').length;

  return (
    <View style={uncoveredStyles.container}>
      <Pressable
        style={uncoveredStyles.row}
        onPress={() => {
          setExpanded(!expanded);
          logEvent('topics_uncovered_toggle', { topic, expanded: !expanded });
        }}
      >
        <View style={{ flex: 1 }}>
          <Text style={uncoveredStyles.name}>{label}</Text>
          <Text style={uncoveredStyles.meta}>
            {articles.length} article{articles.length !== 1 ? 's' : ''}
            {readCount > 0 ? ` \u00b7 ${readCount} read` : ''}
          </Text>
        </View>
        <Text style={uncoveredStyles.chevron}>{expanded ? '\u2013' : '+'}</Text>
      </Pressable>
      {expanded && (
        <View style={uncoveredStyles.articleList}>
          {articles.map(a => {
            const state = getReadingState(a.id);
            const dotColor = state.status === 'reading' ? colors.rubric
              : state.status === 'read' ? colors.claimNew : colors.rule;
            return (
              <Pressable
                key={a.id}
                style={uncoveredStyles.articleRow}
                onPress={() => {
                  logEvent('topics_article_tap', { article_id: a.id });
                  router.push({ pathname: '/reader', params: { id: a.id } });
                }}
              >
                <View style={[uncoveredStyles.dot, { backgroundColor: dotColor }]} />
                <View style={{ flex: 1 }}>
                  <Text style={uncoveredStyles.articleTitle} numberOfLines={1}>
                    {getDisplayTitle(a)}
                  </Text>
                  <Text style={uncoveredStyles.articleMeta}>
                    {a.hostname} {'\u00b7'} {a.estimated_read_minutes} min
                  </Text>
                </View>
              </Pressable>
            );
          })}
        </View>
      )}
    </View>
  );
}

// --- Topics Screen ---

export default function TopicsScreen() {
  const router = useRouter();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useFocusEffect(
    useCallback(() => {
      setFeedbackContext({ screen: 'topics' });
    }, [])
  );

  const allSyntheses = useMemo(() => getSyntheses(), []);

  const sortedSyntheses = useMemo(() =>
    [...allSyntheses].sort((a, b) => b.total_articles - a.total_articles),
    [allSyntheses]
  );

  // Articles not covered by any synthesis, grouped by topic
  const uncoveredGroups = useMemo(() => {
    const coveredIds = new Set<string>();
    for (const s of allSyntheses) {
      for (const id of s.article_ids) coveredIds.add(id);
    }

    const articles = getArticles();
    const groups = new Map<string, ArticleMeta[]>();
    for (const a of articles) {
      if (coveredIds.has(a.id)) continue;
      const topics = a.interest_topics || [];
      const raw = topics[0]?.broad || a.topics[0] || 'Other';
      const key = normalizeTopic(raw);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(a);
    }
    return [...groups.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [allSyntheses]);

  const headerContent = (
    <View style={styles.headerRow}>
      <View style={{ flex: 1 }}>
        <Text style={styles.headerTitle}>Syntheses</Text>
        <Text style={styles.headerSubtitle}>
          {sortedSyntheses.length} synthesized threads across your reading
        </Text>
      </View>
      <Pressable style={styles.drawerButton} onPress={() => {
        logEvent('drawer_open', { source: 'topics' });
        setDrawerOpen(true);
      }}>
        <Text style={styles.drawerButtonText}>{'\u2726'}</Text>
      </Pressable>
    </View>
  );

  const uncoveredContent = uncoveredGroups.length > 0 ? (
    <View style={Platform.OS === 'web' ? webStyles.uncoveredSection : styles.uncoveredSection}>
      <Text style={styles.sectionHead}>
        <Text style={{ color: colors.rubric }}>{'\u2726'} </Text>
        Topics without syntheses
      </Text>
      {uncoveredGroups.map(([topic, articles]) => (
        <UncoveredTopicRow key={topic} topic={topic} articles={articles} />
      ))}
    </View>
  ) : null;

  // --- Web layout: 2-column grid ---
  if (Platform.OS === 'web') {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
        <View style={webStyles.headerArea}>{headerContent}</View>
        <DoubleRule />
        <View style={webStyles.synthGrid as any}>
          {sortedSyntheses.map(s => (
            <SynthesisCard key={s.cluster_id} synthesis={s} />
          ))}
        </View>
        {uncoveredContent}
        <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
      </ScrollView>
    );
  }

  // --- Mobile layout: single-column synthesis cards ---
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <View style={styles.header}>{headerContent}</View>
      <DoubleRule />
      <View style={styles.body}>
        {sortedSyntheses.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>No syntheses yet</Text>
            <Text style={styles.emptySubtitle}>
              Syntheses will appear as the pipeline clusters your reading
            </Text>
          </View>
        ) : (
          sortedSyntheses.map(s => (
            <SynthesisCard key={s.cluster_id} synthesis={s} compact />
          ))
        )}
        {uncoveredContent}
      </View>
      <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </ScrollView>
  );
}

// --- Shared Styles ---

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  contentContainer: {
    paddingBottom: 40,
  },
  header: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 12,
    paddingBottom: 8,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  headerTitle: {
    ...type.screenTitle,
    color: colors.ink,
  },
  headerSubtitle: {
    ...type.screenSubtitle,
    color: colors.textMuted,
    marginTop: 2,
  },
  drawerButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  drawerButtonText: {
    fontFamily: fonts.display,
    fontSize: 16,
    color: colors.rubric,
  },
  body: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 16,
  },
  sectionHead: {
    ...type.sectionHead,
    color: colors.rubric,
    marginBottom: 12,
  },
  uncoveredSection: {
    marginTop: 24,
    paddingTop: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.rule,
  },
  empty: {
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 60,
    gap: 8,
  },
  emptyTitle: {
    ...type.screenTitle,
    color: colors.ink,
    fontSize: 20,
  },
  emptySubtitle: {
    ...type.entrySummary,
    color: colors.textSecondary,
    textAlign: 'center',
  },
});

// --- Synthesis Card Styles ---

const cardStyles: Record<string, any> = {
  card: {
    borderTopWidth: 2,
    borderTopColor: colors.rule,
    paddingTop: 14,
    paddingBottom: 12,
    paddingHorizontal: Platform.OS === 'web' ? 2 : 0,
    ...(Platform.OS === 'web' ? { cursor: 'pointer', transition: 'border-color 0.15s' } : {}),
  },
  cardCompleted: {
    borderTopColor: colors.claimNew,
    opacity: 0.7,
  },
  cardHovered: {
    borderTopColor: colors.rubric,
  },
  title: {
    fontFamily: fonts.displaySemiBold,
    fontSize: Platform.OS === 'web' ? 19 : 17,
    lineHeight: Platform.OS === 'web' ? 24 : 22,
    color: colors.ink,
    marginBottom: 6,
    ...(Platform.OS === 'web' ? { fontWeight: '600' } : {}),
  },
  preview: {
    fontFamily: fonts.reading,
    fontSize: 14,
    lineHeight: 21,
    color: colors.textSecondary,
    marginBottom: 8,
  },
  tensionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginBottom: 8,
    paddingLeft: 2,
  },
  tensionIcon: {
    fontSize: 11,
    color: '#b89840',
    marginTop: 2,
  },
  tensionText: {
    fontFamily: fonts.readingItalic,
    fontSize: 12,
    lineHeight: 17,
    color: colors.textSecondary,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' } : {}),
    flex: 1,
  },
  sourcesSection: {
    marginBottom: 8,
  },
  sourceTitle: {
    fontFamily: fonts.ui,
    fontSize: 11,
    lineHeight: 17,
    color: colors.textMuted,
  },
  sourceMore: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 1,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  readLink: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.rubric,
  },
  completedBadge: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.claimNew,
  },
  articleCount: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
};

// --- Uncovered Topic Styles ---

const uncoveredStyles = StyleSheet.create({
  container: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    minHeight: layout.touchTarget,
  },
  name: {
    fontFamily: fonts.bodyItalic,
    fontSize: 15,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  meta: {
    ...type.metadata,
    color: colors.textMuted,
    marginTop: 2,
  },
  chevron: {
    fontFamily: fonts.display,
    fontSize: 18,
    color: colors.textMuted,
    paddingLeft: 12,
  },
  articleList: {
    paddingBottom: 8,
  },
  articleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    minHeight: layout.touchTarget,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    marginRight: 10,
  },
  articleTitle: {
    ...type.entryTitle,
    color: colors.textPrimary,
    fontSize: 14,
  },
  articleMeta: {
    ...type.metadata,
    color: colors.textMuted,
    marginTop: 1,
  },
});

// --- Web-specific Styles ---

const webStyles: Record<string, any> = {
  headerArea: {
    maxWidth: layout.webFeedMaxWidth,
    marginHorizontal: 'auto',
    width: '100%',
    paddingHorizontal: layout.screenPadding,
    paddingTop: 12,
    paddingBottom: 8,
  },
  synthGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '0 32px',
    maxWidth: layout.webFeedMaxWidth,
    marginHorizontal: 'auto',
    width: '100%',
    paddingHorizontal: layout.screenPadding,
    paddingTop: 20,
  },
  uncoveredSection: {
    maxWidth: layout.webFeedMaxWidth,
    marginHorizontal: 'auto',
    width: '100%',
    paddingHorizontal: layout.screenPadding,
    paddingTop: 32,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.rule,
    marginTop: 24,
  },
};
