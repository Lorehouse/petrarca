# Petrarca — Master Ideas File

> This file tracks ALL ideas for the project. Never delete ideas. Mark as [DEFERRED], [REJECTED], or [DONE] with reasoning. Every agent should add new ideas discovered during work.

---

## Hypothesis Annotation Integration (2026-04-07)
Source: History+PKM research (alif/research/petrarca-integration-plan.html)
- Sync user's Hypothesis annotations via `GET /api/search` (incremental, `search_after` cursor, no rate limits)
- Highlighted passages → `atomic_claims` with `claim_type='user_highlight'` — higher weight than LLM-extracted claims (user chose what matters)
- Annotation count per article = reading depth signal for feed ranking
- Tag → entity/curriculum node linking (user tags "Byzantine Empire" → upgrade knowledge state)
- Auto-import annotated URLs not yet in Petrarca's DB
- ~370 lines, 1-2 sessions. Env: `HYPOTHESIS_API_KEY`, `HYPOTHESIS_USERNAME`

## Entity Extraction Prompt Engineering (2026-04-07)
Source: Shawn Graham's steamroller, kg-hybrid, claude_antiquities_extractor_skill repos
- **Constrained relationship types**: ~15 predicates (RULED, CONQUERED, FOUNDED, INFLUENCED, PART_OF, LOCATED_IN, CAUSED, etc.) instead of free-form descriptions. Produces queryable graphs.
- **Canonical IDs**: `roger_ii_sicily`, `palermo_sicily`, `norman_conquest_sicily_1061` — stable across articles, better than case-insensitive name matching
- **Mentions array**: Track all text variants per entity (`["Roger II", "Roger", "the Norman king"]`) for better dedup
- **Prescribed extraction workflow**: Step-by-step in the prompt (identify → canonicalize → collect mentions → find relationships) vs single "extract entities" instruction
- Prompt-only change, zero dependencies, 1 session

## Zotero Translation Server as Metadata Sidecar (2026-04-07)
Source: Digital Scholar / Sean Takats
- `docker pull zotero/translation-server` (port 1969), `POST /web` with URL → structured JSON
- **Complements** trafilatura (metadata only, no body text). 600+ community-maintained site-specific extractors.
- Gives: `itemType` (blogPost vs journalArticle vs newspaperArticle), structured `creators[]` (first/last/role), `abstractNote`, `DOI`, `publicationTitle`, `language`, `tags[]`
- Trial: run on 50 articles, measure metadata delta vs trafilatura alone. Deploy if >30% hit rate.
- Notable gap: does NOT parse JSON-LD (`<script type="application/ld+json">`)

## Discourser-style Semantic Vectors (2026-04-07)
Source: Shawn Graham's discourser repo
- Define custom semantic dimensions via positive/negative term sets, project articles onto them
- Example axes: `primary_vs_secondary` sources, `military_vs_cultural`, `technical_vs_narrative`
- Three methods: orthogonal projection (best), weighted difference (fast), PCA axis (data-driven)
- Could distinguish "same topic, different angle" from "same topic, same angle" in novelty detection
- Already have MiniLM via limbic. Research spike: 2 hours to test on 100 articles.

## Dual-Model Entity Verification (2026-04-07)
Source: Shawn Graham's steamroller (results_evaluator.py)
- After entity extraction (Gemini Flash), run verification pass (Claude Haiku via `claude -p`, free)
- Checks: is each entity actually in the article? Are canonical IDs consistent? Are relationships supported by text?
- Catches hallucinated entities that pollute the knowledge graph
- Do this only if entity quality remains poor after prompt engineering changes above

## "Provocation Engine" — What's Missing (2026-04-07)
Source: Shawn Graham's archivelens repo
- Instead of just "what's new in this article?", ask "what's conspicuously absent from my reading history?"
- An LLM reviews the user's knowledge graph and identifies gaps, silences, or blind spots
- Could surface as "You've read extensively about Norman Sicily but nothing about the Arab period that preceded it"
- Powerful complement to novelty detection — novelty finds new things, provocation finds missing things

## Knowledge Commons (KCWorks) as Article Source (2026-04-07)
Source: MESH-Research / Michigan State
- REST API at `works.hcommons.org` for searching humanities scholarship
- OAI-PMH for bulk harvesting. DataCite metadata schema.
- `kcworks-nlp-tools` repo has NLP tools for processing article content in chunks
- Could be a curated source of high-quality humanities articles for auto-ingest

## Luhmann Archive as Test Corpus (2026-04-07)
Source: Johannes Schmidt, Bielefeld University
- Public JSON API to 90,000 cross-referenced Zettelkasten cards
- TEI P5 data model with named entity markup and inter-card cross-references
- Luhmann's branching numbering (1, 1a, 1b, 1a1...) = implicit hierarchical knowledge graph
- Interesting test corpus for entity linking against real scholarly knowledge structures

## RAKE Keyword Extraction (2026-04-07)
Source: William Turkel (github.com/williamjturkel/RAKE)
- Rapid Automatic Keyword Extraction — no training data, no LLM cost
- Uses stopword-delimited candidate phrases ranked by co-occurrence statistics
- Could supplement or replace LLM-based keyword extraction for simple/cheap cases
- Useful as a fast pre-filter before expensive LLM entity extraction

## Multi-Pass Entity Resolution (2026-04-07)
Source: Cameron Blevins' us-post-offices repo (github.com/cblevins/us-post-offices)
- Three-phase matching: exact → targeted string modification → fuzzy Levenshtein
- Applied to 166,140 historical post offices — proven at scale
- Pattern directly applicable to entity deduplication across articles
- Currently Petrarca does case-insensitive name matching — this would be more robust

## NewSyntopicon-style Cross-Text Idea Linking (2026-04-07)
Source: github.com/sajjad2881/NewSyntopicon (starred by Chris Aldrich)
- Digital recreation of Mortimer Adler's Syntopicon — links ideas across great books
- Each idea is a node in a graph showing how concepts develop across texts
- Very aligned with Petrarca's curriculum-based knowledge modeling
- Could inform how curriculum nodes link to specific passages across books/articles

## PressForward Image Fallback Chain (2026-04-07)
Source: PressForward WordPress plugin
- Featured image cascade: OG image → `link[rel=image_src]` → Twitter image → first `<img>` with width > 300
- Useful if Petrarca needs article thumbnails/featured images in the feed
- Simple to add to trafilatura post-processing

## Shawn Graham — Potential Collaborator (2026-04-07)
- Professor of Digital Humanities, Carleton University (Ottawa)
- Has 6 repos directly relevant to Petrarca's knowledge graph and entity extraction
- Teaches courses using Obsidian, builds text-to-KG pipelines, studies novelty in corpora
- Contact: shawn.graham@carleton.ca, https://electricarchaeology.ca
- Also: Chris Aldrich (boffosocko.com) starred Stian's hypothesis-to-bullet repo — aware of his work
