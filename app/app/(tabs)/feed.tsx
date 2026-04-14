import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import {
  View, Text, StyleSheet, FlatList, Pressable, Animated,
  Platform, RefreshControl, ScrollView,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  getArticlesByLens, getReadArticles, recordInterestSignal, refreshContent,
  bumpFeedVersion, getFeedVersion, getInProgressArticles,
  getArticleById, getSyntheses, getFeedDistribution,
} from '../../data/store';
import type { FeedLens, SourceCategory } from '../../data/store';
import { ArticleMeta } from '../../data/types';
import { logEvent } from '../../data/logger';
import { colors, fonts, type, layout } from '../../design/tokens';
import { setFeedbackContext } from '../../lib/feedback-context';
import { addToQueue, getNextQueued, getQueuedArticleIds } from '../../data/queue';
import ContinueBar from '../../components/ContinueBar';
import SynthesisScroll from '../../components/SynthesisScroll';
import ArticleRow from '../../components/ArticleRow';
import DoubleRule from '../../components/DoubleRule';
import PetrarcaDrawer from '../../components/PetrarcaDrawer';
import KeyboardHintBar from '../../components/KeyboardHintBar';
import FeedFilterPills from '../../components/FeedFilterPills';
import ResearchSection from '../../components/ResearchSection';
import FeedSidebar from '../../components/FeedSidebar';
import { useKeyboardShortcuts, type ShortcutMap } from '../../hooks/useKeyboardShortcuts';

// --- Feed Screen ---

type ListItem =
  | { type: 'article'; article: ArticleMeta }
  | { type: 'separator' }
  | { type: 'read'; article: ArticleMeta }
  | { type: 'queue_header' };

