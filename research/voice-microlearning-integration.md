# Voice → Microlearning Integration Design

*April 2026*

## The Gap

Voice memos produce rich learning signals. Microlearning needs research queries. They're not connected.

| Voice output | Currently goes to | Should also trigger |
|---|---|---|
| Elicitation **wonderings** ("I wonder...") | Stored in results JSON | Microlearning research |
| Elicitation **research_triggers** | Stored in results JSON | Microlearning research |
| Elicitation **missed** critical facts | Feedback text only | Targeted microlearning |
| Review memo **questions** | `voice_followup` review items | Microlearning research |
| Feedback capture `research_request` | Feedback table | Microlearning research |
| Book voice note **questions** | Book capture record | Microlearning (if question detected) |

## Design Principles

1. **Automatic for explicit signals**: "I wonder why Constantinople was chosen" is unambiguously a research query. Don't make the user tap anything — just research it.
2. **Automatic with guardrails for inferred signals**: Missed facts → generate targeted microlearning, but cap at 1-2 per session to avoid flooding.
3. **Always show feedback**: Every triggered research must show a toast/indicator so the user knows their voice input produced something.
4. **Curriculum context travels with the query**: The voice memo happened in context of a specific node/domain. Pass that through to microlearning so the research is anchored.

## Integration Points (3 server-side changes)

### 1. Voice Elicitation → Microlearning

**Where**: `run_voice_elicitation()` in `review_engine.py`

The elicitation already extracts `wonderings[]` and `research_triggers[{question}]`. After the extraction:

```python
# After LLM extraction, trigger microlearning for wonderings + research_triggers
triggered_cards = []

# Explicit wonderings → always trigger
for wondering in result.get('wonderings', []):
    card = create_microlearning_request(
        query=wondering,
        source_item_id=None,
        source_node_id=node_id,
        source_domain=domain_id,
        conn=conn,
    )
    triggered_cards.append(card)

# Research triggers → always trigger
for trigger in result.get('research_triggers', []):
    query = trigger.get('question', '') if isinstance(trigger, dict) else str(trigger)
    if query:
        card = create_microlearning_request(
            query=query,
            source_item_id=None,
            source_node_id=node_id,
            source_domain=domain_id,
            conn=conn,
        )
        triggered_cards.append(card)

# Missed critical facts → generate 1 targeted microlearning (max)
missed = result.get('missed', [])
if missed and len(missed) >= 1:
    most_important = missed[0]  # already priority-ordered by LLM
    card = create_microlearning_request(
        query=f"Why is this important: {most_important}",
        source_item_id=None,
        source_node_id=node_id,
        source_domain=domain_id,
        conn=conn,
    )
    triggered_cards.append(card)

# Add to response so client can show feedback
result['microlearning_triggered'] = [
    {'id': c['id'], 'query': c['query']} for c in triggered_cards
]
```

**Client change**: Show toast(s) for each triggered card. The elicitation screen already shows rich feedback — add a "Researching X..." line for each triggered query.

### 2. Review Voice Memo → Microlearning

**Where**: `process_voice_memo()` in `review_engine.py`

The memo extraction produces `questions[]`. Currently these become `voice_followup` review items (simple recall questions). But questions like "why did he choose Byzantium?" deserve research, not just a review card.

```python
# After extraction, check for research-worthy questions
triggered_cards = []
for question in result.get('questions', []):
    # Only trigger microlearning for WHY/HOW questions, not factual recall
    q_lower = question.lower()
    if any(w in q_lower for w in ['why', 'how', 'what caused', 'what happened',
                                   'connection between', 'relationship',
                                   'compared to', 'different from']):
        card = create_microlearning_request(
            query=question,
            source_item_id=item_id,
            source_node_id=node_id,
            source_domain=domain_id,
            conn=conn,
        )
        triggered_cards.append(card)

# Cap at 2 per voice memo to avoid flooding
triggered_cards = triggered_cards[:2]
result['microlearning_triggered'] = [
    {'id': c['id'], 'query': c['query']} for c in triggered_cards
]
```

**Client change**: After recording and getting the response, show "Researching: [question]" toast for each triggered card.

### 3. Feedback Capture `research_request` → Microlearning

**Where**: `_route_and_enrich_feedback()` in `research-server.py`

When voice routing classifies intent as `research_request`, the cleaned_text IS the research query.

```python
if routing.get('intent') == 'research_request':
    from review_engine import create_microlearning_request
    from db import get_connection
    conn = get_connection()
    
    # Extract curriculum context from feedback context if available
    context = feedback.get('context', {})
    source_domain = context.get('domain', '')
    source_node = context.get('node_id', '')
    
    card = create_microlearning_request(
        query=routing['cleaned_text'],
        source_node_id=source_node,
        source_domain=source_domain,
        conn=conn,
    )
    conn.close()
    
    # Store the card reference in the feedback record
    feedback['microlearning_card_id'] = card['id']
```

