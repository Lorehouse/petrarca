import { View, Text, Pressable, StyleSheet, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts } from '../design/tokens';
import { getResearchArticles } from '../data/store';
import { logEvent } from '../data/logger';

export default function ResearchSection() {
  const router = useRouter();
  const groups = getResearchArticles();
  if (groups.length === 0) return null;

  return (
    <View style={s.container}>
      <Text style={s.label}>
        <Text style={{ color: colors.rubric }}>{'\u2726'} </Text>From Your Research
      </Text>
      {groups.map(({ query, articles }) => (
        <View key={query}>
          <Text style={s.query}>{'\u21B3'} {query}</Text>
          {articles.map(a => (
            <Pressable
              key={a.id}
              style={s.item}
              onPress={() => {
                logEvent('research_section_tap', { article_id: a.id, query });
                router.push({ pathname: '/reader', params: { id: a.id } });
              }}
            >
              <Text style={s.itemTitle} numberOfLines={1}>{a.title}</Text>
              <Text style={s.itemMeta}>{a.estimated_read_minutes}m</Text>
            </Pressable>
          ))}
        </View>
      ))}
    </View>
  );
}

const s = StyleSheet.create({
  container: {
    marginTop: 14,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderLeftWidth: 2,
    borderLeftColor: colors.rubric,
  },
  label: {
    fontFamily: fonts.ui,
    fontSize: 9,
    letterSpacing: 1.5,
    textTransform: 'uppercase' as const,
    color: colors.rubric,
    marginBottom: 8,
  },
  query: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    marginBottom: 4,
    marginTop: 4,
  },
  item: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingVertical: 5,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(139,37,0,0.06)',
  },
  itemTitle: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.textPrimary,
    flex: 1,
    lineHeight: 18,
    ...(Platform.OS === 'web' ? { cursor: 'pointer' } as any : {}),
  },
  itemMeta: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    marginLeft: 12,
  },
});
