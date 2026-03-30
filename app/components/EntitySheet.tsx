import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator, Linking, Modal, Platform, Pressable,
  ScrollView, StyleSheet, Text, View,
} from 'react-native';
import { colors, fonts, layout } from '../design/tokens';
import { EntityDetails } from '../data/types';
import { fetchEntityDetails, recordEntityTap } from '../lib/book-api';
import { logEvent } from '../data/logger';

interface Props {
  entityId: string | null;
  onClose: () => void;
}

const TYPE_LABELS: Record<string, string> = {
  place: '\u{1F4CD} Place',
  person: '\u{1F464} Person',
  event: '\u26A1 Event',
  period: '\u{1F551} Period',
};

const KNOWLEDGE_COLORS: Record<string, string> = {
  anchored: colors.claimNew,
  engaged: '#b8860b',
  mentioned: colors.textMuted,
  unknown: colors.textFaint,
};

export default function EntitySheet({ entityId, onClose }: Props) {
  const [entity, setEntity] = useState<EntityDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [tapped, setTapped] = useState(false);

  useEffect(() => {
    if (!entityId) {
      setEntity(null);
      setTapped(false);
      return;
    }
    setLoading(true);
    setTapped(false);
    fetchEntityDetails(entityId)
      .then(setEntity)
      .catch(() => setEntity(null))
      .finally(() => setLoading(false));

    // Implicit tap signal — auto-schedules review
    recordEntityTap(entityId, 'tap').catch(() => {});
    logEvent('entity_sheet_opened', { entity_id: entityId });
  }, [entityId]);

  if (!entityId) return null;

  const handleAction = (action: 'unknown' | 'interested') => {
    if (!entityId) return;
    recordEntityTap(entityId, action).catch(() => {});
    logEvent('entity_action', { entity_id: entityId, action });
    setTapped(true);
    if (action === 'unknown') {
      setTimeout(onClose, 800);
    }
  };

  const handleWikipedia = () => {
    if (entity?.wikipedia_url) {
      Linking.openURL(entity.wikipedia_url);
      logEvent('entity_wikipedia', { entity_id: entityId });
    }
  };

  // Best knowledge state across linked nodes
  const bestKnowledge = entity?.curriculum_links?.reduce((best, link) => {
    const rank: Record<string, number> = { anchored: 3, engaged: 2, mentioned: 1, unknown: 0 };
    return (rank[link.knowledge || 'unknown'] || 0) > (rank[best] || 0)
      ? (link.knowledge || 'unknown') : best;
  }, 'unknown' as string) || 'unknown';

  const formatYear = (y: number | null | undefined) => {
    if (y == null) return '';
    return y < 0 ? `${Math.abs(y)} BC` : `${y} AD`;
  };

  return (
    <Modal
      visible={!!entityId}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable style={es.overlay} onPress={onClose}>
        <View />
      </Pressable>
      <View style={es.sheet}>
        <View style={es.handle} />
        <ScrollView style={es.scrollContent} showsVerticalScrollIndicator={false}>
          {loading ? (
            <ActivityIndicator size="small" color={colors.rubric} style={{ padding: 40 }} />
          ) : entity ? (
            <>
              {/* Header: type + name */}
              <View style={es.headerRow}>
                {entity.entity_type && (
                  <Text style={es.typeBadge}>
                    {TYPE_LABELS[entity.entity_type] || entity.entity_type}
                  </Text>
                )}
                <View style={[es.knowledgeDot, { backgroundColor: KNOWLEDGE_COLORS[bestKnowledge] || colors.textFaint }]} />
              </View>

              <Text style={es.entityName}>{entity.name}</Text>
              {entity.modern_name && entity.modern_name !== entity.name ? (
                <Text style={es.modernName}>Modern: {entity.modern_name}</Text>
              ) : null}

              {/* Dates */}
              {(entity.date_start != null || entity.dates) ? (
                <Text style={es.dates}>
                  {entity.date_start != null
                    ? `${formatYear(entity.date_start)}${entity.date_end != null ? ` – ${formatYear(entity.date_end)}` : ''}`
                    : entity.dates}
                </Text>
              ) : null}

              {/* Description */}
              {entity.description ? (
                <Text style={es.description}>{entity.description}</Text>
              ) : null}

              {/* Curriculum links */}
              {entity.curriculum_links?.length > 0 ? (
                <View style={es.linksSection}>
                  <Text style={es.sectionLabel}>In your curriculum</Text>
                  {entity.curriculum_links.map((link, i) => (
                    <View key={i} style={es.linkRow}>
                      <View style={[es.linkDot, { backgroundColor: KNOWLEDGE_COLORS[link.knowledge || 'unknown'] }]} />
                      <View style={es.linkContent}>
                        <Text style={es.linkTitle}>{link.node_title || link.node_id}</Text>
                        {link.lens_emphasis ? (
                          <Text style={es.linkEmphasis}>{link.lens_emphasis}</Text>
                        ) : null}
                      </View>
                    </View>
                  ))}
                </View>
              ) : null}

              {/* Wikipedia link */}
              {entity.wikipedia_url ? (
                <Pressable style={es.wikiLink} onPress={handleWikipedia}>
                  <Text style={es.wikiLinkText}>Wikipedia →</Text>
                </Pressable>
              ) : null}

              {/* Actions */}
              {tapped ? (
                <Text style={es.tappedConfirm}>Noted ✓</Text>
              ) : (
                <View style={es.actionRow}>
                  <Pressable
                    style={[es.actionBtn, es.unknownBtn]}
                    onPress={() => handleAction('unknown')}
                  >
                    <Text style={es.unknownBtnText}>I don't know this</Text>
                  </Pressable>
                  <Pressable
                    style={[es.actionBtn, es.interestedBtn]}
                    onPress={() => handleAction('interested')}
                  >
                    <Text style={es.interestedBtnText}>Tell me more</Text>
                  </Pressable>
                </View>
              )}
            </>
          ) : (
            <Text style={es.errorText}>Entity not found</Text>
          )}
        </ScrollView>
      </View>
    </Modal>
  );
}