**Client change**: The feedback capture already shows a success toast. Extend it: "Feedback sent + researching your question."

## Response Shape Changes

### Voice Elicitation Response (extended)
```json
{
  "captured": [...],
  "missed": [...],
  "interesting": [...],
  "wonderings": [...],
  "research_triggers": [...],
  "suggested_score": "partly",
  "coverage_pct": 60,
  "feedback_summary": "...",
  "microlearning_triggered": [
    {"id": "ml_1234_5678", "query": "Why did Constantinople become the capital?"},
    {"id": "ml_1234_9012", "query": "How did the Edict of Milan change daily life?"}
  ]
}
```

### Review Voice Memo Response (extended)
```json
{
  "transcript": "...",
  "remembered": [...],
  "questions": [...],
  "connections": [...],
  "suggested_score": "partly",
  "follow_ups_created": [...],
  "microlearning_triggered": [
    {"id": "ml_1234_3456", "query": "Why did Constantine choose Byzantium?"}
  ]
}
```

## Client-Side UX

### Review Screen Toast Stack
When a voice memo triggers microlearning, show stacked toasts:

```
┌──────────────────────────────────────┐
│ ⟳ Researching: Why did Constantine   │
│   choose Byzantium?                  │
├──────────────────────────────────────┤
│ ⟳ Researching: How did the Edict of │
│   Milan change daily life?           │
└──────────────────────────────────────┘
```

These use the same `researchingQuery` toast pattern already built for the "Go deeper" buttons. Extend to support multiple simultaneous toasts.

### Voice Elicitation Screen
After showing the recall analysis (captured/missed/coverage), add a section:

```
✦ Your questions are being researched
  › Why did Constantinople become the capital?
  › How did the Edict of Milan affect...?
  
  These will appear as research cards in your next review session.
```

### Feedback Capture
After "Feedback sent" toast, append: "+ researching your question" when intent was `research_request`.

## What NOT to auto-trigger

- **Book voice notes**: Too unstructured. The user is narrating thoughts while reading — not every sentence is a research query. Better to let them manually tap "Research this" on extracted ideas.
- **General notes**: intent=`general_note` is a catch-all. Don't trigger microlearning for "remind me to buy milk."
- **Article feedback**: intent=`article_feedback` is about the article UX, not a research question.
- **Low-confidence routing**: If the voice routing confidence < 0.7, don't auto-trigger.

## Deduplication

Voice memos might produce duplicate or overlapping queries. Before creating a microlearning card:

```python
def _is_duplicate_query(query: str, conn) -> bool:
    """Check if a very similar microlearning query exists from the last 24h."""
    recent = conn.execute(
        "SELECT query FROM microlearning_cards WHERE created_at > ? LIMIT 50",
        (int(time.time() * 1000) - 24 * 3600 * 1000,)
    ).fetchall()
    # Simple substring check — could use embeddings for semantic dedup
    q_lower = query.lower()
    for r in recent:
        existing = r[0].lower()
        if q_lower in existing or existing in q_lower:
            return True
        # Check word overlap
        q_words = set(q_lower.split())
        e_words = set(existing.split())
        overlap = len(q_words & e_words) / max(len(q_words), 1)
        if overlap > 0.7:
            return True
    return False
```

## Rate Limiting

Cap microlearning triggers per session to prevent flooding:
- **Voice elicitation**: max 3 cards per elicitation session (wonderings + triggers + 1 missed)
- **Review voice memo**: max 2 cards per memo
- **Feedback**: max 1 card per feedback submission
- **Global**: max 10 microlearning cards created per hour (across all sources)

## Implementation Order

1. **Server: Wire voice elicitation → microlearning** (highest value — wonderings are the purest signal)
2. **Server: Wire review voice memo → microlearning** (questions during review are highly contextual)
3. **Server: Wire feedback research_request → microlearning** (simple routing change)
4. **Client: Multiple research toast support** (extend existing `researchingQuery` to array)
5. **Client: Voice elicitation results show "researching" section**
6. **Server: Dedup check before creating cards**
7. **Server: Rate limiting**

## Metrics to Track

- `voice_microlearning_triggered` — count per source (elicitation/memo/feedback)
- `voice_microlearning_completed` — how many actually complete research
- `voice_microlearning_reviewed` — how many get reviewed by user
- `voice_microlearning_score` — knew/partly/missed distribution (vs regular microlearning)
- `voice_to_card_latency` — time from voice recording to completed microlearning card

Compare voice-triggered microlearning scores against manually-triggered (from "Go deeper" buttons) to see if voice signals produce more relevant research.
