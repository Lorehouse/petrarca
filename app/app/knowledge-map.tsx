import { useEffect, useMemo, useState, useCallback } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, Platform, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, fonts, type, layout } from '../design/tokens';
import { logEvent } from '../data/logger';
import { RESEARCH_BASE } from '../lib/chat-api';
import DoubleRule from '../components/DoubleRule';

// Knowledge level → display config
const LEVEL_CONFIG = {
  anchored: { label: 'Anchored', color: colors.claimNew, dotColor: colors.claimNew },
  engaged: { label: 'Engaged', color: '#6a8a4a', dotColor: '#6a8a4a' },
  mentioned: { label: 'Mentioned', color: colors.warning, dotColor: colors.warning },
  unknown: { label: 'Unknown', color: colors.textMuted, dotColor: colors.rule },
} as const;

type KnowledgeLevel = keyof typeof LEVEL_CONFIG;

// Server annotates knowledge directly on each node
interface CurriculumNode {
  id: string;
  title: string;
  description: string;
  level: number;
  parent_id: string | null;
  prerequisites: string[];
  obscurity: number;
  knowledge?: KnowledgeLevel;
  interest?: string;
  confidence?: number;
  sources?: string[];
}

interface CurriculumData {
  id: string;
  title: string;
  depth: string;
  node_count: number;
  nodes: CurriculumNode[];
}

interface CurriculumSummary {
  id: string;
  title: string;
  depth: string;
  node_count: number;
}

export default function KnowledgeMapScreen() {
  const router = useRouter();
  const [curricula, setCurricula] = useState<CurriculumSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [curriculum, setCurriculum] = useState<CurriculumData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    logEvent('knowledge_map_open');
    fetch(`${RESEARCH_BASE}/curriculum/list`)
      .then(r => r.json())
      .then(data => {
        setCurricula(data.curricula || []);
        // Auto-select first curriculum
        if (data.curricula?.length > 0) {
          setSelected(data.curricula[0].id);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetch(`${RESEARCH_BASE}/curriculum/${selected}`)
      .then(r => r.json())
      .then(data => {
        setCurriculum(data);
        // Expand all top-level areas by default
        const topLevel = new Set(
          (data.nodes || []).filter((n: CurriculumNode) => n.level === 1).map((n: CurriculumNode) => n.id)
        ) as Set<string>;
        setExpanded(topLevel);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selected]);

  const toggleExpand = useCallback((nodeId: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  // Build tree structure from flat node list
  const tree = useMemo(() => {
    if (!curriculum) return null;
    const nodes = curriculum.nodes;
    const nodeMap: Record<string, CurriculumNode> = {};
    const childrenOf: Record<string, CurriculumNode[]> = {};
    const roots: CurriculumNode[] = [];

    for (const n of nodes) {
      nodeMap[n.id] = n;
      if (n.parent_id == null) {
        roots.push(n);
      } else {
        if (!childrenOf[n.parent_id]) childrenOf[n.parent_id] = [];
        childrenOf[n.parent_id].push(n);
      }
    }

    return { roots, childrenOf, nodeMap };
  }, [curriculum]);

  // Coverage stats — read knowledge directly from nodes
  const stats = useMemo(() => {
    if (!curriculum) return null;
    const total = curriculum.nodes.length;
    const counts = { anchored: 0, engaged: 0, mentioned: 0, unknown: 0 };
    for (const n of curriculum.nodes) {
      const level = (n.knowledge || 'unknown') as KnowledgeLevel;
      counts[level] = (counts[level] || 0) + 1;
    }
    return { total, ...counts };
  }, [curriculum]);

  if (loading && curricula.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.rubric} size="large" />
      </View>
    );
  }

  const isWeb = Platform.OS === 'web';
  const containerStyle = isWeb ? [styles.container, { maxWidth: layout.readingMeasure, alignSelf: 'center' as const, width: '100%' as any }] : styles.container;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.parchment }}>
      <View style={containerStyle}>
        {/* Header */}
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Text style={styles.backText}>← Back</Text>
          </Pressable>
          <Text style={styles.pageTitle}>Knowledge Map</Text>
          <Text style={styles.subtitle}>What you know, what you're learning</Text>
        </View>
        <DoubleRule />

        {/* Domain selector */}
        {curricula.length > 1 && (
          <View style={styles.domainRow}>
            {curricula.map(c => (
              <Pressable
                key={c.id}
                style={[styles.domainTab, selected === c.id && styles.domainTabActive]}
                onPress={() => setSelected(c.id)}
              >
                <Text style={[styles.domainTabText, selected === c.id && styles.domainTabTextActive]}>
                  {c.title.length > 30 ? c.title.slice(0, 30) + '…' : c.title}
                </Text>
              </Pressable>
            ))}
          </View>
        )}

        {loading ? (
          <View style={styles.loadingInline}>
            <ActivityIndicator color={colors.rubric} />
          </View>
        ) : curriculum && tree && stats ? (
          <>
            {/* Coverage bar */}
            <View style={styles.coverageSection}>
              <Text style={styles.sectionHead}>✦ Coverage</Text>
              <View style={styles.coverageBar}>
                {stats.anchored > 0 && (
                  <View style={[styles.coverageSegment, { flex: stats.anchored, backgroundColor: LEVEL_CONFIG.anchored.color }]} />
                )}
                {stats.engaged > 0 && (
                  <View style={[styles.coverageSegment, { flex: stats.engaged, backgroundColor: LEVEL_CONFIG.engaged.color }]} />
                )}
                {stats.mentioned > 0 && (
                  <View style={[styles.coverageSegment, { flex: stats.mentioned, backgroundColor: LEVEL_CONFIG.mentioned.color }]} />
                )}
                {stats.unknown > 0 && (
                  <View style={[styles.coverageSegment, { flex: stats.unknown, backgroundColor: LEVEL_CONFIG.unknown.dotColor }]} />
                )}
              </View>
              <View style={styles.legendRow}>
                {(['anchored', 'engaged', 'mentioned', 'unknown'] as KnowledgeLevel[]).map(level => (
                  <View key={level} style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: LEVEL_CONFIG[level].dotColor }]} />
                    <Text style={styles.legendText}>
                      {LEVEL_CONFIG[level].label} {stats[level]}
                    </Text>
                  </View>
                ))}
              </View>
            </View>

            {/* Tree view */}
            <View style={styles.treeSection}>
              <Text style={styles.sectionHead}>✦ Curriculum</Text>
              {tree.roots.map(root => (
                <TreeNode
                  key={root.id}
                  node={root}
                  childrenOf={tree.childrenOf}
                  nodeMap={tree.nodeMap}
                  expanded={expanded}
                  onToggle={toggleExpand}
                  depth={0}
                />
              ))}
            </View>
          </>
        ) : (
          <Text style={styles.emptyText}>No curricula found. Generate one from the server first.</Text>
        )}
      </View>
    </ScrollView>
  );
}

