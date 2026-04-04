import { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, FlatList, Platform, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout, spacing } from '../design/tokens';
import { logEvent } from '../data/logger';
import { setFeedbackContext } from '../lib/feedback-context';
import { RESEARCH_BASE } from '../lib/chat-api';
import { triggerMicrolearning } from '../lib/book-api';
import DoubleRule from '../components/DoubleRule';

// --- Types ---

interface TimelineNode {
  id: string;
  title: string;
  description: string;
  curriculum: string;
  level: number;
  time_span: [number, number] | null;
  entities: { persons: string[]; places: string[]; events: string[]; time_span?: [number, number] | null };
  knowledge: string;
  interest: string;
}

interface EntityIndex {
  nodes: TimelineNode[];
  persons_index: Record<string, string[]>;
  places_index: Record<string, string[]>;
  events_index: Record<string, string[]>;
  place_hierarchy: Record<string, { parent: string | null; type: string }>;
  curricula: { id: string; short_name: string; title: string }[];
}

type ViewMode = 'entity' | 'cross';
type EntityType = 'place' | 'person';

// --- Domain colors ---

const DOMAIN_COLORS: Record<string, string> = {
  sicily: '#8b4513',
  ancient: '#1e5799',
  roman: '#6b3a8d',
  byzantine: '#2a7a4a',
  islamic: '#b07a1e',
  classical: '#6a5a3a',
  ap_world: '#4a6a8a',
  ap_european: '#8a4a6a',
};

function getDomainColor(domainId: string): string {
  for (const [key, color] of Object.entries(DOMAIN_COLORS)) {
    if (domainId.includes(key)) return color;
  }
  return colors.textSecondary;
}

function getDomainShortName(domainId: string): string {
  if (domainId.includes('sicily')) return 'Sicily';
  if (domainId.includes('ancient_greece') || domainId.includes('ancient_classical')) return 'Greece';
  if (domainId.includes('roman')) return 'Rome';
  if (domainId.includes('byzantine')) return 'Byzantine';
  if (domainId.includes('islamic')) return 'Islamic';
  if (domainId.includes('classical_reception')) return 'Reception';
  if (domainId.includes('ap_world')) return 'AP World';
  if (domainId.includes('ap_european')) return 'AP Euro';
  return domainId.split('_')[0];
}

// --- Helpers ---

function formatYear(year: number): { num: string; era: string } {
  if (year < 0) return { num: String(Math.abs(year)), era: 'BC' };
  return { num: String(year), era: 'AD' };
}

function getCentury(year: number): number {
  if (year < 0) return Math.floor(year / 100) * 100;
  return Math.floor((year - 1) / 100) * 100;
}

