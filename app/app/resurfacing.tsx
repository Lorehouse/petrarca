import { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, TextInput,
  Platform, ActivityIndicator, KeyboardAvoidingView,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { logEvent } from '../data/logger';
import {
  generateResurfacingSession, respondToResurfacing, skipResurfacing,
  generateCurriculumReview, recordReviewResult,
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

function RetrievalCard({
  item,
  onResult,
}: {
  item: ResurfacingItem;
  onResult: (result: string) => void;
}) {
  const [revealed, setRevealed] = useState(false);
  const [graded, setGraded] = useState(false);

  const answerType = item.answer_type || item.question_type || 'concept';
  const typeLabel = answerType === 'date' ? 'Date'
    : answerType === 'name' ? 'Identity'
    : answerType === 'sequence' ? 'Timeline'
    : answerType === 'concept' ? 'Concept'
    : item.type === 'temporal_ordering' ? 'Timeline'
    : 'Event';

  // Grading options based on answer type
  const gradingButtons = answerType === 'date' ? [
    { value: 'exact_year', label: 'Exact year', style: 'correct' as const },
    { value: 'right_decade', label: 'Right decade', style: 'partial' as const },
    { value: 'right_century', label: 'Right century', style: 'weak' as const },
    { value: 'missed', label: 'Missed', style: 'wrong' as const },
  ] : answerType === 'name' ? [
    { value: 'correct', label: 'Knew it', style: 'correct' as const },
    { value: 'wrong', label: 'Didn\'t know', style: 'wrong' as const },
  ] : answerType === 'sequence' ? [
    { value: 'all_correct', label: 'All correct', style: 'correct' as const },
    { value: 'mostly_right', label: 'Mostly right', style: 'partial' as const },
    { value: 'wrong', label: 'Wrong order', style: 'wrong' as const },
  ] : [
    { value: 'correct', label: 'Knew it', style: 'correct' as const },
    { value: 'partial', label: 'Partially', style: 'partial' as const },
    { value: 'missed', label: 'Didn\'t know', style: 'wrong' as const },
  ];

  const handleGrade = (result: string) => {
    onResult(result);
    setGraded(true);
  };

  if (graded) {
    return (
      <View style={cardStyles.card}>
        <Text style={cardStyles.responded}>Recorded {'\u2713'}</Text>
      </View>
    );
  }

  const displayAnswer = item.rich_answer || item.answer || '';
  const anchors = item.anchors || [];

  return (
    <View style={cardStyles.card}>
      {/* Type badge + node */}
      <View style={retrievalStyles.headerRow}>
        <View style={retrievalStyles.typeBadge}>
          <Text style={retrievalStyles.typeBadgeText}>{typeLabel}</Text>
        </View>
        {item.node_title ? (
          <Text style={retrievalStyles.nodeTitle}>{item.node_title}</Text>
        ) : item.cluster_label ? (
          <Text style={retrievalStyles.nodeTitle}>{item.cluster_label}</Text>
        ) : null}
      </View>

      {/* Question */}
      <Text style={retrievalStyles.question}>{item.question}</Text>

      {/* Reveal / Answer */}
      {!revealed ? (
        <Pressable style={retrievalStyles.revealButton} onPress={() => setRevealed(true)}>
          <Text style={retrievalStyles.revealText}>Show answer</Text>
        </Pressable>
      ) : (
        <View>
          {/* Rich answer */}
          <View style={retrievalStyles.answerBox}>
            <Text style={retrievalStyles.answerText}>{displayAnswer}</Text>
          </View>

          {/* Memory hook */}
          {item.memory_hook ? (
            <View style={retrievalStyles.hookBox}>
              <Text style={retrievalStyles.hookLabel}>{'\u2726'} Memory hook</Text>
              <Text style={retrievalStyles.hookText}>{item.memory_hook}</Text>
            </View>
          ) : null}

          {/* Temporal anchors */}
          {anchors.length > 0 ? (
            <View style={retrievalStyles.anchorBox}>
              {anchors.map((a, i) => (
                <Text key={i} style={retrievalStyles.anchorText}>{'\u2022'} {a}</Text>
              ))}
            </View>
          ) : null}

          {/* Grading buttons */}
          <View style={retrievalStyles.gradeRow}>
            {gradingButtons.map(btn => (
              <Pressable
                key={btn.value}
                style={[
                  retrievalStyles.gradeButton,
                  btn.style === 'correct' ? retrievalStyles.gradeCorrect
                    : btn.style === 'partial' ? retrievalStyles.gradePartial
                    : btn.style === 'weak' ? retrievalStyles.gradeWeak
                    : retrievalStyles.gradeWrong,
                ]}
                onPress={() => handleGrade(btn.value)}
              >
                <Text style={[
                  btn.style === 'correct' ? retrievalStyles.gradeCorrectText
                    : btn.style === 'partial' ? retrievalStyles.gradePartialText
                    : btn.style === 'weak' ? retrievalStyles.gradeWeakText
                    : retrievalStyles.gradeWrongText,
                ]}>{btn.label}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}

type SessionMode = 'revisit' | 'review';

export default function ResurfacingScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<SessionMode>('review');
  const [session, setSession] = useState<ResurfacingSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadSession = useCallback(async (m: SessionMode) => {
    setLoading(true);
    setError('');
    setSession(null);
    try {
      const s = m === 'review'
        ? await generateCurriculumReview()
        : await generateResurfacingSession(true);
      setSession(s);
      logEvent(m === 'review' ? 'review_session_loaded' : 'resurfacing_session_loaded', {
        session_id: s.id,
        item_count: s.items?.length ?? 0,
      });
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => {
    let cancelled = false;
    (async () => {
      if (!cancelled) await loadSession(mode);
    })();
    return () => { cancelled = true; };
  }, [mode]));

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

  const handleReviewResult = async (item: ResurfacingItem, result: string) => {
    if (item.question_id) {
      await recordReviewResult(item.question_id, result);
      logEvent('review_result', {
        question_id: item.question_id,
        result,
        question_type: item.question_type || item.type,
        domain: item.domain,
      });
    }
  };

  const switchMode = (m: SessionMode) => {
    setMode(m);
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>{'\u2039'} Library</Text>
      </Pressable>

      <View style={styles.header}>
        <Text style={styles.title}>{mode === 'review' ? 'Review' : 'Revisit'}</Text>
        <Text style={styles.subtitle}>
          {mode === 'review'
            ? 'Test your recall — dates, people, events'
            : 'Reconnect with ideas from your reading'}
        </Text>
      </View>
      <DoubleRule />

      {/* Mode toggle */}
      <View style={styles.modeToggle}>
        <Pressable
          style={[styles.modeButton, mode === 'review' && styles.modeButtonActive]}
          onPress={() => switchMode('review')}
        >
          <Text style={[styles.modeText, mode === 'review' && styles.modeTextActive]}>Review</Text>
        </Pressable>
        <Pressable
          style={[styles.modeButton, mode === 'revisit' && styles.modeButtonActive]}
          onPress={() => switchMode('revisit')}
        >
          <Text style={[styles.modeText, mode === 'revisit' && styles.modeTextActive]}>Revisit</Text>
        </Pressable>
      </View>

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
          <Text style={styles.emptyText}>
            {mode === 'review' ? 'No review questions available.' : 'Nothing to revisit yet.'}
          </Text>
          <Text style={styles.emptySubtext}>
            {mode === 'review'
              ? 'Generate retrieval questions from a curriculum first.'
              : 'Add and read books to start building your resurfacing pool.'}
          </Text>
        </View>
      )}

      {session?.items.map((item, i) => {
        if (item.type === 'retrieval' || item.type === 'temporal_ordering') {
          return (
            <RetrievalCard
              key={item.question_id || `rv-${i}`}
              item={item}
              onResult={(result) => handleReviewResult(item, result)}
            />
          );
        }
        if (item.type === 'dialogue') {
          return (
            <DialogueCard
              key={`d-${i}`}
              item={item}
              onRespond={(text) => handleRespond(item, text)}
              onSkip={() => handleSkip(item)}
            />
          );
        }
        return (
          <ResonanceCard
            key={item.capture_id || `r-${i}`}
            item={item}
            onRespond={(text) => handleRespond(item, text)}
            onSkip={() => handleSkip(item)}
          />
        );
      })}

      {session && session.items.length > 0 && (
        <Text style={styles.sessionMeta}>
          {mode === 'review'
            ? `${session.retrieval_count ?? 0} questions · ${session.ordering_count ?? 0} ordering`
            : `${session.resonance_count} highlights${session.dialogue_count > 0 ? ` · ${session.dialogue_count} dialogue` : ''}`
          }
        </Text>
      )}
    </ScrollView>
    </KeyboardAvoidingView>
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

const retrievalStyles = StyleSheet.create({
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  typeBadge: { backgroundColor: colors.ink, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 2 },
  typeBadgeText: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.parchment, textTransform: 'uppercase', letterSpacing: 0.5, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  nodeTitle: { fontFamily: fonts.bodyItalic, fontSize: 12, color: colors.textSecondary, flex: 1, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  question: { fontFamily: fonts.reading, fontSize: 16, lineHeight: 24, color: colors.ink, marginBottom: 16 },
  revealButton: { borderWidth: 1, borderColor: colors.rubric, borderRadius: 4, paddingVertical: 12, alignItems: 'center' },
  revealText: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  answerBox: { borderLeftWidth: 2, borderLeftColor: colors.claimNew, paddingLeft: 12, marginBottom: 16 },
  answerText: { fontFamily: fonts.reading, fontSize: 15, lineHeight: 22, color: colors.textBody },
  gradeRow: { flexDirection: 'row', gap: 8 },
  gradeButton: { flex: 1, paddingVertical: 10, borderRadius: 4, alignItems: 'center', borderWidth: 1 },
  gradeWrong: { borderColor: colors.rubric, backgroundColor: 'rgba(139,37,0,0.05)' },
  gradeWrongText: { fontFamily: fonts.ui, fontSize: 12, color: colors.rubric },
  gradePartial: { borderColor: colors.textMuted, backgroundColor: 'rgba(176,168,152,0.08)' },
  gradePartialText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary },
  gradeCorrect: { borderColor: colors.claimNew, backgroundColor: 'rgba(42,122,74,0.05)' },
  gradeCorrectText: { fontFamily: fonts.ui, fontSize: 12, color: colors.claimNew },
  gradeWeak: { borderColor: '#b8860b', backgroundColor: 'rgba(184,134,11,0.06)' },
  gradeWeakText: { fontFamily: fonts.ui, fontSize: 12, color: '#b8860b' },
  hookBox: { backgroundColor: 'rgba(139,37,0,0.04)', borderLeftWidth: 2, borderLeftColor: colors.rubric, paddingLeft: 12, paddingVertical: 8, marginBottom: 12, borderRadius: 2 },
  hookLabel: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.rubric, letterSpacing: 0.3, marginBottom: 4, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  hookText: { fontFamily: fonts.readingItalic, fontSize: 14, lineHeight: 20, color: colors.textBody, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  anchorBox: { marginBottom: 14 },
  anchorText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textSecondary, lineHeight: 18, marginBottom: 2 },
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
  modeToggle: { flexDirection: 'row', marginHorizontal: layout.screenPadding, marginBottom: 20, gap: 0, borderWidth: 1, borderColor: colors.rule, borderRadius: 4, overflow: 'hidden' },
  modeButton: { flex: 1, paddingVertical: 8, alignItems: 'center', backgroundColor: 'transparent' },
  modeButtonActive: { backgroundColor: colors.ink },
  modeText: { fontFamily: fonts.body, fontSize: 13, color: colors.textSecondary },
  modeTextActive: { color: colors.parchment },
});
