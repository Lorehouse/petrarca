import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import {
  View, Text, StyleSheet, Pressable, Image, Platform, TextInput,
  ActivityIndicator, Animated, FlatList, Keyboard,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { setFeedbackContext } from '../lib/feedback-context';
import { logEvent } from '../data/logger';
import { includeKindleBook } from '../lib/book-api';
import { addPhysicalBook } from '../data/book-store';
import { RESEARCH_BASE } from '../lib/chat-api';
import { colors, fonts, layout, spacing } from '../design/tokens';
import DoubleRule from '../components/DoubleRule';

// --- Types ---

interface KindleBrowseBook {
  key: string;
  asin?: string;
  title: string;
  title_display: string;
  author: string;
  cover_url?: string;
  progress_pct: number;
  status: string;
  category: string | null;
  added_to_petrarca: boolean;
  purchase_date?: string;
  last_seen?: string;
  is_sideloaded: boolean;
  epub_path?: string;
  source?: string;
}

type StatusFilter = 'all' | 'unreviewed' | 'reading' | 'read' | 'skipped';
type TrackedFilter = 'all' | 'tracked' | 'untracked';
type SortMode = 'recent' | 'title' | 'author' | 'progress';

// --- Component ---

export default function KindleBrowseScreen() {
  const router = useRouter();
  const [books, setBooks] = useState<KindleBrowseBook[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [processing, setProcessing] = useState<Set<string>>(new Set());

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [trackedFilter, setTrackedFilter] = useState<TrackedFilter>('untracked');
  const [sort, setSort] = useState<SortMode>('recent');

  const [toast, setToast] = useState<string | null>(null);
  const toastOpacity = useRef(new Animated.Value(0)).current;

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const showToast = (message: string) => {
    setToast(message);
    Animated.sequence([
      Animated.timing(toastOpacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.delay(2000),
      Animated.timing(toastOpacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => setToast(null));
  };

  const fetchBooks = useCallback(async (offset = 0, append = false) => {
    try {
      if (!append) setLoading(true);
      else setLoadingMore(true);

      const params = new URLSearchParams();
      if (debouncedSearch) params.set('search', debouncedSearch);
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (trackedFilter !== 'all') params.set('tracked', trackedFilter === 'tracked' ? 'true' : 'false');
      params.set('sort', sort);
      params.set('limit', '50');
      params.set('offset', String(offset));

      const resp = await fetch(`${RESEARCH_BASE}/kindle/browse?${params}`);
      if (!resp.ok) return;
      const data = await resp.json();

      if (append) {
        setBooks(prev => [...prev, ...(data.books || [])]);
      } else {
        setBooks(data.books || []);
      }
      setTotal(data.total || 0);
    } catch { /* ignore */ }
    finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [debouncedSearch, statusFilter, trackedFilter, sort]);

  useFocusEffect(useCallback(() => {
    setFeedbackContext({ screen: 'kindle-browse' });
    fetchBooks();
  }, [fetchBooks]));

  // Refetch when filters change
  useEffect(() => { fetchBooks(); }, [fetchBooks]);

  const handleInclude = async (book: KindleBrowseBook) => {
    setProcessing(prev => new Set(prev).add(book.key));
    try {
      logEvent('kindle_browse_include', { key: book.key, title: book.title_display });
      const result = await includeKindleBook(book.key);
      if (result.book) {
        addPhysicalBook(result.book);
        showToast(`Added: ${book.title_display}`);
        // Update local state
        setBooks(prev => prev.map(b =>
          b.key === book.key ? { ...b, added_to_petrarca: true } : b
        ));
      }
    } catch (e) {
      showToast(`Failed to add book`);
    } finally {
      setProcessing(prev => { const n = new Set(prev); n.delete(book.key); return n; });
    }
  };

  const handleLoadMore = () => {
    if (loadingMore || books.length >= total) return;
    fetchBooks(books.length, true);
  };

  const renderBook = ({ item }: { item: KindleBrowseBook }) => {
    const isProcessing = processing.has(item.key);
    const isTracked = item.added_to_petrarca;

    return (
      <Pressable
        style={styles.bookRow}
        onPress={() => {
          if (isTracked) {
            router.push({ pathname: '/book-detail', params: { id: `kindle_${item.asin || item.key}` } } as any);
          }
        }}
      >
        {/* Cover */}
        {item.cover_url ? (
          <Image source={{ uri: item.cover_url }} style={styles.cover} />
        ) : (
          <View style={[styles.cover, styles.coverPlaceholder]}>
            <Text style={styles.coverInitial}>
              {(item.title_display || '?')[0]}
            </Text>
          </View>
        )}

        {/* Details */}
        <View style={styles.bookDetails}>
          <Text style={styles.bookTitle} numberOfLines={2}>
            {item.title_display}
          </Text>
          <Text style={styles.bookAuthor} numberOfLines={1}>
            {item.author || 'Unknown author'}
          </Text>
          <View style={styles.badgeRow}>
            {item.category && (
              <Text style={styles.categoryBadge}>{item.category}</Text>
            )}
            {item.epub_path && (
              <Text style={styles.epubBadge}>EPUB</Text>
            )}
            {item.progress_pct > 0 && (
              <Text style={styles.progressText}>{Math.round(item.progress_pct)}%</Text>
            )}
            {isTracked && (
              <Text style={styles.trackedBadge}>Tracked</Text>
            )}
          </View>
          {item.progress_pct > 0 && (
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${Math.min(100, item.progress_pct)}%` as any }]} />
            </View>
          )}
        </View>

        {/* Action */}
        <View style={styles.actionCol}>
          {isTracked ? (
            <Text style={styles.trackedCheck}>{'\u2713'}</Text>
          ) : isProcessing ? (
            <ActivityIndicator size="small" color={colors.rubric} />
          ) : (
            <Pressable style={styles.includeButton} onPress={() => handleInclude(item)}>
              <Text style={styles.includeButtonText}>Include</Text>
            </Pressable>
          )}
        </View>
      </Pressable>
    );
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backText}>{'\u2039'} Library</Text>
        </Pressable>
        <Text style={styles.screenTitle}>Kindle Library</Text>
        <Text style={styles.screenSubtitle}>
          {total} books{debouncedSearch ? ` matching "${debouncedSearch}"` : ''}
        </Text>
      </View>
      <DoubleRule />

      {/* Search */}
      <View style={styles.searchRow}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search titles & authors..."
          placeholderTextColor={colors.textMuted}
          value={search}
          onChangeText={setSearch}
          returnKeyType="search"
          onSubmitEditing={() => Keyboard.dismiss()}
          clearButtonMode="while-editing"
        />
      </View>

      {/* Status filter */}
      <View style={styles.filterRow}>
        {(['all', 'unreviewed', 'reading', 'read', 'skipped'] as StatusFilter[]).map(s => (
          <Pressable key={s} onPress={() => setStatusFilter(s)}>
            <Text style={[styles.filterChip, statusFilter === s && styles.filterChipActive]}>
              {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Tracked + Sort */}
      <View style={styles.filterRow}>
        {(['all', 'tracked', 'untracked'] as TrackedFilter[]).map(t => (
          <Pressable key={t} onPress={() => setTrackedFilter(t)}>
            <Text style={[styles.filterChip, trackedFilter === t && styles.filterChipActive]}>
              {t === 'all' ? 'All' : t === 'tracked' ? 'Tracked' : 'Untracked'}
            </Text>
          </Pressable>
        ))}
        <View style={styles.sortSpacer} />
        {(['recent', 'title', 'author', 'progress'] as SortMode[]).map(m => (
          <Pressable key={m} onPress={() => setSort(m)}>
            <Text style={[styles.sortChip, sort === m && styles.sortChipActive]}>
              {m === 'recent' ? 'Recent' : m === 'title' ? 'A-Z' : m === 'author' ? 'Author' : '%'}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Book list */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.rubric} />
        </View>
      ) : (
        <FlatList
          data={books}
          keyExtractor={item => item.key}
          renderItem={renderBook}
          onEndReached={handleLoadMore}
          onEndReachedThreshold={0.3}
          ListEmptyComponent={
            <View style={styles.centered}>
              <Text style={styles.emptyText}>No books found</Text>
            </View>
          }
          ListFooterComponent={loadingMore ? (
            <ActivityIndicator size="small" color={colors.rubric} style={{ padding: 16 }} />
          ) : null}
          contentContainerStyle={styles.listContent}
        />
      )}

      {/* Toast */}
      {toast && (
        <Animated.View style={[styles.toast, { opacity: toastOpacity }]}>
          <Text style={styles.toastText}>{toast}</Text>
        </Animated.View>
      )}
    </View>
  );
}

// --- Styles ---

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  header: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: spacing.md,
    maxWidth: layout.contentMaxWidth,
    alignSelf: 'center',
    width: '100%',
  },
  backButton: {
    marginBottom: spacing.xs,
  },
  backText: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 15,
    color: colors.rubric,
  },
  screenTitle: {
    fontFamily: Platform.OS === 'web' ? "'Cormorant Garamond', Georgia, serif" : 'CormorantGaramond',
    fontSize: 28,
    fontWeight: '600',
    color: colors.ink,
    letterSpacing: 0.3,
  },
  screenSubtitle: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 2,
    marginBottom: spacing.sm,
  },

  // Search
  searchRow: {
    paddingHorizontal: layout.screenPadding,
    paddingVertical: spacing.sm,
    maxWidth: layout.contentMaxWidth,
    alignSelf: 'center',
    width: '100%',
  },
  searchInput: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 16,
    color: colors.ink,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.xs,
  },

  // Filters
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: layout.screenPadding,
    paddingVertical: spacing.xs,
    gap: spacing.sm,
    maxWidth: layout.contentMaxWidth,
    alignSelf: 'center',
    width: '100%',
    alignItems: 'center',
  },
  filterChip: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 14,
    color: colors.textMuted,
    paddingVertical: 3,
    paddingHorizontal: 8,
  },
  filterChipActive: {
    color: colors.rubric,
    fontWeight: '600',
    borderBottomWidth: 1.5,
    borderBottomColor: colors.rubric,
  },
  sortSpacer: {
    flex: 1,
  },
  sortChip: {
    fontFamily: Platform.OS === 'web' ? "'DM Sans', sans-serif" : 'DMSans',
    fontSize: 12,
    color: colors.textMuted,
    paddingVertical: 2,
    paddingHorizontal: 6,
  },
  sortChipActive: {
    color: colors.rubric,
    fontWeight: '600',
  },

  // List
  listContent: {
    paddingBottom: 60,
    maxWidth: layout.contentMaxWidth,
    alignSelf: 'center',
    width: '100%',
  },
  bookRow: {
    flexDirection: 'row',
    paddingHorizontal: layout.screenPadding,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.rule,
    gap: spacing.md,
    alignItems: 'flex-start',
  },
  cover: {
    width: 48,
    height: 70,
    borderRadius: 3,
    backgroundColor: colors.parchmentDark,
  },
  coverPlaceholder: {
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.rule,
  },
  coverInitial: {
    fontFamily: Platform.OS === 'web' ? "'Cormorant Garamond', Georgia, serif" : 'CormorantGaramond',
    fontSize: 22,
    color: colors.textMuted,
  },
  bookDetails: {
    flex: 1,
    gap: 2,
  },
  bookTitle: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond-Medium',
    fontSize: 16,
    color: colors.ink,
    lineHeight: 20,
  },
  bookAuthor: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 14,
    color: colors.textSecondary,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginTop: 4,
    alignItems: 'center',
  },
  categoryBadge: {
    fontFamily: Platform.OS === 'web' ? "'DM Sans', sans-serif" : 'DMSans',
    fontSize: 10,
    color: colors.textSecondary,
    backgroundColor: colors.parchmentDark,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 3,
    overflow: 'hidden',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  epubBadge: {
    fontFamily: Platform.OS === 'web' ? "'DM Sans', sans-serif" : 'DMSans-SemiBold',
    fontSize: 10,
    color: colors.success,
    backgroundColor: '#e8f5e9',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 3,
    overflow: 'hidden',
    letterSpacing: 0.3,
  },
  progressText: {
    fontFamily: Platform.OS === 'web' ? "'DM Sans', sans-serif" : 'DMSans',
    fontSize: 11,
    color: colors.textMuted,
  },
  trackedBadge: {
    fontFamily: Platform.OS === 'web' ? "'DM Sans', sans-serif" : 'DMSans',
    fontSize: 10,
    color: colors.rubric,
    borderWidth: 1,
    borderColor: colors.rubric,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressTrack: {
    height: 2,
    backgroundColor: colors.rule,
    borderRadius: 1,
    marginTop: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.rubric,
    borderRadius: 1,
  },

  // Action column
  actionCol: {
    width: 72,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: spacing.xs,
  },
  includeButton: {
    borderWidth: 1,
    borderColor: colors.rubric,
    borderRadius: 4,
    paddingVertical: 5,
    paddingHorizontal: 10,
  },
  includeButtonText: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond-Medium',
    fontSize: 13,
    color: colors.rubric,
  },
  trackedCheck: {
    fontSize: 18,
    color: colors.success,
  },

  // Empty & loading
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 60,
  },
  emptyText: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 16,
    color: colors.textMuted,
    fontStyle: 'italic',
  },

  // Toast
  toast: {
    position: 'absolute',
    bottom: 40,
    left: 20,
    right: 20,
    backgroundColor: colors.ink,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
    alignItems: 'center',
    maxWidth: 400,
    alignSelf: 'center',
  },
  toastText: {
    fontFamily: Platform.OS === 'web' ? "'EB Garamond', Georgia, serif" : 'EBGaramond',
    fontSize: 14,
    color: colors.parchment,
  },
});
