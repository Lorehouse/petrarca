import { View, Text, Pressable, StyleSheet, ScrollView, Platform } from 'react-native';
import { colors, fonts, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import type { SourceCategory } from '../data/store';

interface FeedFilterPillsProps {
  topics: Array<{ topic: string; count: number }>;
  sources: Array<{ source: SourceCategory; label: string; count: number }>;
  activeTopic: string | null;
  activeSource: SourceCategory | null;
  onTopicPress: (topic: string | null) => void;
  onSourcePress: (source: SourceCategory | null) => void;
}

function displayTopic(t: string): string {
  return t.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function FeedFilterPills({
  topics, sources, activeTopic, activeSource, onTopicPress, onSourcePress,
}: FeedFilterPillsProps) {
  if (topics.length === 0) return null;

  return (
    <View style={s.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={s.row}
      >
        <Pressable
          style={[s.pill, !activeTopic && s.pillActive]}
          onPress={() => { logEvent('feed_filter_topic', { topic: 'all' }); onTopicPress(null); }}
        >
          <Text style={[s.pillLabel, !activeTopic && s.pillLabelActive]}>All</Text>
        </Pressable>
        {topics.slice(0, 6).map(({ topic, count }) => (
          <Pressable
            key={topic}
            style={[s.pill, activeTopic === topic && s.pillActive]}
            onPress={() => {
              logEvent('feed_filter_topic', { topic });
              onTopicPress(activeTopic === topic ? null : topic);
            }}
          >
            <Text style={[s.pillLabel, activeTopic === topic && s.pillLabelActive]}>
              {displayTopic(topic)}
            </Text>
          </Pressable>
        ))}
        {sources.length > 1 && <View style={s.divider} />}
        {sources.filter(s => s.count > 0).map(({ source, label }) => (
          <Pressable
            key={source}
            style={[s.sourcePill, activeSource === source && s.sourcePillActive]}
            onPress={() => {
              logEvent('feed_filter_source', { source });
              onSourcePress(activeSource === source ? null : source);
            }}
          >
            <Text style={[s.sourceLabel, activeSource === source && s.sourceLabelActive]}>
              {label}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  container: { marginTop: 12 },
  row: { paddingHorizontal: layout.screenPadding, gap: 7 },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  pillActive: {
    backgroundColor: colors.ink,
    borderColor: colors.ink,
  },
  pillLabel: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.textSecondary,
  },
  pillLabelActive: {
    color: colors.parchment,
  },
  sourcePill: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  sourcePillActive: {
    borderColor: colors.ink,
  },
  sourceLabel: {
    fontFamily: fonts.ui,
    fontSize: 10,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.4,
    color: colors.textMuted,
  },
  sourceLabelActive: {
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  divider: {
    width: 1,
    height: 20,
    backgroundColor: colors.rule,
    alignSelf: 'center' as const,
  },
});
