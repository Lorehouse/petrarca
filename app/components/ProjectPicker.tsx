import { useState, useEffect, useCallback } from 'react';
import {
  View, Text, Pressable, TextInput, Modal, StyleSheet,
  ActivityIndicator, Platform, FlatList,
} from 'react-native';
import { colors, fonts, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { listProjects, createProject, Project } from '../lib/projects-api';

interface ProjectPickerProps {
  visible: boolean;
  onSelect: (project: Project) => void;
  onClose: () => void;
}

export default function ProjectPicker({ visible, onSelect, onClose }: ProjectPickerProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    setCreating(false);
    setNewName('');
    setError('');
    listProjects()
      .then((p) => setProjects(p.filter((proj) => proj.status === 'active')))
      .catch(() => setError('Failed to load projects'))
      .finally(() => setLoading(false));
  }, [visible]);

  const handleCreate = useCallback(async () => {
    const name = newName.trim();
    if (!name) return;
    setError('');
    try {
      const project = await createProject(name);
      logEvent('project_create', { project_id: project.id, name });
      setCreating(false);
      setNewName('');
      onSelect(project);
    } catch {
      setError('Failed to create project');
    }
  }, [newName, onSelect]);

  const handleSelect = useCallback((project: Project) => {
    logEvent('project_picker_select', { project_id: project.id });
    onSelect(project);
  }, [onSelect]);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
          <View style={styles.handleWrap}>
            <View style={styles.handle} />
          </View>

          <Text style={styles.header}>
            <Text style={styles.ornament}>{'\u2726'} </Text>
            ADD TO PROJECT
          </Text>

          {loading ? (
            <ActivityIndicator color={colors.rubric} style={{ paddingVertical: 24 }} />
          ) : (
            <FlatList
              data={projects}
              keyExtractor={(p) => p.id}
              style={styles.list}
              renderItem={({ item }) => (
                <Pressable style={styles.row} onPress={() => handleSelect(item)}>
                  <Text style={styles.rowName}>{item.name}</Text>
                  {item.note_count != null && (
                    <Text style={styles.rowCount}>
                      {item.note_count} note{item.note_count !== 1 ? 's' : ''}
                    </Text>
                  )}
                </Pressable>
              )}
              ListEmptyComponent={
                <Text style={styles.emptyText}>No projects yet</Text>
              }
            />
          )}

          {error ? <Text style={styles.errorText}>{error}</Text> : null}

          {creating ? (
            <View style={styles.createRow}>
              <TextInput
                style={styles.createInput}
                placeholder="Project name"
                placeholderTextColor={colors.textMuted}
                value={newName}
                onChangeText={setNewName}
                onSubmitEditing={handleCreate}
                autoFocus
                returnKeyType="done"
              />
            </View>
          ) : (
            <Pressable style={styles.createBtn} onPress={() => { setCreating(true); logEvent('project_picker_new'); }}>
              <Text style={styles.createBtnText}>+ New Project</Text>
            </Pressable>
          )}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.3)',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  sheet: {
    backgroundColor: colors.parchment,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingHorizontal: 20,
    paddingBottom: Platform.OS === 'ios' ? 34 : 20,
    width: '100%',
    maxWidth: 600,
    maxHeight: '60%',
  },
  handleWrap: {
    alignItems: 'center',
    paddingTop: 10,
    paddingBottom: 12,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.rule,
  },
  header: {
    fontFamily: fonts.bodyMedium,
    fontSize: 11,
    letterSpacing: 1.6,
    color: colors.ink,
    marginBottom: 16,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  ornament: {
    color: colors.rubric,
  },
  list: {
    maxHeight: 240,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    minHeight: layout.touchTarget,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
  },
  rowName: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
    flex: 1,
  },
  rowCount: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textMuted,
    marginLeft: 12,
  },
  emptyText: {
    fontFamily: fonts.readingItalic,
    fontSize: 13,
    color: colors.textMuted,
    paddingVertical: 16,
    textAlign: 'center',
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  errorText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.rubric,
    marginTop: 8,
  },
  createBtn: {
    paddingVertical: 14,
    minHeight: layout.touchTarget,
  },
  createBtnText: {
    fontFamily: fonts.uiMedium,
    fontSize: 13,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const, cursor: 'pointer' as any } : {}),
  },
  createRow: {
    paddingVertical: 8,
  },
  createInput: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.ink,
    borderWidth: 1,
    borderColor: colors.rule,
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    minHeight: layout.touchTarget,
  },
});
