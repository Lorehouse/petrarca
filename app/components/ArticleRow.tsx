import { useState } from 'react';
import { View, Text, Pressable, StyleSheet, Animated, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Swipeable } from 'react-native-gesture-handler';
import { colors, fonts } from '../design/tokens';
import { logEvent } from '../data/logger';
import {
  getReadingState, dismissArticle, recordInterestSignal, markArticleRead,
} from '../data/store';
import { addToQueue } from '../data/queue';
import { isKnowledgeReady, getArticleNovelty } from '../data/knowledge-engine';
import { getDisplayTitle } from '../lib/display-utils';
import type { Article } from '../data/types';

interface ArticleRowProps {
  article: Article;
  onDismiss: () => void;
  onQueue: () => void;
  isFocused?: boolean;
  onSwipeComplete?: () => void;
}

function NoveltyBadge({ noveltyRatio }: { noveltyRatio: number }) {
  const percent = Math.round(noveltyRatio * 100);
  const isHigh = noveltyRatio >= 0.6;
  const isLow = noveltyRatio < 0.4;

  const badgeColor = isLow
    ? 'rgba(176,168,152,0.5)'
    : colors.claimNew;

  const label = isHigh && noveltyRatio >= 0.9 ? 'new' : `${percent}%`;

  return (
    <View style={[styles.badge, { backgroundColor: badgeColor }]}>
      <Text style={styles.badgeText}>{label}</Text>
    </View>
  );
}

