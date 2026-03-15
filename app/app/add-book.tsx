import { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable, Platform, TextInput,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { logEvent } from '../data/logger';
import { addPhysicalBook, generateBookId, updatePhysicalBook } from '../data/book-store';
import { identifyBookCover } from '../lib/book-api';
import type { PhysicalBook } from '../data/types';
import { colors, fonts, type, layout } from '../design/tokens';
import DoubleRule from '../components/DoubleRule';

export default function AddBookScreen() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [pageCount, setPageCount] = useState('');
  const [error, setError] = useState('');

  const takePhoto = useCallback(async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Camera permission needed', 'Please allow camera access to photograph book covers.');
      return undefined;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8, allowsEditing: false });
    if (!result.canceled && result.assets[0]) return result.assets[0].uri;
    return undefined;
  }, []);

  const pickFromLibrary = useCallback(async () => {
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: 'images', quality: 0.8 });
    if (!result.canceled && result.assets[0]) return result.assets[0].uri;
    return undefined;
  }, []);

  const handleCapture = useCallback(async (source: 'camera' | 'library') => {
    const uri = source === 'camera' ? await takePhoto() : await pickFromLibrary();
    if (!uri) return;

    logEvent('book_add_photo_taken', { source });

    // Create placeholder book immediately
    const bookId = generateBookId();
    const placeholder: PhysicalBook = {
      id: bookId,
      title: 'Identifying...',
      author: '',
      cover_image_uri: uri,
      language: 'en',
      topics: [],
      chapters: [],
      reading_status: 'reading',
      added_at: Date.now(),
      last_interaction_at: Date.now(),
      metadata_source: 'photo',
      processing_status: 'identifying',
    };

    await addPhysicalBook(placeholder);
    router.back();

    // Background: identify and update
    try {
      const result = await identifyBookCover(uri);
      await updatePhysicalBook(bookId, {
        title: result.title || 'Unknown Book',
        author: result.author || '',
        cover_url: result.cover_url,
        isbn: result.isbn || undefined,
        publisher: result.publisher || undefined,
        year: result.year || undefined,
        page_count: result.page_count || undefined,
        topics: result.topics || [],
        chapters: result.chapters || [],
        processing_status: 'ready',
      });
      logEvent('book_add_identified', { book_id: bookId, title: result.title });
    } catch (e: any) {
      // Mark as ready even on failure — user can edit manually
      await updatePhysicalBook(bookId, {
        title: 'Unidentified Book',
        processing_status: 'ready',
      });
      logEvent('book_add_identify_failed', { book_id: bookId, error: e.message });
    }
  }, [takePhoto, pickFromLibrary, router]);

  const handleManualSave = useCallback(async () => {
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    const book: PhysicalBook = {
      id: generateBookId(),
      title: title.trim(),
      author: author.trim(),
      page_count: pageCount ? parseInt(pageCount, 10) : undefined,
      language: 'en',
      topics: [],
      chapters: [],
      reading_status: 'reading',
      added_at: Date.now(),
      last_interaction_at: Date.now(),
      metadata_source: 'manual',
      processing_status: 'ready',
    };
    await addPhysicalBook(book);
    logEvent('book_add_manual', { book_id: book.id, title: book.title });
    router.back();
  }, [title, author, pageCount, router]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Text style={styles.backText}>{'\u2039'} Cancel</Text>
      </Pressable>
      <View style={styles.headerSection}>
        <Text style={styles.screenTitle}>Add Book</Text>
        <Text style={styles.screenSubtitle}>Photograph the cover or enter details</Text>
      </View>
      <DoubleRule />

      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <View style={styles.captureStep}>
        <View style={styles.cameraPlaceholder}>
          <Text style={styles.cameraIcon}>{'\u2726'}</Text>
          <Text style={styles.cameraLabel}>Photograph the cover</Text>
          <Text style={styles.cameraHint}>Book will be added instantly, details filled in automatically</Text>
        </View>
        <View style={styles.captureActions}>
          <Pressable style={styles.primaryButton} onPress={() => handleCapture('camera')}>
            <Text style={styles.primaryButtonText}>Take Photo</Text>
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={() => handleCapture('library')}>
            <Text style={styles.secondaryButtonText}>Choose from Photos</Text>
          </Pressable>
        </View>
        <View style={styles.dividerRow}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>or enter manually</Text>
          <View style={styles.dividerLine} />
        </View>

        <View style={styles.manualForm}>
          <Text style={styles.fieldLabel}>Title</Text>
          <TextInput style={styles.textInput} value={title} onChangeText={v => { setTitle(v); setError(''); }} placeholder="Book title" placeholderTextColor={colors.textMuted} />
          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Author</Text>
          <TextInput style={styles.textInput} value={author} onChangeText={setAuthor} placeholder="Author name" placeholderTextColor={colors.textMuted} />
          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Pages</Text>
          <TextInput style={styles.textInput} value={pageCount} onChangeText={setPageCount} placeholder="Total pages" placeholderTextColor={colors.textMuted} keyboardType="numeric" />
          <Pressable style={[styles.primaryButton, { marginTop: 16 }]} onPress={handleManualSave}>
            <Text style={styles.primaryButtonText}>Add to Library</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  content: { paddingBottom: 60, ...(Platform.OS === 'web' ? { maxWidth: layout.readingMeasure + 2 * layout.screenPadding, width: '100%', alignSelf: 'center' as const } : {}) },
  backButton: { paddingHorizontal: layout.screenPadding, paddingTop: 12, paddingBottom: 8 },
  backText: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  headerSection: { paddingHorizontal: layout.screenPadding, paddingBottom: 12 },
  screenTitle: { ...type.screenTitle, color: colors.ink },
  screenSubtitle: { ...type.screenSubtitle, color: colors.textSecondary, marginTop: 2, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
  errorBanner: { backgroundColor: 'rgba(139,37,0,0.08)', paddingVertical: 10, paddingHorizontal: layout.screenPadding, marginTop: 8 },
  errorText: { fontFamily: fonts.ui, fontSize: 13, color: colors.rubric },
  captureStep: { paddingHorizontal: layout.screenPadding, paddingTop: 24 },
  cameraPlaceholder: { height: 220, backgroundColor: colors.parchmentDark, borderWidth: 1, borderColor: colors.rule, borderRadius: 4, borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 20 },
  cameraIcon: { fontFamily: fonts.display, fontSize: 36, color: colors.textMuted },
  cameraLabel: { fontFamily: fonts.reading, fontSize: 15, color: colors.textSecondary },
  cameraHint: { fontFamily: fonts.ui, fontSize: 12, color: colors.textMuted, textAlign: 'center', paddingHorizontal: 40 },
  captureActions: { gap: 10, marginBottom: 20 },
  primaryButton: { backgroundColor: colors.ink, paddingVertical: 14, borderRadius: 3, alignItems: 'center' },
  primaryButtonText: { fontFamily: fonts.body, fontSize: 14, color: colors.parchment },
  secondaryButton: { borderWidth: 1, borderColor: colors.rule, paddingVertical: 14, borderRadius: 3, alignItems: 'center' },
  secondaryButtonText: { fontFamily: fonts.body, fontSize: 14, color: colors.ink },
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 20 },
  dividerLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: colors.rule },
  dividerText: { fontFamily: fonts.ui, fontSize: 12, color: colors.textMuted },
  manualForm: { paddingBottom: 20 },
  fieldLabel: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.textSecondary, letterSpacing: 0.5, textTransform: 'uppercase', marginBottom: 6, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  textInput: { borderWidth: 1, borderColor: colors.rule, borderRadius: 3, paddingVertical: 10, paddingHorizontal: 12, fontFamily: fonts.reading, fontSize: 15, color: colors.textBody, backgroundColor: colors.parchment },
});