function centuryLabel(century: number): string {
  if (century <= -100) {
    const c = Math.abs(century) / 100;
    return `${c}${ordinal(c)} Century BC`;
  }
  if (century < 0) return '1st Century BC';
  const c = century / 100 + 1;
  return `${c}${ordinal(c)} Century AD`;
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

const KNOWLEDGE_COLORS: Record<string, { bg: string; border: string }> = {
  anchored: { bg: colors.ink, border: colors.ink },
  engaged: { bg: colors.rubric, border: colors.rubric },
  mentioned: { bg: colors.rule, border: colors.ink },
  unknown: { bg: 'transparent', border: colors.textMuted },
};

// --- Component ---

export default function TimelineScreen() {
  const router = useRouter();
  const [data, setData] = useState<EntityIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<ViewMode>('entity');
  const [entityType, setEntityType] = useState<EntityType>('place');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [expandedCenturies, setExpandedCenturies] = useState<Set<number>>(new Set());
  const [selectedNode, setSelectedNode] = useState<TimelineNode | null>(null);

  useEffect(() => {
    setFeedbackContext({ screen: 'timeline' });
    logEvent('timeline_open');
    fetch(`${RESEARCH_BASE}/curriculum/entity-index`)
      .then(r => r.json())
      .then((d: EntityIndex) => {
        setData(d);
        // Auto-select a well-connected place (not too broad like "Mediterranean")
        const places = Object.entries(d.places_index)
          .map(([name, ids]) => ({ name, count: ids.length }))
          .filter(p => p.count >= 5 && p.count <= 80)
          .sort((a, b) => b.count - a.count);
        if (places.length > 0) setSelectedEntity(places[0].name);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // Available entities sorted by node count
  const entityList = useMemo(() => {
    if (!data) return [];
    const index = entityType === 'place' ? data.places_index : data.persons_index;
    return Object.entries(index)
      .map(([name, nodeIds]) => ({ name, count: nodeIds.length }))
      .filter(e => e.count >= 2) // skip single-mention entities
      .sort((a, b) => b.count - a.count);
  }, [data, entityType]);

  // Filtered and grouped nodes
  const sections = useMemo(() => {
    if (!data) return [];
    let filtered: TimelineNode[];
    if (mode === 'entity' && selectedEntity) {
      const index = entityType === 'place' ? data.places_index : data.persons_index;
      const nodeIds = new Set(index[selectedEntity] || []);
      filtered = data.nodes.filter(n => nodeIds.has(n.id) && n.time_span);
    } else {
      filtered = data.nodes.filter(n => n.time_span);
    }
    // Sort by start date
    filtered.sort((a, b) => (a.time_span![0]) - (b.time_span![0]));
    // Group by century
    const groups = new Map<number, TimelineNode[]>();
    for (const node of filtered) {
      const c = getCentury(node.time_span![0]);
      if (!groups.has(c)) groups.set(c, []);
      groups.get(c)!.push(node);
    }
    return Array.from(groups.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([century, nodes]) => ({ century, label: centuryLabel(century), nodes }));
  }, [data, mode, entityType, selectedEntity]);

  const toggleCentury = useCallback((century: number) => {
    setExpandedCenturies(prev => {
      const next = new Set(prev);
      if (next.has(century)) next.delete(century);
      else next.add(century);
      return next;
    });
    logEvent('timeline_toggle_century', { century });
  }, []);

  // Auto-expand all centuries when entity changes
  useEffect(() => {
    if (sections.length > 0 && sections.length <= 8) {
      setExpandedCenturies(new Set(sections.map(s => s.century)));
    } else {
      setExpandedCenturies(new Set());
    }
  }, [selectedEntity, mode, sections.length]);

  if (loading) {
    return (
      <View style={styles.container}>
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="small" color={colors.rubric} />
          <Text style={styles.loadingText}>Building timeline index…</Text>
        </View>
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Text style={styles.backText}>← Back</Text>
          </Pressable>
          <Text style={[type.screenTitle, { color: colors.ink }]}>Timeline</Text>
        </View>
        <DoubleRule />
        <Text style={styles.errorText}>{error || 'No data available'}</Text>
      </View>
    );
  }

  const totalNodes = sections.reduce((sum, s) => sum + s.nodes.length, 0);
  const knownCount = sections.reduce(
    (sum, s) => sum + s.nodes.filter(n => n.knowledge !== 'unknown').length, 0,
  );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Text style={styles.backText}>← Back</Text>
          </Pressable>
          <Text style={[type.screenTitle, { color: colors.ink }]}>
            {mode === 'entity' && selectedEntity ? selectedEntity : 'Timeline'}
          </Text>
          <Text style={[type.screenSubtitle, { color: colors.textMuted }]}>
            {mode === 'entity'
              ? `${totalNodes} events · ${knownCount} known`
              : `Across ${data.curricula.length} curricula`}
          </Text>
        </View>
        <DoubleRule />

        {/* Mode toggle */}
        <View style={styles.modeRow}>
          <Pressable
            style={[styles.modeTab, mode === 'entity' && styles.modeTabActive]}
            onPress={() => setMode('entity')}
          >
            <Text style={[styles.modeText, mode === 'entity' && styles.modeTextActive]}>
              By Entity
            </Text>
          </Pressable>
          <Pressable
            style={[styles.modeTab, mode === 'cross' && styles.modeTabActive]}
            onPress={() => setMode('cross')}
          >
            <Text style={[styles.modeText, mode === 'cross' && styles.modeTextActive]}>
              All Domains
            </Text>
          </Pressable>
        </View>

        {/* Entity type toggle + entity pills (entity mode) */}
        {mode === 'entity' && (
          <>
            <View style={styles.entityTypeRow}>
              <Pressable
                style={[styles.typeChip, entityType === 'place' && styles.typeChipActive]}
                onPress={() => { setEntityType('place'); setSelectedEntity(null); }}
              >
                <Text style={[styles.typeChipText, entityType === 'place' && styles.typeChipTextActive]}>
                  Places
                </Text>
              </Pressable>
              <Pressable
                style={[styles.typeChip, entityType === 'person' && styles.typeChipActive]}
                onPress={() => { setEntityType('person'); setSelectedEntity(null); }}
              >
                <Text style={[styles.typeChipText, entityType === 'person' && styles.typeChipTextActive]}>
                  Persons
                </Text>
              </Pressable>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.entityPills}
            >
              {entityList.map(e => (
                <Pressable
                  key={e.name}
                  style={[styles.pill, selectedEntity === e.name && styles.pillActive]}
                  onPress={() => {
                    setSelectedEntity(e.name);
                    setSelectedNode(null);
                    logEvent('timeline_select_entity', { entity: e.name, type: entityType });
                  }}
                >
                  <Text style={[styles.pillText, selectedEntity === e.name && styles.pillTextActive]}>
                    {e.name}
                  </Text>
                  <Text style={[styles.pillCount, selectedEntity === e.name && styles.pillCountActive]}>
                    {e.count}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
          </>
        )}

        {/* Timeline sections */}
        {sections.map(section => {
          const isExpanded = expandedCenturies.has(section.century);
          const sectionKnown = section.nodes.filter(n => n.knowledge !== 'unknown').length;
          return (
            <View key={section.century}>
              {/* Era band header */}
              <Pressable
                style={styles.eraBand}
                onPress={() => toggleCentury(section.century)}
              >
                <View style={styles.eraBandLeft}>
                  <Text style={styles.sectionHead}>
                    ✦ {section.label}
                  </Text>
                  <Text style={styles.eraCount}>
                    {section.nodes.length} events · {sectionKnown} known
                  </Text>
                </View>
                <Text style={styles.expandIcon}>{isExpanded ? '−' : '+'}</Text>
              </Pressable>

              {/* Knowledge density bar */}
              <View style={styles.densityBar}>
                {section.nodes.map(n => {
                  const kc = KNOWLEDGE_COLORS[n.knowledge] || KNOWLEDGE_COLORS.unknown;
                  return (
                    <View
                      key={n.id}
                      style={[styles.densitySegment, {
                        backgroundColor: kc.bg,
                        borderColor: n.knowledge === 'unknown' ? kc.border : 'transparent',
                        borderWidth: n.knowledge === 'unknown' ? 0.5 : 0,
                      }]}
                    />
                  );
                })}
              </View>

              {/* Expanded events */}
              {isExpanded && section.nodes.map(node => (
                <TimelineEvent
                  key={node.id}
                  node={node}
                  showDomain={mode === 'cross'}
                  isSelected={selectedNode?.id === node.id}
                  onPress={() => {
                    setSelectedNode(selectedNode?.id === node.id ? null : node);
                    logEvent('timeline_tap_event', { node_id: node.id });
                  }}
                  onGenerateCard={(query) => {
                    triggerMicrolearning({
                      query,
                      sourceNodeId: node.id,
                      sourceDomain: node.curriculum,
                    }).then(resp => {
                      logEvent('timeline_generate_card', {
                        node_id: node.id, card_id: resp.id, query,
                      });
                    }).catch(e => console.warn('[timeline] microlearning failed:', e));
                  }}
                  onViewInMap={() => {
                    router.push(`/knowledge-map?domain=${node.curriculum}&node=${node.id}` as any);
                  }}
                  onSelectEntity={(name) => {
                    setSelectedEntity(name);
                    setSelectedNode(null);
                    logEvent('timeline_entity_link_tap', { entity: name });
                  }}
                />
              ))}
            </View>
          );
        })}

        {sections.length === 0 && !loading && (
          <View style={styles.emptyWrap}>
            <Text style={styles.emptyText}>
              {mode === 'entity' && !selectedEntity
                ? 'Select an entity above to see its timeline'
                : 'No dated events found'}
            </Text>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
}

// --- Event Row ---

function TimelineEvent({ node, showDomain, isSelected, onPress, onGenerateCard, onViewInMap, onSelectEntity }: {
  node: TimelineNode;
  showDomain: boolean;
  isSelected: boolean;
  onPress: () => void;
  onGenerateCard: (query: string) => void;
  onViewInMap: () => void;
  onSelectEntity: (name: string) => void;
}) {
  const [cardRequested, setCardRequested] = useState(false);
  if (!node.time_span) return null;
  const { num, era } = formatYear(node.time_span[0]);
  const kc = KNOWLEDGE_COLORS[node.knowledge] || KNOWLEDGE_COLORS.unknown;
  const isUnknown = node.knowledge === 'unknown';
  const domainColor = getDomainColor(node.curriculum);

  return (
    <View>
      <Pressable
        style={[styles.eventRow, isSelected && styles.eventRowSelected]}
        onPress={onPress}
      >
        {/* Date margin */}
        <View style={styles.dateMargin}>
          <Text style={styles.dateNum}>{num}</Text>
          <Text style={styles.dateEra}>{era}</Text>
        </View>

        {/* Knowledge dot */}
        <View style={[
          styles.knowledgeDot,
          { backgroundColor: kc.bg, borderColor: kc.border, borderWidth: 1.5 },
        ]} />

        {/* Content */}
        <View style={[styles.eventContent, isUnknown && { opacity: 0.55 }]}>
          <Text style={styles.eventTitle}>{node.title}</Text>
          {showDomain && (
            <Text style={[styles.eventDomain, { color: domainColor }]}>
              {getDomainShortName(node.curriculum)}
            </Text>
          )}
          {isSelected && (
            <Text style={styles.eventDesc}>
              {node.description}
            </Text>
          )}
          {/* Tappable entity links */}
          {isSelected && (
            <View style={styles.entityTags}>
              {[...node.entities.persons, ...node.entities.places].slice(0, 5).map(e => (
                <Pressable key={e} onPress={() => onSelectEntity(e)} hitSlop={4}>
                  <Text style={styles.entityTag}>{e}</Text>
                </Pressable>
              ))}
            </View>
          )}
          {/* Cross-domain connections when selected */}
          {isSelected && node.entities.events.length > 0 && (
            <View style={styles.connectionBanner}>
              <Text style={styles.connectionLabel}>Related events</Text>
              {node.entities.events.map(e => (
                <Text key={e} style={styles.connectionText}>{e}</Text>
              ))}
            </View>
          )}
          {/* Action buttons */}
          {isSelected && (
            <View style={styles.actionRow}>
              <Pressable
                style={[styles.actionBtn, styles.actionBtnPrimary, cardRequested && styles.actionBtnDisabled]}
                onPress={() => {
                  if (cardRequested) return;
                  setCardRequested(true);
                  onGenerateCard(`Tell me about: ${node.title}`);
                }}
                disabled={cardRequested}
              >
                <Text style={[styles.actionBtnText, styles.actionBtnTextPrimary]}>
                  {cardRequested ? '✦ Card queued' : '✦ Generate card'}
                </Text>
              </Pressable>
              <Pressable style={styles.actionBtn} onPress={onViewInMap}>
                <Text style={styles.actionBtnText}>View in map</Text>
              </Pressable>
            </View>
          )}
        </View>
      </Pressable>
      <View style={styles.eventDivider} />
    </View>
  );
}

// --- Styles ---

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  scrollContent: {
    paddingBottom: 32,
  },
  loadingWrap: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  loadingText: {
    ...type.screenSubtitle,
    color: colors.textMuted,
  },
  header: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
  },
  backText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.rubric,
    marginBottom: spacing.sm,
  },
  errorText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    padding: 32,
  },

  // Mode toggle
  modeRow: {
    flexDirection: 'row',
    marginHorizontal: layout.screenPadding,
    marginTop: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.rule,
  },
  modeTab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
  },
  modeTabActive: {
    borderBottomWidth: 2,
    borderBottomColor: colors.rubric,
  },
  modeText: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.textMuted,
  },
  modeTextActive: {
    color: colors.rubric,
  },

  // Entity type toggle
  entityTypeRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: layout.screenPadding,
    marginTop: spacing.md,
  },
  typeChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  typeChipActive: {
    backgroundColor: colors.ink,
    borderColor: colors.ink,
  },
  typeChipText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textSecondary,
  },
  typeChipTextActive: {
    color: colors.parchment,
  },

  // Entity pills
  entityPills: {
    paddingHorizontal: layout.screenPadding,
    paddingVertical: spacing.sm,
    gap: 6,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  pillActive: {
    backgroundColor: colors.ink,
    borderColor: colors.ink,
  },
  pillText: {
    fontFamily: fonts.body,
    fontSize: 12,
    color: colors.textBody,
  },
  pillTextActive: {
    color: colors.parchment,
  },
  pillCount: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
  },
  pillCountActive: {
    color: 'rgba(247,244,236,0.5)',
  },

  // Era bands
  eraBand: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: layout.screenPadding,
    paddingVertical: 10,
    marginTop: spacing.sm,
    backgroundColor: 'rgba(139,37,0,0.04)',
    borderLeftWidth: 2,
    borderLeftColor: colors.rubric,
  },
  eraBandLeft: {},
  sectionHead: {
    ...type.sectionHead,
    color: colors.rubric,
  },
  eraCount: {
    fontFamily: fonts.ui,
    fontSize: 9,
    color: colors.textMuted,
    marginTop: 2,
  },
  expandIcon: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 18,
    color: colors.rubric,
    ...(Platform.OS === 'web' ? { fontWeight: '600' } : {}),
  },

  // Knowledge density bar
  densityBar: {
    flexDirection: 'row',
    gap: 1,
    marginHorizontal: layout.screenPadding,
    height: 6,
    marginBottom: 4,
  },
  densitySegment: {
    flex: 1,
    borderRadius: 1,
  },

  // Event rows
  eventRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 8,
    paddingRight: layout.screenPadding,
    paddingLeft: 4,
    minHeight: 44,
  },
  eventRowSelected: {
    backgroundColor: 'rgba(139,37,0,0.03)',
  },
  dateMargin: {
    width: 52,
    alignItems: 'flex-end',
    paddingRight: 8,
    paddingTop: 1,
  },
  dateNum: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 14,
    color: colors.ink,
    lineHeight: 16,
    ...(Platform.OS === 'web' ? { fontWeight: '600' } : {}),
  },
  dateEra: {
    fontFamily: fonts.uiMedium,
    fontSize: 7,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  knowledgeDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginTop: 4,
    marginRight: 8,
  },
  eventContent: {
    flex: 1,
  },
  eventTitle: {
    fontFamily: fonts.bodyMedium,
    fontSize: 14,
    color: colors.textPrimary,
    lineHeight: 19,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  eventDomain: {
    fontFamily: fonts.uiMedium,
    fontSize: 9,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 1,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  eventDesc: {
    fontFamily: fonts.reading,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 4,
  },
  entityTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 6,
  },
  entityTag: {
    ...type.topicTag,
    color: colors.rubric,
  },
  connectionBanner: {
    marginTop: 6,
    paddingLeft: 8,
    borderLeftWidth: 2,
    borderLeftColor: colors.rubric,
    backgroundColor: 'rgba(139,37,0,0.04)',
    paddingVertical: 4,
  },
  connectionLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 8,
    color: colors.rubric,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    ...(Platform.OS === 'web' ? { fontWeight: '500' } : {}),
  },
  connectionText: {
    fontFamily: fonts.reading,
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 1,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 10,
  },
  actionBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 2,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  actionBtnPrimary: {
    backgroundColor: colors.rubric,
    borderColor: colors.rubric,
  },
  actionBtnDisabled: {
    backgroundColor: colors.parchmentDark,
    borderColor: colors.rule,
  },
  actionBtnText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textSecondary,
  },
  actionBtnTextPrimary: {
    color: colors.parchment,
  },
  eventDivider: {
    height: 1,
    backgroundColor: colors.rule,
    marginLeft: 70,
    marginRight: layout.screenPadding,
    opacity: 0.5,
  },

  // Empty state
  emptyWrap: {
    padding: 32,
    alignItems: 'center',
  },
  emptyText: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textMuted,
    textAlign: 'center',
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' } : {}),
  },
});
