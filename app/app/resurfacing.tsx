import { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, TextInput,
  Platform, ActivityIndicator,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { logEvent } from '../data/logger';
import {
  generateResurfacingSession, respondToResurfacing, skipResurfacing,
} from '../lib/book-api';
import type { ResurfacingSession, ResurfacingItem } from '../data/types';
import { colors, fonts, layout } from '../design/tokens';
import DoubleRule from '../components/DoubleRule';

function ResonanceCard({
  item,
  onRespond,
  onSkip,
}: {
  item: ResurfacingItem;
  onRespond: (text: string) => void;
  onSkip: () => void;
}) {
  const [responseText, setResponseText] = useState('');
  const [showInput, setShowInput] = useState(false);
  const [responded, setResponded] = useState(false);

  const handleRespond = () => {
    if (!responseText.trim()) return;
    onRespond(responseText.trim());
    setResponded(true);
  };

  if (responded) {
    return (
      <View style={cardStyles.card}>
        <Text style={cardStyles.responded}>Response saved {'\u2713'}</Text>
      </View>
    );
  }

  return (
    <View style={cardStyles.card}>
      {/* Book info */}
      <View style={cardStyles.bookRow}>
        {item.book_cover_url ? (
          <Image source={{ uri: item.book_cover_url }} style={cardStyles.cover} />
        ) : (
          <View style={[cardStyles.cover, cardStyles.coverPlaceholder]}>
            <Text style={cardStyles.coverLetter}>{(item.book_title || '?')[0]}</Text>
          </View>
        )}
        <View style={cardStyles.bookInfo}>
          <Text style={cardStyles.bookTitle}>{item.book_title}</Text>
          <Text style={cardStyles.bookMeta}>
            {item.book_author}{item.chapter ? ` · ${item.chapter}` : ''}
            {item.months_since_capture ? ` · ${item.months_since_capture}mo ago` : ''}
          </Text>
        </View>
      </View>

      {/* Highlight */}
      <View style={cardStyles.highlightBox}>
        <Text style={cardStyles.highlightText}>{item.full_text || item.highlight_text}</Text>
      </View>

      {/* Prompt */}
      <Text style={cardStyles.promptText}>{item.prompt_text}</Text>

      {/* Actions */}
      {showInput ? (
        <View style={cardStyles.inputArea}>
          <TextInput
            style={cardStyles.textInput}
            value={responseText}
            onChangeText={setResponseText}
            placeholder="Your thoughts..."
            placeholderTextColor={colors.textMuted}
            multiline
            numberOfLines={3}
            autoFocus
          />
          <View style={cardStyles.inputActions}>
            <Pressable style={cardStyles.sendButton} onPress={handleRespond}>
              <Text style={cardStyles.sendText}>Save response</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <View style={cardStyles.actions}>
          <Pressable style={cardStyles.respondButton} onPress={() => setShowInput(true)}>
            <Text style={cardStyles.respondText}>Respond</Text>
          </Pressable>
          <Pressable style={cardStyles.skipButton} onPress={onSkip}>
            <Text style={cardStyles.skipText}>Skip {'\u2192'}</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

function DialogueCard({
  item,
  onRespond,
  onSkip,
}: {
  item: ResurfacingItem;
  onRespond: (text: string) => void;
  onSkip: () => void;
}) {
  const [responseText, setResponseText] = useState('');
  const [showInput, setShowInput] = useState(false);
  const [responded, setResponded] = useState(false);

  const handleRespond = () => {
    if (!responseText.trim()) return;
    onRespond(responseText.trim());
    setResponded(true);
  };

  if (responded) {
    return (
      <View style={cardStyles.card}>
        <Text style={cardStyles.responded}>Response saved {'\u2713'}</Text>
      </View>
    );
  }

  return (
    <View style={cardStyles.card}>
      <Text style={cardStyles.dialogueLabel}>{'\u2726'} Cross-Book Dialogue</Text>

      {/* Claim A */}
      <View style={cardStyles.claimBox}>
        <Text style={cardStyles.claimBookLabel}>{item.claim_a?.book_title} ({item.claim_a?.book_author})</Text>
        <Text style={cardStyles.claimText}>{item.claim_a?.text}</Text>
      </View>

      <Text style={cardStyles.vsText}>{'\u2195'}</Text>

      {/* Claim B */}
      <View style={cardStyles.claimBox}>
        <Text style={cardStyles.claimBookLabel}>{item.claim_b?.book_title} ({item.claim_b?.book_author})</Text>
        <Text style={cardStyles.claimText}>{item.claim_b?.text}</Text>
      </View>

      {/* Tension prompt */}
      <Text style={cardStyles.promptText}>{item.tension_prompt}</Text>

      {/* Actions */}
      {showInput ? (
        <View style={cardStyles.inputArea}>
          <TextInput
            style={cardStyles.textInput}
            value={responseText}
            onChangeText={setResponseText}
            placeholder="Share your thoughts..."
            placeholderTextColor={colors.textMuted}
            multiline
            numberOfLines={4}
            autoFocus
          />
          <View style={cardStyles.inputActions}>
            <Pressable style={cardStyles.sendButton} onPress={handleRespond}>
              <Text style={cardStyles.sendText}>Save response</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <View style={cardStyles.actions}>
          <Pressable style={cardStyles.respondButton} onPress={() => setShowInput(true)}>
            <Text style={cardStyles.respondText}>Share your thoughts</Text>
          </Pressable>
          <Pressable style={cardStyles.skipButton} onPress={onSkip}>
            <Text style={cardStyles.skipText}>Skip {'\u2192'}</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

export default function ResurfacingScreen() {
  const router = useRouter();
  const [session, setSession] = useState<ResurfacingSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useFocusEffect(useCallback(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const s = await generateResurfacingSession(true);
        if (!cancelled) {
          setSession(s);
          logEvent('resurfacing_session_loaded', {
            session_id: s.id,
            resonance_count: s.resonance_count,
            dialogue_count: s.dialogue_count,
          });
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []));

  const handleRespond = async (item: ResurfacingItem, text: string) => {
    const captureId = item.capture_id || `dialogue_${item.claim_a?.book_id}_${item.claim_b?.book_id}`;
    await respondToResurfacing(captureId, text);
    logEvent('resurfacing_responded', {
      capture_id: captureId,
      type: item.type,
      response_length: text.length,
    });
  };

  const handleSkip = async (item: ResurfacingItem) => {
    if (item.capture_id) {
      await skipResurfacing(item.capture_id);
    }
    logEvent('resurfacing_skipped', {
      capture_id: item.capture_id,
      type: item.type,
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>{'\u2039'} Library</Text>
      </Pressable>

      <View style={styles.header}>
        <Text style={styles.title}>Revisit</Text>
        <Text style={styles.subtitle}>Reconnect with ideas from your reading</Text>
      </View>
      <DoubleRule />

      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color={colors.rubric} />
          <Text style={styles.loadingText}>Preparing your session...</Text>
        </View>
      )}

      {error ? (
        <Text style={styles.errorText}>{error}</Text>
      ) : null}

      {session && session.items.length === 0 && !loading && (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>Nothing to revisit yet.</Text>
          <Text style={styles.emptySubtext}>Add and read books to start building your resurfacing pool.</Text>
        </View>
      )}

      {session?.items.map((item, i) => (
        item.type === 'dialogue' ? (
          <DialogueCard
            key={`d-${i}`}
            item={item}
            onRespond={(text) => handleRespond(item, text)}
            onSkip={() => handleSkip(item)}
          />
        ) : (
          <ResonanceCard
            key={item.capture_id || `r-${i}`}
            item={item}
            onRespond={(text) => handleRespond(item, text)}
            onSkip={() => handleSkip(item)}
          />
        )
      ))}

      {session && session.items.length > 0 && (
        <Text style={styles.sessionMeta}>
          Session {session.id} · {session.resonance_count} highlights
          {session.dialogue_count > 0 ? ` · ${session.dialogue_count} dialogue` : ''}
        </Text>
      )}
    </ScrollView>
  );
}

const cardStyles = StyleSheet.create({
  card: { marginHorizontal: layout.screenPadding, marginBottom: 20, paddingVertical: 16, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule },
  bookRow: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  cover: { width: 40, height: 56, borderRadius: 2 },
  coverPlaceholder: { backgroundColor: colors.parchmentDark, borderWidth: 1, borderColor: colors.rule, alignItems: 'center', justifyContent: 'center' },
  coverLetter: { fontFamily: fonts.displaySemiBold, fontSize: 18, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  bookInfo: { flex: 1, justifyContent: 'center' },
  bookTitle: { fontFamily: fonts.body, fontSize: 14, color: colors.ink, marginBottom: 2 },
  bookMeta: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted },
  highlightBox: { borderLeftWidth: 2, borderLeftColor: colors.rubric, paddingLeft: 12, marginBottom: 14 },
  highlightText: { fontFamily: fonts.reading, fontSize: 15, lineHeight: 22, color: colors.textBody },
  promptText: { fontFamily: fonts.body, fontSize: 14, lineHeight: 20, color: colors.rubric, marginBottom: 14 },
  actions: { flexDirection: 'row', gap: 10 },
  respondButton: { flex: 1, backgroundColor: colors.ink, paddingVertical: 10, borderRadius: 4, alignItems: 'center' },
  respondText: { fontFamily: fonts.body, fontSize: 13, color: colors.parchment },
  skipButton: { paddingVertical: 10, paddingHorizontal: 16 },
  skipText: { fontFamily: fonts.ui, fontSize: 13, color: colors.textMuted },
  inputArea: { gap: 8 },
  textInput: { borderWidth: 1, borderColor: colors.rule, borderRadius: 4, padding: 12, fontFamily: fonts.reading, fontSize: 14, color: colors.textBody, minHeight: 80, textAlignVertical: 'top' },
  inputActions: { flexDirection: 'row', justifyContent: 'flex-end' },
  sendButton: { backgroundColor: colors.ink, paddingVertical: 8, paddingHorizontal: 16, borderRadius: 4 },
  sendText: { fontFamily: fonts.body, fontSize: 13, color: colors.parchment },
  responded: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.claimNew, textAlign: 'center', paddingVertical: 12, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  dialogueLabel: { fontFamily: fonts.bodyItalic, fontSize: 12, color: colors.rubric, marginBottom: 12, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  claimBox: { borderLeftWidth: 2, borderLeftColor: colors.rule, paddingLeft: 12, marginBottom: 8 },
  claimBookLabel: { fontFamily: fonts.uiMedium, fontSize: 10, letterSpacing: 0.3, color: colors.textMuted, textTransform: 'uppercase', marginBottom: 4, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  claimText: { fontFamily: fonts.reading, fontSize: 14, lineHeight: 20, color: colors.textBody },
  vsText: { fontFamily: fonts.display, fontSize: 16, color: colors.textMuted, textAlign: 'center', marginVertical: 4 },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  content: { paddingBottom: 60, ...(Platform.OS === 'web' ? { maxWidth: layout.readingMeasure + 2 * layout.screenPadding, width: '100%', alignSelf: 'center' as const } : {}) },
  backButton: { paddingHorizontal: layout.screenPadding, paddingTop: 12, paddingBottom: 8 },
  backText: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  header: { paddingHorizontal: layout.screenPadding, paddingBottom: 12 },
  title: { fontFamily: fonts.displaySemiBold, fontSize: 28, color: colors.ink, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  subtitle: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textSecondary, marginTop: 4, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  loadingContainer: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', paddingVertical: 40 },
  loadingText: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  errorText: { fontFamily: fonts.reading, fontSize: 14, color: colors.rubric, textAlign: 'center', paddingVertical: 20, paddingHorizontal: layout.screenPadding },
  emptyContainer: { paddingVertical: 40, paddingHorizontal: layout.screenPadding, alignItems: 'center' },
  emptyText: { fontFamily: fonts.reading, fontSize: 16, color: colors.textSecondary, marginBottom: 8 },
  emptySubtext: { fontFamily: fonts.readingItalic, fontSize: 13, color: colors.textMuted, textAlign: 'center', ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  sessionMeta: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted, textAlign: 'center', paddingVertical: 20 },
});
