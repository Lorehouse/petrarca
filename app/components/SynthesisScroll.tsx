import { View, Text, ScrollView, Pressable, StyleSheet, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts } from '../design/tokens';
import { logEvent } from '../data/logger';
import { getSyntheses, isSynthesisCompleted } from '../data/store';
import type { TopicSynthesis } from '../data/types';

function extractPreview(markdown: string): string {
  const lines = markdown.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('#')) continue;
    if (trimmed.startsWith('>')) continue;
    if (trimmed.startsWith('-') || trimmed.startsWith('*') || /^\d+\./.test(trimmed)) continue;
    if (trimmed.length > 40) return trimmed;
  }
  return '';
}

function extractTensionLabel(tension: string | { label: string; description: string }): string {
  if (typeof tension === 'string') return tension;
  return tension.label;
}

export default function SynthesisScroll() {
  const router = useRouter();
  const allSyntheses = getSyntheses();

  if (allSyntheses.length === 0) return null;

  const sorted = [...allSyntheses].sort((a, b) => b.total_articles - a.total_articles);

  return (
    <View style={styles.container}>
      <Text style={styles.sectionHeader}>{'\u2726'} Syntheses</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {sorted.map((synthesis, index) => {
          const completed = isSynthesisCompleted(synthesis.cluster_id);
          const preview = extractPreview(synthesis.synthesis_markdown);
          const tension = synthesis.tensions?.[0];
          const tensionLabel = tension ? extractTensionLabel(tension) : null;
          const isFirst = index === 0;

          return (
            <Pressable
              key={synthesis.cluster_id}
              style={[
                styles.card,
                isFirst && styles.cardFirst,
                completed && styles.cardCompleted,
              ]}
              onPress={() => {
                logEvent('synthesis_scroll_tap', {
                  cluster_id: synthesis.cluster_id,
                  label: synthesis.label,
                });
                router.push({
                  pathname: '/synthesis-reader',
                  params: { clusterId: synthesis.cluster_id },
                });
              }}
            >
              {completed && <View style={styles.completedTopBorder} />}
              <View style={styles.cardInner}>
                <View style={styles.margin}>
                  <Text style={styles.marginCount}>{synthesis.total_articles}</Text>
                  <Text style={styles.marginLabel}>articles</Text>
                  {completed ? (
                    <Text style={styles.marginRead}>{'\u2713'} read</Text>
                  ) : (
                    <View style={styles.marginBar} />
                  )}
                </View>
                <View style={styles.content}>
                  <Text style={styles.title} numberOfLines={2}>{synthesis.label}</Text>
                  {preview ? (
                    <Text style={styles.preview} numberOfLines={2}>{preview}</Text>
                  ) : null}
                  {tensionLabel ? (
                    <Text style={styles.tension} numberOfLines={1}>
                      {'\u26A1'} {tensionLabel}
                    </Text>
                  ) : null}
                  <Text style={styles.readLink}>Read {'\u2192'}</Text>
                </View>
              </View>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 16,
    marginBottom: 8,
  },
  sectionHeader: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.rubric,
    letterSpacing: 2,
    textTransform: 'uppercase',
    marginBottom: 10,
    paddingHorizontal: 16,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  scrollContent: {
    paddingHorizontal: 16,
    gap: 0,
  },
  card: {
    width: 220,
    borderRightWidth: 1,
    borderRightColor: colors.rule,
    overflow: 'hidden',
  },
  cardFirst: {
    width: 260,
  },
  cardCompleted: {
    opacity: 0.65,
  },
  completedTopBorder: {
    height: 2,
    backgroundColor: colors.claimNew,
  },
  cardInner: {
    flexDirection: 'row',
    flex: 1,
  },
  margin: {
    width: 48,
    backgroundColor: colors.parchmentDark,
    borderRightWidth: 1,
    borderRightColor: colors.rule,
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 4,
  },
  marginCount: {
    fontFamily: fonts.display,
    fontSize: 28,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '600' } : {}),
  },
  marginLabel: {
    fontFamily: fonts.ui,
    fontSize: 6,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 1,
  },
  marginBar: {
    width: 14,
    height: 2,
    backgroundColor: colors.rubric,
    marginTop: 6,
  },
  marginRead: {
    fontFamily: fonts.ui,
    fontSize: 7,
    color: colors.claimNew,
    marginTop: 6,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  content: {
    flex: 1,
    padding: 10,
    justifyContent: 'space-between',
  },
  title: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 16,
    color: colors.ink,
    lineHeight: 20,
    marginBottom: 4,
    ...(Platform.OS === 'web' ? { fontWeight: '600' } : {}),
  },
  preview: {
    fontFamily: fonts.reading,
    fontSize: 11,
    color: colors.textSecondary,
    lineHeight: 15,
    marginBottom: 4,
  },
  tension: {
    fontFamily: fonts.readingItalic,
    fontSize: 10,
    color: colors.textSecondary,
    lineHeight: 14,
    marginBottom: 6,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' } : {}),
  },
  readLink: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
});
