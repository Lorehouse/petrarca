import { Platform } from 'react-native';
import type { ArticleMeta, KnowledgeIndex } from './types';
import { logEvent } from './logger';

const API_BASE = Platform.OS === 'web'
  ? `${window.location.protocol}//${window.location.hostname}:8090`
  : 'http://alifstian.duckdns.org:8090';

// Fallback to nginx-served JSON if API is unavailable
const CONTENT_BASE = Platform.OS === 'web'
  ? '/content'
  : 'https://alifstian.duckdns.org/content';

const CONTENT_DIR_NAME = 'content';
const WEB_CACHE_PREFIX = '@petrarca/cache_';

// Lazy-load expo-file-system only on native
let NativeFS: any = null;
function getNativeFS() {
  if (!NativeFS && Platform.OS !== 'web') {
    NativeFS = require('expo-file-system');
  }
  return NativeFS;
}

// --- Web cache helpers ---

function webCacheRead(name: string): string | null {
  return localStorage.getItem(`${WEB_CACHE_PREFIX}${name}`);
}

function webCacheWrite(name: string, data: string) {
  try {
    localStorage.setItem(`${WEB_CACHE_PREFIX}${name}`, data);
  } catch {
    // localStorage full — not critical
  }
}

// --- Native file helpers ---

function getContentDir() {
  const { Paths, Directory } = getNativeFS();
  return new Directory(Paths.document, CONTENT_DIR_NAME);
}

function getCachedFile(name: string) {
  const { Paths, File } = getNativeFS();
  return new File(Paths.document, CONTENT_DIR_NAME, name);
}

function ensureContentDir() {
  const dir = getContentDir();
  if (!dir.exists) {
    dir.create({ intermediates: true });
  }
}

interface Manifest {
  last_updated: string;
  article_count: number;
  articles_hash: string;
  concepts_hash?: string;
  concept_count?: number;
  books_hash?: string;
  knowledge_index_hash?: string;
  clusters_hash?: string;
  syntheses_hash?: string;
}

function cacheWrite(name: string, data: string) {
  if (Platform.OS === 'web') {
    webCacheWrite(name, data);
  } else {
    try {
      ensureContentDir();
      getCachedFile(name).write(data);
    } catch {}
  }
}

function cacheRead(name: string): string | null {
  if (Platform.OS === 'web') {
    return webCacheRead(name);
  }
  try {
    const file = getCachedFile(name);
    // expo-file-system File.text() is sync in newer versions
    return file.exists ? file.text() : null;
  } catch {
    return null;
  }
}

// --- Change detection ---