function TreeNode({
  node,
  childrenOf,
  nodeMap,
  expanded,
  onToggle,
  depth,
}: {
  node: CurriculumNode;
  childrenOf: Record<string, CurriculumNode[]>;
  nodeMap: Record<string, CurriculumNode>;
  expanded: Set<string>;
  onToggle: (id: string) => void;
  depth: number;
}) {
  const level = (node.knowledge || 'unknown') as KnowledgeLevel;
  const config = LEVEL_CONFIG[level];
  const children = childrenOf[node.id] || [];
  const hasChildren = children.length > 0;
  const isExpanded = expanded.has(node.id);
  const [showDesc, setShowDesc] = useState(false);

  // Compute child coverage for areas
  const childSummary = useMemo(() => {
    if (!hasChildren) return null;
    let anchored = 0, engaged = 0, total = 0;
    const count = (nodeId: string) => {
      const kids = childrenOf[nodeId] || [];
      for (const k of kids) {
        total++;
        const kl = (k.knowledge || 'unknown') as KnowledgeLevel;
        if (kl === 'anchored') anchored++;
        else if (kl === 'engaged') engaged++;
        count(k.id);
      }
    };
    count(node.id);
    return { anchored, engaged, total };
  }, [node.id, childrenOf, hasChildren]);

  return (
    <View style={[styles.treeNode, depth > 0 && { marginLeft: 16 }]}>
      <Pressable
        style={styles.nodeRow}
        onPress={() => hasChildren ? onToggle(node.id) : setShowDesc(!showDesc)}
      >
        {/* Knowledge dot */}
        <View style={[styles.knowledgeDot, { backgroundColor: config.dotColor }]} />

        {/* Expand arrow for parents */}
        {hasChildren && (
          <Text style={styles.expandArrow}>{isExpanded ? '▾' : '▸'}</Text>
        )}

        {/* Title */}
        <View style={styles.nodeTitleWrap}>
          <Text style={[styles.nodeTitle, depth === 0 && styles.nodeTitleArea]} numberOfLines={2}>
            {node.title}
          </Text>
          {childSummary && (
            <Text style={styles.nodeMeta}>
              {childSummary.anchored + childSummary.engaged}/{childSummary.total} covered
            </Text>
          )}
        </View>

        {/* Level label */}
        <Text style={[styles.levelLabel, { color: config.color }]}>
          {level !== 'unknown' ? config.label : ''}
        </Text>
      </Pressable>

      {/* Description (for leaf nodes on tap) */}
      {showDesc && !hasChildren && node.description && (
        <Text style={styles.nodeDesc}>{node.description}</Text>
      )}

      {/* Children */}
      {isExpanded && children.map(child => (
        <TreeNode
          key={child.id}
          node={child}
          childrenOf={childrenOf}
          nodeMap={nodeMap}
          expanded={expanded}
          onToggle={onToggle}
          depth={depth + 1}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingBottom: 60,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.parchment,
  },
  header: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 12,
    paddingBottom: 8,
  },
  backText: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.rubric,
    marginBottom: 12,
  },
  pageTitle: {
    ...type.screenTitle,
    color: colors.ink,
  },
  subtitle: {
    ...type.screenSubtitle,
    color: colors.textSecondary,
    marginTop: 2,
  },

  // Domain selector
  domainRow: {
    flexDirection: 'row',
    paddingHorizontal: layout.screenPadding,
    paddingTop: 16,
    gap: 8,
    flexWrap: 'wrap',
  },
  domainTab: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: colors.rule,
  },
  domainTabActive: {
    borderColor: colors.rubric,
    backgroundColor: 'rgba(139, 37, 0, 0.05)',
  },
  domainTabText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.textSecondary,
  },
  domainTabTextActive: {
    color: colors.rubric,
  },

  loadingInline: {
    paddingVertical: 40,
    alignItems: 'center',
  },

  // Coverage
  coverageSection: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 20,
    paddingBottom: 8,
  },
  sectionHead: {
    ...type.sectionHead,
    color: colors.rubric,
    marginBottom: 10,
  },
  coverageBar: {
    flexDirection: 'row',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    backgroundColor: colors.rule,
  },
  coverageSegment: {
    height: '100%',
  },
  legendRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
    flexWrap: 'wrap',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontFamily: fonts.ui,
    fontSize: 11,
    color: colors.textSecondary,
  },

  // Tree
  treeSection: {
    paddingHorizontal: layout.screenPadding,
    paddingTop: 20,
  },
  treeNode: {
    marginBottom: 2,
  },
  nodeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    gap: 8,
    minHeight: 40,
  },
  knowledgeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    flexShrink: 0,
  },
  expandArrow: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.textMuted,
    width: 14,
    textAlign: 'center',
  },
  nodeTitleWrap: {
    flex: 1,
  },
  nodeTitle: {
    fontFamily: fonts.reading,
    fontSize: 14,
    lineHeight: 20,
    color: colors.textBody,
  },
  nodeTitleArea: {
    fontFamily: fonts.bodyMedium,
    fontSize: 15,
    color: colors.ink,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  nodeMeta: {
    fontFamily: fonts.ui,
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 1,
  },
  levelLabel: {
    fontFamily: fonts.ui,
    fontSize: 10,
    letterSpacing: 0.3,
    textTransform: 'uppercase',
    flexShrink: 0,
  },
  nodeDesc: {
    fontFamily: fonts.reading,
    fontSize: 13,
    lineHeight: 19,
    color: colors.textSecondary,
    marginLeft: 16,
    marginBottom: 8,
    paddingLeft: 16,
    borderLeftWidth: 2,
    borderLeftColor: colors.rule,
  },
  emptyText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.textMuted,
    padding: layout.screenPadding,
    paddingTop: 40,
    textAlign: 'center',
  },
});
