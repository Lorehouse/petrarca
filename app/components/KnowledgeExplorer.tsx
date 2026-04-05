import { useCallback, useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Platform, ActivityIndicator, Linking } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout, spacing } from '../design/tokens';
import { logEvent } from '../data/logger';
import { RESEARCH_BASE } from '../lib/chat-api';
import { triggerMicrolearning, fetchEntityDetails } from '../lib/book-api';
import { EntityDetails } from '../data/types';
import EntitySheet from './EntitySheet';
import ExplorerCapture, { CaptureResult } from './ExplorerCapture';

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
  name_to_entity_id?: Record<string, string>;
}

type SubTab = 'timeline' | 'persons' | 'places';
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
  const [entityType, setEntityType] = useState<EntityType>(initialEntityType || 'place');
  const [selectedEntity, setSelectedEntity] = useState<string | null>(initialEntity || null);
  const [expandedCenturies, setExpandedCenturies] = useState<Set<number>>(new Set());
  const [selectedNode, setSelectedNode] = useState<TimelineNode | null>(null);
  const [entityDetails, setEntityDetails] = useState<EntityDetails | null>(null);
  const [entityDetailsLoading, setEntityDetailsLoading] = useState(false);
  const [sheetEntityId, setSheetEntityId] = useState<string | null>(null);
  const [captureExpanded, setCaptureExpanded] = useState(false);

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
      setSelectedEntity(null); // show all domains for a year focus
      const century = getCentury(initialYear);
      setExpandedCenturies(new Set([century]));
    }
  }, [initialYear, data]);

  // Fetch entity details when a person is selected
  useEffect(() => {
    if (!selectedEntity || !data || entityType !== 'person') {
      setEntityDetails(null);
      return;
    }
    const entityId = data.name_to_entity_id?.[selectedEntity];
    if (!entityId) {
      setEntityDetails(null);
      return;
    }
    setEntityDetailsLoading(true);
    fetchEntityDetails(entityId)
      .then(setEntityDetails)
      .catch(() => setEntityDetails(null))
      .finally(() => setEntityDetailsLoading(false));
  }, [selectedEntity, entityType, data]);

  const handleCaptureComplete = useCallback((result: CaptureResult) => {
    if (result.notes_saved > 0 && entityDetails) {
      // Refresh entity details to show new notes
      const entityId = data?.name_to_entity_id?.[selectedEntity || ''];
      if (entityId) {
        fetchEntityDetails(entityId).then(setEntityDetails).catch(() => {});
      }
    }
  }, [entityDetails, data, selectedEntity]);

  // Combined entity list for timeline pills (top places + persons by frequency)
  const entityList = useMemo(() => {
    if (!data) return [];
    const all: { name: string; count: number; type: EntityType }[] = [];
    for (const [name, ids] of Object.entries(data.places_index)) {
      if (ids.length >= 3 && ids.length <= 80) all.push({ name, count: ids.length, type: 'place' });
    }
    for (const [name, ids] of Object.entries(data.persons_index)) {
      if (ids.length >= 3) all.push({ name, count: ids.length, type: 'person' });
    }
    return all.sort((a, b) => b.count - a.count).slice(0, 30);
  }, [data]);

  // Timeline: filtered nodes, optionally grouped by century
  const filteredNodes = useMemo(() => {
    if (!data) return [];
    let filtered: TimelineNode[];
    if (selectedEntity) {
      // Check both indices for the entity
      const placeIds = data.places_index[selectedEntity] || [];
      const personIds = data.persons_index[selectedEntity] || [];
      const nodeIds = new Set([...placeIds, ...personIds]);
      filtered = data.nodes.filter(n => nodeIds.has(n.id) && n.time_span);
    } else {
      filtered = data.nodes.filter(n => n.time_span);
    }
    return filtered.sort((a, b) => (a.time_span![0]) - (b.time_span![0]));
  }, [data, selectedEntity]);

  // Use flat list when few events, century groups when many
  const useFlatLayout = filteredNodes.length <= 15;

  const sections = useMemo(() => {
    if (useFlatLayout) return [];
    const groups = new Map<number, TimelineNode[]>();
    for (const node of filteredNodes) {
      const c = getCentury(node.time_span![0]);
      if (!groups.has(c)) groups.set(c, []);
      groups.get(c)!.push(node);
    }
    return Array.from(groups.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([century, nodes]) => ({ century, label: centuryLabel(century), nodes }));
  }, [filteredNodes, useFlatLayout]);

  const toggleCentury = useCallback((century: number) => {
    setExpandedCenturies(prev => {
      const next = new Set(prev);
      if (next.has(century)) next.delete(century);
      else next.add(century);
      return next;
    });
  }, []);

  // Auto-expand when entity changes — always expand for specific entities,
  // only collapse for unfiltered "All" view with many centuries
  useEffect(() => {
    if (selectedEntity || (sections.length > 0 && sections.length <= 8)) {
      setExpandedCenturies(new Set(sections.map(s => s.century)));
    } else {
      setExpandedCenturies(new Set());
    }
  }, [selectedEntity, sections.length]);

  if (loading) {
    return (
      <View style={s.loadingWrap}>
        <ActivityIndicator size="small" color={colors.rubric} />
        <Text style={s.loadingText}>Loading knowledge index…</Text>
      </View>
    );
  }

  if (!data) return <Text style={s.errorText}>Could not load knowledge data</Text>;

  const totalNodes = filteredNodes.length;
  const knownCount = filteredNodes.filter(n => n.knowledge !== 'unknown').length;

  const showDomain = !selectedEntity;

  const renderEvent = (node: TimelineNode) => (
    <TimelineEvent key={node.id} node={node} showDomain={showDomain}
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
  );

  return (
    <ScrollView contentContainerStyle={s.scrollContent}>
      {/* Knowledge Atlas link */}
      <Pressable style={s.atlasLink} onPress={() => Linking.openURL(`${RESEARCH_BASE}/knowledge/atlas`)}>
        <Text style={s.atlasLinkStar}>✦</Text>
        <Text style={s.atlasLinkText}>Knowledge Atlas</Text>
        <Text style={s.atlasLinkArrow}>→</Text>
      </Pressable>

      {/* Sub-tabs: Timeline / Persons / Places */}
      <View style={s.subTabRow}>
        {(['timeline', 'persons', 'places'] as SubTab[]).map(tab => (
          <Pressable key={tab} style={[s.subTab, subTab === tab && s.subTabActive]}
            onPress={() => setSubTab(tab)}>
            <Text style={[s.subTabText, subTab === tab && s.subTabTextActive]}>
              {tab === 'timeline' ? 'Timeline' : tab === 'persons' ? 'Persons' : 'Places'}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Centralized capture bar */}
      <View style={s.captureBar}>
        {captureExpanded ? (
          <View style={s.captureExpandedWrap}>
            <View style={s.captureHeaderRow}>
              <Text style={s.captureLabel}>Capture</Text>
              <Pressable onPress={() => setCaptureExpanded(false)} hitSlop={8}>
                <Text style={s.captureClose}>✕</Text>
              </Pressable>
            </View>
            <ExplorerCapture mode="general" placeholder="Note, question, or voice recording…" />
          </View>
        ) : (
          <Pressable style={s.captureCollapsedBtn} onPress={() => setCaptureExpanded(true)}>
            <View style={s.captureMicIcon} />
            <Text style={s.captureCollapsedText}>Capture a note or question…</Text>
          </Pressable>
        )}
      </View>

      {/* ── Timeline sub-tab ── */}
      {subTab === 'timeline' && (
        <>
          {/* Entity pills — one row, "All" + mixed places/persons */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.entityPills}>
            <Pressable style={[s.pill, !selectedEntity && s.pillActive]}
              onPress={() => { setSelectedEntity(null); setSelectedNode(null); }}>
              <Text style={[s.pillText, !selectedEntity && s.pillTextActive]}>All</Text>
            </Pressable>
            {entityList.map(e => (
              <Pressable key={e.name} style={[s.pill, selectedEntity === e.name && s.pillActive]}
                onPress={() => { setSelectedEntity(e.name); setEntityType(e.type); setSelectedNode(null); }}>
                <Text style={[s.pillText, selectedEntity === e.name && s.pillTextActive]}>{e.name}</Text>
                <Text style={[s.pillCount, selectedEntity === e.name && s.pillCountActive]}>{e.count}</Text>
              </Pressable>
            ))}
          </ScrollView>

          {/* Summary line */}
          {totalNodes > 0 && !entityDetails && (
            <Text style={s.entitySummary}>
              {selectedEntity || 'All domains'} · {totalNodes} events · {knownCount} known
            </Text>
          )}

          {/* Inline person card when filtering by a person */}
          {selectedEntity && entityType === 'person' && (
            <View style={s.personCard}>
              {entityDetailsLoading ? (
                <ActivityIndicator size="small" color={colors.rubric} style={{ padding: 12 }} />
              ) : entityDetails ? (
                <>
                  <View style={s.personCardHeader}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.personCardName}>{entityDetails.name}</Text>
                      {entityDetails.date_start != null && (
                        <Text style={s.personCardDates}>
                          {entityDetails.date_start < 0 ? `${Math.abs(entityDetails.date_start)} BC` : `${entityDetails.date_start} AD`}
                          {entityDetails.date_end != null ? ` – ${entityDetails.date_end < 0 ? `${Math.abs(entityDetails.date_end)} BC` : `${entityDetails.date_end} AD`}` : ''}
                        </Text>
                      )}
                    </View>
                    <View style={s.personCardStats}>
                      <Text style={s.personCardStatNum}>{totalNodes}</Text>
                      <Text style={s.personCardStatLabel}>events</Text>
                      <Text style={[s.personCardStatNum, { marginTop: 2 }]}>{knownCount}</Text>
                      <Text style={s.personCardStatLabel}>known</Text>
                    </View>
                  </View>
                  {entityDetails.description && (
                    <Text style={s.personCardDesc}>{entityDetails.description}</Text>
                  )}

                  {/* Existing notes */}
                  {entityDetails.notes && entityDetails.notes.length > 0 && (
                    <View style={s.notesSection}>
                      <Text style={s.notesSectionLabel}>What I know</Text>
                      {entityDetails.notes.map(n => (
                        <Text key={n.id} style={s.noteText}>{n.note}</Text>
                      ))}
                    </View>
                  )}

                  {/* Voice/text capture */}
                  <View style={s.personCardCapture}>
                    <ExplorerCapture
                      mode="entity"
                      entityId={entityDetails.entity_id}
                      entityName={entityDetails.name}
                      onCaptureComplete={handleCaptureComplete}
                    />
                  </View>

                  {/* Actions */}
                  <View style={s.personCardActions}>
                    <Pressable style={s.personCardBtn} onPress={() => {
                      setSheetEntityId(entityDetails.entity_id);
                      logEvent('explorer_open_entity_sheet', { entity_id: entityDetails.entity_id });
                    }}>
                      <Text style={s.personCardBtnText}>Full profile →</Text>
                    </Pressable>
                    {entityDetails.wikipedia_url && (
                      <Pressable style={[s.personCardBtn, s.personCardBtnSecondary]} onPress={() => {
                        Linking.openURL(entityDetails.wikipedia_url!);
                      }}>
                        <Text style={[s.personCardBtnText, s.personCardBtnTextSecondary]}>Wikipedia</Text>
                      </Pressable>
                    )}
                  </View>
                </>
              ) : (
                <Text style={s.entitySummary}>
                  {selectedEntity} · {totalNodes} events · {knownCount} known
                </Text>
              )}
            </View>
          )}

          {/* Flat layout for sparse entities (≤15 events) */}
          {useFlatLayout && filteredNodes.length > 0 && filteredNodes.map(renderEvent)}

          {/* Grouped layout for dense entities (>15 events) */}
          {!useFlatLayout && sections.map(section => {
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
                {isExpanded && section.nodes.map(renderEvent)}
              </View>
            );
          })}

          {totalNodes === 0 && (
            <View style={s.emptyWrap}>
              <Text style={s.emptyText}>No dated events found</Text>
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
            setSubTab('timeline');
          }}
        />
      )}

      <View style={{ height: 40 }} />

      {/* Entity Sheet modal */}
      <EntitySheet
        entityId={sheetEntityId}
        onClose={() => setSheetEntityId(null)}
        onExploreEntity={(name) => {
          setSelectedEntity(name);
          setSheetEntityId(null);
          setSubTab('timeline');
        }}
      />
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
              {[...(node.entities.persons || []), ...(node.entities.places || [])].slice(0, 5).map(e => (
                <Pressable key={e} onPress={() => onSelectEntity(e)} hitSlop={4}>
                  <Text style={s.entityTag}>{e}</Text>
                </Pressable>
              ))}
            </View>
          )}
          {isSelected && (node.entities.events || []).length > 0 && (
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
  atlasLink: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    marginHorizontal: layout.screenPadding, marginTop: 8, marginBottom: 4,
    paddingVertical: 8, paddingHorizontal: 12,
    borderWidth: 1, borderColor: colors.rule, backgroundColor: '#fff',
  },
  atlasLinkStar: { fontFamily: fonts.body, fontSize: 14, color: colors.rubric },
  atlasLinkText: { fontFamily: fonts.body, fontSize: 13, color: colors.ink },
  atlasLinkArrow: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted, marginLeft: 'auto' },
  loadingWrap: { padding: 40, alignItems: 'center', gap: 8 },
  loadingText: { ...type.screenSubtitle, color: colors.textMuted },
  errorText: { fontFamily: fonts.reading, fontSize: 14, color: colors.textSecondary, textAlign: 'center', padding: 32 },

  // Sub-tabs
  subTabRow: { flexDirection: 'row', marginHorizontal: layout.screenPadding, borderBottomWidth: 1, borderBottomColor: colors.rule },
  subTab: { flex: 1, alignItems: 'center', paddingVertical: 8 },
  subTabActive: { borderBottomWidth: 2, borderBottomColor: colors.rubric, marginBottom: -1 },
  subTabText: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted },
  subTabTextActive: { color: colors.rubric },

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

  // Inline person card
  personCard: { marginHorizontal: layout.screenPadding, marginBottom: 10, padding: 12, backgroundColor: 'rgba(139,37,0,0.03)', borderLeftWidth: 2, borderLeftColor: colors.rubric, borderRadius: 2 },
  personCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  personCardName: { fontFamily: fonts.displaySemiBold, fontSize: 18, color: colors.ink, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  personCardDates: { fontFamily: fonts.ui, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  personCardStats: { alignItems: 'center', paddingLeft: 12 },
  personCardStatNum: { fontFamily: fonts.displaySemiBold, fontSize: 16, color: colors.ink, ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}) },
  personCardStatLabel: { fontFamily: fonts.ui, fontSize: 8, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
  personCardDesc: { fontFamily: fonts.reading, fontSize: 14, lineHeight: 20, color: colors.textBody, marginTop: 8 },
  personCardActions: { flexDirection: 'row', gap: 8, marginTop: 10 },
  personCardBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 2, backgroundColor: colors.ink },
  personCardBtnSecondary: { backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.rule },
  personCardBtnText: { fontFamily: fonts.ui, fontSize: 11, color: colors.parchment },
  personCardBtnTextSecondary: { color: colors.textSecondary },

  // Notes
  notesSection: { marginTop: 10, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: colors.rule },
  notesSectionLabel: { fontFamily: fonts.uiMedium, fontSize: 9, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  noteText: { fontFamily: fonts.reading, fontSize: 13, lineHeight: 18, color: colors.textBody, marginBottom: 4 },
  personCardCapture: { marginTop: 10 },

  // Centralized capture bar
  captureBar: { marginHorizontal: layout.screenPadding, marginBottom: 8 },
  captureCollapsedBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8, paddingHorizontal: 12, borderWidth: 1, borderColor: colors.rule, borderRadius: 2, backgroundColor: 'rgba(0,0,0,0.02)' },
  captureMicIcon: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.rubric },
  captureCollapsedText: { fontFamily: fonts.reading, fontSize: 13, color: colors.textMuted },
  captureExpandedWrap: { padding: 12, borderWidth: 1, borderColor: colors.rubric, borderRadius: 2, backgroundColor: 'rgba(139,37,0,0.02)' },
  captureHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  captureLabel: { fontFamily: fonts.uiMedium, fontSize: 10, color: colors.rubric, textTransform: 'uppercase', letterSpacing: 0.8, ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}) },
  captureClose: { fontSize: 16, color: colors.textMuted, padding: 4 },
});