export default function ArticleRow({
  article,
  onDismiss,
  onQueue,
  isFocused,
  onSwipeComplete,
}: ArticleRowProps) {
  const router = useRouter();
  const state = getReadingState(article.id);
  const isRead = state.status === 'read';
  const [hovered, setHovered] = useState(false);

  const novelty = isKnowledgeReady() ? getArticleNovelty(article.id) : null;

  const handleSwipeRight = () => {
    dismissArticle(article.id, 'swiped');
    recordInterestSignal('swipe_dismiss', article.id);
    logEvent('feed_swipe_dismiss', { article_id: article.id });
    onDismiss();
  };

  const handleSwipeLeft = async () => {
    await addToQueue(article.id);
    logEvent('feed_swipe_queue', { article_id: article.id });
    onQueue();
  };

  const handleDismissHover = () => {
    dismissArticle(article.id, 'hover_dismiss');
    recordInterestSignal('swipe_dismiss', article.id);
    logEvent('feed_hover_dismiss', { article_id: article.id });
    onDismiss();
  };

  const handleArchiveHover = () => {
    markArticleRead(article.id);
    logEvent('feed_hover_archive', { article_id: article.id });
    onDismiss();
  };

  const renderRightActions = (
    _progress: Animated.AnimatedInterpolation<number>,
    dragX: Animated.AnimatedInterpolation<number>,
  ) => {
    const scale = dragX.interpolate({
      inputRange: [-100, 0],
      outputRange: [1, 0],
      extrapolate: 'clamp',
    });
    return (
      <Animated.View style={[styles.swipeAction, styles.swipeActionDismiss, { transform: [{ scale }] }]}>
        <Text style={styles.swipeActionText}>Dismiss</Text>
      </Animated.View>
    );
  };

  const renderLeftActions = (
    _progress: Animated.AnimatedInterpolation<number>,
    dragX: Animated.AnimatedInterpolation<number>,
  ) => {
    const scale = dragX.interpolate({
      inputRange: [0, 100],
      outputRange: [0, 1],
      extrapolate: 'clamp',
    });
    return (
      <Animated.View style={[styles.swipeAction, styles.swipeActionQueue, { transform: [{ scale }] }]}>
        <Text style={styles.swipeActionText}>Queue</Text>
      </Animated.View>
    );
  };

  const isWeb = Platform.OS === 'web';

  const rowContent = (
    <Pressable
      style={[
        styles.row,
        isRead && styles.rowRead,
        isFocused && styles.rowFocused,
        isWeb && hovered && !isFocused && styles.rowHovered,
      ]}
      onPress={() => {
        logEvent('feed_article_tap', { article_id: article.id });
        recordInterestSignal('open_article', article.id);
        router.push({ pathname: '/reader', params: { id: article.id } });
      }}
      {...(isWeb ? {
        onMouseEnter: () => setHovered(true),
        onMouseLeave: () => setHovered(false),
      } as any : {})}
    >
      {isWeb && hovered && (
        <View style={styles.hoverActions}>
          <Pressable
            style={styles.hoverActionBtn}
            onPress={(e) => {
              e.stopPropagation();
              handleArchiveHover();
            }}
            {...{ onMouseEnter: () => setHovered(true) } as any}
          >
            <Text style={styles.hoverActionText}>{'\u2713'}</Text>
          </Pressable>
          <Pressable
            style={styles.hoverActionBtn}
            onPress={(e) => {
              e.stopPropagation();
              handleDismissHover();
            }}
            {...{ onMouseEnter: () => setHovered(true) } as any}
          >
            <Text style={styles.hoverActionText}>{'\u2715'}</Text>
          </Pressable>
        </View>
      )}
      <View style={styles.margin}>
        {novelty ? (
          <NoveltyBadge noveltyRatio={novelty.novelty_ratio} />
        ) : null}
      </View>
      <View style={styles.content}>
        <Text style={[styles.title, isRead && styles.titleRead]} numberOfLines={1}>
          {getDisplayTitle(article)}
        </Text>
        <Text style={styles.source} numberOfLines={1}>
          {article.hostname}
        </Text>
      </View>
      <View style={styles.minutes}>
        <Text style={styles.minutesText}>{article.estimated_read_minutes}</Text>
      </View>
    </Pressable>
  );

  if (isWeb) return rowContent;

  return (
    <Swipeable
      renderRightActions={renderRightActions}
      renderLeftActions={renderLeftActions}
      onSwipeableOpen={(direction) => {
        onSwipeComplete?.();
        if (direction === 'right') handleSwipeRight();
        else if (direction === 'left') handleSwipeLeft();
      }}
      overshootRight={false}
      overshootLeft={false}
    >
      {rowContent}
    </Swipeable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: colors.rule,
    backgroundColor: colors.parchment,
    minHeight: 44,
  },
  rowRead: {
    opacity: 0.5,
  },
  rowFocused: {
    borderLeftWidth: 3,
    borderLeftColor: colors.rubric,
    backgroundColor: 'rgba(139,37,0,0.03)',
  },
  rowHovered: {
    backgroundColor: 'rgba(139,37,0,0.02)',
  },
  hoverActions: {
    position: 'absolute',
    top: 6,
    right: 4,
    flexDirection: 'row',
    gap: 4,
    zIndex: 5,
  },
  hoverActionBtn: {
    width: 26,
    height: 26,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: colors.rule,
    backgroundColor: colors.parchment,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hoverActionText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.textMuted,
  },
  margin: {
    width: 48,
    backgroundColor: colors.parchmentDark,
    borderRightWidth: 1,
    borderRightColor: colors.rule,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'stretch',
    paddingVertical: 8,
  },
  badge: {
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 2,
  },
  badgeText: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: '#ffffff',
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  content: {
    flex: 1,
    paddingHorizontal: 10,
    paddingVertical: 8,
    justifyContent: 'center',
  },
  title: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.textPrimary,
    lineHeight: 19,
  },
  titleRead: {
    color: colors.textSecondary,
  },
  source: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    marginTop: 2,
  },
  minutes: {
    width: 32,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'stretch',
  },
  minutesText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  swipeAction: {
    justifyContent: 'center',
    paddingHorizontal: 20,
    marginVertical: 0,
  },
  swipeActionDismiss: {
    backgroundColor: colors.rubric,
    alignItems: 'flex-end',
  },
  swipeActionQueue: {
    backgroundColor: colors.claimNew,
    alignItems: 'flex-start',
  },
  swipeActionText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.parchment,
  },
});