function getLocalManifest(): Manifest | null {
  const raw = cacheRead('manifest.json');
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export async function checkForUpdates(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_BASE}/api/manifest`, { cache: 'no-store' });
    if (!resp.ok) return false;
    const remote: Manifest = await resp.json();

    const local = getLocalManifest();
    if (!local) return true;

    return remote.articles_hash !== local.articles_hash
      || remote.knowledge_index_hash !== local.knowledge_index_hash
      || remote.clusters_hash !== local.clusters_hash
      || remote.syntheses_hash !== local.syntheses_hash;
  } catch {
    return false;
  }
}

// --- Download ---

export interface DownloadedContent {
  articles: ArticleMeta[];
  knowledgeIndex: KnowledgeIndex | null;
  conceptClusters: any | null;
  syntheses: any | null;
}

export async function downloadContent(): Promise<DownloadedContent | null> {
  try {
    if (Platform.OS !== 'web') ensureContentDir();

    const [articlesResp, manifestResp, knowledgeResp, clustersResp, synthesesResp] = await Promise.all([
      fetch(`${API_BASE}/api/articles-meta`),
      fetch(`${API_BASE}/api/manifest`),
      fetch(`${API_BASE}/api/knowledge-index`).catch(() => null),
      fetch(`${API_BASE}/api/clusters`).catch(() => null),
      fetch(`${API_BASE}/api/syntheses`).catch(() => null),
    ]);

    if (!articlesResp.ok) {
      // Fallback to old nginx JSON if API unavailable
      return downloadContentFallback();
    }

    const articlesData = await articlesResp.json();
    const articles: ArticleMeta[] = articlesData.articles || articlesData;
    const manifestText = await manifestResp.text();

    let knowledgeIndex: KnowledgeIndex | null = null;
    if (knowledgeResp && knowledgeResp.ok) {
      const knowledgeText = await knowledgeResp.text();
      knowledgeIndex = JSON.parse(knowledgeText);
      cacheWrite('knowledge_index.json', knowledgeText);
    }

    let conceptClusters: any = null;
    if (clustersResp && clustersResp.ok) {
      const clustersText = await clustersResp.text();
      conceptClusters = JSON.parse(clustersText);
      cacheWrite('concept_clusters.json', clustersText);
    }

    let syntheses: any = null;
    if (synthesesResp && synthesesResp.ok) {
      const synthesesData = JSON.parse(await synthesesResp.text());
      syntheses = Array.isArray(synthesesData) ? synthesesData : synthesesData?.syntheses ?? null;
      cacheWrite('syntheses.json', JSON.stringify(synthesesData));
    }

    cacheWrite('articles_meta.json', JSON.stringify(articles));
    cacheWrite('manifest.json', manifestText);

    logEvent('content_downloaded', {
      article_count: articles.length,
      knowledge_index: !!knowledgeIndex,
      clusters: !!conceptClusters,
      syntheses: !!syntheses,
      source: 'api',
    });
    return { articles, knowledgeIndex, conceptClusters, syntheses };
  } catch (e) {
    logEvent('content_download_error', { error: String(e) });
    // Try fallback
    return downloadContentFallback();
  }
}

/** Fallback: download from nginx-served JSON files (pre-Phase 4 compatibility). */
async function downloadContentFallback(): Promise<DownloadedContent | null> {
  try {
    if (Platform.OS !== 'web') ensureContentDir();

    const [articlesResp, manifestResp, knowledgeResp, clustersResp, synthesesResp] = await Promise.all([
      fetch(`${CONTENT_BASE}/articles.json`),
      fetch(`${CONTENT_BASE}/manifest.json`),
      fetch(`${CONTENT_BASE}/knowledge_index.json`).catch(() => null),
      fetch(`${CONTENT_BASE}/concept_clusters.json`).catch(() => null),
      fetch(`${CONTENT_BASE}/syntheses.json`).catch(() => null),
    ]);

    if (!articlesResp.ok) return null;

    const fullArticles = await articlesResp.json();
    // Strip content_markdown and sections for in-memory use
    const articles: ArticleMeta[] = fullArticles.map((a: any) => {
      const { content_markdown, sections, ...meta } = a;
      return meta;
    });
    const manifestText = await manifestResp.text();

    let knowledgeIndex: KnowledgeIndex | null = null;
    if (knowledgeResp && knowledgeResp.ok) {
      const knowledgeText = await knowledgeResp.text();
      knowledgeIndex = JSON.parse(knowledgeText);
      cacheWrite('knowledge_index.json', knowledgeText);
    }

    let conceptClusters: any = null;
    if (clustersResp && clustersResp.ok) {
      const clustersText = await clustersResp.text();
      conceptClusters = JSON.parse(clustersText);
      cacheWrite('concept_clusters.json', clustersText);
    }

    let syntheses: any = null;
    if (synthesesResp && synthesesResp.ok) {
      const synthesesData = JSON.parse(await synthesesResp.text());
      syntheses = Array.isArray(synthesesData) ? synthesesData : synthesesData?.syntheses ?? null;
      cacheWrite('syntheses.json', JSON.stringify(synthesesData));
    }

    cacheWrite('articles_meta.json', JSON.stringify(articles));
    cacheWrite('manifest.json', manifestText);

    logEvent('content_downloaded', {
      article_count: articles.length,
      knowledge_index: !!knowledgeIndex,
      clusters: !!conceptClusters,
      syntheses: !!syntheses,
      source: 'fallback_json',
    });
    return { articles, knowledgeIndex, conceptClusters, syntheses };
  } catch (e) {
    logEvent('content_download_fallback_error', { error: String(e) });
    return null;
  }
}

// --- Load cached ---

export async function loadCachedContent(): Promise<DownloadedContent | null> {
  try {
    // Try new meta-only cache first, fall back to old full articles cache
    let articlesRaw = cacheRead('articles_meta.json');
    if (!articlesRaw) {
      // Fall back to old cache (full articles) — strip content fields
      articlesRaw = cacheRead('articles.json');
      if (!articlesRaw) return null;
      const full = JSON.parse(articlesRaw);
      const stripped = full.map((a: any) => {
        const { content_markdown, sections, ...meta } = a;
        return meta;
      });
      articlesRaw = JSON.stringify(stripped);
    }

    const knowledgeRaw = cacheRead('knowledge_index.json');
    const clustersRaw = cacheRead('concept_clusters.json');
    const synthesesRaw = cacheRead('syntheses.json');

    let parsedSyntheses = null;
    if (synthesesRaw) {
      const data = JSON.parse(synthesesRaw);
      parsedSyntheses = Array.isArray(data) ? data : data?.syntheses ?? null;
    }

    return {
      articles: JSON.parse(articlesRaw),
      knowledgeIndex: knowledgeRaw ? JSON.parse(knowledgeRaw) : null,
      conceptClusters: clustersRaw ? JSON.parse(clustersRaw) : null,
      syntheses: parsedSyntheses,
    };
  } catch {
    return null;
  }
}
