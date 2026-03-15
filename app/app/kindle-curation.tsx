import { useState, useCallback, useMemo, useRef } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Image, Platform,
  ActivityIndicator, Animated,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { logEvent } from '../data/logger';
import { RESEARCH_BASE } from '../lib/chat-api';
import { includeKindleBook } from '../lib/book-api';
import { addPhysicalBook } from '../data/book-store';
import { colors, fonts, layout } from '../design/tokens';
import DoubleRule from '../components/DoubleRule';

interface KindleBook {
  asin?: string;
  title: string;
  title_display?: string;
  author: string;
  cover_url?: string;
  progress?: { text?: string; percent?: number };
  status: string;   // unreviewed | reading | read | skipped
  category?: string; // non-fiction | historical-novel | novel | other
  added_to_petrarca?: boolean;
  first_seen?: string;
  last_seen?: string;
  finished_date?: string;
}

type SortMode = 'title' | 'progress' | 'recent' | 'category';
type FilterMode = 'all' | 'unreviewed' | 'non-fiction' | 'read' | 'skipped';

export default function KindleCurationScreen() {
  const router = useRouter();
  const [booksMap, setBooksMap] = useState<Record<string, KindleBook>>({});
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<Set<string>>(new Set());
  const [sort, setSort] = useState<SortMode>('recent');
  const [filter, setFilter] = useState<FilterMode>('unreviewed');
  const [classifying, setClassifying] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const toastOpacity = useRef(new Animated.Value(0)).current;

  const showToast = (message: string) => {
    setToast(message);
    Animated.sequence([
      Animated.timing(toastOpacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.delay(2000),
      Animated.timing(toastOpacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => setToast(null));
  };

  const fetchLibrary = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await fetch(`${RESEARCH_BASE}/kindle/library?exclude_processed=true`);
      if (resp.ok) {
        const data = await resp.json();
        setBooksMap(data.books || {});
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useFocusEffect(useCallback(() => { fetchLibrary(); }, [fetchLibrary]));

  const displayTitle = (book: KindleBook) => book.title_display || book.title;

  const books = useMemo(() => {
    let list = Object.entries(booksMap).map(([key, book]) => ({
      ...book,
      key,
      progressNum: book.progress?.percent || (book.progress?.text ? parseInt(book.progress.text) || 0 : 0),
    }));

    // Filter
    if (filter === 'unreviewed') list = list.filter(b => b.status === 'unreviewed');
    else if (filter === 'non-fiction') list = list.filter(b => ['non-fiction', 'classical-literature', 'literary-fiction', 'language-learning'].includes(b.category || ''));
    else if (filter === 'read') list = list.filter(b => b.status === 'read');
    else if (filter === 'skipped') list = list.filter(b => b.status === 'skipped');

    // Sort — use displayTitle for title sort
    if (sort === 'title') list.sort((a, b) => displayTitle(a).localeCompare(displayTitle(b)));
    else if (sort === 'progress') list.sort((a, b) => b.progressNum - a.progressNum);
    else if (sort === 'recent') list.sort((a, b) => (b.last_seen || '').localeCompare(a.last_seen || ''));
    else if (sort === 'category') list.sort((a, b) => (a.category || 'zzz').localeCompare(b.category || 'zzz'));

    return list;
  }, [booksMap, sort, filter]);

  const counts = useMemo(() => ({
    total: Object.keys(booksMap).length,
    unreviewed: Object.values(booksMap).filter(b => b.status === 'unreviewed').length,
    read: Object.values(booksMap).filter(b => b.status === 'read').length,
    nonFiction: Object.values(booksMap).filter(b => ['non-fiction', 'classical-literature', 'literary-fiction', 'language-learning'].includes(b.category || '')).length,
    skipped: Object.values(booksMap).filter(b => b.status === 'skipped').length,
  }), [booksMap]);

  const curate = async (key: string, updates: Partial<KindleBook>) => {
    setProcessing(prev => new Set(prev).add(key));
    try {
      await fetch(`${RESEARCH_BASE}/kindle/curate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates: [{ key, ...updates }] }),
      });
      setBooksMap(prev => ({
        ...prev,
        [key]: { ...prev[key], ...updates },
      }));
      logEvent('kindle_curate', { key, ...updates });
    } catch { /* ignore */ }
    finally {
      setProcessing(prev => { const n = new Set(prev); n.delete(key); return n; });
    }
  };

  const handleInclude = async (key: string) => {
    setProcessing(prev => new Set(prev).add(key));
    try {
      const result = await includeKindleBook(key);
      if (result.book && !result.already_existed) {
        await addPhysicalBook(result.book);
      }
      // Remove from local list
      setBooksMap(prev => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      const title = displayTitle(booksMap[key]) || result.book?.title || 'Book';
      showToast(`Added "${title}" to Library`);
      logEvent('kindle_include', { key, title });
    } catch (e) {
      showToast('Failed to include book');
    } finally {
      setProcessing(prev => { const n = new Set(prev); n.delete(key); return n; });
    }
  };

  const classifyAll = async () => {
    setClassifying(true);
    try {
      await fetch(`${RESEARCH_BASE}/kindle/classify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      logEvent('kindle_classify_triggered');
      setTimeout(fetchLibrary, 15000);
    } catch { /* ignore */ }
    finally { setClassifying(false); }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>{'\u2039'} Library</Text>
      </Pressable>

      <View style={styles.header}>
        <Text style={styles.title}>Import from Kindle</Text>
        <Text style={styles.subtitle}>
          {counts.total} books · {counts.unreviewed} to review · {counts.read} read · {counts.nonFiction} non-fiction
        </Text>
      </View>
      <DoubleRule />

      {/* Actions */}
      <View style={styles.actionsRow}>
        <Pressable style={styles.actionButton} onPress={classifyAll} disabled={classifying}>
          {classifying ? <ActivityIndicator size="small" color={colors.rubric} /> :
            <Text style={styles.actionText}>Auto-classify</Text>}
        </Pressable>
      </View>

      {/* Filters */}
      <View style={styles.filterRow}>
        {([
          ['all', `All (${counts.total})`],
          ['unreviewed', `Review (${counts.unreviewed})`],
          ['non-fiction', `Non-fiction (${counts.nonFiction})`],
          ['read', `Read (${counts.read})`],
          ['skipped', `Skipped (${counts.skipped})`],
        ] as [FilterMode, string][]).map(([mode, label]) => (
          <Pressable key={mode} style={styles.filterTab} onPress={() => setFilter(mode)}>
            <Text style={[styles.filterText, filter === mode && styles.filterTextActive]}>{label}</Text>
            {filter === mode && <View style={styles.filterDot} />}
          </Pressable>
        ))}
      </View>

      {/* Sort */}
      <View style={styles.sortRow}>
        <Text style={styles.sortLabel}>Sort:</Text>
        {(['recent', 'title', 'progress', 'category'] as SortMode[]).map(mode => (
          <Pressable key={mode} onPress={() => setSort(mode)}>
            <Text style={[styles.sortOption, sort === mode && styles.sortOptionActive]}>
              {mode === 'recent' ? 'Recent' : mode === 'title' ? 'Title' : mode === 'progress' ? 'Progress' : 'Category'}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading && <ActivityIndicator size="small" color={colors.rubric} style={{ marginTop: 20 }} />}

      {/* Book list */}
      {books.map(book => (
        <View key={book.key} style={styles.bookRow}>
          {book.cover_url ? (
            <Image source={{ uri: book.cover_url }} style={styles.bookCover} />
          ) : (
            <View style={[styles.bookCover, styles.bookCoverPlaceholder]}>
              <Text style={styles.bookCoverLetter}>{displayTitle(book)[0]}</Text>
            </View>
          )}
          <View style={styles.bookInfo}>
            <Text style={styles.bookTitle} numberOfLines={2}>{displayTitle(book)}</Text>
            <Text style={styles.bookAuthor} numberOfLines={1}>{book.author}</Text>
            <View style={styles.bookMeta}>
              {book.category && <Text style={styles.categoryBadge}>{book.category}</Text>}
              {book.progressNum > 0 && <Text style={styles.progressText}>{book.progressNum}%</Text>}
              {book.status !== 'unreviewed' && (
                <Text style={[styles.statusBadge,
                  book.status === 'read' && styles.statusRead,
                  book.status === 'skipped' && styles.statusSkipped,
                  book.status === 'reading' && styles.statusReading,
                ]}>{book.status}</Text>
              )}
            </View>
          </View>
          <View style={styles.bookActions}>
            {processing.has(book.key) ? (
              <ActivityIndicator size="small" color={colors.rubric} />
            ) : book.status === 'read' ? (
              <>
                <Pressable style={styles.actionPill} onPress={() => handleInclude(book.key)}>
                  <Text style={styles.actionPillText}>{'\u2726'} Include</Text>
                </Pressable>
                <Pressable style={styles.skipPill} onPress={() => curate(book.key, { status: 'skipped' })}>
                  <Text style={styles.skipPillText}>Skip</Text>
                </Pressable>
              </>
            ) : book.status === 'skipped' ? (
              <Pressable style={styles.actionPill} onPress={() => curate(book.key, { status: 'unreviewed' })}>
                <Text style={styles.actionPillText}>Undo</Text>
              </Pressable>
            ) : (
              <>
                <Pressable style={styles.actionPill} onPress={() => curate(book.key, { status: 'read' })}>
                  <Text style={styles.actionPillText}>{'\u2713'} Read</Text>
                </Pressable>
                <Pressable style={styles.skipPill} onPress={() => curate(book.key, { status: 'skipped' })}>
                  <Text style={styles.skipPillText}>Skip</Text>
                </Pressable>
              </>
            )}
          </View>
        </View>
      ))}

      {!loading && books.length === 0 && (
        <View style={styles.empty}>
          <Text style={styles.emptyText}>
            {filter === 'unreviewed' ? 'All books reviewed!' :
             filter === 'read' ? 'No books marked as read yet.' :
             'No books found.'}
          </Text>
        </View>
      )}

      {/* Toast */}
      {toast && (
        <Animated.View style={[styles.toast, { opacity: toastOpacity }]}>
          <Text style={styles.toastText}>{toast}</Text>
        </Animated.View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  content: { paddingBottom: 60, ...(Platform.OS === 'web' ? { maxWidth: 800, width: '100%', alignSelf: 'center' as const } : {}) },
  backButton: { paddingHorizontal: layout.screenPadding, paddingTop: 12, paddingBottom: 8 },
  backText: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  header: { paddingHorizontal: layout.screenPadding, paddingBottom: 12 },
  title: { fontFamily: fonts.displaySemiBold, fontSize: 28, color: colors.ink, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  subtitle: { fontFamily: fonts.ui, fontSize: 12, color: colors.textMuted, marginTop: 4 },
  actionsRow: { flexDirection: 'row', gap: 8, paddingHorizontal: layout.screenPadding, paddingVertical: 10 },
  actionButton: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 4, borderWidth: 1, borderColor: colors.rubric },
  actionText: { fontFamily: fonts.body, fontSize: 12, color: colors.rubric },
  filterRow: { flexDirection: 'row', paddingHorizontal: layout.screenPadding, paddingTop: 8, paddingBottom: 4, flexWrap: 'wrap', gap: 2, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule },
  filterTab: { paddingVertical: 8, paddingHorizontal: 10, alignItems: 'center', minHeight: 36, justifyContent: 'center' },
  filterText: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, letterSpacing: 0.3 },
  filterTextActive: { color: colors.ink },
  filterDot: { width: 4, height: 4, borderRadius: 2, backgroundColor: colors.rubric, marginTop: 3 },
  sortRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: layout.screenPadding, paddingVertical: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule },
  sortLabel: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.textMuted, letterSpacing: 0.5, textTransform: 'uppercase', ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  sortOption: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, paddingVertical: 4, paddingHorizontal: 6 },
  sortOptionActive: { color: colors.rubric },
  bookRow: { flexDirection: 'row', paddingHorizontal: layout.screenPadding, paddingVertical: 10, gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule, alignItems: 'center' },
  bookCover: { width: 44, height: 62, borderRadius: 2 },
  bookCoverPlaceholder: { backgroundColor: colors.parchmentDark, borderWidth: 1, borderColor: colors.rule, alignItems: 'center', justifyContent: 'center' },
  bookCoverLetter: { fontFamily: fonts.displaySemiBold, fontSize: 20, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  bookInfo: { flex: 1 },
  bookTitle: { fontFamily: fonts.body, fontSize: 13, lineHeight: 17, color: colors.ink, marginBottom: 2 },
  bookAuthor: { fontFamily: fonts.readingItalic, fontSize: 11, color: colors.textSecondary, marginBottom: 4, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  bookMeta: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', alignItems: 'center' },
  categoryBadge: { fontFamily: fonts.ui, fontSize: 9, color: colors.textMuted, backgroundColor: colors.parchmentDark, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 3 },
  progressText: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted },
  statusBadge: { fontFamily: fonts.ui, fontSize: 9, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 3 },
  statusRead: { backgroundColor: 'rgba(42,122,74,0.1)', color: colors.claimNew },
  statusSkipped: { backgroundColor: 'rgba(176,168,152,0.15)', color: colors.textMuted },
  statusReading: { backgroundColor: 'rgba(139,37,0,0.08)', color: colors.rubric },
  bookActions: { gap: 4, alignItems: 'flex-end' },
  actionPill: { paddingVertical: 5, paddingHorizontal: 10, borderRadius: 12, borderWidth: 1, borderColor: colors.claimNew },
  actionPillText: { fontFamily: fonts.ui, fontSize: 10, color: colors.claimNew },
  skipPill: { paddingVertical: 5, paddingHorizontal: 10, borderRadius: 12, borderWidth: 1, borderColor: colors.rule },
  skipPillText: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted },
  empty: { paddingVertical: 40, alignItems: 'center' },
  emptyText: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textMuted, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  toast: {
    position: 'absolute', bottom: 80, left: 20, right: 20,
    backgroundColor: colors.ink, borderRadius: 8, paddingVertical: 12, paddingHorizontal: 16,
    alignItems: 'center',
    ...(Platform.OS === 'web' ? { maxWidth: 400, alignSelf: 'center' as const, left: '50%' as any, transform: [{ translateX: '-50%' as any }] } : {}),
  },
  toastText: { fontFamily: fonts.ui, fontSize: 13, color: colors.parchment },
});
