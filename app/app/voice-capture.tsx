import { useCallback } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';
import { useFocusEffect } from 'expo-router';
import ExplorerCapture, { type CaptureResult } from '../components/ExplorerCapture';
import DoubleRule from '../components/DoubleRule';

export default function VoiceCaptureScreen() {
  const router = useRouter();

  useFocusEffect(
    useCallback(() => {
      logEvent('voice_capture_screen_open');
      setFeedbackContext({ screen: 'voice-capture' });
    }, [])
  );

  const handleComplete = useCallback((result: CaptureResult) => {
    logEvent('voice_capture_complete', {
      notes_saved: result.notes_saved,
      entities: result.entities_detected?.length ?? 0,
      research: result.research_triggered?.length ?? 0,
    });
  }, []);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backText}>{'\u2190'} Back</Text>
        </Pressable>
        <Text style={styles.title}>Capture Voice</Text>
        <Text style={styles.subtitle}>
          Record what you learned — a podcast, book, conversation
        </Text>
      </View>

      <DoubleRule />

      <View style={styles.captureArea}>
        <ExplorerCapture
          mode="general"
          placeholder="What did you just learn?"
          onCaptureComplete={handleComplete}
        />
      </View>

      <View style={styles.hint}>
        <Text style={styles.hintText}>
          Your recording will be transcribed and matched against your curriculum.
          Facts, entities, and wonderings are extracted automatically.
        </Text>
      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  header: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 8,
    paddingBottom: 8,
  },
  backButton: {
    paddingVertical: 4,
    marginBottom: 4,
    alignSelf: 'flex-start',
    minHeight: 44,
    justifyContent: 'center',
  },
  backText: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.textMuted,
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
  captureArea: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 24,
    paddingBottom: 16,
  },
  hint: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 8,
  },
  hintText: {
    fontFamily: fonts.reading,
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 18,
  },
});
