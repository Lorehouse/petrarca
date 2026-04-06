# How Historians Think: Research Findings for Petrarca

**Created:** 2026-04-06  
**Purpose:** Research synthesis on historian cognition, expert vs. novice knowledge, and how expert historians approach unfamiliar domains. Directly informs Petrarca's knowledge elicitation and review system design.

---

## 1. The Expert/Expert Study: What Happens When a Historian Doesn't Know the Facts

The most directly relevant study is Wineburg's "Reading Abraham Lincoln: An Expert/Expert Study in the Interpretation of Historical Texts" (*Cognitive Science*, 22(3), 1998, pp. 319-346).

### Setup
Two university historians read the same set of seven primary source documents about Abraham Lincoln and slavery. H1 was a Lincoln/Civil War specialist; H2 was an American historian but not a specialist in this period.

### The specialist (H1): facts as infrastructure
- Knew the sequence of days within specific months of the Lincoln presidency
- Could place the colonization speech in micro-chronological context: Bull Run → Seward's advice to wait for a victory → Antietam
- Knew personal details (Garrison's son editing The Nation, their father-son debate about Reconstruction corruption)
- 61% of his comments were contextual (building biographical, chronological, linguistic, historiographic context)
- Defined the key issues in **4 minutes** — the task's nexus of conflicts between natural law, enacted law, and divine law
- His protocol read like a "profess-aloud" — ready-made interpretations flowing from vast factual knowledge
- Reading time: 165 minutes (more time because more to say, not because of difficulty)

### The non-specialist (H2): disciplinary skills without facts
- Confused almost immediately: "I'm not quite sure about what I do and don't know about Lincoln"
- 18% of comments were self-referential (metacognitive monitoring, tracking confusion) vs. H1's 9%
- Only 31% contextual (vs. H1's 61%) — he simply didn't have the knowledge to build context
- Asked **4.2 questions per document** — a "prolonged exercise in the specification of ignorance"
- 21 instances of specifying ignorance (vs. H1's 7)

### How H2 compensated — "adaptive expertise"
After 43 minutes of "cognitive flailing," H2 built an interpretive framework through an 8-link zigzag backward through the documents:
1. Started from Robinson's religious racism (God ordained slavery)
2. Searched backward: does Lincoln connect God to slavery? No — Lincoln appeals to natural rights, not God
3. Kept tracking this thread through 6 more backward links
4. By the end, arrived at a sophisticated interpretation: Robinson appeals to God to *restrict* human status; Lincoln appeals to God to *connect* the races in common humanity

**H2 ended up at a similar interpretation to where H1 *began*.** But H2 arrived there 40 minutes later, through painful iteration, and with a narrower interpretation than H1's rich, multi-layered reading.

### Two forms of expertise
Wineburg distinguishes:
- **Specific expertise** (H1): "Encyclopedic knowledge of topic and its chronology, down to the sequence of days within a specific month. Extensive knowledge of familial texts as well as positions of competing interpretive schools."
- **Generic expertise** (H2): "Ability to work through confusion, resist the urge to simplify, and regain intellectual footing despite major gaps in knowledge: in short, the ability to develop new knowledge even when lacking many of the requisite tools to do so."

Both are real expertise. Neither is sufficient alone. But H1's specific expertise gave him a massive head start.

### Key quotes from the paper

> "The quintessential expert, as Glaser summarized the research literature in 1984, possessed rich networks of highly-elaborated knowledge... However, in the decade or so since, a series of studies have complicated the image of the smooth and efficient expert."

> "Compared to novices, expert writers took more time, detected more problems, agonized longer over revisions. Similarly, it was historians, not students, who echoed pangs of doubt about their interpretations, second-guessing themselves and appending strings of qualifications. Novices quickly formed interpretations and typically never looked back."

> "Adaptive expertise speaks to the ability to apply, adapt, and otherwise stretch knowledge so that it addresses new situations — often situations in which key knowledge is lacking. Expertise is less the rapid firing and deployment of knowledge than the ability to pick oneself up after a tumble, work through confusion, and reorient oneself to the problem at hand."

### What this means for Petrarca

1. **Facts are the speed multiplier for deep thinking.** H2's disciplinary skills were real but costly — 40 minutes of flailing to reach a position H1 started at. The factual scaffold (dates, figures, events, sequences) lets you start at a sophisticated level.

2. **The "Guns, Germs, and Steel problem" is real.** Going into deep principles without facts produces H2's experience: confusion, uncertainty, narrow interpretation. Not failure — but inefficiency and shallowness.

3. **But disciplinary thinking skills transfer.** H2 wasn't helpless. His ability to specify ignorance, resist simplification, and systematically search for connections is exactly what distinguished him from a novice. These skills — sourcing, contextualization, corroboration — are what Petrarca should eventually help develop, but only after the factual scaffold is in place.

4. **"Specification of ignorance" is a valuable skill to track.** H2's questions accumulated into a coherent search strategy. When the user says "I don't know" or "I wonder if..." during voice elicitation, that's the same skill. The system should value and track these utterances, not just factual recall.

---

## 2. Expert vs. Novice Knowledge Structures — The Full Picture

### Chi, Feltovich & Glaser (1981): The original finding
Experts categorize by deep principles; novices by surface features. But this was studied in physics, where there *are* clean deep principles. History is messier.

### The critical nuance: experts also have vast surface knowledge
The Chi finding is often oversimplified as "experts think in principles, novices think in facts." But the Wineburg Lincoln study shows that expert historians have **both**:
- Deep principles (how to read sources, how to contextualize, how to corroborate)
- AND massive factual knowledge (down to specific days in specific months)

The principles without the facts produce H2's experience — functional but effortful and narrow. The facts without the principles produce what novices do — accept surface reading, miss subtext, form quick judgments without qualification.

### Schneider, Korkel & Weinert (1989): Knowledge trumps ability
In studies with children, domain-specific knowledge about soccer predicted memory performance on soccer-related stories *better than IQ*. Low-IQ soccer experts outperformed high-IQ soccer novices. The knowledge organization — not general intelligence — is what drives comprehension and retention.

### Recht & Leslie (1988): Knowledge trumps reading skill
High-knowledge poor readers recalled more text content than low-knowledge good readers. Knowledge structure trumps reading skill for comprehension and retention.

**Implication:** The factual scaffold Petrarca builds through review and elicitation IS the system's primary value. More factual knowledge → better comprehension of everything else read in that domain.

---

## 3. Historical Thinking: The Four Strategies

Wineburg's earlier work (1991, *Historical Thinking and Other Unnatural Acts*) identified four heuristics that expert historians use but novices typically don't:

1. **Sourcing**: Who created this document? What's their perspective, position, motivation? Historians check attribution *before* engaging with content. Students dive straight in.

2. **Contextualization**: When and where was this created? What else was happening? H1 placed Lincoln's colonization speech in the context of Union defeats, the Emancipation Proclamation timing, Antietam.

3. **Corroboration**: How does this compare with other accounts? Historians validate by finding the same claim in different sources. Novices never use this heuristic.

4. **Close reading**: What claims does the text actually make? What language choices reveal? H2's careful attention to Lincoln's use of "perhaps" and "physical difference" — parsing exact words for implications.

### Seixas' "Big Six" (2013)
Expanded framework for historical thinking competencies, each with graduated benchmarks:
1. **Historical significance** — Why does this matter?
2. **Primary source evidence** — How do we know?
3. **Continuity and change** — What stayed the same, what changed?
4. **Cause and consequence** — Why did it happen? What followed?
5. **Historical perspectives** — How did people at the time see this?
6. **Ethical dimensions** — How do we judge past actions?

### Andrews & Burke's "Five C's" (2007)
The AHA framework: Change over time, Causality, Context, Contingency, Complexity. These are "habits of mind" that transfer across any historical domain.

---

## 4. How an Expert Historian Approaches a New Domain

Based on synthesizing the Wineburg Lincoln study, the adaptive expertise literature, and the historical thinking frameworks:

### What transfers (disciplinary skills)
- The sourcing heuristic (always check who wrote this and why)
- The ability to specify ignorance productively (H2's linked questions)
- Resistance to premature simplification
- The habit of contextualization (even if the specific context must be learned)
- Corroboration instinct (compare across sources)
- Understanding that words have histories and multiple interpretations

### What doesn't transfer (domain content)
- Specific chronological sequences
- Key figures, their relationships, their positions
- The specific debates and interpretive schools within that domain
- Biographical context for primary actors
- Linguistic context (period-specific terminology)

### How they'd approach Edo Japan from scratch
Based on the Wineburg patterns:
1. **Establish temporal scaffolding** — When does this period start/end? What comes before/after? What's happening simultaneously in Europe, China, Korea?
2. **Build a cast of characters** — Key figures (Tokugawa Ieyasu), their roles, relationships, factional alignments
3. **Map the geography** — Where is power centered? What are the key cities/regions? How does geography shape politics?
4. **Source the sources** — What kind of evidence survives? Who wrote about Edo Japan and when? How reliable are different accounts?
5. **Resist premature frameworks** — Don't immediately apply "feudalism" or "absolutism" from European history. Track what's genuinely similar and what's superficially similar.
6. **Cross-reference constantly** — "This reminds me of the Venetian system" or "This is analogous to the Roman senatorial class" — but with awareness that analogies can mislead
7. **Specify ignorance** — Explicitly track "I don't know whether..." questions, which become research targets

A layperson would: read a popular overview, absorb the gist ("Japan was isolated for 250 years under the Shoguns"), forget the specifics within a month. The factual scaffold never gets built.

---

## 5. The Free Recall Hierarchy — Why Voice Elicitation Is the Right Mechanism

### Karpicke & Blunt (2011, Science)
Retrieval practice beats concept mapping, even on concept-map tests. The mechanism: retrieval activates the entire semantic network around a concept, not just the target memory.

### The hierarchy
From the beyond-flashcards research:
- **Free recall** (open-ended: "What do you remember about X?") promotes both relational AND item-specific processing
- **Cued recall** (prompted: "What was the argument about X?") promotes only item-specific processing
- **Recognition** (multiple choice) promotes only familiarity, not recollection

Free recall "enhances relational processing — the kind of processing that supports conceptual understanding." Cued recall "does not appear to enhance conceptual organization and under some conditions can disrupt it."

### Elaborative retrieval hypothesis (Carpenter, 2009)
During retrieval, not just the target but also semantically related information is activated. Testing concept A can strengthen memory for *related, untested concept B* — but only if they're well-integrated. This is why Petrarca's connected curriculum structure matters: reviewing one node should strengthen related nodes through spreading activation.

### Successive relearning (Rawson & Dunlosky, 2022)
Three spaced relearning sessions may be sufficient for maximal benefit. Retention at 1 month: 68% with successive relearning vs. 11% baseline. Extra effort on initial criterion doesn't persist — additional spaced encounters matter more than deep drilling on first contact.

---

## 6. Fuzzy-Trace Theory: Why Different Knowledge Types Need Different Scheduling

Brainerd & Reyna's theory: two parallel memory traces encoded for every experience:
- **Verbatim traces** (exact facts, dates, names): Decay within days-to-a-week
- **Gist traces** (frameworks, arguments, "so what"): Persist weeks-to-months

Without reinforcement:
- 1 week: Recall main arguments + key examples
- 1 month: Thesis clear, arguments fuzzy, examples gone
- 3 months: Only the "big idea"
- 1 year: Vague sense of "having read something about X"

A single well-timed reconnection can restore the full gist framework. Gist traces can be reactivated even after long delays.

**Critical for scheduling**: Dates/names need short intervals and frequent review. Frameworks/connections need longer intervals but survive well on their own. The current system treats all knowledge types identically.

---

## 7. Knowledge Resonance and Natural Spacing

### Schema theory / mPFC resonance detection
The medial prefrontal cortex functions as a "resonance detector" — recognizes when new information fits existing schemas. When congruence is detected, new information integrates directly into the existing knowledge structure, and the old schema is strengthened simultaneously.

### Natural spacing > artificial SRS
Reading new material that touches on previously-read concepts creates "natural spacing" with advantages over flashcard SRS:
- Novel context (more retrieval cues)
- Incidental retrieval (recognition triggers recall)
- Elaborative connection (reader naturally compares perspectives)
- Intrinsic motivation (new article is interesting, not a chore)

Transfer-appropriate processing: the best retrieval cue for something encoded during reading is *another reading context*, not a flashcard.

### Retrieval-induced facilitation (not just forgetting)
Anderson, Bjork & Bjork (1994) showed retrieving some items can impair recall of related items. But Chan et al. (2006) found this reverses for well-integrated knowledge: "High integration + delay = facilitation rather than forgetting." The connected curriculum structure protects against retrieval-induced forgetting.

---

## 8. Measuring Knowledge Growth Longitudinally

### Pathfinder Networks (Goldsmith et al., 1991)
Similarity between student's knowledge network and expert's network correlates with exam performance at r = .74 — the single best predictor. Three metrics: PRX (proximity), GTD (graph-theoretic distance), PFC (Pathfinder closeness).

The curriculum graph IS the expert network. Voice transcript analysis can derive the learner's network from: which nodes they mention, which connections they articulate, which nodes they demonstrate understanding of.

### SNAFU (Zemla & Austerweil, 2026)
Python tool for estimating semantic networks from free recall. Six methods including U-INVITE (maximum likelihood censored random walk). Install: `pip install git+https://github.com/AusterweilLab/snafu-py`. Adaptation needed: extract entities from voice transcripts in recall order, treat as recall "items."

### Multi-trial free recall (Adroer et al., 2024)
Test-retest reliability ~0.8 for repeated free recall. Strategies stabilize after ~5 trials. No ceiling effects reported. Key metrics: overall recall accuracy, serial position effects, temporal organization (contiguity), semantic clustering.

### Voice sweep protocol (proposed in knowledge-systems-deep-dive.md)
Monthly domain-wide assessment: "Tell me the history of Sicily — everything you remember." Five measurement dimensions:
1. **Coverage** — fraction of curriculum nodes mentioned
2. **Depth** — average knowledge level of mentioned nodes
3. **Connectivity** — connections articulated between nodes
4. **Accuracy** — FActScore-style claim verification
5. **Organization** — expert-like clustering vs. random recall

This is genuinely novel — no existing system does repeated domain-level voice free recall as a longitudinal growth metric.

---

## References

- Wineburg, S. (1998). "Reading Abraham Lincoln: An Expert/Expert Study in the Interpretation of Historical Texts." *Cognitive Science*, 22(3), 319-346.
- Wineburg, S. (2001). *Historical Thinking and Other Unnatural Acts*. Temple University Press.
- Chi, M., Feltovich, P., & Glaser, R. (1981). "Categorization and Representation of Physics Problems by Experts and Novices." *Cognitive Science*, 5, 121-152.
- Seixas, P. (2013). *The Big Six Historical Thinking Concepts*. Nelson Education.
- Andrews, T. & Burke, F. (2007). "What Does It Mean to Think Historically?" *Perspectives on History* (AHA).
- Karpicke, J. & Blunt, J. (2011). "Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping." *Science*, 331, 772-775.
- Carpenter, S. (2009). "Cue strength as a moderator of the testing effect." *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 35(6), 1563-1569.
- Rawson, K. & Dunlosky, J. (2022). "Successive relearning." *Journal of Experimental Psychology: General*.
- Brainerd, C. & Reyna, V. Fuzzy-Trace Theory.
- Goldsmith, T., Johnson, P., & Acton, W. (1991). "Assessing Structural Knowledge." *Journal of Educational Psychology*, 83(1), 88-96.
- Zemla, J. & Austerweil, J. (2026). "Estimating semantic networks from free recall." *Memory & Cognition*.
- Recht, D. & Leslie, L. (1988). "Effect of Prior Knowledge on Good and Poor Readers' Memory of Text." *Journal of Educational Psychology*, 80(1), 16-20.
- Schneider, W., Korkel, J., & Weinert, F. (1989). "Domain-Specific Knowledge and Memory Performance." *Journal of Educational Psychology*, 81(3), 306-312.
