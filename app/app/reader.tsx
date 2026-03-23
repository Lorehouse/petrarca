import React, { useState, useEffect, useRef, useCallback, useMemo, Component } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Linking,
  NativeSyntheticEvent, NativeScrollEvent,
  Platform, Clipboard, Animated,
} from 'react-native';
import AskAI from '../components/AskAI';
import VoiceFeedback from '../components/VoiceFeedback';
import DoubleRule from '../components/DoubleRule';
import { spawnTopicResearch, ingestUrl, getIngestStatus, reportBadScrape, generateMoreQuestions } from '../lib/chat-api';
import { addToQueue, addToQueueFront } from '../data/queue';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { getArticleById, getArticles, getReadingState, updateReadingState, getHighlightBlockIndices, addHighlight, removeHighlight, markArticleRead, recordInterestSignal, recordTopicInterestSignal, getCrossArticleConnections, getParagraphConnections, dismissArticle, getAdjacentArticleId } from '../data/store';
import type { FeedLens } from '../data/store';
import { Article, ArticleMeta, ArticleContent, ArticleEntity, FollowUpQuestion, InterestTopic } from '../data/types';
import { getArticleContent } from '../data/article-content';
import type { CrossArticleConnection } from '../data/knowledge-engine';
import * as Haptics from 'expo-haptics';
import { logEvent } from '../data/logger';
import { isSectionValid, parseInlineMarkdown, splitMarkdownBlocks, parseMarkdownBlock } from '../lib/markdown-utils';
import { getDisplayTitle } from '../lib/display-utils';
import { toggleBookmark, isBookmarked } from '../data/bookmarks';
import { getQueuedArticleIds, removeFromQueue } from '../data/queue';
import RelatedArticles from '../components/RelatedArticles';
import LinkToast from '../components/LinkToast';
import KeyboardHintBar from '../components/KeyboardHintBar';
import { useKeyboardShortcuts, type ShortcutMap } from '../hooks/useKeyboardShortcuts';
import { colors, fonts, type, spacing, layout } from '../design/tokens';
import { setFeedbackContext } from '../lib/feedback-context';
import {
  computeParagraphDimming, classifyArticleClaims,
  markArticleEncountered, markArticleReadUpTo, getArticleParagraphCount,
  isKnowledgeReady, getArticleNovelty, getSimilarArticles,
} from '../data/knowledge-engine';
import type { SimilarArticle } from '../data/knowledge-engine';

const SCROLL_POSITION_SAVE_INTERVAL_MS = 2000;

// --- Error Boundary ---

interface ReaderErrorBoundaryProps {
  articleId: string;
  onGoBack: () => void;
  children: React.ReactNode;
}

interface ReaderErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ReaderErrorBoundary extends Component<ReaderErrorBoundaryProps, ReaderErrorBoundaryState> {
  constructor(props: ReaderErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ReaderErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    logEvent('reader_error', { error: error.message, articleId: this.props.articleId });
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={errorBoundaryStyles.container}>
          <Text style={errorBoundaryStyles.title}>Something went wrong</Text>
          <Text style={errorBoundaryStyles.message}>{this.state.error?.message}</Text>
          <Pressable style={errorBoundaryStyles.button} onPress={this.props.onGoBack}>
            <Text style={errorBoundaryStyles.buttonText}>Go back</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}

const errorBoundaryStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  title: {
    fontFamily: fonts.ui,
    fontSize: 18,
    color: colors.ink,
    marginBottom: 8,
  },
  message: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 24,
  },
  button: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: colors.rule,
    borderRadius: 4,
  },
  buttonText: {
    fontFamily: fonts.ui,
    fontSize: 14,
    color: colors.rubric,
  },
});

// --- Types ---

type IngestStatus = 'processing' | 'queued' | 'failed';
interface IngestState {
  status: IngestStatus;
  ingestId: string;
  articleId: string;
}

type ReadingMode = 'full' | 'guided' | 'new_only';

interface ParagraphDimming {
  paragraph_index: number;
  opacity: number;
  novelty: 'novel' | 'mostly_novel' | 'mixed' | 'mostly_familiar' | 'familiar' | 'neutral';
  claim_counts: { new: number; extends: number; known: number };
}

interface ClaimClassification {
  claim_id: string;
  text: string;
  classification: 'NEW' | 'KNOWN' | 'EXTENDS';
  similarity_score: number;
  source_paragraphs: number[];
  claim_type: string;
}

interface ArticleNovelty {
  article_id: string;
  total_claims: number;
  new_claims: number;
  extends_claims: number;
  known_claims: number;
  novelty_ratio: number;
  curiosity_score: number;
}

// --- Paragraph to block mapping ---

function buildParagraphToBlockMap(content: string): Map<number, number[]> {
  const paragraphs = content.split('\n\n').map(p => p.trim()).filter(Boolean);
  const blocks = splitMarkdownBlocks(content);

  const map = new Map<number, number[]>();
  for (let pi = 0; pi < paragraphs.length; pi++) {
    const paraText = paragraphs[pi].toLowerCase();
    const blockIndices: number[] = [];
    for (let bi = 0; bi < blocks.length; bi++) {
      if (blocks[bi].toLowerCase().includes(paraText.slice(0, 50)) ||
          paraText.includes(blocks[bi].toLowerCase().slice(0, 50))) {
        blockIndices.push(bi);
      }
    }
    if (blockIndices.length > 0) map.set(pi, blockIndices);
  }
  return map;
}

// --- Animated Claim Item (stagger reveal) ---

function AnimatedClaimItem({ text, index }: { text: string; index: number }) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const delay = index * 80;
    const timer = setTimeout(() => {
      Animated.timing(anim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }, delay);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Animated.View style={[
      styles.noveltyItem,
      {
        opacity: anim,
        transform: [{
          translateY: anim.interpolate({
            inputRange: [0, 1],
            outputRange: [12, 0],
          }),
        }],
      },
    ]}>
      <View style={styles.noveltyDot} />
      <Text style={styles.noveltyText}>{text}</Text>
    </Animated.View>
  );
}

// --- Animated Highlight Wrap (long-press amber border fade-in) ---

function AnimatedHighlightWrap({ isHighlighted, children }: {
  isHighlighted: boolean;
  children: React.ReactNode;
}) {
  const anim = useRef(new Animated.Value(isHighlighted ? 1 : 0)).current;
  const prevHighlighted = useRef(isHighlighted);

  useEffect(() => {
    if (isHighlighted !== prevHighlighted.current) {
      prevHighlighted.current = isHighlighted;
      Animated.timing(anim, {
        toValue: isHighlighted ? 1 : 0,
        duration: 200,
        useNativeDriver: false,
      }).start();
    }
  }, [isHighlighted]);

  return (
    <View style={{ position: 'relative' }}>
      <Animated.View
        pointerEvents="none"
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: 0,
          width: 3,
          backgroundColor: '#c9a84c',
          opacity: anim,
        }}
      />
      <Animated.View style={{
        paddingLeft: anim.interpolate({
          inputRange: [0, 1],
          outputRange: [0, 10],
        }),
        backgroundColor: anim.interpolate({
          inputRange: [0, 1],
          outputRange: ['rgba(201, 168, 76, 0)', 'rgba(201, 168, 76, 0.15)'],
        }),
      }}>
        {children}
      </Animated.View>
    </View>
  );
}

// --- Animated Novelty Bar (knowledge bars with staggered fill) ---

