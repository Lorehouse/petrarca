import { useEffect } from 'react';
import { View, StyleSheet, Pressable, Text } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout, spacing } from '../design/tokens';
import { setFeedbackContext } from '../lib/feedback-context';
import DoubleRule from '../components/DoubleRule';
import KnowledgeExplorer from '../components/KnowledgeExplorer';

export default function TimelineScreen() {
  const router = useRouter();

  useEffect(() => {
    setFeedbackContext({ screen: 'timeline' });
  }, []);

  return (
    <View style={styles.container}>
      {/* Header (standalone screen only) */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Text style={styles.backText}>← Back</Text>
        </Pressable>
        <Text style={[type.screenTitle, { color: colors.ink }]}>Knowledge Explorer</Text>
        <Text style={[type.screenSubtitle, { color: colors.textMuted }]}>
          Timeline, persons & places across your curricula
        </Text>
      </View>
      <DoubleRule />
      <KnowledgeExplorer />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  header: { paddingHorizontal: layout.screenPadding, paddingTop: spacing.sm, paddingBottom: spacing.sm },
  backText: { fontFamily: fonts.ui, fontSize: 12, color: colors.rubric, marginBottom: spacing.sm },
});
