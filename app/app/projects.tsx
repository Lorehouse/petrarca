import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';
import { listProjects, Project } from '../lib/projects-api';
import DoubleRule from '../components/DoubleRule';

export default function ProjectsScreen() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setFeedbackContext({ screen: 'projects' });
    logEvent('projects_open');
  }, []);

  const loadProjects = useCallback(() => {
    setLoading(true);
    setError('');
    listProjects()
      .then(setProjects)
      .catch(() => setError('Failed to load projects'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  const active = projects.filter((p) => p.status === 'active');
  const archived = projects.filter((p) => p.status === 'archived');

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    } catch {
      return '';
    }
  };

  const navigateToProject = useCallback((project: Project) => {
    logEvent('projects_tap', { project_id: project.id });
    router.push({ pathname: '/project-detail', params: { id: project.id } } as any);
  }, [router]);

  const renderRow = (project: Project) => (
    <Pressable
      key={project.id}
      style={styles.row}
      onPress={() => navigateToProject(project)}
    >
      <View style={styles.rowLeft}>
        <Text style={styles.rowName}>{project.name}</Text>
        {project.description ? (
          <Text style={styles.rowDesc} numberOfLines={1}>{project.description}</Text>
        ) : null}
      </View>
      <View style={styles.rowRight}>
        {project.note_count != null && (
          <Text style={styles.rowMeta}>
            {project.note_count} note{project.note_count !== 1 ? 's' : ''}
          </Text>
        )}
        {project.last_activity && (
          <Text style={styles.rowMeta}>{formatDate(project.last_activity)}</Text>
        )}
      </View>
    </Pressable>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Pressable onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
        <Text style={styles.backText}>{'\u2190'} Feed</Text>
      </Pressable>

      <Text style={styles.pageTitle}>Projects</Text>
      <View style={styles.doubleRuleWrap}>
        <DoubleRule />
      </View>

      {loading ? (
        <ActivityIndicator color={colors.rubric} style={{ paddingVertical: 32 }} />
      ) : error ? (
        <View style={styles.errorWrap}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={loadProjects} style={styles.retryBtn}>
            <Text style={styles.retryText}>Retry</Text>
          </Pressable>
        </View>
      ) : (
        <>
          {active.length > 0 && (
            <>
              <Text style={styles.sectionLabel}>{'\u2726'} ACTIVE</Text>
              {active.map(renderRow)}
            </>
          )}

          {archived.length > 0 && (
            <>
              <View style={styles.thinRule} />
              <Text style={styles.sectionLabel}>{'\u2726'} ARCHIVED</Text>
              {archived.map(renderRow)}
            </>
          )}

          {projects.length === 0 && (
            <Text style={styles.emptyText}>
              No projects yet. Add notes to a project from the feedback button.
            </Text>
          )}
        </>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
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
    marginBottom: 8,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  doubleRuleWrap: {
    marginHorizontal: -layout.screenPadding,
    marginBottom: 28,
  },
  sectionLabel: {
    fontFamily: fonts.bodyMedium,
    fontSize: 11,
    letterSpacing: 1.6,
    color: colors.rubric,
    marginBottom: 12,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    minHeight: layout.touchTarget,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
    ...(Platform.OS === 'web' ? { cursor: 'pointer' as any } : {}),
  },
  rowLeft: { flex: 1, marginRight: 12 },
  rowName: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
  },
  rowDesc: {
    fontFamily: fonts.reading,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  rowRight: { alignItems: 'flex-end' },
  rowMeta: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
  },
  thinRule: {
    height: 1,
    backgroundColor: colors.rule,
    marginVertical: 24,
  },
  emptyText: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textMuted,
    paddingVertical: 32,
    textAlign: 'center',
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  errorWrap: { alignItems: 'center', paddingVertical: 32 },
  errorText: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.rubric,
    marginBottom: 12,
  },
  retryBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: colors.rubric,
    borderRadius: 6,
  },
  retryText: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
});
