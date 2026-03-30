import { useState, useCallback, useMemo } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, Platform,
  ActivityIndicator, Animated,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Swipeable } from 'react-native-gesture-handler';
import { setFeedbackContext } from '../../lib/feedback-context';
import { logEvent } from '../../data/logger';
import { getPhysicalBooks, getBookCaptures, archiveBook } from '../../data/book-store';
import { useBookStoreVersion } from '../../data/use-book-store';
import type { PhysicalBook } from '../../data/types';
import { colors, fonts, type, layout } from '../../design/tokens';
import DoubleRule from '../../components/DoubleRule';
import PetrarcaDrawer from '../../components/PetrarcaDrawer';

function formatTimeAgo(timestamp: number): string {
  const hours = Math.floor((Date.now() - timestamp) / 3600000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = Math.min(100, Math.round((current / total) * 100));
  return (
    <View style={progressStyles.track}>
      <View style={[progressStyles.fill, { width: `${pct}%` as any }]} />
    </View>
  );
}

const progressStyles = StyleSheet.create({
  track: { height: 3, backgroundColor: colors.rule, borderRadius: 1.5, overflow: 'hidden', marginTop: 8 },
  fill: { height: '100%', backgroundColor: colors.rubric, borderRadius: 1.5 },
});

function BookRow({ book, captureCount, onPress, onDelete }: { book: PhysicalBook; captureCount: number; onPress: () => void; onDelete: () => void }) {
  const [hovered, setHovered] = useState(false);
  const isWeb = Platform.OS === 'web';
  const isIdentifying = book.processing_status === 'identifying';
  const statusLabel = isIdentifying ? 'Identifying...'
    : book.reading_status === 'finished' ? 'Finished'
    : book.reading_status === 'want_to_read' ? 'Want to read'
    : book.reading_status === 'paused' ? 'Paused'
    : book.current_chapter || 'Reading';
  const positionText = book.current_page
    ? `p. ${book.current_page}${book.page_count ? ` / ${book.page_count}` : ''}`
    : null;
  const coverUri = book.cover_url || book.cover_image_uri;

  const renderRightActions = (
    _progress: Animated.AnimatedInterpolation<number>,
    dragX: Animated.AnimatedInterpolation<number>,
  ) => {
    const scale = dragX.interpolate({ inputRange: [-100, 0], outputRange: [1, 0], extrapolate: 'clamp' });
    return (
      <Animated.View style={[bookStyles.swipeAction, { transform: [{ scale }] }]}>
        <Text style={bookStyles.swipeActionText}>Remove</Text>
      </Animated.View>
    );
  };

  const rowContent = (
    <Pressable
      style={[bookStyles.row, isWeb && hovered && bookStyles.rowHovered]}
      onPress={onPress}
      {...(isWeb ? { onMouseEnter: () => setHovered(true), onMouseLeave: () => setHovered(false) } as any : {})}
    >
      <View style={bookStyles.coverWrap}>
        {coverUri ? (
          <Image source={{ uri: coverUri }} style={bookStyles.cover} />
        ) : (
          <View style={bookStyles.coverPlaceholder}>
            <Text style={bookStyles.coverInitial}>{book.title.charAt(0)}</Text>
          </View>
        )}
      </View>
      <View style={bookStyles.info}>
        <Text style={bookStyles.title} numberOfLines={2}>{book.title}</Text>
        <Text style={bookStyles.author}>{book.author}</Text>
        <View style={bookStyles.metaRow}>
          <Text style={bookStyles.status}>{statusLabel}</Text>
          {positionText && <Text style={bookStyles.position}> · {positionText}</Text>}
        </View>
        {book.topics.length > 0 && (
          <View style={bookStyles.topicRow}>
            {book.topics.slice(0, 2).map(t => (
              <Text key={t} style={bookStyles.topic}>{t}</Text>
            ))}
          </View>
        )}
        {book.current_page && book.page_count && book.reading_status === 'reading' && (
          <ProgressBar current={book.current_page} total={book.page_count} />
        )}
      </View>
      <View style={bookStyles.sidebar}>
        {isIdentifying ? (
          <ActivityIndicator size="small" color={colors.rubric} />
        ) : (
          <>
            <Text style={bookStyles.sideNumber}>{captureCount}</Text>
            <Text style={bookStyles.sideLabel}>notes</Text>
            <Text style={bookStyles.timeAgo}>{formatTimeAgo(book.last_interaction_at)}</Text>
          </>
        )}
      </View>
      {isWeb && hovered && (
        <Pressable style={bookStyles.removeButton} onPress={(e) => { e.stopPropagation(); onDelete(); }} hitSlop={8}>
          <Text style={bookStyles.removeButtonText}>×</Text>
        </Pressable>
      )}
    </Pressable>
  );

  if (isWeb) return rowContent;

  return (
    <Swipeable
      renderRightActions={renderRightActions}
      onSwipeableOpen={() => onDelete()}
      overshootRight={false}
    >
      {rowContent}
    </Swipeable>
  );
}

const bookStyles = StyleSheet.create({
  row: { position: 'relative' as const, flexDirection: 'row', paddingVertical: 14, paddingHorizontal: layout.screenPadding, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule, gap: 14, backgroundColor: colors.parchment, ...(Platform.OS === 'web' ? { cursor: 'pointer' as any } : {}) },
  rowHovered: { backgroundColor: colors.parchmentHover },
  coverWrap: { width: 52, height: 72, borderRadius: 2, overflow: 'hidden', backgroundColor: colors.rule },
  cover: { width: 52, height: 72, borderRadius: 2 },
  coverPlaceholder: { width: 52, height: 72, backgroundColor: colors.parchmentDark, borderWidth: 1, borderColor: colors.rule, borderRadius: 2, alignItems: 'center', justifyContent: 'center' },
  coverInitial: { fontFamily: fonts.displaySemiBold, fontSize: 24, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  info: { flex: 1 },
  title: { fontFamily: fonts.bodyMedium, fontSize: 15, lineHeight: 20, color: colors.textPrimary, marginBottom: 2, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  author: { fontFamily: fonts.readingItalic, fontSize: 13, color: colors.textSecondary, marginBottom: 4, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  metaRow: { flexDirection: 'row', alignItems: 'center' },
  status: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted },
  position: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted },
  topicRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  topic: { fontFamily: fonts.bodyItalic, fontSize: 11, color: colors.rubric, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  sidebar: { width: 56, alignItems: 'flex-end', justifyContent: 'flex-start', paddingTop: 2 },
  sideNumber: { fontFamily: fonts.displaySemiBold, fontSize: 22, color: colors.ink, lineHeight: 26, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  sideLabel: { fontFamily: fonts.uiMedium, fontSize: 9, letterSpacing: 0.5, textTransform: 'uppercase', color: colors.textMuted, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  timeAgo: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted, marginTop: 6 },
  removeButton: { position: 'absolute', top: 6, right: 6, width: 24, height: 24, borderRadius: 12, backgroundColor: colors.parchmentDark, alignItems: 'center', justifyContent: 'center' },
  removeButtonText: { fontFamily: fonts.ui, fontSize: 16, color: colors.textMuted, lineHeight: 18 },
  swipeAction: { justifyContent: 'center', paddingHorizontal: 24, backgroundColor: colors.rubric, alignItems: 'flex-end' },
  swipeActionText: { fontFamily: fonts.ui, fontSize: 13, color: colors.parchment },
});

type FilterMode = 'active' | 'all' | 'archived';

export default function LibraryScreen() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterMode>('active');
  const [refreshKey, setRefreshKey] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Re-read books when screen is focused
  useFocusEffect(useCallback(() => {
    setRefreshKey(k => k + 1);
    setFeedbackContext({ screen: 'library' });
  }, []));

  const storeVersion = useBookStoreVersion();
  const allBooks = useMemo(() => getPhysicalBooks(), [refreshKey, storeVersion]);

  const books = useMemo(() => {
    // Always exclude archived (soft-deleted) books
    const visible = allBooks.filter(b => b.reading_status !== 'archived');
    if (filter === 'active') {
      return visible.filter(b => b.reading_status !== 'finished');
    } else if (filter === 'archived') {
      return visible.filter(b => b.reading_status === 'finished');
    }
    return visible;
  }, [allBooks, filter]);

  const captureCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const b of allBooks) {
      counts[b.id] = getBookCaptures(b.id).length;
    }
    return counts;
  }, [allBooks, refreshKey, storeVersion]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <View style={styles.headerContainer}>
        <View style={styles.titleRow}>
          <View>
            <Text style={styles.screenTitle}>Library</Text>
            <Text style={styles.screenSubtitle}>Books & reading notes</Text>
          </View>
          <View style={{ flexDirection: 'row', gap: 6 }}>
            <Pressable style={styles.revisitButton} onPress={() => {
              logEvent('library_revisit_tap');
              router.push('/resurfacing' as any);
            }}>
              <Text style={styles.revisitButtonText}>{'\u2726'} Revisit</Text>
            </Pressable>
            <Pressable style={styles.revisitButton} onPress={() => {
              logEvent('library_kindle_tap');
              router.push('/kindle-curation' as any);
            }}>
              <Text style={styles.revisitButtonText}>Kindle</Text>
            </Pressable>
            <Pressable style={styles.addButton} onPress={() => {
              logEvent('library_add_book_tap');
              router.push('/add-book' as any);
            }}>
              <Text style={styles.addButtonText}>+</Text>
            </Pressable>
            <Pressable style={styles.drawerButton} onPress={() => {
              logEvent('drawer_open', { source: 'library' });
              setDrawerOpen(true);
            }}>
              <Text style={styles.drawerButtonText}>{'\u2726'}</Text>
            </Pressable>
          </View>
        </View>
        <DoubleRule />
        <View style={styles.filterRow}>
          {(['active', 'all', 'archived'] as FilterMode[]).map(mode => (
            <Pressable key={mode} style={styles.filterTab} onPress={() => {
              logEvent('library_filter_change', { filter: mode });
              setFilter(mode);
            }}>
              <Text style={[styles.filterText, filter === mode && styles.filterTextActive]}>
                {mode === 'active' ? 'Reading' : mode === 'all' ? 'All' : 'Finished'}
              </Text>
              {filter === mode && <View style={styles.filterDot} />}
            </Pressable>
          ))}
        </View>
      </View>

      {books.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>{'\u2726'}</Text>
          <Text style={styles.emptyTitle}>No books here yet</Text>
          <Text style={styles.emptySubtitle}>
            {filter === 'archived' ? 'Finished books will appear here' : 'Tap "+ Add Book" to photograph a cover'}
          </Text>
        </View>
      ) : (
        books.map(book => (
          <BookRow key={book.id} book={book} captureCount={captureCounts[book.id] || 0}
            onPress={() => { logEvent('library_book_tap', { book_id: book.id }); router.push({ pathname: '/book-detail', params: { id: book.id } } as any); }}
            onDelete={() => {
              const doArchive = () => {
                archiveBook(book.id);
                logEvent('library_book_removed', { book_id: book.id, title: book.title });
              };
              if (Platform.OS === 'web') {
                if (confirm(`Remove "${book.title}" from library?`)) doArchive();
              } else {
                Alert.alert('Remove book', `Remove "${book.title}" from your library?`, [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Remove', style: 'destructive', onPress: doArchive },
                ]);
              }
            }} />
        ))
      )}
      <PetrarcaDrawer visible={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  content: { paddingBottom: 40, ...(Platform.OS === 'web' ? { maxWidth: layout.contentMaxWidth, width: '100%', alignSelf: 'center' as const } : {}) },
  headerContainer: { paddingTop: 12 },
  titleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', paddingHorizontal: layout.screenPadding, marginBottom: 12 },
  screenTitle: { ...type.screenTitle, color: colors.ink },
  screenSubtitle: { ...type.screenSubtitle, color: colors.textSecondary, marginTop: 2, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  addButton: { borderWidth: 1, borderColor: colors.rubric, paddingVertical: 8, paddingHorizontal: 16, borderRadius: 2, marginTop: 4 },
  addButtonText: { fontFamily: fonts.body, fontSize: 13, color: colors.rubric },
  revisitButton: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 4, borderWidth: 1, borderColor: colors.rubric },
  revisitButtonText: { fontFamily: fonts.body, fontSize: 13, color: colors.rubric },
  drawerButton: { paddingVertical: 8, paddingHorizontal: 12, borderRadius: 4, borderWidth: 1, borderColor: colors.rule },
  drawerButtonText: { fontFamily: fonts.display, fontSize: 16, color: colors.rubric },
  filterRow: { flexDirection: 'row', paddingHorizontal: layout.screenPadding, paddingTop: 14, paddingBottom: 4, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule },
  filterTab: { paddingVertical: 10, paddingHorizontal: 16, alignItems: 'center', minHeight: 44, justifyContent: 'center' },
  filterText: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted },
  filterTextActive: { color: colors.ink },
  filterDot: { position: 'absolute', bottom: 0, width: 4, height: 4, borderRadius: 2, backgroundColor: colors.rubric },
  empty: { alignItems: 'center', paddingTop: 80, gap: 8 },
  emptyIcon: { fontFamily: fonts.display, fontSize: 28, color: colors.textMuted, marginBottom: 4 },
  emptyTitle: { ...type.screenTitle, color: colors.ink, fontSize: 18 },
  emptySubtitle: { ...type.entrySummary, color: colors.textSecondary, textAlign: 'center', paddingHorizontal: 40 },
});