function AnimatedNoveltyBar({ novelty, articleId }: { novelty: ArticleNovelty; articleId: string }) {
  const segments = [
    { value: novelty.new_claims, style: marginStyles.noveltyBarNew },
    { value: novelty.extends_claims || 0.01, style: marginStyles.noveltyBarExt },
    { value: novelty.known_claims || 0.01, style: marginStyles.noveltyBarKnown },
  ];
  const anims = useRef(segments.map(() => new Animated.Value(0))).current;
  const logged = useRef(false);

  useEffect(() => {
    const timers = segments.map((_, i) =>
      setTimeout(() => {
        Animated.timing(anims[i], {
          toValue: 1,
          duration: 400,
          useNativeDriver: false,
        }).start(() => {
          if (i === segments.length - 1 && !logged.current) {
            logged.current = true;
            logEvent('knowledge_bar_animated', { articleId });
          }
        });
      }, i * 60)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <View style={marginStyles.noveltyBar}>
      {segments.map((seg, i) => {
        const fraction = total > 0 ? seg.value / total : 0;
        const animatedWidth = anims[i].interpolate({
          inputRange: [0, 1],
          outputRange: ['0%', `${(fraction * 100).toFixed(1)}%`],
        });
        return (
          <Animated.View
            key={i}
            style={[seg.style, { flex: undefined, width: animatedWidth }] as any}
          />
        );
      })}
    </View>
  );
}

// --- Post-Read Interest Card (Hierarchical) ---

interface TopicGroup {
  broad: string;
  specifics: Array<{ specific: string; entities: string[] }>;
}

function groupTopicsByBroad(topics: InterestTopic[]): TopicGroup[] {
  const map = new Map<string, Map<string, string[]>>();
  for (const t of topics) {
    if (!map.has(t.broad)) map.set(t.broad, new Map());
    const specificMap = map.get(t.broad)!;
    if (!specificMap.has(t.specific)) specificMap.set(t.specific, []);
    if (t.entity) {
      const entities = specificMap.get(t.specific)!;
      if (!entities.includes(t.entity)) entities.push(t.entity);
    }
  }
  return Array.from(map.entries()).map(([broad, specificMap]) => ({
    broad,
    specifics: Array.from(specificMap.entries()).map(([specific, entities]) => ({ specific, entities })),
  }));
}

function formatTopicLabel(slug: string): string {
  return slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}


function stripLeadingTitle(text: string, title: string): string {
  if (!text) return '';
  const lines = text.split('\n');
  const firstLine = lines[0].replace(/^#+\s*/, '').trim();
  if (firstLine === title.trim()) {
    return lines.slice(1).join('\n').trimStart();
  }
  return text;
}

// --- Reading Mode Toggle ---

function ReadingModeToggle({ mode, onModeChange }: {
  mode: ReadingMode;
  onModeChange: (mode: ReadingMode) => void;
}) {
  const modes: { key: ReadingMode; label: string }[] = [
    { key: 'full', label: 'FULL' },
    { key: 'guided', label: 'GUIDED' },
    { key: 'new_only', label: 'NEW ONLY' },
  ];

  return (
    <View style={styles.readingModeContainer}>
      <View style={styles.readingModeTrack}>
        {modes.map(({ key, label }) => (
          <Pressable
            key={key}
            style={[
              styles.readingModeButton,
              mode === key && styles.readingModeButtonActive,
            ]}
            onPress={() => onModeChange(key)}
          >
            <Text style={[
              styles.readingModeLabel,
              mode === key && styles.readingModeLabelActive,
            ]}>
              {label}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// --- Inline markdown rendering ---

interface LinkHandler {
  ingestStates: Record<string, IngestState>;
  onIngest: (url: string) => void;
  onIngestQueued?: (url: string, articleId: string) => void;
}

function isIngestableUrl(url: string): boolean {
  if (!url.startsWith('http://') && !url.startsWith('https://')) return false;
  // Skip obvious non-article URLs
  const lower = url.toLowerCase();
  if (/\.(png|jpg|jpeg|gif|svg|webp|pdf|mp3|mp4|zip|tar|gz)(\?|$)/.test(lower)) return false;
  return true;
}

/** Extract a map of lowercased link text → URL from markdown text */
function extractLinkUrls(text: string): Map<string, string> {
  const map = new Map<string, string>();
  const re = /\[([^\]]+)\]\(([^)]+)\)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    map.set(m[1].toLowerCase(), m[2]);
  }
  return map;
}

function renderInlineMarkdown(
  text: string,
  linkHandler?: LinkHandler,
  entityNames?: Set<string>,
): (string | React.ReactElement)[] {
  const segments = parseInlineMarkdown(text);
  return segments.map((seg, i) => {
    switch (seg.type) {
      case 'link': {
        // If this link text matches an entity, render as plain text so EntityHighlightText can handle it
        if (entityNames && entityNames.has(seg.text.toLowerCase())) {
          return seg.text;
        }

        const canIngest = linkHandler && isIngestableUrl(seg.url);
        const ingestState = canIngest ? linkHandler.ingestStates[seg.url] : undefined;
        const linkStyle = canIngest ? styles.markdownLinkIngest : styles.markdownLinkExternal;
        const suffixChar = canIngest ? ' \u2295' : ' \u2197';

        return (
          <Text key={`link-${i}`}>
            <Text
              style={linkStyle}
              onPress={() => {
                if (canIngest && !ingestState) {
                  logEvent('reader_link_ingest', { url: seg.url, link_text: seg.text?.slice(0, 80) });
                  linkHandler.onIngest(seg.url);
                } else {
                  logEvent('reader_link_tap', { url: seg.url, link_text: seg.text?.slice(0, 80) });
                  Linking.openURL(seg.url);
                }
              }}
              onLongPress={() => {
                logEvent('reader_link_open', { url: seg.url });
                Linking.openURL(seg.url);
              }}
              {...(Platform.OS === 'web' ? { accessibilityRole: 'link', href: seg.url, hrefAttrs: { target: '_blank', rel: 'noopener noreferrer' } } as any : {})}
            >
              {seg.text}
            </Text>
            <Text style={styles.linkSuffix}>{suffixChar}</Text>
            {ingestState?.status === 'processing' && (
              <Text style={styles.ingestBadgeProcessing}>{' processing\u2026'}</Text>
            )}
            {ingestState?.status === 'queued' && (
              <Text style={styles.ingestBadgeQueued}>{' queued \u2713'}</Text>
            )}
            {ingestState?.status === 'failed' && (
              <Text style={styles.ingestBadgeFailed}>{' failed'}</Text>
            )}
          </Text>
        );
      }
      case 'bold':
        return <Text key={`bold-${i}`} style={styles.markdownBold}>{seg.text}</Text>;
      case 'italic':
        return <Text key={`italic-${i}`} style={styles.markdownItalic}>{seg.text}</Text>;
      case 'code':
        return <Text key={`code-${i}`} style={styles.markdownInlineCode}>{seg.text}</Text>;
      default:
        return seg.text;
    }
  });
}

// --- Collapsed familiar blocks bar ---

function CollapsedBar({ blockCount, onExpand }: {
  blockCount: number;
  onExpand: () => void;
}) {
  return (
    <Pressable style={styles.collapsedBar} onPress={onExpand}>
      <View style={styles.collapsedBarContent}>
        <View style={styles.collapsedBarDot} />
        <Text style={styles.collapsedBarText}>
          {blockCount} familiar {blockCount === 1 ? 'section' : 'sections'}
        </Text>
      </View>
      <Text style={styles.collapsedBarExpand}>{'▼'}</Text>
    </Pressable>
  );
}

// --- Entity Highlight Text ---

function EntityHighlightText({
  children,
  entities,
  onEntityPress,
  linkUrls,
}: {
  children: (string | React.ReactElement)[];
  entities: ArticleEntity[];
  onEntityPress: (entity: ArticleEntity, url?: string) => void;
  linkUrls?: Map<string, string>;
}) {
  if (!entities || entities.length === 0) return <>{children}</>;

  // Collect all mention strings, sorted longest-first to avoid partial matches
  const mentionMap = new Map<string, ArticleEntity>();
  for (const ent of entities) {
    for (const m of ent.mentions) {
      mentionMap.set(m.toLowerCase(), ent);
    }
  }
  const mentionKeys = Array.from(mentionMap.keys()).sort((a, b) => b.length - a.length);
  if (mentionKeys.length === 0) return <>{children}</>;

  // Build a case-insensitive regex that matches any mention
  const escaped = mentionKeys.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = new RegExp(`(${escaped.join('|')})`, 'gi');

  return (
    <>
      {children.map((child, ci) => {
        if (typeof child !== 'string') return child;
        const parts = child.split(pattern);
        if (parts.length === 1) return child;
        return parts.map((part, pi) => {
          const entity = mentionMap.get(part.toLowerCase());
          if (entity) {
            const url = linkUrls?.get(part.toLowerCase());
            return (
              <Text
                key={`ent-${ci}-${pi}`}
                style={[entityStyles.entityMention, url && entityStyles.entityMentionLinked]}
                onPress={() => {
                  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                  onEntityPress(entity, url);
                }}
              >
                {part}
              </Text>
            );
          }
          return part;
        });
      })}
    </>
  );
}

// --- Entity Popup ---

function EntityPopup({
  entity,
  articleTitle,
  url,
  onResearch,
  onIngest,
  onDismiss,
}: {
  entity: ArticleEntity;
  articleTitle: string;
  url?: string;
  onResearch: () => void;
  onIngest?: () => void;
  onDismiss: () => void;
}) {
  // Product pages, landing pages, company sites → research is better than raw ingest
  const isArticleLike = url ? /\/(blog|article|post|news|index|introducing|announce)/i.test(url) || /\.(md|html)(\?|$)/i.test(url) : false;

  return (
    <View style={entityStyles.popupContainer}>
      <Text style={entityStyles.popupType}>{entity.type.toUpperCase()}</Text>
      <Text style={entityStyles.popupName}>{entity.name}</Text>
      <Text style={entityStyles.popupSynthesis}>{entity.synthesis}</Text>
      {url && (
        <Pressable onPress={() => { logEvent('entity_open_url', { entity: entity.name, url }); Linking.openURL(url); }}>
          <Text style={entityStyles.popupUrl} numberOfLines={1}>{url.replace(/^https?:\/\/(www\.)?/, '')}</Text>
        </Pressable>
      )}
      <View style={entityStyles.popupActions}>
        {url && isArticleLike && onIngest && (
          <Pressable
            style={entityStyles.popupAction}
            onPress={() => {
              logEvent('entity_ingest_tap', { entity: entity.name, url, article_title: articleTitle });
              onIngest();
            }}
          >
            <Text style={entityStyles.popupActionResearch}>{'Save article \u2913'}</Text>
          </Pressable>
        )}
        <Pressable
          style={entityStyles.popupAction}
          onPress={() => {
            logEvent('entity_research_tap', { entity: entity.name, url, article_title: articleTitle });
            onResearch();
          }}
        >
          <Text style={entityStyles.popupActionResearch}>{'Research more \u2197'}</Text>
        </Pressable>
        <Pressable style={entityStyles.popupAction} onPress={onDismiss}>
          <Text style={entityStyles.popupActionDismiss}>Dismiss</Text>
        </Pressable>
      </View>
    </View>
  );
}

// --- Follow-up Research Prompts ---

function FollowUpSection({
  questions,
  articleTitle,
  articleId,
  articleSummary,
}: {
  questions: FollowUpQuestion[];
  articleTitle: string;
  articleId: string;
  articleSummary: string;
}) {
  const [launchedIndices, setLaunchedIndices] = useState<Set<number>>(new Set());
  const [extraQuestions, setExtraQuestions] = useState<FollowUpQuestion[]>([]);
  const [generating, setGenerating] = useState(false);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  if (!questions || questions.length === 0) return null;

  const allQuestions = [...questions, ...extraQuestions];

  const handleResearch = async (q: FollowUpQuestion, index: number) => {
    logEvent('research_prompt_tap', { article_id: articleId, question: q.question });
    try {
      await spawnTopicResearch(
        q.question,
        `From article: ${articleTitle}\nConnects to: ${q.connects_to}\nSummary: ${articleSummary}`,
        [articleTitle],
      );
      setLaunchedIndices(prev => new Set(prev).add(index));
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      logEvent('research_prompt_launched', { article_id: articleId, question: q.question, connects_to: q.connects_to });
    } catch (e) {
      logEvent('research_prompt_error', { article_id: articleId, error: String(e) });
    }
  };

  const handleGenerateMore = async () => {
    logEvent('further_inquiry_generate_more', { article_id: articleId, existing_count: allQuestions.length });
    setGenerating(true);

    // Pulsing animation for the ✦
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 600, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      ])
    );
    pulse.start();

    try {
      const existingTexts = allQuestions.map(q => q.question);
      const newQuestions = await generateMoreQuestions(articleId, existingTexts);
      setExtraQuestions(prev => [...prev, ...newQuestions]);
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      logEvent('further_inquiry_generated', { article_id: articleId, new_count: newQuestions.length });
    } catch (e) {
      logEvent('further_inquiry_generate_error', { article_id: articleId, error: String(e) });
    } finally {
      pulse.stop();
      pulseAnim.setValue(1);
      setGenerating(false);
    }
  };

  return (
    <View style={followUpStyles.container}>
      <Text style={followUpStyles.sectionTitle}>{'\u2726 FURTHER INQUIRY'}</Text>
      {allQuestions.map((q, i) => (
        <View key={i} style={followUpStyles.questionCard}>
          <Text style={followUpStyles.questionText}>{q.question}</Text>
          <Text style={followUpStyles.connectsTo}>{q.connects_to}</Text>
          {launchedIndices.has(i) ? (
            <Text style={followUpStyles.launchedText}>{'\u2713 Research launched'}</Text>
          ) : (
            <Pressable
              style={followUpStyles.researchButton}
              onPress={() => handleResearch(q, i)}
            >
              <Text style={followUpStyles.researchButtonText}>{'Research this \u2197'}</Text>
            </Pressable>
          )}
        </View>
      ))}
      <Pressable
        style={followUpStyles.generateMoreButton}
        onPress={handleGenerateMore}
        disabled={generating}
      >
        {generating ? (
          <Animated.Text style={[followUpStyles.generateMoreText, { opacity: pulseAnim }]}>
            {'\u2726 Generating...'}
          </Animated.Text>
        ) : (
          <Text style={followUpStyles.generateMoreText}>{'More questions \u2197'}</Text>
        )}
      </Pressable>
    </View>
  );
}

// --- Follow Topics Section ---

function pickFollowChips(topics: InterestTopic[]): { label: string; topic: InterestTopic }[] {
  if (!topics || topics.length === 0) return [];
  const chips: { label: string; topic: InterestTopic }[] = [];
  const seen = new Set<string>();

  // First pass: entities (most specific, e.g. "Moss")
  for (const t of topics) {
    if (t.entity && !seen.has(t.entity)) {
      seen.add(t.entity);
      chips.push({ label: t.entity, topic: t });
      if (chips.length >= 2) break;
    }
  }

  // Second pass: specific topics (e.g. "agent collaboration tools")
  for (const t of topics) {
    const key = t.specific;
    if (!seen.has(key)) {
      seen.add(key);
      const label = key.replace(/-/g, ' ');
      chips.push({ label, topic: t });
      if (chips.length >= 3) break;
    }
  }

  return chips;
}

function FollowTopicsSection({ topics, articleId }: { topics: InterestTopic[]; articleId: string }) {
  const chips = useMemo(() => pickFollowChips(topics), [topics]);
  const [active, setActive] = useState<Set<string>>(new Set());

  if (chips.length === 0) return null;

  const toggle = (label: string, topic: InterestTopic) => {
    const next = new Set(active);
    const isOn = next.has(label);
    if (isOn) {
      next.delete(label);
      recordTopicInterestSignal('interest_chip_negative', topic);
      logEvent('follow_topic_off', { article_id: articleId, label, broad: topic.broad, specific: topic.specific });
    } else {
      next.add(label);
      recordTopicInterestSignal('interest_chip_positive', topic);
      logEvent('follow_topic_on', { article_id: articleId, label, broad: topic.broad, specific: topic.specific });
      if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    setActive(next);
  };

  return (
    <View style={followTopicStyles.container}>
      <Text style={followTopicStyles.sectionTitle}>{'\u2726 FOLLOW'}</Text>
      <View style={followTopicStyles.chipRow}>
        {chips.map(({ label, topic }) => {
          const isOn = active.has(label);
          return (
            <Pressable
              key={label}
              style={[followTopicStyles.chip, isOn && followTopicStyles.chipActive]}
              onPress={() => toggle(label, topic)}
            >
              <Text style={[followTopicStyles.chipText, isOn && followTopicStyles.chipTextActive]}>
                {label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

// --- Connected Reading Section ---

function ConnectedReadingSection({
  connections,
  articleId,
}: {
  connections: CrossArticleConnection[];
  articleId: string;
}) {
  const [queuedIds, setQueuedIds] = useState<Set<string>>(new Set());
  const router = useRouter();
  const allArticles = getArticles();

  if (!connections || connections.length === 0) return null;

  const handleQueue = async (connArticleId: string) => {
    await addToQueueFront(connArticleId);
    setQueuedIds(prev => new Set(prev).add(connArticleId));
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    logEvent('cross_article_queue', {
      source_article_id: articleId,
      target_article_id: connArticleId,
    });
  };

  const handleNavigate = (connArticleId: string) => {
    logEvent('cross_article_navigate', {
      source_article_id: articleId,
      target_article_id: connArticleId,
    });
    router.push({ pathname: '/reader', params: { id: connArticleId } });
  };

  return (
    <View style={connectedStyles.container}>
      <Text style={connectedStyles.sectionTitle}>{'\u2726 CONNECTED READING'}</Text>
      {connections.map((conn) => {
        const targetArticle = allArticles.find(a => a.id === conn.articleId);
        if (!targetArticle) return null;
        const title = getDisplayTitle(targetArticle);
        const readingState = getReadingState(conn.articleId);
        const isRead = readingState.status === 'read';
        const isAlreadyQueued = queuedIds.has(conn.articleId);

        return (
          <Pressable
            key={conn.articleId}
            style={[connectedStyles.card, isRead && connectedStyles.cardRead]}
            onLongPress={() => handleNavigate(conn.articleId)}
          >
            <Text
              style={[connectedStyles.cardTitle, isRead && connectedStyles.cardTitleRead]}
              numberOfLines={2}
            >
              {title}
            </Text>
            <View style={connectedStyles.cardMeta}>
              <Text style={connectedStyles.cardClaimCount}>
                {conn.sharedClaimCount} shared {conn.sharedClaimCount === 1 ? 'claim' : 'claims'}
              </Text>
              {isRead ? (
                <Text style={connectedStyles.cardReadLabel}>
                  {'read ' + formatTimeAgo(readingState.completed_at || readingState.last_read_at)}
                </Text>
              ) : isAlreadyQueued ? (
                <Text style={connectedStyles.cardQueuedLabel}>{'✓ Queued'}</Text>
              ) : (
                <Pressable
                  style={connectedStyles.queueButton}
                  onPress={() => handleQueue(conn.articleId)}
                  hitSlop={8}
                >
                  <Text style={connectedStyles.queueButtonText}>+ Queue</Text>
                </Pressable>
              )}
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

function formatTimeAgo(timestamp: number): string {
  if (!timestamp) return '';
  const days = Math.floor((Date.now() - timestamp) / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

function formatDate(d: string): string {
  try {
    const date = new Date(d);
    if (isNaN(date.getTime())) return d;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return d; }
}

// --- Inline Cross-Article Annotation ---

function InlineCrossArticleAnnotation({
  articleId: connArticleId,
  sourceArticleId,
}: {
  articleId: string;
  sourceArticleId: string;
}) {
  const [queued, setQueued] = useState(false);
  const router = useRouter();
  const allArticles = getArticles();
  const targetArticle = allArticles.find(a => a.id === connArticleId);

  if (!targetArticle) return null;

  const title = getDisplayTitle(targetArticle);
  const readingState = getReadingState(connArticleId);
  const isRead = readingState.status === 'read';

  return (
    <View style={connectedStyles.inlineAnnotation}>
      <Pressable
        onPress={async () => {
          if (!isRead && !queued) {
            await addToQueueFront(connArticleId);
            setQueued(true);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            logEvent('inline_cross_article_queue', {
              source_article_id: sourceArticleId,
              target_article_id: connArticleId,
            });
          }
        }}
        onLongPress={() => {
          logEvent('inline_cross_article_navigate', {
            source_article_id: sourceArticleId,
            target_article_id: connArticleId,
          });
          router.push({ pathname: '/reader', params: { id: connArticleId } });
        }}
      >
        <Text style={connectedStyles.inlineAnnotationText}>
          <Text style={connectedStyles.inlineAnnotationPrefix}>Also in: </Text>
          <Text style={[
            connectedStyles.inlineAnnotationTitle,
            isRead && connectedStyles.inlineAnnotationTitleRead,
          ]}>
            {title}
          </Text>
          {isRead ? (
            <Text style={connectedStyles.inlineAnnotationRead}>{' (read)'}</Text>
          ) : queued ? (
            <Text style={connectedStyles.inlineAnnotationQueued}>{' ✓ queued'}</Text>
          ) : (
            <Text style={connectedStyles.inlineAnnotationQueue}>{' · tap to queue'}</Text>
          )}
        </Text>
      </Pressable>
    </View>
  );
}

// --- Markdown renderer ---

function MarkdownText({ content, highlightedBlocks, onBlockLongPress, blockDimming, readingMode = 'full', entities, onEntityLongPress, linkHandler, paragraphConnections, sourceArticleId }: {
  content: string;
  highlightedBlocks?: Set<number>;
  onBlockLongPress?: (blockIndex: number, text: string) => void;
  blockDimming?: Map<number, { opacity: number; novelty: string }> | null;
  readingMode?: ReadingMode;
  entities?: ArticleEntity[];
  onEntityLongPress?: (entity: ArticleEntity, url?: string) => void;
  linkHandler?: LinkHandler;
  paragraphConnections?: Map<number, Array<{ articleId: string; claimText: string }>> | null;
  sourceArticleId?: string;
}) {
  const [expandedCollapsedRanges, setExpandedCollapsedRanges] = useState(new Set<number>());

  if (!content) return null;
  const blocks = splitMarkdownBlocks(content);

  // Build collapsed ranges for new_only mode
  type RenderItem =
    | { type: 'block'; index: number }
    | { type: 'collapsed'; startIndex: number; count: number; blockIndices: number[] };

  const renderBlocks: RenderItem[] = [];

  if (readingMode === 'new_only' && blockDimming) {
    let i = 0;
    while (i < blocks.length) {
      const dimming = blockDimming.get(i);
      const isFamiliar = dimming && dimming.opacity < 0.7;

      if (isFamiliar) {
        const startIndex = i;
        const familiarIndices: number[] = [];
        while (i < blocks.length) {
          const d = blockDimming.get(i);
          if (d && d.opacity < 0.7) {
            familiarIndices.push(i);
            i++;
          } else {
            break;
          }
        }
        renderBlocks.push({ type: 'collapsed', startIndex, count: familiarIndices.length, blockIndices: familiarIndices });
      } else {
        renderBlocks.push({ type: 'block', index: i });
        i++;
      }
    }
  } else {
    for (let i = 0; i < blocks.length; i++) {
      renderBlocks.push({ type: 'block', index: i });
    }
  }

  function renderSingleBlock(raw: string, i: number, opacityOverride?: number) {
    const block = parseMarkdownBlock(raw);
    const isHighlighted = highlightedBlocks?.has(i);
    const dimming = blockDimming?.get(i);

    // In guided mode, apply opacity from the dimming map
    const blockOpacity = readingMode === 'guided' && dimming ? dimming.opacity : opacityOverride ?? 1;
    const opacityStyle = blockOpacity < 1 ? { opacity: blockOpacity } : undefined;

    // Novel marker: green left border on novel paragraphs in guided/new_only modes
    const isNovel = dimming && (dimming.novelty === 'novel' || dimming.novelty === 'mostly_novel') && readingMode !== 'full';
    const novelMarkerStyle = isNovel ? { borderLeftWidth: 2, borderLeftColor: colors.claimNew, paddingLeft: 8 } as const : undefined;

    switch (block.type) {
      case 'heading':
        return (
          <View key={i} style={[opacityStyle, novelMarkerStyle]}>
            <Text style={[
              styles.markdownHeading,
              block.level === 1 && { fontSize: 22 },
              block.level === 2 && { fontSize: 19 },
              (block.level ?? 3) >= 3 && { fontSize: 17 },
            ]}>
              {renderInlineMarkdown(block.content, linkHandler)}
            </Text>
          </View>
        );

      case 'hr':
        return <View key={i} style={[styles.markdownHr, opacityStyle, novelMarkerStyle]} />;

      case 'ul':
        return (
          <AnimatedHighlightWrap key={i} isHighlighted={!!isHighlighted}>
            <Pressable
              style={[styles.markdownList, opacityStyle, novelMarkerStyle]}
              onLongPress={onBlockLongPress ? () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); onBlockLongPress(i, raw); } : undefined}
            >
              {(block.items || []).map((item, j) => (
                <View key={j} style={styles.markdownListItem}>
                  <Text style={styles.markdownBullet}>{'·'}</Text>
                  <Text style={styles.markdownText}>{renderInlineMarkdown(item, linkHandler)}</Text>
                </View>
              ))}
            </Pressable>
          </AnimatedHighlightWrap>
        );

      case 'ol':
        return (
          <AnimatedHighlightWrap key={i} isHighlighted={!!isHighlighted}>
            <Pressable
              style={[styles.markdownList, opacityStyle, novelMarkerStyle]}
              onLongPress={onBlockLongPress ? () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); onBlockLongPress(i, raw); } : undefined}
            >
              {(block.items || []).map((item, j) => (
                <View key={j} style={styles.markdownListItem}>
                  <Text style={styles.markdownOrderedBullet}>{j + 1}.</Text>
                  <Text style={styles.markdownText}>{renderInlineMarkdown(item, linkHandler)}</Text>
                </View>
              ))}
            </Pressable>
          </AnimatedHighlightWrap>
        );

      case 'code':
        return (
          <AnimatedHighlightWrap key={i} isHighlighted={!!isHighlighted}>
            <View style={[styles.codeBlock, opacityStyle, novelMarkerStyle]}>
              <Text style={styles.codeText}>{block.content}</Text>
            </View>
          </AnimatedHighlightWrap>
        );

      case 'blockquote':
        return (
          <AnimatedHighlightWrap key={i} isHighlighted={!!isHighlighted}>
            <Pressable
              onLongPress={onBlockLongPress ? () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); onBlockLongPress(i, raw); } : undefined}
              style={[styles.markdownBlockquote, opacityStyle, novelMarkerStyle]}
            >
              <Text style={styles.markdownBlockquoteText}>{renderInlineMarkdown(block.content, linkHandler)}</Text>
            </Pressable>
          </AnimatedHighlightWrap>
        );

      case 'table':
        return (
          <View key={i} style={[styles.tableContainer, opacityStyle, novelMarkerStyle]}>
            {block.headers && block.headers.length > 0 && (
              <View style={styles.tableRow}>
                {block.headers.map((h, hi) => (
                  <View key={hi} style={[styles.tableCell, styles.tableHeaderCell]}>
                    <Text style={styles.tableHeaderText}>{renderInlineMarkdown(h, linkHandler)}</Text>
                  </View>
                ))}
              </View>
            )}
            {(block.rows || []).map((row, ri) => (
              <View key={ri} style={[styles.tableRow, ri % 2 === 1 && styles.tableRowAlt]}>
                {row.map((cell, ci) => (
                  <View key={ci} style={styles.tableCell}>
                    <Text style={styles.tableCellText}>{renderInlineMarkdown(cell, linkHandler)}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        );

      default: {
        // Build entity name set so renderInlineMarkdown can yield linked entities as plain text
        const entityNameSet = entities && entities.length > 0
          ? new Set(entities.flatMap(e => e.mentions.map(m => m.toLowerCase())))
          : undefined;
        const blockLinkUrls = entityNameSet ? extractLinkUrls(block.content) : undefined;
        const inlineContent = renderInlineMarkdown(block.content, linkHandler, entityNameSet);
        const blockConnections = paragraphConnections?.get(i);
        // Deduplicate connections per article (show max 1 annotation per article per paragraph)
        const uniqueConnections = blockConnections
          ? Array.from(new Map(blockConnections.map(c => [c.articleId, c])).values()).slice(0, 2)
          : [];
        return (
          <AnimatedHighlightWrap key={i} isHighlighted={!!isHighlighted}>
            <Pressable
              onLongPress={onBlockLongPress ? () => { if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); onBlockLongPress(i, block.content); } : undefined}
              style={[opacityStyle, novelMarkerStyle]}
            >
              <Text style={styles.markdownText}>
                {entities && entities.length > 0 && onEntityLongPress ? (
                  <EntityHighlightText entities={entities} onEntityPress={onEntityLongPress} linkUrls={blockLinkUrls}>
                    {inlineContent}
                  </EntityHighlightText>
                ) : inlineContent}
              </Text>
            </Pressable>
            {uniqueConnections.map(conn => (
              <InlineCrossArticleAnnotation
                key={conn.articleId}
                articleId={conn.articleId}
                sourceArticleId={sourceArticleId || ''}
              />
            ))}
          </AnimatedHighlightWrap>
        );
      }
    }
  }

  return (
    <View>
      {renderBlocks.map((item, idx) => {
        if (item.type === 'collapsed') {
          const isExpanded = expandedCollapsedRanges.has(item.startIndex);
          if (isExpanded) {
            return (
              <View key={`collapsed-${item.startIndex}`}>
                {item.blockIndices.map((bi) => renderSingleBlock(blocks[bi], bi, colors.claimKnownOpacity))}
                <Pressable
                  style={styles.collapseBar}
                  onPress={() => {
                    setExpandedCollapsedRanges((prev: Set<number>) => {
                      const next = new Set(prev);
                      next.delete(item.startIndex);
                      return next;
                    });
                    logEvent('collapsed_bar_collapse', { block_count: item.count });
                  }}
                >
                  <Text style={styles.collapsedBarText}>{'▲ Collapse'}</Text>
                </Pressable>
              </View>
            );
          }
          return (
            <CollapsedBar
              key={`collapsed-${item.startIndex}`}
              blockCount={item.count}
              onExpand={() => {
                setExpandedCollapsedRanges((prev: Set<number>) => new Set(prev).add(item.startIndex));
                logEvent('collapsed_bar_expand', { block_count: item.count });
              }}
            />
          );
        }
        return renderSingleBlock(blocks[item.index], item.index);
      })}
    </View>
  );
}

// --- AI Chat context builder ---

function buildAIChatContext(article: Article): string {
  const parts = [
    `Title: ${article.title}`,
    `Author: ${article.author}`,
    `Source: ${article.hostname} (${article.source_url})`,
    `Type: ${article.content_type}`,
    `Summary: ${article.one_line_summary}`,
    '',
    `Full summary: ${article.full_summary}`,
  ];
  if (article.key_claims?.length) {
    parts.push('', 'Key claims:', ...article.key_claims.map(c => `- ${c}`));
  }
  if (article.interest_topics?.length) {
    parts.push('', 'Topics:', ...article.interest_topics.map(t => `- ${t.broad}: ${t.specific}`));
  }
  // Include article text (truncated to ~4000 chars to stay within context limits)
  if (article.content_markdown) {
    parts.push('', '--- Article text (truncated) ---', article.content_markdown.slice(0, 4000));
  }
  return parts.join('\n');
}

// --- Web Grid Style ---

const webGridStyle = Platform.OS === 'web' ? {
  display: 'grid' as any,
  gridTemplateColumns: `${layout.webReaderLeftMargin}px 1fr ${layout.webReaderRightMargin}px` as any,
  maxWidth: layout.webReaderMaxWidth,
  margin: '0 auto' as any,
  minHeight: '100vh' as any,
  gap: 0,
} as any : undefined;

// --- Web Left Margin ---

function ReaderLeftMargin({
  article,
  novelty,
  readingMode,
  onModeChange,
  bookmarked,
  onStar,
  onDismiss,
  onDone,
  onAskAI,
  scrollProgress,
  hasDimming,
  shortcuts,
}: {
  article: ArticleMeta;
  novelty: ArticleNovelty | null;
  readingMode: ReadingMode;
  onModeChange: (mode: ReadingMode) => void;
  bookmarked: boolean;
  onStar: () => void;
  onDismiss: () => void;
  onDone: () => void;
  onAskAI: () => void;
  scrollProgress: number;
  hasDimming: boolean;
  shortcuts: Record<string, { handler: () => void; label: string }>;
}) {
  const topics = article.interest_topics || [];
  const uniqueBroadTopics = [...new Set(topics.map(t => t.broad))];

  const stickyStyle = {
    position: 'sticky' as any,
    top: 42,
    alignSelf: 'start' as any,
    height: 'calc(100vh - 42px)' as any,
    overflowY: 'auto' as any,
  } as any;

  return (
    <View style={[marginStyles.leftMargin, stickyStyle]}>
      {/* Source */}
      <View style={marginStyles.metaBlock}>
        <Text style={marginStyles.metaLabel}>Source</Text>
        <Text style={marginStyles.metaValue} numberOfLines={1}>{article.hostname}</Text>
      </View>

      {/* Date */}
      {article.date ? (
        <View style={marginStyles.metaBlock}>
          <Text style={marginStyles.metaLabel}>Published</Text>
          <Text style={marginStyles.metaValue}>{formatDate(article.date)}</Text>
        </View>
      ) : null}

      {/* Length */}
      <View style={marginStyles.metaBlock}>
        <Text style={marginStyles.metaLabel}>Length</Text>
        <Text style={marginStyles.metaValue}>
          {article.estimated_read_minutes} min{article.word_count ? ` \u00B7 ${article.word_count.toLocaleString()} words` : ''}
        </Text>
      </View>

      {/* Topics */}
      {uniqueBroadTopics.length > 0 ? (
        <View style={marginStyles.metaBlock}>
          <Text style={marginStyles.metaLabel}>Topics</Text>
          {uniqueBroadTopics.map((t, i) => (
            <Text key={i} style={marginStyles.topicText}>{formatTopicLabel(t)}</Text>
          ))}
        </View>
      ) : null}

      {/* Novelty bar */}
      {novelty ? (
        <View style={marginStyles.noveltyBlock}>
          <Text style={marginStyles.metaLabel}>Novelty</Text>
          <AnimatedNoveltyBar novelty={novelty} articleId={article.id} />
          <Text style={marginStyles.noveltyCounts}>
            {novelty.new_claims} new {'\u00B7'} {novelty.extends_claims} ext {'\u00B7'} {novelty.known_claims} known
          </Text>
        </View>
      ) : null}

      {/* Reading mode toggle — text-based */}
      {hasDimming ? (
        <View style={marginStyles.modeBlock}>
          <Text style={marginStyles.metaLabel}>Reading mode</Text>
          <View style={marginStyles.modeRow}>
            {(['full', 'guided', 'new_only'] as ReadingMode[]).map((mode) => (
              <Pressable key={mode} onPress={() => onModeChange(mode)}>
                <Text style={[
                  marginStyles.modeText,
                  readingMode === mode && marginStyles.modeTextActive,
                ]}>
                  {mode === 'full' ? 'Full' : mode === 'guided' ? 'Guided' : 'New'}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}

      {/* Actions — text links */}
      <View style={marginStyles.actionsSection}>
        <Pressable onPress={onStar} style={marginStyles.actionLink}>
          <Text style={[marginStyles.actionLinkText, bookmarked && { color: colors.rubric }]}>
            {bookmarked ? '\u2605' : '\u2606'} {bookmarked ? 'Bookmarked' : 'Bookmark'}
          </Text>
        </Pressable>
        <Pressable onPress={onDone} style={marginStyles.actionLink}>
          <Text style={marginStyles.actionLinkText}>{'\u2713'} Mark as read</Text>
        </Pressable>
        <Pressable onPress={onDismiss} style={marginStyles.actionLink}>
          <Text style={marginStyles.actionLinkText}>{'\u2715'} Dismiss</Text>
        </Pressable>
        <Pressable onPress={onAskAI} style={marginStyles.actionLink}>
          <Text style={marginStyles.actionLinkText}>{'\u2726'} Ask AI</Text>
        </Pressable>
      </View>

      {/* Keyboard shortcuts */}
      <View style={marginStyles.shortcutsBlock}>
        {Object.entries(shortcuts).filter(([key]) => key !== '?').map(([key, s]) => (
          <View key={key} style={marginStyles.shortcutRow}>
            <View style={marginStyles.kbdBadge}>
              <Text style={marginStyles.kbdText}>{key}</Text>
            </View>
            <Text style={marginStyles.shortcutLabel}>{s.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

// --- Web Right Margin ---

function ReaderRightMargin({
  article,
  nextArticle,
  connections,
  followUpQuestions,
  onNavigateArticle,
  onUpNext,
}: {
  article: ArticleMeta;
  nextArticle: ArticleMeta | null;
  connections: CrossArticleConnection[];
  followUpQuestions: FollowUpQuestion[];
  onNavigateArticle: (id: string) => void;
  onUpNext: () => void;
}) {
  const allArticles = getArticles();
  const [launchedIndices, setLaunchedIndices] = useState<Set<number>>(new Set());

  const stickyStyle = {
    position: 'sticky' as any,
    top: 42,
    alignSelf: 'start' as any,
    height: 'calc(100vh - 42px)' as any,
    overflowY: 'auto' as any,
  } as any;

  const handleResearch = async (q: FollowUpQuestion, index: number) => {
    logEvent('research_prompt_tap', { article_id: article.id, question: q.question });
    try {
      await spawnTopicResearch(
        q.question,
        `From article: ${article.title}\nConnects to: ${q.connects_to}\nSummary: ${article.one_line_summary}`,
        [article.title],
      );
      setLaunchedIndices(prev => new Set(prev).add(index));
      logEvent('research_prompt_launched', { article_id: article.id, question: q.question });
    } catch (e) {
      logEvent('research_prompt_error', { article_id: article.id, error: String(e) });
    }
  };

  // Related articles for right margin
  const relatedArticles = useMemo(() => {
    const topics = article.interest_topics || [];
    if (topics.length === 0) return [];
    const topicSet = new Set(topics.map(t => t.specific));
    const broadSet = new Set(topics.map(t => t.broad));
    const connIds = new Set(connections.map(c => c.articleId));
    const scored: { article: ArticleMeta; overlap: number }[] = [];
    for (const other of allArticles) {
      if (other.id === article.id || connIds.has(other.id)) continue;
      const otherTopics = other.interest_topics || [];
      let overlap = 0;
      for (const t of otherTopics) {
        if (topicSet.has(t.specific)) overlap += 2;
        else if (broadSet.has(t.broad)) overlap += 1;
      }
      if (overlap > 0) scored.push({ article: other, overlap });
    }
    scored.sort((a, b) => b.overlap - a.overlap);
    return scored.slice(0, 3).map(s => s.article);
  }, [article.id, allArticles, connections]);

  return (
    <View style={[marginStyles.rightMargin, stickyStyle]}>
      {/* Up Next */}
      {nextArticle ? (
        <View style={marginStyles.rightSection}>
          <Text style={marginStyles.rightSectionTitle}>Up next in queue</Text>
          <Pressable onPress={onUpNext} style={marginStyles.footnoteItem}>
            <Text style={marginStyles.footnoteText} numberOfLines={2}>{getDisplayTitle(nextArticle)}</Text>
            <Text style={marginStyles.footnoteMeta}>
              {nextArticle.hostname}{nextArticle.estimated_read_minutes ? ` \u00B7 ${nextArticle.estimated_read_minutes} min` : ''}
            </Text>
          </Pressable>
        </View>
      ) : null}

      {/* Connected reading */}
      {connections.length > 0 ? (
        <View style={marginStyles.rightSection}>
          <Text style={marginStyles.rightSectionTitle}>Connected reading</Text>
          {connections.map((conn) => {
            const target = allArticles.find(a => a.id === conn.articleId);
            if (!target) return null;
            return (
              <Pressable
                key={conn.articleId}
                style={marginStyles.footnoteItem}
                onPress={() => onNavigateArticle(conn.articleId)}
              >
                <Text style={marginStyles.footnoteText} numberOfLines={2}>{getDisplayTitle(target)}</Text>
                <Text style={marginStyles.footnoteMeta}>
                  {conn.sharedClaimCount} shared {conn.sharedClaimCount === 1 ? 'claim' : 'claims'}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}

      {/* Follow-up questions */}
      {followUpQuestions.length > 0 ? (
        <View style={marginStyles.rightSection}>
          <Text style={marginStyles.rightSectionTitle}>Further inquiry</Text>
          {followUpQuestions.slice(0, 3).map((q, i) => (
            <View key={i} style={marginStyles.inquiryItem}>
              <Text style={marginStyles.inquiryText} numberOfLines={3}>{q.question}</Text>
              {launchedIndices.has(i) ? (
                <Text style={marginStyles.researchLaunched}>{'\u2713 Launched'}</Text>
              ) : (
                <Pressable onPress={() => handleResearch(q, i)}>
                  <Text style={marginStyles.researchLink}>{'Research this \u2197'}</Text>
                </Pressable>
              )}
            </View>
          ))}
        </View>
      ) : null}

      {/* Related articles */}
      {relatedArticles.length > 0 ? (
        <View style={marginStyles.rightSection}>
          <Text style={marginStyles.rightSectionTitle}>Related</Text>
          {relatedArticles.map((a) => (
            <Pressable
              key={a.id}
              style={marginStyles.footnoteItem}
              onPress={() => onNavigateArticle(a.id)}
            >
              <Text style={marginStyles.footnoteText} numberOfLines={2}>{getDisplayTitle(a)}</Text>
              <Text style={marginStyles.footnoteMeta}>
                {a.hostname}{a.estimated_read_minutes ? ` \u00B7 ${a.estimated_read_minutes} min` : ''}
              </Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

// --- Main Reader Screen ---

export default function ReaderScreen() {
  const { id, lens, autoAdvanceFrom } = useLocalSearchParams<{ id: string; lens?: string; autoAdvanceFrom?: string }>();
  const router = useRouter();
  const feedLens = (lens || 'best') as FeedLens;
  const articleMeta = getArticleById(id || '');
  const [articleContent, setArticleContent] = useState<ArticleContent | null>(null);
  const [contentLoading, setContentLoading] = useState(true);

  // Lazy-load article content
  useEffect(() => {
    if (!id) return;
    setContentLoading(true);
    getArticleContent(id).then(content => {
      setArticleContent(content);
      setContentLoading(false);
    });
  }, [id]);

  // Composite article object for compatibility with existing code
  const article = useMemo(() => {
    if (!articleMeta) return undefined;
    if (!articleContent) return { ...articleMeta, content_markdown: '', sections: [] } as Article;
    return { ...articleMeta, ...articleContent } as Article;
  }, [articleMeta, articleContent]);

  const scrollRef = useRef<ScrollView>(null);
  const enterTime = useRef(Date.now());
  const lastScrollY = useRef(0);
  const lastPositionSaveTime = useRef(0);
  const scrollMilestone = useRef(0);
  const [highlightedBlocks, setHighlightedBlocks] = useState<Set<number>>(new Set());
  const [readingMode, setReadingMode] = useState<ReadingMode>('guided');
  const [scrollProgress, setScrollProgress] = useState(0);

  // Sync feedback context with reading state
  useEffect(() => { setFeedbackContext({ readingMode, scrollProgress: Math.round(scrollProgress) }); }, [readingMode, scrollProgress]);
  const [bookmarked, setBookmarked] = useState(() => article ? isBookmarked(article.id) : false);
  const [showMenu, setShowMenu] = useState(false);
  const [showAIChat, setShowAIChat] = useState(false);
  const [showVoiceFeedback, setShowVoiceFeedback] = useState(false);
  const [activeEntity, setActiveEntity] = useState<ArticleEntity | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [linkToast, setLinkToast] = useState<{ domain: string; articleId: string } | null>(null);
  const voicePulseAnim = useRef(new Animated.Value(1)).current;

  // Adjacent articles for top bar navigation
  const prevArticleId = useMemo(() => article ? getAdjacentArticleId(article.id, 'prev', feedLens) : null, [article, feedLens]);
  const nextArticleId = useMemo(() => article ? getAdjacentArticleId(article.id, 'next', feedLens) : null, [article, feedLens]);
  const prevArticle = prevArticleId ? getArticleById(prevArticleId) : null;
  const nextArticle = nextArticleId ? getArticleById(nextArticleId) : null;

  // Cross-article connections
  const crossArticleConnections = useMemo(() => {
    if (!article) return [];
    return getCrossArticleConnections(article.id);
  }, [article]);

  const paragraphConnections = useMemo(() => {
    if (!article) return null;
    return getParagraphConnections(article.id);
  }, [article]);

  const contentHeight = useRef(0);
  const viewportHeight = useRef(0);
  const maxScrollY = useRef(0);
  const completionFlash = useRef(new Animated.Value(0)).current;

  // Auto-clear status toast
  useEffect(() => {
    if (!statusMessage) return;
    const t = setTimeout(() => setStatusMessage(null), 2000);
    return () => clearTimeout(t);
  }, [statusMessage]);


  // Voice note pulsing animation
  useEffect(() => {
    if (showVoiceFeedback) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(voicePulseAnim, { toValue: 0.3, duration: 600, useNativeDriver: true }),
          Animated.timing(voicePulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ]),
      );
      pulse.start();
      return () => pulse.stop();
    } else {
      voicePulseAnim.setValue(1);
    }
  }, [showVoiceFeedback]);

  // --- Keyboard shortcuts (web only) ---
  const readingModes: ReadingMode[] = ['full', 'guided', 'new_only'];
  const readerShortcuts = useMemo((): ShortcutMap => {
    if (!article) return {};
    return {
      j: { handler: () => {
        const next = getAdjacentArticleId(article.id, 'next', feedLens);
        if (next) router.replace({ pathname: '/reader', params: { id: next, lens: feedLens } });
      }, label: 'next' },
      k: { handler: () => {
        const prev = getAdjacentArticleId(article.id, 'prev', feedLens);
        if (prev) router.replace({ pathname: '/reader', params: { id: prev, lens: feedLens } });
      }, label: 'prev' },
      Escape: { handler: () => router.back(), label: 'back' },
      s: { handler: () => {
        const next = !bookmarked;
        toggleBookmark(article.id);
        setBookmarked(next);
        setStatusMessage(next ? 'Bookmarked' : 'Unbookmarked');
      }, label: 'star' },
      e: { handler: () => {
        dismissArticle(article.id, 'keyboard');
        recordInterestSignal('swipe_dismiss', article.id);
        setStatusMessage('Disregarded');
        setTimeout(() => router.back(), 600);
      }, label: 'disregard' },
      d: { handler: () => handleDone(), label: 'done' },
      m: { handler: () => {
        const idx = readingModes.indexOf(readingMode);
        setReadingMode(readingModes[(idx + 1) % readingModes.length]);
      }, label: 'mode' },
      a: { handler: () => setShowAIChat(true), label: 'ask AI' },
      gi: { handler: () => router.replace('/'), label: 'go to index' },
      '?': { handler: () => {}, label: 'shortcuts' },
    };
  }, [article, bookmarked, readingMode, feedLens, router]);

  useKeyboardShortcuts(readerShortcuts, !showAIChat && !showVoiceFeedback && !showMenu);

  // Link ingestion state
  const [ingestStates, setIngestStates] = useState<Record<string, IngestState>>({});
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  const handleLinkIngest = useCallback(async (url: string) => {
    if (ingestStates[url]) return; // Already ingesting
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    try {
      const result = await ingestUrl(url, 'reader_link');
      setIngestStates(prev => ({
        ...prev,
        [url]: { status: 'processing', ingestId: result.ingest_id, articleId: result.article_id },
      }));

      // Poll for completion
      const timer = setInterval(async () => {
        try {
          const status = await getIngestStatus(result.ingest_id);
          if (status.status === 'completed') {
            clearInterval(timer);
            delete pollTimers.current[url];
            setIngestStates(prev => ({
              ...prev,
              [url]: { ...prev[url], status: 'queued' },
            }));
            await addToQueue(result.article_id);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            try {
              const domain = new URL(url).hostname.replace(/^www\./, '');
              setLinkToast({ domain, articleId: result.article_id });
            } catch {}
            logEvent('reader_link_queued', { url, article_id: result.article_id });
          } else if (status.status === 'failed') {
            clearInterval(timer);
            delete pollTimers.current[url];
            setIngestStates(prev => ({
              ...prev,
              [url]: { ...prev[url], status: 'failed' },
            }));
          }
        } catch {
          // Poll errors are transient, keep trying
        }
      }, 5000);
      pollTimers.current[url] = timer;
    } catch {
      setIngestStates(prev => ({
        ...prev,
        [url]: { status: 'failed', ingestId: '', articleId: '' },
      }));
    }
  }, [ingestStates]);

  // Clean up polling timers on unmount
  useEffect(() => {
    return () => {
      Object.values(pollTimers.current).forEach(clearInterval);
    };
  }, []);

  const linkHandler = useMemo<LinkHandler>(() => ({
    ingestStates,
    onIngest: handleLinkIngest,
  }), [ingestStates, handleLinkIngest]);

  // Next queued article for "Up next" footer
  const nextQueuedArticle = useMemo(() => {
    const queuedIds = getQueuedArticleIds();
    const nextId = queuedIds.find(qId => qId !== id);
    if (!nextId) return null;
    return getArticleById(nextId) || null;
  }, [id]);

  // Knowledge engine data
  const paragraphDimming = useMemo(() => {
    if (!article || !isKnowledgeReady()) return null;
    return computeParagraphDimming(article.id) as ParagraphDimming[] | null;
  }, [article?.id]);

  const claimClassifications = useMemo(() => {
    if (!article || !isKnowledgeReady()) return null;
    return classifyArticleClaims(article.id) as ClaimClassification[] | null;
  }, [article?.id]);

  const articleNovelty = useMemo(() => {
    if (!article || !isKnowledgeReady()) return null;
    return getArticleNovelty(article.id) as ArticleNovelty | null;
  }, [article?.id]);

  // Similar articles the user has already read
  const readSimilarArticles = useMemo(() => {
    if (!article || !isKnowledgeReady()) return [];
    const similar = getSimilarArticles(article.id, 0.52);
    const results: Array<{ id: string; title: string; score: number }> = [];
    for (const s of similar) {
      const state = getReadingState(s.articleId);
      if (state.status === 'read') {
        const a = getArticleById(s.articleId);
        if (a) {
          results.push({ id: a.id, title: getDisplayTitle(a), score: s.score });
        }
      }
    }
    return results.slice(0, 3);
  }, [article?.id]);

  // Verdict line based on novelty ratio
  const verdictLine = useMemo(() => {
    if (!articleNovelty || articleNovelty.total_claims === 0) return null;
    const { novelty_ratio, new_claims, extends_claims, known_claims } = articleNovelty;
    if (novelty_ratio > 0.9) return 'Almost entirely new territory';
    if (novelty_ratio > 0.7) return `Mostly new \u2014 ${known_claims} familiar anchor${known_claims !== 1 ? 's' : ''}`;
    if (novelty_ratio >= 0.4) return `Extends what you know \u2014 ${new_claims} new claim${new_claims !== 1 ? 's' : ''}, ${extends_claims} that deepen`;
    return `Mostly familiar \u2014 ${new_claims} new detail${new_claims !== 1 ? 's' : ''} worth scanning`;
  }, [articleNovelty]);

  // Skip nudge: show when >70% claims are known
  const skipNudge = useMemo(() => {
    if (!articleNovelty || articleNovelty.total_claims === 0) return null;
    const knownRatio = articleNovelty.known_claims / articleNovelty.total_claims;
    if (knownRatio <= 0.7) return null;
    const newCount = articleNovelty.new_claims + articleNovelty.extends_claims;
    return newCount;
  }, [articleNovelty]);

  // Build full article content — prefer sections if available
  const fullContent = useMemo(() => {
    if (!article) return '';
    return article.sections && article.sections.length > 0
      ? article.sections
          .filter(isSectionValid)
          .map(s => `## ${s.heading}\n\n${s.content}`)
          .join('\n\n')
      : stripLeadingTitle(article.content_markdown, article.title);
  }, [article?.id]);

  // Map paragraph-level dimming to block-level dimming
  const blockDimming = useMemo(() => {
    if (!paragraphDimming || !fullContent) return null;
    const paraToBlock = buildParagraphToBlockMap(fullContent);
    const blockMap = new Map<number, { opacity: number; novelty: string }>();
    for (const pd of paragraphDimming) {
      const blockIndices = paraToBlock.get(pd.paragraph_index) || [];
      for (const bi of blockIndices) {
        blockMap.set(bi, { opacity: pd.opacity, novelty: pd.novelty });
      }
    }
    return blockMap;
  }, [paragraphDimming, fullContent]);

  // Initialize reading state
  useEffect(() => {
    if (!article) return;
    const state = getReadingState(article.id);
    if (state.status === 'unread') {
      updateReadingState(article.id, { status: 'reading', started_at: Date.now(), last_read_at: Date.now() });
    } else {
      updateReadingState(article.id, { status: 'reading', last_read_at: Date.now() });
    }
    logEvent('reader_open', { article_id: article.id, title: article.title });
    setFeedbackContext({ screen: 'reader', articleId: article.id, articleTitle: getDisplayTitle(article), activeLens: feedLens });

    // Restore scroll position + ensure arrow-key scrolling works on web
    const savedY = state.scroll_position_y || 0;
    if (savedY > 0) {
      setTimeout(() => {
        if (Platform.OS === 'web') {
          window.scrollTo({ top: savedY });
        } else {
          scrollRef.current?.scrollTo({ y: savedY, animated: false });
        }
      }, 300);
    }
    let webStyleEl: HTMLStyleElement | null = null;
    const prevBodyOverflow = Platform.OS === 'web' ? document.body.style.overflow : '';
    if (Platform.OS === 'web') {
      // React Native Web sets body { overflow: hidden }, which blocks arrow-key scrolling.
      // Override to 'auto' so the browser handles scroll natively (arrow keys, Page Up/Down).
      document.body.style.overflow = 'auto';
      setTimeout(() => {
        (document.activeElement as HTMLElement)?.blur();
        document.body.focus();
      }, 100);
      // Suppress focus outlines on divs (React Native Web renders Views as divs)
      webStyleEl = document.createElement('style');
      webStyleEl.textContent = 'div:focus, body:focus { outline: none !important; }';
      document.head.appendChild(webStyleEl);
    }

    return () => {
      if (webStyleEl) document.head.removeChild(webStyleEl);
      if (Platform.OS === 'web') document.body.style.overflow = prevBodyOverflow;
      const elapsed = Date.now() - enterTime.current;
      const currentState = getReadingState(article.id);
      updateReadingState(article.id, {
        time_spent_ms: (currentState.time_spent_ms || 0) + elapsed,
        last_read_at: Date.now(),
        scroll_position_y: lastScrollY.current,
      });

      // Mark claims as encountered based on how far the user actually scrolled
      if (isKnowledgeReady() && contentHeight.current > 0) {
        const totalParas = getArticleParagraphCount(article.id);
        if (totalParas > 0) {
          const readUpToY = maxScrollY.current + viewportHeight.current;
          const readFraction = Math.min(1, readUpToY / contentHeight.current);
          const maxPara = Math.floor(readFraction * totalParas);
          const engagement = elapsed > 60000 ? 'read' : 'skim';
          markArticleReadUpTo(article.id, maxPara, engagement);
        }
      }

      logEvent('reader_close', { article_id: article.id, time_spent_ms: elapsed });
    };
  }, []);

  // Load highlights
  useEffect(() => {
    if (!article) return;
    setHighlightedBlocks(getHighlightBlockIndices(article.id));
  }, [article?.id]);

  // Scroll handler — save position periodically + track progress (mobile)
  const handleScroll = useCallback((event: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (!article) return;
    const { contentOffset, contentSize, layoutMeasurement } = event.nativeEvent;
    const scrollY = contentOffset.y;
    const now = Date.now();

    if (now - lastPositionSaveTime.current >= SCROLL_POSITION_SAVE_INTERVAL_MS) {
      lastPositionSaveTime.current = now;
      updateReadingState(article.id, { scroll_position_y: Math.round(scrollY) });
    }

    lastScrollY.current = scrollY;
    if (scrollY > maxScrollY.current) maxScrollY.current = scrollY;
    contentHeight.current = contentSize.height;
    viewportHeight.current = layoutMeasurement.height;

    const maxScroll = contentSize.height - layoutMeasurement.height;
    if (maxScroll > 0) {
      const pct = Math.min(100, Math.max(0, (scrollY / maxScroll) * 100));
      setScrollProgress(pct);
      // Log scroll milestones (25%, 50%, 75%, 100%)
      const milestone = Math.floor(pct / 25) * 25;
      if (milestone > 0 && milestone > (scrollMilestone.current || 0)) {
        scrollMilestone.current = milestone;
        logEvent('reader_scroll_milestone', { article_id: article.id, pct: milestone });
      }
    }
  }, [article]);

  // Web: use window scroll for progress tracking (browser handles scrolling)
  useEffect(() => {
    if (Platform.OS !== 'web' || !article) return;
    const onWindowScroll = () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight;
      const viewHeight = window.innerHeight;
      const maxScroll = docHeight - viewHeight;
      const now = Date.now();

      if (now - lastPositionSaveTime.current >= SCROLL_POSITION_SAVE_INTERVAL_MS) {
        lastPositionSaveTime.current = now;
        updateReadingState(article.id, { scroll_position_y: Math.round(scrollY) });
      }

      lastScrollY.current = scrollY;
      if (scrollY > maxScrollY.current) maxScrollY.current = scrollY;
      contentHeight.current = docHeight;
      viewportHeight.current = viewHeight;

      if (maxScroll > 0) {
        const pct = Math.min(100, Math.max(0, (scrollY / maxScroll) * 100));
        setScrollProgress(pct);
        const milestone = Math.floor(pct / 25) * 25;
        if (milestone > 0 && milestone > (scrollMilestone.current || 0)) {
          scrollMilestone.current = milestone;
          logEvent('reader_scroll_milestone', { article_id: article.id, pct: milestone });
        }
      }
    };
    window.addEventListener('scroll', onWindowScroll, { passive: true });
    return () => window.removeEventListener('scroll', onWindowScroll);
  }, [article]);

  // Highlight handler
  const handleBlockLongPress = useCallback((blockIndex: number, text: string) => {
    if (!article) return;
    const indices = getHighlightBlockIndices(article.id);
    if (indices.has(blockIndex)) {
      removeHighlight(article.id, blockIndex);
      setHighlightedBlocks((prev: Set<number>) => {
        const next = new Set(prev);
        next.delete(blockIndex);
        return next;
      });
      logEvent('reader_highlight_remove', { article_id: article.id, block_index: blockIndex });
    } else {
      addHighlight({
        id: `hl_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        article_id: article.id,
        block_index: blockIndex,
        text: text.slice(0, 500),
        highlighted_at: Date.now(),
        zone: 'full',
      });
      setHighlightedBlocks((prev: Set<number>) => new Set(prev).add(blockIndex));
      recordInterestSignal('highlight_paragraph', article.id);
      logEvent('paragraph_highlight', { articleId: article.id, paragraphIndex: blockIndex });
      logEvent('reader_highlight_add', { article_id: article.id, block_index: blockIndex, text_preview: text.slice(0, 80) });
    }
  }, [article]);

  // Entity tap handler
  const [activeEntityUrl, setActiveEntityUrl] = useState<string | undefined>();

  const handleEntityLongPress = useCallback((entity: ArticleEntity, url?: string) => {
    setActiveEntity(entity);
    setActiveEntityUrl(url);
    logEvent('entity_popup_open', { article_id: article?.id, entity: entity.name, entity_type: entity.type, url });
  }, [article]);

  const handleEntityIngest = useCallback(async () => {
    if (!activeEntityUrl) return;
    try {
      const result = await ingestUrl(activeEntityUrl, 'reader_link');
      await addToQueue(result.article_id);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      logEvent('entity_ingest_launched', { article_id: article?.id, entity: activeEntity?.name, url: activeEntityUrl });
    } catch (e) {
      logEvent('entity_ingest_error', { url: activeEntityUrl, error: String(e) });
    }
    setActiveEntity(null);
    setActiveEntityUrl(undefined);
  }, [article, activeEntity, activeEntityUrl]);

  const handleEntityResearch = useCallback(async () => {
    if (!article || !activeEntity) return;
    const context = activeEntityUrl
      ? `Entity: ${activeEntity.name} (${activeEntity.type})\n${activeEntity.synthesis}\nURL: ${activeEntityUrl}\nFrom article: ${article.title}`
      : `Entity: ${activeEntity.name} (${activeEntity.type})\n${activeEntity.synthesis}\nFrom article: ${article.title}`;
    try {
      await spawnTopicResearch(
        activeEntity.name,
        context,
        [article.title],
      );
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      logEvent('entity_research_launched', { article_id: article.id, entity: activeEntity.name, url: activeEntityUrl });
    } catch (e) {
      logEvent('entity_research_error', { article_id: article.id, entity: activeEntity.name, error: String(e) });
    }
    setActiveEntity(null);
    setActiveEntityUrl(undefined);
  }, [article, activeEntity, activeEntityUrl]);

  // Auto-advance: queue first, then next in feed ranking, then back
  const advanceOrGoBack = useCallback(async () => {
    if (!article) return;
    await removeFromQueue(article.id);
    const queuedIds = getQueuedArticleIds();
    const nextId = queuedIds.find(qId => qId !== article.id);
    const nextArticle = nextId ? getArticleById(nextId) : null;

    if (nextArticle) {
      logEvent('auto_advance_triggered', { from_article_id: article.id, to_article_id: nextArticle.id, source: 'queue' });
      router.replace({ pathname: '/reader', params: { id: nextArticle.id, autoAdvanceFrom: article.id } });
    } else {
      // No queue — advance to next ranked article in feed
      const nextFeedId = getAdjacentArticleId(article.id, 'next', feedLens);
      if (nextFeedId) {
        logEvent('auto_advance_triggered', { from_article_id: article.id, to_article_id: nextFeedId, source: 'feed' });
        router.replace({ pathname: '/reader', params: { id: nextFeedId, autoAdvanceFrom: article.id } });
      } else {
        router.back();
      }
    }
  }, [article, router, feedLens]);

  // Done handler — mark read and immediately advance to next
  const handleDone = useCallback(() => {
    if (!article) return;
    // Capture next feed article BEFORE marking read (read articles are filtered from feed)
    const precomputedNextFeedId = getAdjacentArticleId(article.id, 'next', feedLens);
    markArticleRead(article.id);
    markArticleEncountered(article.id, 'read');
    recordInterestSignal('tap_done', article.id);
    logEvent('reader_done', { article_id: article.id });

    // Brief completion flash, then advance
    completionFlash.setValue(0);
    Animated.timing(completionFlash, {
      toValue: 1,
      duration: 400,
      useNativeDriver: true,
    }).start(async () => {
      // Queue takes priority, then precomputed feed next, then back
      await removeFromQueue(article.id);
      const queuedIds = getQueuedArticleIds();
      const nextQueueId = queuedIds.find(qId => qId !== article.id);
      const nextQueued = nextQueueId ? getArticleById(nextQueueId) : null;

      if (nextQueued) {
        logEvent('auto_advance_triggered', { from_article_id: article.id, to_article_id: nextQueued.id, source: 'queue' });
        router.replace({ pathname: '/reader', params: { id: nextQueued.id, autoAdvanceFrom: article.id } });
      } else if (precomputedNextFeedId) {
        logEvent('auto_advance_triggered', { from_article_id: article.id, to_article_id: precomputedNextFeedId, source: 'feed' });
        router.replace({ pathname: '/reader', params: { id: precomputedNextFeedId, autoAdvanceFrom: article.id } });
      } else {
        router.back();
      }
    });
  }, [article, feedLens, router]);

  // Up next handler — navigate to next queued article
  const handleUpNext = useCallback(async () => {
    if (!article || !nextQueuedArticle) return;
    markArticleRead(article.id);
    markArticleEncountered(article.id, 'read');
    recordInterestSignal('tap_done', article.id);
    await removeFromQueue(article.id);
    logEvent('reader_up_next', { from_article_id: article.id, to_article_id: nextQueuedArticle.id });
    router.replace({ pathname: '/reader', params: { id: nextQueuedArticle.id } });
  }, [article, nextQueuedArticle, router]);


  const isWeb = Platform.OS === 'web';
  const hasDimming = !!(blockDimming && Array.from(blockDimming.values()).some(d => d.opacity < 1));

  // Web margin: star handler
  const handleWebStar = useCallback(async () => {
    if (!article) return;
    const nowBookmarked = await toggleBookmark(article.id);
    setBookmarked(nowBookmarked);
    recordInterestSignal(nowBookmarked ? 'bookmark_add' : 'bookmark_remove', article.id);
    logEvent('reader_margin_star', { article_id: article.id, bookmarked: nowBookmarked });
  }, [article]);

  // Web margin: dismiss handler
  const handleWebDismiss = useCallback(() => {
    if (!article) return;
    dismissArticle(article.id, 'margin_dismiss');
    recordInterestSignal('swipe_dismiss', article.id);
    logEvent('reader_margin_dismiss', { article_id: article.id });
    setStatusMessage('Dismissed');
    setTimeout(() => router.back(), 600);
  }, [article, router]);

  // Web margin: navigate to article
  const handleNavigateArticle = useCallback((targetId: string) => {
    logEvent('margin_navigate_article', { source_article_id: article?.id, target_article_id: targetId });
    router.push({ pathname: '/reader', params: { id: targetId } });
  }, [article, router]);

  if (!articleMeta || !article) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Article not found</Text>
        <Pressable onPress={() => router.back()}>
          <Text style={styles.backLink}>Back to feed</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Top bar */}
      <View style={[styles.topBar, Platform.OS === 'web' && styles.topBarWeb]}>
        <Pressable onPress={() => {
          logEvent('reader_back', { article_id: article.id });
          router.back();
        }} style={styles.backButton}>
          <Text style={styles.backLinkText}>{'← Feed'}</Text>
        </Pressable>
        {Platform.OS === 'web' && prevArticle ? (
          <Pressable onPress={() => {
            router.replace({ pathname: '/reader', params: { id: prevArticle.id, lens: feedLens } });
          }} style={styles.topBarNavBtn}>
            <Text style={styles.topBarNavText} numberOfLines={1}>{'‹ '}{getDisplayTitle(prevArticle)}</Text>
          </Pressable>
        ) : null}
        <View style={{ flex: 1 }} />
        {Platform.OS === 'web' && nextArticle ? (
          <Pressable onPress={() => {
            router.replace({ pathname: '/reader', params: { id: nextArticle.id, lens: feedLens } });
          }} style={styles.topBarNavBtn}>
            <Text style={styles.topBarNavText} numberOfLines={1}>{getDisplayTitle(nextArticle)}{' ›'}</Text>
          </Pressable>
        ) : null}
        {Platform.OS === 'web' ? (
          <Text style={styles.webProgressText}>{Math.round(scrollProgress)}%</Text>
        ) : (
          <>
            <Pressable onPress={async () => {
              const nowBookmarked = await toggleBookmark(article.id);
              setBookmarked(nowBookmarked);
              recordInterestSignal(nowBookmarked ? 'bookmark_add' : 'bookmark_remove', article.id);
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            }} style={styles.bookmarkButton}>
              <Text style={[styles.bookmarkText, bookmarked && styles.bookmarkTextActive]}>
                {bookmarked ? '★' : '☆'}
              </Text>
            </Pressable>
            <Pressable onPress={() => {
              setShowVoiceFeedback(!showVoiceFeedback);
              logEvent('voice_note_toolbar_tap', { article_id: article.id });
            }} style={styles.voiceToolbarButton}>
              {showVoiceFeedback ? (
                <Animated.Text style={[styles.voiceToolbarDotActive, { opacity: voicePulseAnim }]}>
                  {'\u25CF'}
                </Animated.Text>
              ) : (
                <Text style={styles.voiceToolbarDot}>{'\u25CF'}</Text>
              )}
            </Pressable>
            <Pressable onPress={() => {
              setShowMenu(!showMenu);
              logEvent('reader_menu_toggle', { article_id: article.id });
            }} style={styles.menuButton}>
              <Text style={styles.menuButtonText}>⋯</Text>
            </Pressable>
          </>
        )}
      </View>

      {/* Dropdown menu */}
      {showMenu && (
        <View style={styles.menuDropdown}>
          {/* Article ID */}
          <Pressable onPress={() => {
            Clipboard.setString(article.id);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            logEvent('reader_copy_id', { article_id: article.id });
          }} style={styles.menuItem}>
            <Text style={styles.menuItemLabel}>ID</Text>
            <Text style={styles.menuItemValue} numberOfLines={1}>{article.id}</Text>
          </Pressable>

          {/* Source */}
          <View style={styles.menuItem}>
            <Text style={styles.menuItemLabel}>Source</Text>
            <Text style={styles.menuItemValue} numberOfLines={1}>{article.hostname}</Text>
          </View>

          {/* Content type */}
          <View style={styles.menuItem}>
            <Text style={styles.menuItemLabel}>Type</Text>
            <Text style={styles.menuItemValue}>{article.content_type}</Text>
          </View>

          {/* Word count + read time */}
          <View style={styles.menuItem}>
            <Text style={styles.menuItemLabel}>Length</Text>
            <Text style={styles.menuItemValue}>{article.word_count?.toLocaleString()} words · {article.estimated_read_minutes} min</Text>
          </View>

          {/* Date */}
          {article.date ? (
            <View style={styles.menuItem}>
              <Text style={styles.menuItemLabel}>Date</Text>
              <Text style={styles.menuItemValue}>{formatDate(article.date)}</Text>
            </View>
          ) : null}

          {/* Topics */}
          {article.interest_topics && article.interest_topics.length > 0 ? (
            <View style={styles.menuItem}>
              <Text style={styles.menuItemLabel}>Topics</Text>
              <Text style={styles.menuItemValue} numberOfLines={2}>
                {article.interest_topics.map(t => t.broad).join(', ')}
              </Text>
            </View>
          ) : null}

          {/* Divider */}
          <View style={styles.menuDivider} />

          {/* Open source */}
          <Pressable onPress={() => {
            logEvent('reader_open_source', { article_id: article.id, url: article.source_url });
            Linking.openURL(article.source_url);
            setShowMenu(false);
          }} style={styles.menuAction}>
            <Text style={styles.menuActionText}>Open source →</Text>
          </Pressable>

          {/* Copy link */}
          <Pressable onPress={() => {
            Clipboard.setString(article.source_url);
            logEvent('reader_copy_link', { article_id: article.id, url: article.source_url });
            if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            setShowMenu(false);
            setStatusMessage('Link copied');
          }} style={styles.menuAction}>
            <Text style={styles.menuActionText}>Copy link</Text>
          </Pressable>

          {/* Report bad scrape */}
          <Pressable onPress={() => {
            reportBadScrape(article.id, article.source_url, article.title);
            logEvent('report_bad_scrape', { article_id: article.id });
            if (Platform.OS !== 'web') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            setShowMenu(false);
            setStatusMessage('Reported');
          }} style={styles.menuAction}>
            <Text style={[styles.menuActionText, { color: colors.textMuted }]}>Report bad scrape</Text>
          </Pressable>

          {/* Ask AI */}
          <Pressable onPress={() => {
            setShowMenu(false);
            setShowAIChat(true);
            logEvent('ai_chat_open', { article_id: article.id });
          }} style={styles.menuAction}>
            <Text style={[styles.menuActionText, { color: colors.rubric }]}>✦ Ask AI</Text>
          </Pressable>

          {/* Voice note */}
          <Pressable onPress={() => {
            setShowMenu(false);
            setShowVoiceFeedback(true);
            logEvent('voice_note_open', { article_id: article.id });
          }} style={styles.menuAction}>
            <Text style={styles.menuActionText}>● Voice note</Text>
          </Pressable>

          {/* Research topics */}
          {article.interest_topics && article.interest_topics.length > 0 ? (
            <Pressable onPress={async () => {
              const topic = article.interest_topics![0].broad;
              setShowMenu(false);
              try {
                await spawnTopicResearch(
                  topic,
                  `Article: ${article.title}\nSummary: ${article.one_line_summary}`,
                  [article.title],
                );
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
                logEvent('research_spawned', { article_id: article.id, topic });
              } catch (e) {
                logEvent('research_spawn_error', { article_id: article.id, error: String(e) });
              }
            }} style={styles.menuAction}>
              <Text style={[styles.menuActionText, { color: colors.claimNew }]}>
                ↗ Research "{article.interest_topics[0].broad}"
              </Text>
            </Pressable>
          ) : null}

          {/* Divider before destructive action */}
          <View style={styles.menuDivider} />

          {/* Disregard */}
          <Pressable onPress={() => {
            dismissArticle(article.id, 'reader_disregard');
            recordInterestSignal('swipe_dismiss', article.id);
            logEvent('reader_disregard', { article_id: article.id });
            setShowMenu(false);
            setStatusMessage('Disregarded');
            setTimeout(() => router.back(), 600);
          }} style={styles.menuAction}>
            <Text style={[styles.menuActionText, { color: colors.textMuted }]}>Disregard</Text>
          </Pressable>
        </View>
      )}

      {/* Status toast */}
      {statusMessage ? (
        <View style={styles.statusToast}>
          <Text style={styles.statusToastText}>{statusMessage}</Text>
        </View>
      ) : null}

      {/* Link queued toast */}
      {linkToast && (
        <LinkToast
          domain={linkToast.domain}
          articleId={linkToast.articleId}
          onViewQueue={() => {
            setLinkToast(null);
            router.push('/queue');
          }}
          onDismiss={() => setLinkToast(null)}
        />
      )}

      {/* Progress bar with completion flash */}
      <View style={[styles.progressBarTrack, isWeb && styles.progressBarTrackWeb]}>
        <View style={[styles.progressBarFill, { width: `${scrollProgress}%` as any }]} />
        <Animated.View style={[
          styles.completionFlash,
          {
            opacity: completionFlash.interpolate({
              inputRange: [0, 0.15, 0.85, 1],
              outputRange: [0, 0.9, 0.9, 0],
            }),
            transform: [{
              translateX: completionFlash.interpolate({
                inputRange: [0, 1],
                outputRange: [-400, 400],
              }),
            }],
          },
        ]} />
      </View>

      <ReaderErrorBoundary articleId={article.id} onGoBack={() => router.back()}>
      {/* Web: 3-column grid layout / Mobile: single column */}
      <View style={isWeb ? webGridStyle : { flex: 1 }}>
        {/* Left margin (web only) */}
        {isWeb && (
          <ReaderLeftMargin
            article={article}
            novelty={articleNovelty}
            readingMode={readingMode}
            onModeChange={(mode) => {
              setReadingMode(mode);
              logEvent('reading_mode_change', { article_id: article.id, mode });
            }}
            bookmarked={bookmarked}
            onStar={handleWebStar}
            onDismiss={handleWebDismiss}
            onDone={handleDone}
            onAskAI={() => setShowAIChat(true)}
            scrollProgress={scrollProgress}
            hasDimming={hasDimming}
            shortcuts={readerShortcuts}
          />
        )}

        {/* Center column: web uses View (browser scrolls page), mobile uses ScrollView */}
        {isWeb ? (
          <View style={[styles.scroll, styles.scrollWeb]}>
            <Text style={styles.articleTitle}>{getDisplayTitle(article)}</Text>
            <View style={styles.metaRow}>
              {article.author ? <Text style={styles.metaText}>{article.author}</Text> : null}
              <Text style={styles.metaText}>{article.hostname}</Text>
              {article.date ? <Text style={styles.metaText}>{formatDate(article.date)}</Text> : null}
              <Text style={styles.metaText}>{article.estimated_read_minutes} min</Text>
            </View>
            <View style={{ marginVertical: 16 }}>
              <DoubleRule />
            </View>

            {claimClassifications ? (() => {
              const newClaims = claimClassifications.filter((c: ClaimClassification) => c.classification === 'NEW');
              const interesting = newClaims.filter((c: ClaimClassification) => c.claim_type !== 'factual');
              const fallback = newClaims.filter((c: ClaimClassification) => c.claim_type === 'factual');
              const displayClaims = [...interesting, ...fallback].slice(0, 3);
              if (displayClaims.length === 0 && newClaims.length === 0) return null;
              return (
                <View style={styles.noveltyCard}>
                  <Text style={styles.noveltyTitle}>{'✦ What\u2019s new for you'}</Text>
                  {verdictLine && (
                    <Text style={styles.verdictLine}>{verdictLine}</Text>
                  )}
                  {articleNovelty && (
                    <View style={styles.noveltyStats}>
                      <Text style={styles.noveltyStatText}>
                        {articleNovelty.new_claims} new · {articleNovelty.extends_claims} extend · {articleNovelty.known_claims} familiar
                      </Text>
                    </View>
                  )}
                  {displayClaims.map((c: ClaimClassification, i: number) => (
                    <AnimatedClaimItem key={i} text={c.text} index={i} />
                  ))}
                  {readSimilarArticles.length > 0 && (
                    <View style={styles.similarSection}>
                      <Text style={styles.similarLabel}>Similar to:</Text>
                      {readSimilarArticles.map((sa) => (
                        <Pressable
                          key={sa.id}
                          onPress={() => {
                            logEvent('briefing_similar_tap', { article_id: article.id, similar_id: sa.id });
                            router.push({ pathname: '/reader', params: { id: sa.id } });
                          }}
                        >
                          <Text style={styles.similarArticle}>
                            {sa.title} ({Math.round(sa.score * 100)}%)
                          </Text>
                        </Pressable>
                      ))}
                    </View>
                  )}
                  {skipNudge !== null && (
                    <Pressable
                      onPress={() => {
                        logEvent('briefing_skip_tap', { article_id: article.id, new_claims: skipNudge });
                        setReadingMode('new_only');
                      }}
                    >
                      <Text style={styles.skipNudge}>
                        Most of this covers ground you{'\u2019'}ve seen.{' '}
                        <Text style={styles.skipNudgeLink}>Read {skipNudge} new claim{skipNudge !== 1 ? 's' : ''} only {'\u2192'}</Text>
                      </Text>
                    </Pressable>
                  )}
                </View>
              );
            })() : article.novelty_claims && article.novelty_claims.length > 0 ? (
              <View style={styles.noveltyCard}>
                <Text style={styles.noveltyTitle}>{'✦ What\u2019s new'}</Text>
                {article.novelty_claims.slice(0, 3).map((nc, i) => (
                  <AnimatedClaimItem key={i} text={nc.claim} index={i} />
                ))}
              </View>
            ) : null}

            <MarkdownText
              content={fullContent}
              highlightedBlocks={highlightedBlocks}
              onBlockLongPress={handleBlockLongPress}
              blockDimming={blockDimming}
              readingMode={readingMode}
              entities={article.entities}
              onEntityLongPress={handleEntityLongPress}
              linkHandler={linkHandler}
              paragraphConnections={paragraphConnections}
              sourceArticleId={article.id}
            />

            {activeEntity && (
              <EntityPopup
                entity={activeEntity}
                articleTitle={article.title}
                url={activeEntityUrl}
                onResearch={handleEntityResearch}
                onIngest={activeEntityUrl ? handleEntityIngest : undefined}
                onDismiss={() => {
                  logEvent('entity_popup_dismiss', { article_id: article.id, entity: activeEntity.name });
                  setActiveEntity(null);
                  setActiveEntityUrl(undefined);
                }}
              />
            )}

            <View style={{ height: 100 }} />
          </View>
        ) : (
          <ScrollView
            ref={scrollRef}
            style={styles.scroll}
            showsVerticalScrollIndicator={false}
            scrollEventThrottle={16}
            onScroll={handleScroll}
          >
            <Text style={styles.articleTitle}>{getDisplayTitle(article)}</Text>
            <View style={styles.metaRow}>
              {article.author ? <Text style={styles.metaText}>{article.author}</Text> : null}
              <Text style={styles.metaText}>{article.hostname}</Text>
              {article.date ? <Text style={styles.metaText}>{formatDate(article.date)}</Text> : null}
              <Text style={styles.metaText}>{article.estimated_read_minutes} min</Text>
            </View>
            <View style={{ marginVertical: 16 }}>
              <DoubleRule />
            </View>

            {claimClassifications ? (() => {
              const newClaims = claimClassifications.filter((c: ClaimClassification) => c.classification === 'NEW');
              const interesting = newClaims.filter((c: ClaimClassification) => c.claim_type !== 'factual');
              const fallback = newClaims.filter((c: ClaimClassification) => c.claim_type === 'factual');
              const displayClaims = [...interesting, ...fallback].slice(0, 3);
              if (displayClaims.length === 0 && newClaims.length === 0) return null;
              return (
                <View style={styles.noveltyCard}>
                  <Text style={styles.noveltyTitle}>{'✦ What\u2019s new for you'}</Text>
                  {verdictLine && (
                    <Text style={styles.verdictLine}>{verdictLine}</Text>
                  )}
                  {articleNovelty && (
                    <View style={styles.noveltyStats}>
                      <Text style={styles.noveltyStatText}>
                        {articleNovelty.new_claims} new · {articleNovelty.extends_claims} extend · {articleNovelty.known_claims} familiar
                      </Text>
                    </View>
                  )}
                  {displayClaims.map((c: ClaimClassification, i: number) => (
                    <AnimatedClaimItem key={i} text={c.text} index={i} />
                  ))}
                  {readSimilarArticles.length > 0 && (
                    <View style={styles.similarSection}>
                      <Text style={styles.similarLabel}>Similar to:</Text>
                      {readSimilarArticles.map((sa) => (
                        <Pressable
                          key={sa.id}
                          onPress={() => {
                            logEvent('briefing_similar_tap', { article_id: article.id, similar_id: sa.id });
                            router.push({ pathname: '/reader', params: { id: sa.id } });
                          }}
                        >
                          <Text style={styles.similarArticle}>
                            {sa.title} ({Math.round(sa.score * 100)}%)
                          </Text>
                        </Pressable>
                      ))}
                    </View>
                  )}
                  {skipNudge !== null && (
                    <Pressable
                      onPress={() => {
                        logEvent('briefing_skip_tap', { article_id: article.id, new_claims: skipNudge });
                        setReadingMode('new_only');
                      }}
                    >
                      <Text style={styles.skipNudge}>
                        Most of this covers ground you{'\u2019'}ve seen.{' '}
                        <Text style={styles.skipNudgeLink}>Read {skipNudge} new claim{skipNudge !== 1 ? 's' : ''} only {'\u2192'}</Text>
                      </Text>
                    </Pressable>
                  )}
                </View>
              );
            })() : article.novelty_claims && article.novelty_claims.length > 0 ? (
              <View style={styles.noveltyCard}>
                <Text style={styles.noveltyTitle}>{'✦ What\u2019s new'}</Text>
                {article.novelty_claims.slice(0, 3).map((nc, i) => (
                  <AnimatedClaimItem key={i} text={nc.claim} index={i} />
                ))}
              </View>
            ) : null}

            {hasDimming && (
              <ReadingModeToggle mode={readingMode} onModeChange={(mode) => {
                setReadingMode(mode);
                logEvent('reading_mode_change', { article_id: article.id, mode });
              }} />
            )}

            <MarkdownText
              content={fullContent}
              highlightedBlocks={highlightedBlocks}
              onBlockLongPress={handleBlockLongPress}
              blockDimming={blockDimming}
              readingMode={readingMode}
              entities={article.entities}
              onEntityLongPress={handleEntityLongPress}
              linkHandler={linkHandler}
              paragraphConnections={paragraphConnections}
              sourceArticleId={article.id}
            />

            {activeEntity && (
              <EntityPopup
                entity={activeEntity}
                articleTitle={article.title}
                url={activeEntityUrl}
                onResearch={handleEntityResearch}
                onIngest={activeEntityUrl ? handleEntityIngest : undefined}
                onDismiss={() => {
                  logEvent('entity_popup_dismiss', { article_id: article.id, entity: activeEntity.name });
                  setActiveEntity(null);
                  setActiveEntityUrl(undefined);
                }}
              />
            )}

            <ConnectedReadingSection
              connections={crossArticleConnections.filter(c => getReadingState(c.articleId).status !== 'read')}
              articleId={article.id}
            />

            <FollowTopicsSection topics={article.interest_topics || []} articleId={article.id} />

            <FollowUpSection
              questions={article.follow_up_questions || []}
              articleTitle={article.title}
              articleId={article.id}
              articleSummary={article.one_line_summary}
            />

            <RelatedArticles article={article} excludeIds={new Set(crossArticleConnections.map(c => c.articleId))} />

            <View style={{ height: 100 }} />
          </ScrollView>
        )}

        {/* Right margin (web only) */}
        {isWeb && (
          <ReaderRightMargin
            article={article}
            nextArticle={nextQueuedArticle}
            connections={crossArticleConnections}
            followUpQuestions={article.follow_up_questions || []}
            onNavigateArticle={handleNavigateArticle}
            onUpNext={handleUpNext}
          />
        )}
      </View>

      {/* Bottom action bar — mobile: triage buttons, web: keyboard hint bar */}
      {Platform.OS !== 'web' && (
        <View style={styles.footerBar}>
          <Pressable style={styles.actionBtn} onPress={() => {
            const next = !bookmarked;
            toggleBookmark(article.id);
            setBookmarked(next);
            if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            logEvent('reader_footer_star', { article_id: article.id, bookmarked: next });
          }}>
            <Text style={[styles.actionBtnText, bookmarked && { color: colors.rubric }]}>
              {bookmarked ? '★' : '☆'}
            </Text>
          </Pressable>
          <Pressable style={styles.actionBtn} onPress={() => {
            dismissArticle(article.id, 'footer_dismiss');
            recordInterestSignal('swipe_dismiss', article.id);
            logEvent('reader_footer_dismiss', { article_id: article.id });
            setStatusMessage('Dismissed');
            setTimeout(() => router.back(), 600);
          }}>
            <Text style={styles.actionBtnText}>✕</Text>
          </Pressable>
          <View style={styles.actionSpacer} />
          <Pressable style={styles.doneButton} onPress={handleDone}>
            <Text style={styles.doneButtonText}>Done</Text>
          </Pressable>
          {nextQueuedArticle ? (
            <Pressable style={styles.upNextButton} onPress={handleUpNext}>
              <Text style={styles.upNextTitle} numberOfLines={1}>
                {getDisplayTitle(nextQueuedArticle)} →
              </Text>
            </Pressable>
          ) : null}
        </View>
      )}


      {/* AI Chat */}
      {showAIChat && (
        <AskAI
          articleId={article.id}
          context={buildAIChatContext(article)}
          onClose={() => setShowAIChat(false)}
        />
      )}

      {/* Voice Note */}
      {showVoiceFeedback && (
        <View style={styles.voiceFeedbackOverlay}>
          <VoiceFeedback
            articleId={article.id}
            articleTitle={article.title}
            topics={(article.interest_topics || []).map(t => t.broad)}
            articleContext={buildAIChatContext(article)}
            onClose={() => setShowVoiceFeedback(false)}
          />
        </View>
      )}

      </ReaderErrorBoundary>

      {!isWeb && <KeyboardHintBar shortcuts={readerShortcuts} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: Platform.OS === 'web' ? undefined as any : 1,
    backgroundColor: colors.parchment,
    ...(Platform.OS !== 'web' ? {
      maxWidth: layout.readingMeasure,
      alignSelf: 'center' as const,
      width: '100%' as any,
    } : {
      outline: 'none',
    } as any),
  },

  // Top bar
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: layout.screenPadding,
    paddingVertical: 10,
    gap: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
  },
  topBarWeb: {
    maxWidth: layout.webReaderMaxWidth,
    alignSelf: 'center' as const,
    width: '100%' as any,
    paddingHorizontal: 32,
    position: 'sticky' as any,
    top: 0,
    zIndex: 10,
    backgroundColor: colors.parchment,
    paddingTop: 4,
  },
  webProgressText: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  topBarNavBtn: {
    maxWidth: 200,
    paddingVertical: 4,
    paddingHorizontal: 8,
  },
  topBarNavText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  backButton: {
    paddingVertical: 4,
  },
  backLinkText: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.textMuted,
  },
  bookmarkButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    minWidth: 44,
    minHeight: 44,
    justifyContent: 'center' as const,
    alignItems: 'center' as const,
  },
  bookmarkText: {
    fontSize: 20,
    color: colors.textMuted,
  },
  bookmarkTextActive: {
    color: colors.rubric,
  },
  voiceToolbarButton: {
    paddingHorizontal: 6,
    paddingVertical: 4,
    minWidth: 44,
    minHeight: 44,
    justifyContent: 'center' as const,
    alignItems: 'center' as const,
  },
  voiceToolbarDot: {
    fontFamily: fonts.ui,
    fontSize: 16,
    color: colors.textMuted,
  },
  voiceToolbarDotActive: {
    fontFamily: fonts.ui,
    fontSize: 16,
    color: colors.rubric,
  },
  menuButton: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    minWidth: 44,
    minHeight: 44,
    justifyContent: 'center' as const,
    alignItems: 'center' as const,
  },
  menuButtonText: {
    fontSize: 22,
    color: colors.textMuted,
    fontFamily: fonts.display,
  },
  menuDropdown: {
    backgroundColor: colors.parchment,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
    paddingHorizontal: 16,
    paddingVertical: 8,
    ...(Platform.OS === 'web' ? {
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    } : {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.08,
      shadowRadius: 8,
      elevation: 3,
    }),
  },
  menuItem: {
    flexDirection: 'row' as const,
    alignItems: 'flex-start' as const,
    paddingVertical: 5,
    gap: 10,
  },
  menuItemLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
    width: 50,
    marginTop: 2,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  menuItemValue: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textBody,
    flex: 1,
  },
  menuDivider: {
    height: 1,
    backgroundColor: colors.rule,
    marginVertical: 6,
  },
  menuAction: {
    paddingVertical: 8,
    minHeight: 36,
    justifyContent: 'center' as const,
  },
  menuActionText: {
    fontFamily: fonts.ui,
    fontSize: 14,
    color: colors.textBody,
  },
  statusToast: {
    position: 'absolute' as const,
    top: 60,
    alignSelf: 'center' as const,
    backgroundColor: colors.ink,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 4,
    zIndex: 200,
  },
  statusToastText: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.parchment,
  },
  voiceFeedbackOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
  },

  // Progress bar
  progressBarTrack: {
    height: 2,
    backgroundColor: colors.rule,
    overflow: 'hidden' as const,
  },
  progressBarTrackWeb: {
    position: 'fixed' as any,
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
    height: 2,
  },
  progressBarFill: {
    height: 2,
    backgroundColor: colors.rubric,
  },
  completionFlash: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    width: 120,
    height: 2,
    backgroundColor: '#c9a84c',
  },

  // Scroll
  scroll: {
    flex: 1,
    paddingHorizontal: layout.screenPadding,
  },
  scrollWeb: {
    paddingHorizontal: 48,
    ...(Platform.OS === 'web' ? { outline: 'none' } as any : {}),
  },

  // Header
  articleTitle: {
    ...type.readerTitle,
    color: colors.ink,
    marginTop: 20,
    marginBottom: 12,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 32,
  },
  metaText: {
    ...type.metadata,
    color: colors.textMuted,
  },

  // Novelty card
  noveltyCard: {
    borderLeftWidth: 2,
    borderLeftColor: colors.rubric,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 28,
    ...(Platform.OS === 'web' ? { background: 'linear-gradient(135deg, rgba(240,236,226,0.5), rgba(247,244,236,0))' as any } : { backgroundColor: 'rgba(240,236,226,0.3)' }),
  },
  noveltyTitle: {
    ...type.sectionHead,
    color: colors.rubric,
    marginBottom: 8,
  },
  noveltyStats: {
    marginBottom: 8,
  },
  noveltyStatText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textSecondary,
    letterSpacing: 0.3,
  },
  noveltyItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 4,
  },
  noveltyDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.rubric,
    marginTop: 8,
  },
  noveltyText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    lineHeight: 21,
    color: colors.textBody,
    flex: 1,
  },
  verdictLine: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    lineHeight: 21,
    color: colors.textSecondary,
    marginBottom: 6,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  similarSection: {
    marginTop: 10,
  },
  similarLabel: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
    letterSpacing: 0.3,
    marginBottom: 3,
  },
  similarArticle: {
    fontFamily: fonts.readingItalic,
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginBottom: 2,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  skipNudge: {
    fontFamily: fonts.ui,
    fontSize: 12,
    lineHeight: 18,
    color: colors.textMuted,
    marginTop: 10,
  },
  skipNudgeLink: {
    color: colors.rubric,
    fontFamily: fonts.uiMedium,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },

  // Reading mode toggle
  readingModeContainer: {
    alignItems: 'center',
    marginVertical: 12,
  },
  readingModeTrack: {
    flexDirection: 'row',
    backgroundColor: colors.parchmentDark,
    borderRadius: 0,
  },
  readingModeButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    minHeight: layout.touchTarget,
    justifyContent: 'center',
    alignItems: 'center',
  },
  readingModeButtonActive: {
    backgroundColor: colors.ink,
  },
  readingModeLabel: {
    fontFamily: fonts.ui,
    fontSize: 11,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.88,
    color: colors.textMuted,
  },
  readingModeLabelActive: {
    color: colors.parchment,
  },

  // Collapsed bar (stretchtext)
  collapsedBar: {
    backgroundColor: colors.parchmentDark,
    borderLeftWidth: 2,
    borderLeftColor: colors.claimKnown,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  collapsedBarContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  collapsedBarDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.textMuted,
  },
  collapsedBarText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  collapsedBarExpand: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  collapseBar: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    marginBottom: 14,
    alignItems: 'center',
  },

  // Footer action bar (mobile)
  footerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: layout.screenPadding,
    paddingVertical: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.rule,
    backgroundColor: colors.parchment,
    gap: 4,
  },
  actionBtn: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionBtnText: {
    fontSize: 18,
    color: colors.textMuted,
  },
  actionSpacer: {
    flex: 1,
  },
  doneButton: {
    backgroundColor: colors.ink,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 16,
    minHeight: 36,
    justifyContent: 'center',
  },
  doneButtonText: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.parchment,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  upNextButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    minHeight: 36,
    paddingHorizontal: 6,
    maxWidth: 160,
  },
  upNextTitle: {
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.textSecondary,
  },

  // Markdown styles
  markdownText: {
    ...type.readerBody,
    color: colors.textBody,
    marginBottom: 24,
  },
  markdownHeading: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 20,
    lineHeight: 28,
    color: colors.ink,
    marginTop: 40,
    marginBottom: 16,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  markdownHr: {
    height: 1,
    backgroundColor: colors.rule,
    marginVertical: 20,
  },
  markdownLink: {
    color: colors.rubric,
    textDecorationLine: 'underline' as const,
    textDecorationColor: 'rgba(139,37,0,0.15)' as any,
  },
  markdownLinkIngest: {
    color: colors.rubric,
    textDecorationLine: 'underline' as const,
    textDecorationColor: 'rgba(139,37,0,0.15)' as any,
  },
  markdownLinkExternal: {
    color: colors.rubric,
    textDecorationLine: 'underline' as const,
    textDecorationStyle: 'dashed' as const,
    textDecorationColor: 'rgba(139,37,0,0.15)' as any,
  },
  linkSuffix: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  ingestBadgeProcessing: {
    fontFamily: fonts.ui,
    fontSize: 8,
    color: colors.textMuted,
    letterSpacing: 0.3,
  },
  ingestBadgeQueued: {
    fontFamily: fonts.ui,
    fontSize: 8,
    color: colors.claimNew,
    letterSpacing: 0.3,
  },
  ingestBadgeFailed: {
    fontFamily: fonts.ui,
    fontSize: 8,
    color: colors.rubric,
    letterSpacing: 0.3,
  },
  markdownBold: {
    fontFamily: fonts.readingMedium,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  markdownItalic: {
    fontFamily: fonts.readingItalic,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  markdownInlineCode: {
    fontFamily: Platform.select({ web: 'monospace', default: 'Courier' }),
    backgroundColor: colors.parchmentDark,
    fontSize: 14,
    paddingHorizontal: 4,
  },
  markdownList: {
    marginBottom: 24,
    paddingLeft: 4,
  },
  markdownListItem: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 5,
  },
  markdownBullet: {
    fontFamily: fonts.reading,
    fontSize: 16,
    color: colors.rubric,
    width: 12,
    fontWeight: 'bold' as const,
  },
  markdownOrderedBullet: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.textMuted,
    width: 20,
    textAlign: 'right' as const,
  },
  markdownBlockquote: {
    borderLeftWidth: 2,
    borderLeftColor: colors.rubric,
    paddingLeft: 20,
    paddingVertical: 16,
    paddingRight: 16,
    marginBottom: 20,
    ...(Platform.OS === 'web' ? { background: 'linear-gradient(135deg, rgba(240,236,226,0.6), rgba(247,244,236,0))' as any } : { backgroundColor: 'rgba(240,236,226,0.4)' }),
  },
  markdownBlockquoteText: {
    fontFamily: fonts.readingItalic,
    fontSize: 15,
    lineHeight: 24,
    color: colors.textSecondary,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  codeBlock: {
    backgroundColor: 'rgba(240,236,226,0.5)',
    borderLeftWidth: 2,
    borderLeftColor: colors.rule,
    padding: 16,
    paddingLeft: 18,
    marginBottom: 20,
  },
  codeText: {
    fontFamily: Platform.select({ web: "'JetBrains Mono', monospace", default: 'Courier' }),
    fontSize: 12.5,
    lineHeight: 20,
    color: colors.textSecondary,
  },

  // Table
  tableContainer: {
    marginBottom: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.rule,
  },
  tableRow: {
    flexDirection: 'row',
  },
  tableRowAlt: {
    backgroundColor: colors.parchmentDark,
  },
  tableCell: {
    flex: 1,
    padding: 8,
    borderRightWidth: StyleSheet.hairlineWidth,
    borderRightColor: colors.rule,
  },
  tableHeaderCell: {
    backgroundColor: colors.parchmentDark,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
  },
  tableHeaderText: {
    fontFamily: fonts.uiMedium,
    fontSize: 12,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  tableCellText: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textBody,
    lineHeight: 18,
  },

  // Highlight
  paragraphHighlight: {
    backgroundColor: 'rgba(218, 165, 32, 0.15)',
    borderLeftWidth: 3,
    borderLeftColor: 'rgba(218, 165, 32, 0.6)',
    paddingLeft: 10,
  },


  // Error state
  errorText: {
    ...type.screenTitle,
    color: colors.ink,
    textAlign: 'center',
    marginTop: 100,
  },
  backLink: {
    ...type.metadata,
    color: colors.rubric,
    textAlign: 'center',
    marginTop: 12,
  },
});

const entityStyles = StyleSheet.create({
  entityMention: {
    textDecorationLine: 'underline',
    textDecorationStyle: 'dotted',
    textDecorationColor: colors.textMuted,
  },
  entityMentionLinked: {
    textDecorationColor: colors.rubric,
  },
  popupContainer: {
    backgroundColor: colors.parchmentDark,
    borderLeftWidth: 3,
    borderLeftColor: colors.rubric,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 16,
    marginTop: 4,
  },
  popupType: {
    fontFamily: fonts.ui,
    fontSize: 9,
    textTransform: 'uppercase',
    letterSpacing: 1,
    color: colors.textMuted,
    marginBottom: 4,
  },
  popupName: {
    fontFamily: fonts.body,
    fontSize: 16,
    color: colors.ink,
    marginBottom: 6,
  },
  popupSynthesis: {
    fontFamily: fonts.reading,
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginBottom: 10,
  },
  popupUrl: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
    marginBottom: 10,
    textDecorationLine: 'underline',
  },
  popupActions: {
    flexDirection: 'row',
    gap: 16,
    flexWrap: 'wrap',
  },
  popupAction: {
    paddingVertical: 4,
    minHeight: layout.touchTarget,
    justifyContent: 'center',
  },
  popupActionResearch: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
  },
  popupActionDismiss: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
});

const followUpStyles = StyleSheet.create({
  container: {
    marginTop: 24,
    marginBottom: 8,
  },
  sectionTitle: {
    ...type.sectionHead,
    color: colors.rubric,
    marginBottom: 12,
  },
  questionCard: {
    borderLeftWidth: 2,
    borderLeftColor: colors.rule,
    paddingLeft: 14,
    marginBottom: 16,
  },
  questionText: {
    fontFamily: fonts.readingItalic,
    fontSize: 15,
    lineHeight: 22,
    color: colors.textBody,
    marginBottom: 4,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  connectsTo: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  researchButton: {
    paddingVertical: 4,
    alignSelf: 'flex-start',
    minHeight: layout.touchTarget,
    justifyContent: 'center',
  },
  researchButtonText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
  },
  launchedText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.claimNew,
  },
  generateMoreButton: {
    paddingVertical: 4,
    alignSelf: 'flex-start',
    minHeight: layout.touchTarget,
    justifyContent: 'center',
    marginTop: 4,
  },
  generateMoreText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.rubric,
  },
});

// --- Follow Topics Styles ---

const followTopicStyles = StyleSheet.create({
  container: {
    marginTop: 24,
    marginBottom: 8,
  },
  sectionTitle: {
    ...type.sectionHead,
    color: colors.rubric,
    marginBottom: 12,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  chip: {
    borderWidth: 1,
    borderColor: colors.rule,
    borderRadius: 3,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minHeight: layout.touchTarget,
    justifyContent: 'center',
  },
  chipActive: {
    borderColor: colors.rubric,
    backgroundColor: 'rgba(139,37,0,0.05)',
  },
  chipText: {
    fontFamily: fonts.bodyItalic,
    fontSize: 13,
    color: colors.textSecondary,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  chipTextActive: {
    color: colors.rubric,
  },
});

// --- Connected Reading Styles ---

const connectedStyles = StyleSheet.create({
  container: {
    marginTop: 24,
    marginBottom: 8,
  },
  sectionTitle: {
    ...type.sectionHead,
    color: colors.rubric,
    marginBottom: 12,
  },
  card: {
    borderLeftWidth: 2,
    borderLeftColor: colors.rule,
    paddingLeft: 14,
    paddingVertical: 8,
    marginBottom: 12,
  },
  cardRead: {
    opacity: 0.6,
  },
  cardTitle: {
    fontFamily: fonts.bodyMedium,
    fontSize: 14,
    lineHeight: 19,
    color: colors.textPrimary,
    marginBottom: 4,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  cardTitleRead: {
    color: colors.textSecondary,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardClaimCount: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    flex: 1,
  },
  cardReadLabel: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  cardQueuedLabel: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.claimNew,
  },
  queueButton: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: colors.rubric,
    minHeight: 28,
    justifyContent: 'center',
  },
  queueButtonText: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  // Inline annotations
  inlineAnnotation: {
    paddingLeft: 16,
    paddingVertical: 4,
    marginTop: -4,
    marginBottom: 4,
  },
  inlineAnnotationText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    lineHeight: 16,
  },
  inlineAnnotationPrefix: {
    color: colors.textMuted,
  },
  inlineAnnotationTitle: {
    color: colors.rubric,
    fontFamily: fonts.bodyItalic,
    fontSize: 11,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  inlineAnnotationTitleRead: {
    color: colors.textSecondary,
  },
  inlineAnnotationRead: {
    color: colors.textMuted,
    fontSize: 10,
  },
  inlineAnnotationQueued: {
    color: colors.claimNew,
    fontSize: 10,
  },
  inlineAnnotationQueue: {
    color: colors.textMuted,
    fontSize: 10,
  },
});

// --- Web Margin Styles (Airy Folio) ---

const marginStyles = StyleSheet.create({
  // Left margin
  leftMargin: {
    paddingTop: 48,
    paddingBottom: 48,
    paddingLeft: 28,
    paddingRight: 24,
    borderRightWidth: 1,
    borderRightColor: colors.rule,
  },

  // Metadata blocks — italic EB Garamond labels
  metaBlock: {
    marginBottom: 22,
  },
  metaLabel: {
    fontFamily: fonts.bodyItalic,
    fontSize: 11.5,
    color: colors.textMuted,
    marginBottom: 3,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  metaValue: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
    lineHeight: 20,
  },
  topicText: {
    fontFamily: fonts.bodyItalic,
    fontSize: 12.5,
    color: colors.rubric,
    lineHeight: 20,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },

  // Novelty bar
  noveltyBlock: {
    marginBottom: 22,
  },
  noveltyBar: {
    flexDirection: 'row' as const,
    height: 3,
    marginTop: 6,
    marginBottom: 4,
    gap: 1,
  },
  noveltyBarNew: {
    height: 3,
    backgroundColor: colors.claimNew,
  },
  noveltyBarExt: {
    height: 3,
    backgroundColor: colors.textMuted,
  },
  noveltyBarKnown: {
    height: 3,
    backgroundColor: colors.rule,
  },
  noveltyCounts: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
  },

  // Reading mode toggle — text with rubric underline
  modeBlock: {
    marginBottom: 22,
  },
  modeRow: {
    flexDirection: 'row' as const,
    gap: 14,
    marginTop: 4,
  },
  modeText: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.textMuted,
  },
  modeTextActive: {
    color: colors.ink,
    borderBottomWidth: 1.5,
    borderBottomColor: colors.rubric,
    paddingBottom: 1,
  },

  // Actions — text links
  actionsSection: {
    borderTopWidth: 1,
    borderTopColor: colors.rule,
    paddingTop: 20,
    marginTop: 28,
    gap: 10,
  },
  actionLink: {
    paddingVertical: 1,
  },
  actionLinkText: {
    fontFamily: fonts.body,
    fontSize: 13.5,
    color: colors.textSecondary,
  },

  // Keyboard shortcuts
  shortcutsBlock: {
    borderTopWidth: 1,
    borderTopColor: colors.rule,
    paddingTop: 14,
    marginTop: 24,
  },
  kbdBadge: {
    minWidth: 18,
    height: 16,
    backgroundColor: colors.parchmentDark,
    borderRadius: 2,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    paddingHorizontal: 4,
  },
  kbdText: {
    fontFamily: fonts.ui,
    fontSize: 9.5,
    color: colors.textMuted,
  },
  shortcutRow: {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    gap: 7,
    marginBottom: 5,
  },
  shortcutLabel: {
    fontFamily: fonts.ui,
    fontSize: 9.5,
    color: colors.textMuted,
  },

  // Right margin — footnote style
  rightMargin: {
    paddingTop: 48,
    paddingBottom: 48,
    paddingLeft: 24,
    paddingRight: 28,
    borderLeftWidth: 1,
    borderLeftColor: colors.rule,
  },
  rightSection: {
    marginBottom: 28,
  },
  rightSectionTitle: {
    fontFamily: fonts.bodyItalic,
    fontSize: 11.5,
    color: colors.textMuted,
    marginBottom: 10,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  footnoteItem: {
    marginBottom: 14,
    paddingLeft: 10,
    borderLeftWidth: 1,
    borderLeftColor: 'transparent',
  },
  footnoteText: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 19,
  },
  footnoteMeta: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    marginTop: 2,
  },
  inquiryItem: {
    marginBottom: 12,
    paddingLeft: 10,
  },
  inquiryText: {
    fontFamily: fonts.readingItalic,
    fontSize: 12.5,
    color: colors.textSecondary,
    lineHeight: 18,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  researchLink: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.rubric,
    marginTop: 2,
  },
  researchLaunched: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.claimNew,
    marginTop: 2,
  },
});
