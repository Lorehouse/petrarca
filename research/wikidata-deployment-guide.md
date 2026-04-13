# Wikidata Entity Resolution — Deployment Guide

Step-by-step deployment of PR 3 (branch `sh/wikidata-backfill`, [PR #2](https://github.com/houshuang/petrarca/pull/2)) to production.

This guide assumes you're running from `~/src/petrarca` on the laptop, and `alif` is the Hetzner production server.

## Pre-flight

Everything required on alif is already staged. Verify:

```bash
# Schema migration already applied (from session 70 — safe to re-run).
ssh alif "python3 /tmp/migrate_wikidata_schema.py /opt/petrarca/data/petrarca.db 2>&1 | head -10"
# Expected: all "ok: ..." lines. If the file was cleaned up, scp it again.

# limbic suite green on laptop.
cd ~/src/limbic && .venv/bin/python -m pytest tests/ -q
# Expected: 462 passed, 12 skipped.

# Petrarca tests green (including the 45 new ones).
cd ~/src/petrarca && python3 -m pytest scripts/tests/ -q
# Expected: 66 passed, 9 skipped.
```

## Step 1: Review + merge PR

Open [petrarca#2](https://github.com/houshuang/petrarca/pull/2). Sanity-check:

- Nine commits, ~3,500 lines added under `scripts/` + `research/session-changelog.md`
- Pre-existing dirty files in repo (`app/lib/voice-upload-service.ts`, etc.) are NOT included

Merge when ready. I used a merge commit for clarity; a squash also works since all commits are on-topic.

## Step 2: Deploy `research-server.py` to alif

The server file changed to add the admin endpoints. Use the normal deploy flow — whatever rsync+restart pattern you use for research-server.py. After deploy, smoke test:

```bash
curl -s https://<your-petrarca-host>:8090/admin/entity-queue-data?limit=1 | head -c 200
# Expected: JSON with items + counts (may be empty on first run)
```

## Step 3: Run the backfill

```bash
# On alif. ~10 min, ~$0.05, resumable via Ctrl-C.
ssh alif "cd /opt/petrarca && /opt/limbic/.venv/bin/python scripts/backfill_wikidata.py --pass all 2>&1 | tee /tmp/backfill-$(date +%Y%m%d).log"
```

Expected final output:

```
coverage: ~510/591 resolved (~86%), ~80 in review queue
```

If you interrupt, re-run the same command — `BatchProcessor` picks up where it left off via `/opt/petrarca/data/wikidata_backfill_state.db`.

## Step 4: Auto-merge safe duplicates

```bash
# Preview first:
ssh alif "cd /opt/petrarca && python3 scripts/merge_entity_dupes.py --list"

# Then apply:
ssh alif "cd /opt/petrarca && python3 scripts/merge_entity_dupes.py --apply --safe-only"
```

This removes ~20 duplicate `shared_entities` rows and re-parents their data to the canonical owner. Audit trail in `/opt/petrarca/data/merge_audit.jsonl`.

The 2 `REVIEW` pairs (`ancient_greece ↔ greece`, `abbasid_caliphate ↔ arab_caliphates`) stay in the queue — they're resolver conflations, not real duplicates. Triage via the review UI.

## Step 5: Clean up stale audit rows (optional)

If this is the first backfill, pass-1 rows may have `superseded_by=NULL` even though later passes superseded them. Cosmetic, but:

```bash
ssh alif "cd /opt/petrarca && python3 scripts/cleanup_stale_resolutions.py"
```

## Step 6: Triage the review queue

Visit `https://<your-petrarca-host>:8090/admin/entity-queue`.

Expected state:
- ~80 items (mostly `period`-type curriculum-internal labels like "Aragonese Rule")
- 2 `needs_review` dedup candidates (Ancient Greece / Abbasid)
- 0 resolved items in the current filter (they're not in the queue)

For each row you care about: expand → pick a candidate → click "Commit". For the `needs_review` dedup rows: click "load merge candidate" → "Merge X → Y".

Many of the remaining items are genuinely absent from Wikidata (curriculum categories) and can stay un-resolved indefinitely — they just won't have canonical identities.

## Rollback

Everything is reversible. To roll back to pre-PR-3 state:

```sql
-- On alif, after SSH into sqlite3 /opt/petrarca/data/petrarca.db
UPDATE shared_entities SET wikidata_qid = NULL;
DELETE FROM entity_resolutions;
DELETE FROM entity_external_ids;
```

The schema columns stay (harmless) and you can re-run the backfill anytime.

If a merge went wrong: the duplicate entity is gone but the child rows moved to canonical. To restore, you'd replay from `/opt/petrarca/data/merge_audit.jsonl` (each line has the source/target + table moves). No script for this yet — I'd just restore from a DB backup if it matters.

## Validation checkpoints

After backfill, verify:

```bash
ssh alif 'sqlite3 /opt/petrarca/data/petrarca.db "
  SELECT \"entities\" AS metric, COUNT(*) FROM shared_entities
  UNION ALL SELECT \"committed QIDs\", COUNT(*) FROM shared_entities WHERE wikidata_qid IS NOT NULL
  UNION ALL SELECT \"external IDs\", COUNT(*) FROM entity_external_ids
  UNION ALL SELECT \"audit rows\", COUNT(*) FROM entity_resolutions
  UNION ALL SELECT \"active audit rows\", COUNT(*) FROM entity_resolutions WHERE superseded_by IS NULL
"'
```

Expected (order of magnitude):
- entities ≈ 591 before merges, ~570 after
- committed QIDs ≈ 510-515
- external IDs ≈ 1,800-2,000
- audit rows ≈ 1,500-2,000 (including superseded)
- active audit rows ≈ entity count

## What's next (PR 4 — not in this deployment)

After this deployment settles, the next step is wiring the resolver into
`process_voice_capture()` so live voice transcripts get QIDs automatically.
The Rollo transcript `vt_1776097010_8381` is the smoke-test target — that
transcript (which triggered this entire project) currently has 0
knowledge_items because the old lexical matching failed.

`scripts/reprocess_voice_with_qids.py` already proves the pattern works:
it resolves 11 of 13 entities in the Rollo transcript correctly via the
full resolver pipeline. PR 4 proper will replace `process_voice_capture`'s
lexical candidate construction with the resolver call.
