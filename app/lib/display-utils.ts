/** Shared display utilities */

/** Safely format a date value that may be epoch-ms, ISO string, or nullish.
 *  Handles the mixed date formats the server sends. */
export function safeDate(v: unknown, fallback = '—'): string {
  if (v == null) return fallback;
  const d = new Date(typeof v === 'number' ? v : Date.parse(v as string));
  if (isNaN(d.getTime())) return fallback;
  return d.toLocaleDateString();
}

export function getDisplayTitle(article: { title: string; one_line_summary: string }): string {
  if (/^Thread by @/i.test(article.title) && article.one_line_summary && article.one_line_summary !== '[dry run]') {
    return article.one_line_summary;
  }
  return article.title;
}

/** Normalize topic key: hyphens→spaces, lowercase, collapse whitespace */
export function normalizeTopic(topic: string): string {
  return topic.replace(/-/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
}

/** Display-friendly topic: "medieval-history" → "Medieval History" */
export function displayTopic(topic: string): string {
  return normalizeTopic(topic).replace(/\b\w/g, c => c.toUpperCase());
}