const es = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  sheet: {
    backgroundColor: colors.parchment,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: '60%',
    paddingBottom: Platform.OS === 'ios' ? 34 : 16,
    ...(Platform.OS === 'web' ? {
      maxWidth: layout.readingMeasure + 2 * layout.screenPadding,
      alignSelf: 'center' as const,
      width: '100%',
    } : {}),
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.rule,
    alignSelf: 'center',
    marginTop: 8,
    marginBottom: 12,
  },
  scrollContent: {
    paddingHorizontal: layout.screenPadding,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  typeBadge: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textSecondary,
    letterSpacing: 0.3,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  knowledgeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  entityName: {
    fontFamily: fonts.displaySemiBold,
    fontSize: 24,
    color: colors.ink,
    marginBottom: 2,
    ...(Platform.OS === 'web' ? { fontWeight: '600' as const } : {}),
  },
  modernName: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 4,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  dates: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.textMuted,
    marginBottom: 10,
  },
  description: {
    fontFamily: fonts.reading,
    fontSize: 15,
    lineHeight: 22,
    color: colors.textBody,
    marginBottom: 16,
  },
  linksSection: {
    marginBottom: 16,
  },
  sectionLabel: {
    fontFamily: fonts.uiMedium,
    fontSize: 10,
    color: colors.textMuted,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    marginBottom: 8,
    ...(Platform.OS === 'web' ? { fontWeight: '500' as const } : {}),
  },
  linkRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 6,
  },
  linkDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 6,
  },
  linkContent: {
    flex: 1,
  },
  linkTitle: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.ink,
    lineHeight: 18,
  },
  linkEmphasis: {
    fontFamily: fonts.readingItalic,
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 16,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  wikiLink: {
    marginBottom: 16,
  },
  wikiLinkText: {
    fontFamily: fonts.ui,
    fontSize: 13,
    color: colors.info,
    textDecorationLine: 'underline',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 8,
  },
  actionBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 4,
    alignItems: 'center',
    borderWidth: 1,
  },
  unknownBtn: {
    borderColor: colors.rubric,
    backgroundColor: 'rgba(139,37,0,0.05)',
  },
  unknownBtnText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: colors.rubric,
  },
  interestedBtn: {
    borderColor: '#b8860b',
    backgroundColor: 'rgba(184,134,11,0.06)',
  },
  interestedBtnText: {
    fontFamily: fonts.ui,
    fontSize: 12,
    color: '#b8860b',
  },
  tappedConfirm: {
    fontFamily: fonts.readingItalic,
    fontSize: 14,
    color: colors.claimNew,
    textAlign: 'center',
    paddingVertical: 12,
    ...(Platform.OS === 'web' ? { fontStyle: 'italic' as const } : {}),
  },
  errorText: {
    fontFamily: fonts.reading,
    fontSize: 14,
    color: colors.textMuted,
    textAlign: 'center',
    padding: 40,
  },
});
