# Beyond Flashcards: Keeping Book Knowledge Alive Without Traditional SRS

Research on alternatives to Anki-style spaced repetition for conceptual knowledge from physical book reading. Focused on mechanisms that could be implemented in Petrarca.

---

## 1. Why Traditional SRS Fails for Conceptual Knowledge

### The Core Problem

Traditional SRS (Anki, SuperMemo flashcards) reinforces single prompt-response links. This works for discrete facts (vocabulary, dates, formulas) but breaks down for the kind of knowledge gained from reading nonfiction books: arguments, conceptual frameworks, causal chains, interpretive lenses.

**Scott H. Young's critique** ([source](https://www.scotthyoung.com/blog/2014/11/07/srs-for-concepts/)): SRS is "fantastic for discrete pieces of information" but "struggles with conceptual understanding." The fundamental limitation is that SRS reinforces isolated links between a prompt and a response, while conceptual understanding requires understanding how ideas relate to and depend on each other.

**LessWrong critique** ([source](https://www.lesswrong.com/posts/As9E3HfgED2zkTAfB/a-vote-against-spaced-repetition)): After using SRS "religiously for 3 years," users report insufficient returns on time investment for complex material. The card-creation burden is enormous for conceptual material, and cards tend to either be too simple (missing the concept) or too complex (effectively re-reading a paragraph).

**Anki's structural gap**: Anki does not support card dependencies -- it cannot ensure you've mastered prerequisite concepts before advancing to dependent material. Knowledge graphs, argument structures, and conceptual hierarchies cannot be represented.

### What SRS Gets Right (and What to Preserve)

The spacing effect itself is one of the most robust findings in cognitive psychology. The problem isn't spacing -- it's the flashcard format. Key elements to preserve:
- **Expanding intervals** between re-encounters with material
- **Active engagement** at the moment of re-encounter (not passive re-reading)
- **Tracking** which knowledge is fading and which is reinforced

### Andy Matuschak's Attempt to Bridge the Gap

Matuschak's "mnemonic medium" ([source](https://notes.andymatuschak.org/Mnemonic_medium)) embeds SRS prompts directly into narrative prose (Quantum Country). He argues SRS *can* develop conceptual understanding ([source](https://notes.andymatuschak.org/z9Vi7YVx7NzxU2wawNgsJbk)) if prompts are carefully written to test connections, implications, causes, and consequences rather than isolated facts.

**Quantum Country data** ([source](https://notes.andymatuschak.org/z93QR51f6HAUPLVDxE6KT1T)): After 30 minutes of practice, most readers remember answers to almost all 112 questions across intervals of 2+ weeks. After 1.5 hours of practice, retention holds for 9+ weeks. This shows exponential returns -- but requires carefully authored conceptual prompts, which is labor-intensive.

**Key insight for Petrarca**: The mnemonic medium works because it tests conceptual relationships, not facts. Petrarca could generate conceptual prompts from book captures using LLMs, but there may be even better approaches that don't require the flashcard format at all.

---

## 2. Elaborative Retrieval vs. Rote Retrieval

### The Karpicke & Blunt Landmark Study

Karpicke & Blunt (2011, *Science*) ([source](https://www.science.org/doi/10.1126/science.1199327)) demonstrated that retrieval practice produces more learning than elaborative studying with concept mapping. Crucially, the advantage held even when the test required creating concept maps -- suggesting retrieval itself (not the study format) is the active ingredient.

### The Mechanism Difference

- **Rote retrieval**: Recall a specific fact when given a cue. Strengthens a single memory trace.
- **Elaborative retrieval**: Reconstruct knowledge from context -- explain relationships, generate implications, connect to prior knowledge. Strengthens the entire network around a concept.

During elaboration, subjects build detailed representations by enriching encoded features. During retrieval, subjects use cues to *reconstruct* knowledge from context. The reconstruction process itself strengthens memory more than passive re-exposure.

### Free Recall vs. Cued Recall vs. Recognition

Research on testing formats reveals a hierarchy ([source](https://www.sciencedirect.com/science/article/abs/pii/S0749596X19300026)):

- **Free recall** (open-ended: "What do you remember about X?") promotes both relational and item-specific processing
- **Cued recall** (prompted: "What was the author's argument about X?") promotes primarily item-specific processing
- **Recognition** (multiple choice, yes/no) promotes only familiarity, not recollection

Free recall enhances relational processing -- the kind of processing that supports conceptual understanding. Cued recall and recognition "do not appear to enhance conceptual organization and under some conditions can disrupt it."

**Implication for Petrarca**: When resurfacing book knowledge, prefer open-ended prompts ("What was Pirenne's thesis about the Mediterranean?") over recognition-style prompts ("Did Pirenne argue that X or Y?"). The harder format produces better retention.

---

## 3. The Spacing Effect Without Flashcards

### What Triggers Spacing Benefits

The spacing effect does not require flashcards. It requires **repeated encounters with material at expanding intervals**, ideally with some form of retrieval or active processing at each encounter. Mechanisms that produce spacing benefits ([source](https://www.nature.com/articles/s44159-022-00089-1)):

1. **Contextual variation**: Different contextual information is encoded with each spaced encounter. More retrieval cues are encoded, leading to more robust recall.
2. **Retrieval demand**: Spaced sessions require retrieving information from earlier sessions, engaging retrieval practice benefits automatically.
3. **Deficient processing of massed study**: Massed repetition feels easy, creating an illusion of competence without deep processing.

### Natural Spacing Through Reading

Reading new material that touches on concepts from a previously-read book creates "natural spacing" with several advantages over artificial SRS:

- **Novel context**: The concept appears in a genuinely new context, encoding additional retrieval cues
- **Incidental retrieval**: The reader's recognition of a familiar concept triggers retrieval of the original source
- **Elaborative connection**: The reader naturally compares and contrasts the two sources' perspectives
- **Intrinsic motivation**: The new article is interesting in its own right, not a chore

Research on vocabulary learning through reading confirms this mechanism ([source](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.13135)): "Spaced contextual word learning is incremental and is facilitated through an inference-feedback loop that involves making contextual inferences, retrieving knowledge from previous learning episodes, and processing feedback."

### Interleaving: Mixing Topics Aids Learning

Bjork's "desirable difficulties" framework ([source](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf)) identifies interleaving as a key difficulty that enhances long-term retention:

- Rohrer and Taylor (2007) found interleaved practice produced **43% better performance** on delayed tests vs. blocked practice
- Interleaving forces the brain to discriminate between similar concepts, strengthening mental models
- Bjork & Bjork (2011) classify interleaving as a "desirable difficulty" that slows initial learning but strengthens long-term retention

**Implication for Petrarca**: A reading feed that naturally interleaves articles touching on different books' concepts provides interleaving benefits. If a user reads a Pirenne-adjacent article, then a Menocal-adjacent one, then something unrelated, this is better for retention than reading all Pirenne-related articles in a block.

---

## 4. Gist Memory vs. Verbatim Memory: How Concepts Decay Differently

### Fuzzy-Trace Theory

Brainerd & Reyna's Fuzzy-Trace Theory ([source](https://en.wikipedia.org/wiki/Fuzzy-trace_theory)) proposes that people encode two parallel memory traces:

- **Verbatim trace**: Surface form -- exact words, numbers, specific examples
- **Gist trace**: Essential meaning -- the argument, the framework, the "so what"

These are "encoded in parallel, stored separately, and can be retrieved independently of each other." The critical finding: **verbatim traces become inaccessible faster than gist traces**. Gist memories are more resistant to forgetting.

### What Readers Actually Retain

Research on book retention ([source](https://effectiviology.com/verbatim-effect/)):

- Readers retain "general themes and key concepts" but struggle with "names, arguments, specific examples" after months
- People usually have a clear memory of a film's central theme but a less clear memory of detailed episodes, particularly with time
- Without reinforcement, ~50% of detail is lost within hours, ~90% within a week
- But *gist* persists much longer -- often months or years for well-understood material

**The paradox**: The most valuable part of nonfiction reading (the gist -- the conceptual framework, the argument structure) is actually the most durable. What fades is the evidence, examples, and specifics that *support* the gist. This suggests a retention strategy should focus on:

1. **Reinforcing the gist** occasionally (to prevent even gist decay)
2. **Re-connecting details to the gist** when they're encountered in new contexts
3. **Not worrying about verbatim retention** of specific passages

### How Long Does Book Knowledge Last?

Without any reinforcement ([source](https://medium.com/@alexallain/making-the-most-out-of-non-fiction-b268a79fce48)):
- **1 week**: Can recall main arguments, key examples, specific passages that resonated
- **1 month**: Main thesis is clear, specific arguments are fuzzy, examples are gone
- **3 months**: Can state the book's "big idea" but not reconstruct its argument
- **1 year**: Vague sense of "having read something about X"

With even minimal reinforcement (encountering related concepts, discussing the book, rereading notes):
- Gist retention extends to years
- Key arguments can be reconstructed from partial cues
- The framework becomes a lens applied to new information

---

## 5. Elaborative Interrogation and Self-Explanation

### Research on "Why?" and "How?" Questions

Elaborative interrogation involves asking "why is this true?" or "how does this work?" while reading. Research shows significant benefits ([source](https://www.uwlax.edu/catl/guides/teaching-improvement-guide/how-can-i-improve/elaborative-interrogation/)):

- EI group outperformed standard study group 76% vs. 69% on tests
- Elaborative interrogation prompts learners to associate new material with prior knowledge and create new knowledge structures
- Generating explanations requires "higher degree of effortful and analytic processing" than passive reading

### The Self-Explanation Effect

Self-explanation -- explaining to yourself *why* a statement is true and *how* it connects to what you know -- is even more powerful than elaborative interrogation ([source](https://learning.northeastern.edu/the-power-of-self-explanation/)):

- Self-explanation participants "significantly outperformed elaborative interrogation and repetition control participants" on cued recall and recognition
- Works because it requires the reader to identify gaps in their understanding
- Forces construction of causal mental models

### The Generation Effect

The generation effect ([source](https://www.structural-learning.com/post/generation-effect-active-learning)) shows that actively producing information yourself produces better memory than passively receiving it:

- "Students who generate questions about content process it more deeply than those who simply read it"
- Question generation initiates "hypothesizing, predicting, thought-experimenting, and explaining"
- Self-generated questions create "elaborative encoding" -- the gold standard for durable learning

### Critical Limitation: Prior Knowledge Required

A key caveat for all these techniques: "Students need background knowledge of a topic in order to produce good explanations." If the material is entirely novel, elaborative interrogation may fail because the reader simply cannot generate meaningful explanations.

**Implication for Petrarca**: Elaborative prompts work best *after* initial reading, when the reader has some knowledge to work with. Prompts should be calibrated to the reader's familiarity -- asking "how does this connect to [known concept]?" rather than "why is this true?" for unfamiliar material.

### What Kinds of Prompts Work Best for Complex Material?

Based on the research, a hierarchy of prompt effectiveness:

1. **Connection prompts** (best): "How does this relate to [concept from another book]?"
2. **Explanation prompts**: "Why does the author argue X rather than Y?"
3. **Implication prompts**: "What would follow if this argument is correct?"
4. **Contrast prompts**: "How does this differ from [similar concept]?"
5. **Application prompts**: "Where might you see this pattern in [current events/other domain]?"
6. **Recognition prompts** (weakest): "Did the author say X or Y?"

---

## 6. Connection-Based Resurfacing: The Central Mechanism

### Spreading Activation in Memory Networks

Memory is organized as a network of nodes (concepts) connected by links (associations). When one node is activated, it sends activation along its links to connected nodes ([source](https://www.cognitivepsychology.com/Spreading_Activation)). This is "spreading activation" -- the mechanism by which encountering concept X automatically triggers partial recall of related concept Y.

**Retrieval-induced facilitation** ([source](https://www.researchgate.net/publication/6708733_Retrieval_induced_facilitation_Initially_nontested_material_can_benefit_from_prior_testing)): Testing (retrieving) one piece of information can actually *improve* recall of related, untested information. This is the opposite of retrieval-induced forgetting, and it occurs when the items share a coherent mental model. When multiple pieces of information are stored in the same mental model, retrieving one strengthens the others via spreading activation.

### Analogical Reminding

"Remote analogical reminding" ([source](https://link.springer.com/article/10.3758/bf03201088)) occurs when one episode is cued by another sharing similar themes but not similar surface features. Human memory is sensitive to deep structural similarity, not just superficial overlap.

Research on comparison vs. reminding ([source](https://link.springer.com/article/10.1186/s41235-016-0028-1)) found that **remindings led to better transfer than explicit comparison**. Remindings promote memory for individual episodes *and* generalization because they prompt learners to retrieve earlier episodes during encoding of new episodes and to compare across episodes.

**This is exactly what Petrarca could harness**: When a user reads a new article about Mediterranean trade, and it *reminds* them of Pirenne's thesis, that reminding event is more powerful than explicitly being shown a flashcard about Pirenne.

### Schema Theory and "Resonance Detection"

The medial prefrontal cortex (mPFC) functions as a "resonance detector" ([source](https://pmc.ncbi.nlm.nih.gov/articles/PMC7479862/)) that recognizes when new information fits into pre-existing knowledge structures (schemas). When congruence is detected:

1. The mPFC detects fit with existing schema
2. New information is directly integrated into the existing knowledge structure
3. The old schema is strengthened and updated simultaneously

This is "knowledge resonance" -- the phenomenon where old ideas are reactivated when new, related ideas arrive. The key insight: **the brain already does this naturally, but it needs the right cues**. Petrarca's job is to provide those cues.

### Reactivation During New Learning

A study in *npj Science of Learning* ([source](https://www.nature.com/articles/s41539-018-0027-8)) found that "reactivation of previously learned information during new learning leads to integration of old and new memories and strengthens long-term retention." The integration process is not passive -- it requires active reactivation of the old memory while encoding the new one.

### Transfer-Appropriate Processing

Memory retrieval is best when the cognitive processes at retrieval match those at encoding ([source](https://en.wikipedia.org/wiki/Transfer-appropriate_processing)). If you encoded a concept while reading deeply and making connections, the best retrieval cue is another deep reading context where connections are being made -- not a flashcard prompt.

**Implication for Petrarca**: The ideal "review" of book knowledge is not a flashcard review session, but encountering a related concept while reading a new article, in a reading context similar to the original encoding. The system should surface book captures *during* article reading when connections exist.

---

## 7. The Readwise Model: What Works and What's Missing

### How Readwise Works

Readwise ([source](https://docs.readwise.io/readwise/docs/faqs/reviewing-highlights)) uses a recall probability half-life model:

- **First half of Daily Review**: Unprocessed highlights resurfaced randomly (stochastic)
- **Second half**: Mastery cards resurfaced via SRS algorithm (recall probability < 50%)
- **Half-lives**: "Soon" = 7 days, "Later" = 14 days, "Someday" = 28 days
- **Frequency tuning**: Books with more highlights appear proportionally more often
- **Active recall**: Some cards presented as cloze deletions or questions

### What Readwise Gets Right

- **Low friction**: Daily email/app review takes 5-10 minutes
- **Re-exposure at least triggers recognition**: Even passive re-reading has some benefit
- **Serendipitous connections**: Random resurfacing occasionally creates surprising juxtapositions
- **No card-creation burden**: Highlights are captured during reading, not authored afterward

### What Readwise Gets Wrong (for Conceptual Knowledge)

- **Decontextualized highlights**: Seeing "The Mediterranean was a Roman lake" without the surrounding argument loses the gist
- **No connection to current reading**: Highlights appear randomly, not when they're relevant to what you're reading now
- **Passive re-reading dominates**: Most users just re-read highlights without active engagement
- **No knowledge model**: The system doesn't know what you know or what's fading
- **No inter-book connections**: Each book's highlights exist in isolation

### Re-exposure vs. Active Recall: The Research

Active recall is substantially more effective than re-reading. Meta-analyses show effect sizes of g = 0.50 to g = 0.61 for retrieval practice vs. re-studying ([source](https://pmc.ncbi.nlm.nih.gov/articles/PMC8759977/)). However, even passive re-exposure has *some* benefit -- it maintains recognition (familiarity) even if it doesn't strengthen recollection.

**The practical question**: Is the small benefit of passive re-exposure worth the daily time investment? For most Readwise users, probably yes, because the cost is low (5 minutes). But could the same 5 minutes be used more effectively? Almost certainly.

---

## 8. Experimental Directions for Petrarca

Based on the research above, here are concrete mechanisms that could be built and tested.

### 8.1 Concept Encounters

**Mechanism**: When a book concept appears in a new article, surface the book capture alongside the article.

**How it works**:
1. Book captures are decomposed into atomic claims and embedded (already in Petrarca's pipeline)
2. Article claims are embedded and compared against book claims
3. When cosine similarity exceeds a threshold (e.g., 0.68-0.78, the EXTENDS range), the book capture is surfaced
4. Surfaced as a margin annotation or inline card: "From [Book Title]: [relevant capture]"

**Why it should work**:
- Triggers analogical reminding (research shows remindings > explicit comparison)
- Provides natural spacing in a genuine reading context
- Context-dependent memory: encoding and retrieval contexts match (both are reading)
- Elaborative processing: reader naturally compares the two perspectives

**What to measure**: Does encountering book concepts in articles slow gist decay? Compare knowledge retention for concepts that are encountered in articles vs. concepts that are not.

**Implementation sketch**:
- At article load time, compare article claims against all book claims in the knowledge index
- If matches are found, render them as "Reading Echoes" (see 8.4) in the article margin
- Track when a book concept is "encountered" -- this is an implicit reinforcement event
- Use encounter events to update the knowledge half-life for that concept

### 8.2 Evolving Summaries

**Mechanism**: Your summary of a book grows and changes as you read related material.

**How it works**:
1. After initial book reading, generate a "current understanding" summary from captures
2. As the reader encounters related articles, the system notes connections
3. Periodically (weekly?), regenerate the summary incorporating new connections: "Your understanding of Pirenne has been enriched by 3 articles this month. New connections: [X challenged Pirenne's dating], [Y provided supporting evidence for the trade disruption thesis]"

**Why it should work**:
- Progressive summarization (Forte, [source](https://fortelabs.com/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/)): knowledge is "gradually distilled" through multiple review passes
- Each summary revision requires elaborative retrieval of the book's arguments
- Makes the value of continued reading visible -- your understanding demonstrably grows

**What to measure**: Do users who receive evolving summaries retain book arguments longer than those who don't? Can they reconstruct a book's argument more accurately after 3 months?

**Implementation sketch**:
- Store a `book_understanding` object per book: initial summary + list of connection events
- When a connection event occurs (via concept encounters), log it
- Weekly LLM pass: regenerate summary incorporating connections
- Surface the evolving summary on the book detail screen
- Show a "knowledge timeline" of how understanding has developed

### 8.3 Argument Challenges

**Mechanism**: Periodically present a claim that challenges something from a book, prompting the reader to articulate the book's counterargument.

**How it works**:
1. For each book, identify its core claims/arguments
2. From the article corpus, find claims that contradict or complicate those arguments
3. Present as a "Challenge": "This article argues [X]. How would Pirenne respond?"
4. The reader's response (typed, voice, or selected from options) constitutes elaborative retrieval

**Why it should work**:
- Elaborative interrogation: "why is this true?" prompts are highly effective for retention
- The generation effect: producing an argument yourself strengthens memory more than reading one
- Argument engagement promotes relational processing (the strongest form of encoding)
- Creates "desirable difficulty" -- the challenge is harder than a flashcard but more beneficial

**What to measure**: Does engaging with argument challenges improve retention of the book's core thesis? Compare retention for books with challenges vs. books without.

**Implementation sketch**:
- Identify "challengeable" book claims using NLI (Natural Language Inference) or cosine similarity with inverted polarity
- Present challenges as push notifications or in a dedicated "Challenge" section
- Accept free-text responses (generation effect > recognition)
- LLM evaluates the response for engagement with the original argument
- Track which books have received challenges and compare retention

### 8.4 Reading Echoes

**Mechanism**: Brief moments where past reading enriches current reading, surfaced as subtle annotations.

**How it works**:
1. While reading an article, concepts that connect to book knowledge are detected
2. A subtle "echo" appears -- a brief annotation showing the connection: "cf. [Book], Ch. 3: [relevant quote]"
3. The echo is not a full resurfacing -- just a gentle reminder that creates a moment of recognition
4. Tapping the echo shows the full book capture with context

**Why it should work**:
- Incidental spaced retrieval: encountering concepts in new contexts without deliberate study
- Spreading activation: the echo activates the broader network of book knowledge
- Transfer-appropriate processing: the retrieval context (reading) matches the encoding context
- Low friction: doesn't interrupt the reading flow

**Design considerations**:
- Echoes should be **subtle** -- a thin left border, a small icon, a muted color
- Don't show too many per article (max 2-3) to avoid clutter and "echo fatigue"
- Prioritize echoes for concepts that are **fading** (based on knowledge half-life)
- Show echoes for concepts that are **genuinely relevant**, not just superficially similar

**What to measure**: Do reading echoes slow the decay of book knowledge? Do readers who see echoes retain more of the book's arguments than those who don't?

### 8.5 Knowledge Half-Life Dashboard

**Mechanism**: A visual dashboard showing which book ideas are fading and which are being reinforced by ongoing reading.

**How it works**:
1. Each book concept has a "vitality" score based on:
   - Time since last encounter (decay)
   - Number of encounters in articles (reinforcement)
   - Quality of encounters (passive re-reading vs. active engagement)
2. Dashboard shows books and their concepts on a vitality gradient: vibrant (recently reinforced) to fading (no encounters, long time)
3. "Fading" concepts become candidates for active resurfacing

**Vitality model** (based on fuzzy-trace theory):
- **Gist vitality**: Decays slowly (half-life ~6 months without any reinforcement). Reinforced by any encounter with related concepts.
- **Detail vitality**: Decays quickly (half-life ~2 weeks). Reinforced only by re-reading the specific capture or encountering the specific claim.
- **Each encounter** extends the half-life (FSRS-style stability increase, but simpler: `new_halflife = old_halflife * 1.5`)

**Dashboard elements**:
- Books ranked by "knowledge health": how much of each book's core argument is still vital
- Per-book view: list of concepts with vitality bars (green = vital, amber = fading, red = near-forgotten)
- "Reinforced this week": concepts that were encountered in new articles
- "At risk": concepts approaching the forgetting threshold with no recent reinforcement

**What to measure**: Does visibility of knowledge decay change reading behavior? Do users who see the dashboard read more articles connected to fading books?

### 8.6 Prompted Self-Explanation During Capture

**Mechanism**: When the user captures a passage from a book (photo, voice, text), prompt them with a self-explanation question.

**How it works**:
1. User takes a photo of a passage or dictates a note
2. System generates a brief prompt: "Why is this significant to the book's argument?" or "How does this connect to [previously captured concept]?"
3. User responds (voice or text), creating an elaborative encoding
4. The response is stored alongside the capture

**Why it should work**:
- Self-explanation effect: explaining why something matters creates deeper encoding
- Generation effect: producing the explanation yourself > reading one
- Connection to prior captures creates a network of related concepts
- The prompt arrives at the moment of highest engagement (the user just chose to capture this)

**Prompt types** (calibrated to capture history):
- **First capture from a book**: "What's the main argument this passage supports?"
- **Subsequent captures**: "How does this connect to your earlier capture about [X]?"
- **Cross-book captures**: "This reminds me of [concept from another book]. Do you see a connection?"
- **After several captures**: "What would you say is the book's central thesis so far?"

**What to measure**: Do captures with self-explanation prompts produce better retention than captures without? Is the additional friction worth the retention benefit?

### 8.7 Concept Constellation View

**Mechanism**: A visual map showing how concepts from different books connect to each other and to articles in the feed.

**How it works**:
1. Book concepts and article claims are embedded in the same vector space (already in Petrarca)
2. A force-directed graph shows clusters of related concepts across books and articles
3. Connections are weighted by semantic similarity
4. The map evolves as new articles arrive and new captures are made

**Why it should work**:
- Makes the knowledge network visible, which aids metacognition
- Reveals unexpected connections between books (analogical transfer)
- Shows which areas of knowledge are well-connected (robust) vs. isolated (fragile)
- Creates intrinsic motivation to "fill in" gaps in the constellation

---

## 9. Synthesis: A Retention Architecture for Petrarca

### The Core Thesis

**The best way to keep book knowledge alive is not to review it in isolation, but to connect it to new reading.** Every article in the feed is a potential reinforcement event for book knowledge. The system's job is to detect and surface these connections.

### Three Layers of Retention

**Layer 1: Passive Reinforcement (automatic, invisible)**
- Track when book concepts are semantically matched by new articles
- Update concept vitality scores automatically
- No user action required -- just reading the feed reinforces connected book knowledge

**Layer 2: Active Resurfacing (gentle, optional)**
- Reading Echoes: subtle margin annotations connecting current article to book knowledge
- Concept Encounters: when a strong match is found, surface the book capture
- Knowledge Dashboard: show what's vital and what's fading
- User can engage or ignore -- the system adapts to their engagement level

**Layer 3: Deep Engagement (effortful, periodic)**
- Argument Challenges: periodically prompt the reader to defend or articulate book arguments
- Self-Explanation prompts: at capture time, prompt elaborative encoding
- Evolving Summaries: periodic synthesis of how understanding has grown

### What to Build First

**Priority 1: Concept Encounters** (highest research support, aligns with existing infrastructure)
- Petrarca already has claim embeddings for articles and can have them for book captures
- The matching infrastructure exists (cosine similarity, EXTENDS threshold)
- Low implementation cost, high potential impact
- Provides data for all other features (encounter events are the foundation)

**Priority 2: Reading Echoes** (requires concept encounters, adds reader integration)
- Render matched book concepts as margin annotations during article reading
- Subtle, non-intrusive, low friction

**Priority 3: Knowledge Half-Life Dashboard** (requires encounter tracking, provides motivation)
- Visualize knowledge vitality per book and per concept
- Uses existing FSRS-style decay model, simplified to binary seen/unseen + encounter-based reinforcement

**Priority 4: Prompted Self-Explanation** (independent of other features, testable immediately)
- Add LLM-generated prompts to the book capture flow
- Store responses as enriched captures

---

## 10. Key Research Sources

### Spacing, Retrieval, and Desirable Difficulties
- [Bjork & Bjork (2011) — Desirable Difficulties in Learning](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf)
- [Karpicke & Blunt (2011) — Retrieval Practice Produces More Learning than Elaborative Studying](https://www.science.org/doi/10.1126/science.1199327)
- [Rawson & Dunlosky (2022) — Spacing and Retrieval Practice](https://www.nature.com/articles/s44159-022-00089-1)
- [Scientific American — The Interleaving Effect](https://www.scientificamerican.com/article/the-interleaving-effect-mixing-it-up-boosts-learning/)

### Memory Architecture
- [Fuzzy-Trace Theory — Wikipedia](https://en.wikipedia.org/wiki/Fuzzy-trace_theory)
- [Effectiviology — The Verbatim Effect](https://effectiviology.com/verbatim-effect/)
- [Alonso et al. (2020) — Prior Knowledge in Memory](https://pmc.ncbi.nlm.nih.gov/articles/PMC7479862/)
- [van Kesteren et al. (2018) — Reactivation of Prior Knowledge During Educational Learning](https://www.nature.com/articles/s41539-018-0027-8)

### Reminding and Analogical Transfer
- [Gentner et al. — Comparison vs. Reminding](https://link.springer.com/article/10.1186/s41235-016-0028-1)
- [Wharton et al. (1996) — Remote Analogical Reminding](https://link.springer.com/article/10.3758/bf03201088)
- [Retrieval-Induced Facilitation](https://www.researchgate.net/publication/6708733_Retrieval_induced_facilitation_Initially_nontested_material_can_benefit_from_prior_testing)
- [Spreading Activation — Cognitive Psychology Reference](https://www.cognitivepsychology.com/Spreading_Activation)

### Elaborative Interrogation and Self-Explanation
- [UW-La Crosse — Elaborative Interrogation Guide](https://www.uwlax.edu/catl/guides/teaching-improvement-guide/how-can-i-improve/elaborative-interrogation/)
- [Northeastern — The Power of Self-Explanation](https://learning.northeastern.edu/the-power-of-self-explanation/)
- [Structural Learning — The Generation Effect](https://www.structural-learning.com/post/generation-effect-active-learning)

### SRS and Knowledge Retention Tools
- [Andy Matuschak — Mnemonic Medium](https://notes.andymatuschak.org/Mnemonic_medium)
- [Andy Matuschak — SRS for Conceptual Understanding](https://notes.andymatuschak.org/z9Vi7YVx7NzxU2wawNgsJbk)
- [Readwise — How Reviews Work](https://docs.readwise.io/readwise/docs/faqs/reviewing-highlights)
- [Scott H. Young — SRS for Concepts](https://www.scotthyoung.com/blog/2014/11/07/srs-for-concepts/)
- [LessWrong — A Vote Against Spaced Repetition](https://www.lesswrong.com/posts/As9E3HfgED2zkTAfB/a-vote-against-spaced-repetition)
- [SuperMemo — Incremental Reading](https://help.supermemo.org/wiki/Incremental_reading)
- [Forte Labs — Progressive Summarization](https://fortelabs.com/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/)

### Knowledge Decay
- [Farnam Street — Half-Life of Knowledge](https://fs.blog/half-life/)
- [Half-Life of Knowledge — Wikipedia](https://en.wikipedia.org/wiki/Half-life_of_knowledge)
- [Farnam Street — How to Remember What You Read](https://fs.blog/how-to-remember-what-you-read/)
