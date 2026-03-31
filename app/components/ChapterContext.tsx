import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, Pressable, StyleSheet, Platform, ActivityIndicator, Modal, ScrollView,
} from 'react-native';
import { colors, fonts, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { getChapterContext, type ChapterContextResult, type ChapterContextNode } from '../lib/review-api';

const KNOWLEDGE_DOT: Record<string, { color: string; label: string }> = {
  anchored: { color: colors.claimNew, label: 'Know well' },
  engaged: { color: '#6a8a4a', label: 'Partial' },
  mentioned: { color: colors.warning, label: 'Heard of' },
  unknown: { color: colors.rule, label: 'New' },
};

interface Props {
  bookId: string;
  chapterNumber: number;
  chapterTitle: string;
  mode: 'preview' | 'review';
  visible: boolean;
  onClose: () => void;
}

export default function ChapterContext({ bookId, chapterNumber, chapterTitle, mode, visible, onClose }: Props) {
  const [data, setData] = useState<ChapterContextResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assessmentAnswer, setAssessmentAnswer] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) {
      setData(null);
      setError(null);
      setAssessmentAnswer(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getChapterContext(bookId, chapterNumber, chapterTitle, mode)
      .then(result => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
          logEvent('chapter_context_loaded', {
            book_id: bookId, chapter: chapterNumber, mode,
            nodes: result.nodes?.length || 0,
          });
        }
      })
      .catch(e => {
        if (!cancelled) {
          setError('Could not load curriculum context');
          setLoading(false);
          logEvent('chapter_context_error', { book_id: bookId, chapter: chapterNumber, error: String(e) });
        }
      });

    return () => { cancelled = true; };
  }, [visible, bookId, chapterNumber, chapterTitle, mode]);

  const handleAssessment = useCallback((answer: string) => {
    setAssessmentAnswer(answer);
    if (data?.assessment_question) {
      logEvent('chapter_context_assessment', {
        book_id: bookId, chapter: chapterNumber,
        node_id: data.assessment_question.node_id, answer,
      });
    }
  }, [data, bookId, chapterNumber]);

  const modeLabel = mode === 'preview'
    ? `Preview: Chapter ${chapterNumber}`
    : `After Chapter ${chapterNumber}`;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={s.backdrop} onPress={onClose}>
        <Pressable style={s.card} onPress={e => e.stopPropagation()}>
          <ScrollView showsVerticalScrollIndicator={false} style={s.scroll} contentContainerStyle={s.scrollContent}>
            {/* Header */}
            <View style={s.header}>
              <Text style={s.modeLabel}>{modeLabel}</Text>
              <Pressable onPress={onClose} hitSlop={12}>
                <Text style={s.closeBtn}>Close</Text>
              </Pressable>
            </View>
            {chapterTitle ? <Text style={s.chapterTitle}>{chapterTitle}</Text> : null}
            <View style={s.rule} />

            {/* Loading */}
            {loading && (
              <View style={s.loadingWrap}>
                <ActivityIndicator size="small" color={colors.rubric} />
                <Text style={s.loadingText}>
                  {mode === 'preview' ? 'Mapping chapter to curriculum...' : 'Generating review context...'}
                </Text>
              </View>
            )}

            {/* Error */}
            {error && <Text style={s.errorText}>{error}</Text>}

            {/* No nodes */}
            {data && data.nodes.length === 0 && (
              <Text style={s.emptyText}>{data.message || 'No curriculum nodes mapped to this chapter.'}</Text>
            )}

            {/* Content */}
            {data && data.nodes.length > 0 && (
              <>
                {/* Summary bar */}
                <View style={s.summaryBar}>
                  <View style={s.summaryItem}>
                    <Text style={s.summaryNum}>{data.summary.total}</Text>
                    <Text style={s.summaryLabel}>concepts</Text>
                  </View>
                  <View style={s.summaryItem}>
                    <Text style={[s.summaryNum, { color: colors.claimNew }]}>{data.summary.new}</Text>
                    <Text style={s.summaryLabel}>new</Text>
                  </View>
                  <View style={s.summaryItem}>
                    <Text style={[s.summaryNum, { color: '#6a8a4a' }]}>{data.summary.known}</Text>
                    <Text style={s.summaryLabel}>known</Text>
                  </View>
                </View>

                {/* Preview: what you'll learn */}
                {mode === 'preview' && (
                  <Text style={s.sectionTitle}>{'\u2726'} What you'll encounter</Text>
                )}
                {mode === 'review' && (
                  <Text style={s.sectionTitle}>{'\u2726'} What this chapter covered</Text>
                )}

                {/* Node list */}
                {data.nodes.map(node => (
                  <NodeCard key={node.node_id} node={node} mode={mode} />
                ))}

                {/* Preview: shaky prerequisites */}
                {mode === 'preview' && data.nodes.some(n => (n.shaky_prerequisites?.length ?? 0) > 0) && (
                  <>
                    <View style={[s.rule, { marginTop: 16 }]} />
                    <Text style={[s.sectionTitle, { color: colors.rubric }]}>
                      {'\u2726'} Shaky prerequisites
                    </Text>
                    <Text style={s.prereqHint}>
                      These underpin concepts in this chapter but you may not know them well yet.
                    </Text>
                    {data.nodes.flatMap(n => n.shaky_prerequisites || [])
                      .filter((p, i, arr) => arr.findIndex(x => x.node_id === p.node_id) === i)
                      .map(prereq => (
                        <View key={prereq.node_id} style={s.prereqRow}>
                          <View style={[s.dot, { backgroundColor: KNOWLEDGE_DOT[prereq.knowledge]?.color || colors.rule }]} />
                          <View style={{ flex: 1 }}>
                            <Text style={s.prereqTitle}>{prereq.node_title}</Text>
                            {prereq.description ? (
                              <Text style={s.prereqDesc} numberOfLines={2}>{prereq.description}</Text>
                            ) : null}
                          </View>
                        </View>
                      ))
                    }
                  </>
                )}

                {/* Review: assessment question */}
                {mode === 'review' && data.assessment_question && (
                  <>
                    <View style={[s.rule, { marginTop: 16 }]} />
                    <Text style={s.sectionTitle}>{'\u2726'} Quick self-check</Text>
                    <Text style={s.questionText}>{data.assessment_question.question}</Text>
                    <Text style={s.questionNode}>{data.assessment_question.node_title}</Text>
                    {assessmentAnswer ? (
                      <Text style={s.assessmentResult}>
                        {assessmentAnswer === 'knew' ? 'Got it.' : assessmentAnswer === 'some' ? 'Partially.' : 'Worth revisiting.'}
                      </Text>
                    ) : (
                      <View style={s.assessmentRow}>
                        {[
                          { key: 'new', label: 'New to me' },
                          { key: 'some', label: 'Somewhat' },
                          { key: 'knew', label: 'Knew this' },
                        ].map(opt => (
                          <Pressable key={opt.key} style={s.assessmentBtn} onPress={() => handleAssessment(opt.key)}>
                            <Text style={s.assessmentBtnText}>{opt.label}</Text>
                          </Pressable>
                        ))}
                      </View>
                    )}
                  </>
                )}
              </>
            )}
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function NodeCard({ node, mode }: { node: ChapterContextNode; mode: 'preview' | 'review' }) {
  const kDot = KNOWLEDGE_DOT[node.knowledge] || KNOWLEDGE_DOT.unknown;

  return (
    <View style={s.nodeCard}>
      <View style={s.nodeHeader}>
        <View style={[s.dot, { backgroundColor: kDot.color }]} />
        <Text style={s.nodeTitle}>{node.node_title}</Text>
        {mode === 'preview' && node.is_new && (
          <Text style={s.newBadge}>new</Text>
        )}
      </View>
      {node.description ? (
        <Text style={s.nodeDesc} numberOfLines={3}>{node.description}</Text>
      ) : null}
      {mode === 'review' && node.temporal_hook ? (
        <Text style={s.temporalHook}>{node.temporal_hook}</Text>
      ) : null}
      {node.lens ? <Text style={s.lensTag}>{node.lens}</Text> : null}
    </View>
  );
}

