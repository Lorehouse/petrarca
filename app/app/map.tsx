import { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { colors, fonts, layout } from '../design/tokens';
import { RESEARCH_BASE } from '../lib/chat-api';
import { EntityDetails } from '../data/types';
import { logEvent } from '../data/logger';
import { recordEntityTap } from '../lib/book-api';
import AncientMap, { AncientMapRef, MapFilter, MapRoute, MapSelectEvent, MapActionEvent } from '../components/AncientMap';
import EntitySheet from '../components/EntitySheet';

const DOMAIN_FILTERS: MapFilter[] = [
  { id: 'greek_sicily', label: 'Greek Sicily', field: 'region', value: 'greek_sicily' },
  { id: 'mainland_greece', label: 'Mainland Greece', field: 'region', value: 'mainland_greece' },
  { id: 'phoenician', label: 'Phoenician', field: 'region', value: 'phoenician' },
];

const ROUTES: MapRoute[] = [
  { id: 'corinth_syracuse', from: 'corinth', to: 'syracuse', label: 'Colonization',
    waypoints: [[37.9386, 22.9322], [37.5, 20.0], [37.2, 17.5], [37.0755, 15.2866]] },
  { id: 'gela_akragas', from: 'gela', to: 'akragas',
    waypoints: [[37.0666, 14.2498], [37.3111, 13.5765]] },
  { id: 'carthage_motya', from: 'carthage', to: 'motya', label: 'Trade',
    waypoints: [[36.8528, 10.3233], [37.3, 11.5], [37.8686, 12.4669]] },
];

export default function MapScreen() {
  const mapRef = useRef<AncientMapRef>(null);
  const [entities, setEntities] = useState<EntityDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  // Fetch place entities from server
  useEffect(() => {
    fetch(`${RESEARCH_BASE}/entities?type=place`)
      .then(r => r.json())
      .then(setEntities)
      .catch(() => setEntities([]))
      .finally(() => setLoading(false));
    logEvent('map_screen_opened');
  }, []);

  const handleSelect = useCallback((event: MapSelectEvent | null) => {
    if (event) {
      setSelectedEntityId(event.entityId);
      logEvent('map_entity_selected', { entity_id: event.entityId });
    } else {
      setSelectedEntityId(null);
    }
  }, []);

  const handleAction = useCallback((event: MapActionEvent) => {
    const tapAction = event.action === 'got_it' ? 'tap' : event.action;
    recordEntityTap(event.entityId, tapAction).catch(() => {});
    logEvent('map_entity_action', { entity_id: event.entityId, action: event.action });
    if (event.action === 'unknown') {
      mapRef.current?.updateKnowledge(event.entityId, 'unknown');
    }
  }, []);

  const handleEntitySheetClose = useCallback(() => {
    setSelectedEntityId(null);
    mapRef.current?.selectEntity(null);
  }, []);

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="small" color={colors.rubric} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <AncientMap
        ref={mapRef}
        entities={entities}
        filters={DOMAIN_FILTERS}
        routes={ROUTES}
        showEntitySheet={false}
        onEntitySelect={handleSelect}
        onEntityAction={handleAction}
      />
      <EntitySheet
        entityId={selectedEntityId}
        onClose={handleEntitySheetClose}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.parchment,
  },
  loading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.parchment,
  },
});
