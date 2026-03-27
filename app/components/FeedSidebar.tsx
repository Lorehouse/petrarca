import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts } from '../design/tokens';
import { logEvent } from '../data/logger';
import type { SourceCategory } from '../data/store';
import { getResearchArticles, getResearchQuery } from '../data/store';

const SOURCE_COLORS: Record<SourceCategory, string> = {
  twitter: '#1DA1F2',
  newsletter: '#e67e22',
  research: colors.rubric,
  exploration: colors.textMuted,
  other: colors.rule,
};

interface FeedSidebarProps {
  topics: Array<{ topic: string; count: number }>;
  sources: Array<{ source: SourceCategory; label: string; count: number }>;
  activeTopic: string | null;
  activeSource: SourceCategory | null;
  totalCount: number;
  onTopicPress: (topic: string | null) => void;
  onSourcePress: (source: SourceCategory | null) => void;
  onDrawerOpen: () => void;
}

function displayTopic(t: string): string {
  return t.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function FeedSidebar({
  topics, sources, activeTopic, activeSource, totalCount,
  onTopicPress, onSourcePress, onDrawerOpen,
}: FeedSidebarProps) {
  const router = useRouter();
  const researchGroups = getResearchArticles();

  return (
    <View style={s.container}>
      <Text style={s.title}>Feed</Text>
      <Pressable style={s.drawerBtn} onPress={onDrawerOpen}>
        <Text style={s.drawerBtnText}>{'\u2726'} Menu</Text>
      </Pressable>

      {/* Topics */}
      <Text style={s.sectionLabel}>Topics</Text>
      <Pressable style={s.topicRow} onPress={() => onTopicPress(null)}>
        <Text style={[s.topicName, !activeTopic && s.topicActive]}>All</Text>
        <Text style={s.topicCount}>{totalCount}</Text>
      </Pressable>
      {topics.slice(0, 8).map(({ topic, count }) => (
        <Pressable
          key={topic}
          style={s.topicRow}
          onPress={() => {
            logEvent('sidebar_filter_topic', { topic });
            onTopicPress(activeTopic === topic ? null : topic);
          }}
        >
          <Text style={[s.topicName, activeTopic === topic && s.topicActive]}>
            {displayTopic(topic)}
          </Text>
          <Text style={s.topicCount}>{count}</Text>
        </Pressable>
      ))}

      {/* Sources */}
      <Text style={s.sectionLabel}>Sources</Text>
      <Pressable style={s.sourceRow} onPress={() => onSourcePress(null)}>
        <View style={[s.sourceDot, { backgroundColor: colors.ink }]} />
        <Text style={[s.sourceName, !activeSource && s.sourceActive]}>All</Text>
        <Text style={s.sourceCount}>{totalCount}</Text>
      </Pressable>
      {sources.map(({ source, label, count }) => (
        <Pressable
          key={source}
          style={s.sourceRow}
          onPress={() => {
            logEvent('sidebar_filter_source', { source });
            onSourcePress(activeSource === source ? null : source);
          }}
        >
          <View style={[s.sourceDot, { backgroundColor: SOURCE_COLORS[source] }]} />
          <Text style={[s.sourceName, activeSource === source && s.sourceActive]}>{label}</Text>
          <Text style={s.sourceCount}>{count}</Text>
        </Pressable>
      ))}

      {/* Research */}
      {researchGroups.length > 0 && (
        <View style={s.researchBox}>
          <Text style={s.researchLabel}>{'\u2726'} Your Research</Text>
          {researchGroups.map(({ query, articles }) => (
            <View key={query}>
              {articles.map(a => (
                <Pressable
                  key={a.id}
                  style={s.researchItem}
                  onPress={() => {
                    logEvent('sidebar_research_tap', { article_id: a.id });
                    router.push({ pathname: '/reader', params: { id: a.id } });
                  }}
                >
                  <Text style={s.researchTitle} numberOfLines={2}>{a.title}</Text>
                  <Text style={s.researchQuery}>{'\u21B3'} {query}</Text>
                </Pressable>
              ))}
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  container: {
    position: 'sticky' as any,
    top: 16,
    alignSelf: 'flex-start' as const,
    paddingLeft: 16,
  },
  title: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 20,
    color: colors.ink,
    fontWeight: '600',
  },
  drawerBtn: {
    marginTop: 10,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: colors.rule,
    alignItems: 'center' as const,
  },
  drawerBtnText: {
    fontFamily: fonts.display,
    fontSize: 14,
    color: colors.rubric,
  },
  sectionLabel: {
    fontFamily: fonts.ui,
    fontSize: 8,
    letterSpacing: 1.5,
    textTransform: 'uppercase' as const,
    color: colors.rubric,
    marginTop: 18,
    marginBottom: 6,
  },
  topicRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingVertical: 4,
    cursor: 'pointer' as any,
  },
  topicName: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.textSecondary,
  },
  topicActive: {
    color: colors.ink,
    fontWeight: '500' as any,
  },
  topicCount: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 3,
    cursor: 'pointer' as any,
  },
  sourceDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
  },
  sourceName: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textSecondary,
    flex: 1,
  },
  sourceActive: {
    color: colors.ink,
  },
  sourceCount: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  researchBox: {
    marginTop: 16,
    padding: 8,
    borderWidth: 1,
    borderColor: 'rgba(139,37,0,0.12)',
  },
  researchLabel: {
    fontFamily: fonts.ui,
    fontSize: 8,
    letterSpacing: 1,
    textTransform: 'uppercase' as const,
    color: colors.rubric,
    marginBottom: 6,
  },
  researchItem: {
    paddingVertical: 4,
    cursor: 'pointer' as any,
  },
  researchTitle: {
    fontFamily: fonts.body,
    fontSize: 12.5,
    color: colors.textPrimary,
    lineHeight: 16,
  },
  researchQuery: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    marginTop: 1,
  },
});