const s = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(42,36,32,0.55)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  card: {
    backgroundColor: colors.parchment,
    borderRadius: 8,
    maxWidth: 500,
    width: '100%',
    maxHeight: '85%',
    ...(Platform.OS === 'web' ? { maxHeight: '80vh' as any } : {}),
  },
  scroll: { flex: 1 },
  scrollContent: { padding: 20 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  modeLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  closeBtn: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.textSecondary,
  },
  chapterTitle: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 20,
    lineHeight: 25,
    color: colors.ink,
    marginBottom: 12,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  rule: {
    height: 2,
    backgroundColor: colors.rubric,
    width: 40,
    marginBottom: 14,
  },
  loadingWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 20,
  },
  loadingText: {
    fontFamily: fonts.readingItalic,
    fontSize: 13,
    color: colors.textMuted,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  errorText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.rubric,
    paddingVertical: 16,
  },
  emptyText: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textMuted,
    paddingVertical: 16,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  summaryBar: {
    flexDirection: 'row',
    gap: 20,
    marginBottom: 16,
  },
  summaryItem: { alignItems: 'center' },
  summaryNum: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 22,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  summaryLabel: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
  },
  sectionTitle: {
    fontFamily: fonts.bodyItalic,
    fontSize: 12,
    color: colors.rubric,
    marginBottom: 10,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  // Node card
  nodeCard: {
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  nodeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  nodeTitle: {
    fontFamily: fonts.bodyMedium,
    fontSize: 14,
    color: colors.ink,
    flex: 1,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  newBadge: {
    fontFamily: fonts.uiMedium,
    fontSize: 9,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    color: colors.claimNew,
    borderWidth: 1,
    borderColor: colors.claimNew,
    borderRadius: 3,
    paddingHorizontal: 5,
    paddingVertical: 1,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  nodeDesc: {
    fontFamily: fonts.reading,
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    paddingLeft: 16,
  },
  temporalHook: {
    fontFamily: fonts.readingItalic,
    fontSize: 12,
    lineHeight: 17,
    color: colors.rubric,
    paddingLeft: 16,
    marginTop: 4,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  lensTag: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    paddingLeft: 16,
    marginTop: 2,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  // Prerequisites
  prereqHint: {
    fontFamily: fonts.reading,
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginBottom: 10,
  },
  prereqRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  prereqTitle: {
    fontFamily: fonts.bodyMedium,
    fontSize: 13,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  prereqDesc: {
    fontFamily: fonts.reading,
    fontSize: 12,
    lineHeight: 17,
    color: colors.textMuted,
    marginTop: 2,
  },
  // Assessment
  questionText: {
    fontFamily: fonts.reading,
    fontSize: 15,
    lineHeight: 22,
    color: colors.textBody,
    marginBottom: 6,
  },
  questionNode: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  assessmentRow: {
    flexDirection: 'row',
    gap: 8,
  },
  assessmentBtn: {
    flex: 1,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: colors.rule,
    borderRadius: 4,
    alignItems: 'center',
  },
  assessmentBtnText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.textBody,
  },
  assessmentResult: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textSecondary,
    paddingVertical: 8,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
});
