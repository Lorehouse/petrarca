# Map View Design Exploration Brief

*2026-03-30. To be explored with design-explorer in a separate session.*

## Context

Petrarca is a knowledge learning app (Expo SDK 54, React Native) focused on ancient Mediterranean history — Sicily, Ancient Greece, Rome, Byzantine, Islamic civilizations. The review system tests knowledge of historical events, people, and places. Users currently have no geographic context — they encounter "Akragas", "Himera", "Corinth", "Syracuse" in review cards without knowing where these places are relative to each other.

See `/Users/stian/src/petrarca/research/entity-context-spec.md` for the full entity context system this map view plugs into.

## What the Map Needs to Do

### Core Requirements

1. **Show ancient places on an interactive map** — ~30-50 locations across the Mediterranean (Sicily, southern Italy, Greece, Anatolia, North Africa, Levant)
2. **Markers colored by knowledge state** — unknown (gray), encountered (amber), anchored (green). Data comes from `knowledge_states` table via API.
3. **Tap a marker → entity info** — Show entity name, brief description, dates, linked curriculum nodes. Ideally opens the same Entity Sheet used in review cards (bottom sheet with actions).
4. **Zoom and pan** — User should be able to zoom into Sicily to see individual colonies, or zoom out to see the whole Mediterranean.
5. **Work in Expo/React Native** — Must run on iOS (primary), ideally also web.

### Nice to Have

- **Time slider** — Filter markers by era (e.g., "750-500 BC: Colonization era" vs "480-400 BC: Age of Tyrants"). Markers appear/disappear as you scrub through time.
- **Domain filter pills** — Show only Sicily entities, or only Ancient Greece, etc.
- **Route/connection lines** — e.g., show the colonization route from Corinth → Syracuse, or trade routes.
- **Cluster labels** — Regional labels like "Magna Graecia", "Greek Sicily", "Phoenician West".
- **Current review session overlay** — Highlight the places mentioned in today's review cards.

### Entry Points

- From Entity Sheet: "View on map" button centers map on that entity
- From drawer navigation: Standalone map screen
- From knowledge-map screen: Geographic view toggle (currently tree view only)

## Technical Options to Explore

### Option A: Leaflet in WebView

- Embed a Leaflet.js map in a `<WebView>` component
- Pros: Zero native dependencies, no API key, full CSS control, custom tile layers (could use a historical/terrain map), works on web too
- Cons: WebView communication overhead (postMessage for taps), not truly native feel, potential scroll/gesture conflicts with parent RN scroll views
- Tile options: OpenStreetMap, Stamen Terrain, CartoDB Positron (clean/minimal), or even a historical map overlay

### Option B: react-native-maps

- Google Maps (Android) / Apple Maps (iOS) native components
- Pros: Native performance, smooth pinch-zoom-pan, gesture handling built in, Expo SDK support via `expo-maps` or `react-native-maps`
- Cons: Requires API keys for Google Maps, heavier dependency, less visual customization, looks modern (not historical)

### Option C: Static SVG/Image

- Pre-rendered Mediterranean map as SVG with clickable regions
- Pros: Zero dependencies, instant load, works offline, can be hand-designed to look beautiful and period-appropriate
- Cons: No real zoom/pan (or limited), hard to update, fixed level of detail, manual coordinate mapping

### Option D: Mapbox GL

- `@rnmapbox/maps` — vector tiles with full style control
- Pros: Beautiful custom styles (could create an "ancient parchment" style), great performance, offline tile caching
- Cons: Requires Mapbox API key (free tier generous), heavier dependency than Leaflet

## Visual Direction

The app uses a warm, bookish design language (cream backgrounds `#faf8f3`, dark brown text `#2c1810`, serif headers). The map should feel like it belongs in a historical atlas, not Google Maps. Consider:

- Muted/terrain tile layers (not satellite, not bright colors)
- Parchment-style backgrounds
- Serif labels for ancient place names
- Subtle animation for knowledge-state color transitions

## Design Tokens (from app)

```typescript
// From app/design/tokens.ts
colors = {
  background: '#faf8f3',
  text: '#2c1810',
  textSecondary: '#6b5b4f',
  accent: '#8b0000',
  border: '#e8e0d4',
  cardBg: '#ffffff',
}
```

## Sample Entity Data for Prototyping

```json
[
  {"name": "Syracuse", "modern": "Siracusa", "lat": 37.0755, "lon": 15.2866, "type": "place", "state": "anchored", "dates": "734 BC–present", "desc": "Greatest Greek colony in Sicily, founded by Corinthians"},
  {"name": "Akragas", "modern": "Agrigento", "lat": 37.3111, "lon": 13.5765, "type": "place", "state": "unknown", "dates": "~580 BC–406 BC", "desc": "Wealthy Greek colony, destroyed by Carthage in 406 BC"},
  {"name": "Himera", "modern": "Termini Imerese", "lat": 37.9725, "lon": 13.6942, "type": "place", "state": "encountered", "dates": "648–409 BC", "desc": "Site of Greek victory over Carthage, 480 BC"},
  {"name": "Naxos", "modern": "Giardini Naxos", "lat": 37.8231, "lon": 15.2672, "type": "place", "state": "encountered", "dates": "734 BC–", "desc": "First Greek colony on Sicily"},
  {"name": "Corinth", "modern": "Korinthos", "lat": 37.9386, "lon": 22.9322, "type": "place", "state": "anchored", "dates": "~6000 BC–", "desc": "Major Greek city-state, mother city of Syracuse"},
  {"name": "Athens", "modern": "Athens", "lat": 37.9838, "lon": 23.7275, "type": "place", "state": "anchored", "dates": "~3000 BC–", "desc": "Leading Greek city-state, launched disastrous Sicilian expedition 415 BC"},
  {"name": "Carthage", "modern": "Tunis suburb", "lat": 36.8528, "lon": 10.3233, "type": "place", "state": "encountered", "dates": "814–146 BC", "desc": "Phoenician power, major rival of Greek Sicily"},
  {"name": "Selinunte", "modern": "Marinella di Selinunte", "lat": 37.5847, "lon": 12.8253, "type": "place", "state": "unknown", "dates": "628–250 BC", "desc": "Westernmost Greek colony on Sicily, destroyed by Carthage 409 BC"},
  {"name": "Gela", "modern": "Gela", "lat": 37.0666, "lon": 14.2498, "type": "place", "state": "encountered", "dates": "688 BC–", "desc": "Cretan-Rhodian colony, mother city of Akragas"},
  {"name": "Sparta", "modern": "Sparti", "lat": 37.0739, "lon": 22.4297, "type": "place", "state": "anchored", "dates": "~900 BC–", "desc": "Militaristic Greek city-state, rival of Athens"},
  {"name": "Motya", "modern": "San Pantaleo island", "lat": 37.8686, "lon": 12.4669, "type": "place", "state": "unknown", "dates": "~800–397 BC", "desc": "Phoenician island fortress off western Sicily, destroyed by Dionysius I"},
  {"name": "Messina", "modern": "Messina", "lat": 38.1938, "lon": 15.5540, "type": "place", "state": "encountered", "dates": "~730 BC–", "desc": "Greek colony (Zancle/Messana) controlling the strait to Italy"}
]
```

## Deliverable

Multiple design mockups exploring the options above, especially:
1. A Leaflet WebView prototype with terrain tiles and the sample data
2. Visual treatment options (parchment style vs clean modern vs hybrid)
3. How the marker → entity sheet interaction works
4. How a time slider could work
5. Mobile layout considerations (full screen vs half screen, navigation integration)
