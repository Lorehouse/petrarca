import { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Platform, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout, spacing } from '../design/tokens';
import { logEvent } from '../data/logger';
import { RESEARCH_BASE } from '../lib/chat-api';
import { triggerMicrolearning } from '../lib/book-api';

// --- Types (exported for reuse) ---

export interface TimelineNode {
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

export interface EntityIndex {
  nodes: TimelineNode[];
  persons_index: Record<string, string[]>;
  places_index: Record<string, string[]>;
  events_index: Record<string, string[]>;
  place_hierarchy: Record<string, { parent: string | null; type: string }>;
  curricula: { id: string; short_name: string; title: string }[];
}

type SubTab = 'timeline' | 'persons' | 'places';
type ViewMode = 'entity' | 'cross';
type EntityType = 'place' | 'person';

// --- Domain colors ---

const DOMAIN_COLORS: Record<string, string> = {
  sicily: '#8b4513', ancient: '#1e5799', roman: '#6b3a8d',
  byzantine: '#2a7a4a', islamic: '#b07a1e', classical: '#6a5a3a',
  ap_world: '#4a6a8a', ap_european: '#8a4a6a',
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

// --- Date detection utility (exported for use in AnnotatedText) ---

export interface DetectedDate {
  year: number; // negative for BC
  start: number; // character offset
  end: number;
  text: string; // the matched text
}

/** Parse historical dates from text: "480 BC", "1453 AD", "330 BCE", etc. */
export function detectDates(text: string): DetectedDate[] {
  const pattern = /\b(\d{1,4})\s*(BC|BCE|AD|CE|B\.C\.|A\.D\.)\b/gi;
  const results: DetectedDate[] = [];
  let match;
  while ((match = pattern.exec(text)) !== null) {
    const rawYear = parseInt(match[1], 10);
    const era = match[2].toUpperCase().replace(/\./g, '');
    const year = (era === 'BC' || era === 'BCE') ? -rawYear : rawYear;
    results.push({
      year,
      start: match.index,
      end: match.index + match[0].length,
      text: match[0],
    });
  }
  return results;
}

// --- Props ---

interface KnowledgeExplorerProps {
  /** Pre-select an entity by name (navigated from a review card entity tap) */
  initialEntity?: string;
  /** Focus the timeline on a specific year (navigated from a date tap) */
  initialYear?: number;
  /** Whether to show as 'person' or 'place' type initially */
  initialEntityType?: EntityType;
}

// --- Component ---

export default function KnowledgeExplorer({ initialEntity, initialYear, initialEntityType }: KnowledgeExplorerProps) {
  const router = useRouter();
  const [data, setData] = useState<EntityIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [subTab, setSubTab] = useState<SubTab>('timeline');
  const [mode, setMode] = useState<ViewMode>(initialEntity ? 'entity' : 'entity');
  const [entityType, setEntityType] = useState<EntityType>(initialEntityType || 'place');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(initialEntity || null);
  const [expandedCenturies, setExpandedCenturies] = useState<Set<number>>(new Set());
  const [selectedNode, setSelectedNode] = useState<TimelineNode | null>(null);

  useEffect(() => {
    logEvent('explorer_open', { initial_entity: initialEntity, initial_year: initialYear });
    fetch(`${RESEARCH_BASE}/curriculum/entity-index`)
      .then(r => r.json())
      .then((d: EntityIndex) => {
        setData(d);
        if (!initialEntity) {
          const places = Object.entries(d.places_index)
            .map(([name, ids]) => ({ name, count: ids.length }))
            .filter(p => p.count >= 5 && p.count <= 80)
            .sort((a, b) => b.count - a.count);
          if (places.length > 0) setSelectedEntity(places[0].name);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // When initial entity/year changes (deep link navigation)
  useEffect(() => {
    if (initialEntity && data) {
      setSelectedEntity(initialEntity);
      setSubTab('timeline');
      // Detect if it's a person or place
      if (data.persons_index[initialEntity]) setEntityType('person');
      else setEntityType('place');
    }
  }, [initialEntity, data]);

  useEffect(() => {
    if (initialYear && data) {
      setSubTab('timeline');
      setMode('cross');
      const century = getCentury(initialYear);
      setExpandedCenturies(new Set([century]));
    }
  }, [initialYear, data]);

  // Entity list for current type
  const entityList = useMemo(() => {
    if (!data) return [];
    const index = entityType === 'place' ? data.places_index : data.persons_index;
    return Object.entries(index)
      .map(([name, nodeIds]) => ({ name, count: nodeIds.length }))
      .filter(e => e.count >= 2)
      .sort((a, b) => b.count - a.count);
  }, [data, entityType]);

  // Timeline sections (grouped by century)
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
    filtered.sort((a, b) => (a.time_span![0]) - (b.time_span![0]));
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
  }, []);

  // Auto-expand when entity changes
  useEffect(() => {
    if (sections.length > 0 && sections.length <= 8) {
      setExpandedCenturies(new Set(sections.map(s => s.century)));
    } else {
      setExpandedCenturies(new Set());
    }
  }, [selectedEntity, mode, sections.length]);

  if (loading) {
    return (
      <View style={s.loadingWrap}>
        <ActivityIndicator size="small" color={colors.rubric} />
        <Text style={s.loadingText}>Loading knowledge index…</Text>
      </View>
    );
  }

  if (!data) return <Text style={s.errorText}>Could not load knowledge data</Text>;

  const totalNodes = sections.reduce((sum, sec) => sum + sec.nodes.length, 0);
  const knownCount = sections.reduce(
    (sum, sec) => sum + sec.nodes.filter(n => n.knowledge !== 'unknown').length, 0,
  );

  return (
    <ScrollView contentContainerStyle={s.scrollContent}>
      {/* Sub-tabs */}
      <View style={s.subTabRow}>
        {(['timeline', 'persons', 'places'] as SubTab[]).map(tab => (
          <Pressable
            key={tab}
            style={[s.subTab, subTab === tab && s.subTabActive]}
            onPress={() => setSubTab(tab)}
          >
            <Text style={[s.subTabText, subTab === tab && s.subTabTextActive]}>
              {tab === 'timeline' ? 'Timeline' : tab === 'persons' ? 'Persons' : 'Places'}
            </Text>
            <Text style={[s.subTabCount, subTab === tab && s.subTabCountActive]}>
              {tab === 'timeline' ? totalNodes
                : tab === 'persons' ? Object.keys(data.persons_index).length
                : Object.keys(data.places_index).length}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* ── Timeline sub-tab ── */}
      {subTab === 'timeline' && (
        <>
          {/* Mode toggle */}
          <View style={s.modeRow}>
            <Pressable style={[s.modeTab, mode === 'entity' && s.modeTabActive]} onPress={() => setMode('entity')}>
              <Text style={[s.modeText, mode === 'entity' && s.modeTextActive]}>By Entity</Text>
            </Pressable>
            <Pressable style={[s.modeTab, mode === 'cross' && s.modeTabActive]} onPress={() => setMode('cross')}>
              <Text style={[s.modeText, mode === 'cross' && s.modeTextActive]}>All Domains</Text>
            </Pressable>
          </View>

          {mode === 'entity' && (
            <>
              <View style={s.entityTypeRow}>
                <Pressable style={[s.typeChip, entityType === 'place' && s.typeChipActive]}
                  onPress={() => { setEntityType('place'); setSelectedEntity(null); }}>
                  <Text style={[s.typeChipText, entityType === 'place' && s.typeChipTextActive]}>Places</Text>
                </Pressable>
                <Pressable style={[s.typeChip, entityType === 'person' && s.typeChipActive]}
                  onPress={() => { setEntityType('person'); setSelectedEntity(null); }}>
                  <Text style={[s.typeChipText, entityType === 'person' && s.typeChipTextActive]}>Persons</Text>
                </Pressable>
              </View>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.entityPills}>
                {entityList.map(e => (
                  <Pressable key={e.name} style={[s.pill, selectedEntity === e.name && s.pillActive]}
                    onPress={() => { setSelectedEntity(e.name); setSelectedNode(null); }}>
                    <Text style={[s.pillText, selectedEntity === e.name && s.pillTextActive]}>{e.name}</Text>
                    <Text style={[s.pillCount, selectedEntity === e.name && s.pillCountActive]}>{e.count}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            </>
          )}

          {selectedEntity && mode === 'entity' && (
            <Text style={s.entitySummary}>
              {selectedEntity} · {totalNodes} events · {knownCount} known
            </Text>
          )}

          {sections.map(section => {
            const isExpanded = expandedCenturies.has(section.century);
            const sectionKnown = section.nodes.filter(n => n.knowledge !== 'unknown').length;
            return (
              <View key={section.century}>
                <Pressable style={s.eraBand} onPress={() => toggleCentury(section.century)}>
                  <View>
                    <Text style={s.sectionHead}>✦ {section.label}</Text>
                    <Text style={s.eraCount}>{section.nodes.length} events · {sectionKnown} known</Text>
                  </View>
                  <Text style={s.expandIcon}>{isExpanded ? '−' : '+'}</Text>
                </Pressable>
                <View style={s.densityBar}>
                  {section.nodes.map(n => {
                    const kc = KNOWLEDGE_COLORS[n.knowledge] || KNOWLEDGE_COLORS.unknown;
                    return <View key={n.id} style={[s.densitySegment, {
                      backgroundColor: kc.bg,
                      borderColor: n.knowledge === 'unknown' ? kc.border : 'transparent',
                      borderWidth: n.knowledge === 'unknown' ? 0.5 : 0,
                    }]} />;
                  })}
                </View>
                {isExpanded && section.nodes.map(node => (
                  <TimelineEvent key={node.id} node={node} showDomain={mode === 'cross'}
                    isSelected={selectedNode?.id === node.id}
                    onPress={() => {
                      setSelectedNode(selectedNode?.id === node.id ? null : node);
                      logEvent('explorer_tap_event', { node_id: node.id });
                    }}
                    onGenerateCard={(query) => {
                      triggerMicrolearning({ query, sourceNodeId: node.id, sourceDomain: node.curriculum })
                        .then(r => logEvent('explorer_generate_card', { node_id: node.id, card_id: r.id }))
                        .catch(e => console.warn('[explorer] microlearning failed:', e));
                    }}
                    onViewInMap={() => router.push(`/knowledge-map?domain=${node.curriculum}&node=${node.id}` as any)}
                    onSelectEntity={(name) => { setSelectedEntity(name); setSelectedNode(null); }}
                  />
                ))}
              </View>
            );
          })}

          {sections.length === 0 && (
            <View style={s.emptyWrap}>
              <Text style={s.emptyText}>
                {!selectedEntity ? 'Select an entity above' : 'No dated events found'}
              </Text>
            </View>
          )}
        </>
      )}

      {/* ── Persons sub-tab ── */}
      {subTab === 'persons' && (
        <EntityListView
          entities={data.persons_index}
          nodes={data.nodes}
          entityType="person"
          onSelectEntity={(name) => {
            setSelectedEntity(name);
            setEntityType('person');
            setMode('entity');
            setSubTab('timeline');
          }}
        />
      )}

      {/* ── Places sub-tab ── */}
      {subTab === 'places' && (
        <EntityListView
          entities={data.places_index}
          nodes={data.nodes}
          entityType="place"
          onSelectEntity={(name) => {
            setSelectedEntity(name);
            setEntityType('place');
            setMode('entity');
            setSubTab('timeline');
          }}
        />
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

// --- Entity List View (Persons / Places sub-tab) ---

function EntityListView({ entities, nodes, entityType, onSelectEntity }: {
  entities: Record<string, string[]>;
  nodes: TimelineNode[];
  entityType: string;
  onSelectEntity: (name: string) => void;
}) {
  const nodeMap = useMemo(() => {
    const map = new Map<string, TimelineNode>();
    for (const n of nodes) map.set(n.id, n);
    return map;
  }, [nodes]);

  const sorted = useMemo(() => {
    return Object.entries(entities)
      .map(([name, nodeIds]) => {
        const linkedNodes = nodeIds.map(id => nodeMap.get(id)).filter(Boolean) as TimelineNode[];
        const dates = linkedNodes.filter(n => n.time_span).map(n => n.time_span!);
        const minYear = dates.length > 0 ? Math.min(...dates.map(d => d[0])) : null;
        const maxYear = dates.length > 0 ? Math.max(...dates.map(d => d[1])) : null;
        const knownCount = linkedNodes.filter(n => n.knowledge !== 'unknown').length;
        const domains = [...new Set(linkedNodes.map(n => n.curriculum))];
        return { name, count: nodeIds.length, minYear, maxYear, knownCount, domains };
      })
      .filter(e => e.count >= 2)
      .sort((a, b) => b.count - a.count);
  }, [entities, nodeMap]);

  return (
    <View style={{ paddingHorizontal: layout.screenPadding }}>
      {sorted.map(entity => (
        <Pressable key={entity.name} style={s.entityRow} onPress={() => onSelectEntity(entity.name)}>
          <View style={s.entityRowLeft}>
            <Text style={s.entityName}>{entity.name}</Text>
            <View style={s.entityMeta}>
              {entity.minYear !== null && (
                <Text style={s.entityDates}>
                  {formatYear(entity.minYear).num} {formatYear(entity.minYear).era}
                  {entity.maxYear !== null && entity.maxYear !== entity.minYear
                    ? ` – ${formatYear(entity.maxYear).num} ${formatYear(entity.maxYear).era}` : ''}
                </Text>
              )}
              <Text style={s.entityNodeCount}>
                {entity.count} nodes · {entity.knownCount} known
              </Text>
            </View>
            <View style={s.entityDomainRow}>
              {entity.domains.slice(0, 4).map(d => (
                <View key={d} style={[s.domainDot, { backgroundColor: getDomainColor(d) }]} />
              ))}
            </View>
          </View>
          <Text style={s.entityChevron}>›</Text>
        </Pressable>
      ))}
    </View>
  );
}

// --- Timeline Event Row ---

function TimelineEvent({ node, showDomain, isSelected, onPress, onGenerateCard, onViewInMap, onSelectEntity }: {
  node: TimelineNode; showDomain: boolean; isSelected: boolean;
  onPress: () => void; onGenerateCard: (q: string) => void;
  onViewInMap: () => void; onSelectEntity: (name: string) => void;
}) {
  const [cardRequested, setCardRequested] = useState(false);
  if (!node.time_span) return null;
  const { num, era } = formatYear(node.time_span[0]);
  const kc = KNOWLEDGE_COLORS[node.knowledge] || KNOWLEDGE_COLORS.unknown;
  const isUnknown = node.knowledge === 'unknown';
  const domainColor = getDomainColor(node.curriculum);

  return (
    <View>
      <Pressable style={[s.eventRow, isSelected && s.eventRowSelected]} onPress={onPress}>
        <View style={s.dateMargin}>
          <Text style={s.dateNum}>{num}</Text>
          <Text style={s.dateEra}>{era}</Text>
        </View>
        <View style={[s.knowledgeDot, { backgroundColor: kc.bg, borderColor: kc.border, borderWidth: 1.5 }]} />
        <View style={[s.eventContent, isUnknown && { opacity: 0.55 }]}>
          <Text style={s.eventTitle}>{node.title}</Text>
          {showDomain && <Text style={[s.eventDomain, { color: domainColor }]}>{getDomainShortName(node.curriculum)}</Text>}
          {isSelected && <Text style={s.eventDesc}>{node.description}</Text>}
          {isSelected && (
            <View style={s.entityTags}>
              {[...node.entities.persons, ...node.entities.places].slice(0, 5).map(e => (
                <Pressable key={e} onPress={() => onSelectEntity(e)} hitSlop={4}>
                  <Text style={s.entityTag}>{e}</Text>
                </Pressable>
              ))}
            </View>
          )}
          {isSelected && node.entities.events.length > 0 && (
            <View style={s.connectionBanner}>
              <Text style={s.connectionLabel}>Related events</Text>
              {node.entities.events.map(e => <Text key={e} style={s.connectionText}>{e}</Text>)}
            </View>
          )}
          {isSelected && (
            <View style={s.actionRow}>
              <Pressable style={[s.actionBtn, s.actionBtnPrimary, cardRequested && s.actionBtnDisabled]}
                onPress={() => { if (!cardRequested) { setCardRequested(true); onGenerateCard(`Tell me about: ${node.title}`); } }}
                disabled={cardRequested}>
                <Text style={[s.actionBtnText, s.actionBtnTextPrimary]}>
                  {cardRequested ? '✦ Card queued' : '✦ Generate card'}
                </Text>
              </Pressable>
              <Pressable style={s.actionBtn} onPress={onViewInMap}>
                <Text style={s.actionBtnText}>View in map</Text>
              </Pressable>
            </View>
          )}
        </View>
      </Pressable>
      <View style={s.eventDivider} />
    </View>
  );
}

// --- Styles ---

const s = StyleSheet.create({
  scrollContent: { paddingBottom: 32 },
  loadingWrap: { padding: 40, alignItems: 'center', gap: 8 },
  loadingText: { ...type.screenSubtitle, color: colors.textMuted },
  errorText: { fontFamily: fonts.reading, fontSize: 14, color: colors.textSecondary, textAlign: 'center', padding: 32 },

  // Sub-tabs
  subTabRow: { flexDirection: 'row', marginHorizontal: layout.screenPadding, borderBottomWidth: 1, borderBottomColor: colors.rule },
  subTab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, paddingVertical: 10 },
  subTabActive: { borderBottomWidth: 2, borderBottomColor: colors.rubric },
  subTabText: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted },
  subTabTextActive: { color: colors.rubric },
  subTabCount: { fontFamily: fonts.ui, fontSize: 9, color: colors.textMuted },
  subTabCountActive: { color: colors.rubric },

  // Mode toggle
  modeRow: { flexDirection: 'row', marginHorizontal: layout.screenPadding, marginTop: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.rule },
  modeTab: { flex: 1, paddingVertical: 7, alignItems: 'center' },
  modeTabActive: { borderBottomWidth: 2, borderBottomColor: colors.ink },
  modeText: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted },
  modeTextActive: { color: colors.ink },

  // Entity type chips
  entityTypeRow: { flexDirection: 'row', gap: 8, paddingHorizontal: layout.screenPadding, marginTop: spacing.sm },
  typeChip: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1, borderColor: colors.rule },
  typeChipActive: { backgroundColor: colors.ink, borderColor: colors.ink },
  typeChipText: { fontFamily: fonts.ui, fontSize: 11, color: colors.textSecondary },
  typeChipTextActive: { color: colors.parchment },

  // Entity pills
  entityPills: { paddingHorizontal: layout.screenPadding, paddingVertical: spacing.sm, gap: 6 },
  pill: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12, borderWidth: 1, borderColor: colors.rule },
  pillActive: { backgroundColor: colors.ink, borderColor: colors.ink },
  pillText: { fontFamily: fonts.body, fontSize: 12, color: colors.textBody },
  pillTextActive: { color: colors.parchment },
  pillCount: { fontFamily: fonts.ui, fontSize: 9, color: colors.textMuted },
  pillCountActive: { color: 'rgba(247,244,236,0.5)' },

  entitySummary: { fontFamily: fonts.readingItalic, fontSize: 12, color: colors.textMuted, paddingHorizontal: layout.screenPadding, marginBottom: 4, ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },

  // Era bands
  eraBand: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: layout.screenPadding, paddingVertical: 10, marginTop: spacing.sm, backgroundColor: 'rgba(139,37,0,0.04)', borderLeftWidth: 2, borderLeftColor: colors.rubric },
  sectionHead: { ...type.sectionHead, color: colors.rubric },
  eraCount: { fontFamily: fonts.ui, fontSize: 9, color: colors.textMuted, marginTop: 2 },
  expandIcon: { fontFamily: fonts.displaySemiBold, fontSize: 18, color: colors.rubric, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },

  // Density bar
  densityBar: { flexDirection: 'row', gap: 1, marginHorizontal: layout.screenPadding, height: 6, marginBottom: 4 },
  densitySegment: { flex: 1, borderRadius: 1 },

  // Event rows
  eventRow: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 8, paddingRight: layout.screenPadding, paddingLeft: 4, minHeight: 44 },
  eventRowSelected: { backgroundColor: 'rgba(139,37,0,0.03)' },
  dateMargin: { width: 52, alignItems: 'flex-end', paddingRight: 8, paddingTop: 1 },
  dateNum: { fontFamily: fonts.displaySemiBold, fontSize: 14, color: colors.ink, lineHeight: 16, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  dateEra: { fontFamily: fonts.uiMedium, fontSize: 7, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  knowledgeDot: { width: 10, height: 10, borderRadius: 5, marginTop: 4, marginRight: 8 },
  eventContent: { flex: 1 },
  eventTitle: { fontFamily: fonts.bodyMedium, fontSize: 14, color: colors.textPrimary, lineHeight: 19, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  eventDomain: { fontFamily: fonts.uiMedium, fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 1, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  eventDesc: { fontFamily: fonts.reading, fontSize: 13, color: colors.textSecondary, lineHeight: 18, marginTop: 4 },
  entityTags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6 },
  entityTag: { ...type.topicTag, color: colors.rubric },
  connectionBanner: { marginTop: 6, paddingLeft: 8, borderLeftWidth: 2, borderLeftColor: colors.rubric, backgroundColor: 'rgba(139,37,0,0.04)', paddingVertical: 4 },
  connectionLabel: { fontFamily: fonts.uiMedium, fontSize: 8, color: colors.rubric, textTransform: 'uppercase', letterSpacing: 0.5, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  connectionText: { fontFamily: fonts.reading, fontSize: 12, color: colors.textSecondary, marginTop: 1 },

  // Action buttons
  actionRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
  actionBtn: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 2, borderWidth: 1, borderColor: colors.rule },
  actionBtnPrimary: { backgroundColor: colors.rubric, borderColor: colors.rubric },
  actionBtnDisabled: { backgroundColor: colors.parchmentDark, borderColor: colors.rule },
  actionBtnText: { fontFamily: fonts.ui, fontSize: 11, color: colors.textSecondary },
  actionBtnTextPrimary: { color: colors.parchment },
  eventDivider: { height: 1, backgroundColor: colors.rule, marginLeft: 70, marginRight: layout.screenPadding, opacity: 0.5 },

  // Entity list (persons/places sub-tabs)
  entityRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.rule },
  entityRowLeft: { flex: 1 },
  entityName: { fontFamily: fonts.bodyMedium, fontSize: 15, color: colors.textPrimary, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  entityMeta: { flexDirection: 'row', gap: 8, marginTop: 2 },
  entityDates: { fontFamily: fonts.display, fontSize: 12, color: colors.ink },
  entityNodeCount: { fontFamily: fonts.ui, fontSize: 10, color: colors.textMuted },
  entityDomainRow: { flexDirection: 'row', gap: 3, marginTop: 4 },
  domainDot: { width: 6, height: 6, borderRadius: 3 },
  entityChevron: { fontFamily: fonts.display, fontSize: 18, color: colors.textMuted },

  // Empty
  emptyWrap: { padding: 32, alignItems: 'center' },
  emptyText: { fontFamily: fonts.readingItalic, fontSize: 14, color: colors.textMuted, textAlign: 'center', ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}) },
});
