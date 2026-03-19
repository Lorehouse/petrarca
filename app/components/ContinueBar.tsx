import { View, Text, Pressable, StyleSheet, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts } from '../design/tokens';
import { logEvent } from '../data/logger';
import { getInProgressArticles, getReadingState } from '../data/store';
import { getDisplayTitle } from '../lib/display-utils';

export default function ContinueBar() {
  const router = useRouter();

  const inProgress = getInProgressArticles();
  const article = inProgress[0];

  if (!article) return null;

  const state = getReadingState(article.id);
  const progressRatio = state.time_spent_ms > 0
    ? Math.min(state.time_spent_ms / (article.estimated_read_minutes * 60 * 1000), 0.99)
    : 0.05;
  const progressPercent = Math.round(progressRatio * 100);

  return (
    <Pressable
      style={styles.bar}
      onPress={() => {
        logEvent('continue_bar_tap', { article_id: article.id });
        router.push({ pathname: '/reader', params: { id: article.id } });
      }}
    >
      <Text style={styles.label}>CONTINUE</Text>
      <Text style={styles.title} numberOfLines={1}>{getDisplayTitle(article)}</Text>
      <View style={styles.progressRing}>
        <View style={styles.progressCircle}>
          <Text style={styles.progressText}>{progressPercent}</Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: colors.ink,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    gap: 10,
  },
  label: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: 'rgba(255,255,255,0.4)',
    letterSpacing: 1,
    textTransform: 'uppercase',
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  title: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: '#ffffff',
    flex: 1,
  },
  progressRing: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.25)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressText: {
    fontFamily: fonts.display,
    fontSize: 10,
    color: '#ffffff',
    ...(Platform.OS === 'web' ? { fontWeight: '600' } : {}),
  },
});
