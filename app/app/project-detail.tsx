import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, Pressable, TextInput, StyleSheet,
  ActivityIndicator, Platform, KeyboardAvoidingView,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { colors, fonts, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';
import { getProject, addProjectNote, Project, ProjectNote } from '../lib/projects-api';
import DoubleRule from '../components/DoubleRule';

export default function ProjectDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [notes, setNotes] = useState<ProjectNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [noteText, setNoteText] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    setFeedbackContext({ screen: 'project-detail', extra: { project_id: id } });
    logEvent('project_detail_open', { project_id: id });
  }, [id]);

  const loadProject = useCallback(() => {
    if (!id) return;
    setLoading(true);
    setError('');
    getProject(id)
      .then(({ project: p, notes: n }) => {
        setProject(p);
        setNotes(n);
      })
      .catch(() => setError('Failed to load project'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { loadProject(); }, [loadProject]);

  const handleAddNote = useCallback(async () => {
    if (!id || !noteText.trim()) return;
    setSending(true);
    try {
      const note = await addProjectNote(id, noteText.trim());
      logEvent('project_note_add', { project_id: id, note_id: note.id });
      setNotes((prev) => [note, ...prev]);
      setNoteText('');
    } catch {
      setError('Failed to add note');
    } finally {
      setSending(false);
    }
  }, [id, noteText]);

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const navigateToSource = useCallback((source: ProjectNote['source']) => {
    if (!source) return;
    logEvent('project_note_source_tap', { source_type: source.type, source_id: source.id });
    if (source.type === 'article') {
      router.push({ pathname: '/reader', params: { id: source.id } } as any);
    }
  }, [router]);

  const sortedNotes = [...notes].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator color={colors.rubric} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.parchment }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
          <Text style={styles.backText}>{'\u2190'} Projects</Text>
        </Pressable>

        <Text style={styles.pageTitle}>{project?.name || 'Project'}</Text>
        {project?.description ? (
          <Text style={styles.pageSub}>{project.description}</Text>
        ) : null}
        <View style={styles.doubleRuleWrap}>
          <DoubleRule />
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <Text style={styles.sectionLabel}>{'\u2726'} NOTES</Text>

        {sortedNotes.length === 0 && (
          <Text style={styles.emptyText}>No notes yet. Add one below.</Text>
        )}

        {sortedNotes.map((note) => (
          <View key={note.id} style={styles.noteCard}>
            <Text style={styles.noteText}>{note.text}</Text>
            <View style={styles.noteMeta}>
              <Text style={styles.noteTime}>{formatTimestamp(note.created_at)}</Text>
              {note.audio_file && (
                <Text style={styles.audioTag}>{'\u266A'} audio</Text>
              )}
            </View>
            {note.source && (
              <Pressable onPress={() => navigateToSource(note.source)} style={styles.sourceLink}>
                <Text style={styles.sourceText} numberOfLines={1}>
                  {'\u2192'} {note.source.title}
                </Text>
              </Pressable>
            )}
          </View>
        ))}

        <View style={{ height: 80 }} />
      </ScrollView>

      <View style={styles.inputBar}>
        <TextInput
          style={styles.noteInput}
          placeholder="Add a note..."
          placeholderTextColor={colors.textMuted}
          value={noteText}
          onChangeText={setNoteText}
          multiline
          maxLength={4000}
        />
        <Pressable
          style={[styles.sendBtn, (!noteText.trim() || sending) && styles.sendBtnDisabled]}
          onPress={handleAddNote}
          disabled={!noteText.trim() || sending}
        >
          <Text style={[styles.sendLabel, (!noteText.trim() || sending) && styles.sendLabelDisabled]}>
            {sending ? '...' : 'Add'}
          </Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.parchment },
  content: {
    maxWidth: layout.contentMaxWidth,
    width: '100%',
    alignSelf: 'center',
    paddingHorizontal: layout.screenPadding,
    paddingTop: 16,
  },
  backBtn: { marginBottom: 16 },
  backText: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { cursor: 'pointer' as any } : {}),
  },
  pageTitle: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 24,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  pageSub: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textMuted,
    marginTop: 4,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  doubleRuleWrap: {
    marginHorizontal: -layout.screenPadding,
    marginTop: 8,
    marginBottom: 28,
  },
  sectionLabel: {
    fontFamily: fonts.bodyMedium,
    fontSize: 11,
    letterSpacing: 1.6,
    color: colors.rubric,
    marginBottom: 16,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  emptyText: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textMuted,
    paddingVertical: 20,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  errorText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.rubric,
    marginBottom: 12,
  },
  noteCard: {
    borderLeftWidth: 2,
    borderLeftColor: colors.rule,
    paddingLeft: 14,
    paddingVertical: 10,
    marginBottom: 16,
  },
  noteText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    lineHeight: 22,
    color: colors.textBody,
  },
  noteMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 6,
  },
  noteTime: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  audioTag: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
  },
  sourceLink: {
    marginTop: 6,
    minHeight: 28,
    justifyContent: 'center',
  },
  sourceText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { cursor: 'pointer' as any } : {}),
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: layout.screenPadding,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.rule,
    backgroundColor: colors.parchment,
    maxWidth: layout.contentMaxWidth,
    width: '100%',
    alignSelf: 'center',
  },
  noteInput: {
    flex: 1,
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.textBody,
    borderWidth: 1,
    borderColor: colors.rule,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minHeight: 40,
    maxHeight: 100,
    marginRight: 10,
    textAlignVertical: 'top',
  },
  sendBtn: {
    backgroundColor: colors.rubric,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    minHeight: 40,
    justifyContent: 'center',
  },
  sendBtnDisabled: { backgroundColor: colors.rule },
  sendLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.parchment,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  sendLabelDisabled: { color: colors.textMuted },
});