export default function FeedScreen() {
  const router = useRouter();
  const [, forceUpdate] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(Platform.OS === 'web' ? 0 : -1);
  const [topicFilter, setTopicFilter] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState<SourceCategory | null>(null);
  const spinAnim = useRef(new Animated.Value(0)).current;
  const flatListRef = useRef<FlatList>(null);

  // Swipe hint — shown once on mobile
  const SWIPE_HINT_KEY = '@petrarca/swipe_hint_shown';
  const [showSwipeHint, setShowSwipeHint] = useState(false);
  const swipeHintTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    AsyncStorage.getItem(SWIPE_HINT_KEY).then(val => {
      if (val !== 'true') {
        setShowSwipeHint(true);
        logEvent('swipe_hint_shown');
      }
    });
    return () => { if (swipeHintTimeoutRef.current) clearTimeout(swipeHintTimeoutRef.current); };
  }, []);

  useEffect(() => {
    if (!showSwipeHint) return;
    swipeHintTimeoutRef.current = setTimeout(() => {
      setShowSwipeHint(false);
      AsyncStorage.setItem(SWIPE_HINT_KEY, 'true');
      logEvent('swipe_hint_dismissed', { trigger: 'timeout' });
    }, 4000);
    return () => { if (swipeHintTimeoutRef.current) clearTimeout(swipeHintTimeoutRef.current); };
  }, [showSwipeHint]);

  const dismissSwipeHint = useCallback((trigger: 'swipe' | 'tap') => {
    if (!showSwipeHint) return;
    setShowSwipeHint(false);
    if (swipeHintTimeoutRef.current) clearTimeout(swipeHintTimeoutRef.current);
    AsyncStorage.setItem(SWIPE_HINT_KEY, 'true');
    logEvent('swipe_hint_dismissed', { trigger });
  }, [showSwipeHint]);

  // Stable FlatList viewability tracking
  const onViewableItemsChanged = useRef(({ viewableItems }: any) => {
    const articleIds = viewableItems
      .filter((v: any) => v.item?.article?.id)
      .map((v: any) => v.item.article.id);
    if (articleIds.length > 0) logEvent('feed_articles_visible', { article_ids: articleIds });
  }).current;
  const viewabilityConfig = useRef({ itemVisiblePercentThreshold: 50, minimumViewTime: 1000 }).current;

  useFocusEffect(
    useCallback(() => {
      bumpFeedVersion();
      forceUpdate(n => n + 1);
      setFeedbackContext({ screen: 'feed', articleId: undefined, articleTitle: undefined, scrollProgress: undefined, readingMode: undefined });
    }, [])
  );

  useEffect(() => {
    if (refreshing) {
      spinAnim.setValue(0);
      Animated.loop(Animated.timing(spinAnim, { toValue: 1, duration: 1200, useNativeDriver: true })).start();
    } else {
      spinAnim.stopAnimation();
    }
  }, [refreshing]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    logEvent('feed_pull_refresh');
    try { await refreshContent(); } finally {
      setRefreshing(false);
      bumpFeedVersion();
      forceUpdate(n => n + 1);
    }
  }, []);

  const feedVersion = getFeedVersion();

  // Unfiltered articles for distribution counts, filtered for display
  const allFeedArticles = useMemo(() => getArticlesByLens('best').slice(0, 30), [feedVersion]);
  const articles = useMemo(() =>
    getArticlesByLens('best', topicFilter || undefined, sourceFilter || undefined).slice(0, 30),
    [feedVersion, topicFilter, sourceFilter]);
  const distribution = useMemo(() => getFeedDistribution(allFeedArticles), [allFeedArticles]);

  const handleDismiss = useCallback(() => { bumpFeedVersion(); forceUpdate(n => n + 1); }, []);
  const handleQueue = useCallback(() => { bumpFeedVersion(); forceUpdate(n => n + 1); }, []);

  // Keyboard nav data
  const getFocusedArticle = useCallback(() => {
    if (focusedIndex < 0 || focusedIndex >= articles.length) return null;
    return articles[focusedIndex];
  }, [focusedIndex, articles]);

  const scrollToArticle = useCallback((index: number) => {
    if (Platform.OS === 'web') {
      const article = articles[index];
      if (article) {
        const el = document.getElementById(`article-${article.id}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } else {
      try { flatListRef.current?.scrollToIndex({ index, viewPosition: 0.3, animated: true }); } catch {}
    }
  }, [articles]);

  // Keyboard shortcuts (web)
  const feedShortcuts = useMemo((): ShortcutMap => ({
    j: { handler: () => setFocusedIndex(i => {
      const next = Math.min(Math.max(i, 0) + 1, articles.length - 1);
      scrollToArticle(next); return next;
    }), label: 'next' },
    k: { handler: () => setFocusedIndex(i => {
      if (i <= 0) { if (Platform.OS === 'web') window.scrollTo({ top: 0, behavior: 'smooth' }); return -1; }
      const prev = i - 1; scrollToArticle(prev); return prev;
    }), label: 'prev' },
    Enter: { handler: () => {
      const a = getFocusedArticle();
      if (a) {
        logEvent('feed_article_tap', { article_id: a.id, via: 'keyboard' });
        recordInterestSignal('open_article', a.id);
        router.push({ pathname: '/reader', params: { id: a.id, lens: 'best' } });
      }
    }, label: 'open' },
    o: { handler: () => {
      const a = getFocusedArticle();
      if (a) {
        logEvent('feed_article_tap', { article_id: a.id, via: 'keyboard' });
        recordInterestSignal('open_article', a.id);
        router.push({ pathname: '/reader', params: { id: a.id, lens: 'best' } });
      }
    }, label: 'open' },
    e: { handler: () => {
      const a = getFocusedArticle();
      if (a) { import('../../data/store').then(m => m.dismissArticle(a.id, 'keyboard')); recordInterestSignal('swipe_dismiss', a.id); handleDismiss(); }
    }, label: 'dismiss' },
    q: { handler: async () => {
      const a = getFocusedArticle();
      if (a) { await addToQueue(a.id); handleQueue(); }
    }, label: 'queue' },
    r: { handler: () => { if (!refreshing) handleRefresh(); }, label: 'refresh' },
    gi: { handler: () => { window.scrollTo({ top: 0, behavior: 'smooth' }); setFocusedIndex(-1); }, label: 'top' },
    '?': { handler: () => {}, label: 'shortcuts' },
  }), [articles, getFocusedArticle, refreshing, handleDismiss, handleQueue, handleRefresh, router, scrollToArticle]);

  useKeyboardShortcuts(feedShortcuts, !drawerOpen);

  // --- Shared content pieces ---
  const refreshOrnament = refreshing ? (
    <View style={s.refreshOrnament}>
      <Animated.Text style={[s.refreshStar, {
        transform: [{ rotate: spinAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] }) }],
      }]}>{'\u2726'}</Animated.Text>
    </View>
  ) : null;

  const filterLabel = topicFilter || sourceFilter
    ? `${'\u2726'} For You${topicFilter ? ` \u00b7 ${topicFilter.replace(/-/g, ' ')}` : ''}${sourceFilter ? ` \u00b7 ${sourceFilter}` : ''}`
    : `${'\u2726'} For You`;

  // --- Mobile header ---
  const mobileHeaderContent = useMemo(() => (
    <>
      {refreshOrnament}
      <ContinueBar />
      <View style={s.headerRow}>
        <View style={{ flex: 1 }}>
          <Text style={s.headerTitle}>Feed</Text>
          <Text style={s.headerSubtitle}>
            {allFeedArticles.length} articles {'\u00b7'} {getSyntheses().length} syntheses
          </Text>
        </View>
        <Pressable style={s.drawerButton} onPress={() => {
          logEvent('drawer_open', { source: 'feed' });
          setDrawerOpen(true);
        }}>
          <Text style={s.drawerButtonText}>{'\u2726'}</Text>
        </Pressable>
      </View>
      <View style={{ paddingHorizontal: layout.screenPadding }}>
        <View style={{ height: 2, backgroundColor: colors.ink }} />
        <View style={{ height: 1, backgroundColor: colors.ink, marginTop: 5 }} />
      </View>
      <SynthesisScroll />
      <View style={{ paddingHorizontal: layout.screenPadding, marginTop: 4 }}>
        <View style={{ height: 1, backgroundColor: colors.ink }} />
        <View style={{ height: 1, backgroundColor: colors.ink, marginTop: 5 }} />
      </View>
      <View style={{ paddingHorizontal: layout.screenPadding }}>
        <ResearchSection />
      </View>
      <FeedFilterPills
        topics={distribution.topics}
        sources={distribution.sources}
        activeTopic={topicFilter}
        activeSource={sourceFilter}
        onTopicPress={setTopicFilter}
        onSourcePress={setSourceFilter}
      />
      <View style={s.forYouHeader}>
        <Text style={s.sectionLabel}>
          <Text style={{ color: colors.rubric }}>{filterLabel}</Text>
        </Text>
      </View>
    </>
  ), [refreshing, spinAnim, allFeedArticles.length, distribution, topicFilter, sourceFilter]);

  const focusedArticleId = focusedIndex >= 0 && focusedIndex < articles.length
    ? articles[focusedIndex].id : null;

  const queuedSet = useMemo(() => new Set(getQueuedArticleIds()), [feedVersion]);

  // --- Web layout (sidebar + feed) ---
  if (Platform.OS === 'web') {
    const webReadArticles = getReadArticles();

    return (
      <GestureHandlerRootView style={s.container}>
        <ScrollView style={s.container} contentContainerStyle={{ paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
          <View style={s.webSidebarLayout}>
            {/* Left sidebar */}
            <FeedSidebar
              topics={distribution.topics}
              sources={distribution.sources}
              activeTopic={topicFilter}
              activeSource={sourceFilter}
              totalCount={allFeedArticles.length}
              onTopicPress={setTopicFilter}
              onSourcePress={setSourceFilter}
              onDrawerOpen={() => { logEvent('drawer_open', { source: 'feed' }); setDrawerOpen(true); }}
            />
            {/* Feed column */}
            <View style={s.webFeedColumn}>
              {refreshOrnament}
              <ContinueBar />
              <View style={{ paddingHorizontal: 0 }}>
                <View style={{ height: 2, backgroundColor: colors.ink }} />
                <View style={{ height: 1, backgroundColor: colors.ink, marginTop: 5 }} />
              </View>
              <SynthesisScroll />
              <View style={{ marginTop: 4 }}>
                <View style={{ height: 1, backgroundColor: colors.ink }} />
                <View style={{ height: 1, backgroundColor: colors.ink, marginTop: 5 }} />
              </View>
              <View style={s.forYouHeader}>
                <Text style={s.sectionLabel}>
                  <Text style={{ color: colors.rubric }}>{filterLabel}</Text>
                </Text>
              </View>
              {articles.length === 0 ? (
                <View style={s.empty}>
                  <Text style={s.emptyTitle}>No articles match</Text>
                  <Text style={s.emptySubtitle}>Try a different filter</Text>
                </View>
              ) : (
                articles.map((article, i) => {
                  const showQueueHeader = i === 0 && queuedSet.has(article.id);
                  return (
                    <View key={article.id} nativeID={`article-${article.id}`}>
                      {showQueueHeader && (
                        <View style={s.queueHeader}>
                          <Text style={s.queueHeaderText}>
                            <Text style={{ color: colors.rubric }}>{'\u2726'} </Text>UP NEXT
                          </Text>
                        </View>
                      )}
                      <ArticleRow
                        article={article}
                        onDismiss={handleDismiss}
                        onQueue={handleQueue}
                        isFocused={article.id === focusedArticleId}
                      />
                    </View>
                  );
                })
              )}
              {webReadArticles.length > 0 && (
                <>
                  <View style={s.readSeparator}>
                    <View style={s.readSeparatorLine} />
                    <Text style={s.readSeparatorText}>Read</Text>
                    <View style={s.readSeparatorLine} />
                  </View>
                  {webReadArticles.map(article => (
                    <View key={article.id}>
                      <ArticleRow article={article} onDismiss={handleDismiss} onQueue={handleQueue} />
                    </View>
                  ))}
                </>
              )}
            </View>
          </View>
        </ScrollView>
        <KeyboardHintBar shortcuts={feedShortcuts} />
        <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
      </GestureHandlerRootView>
    );
  }

  // --- Mobile layout ---
  const mobileListData = useMemo((): ListItem[] => {
    const items: ListItem[] = [];
    let addedQueueHeader = false;
    for (const a of articles) {
      if (!addedQueueHeader && queuedSet.has(a.id)) {
        items.push({ type: 'queue_header' });
        addedQueueHeader = true;
      }
      items.push({ type: 'article', article: a });
    }
    const readArticles = getReadArticles();
    if (readArticles.length > 0) {
      items.push({ type: 'separator' });
      for (const a of readArticles) items.push({ type: 'read', article: a });
    }
    return items;
  }, [feedVersion, articles, queuedSet]);

  const firstArticleId = useMemo(() => {
    const first = mobileListData.find(item => item.type === 'article');
    return first && first.type === 'article' ? first.article.id : null;
  }, [mobileListData]);

  const mobileRenderItem = useCallback(({ item }: { item: ListItem }) => {
    switch (item.type) {
      case 'article': {
        const isFirst = item.article.id === firstArticleId;
        return (
          <View>
            <ArticleRow
              article={item.article}
              onDismiss={handleDismiss}
              onQueue={handleQueue}
              isFocused={item.article.id === focusedArticleId}
              onSwipeComplete={showSwipeHint ? () => dismissSwipeHint('swipe') : undefined}
            />
            {isFirst && showSwipeHint && (
              <Pressable style={s.swipeHintOverlay} onPress={() => dismissSwipeHint('tap')}>
                <View style={s.swipeHintPill}>
                  <Text style={s.swipeHintText}>{'\u2190 dismiss \u00b7 queue \u2192'}</Text>
                </View>
              </Pressable>
            )}
          </View>
        );
      }
      case 'queue_header':
        return (
          <View style={s.queueHeader}>
            <Text style={s.queueHeaderText}>
              <Text style={{ color: colors.rubric }}>{'\u2726'} </Text>UP NEXT
            </Text>
          </View>
        );
      case 'separator':
        return (
          <View style={[s.readSeparator, { paddingHorizontal: layout.screenPadding }]}>
            <View style={s.readSeparatorLine} />
            <Text style={s.readSeparatorText}>Read</Text>
            <View style={s.readSeparatorLine} />
          </View>
        );
      case 'read':
        return <ArticleRow article={item.article} onDismiss={handleDismiss} onQueue={handleQueue} />;
      default:
        return null;
    }
  }, [handleDismiss, handleQueue, focusedArticleId, firstArticleId, showSwipeHint, dismissSwipeHint]);

  const mobileKeyExtractor = useCallback((item: ListItem, index: number) => {
    if (item.type === 'article' || item.type === 'read') return item.article.id;
    if (item.type === 'queue_header') return 'queue-header';
    return `${item.type}-${index}`;
  }, []);

  return (
    <GestureHandlerRootView style={s.container}>
      <FlatList
        ref={flatListRef}
        data={mobileListData}
        keyExtractor={mobileKeyExtractor}
        ListHeaderComponent={() => <View>{mobileHeaderContent}</View>}
        renderItem={mobileRenderItem}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor="transparent"
            colors={['transparent']}
            style={{ backgroundColor: 'transparent' }}
          />
        }
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={viewabilityConfig}
        extraData={focusedArticleId}
        contentContainerStyle={{ paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
        removeClippedSubviews={false}
        ListEmptyComponent={
          <View style={s.empty}>
            <Text style={s.emptyTitle}>No articles yet</Text>
            <Text style={s.emptySubtitle}>Content will appear here once synced</Text>
          </View>
        }
      />
      <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </GestureHandlerRootView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  webContainer: { maxWidth: layout.webFeedMaxWidth, width: '100%', alignSelf: 'center' as const },
  webSidebarLayout: {
    flexDirection: 'row',
    maxWidth: 920,
    width: '100%',
    alignSelf: 'center' as const,
    gap: 24,
    paddingRight: 16,
  } as any,
  webFeedColumn: {
    flex: 1,
    maxWidth: 680,
  },

  headerRow: {
    flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between',
    paddingHorizontal: layout.screenPadding, paddingTop: 10, paddingBottom: 6,
  },
  headerTitle: { fontFamily: fonts.displaySemiBold, fontSize: 22, color: colors.ink, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  headerSubtitle: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted, marginTop: 3 },
  drawerButton: { paddingVertical: 8, paddingHorizontal: 12, borderRadius: 4, borderWidth: 1, borderColor: colors.rule },
  drawerButtonText: { fontFamily: fonts.display, fontSize: 16, color: colors.rubric },

  forYouHeader: { paddingHorizontal: layout.screenPadding, paddingTop: 10, paddingBottom: 4 },
  sectionLabel: { fontFamily: fonts.ui, fontSize: 9, color: colors.rubric, letterSpacing: 2, textTransform: 'uppercase' as const },

  refreshOrnament: { alignItems: 'center' as const, paddingVertical: 12 },
  refreshStar: { fontFamily: fonts.display, fontSize: 22, color: colors.rubric },

  queueHeader: { paddingHorizontal: layout.screenPadding, paddingTop: 10, paddingBottom: 4 },
  queueHeaderText: { fontFamily: fonts.body, fontSize: 11, color: colors.rubric, letterSpacing: 2, textTransform: 'uppercase' as const },

  readSeparator: { flexDirection: 'row', alignItems: 'center', paddingVertical: 16, gap: 12 },
  readSeparatorLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: colors.rule },
  readSeparatorText: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted, textTransform: 'uppercase' as const, letterSpacing: 1.5 },

  empty: { justifyContent: 'center', alignItems: 'center', paddingTop: 100, gap: 8 },
  emptyTitle: { ...type.screenTitle, color: colors.ink, fontSize: 20 },
  emptySubtitle: { ...type.entrySummary, color: colors.textSecondary },

  swipeHintOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, justifyContent: 'center', alignItems: 'center', zIndex: 20 },
  swipeHintPill: { backgroundColor: 'rgba(42,36,32,0.85)', paddingHorizontal: 20, paddingVertical: 10, borderRadius: 20 },
  swipeHintText: { fontFamily: fonts.ui, fontSize: 14, color: '#ffffff', letterSpacing: 0.3 },
});
