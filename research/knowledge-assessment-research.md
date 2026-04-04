# Research Report: Knowledge Assessment, Tracking, and Maintenance for Complex Domains

**Created:** 2026-04-04
**Context:** Research synthesis for Petrarca's knowledge modeling system — how to assess, track, and maintain understanding of complex historical topics across books and articles over time.

---

## Table of Contents

1. [Knowledge State Assessment in Complex Domains](#1-knowledge-state-assessment-in-complex-domains)
2. [Free Recall as Knowledge Assessment](#2-free-recall-as-knowledge-assessment)
3. [Knowledge Maps and Concept Maps as Assessment](#3-knowledge-maps-and-concept-maps-as-assessment)
4. [Spaced Retrieval Beyond Flashcards](#4-spaced-retrieval-beyond-flashcards)
5. [Longitudinal Knowledge Tracking](#5-longitudinal-knowledge-tracking)
6. [Voice-Based Knowledge Elicitation](#6-voice-based-knowledge-elicitation)
7. [Existing Systems for Reader Knowledge Tracking](#7-existing-systems-for-reader-knowledge-tracking)
8. [Synthesis: Implications for Petrarca](#8-synthesis-implications-for-petrarca)

---

## 1. Knowledge State Assessment in Complex Domains

### 1.1 Concept Inventories: The Physics Model and Why It Doesn't Transfer

The **Force Concept Inventory** (FCI), developed by Hestenes, Wells, & Halloun (1992), revolutionized physics education by revealing a shocking gap: while ~80% of students could *state* Newton's Third Law after completing a course, fewer than 15% actually *understood* it as measured by the FCI. The key insight: standard exams tested recall and computation, not conceptual understanding.

Concept inventories have proliferated across STEM fields (biology, chemistry, geoscience, astronomy, computer science), but they have **not successfully transferred to history or humanities**. The reason is structural: concept inventories work by identifying a fixed set of common misconceptions about phenomena with objectively correct answers. History doesn't have "misconceptions" in the same way — historical understanding involves interpretation, perspective-taking, and argumentation rather than convergence on correct models.

**Key paper:** Epstein, J. (2013). "The Calculus Concept Inventory — Measurement of the Effect of Teaching Methodology in Mathematics." *Notices of the AMS*. Defines concept inventories as tests of "the most basic conceptual comprehension of foundations of a subject and not of computational skill."

**Implication for Petrarca:** Don't try to build a concept inventory for history. The FCI model works for domains with stable misconceptions and correct answers. Historical knowledge is better assessed through structural and process-based methods (see sections 2-3).

### 1.2 Expert vs. Novice Knowledge Structures (Chi, Feltovich, & Glaser)

The landmark study by **Chi, Feltovich, & Glaser (1981)**, "Categorization and Representation of Physics Problems by Experts and Novices" (*Cognitive Science*, 5, 121-152), established the foundational framework for understanding how expertise manifests in knowledge organization.

**Key findings:**
- **Experts categorize by deep principles** (e.g., "this is a conservation of energy problem"), while **novices categorize by surface features** (e.g., "this is an inclined plane problem").
- The difference isn't primarily knowledge *amount* — it's knowledge *organization*. Experts have richly interconnected schemas organized around core principles. Novices store disconnected facts and procedures.
- Experts' problem representations are *forward-working* (principle → solution) while novices' are *backward-working* (given → formula → answer).

This was extended by **Glaser & Chi (1988)**, "Overview of Expertise Research" (CMU Technical Report), which identified seven general characteristics of expert knowledge: (1) excelling mainly in their own domains, (2) perceiving large meaningful patterns, (3) fast problem-solving with little error, (4) superior short-term and long-term memory, (5) seeing problems at a deeper level, (6) spending more time analyzing qualitatively, (7) strong self-monitoring skills.

The NRC's *How People Learn* (2000) synthesizes this research: "Experts' knowledge is organized around core concepts or 'big ideas' that guide their thinking about their domains." Novices "organize knowledge as a list of facts, formulas, or heuristics."

**Implication for Petrarca:** The system should track not just *what* the user knows but *how their knowledge is organized*. A user who knows 50 facts about Sicily but can't connect them to larger patterns (Greek colonization as part of Mediterranean trade, tyranny as a political phenomenon, etc.) is at a novice stage. A user who can place events within causal frameworks is developing expertise. The curriculum node structure already captures this — nodes represent organizational principles, not isolated facts.

### 1.3 How Historians Think (Sam Wineburg)

**Sam Wineburg's** work, culminating in *Historical Thinking and Other Unnatural Acts* (2001), used think-aloud protocols to reveal fundamental differences between how historians and students read primary sources.

**Key finding — the sourcing heuristic:** When given a document, historians immediately check the attribution (who wrote this, when, for what audience, what was their position) before engaging with content. Students dive into the text directly. "The historian took the document and read the first words of the first sentence. Then he shifted attention to the attribution and dwelled on it forever." In every study of historical reading, "sourcing is the touchstone that distinguishes expert from novice practice."

**Four historical thinking strategies** (Wineburg & Reisman):
1. **Sourcing** — Who created this? What's their perspective and motivation?
2. **Contextualization** — When and where was this created? What else was happening?
3. **Corroboration** — How does this compare with other accounts?
4. **Close reading** — What claims does the text actually make? What language choices reveal?

**Central thesis:** Historical thinking is "unnatural" — it requires actively suppressing presentism (judging the past by present standards) and building empathic understanding of how people in different times thought. This is a disciplinary skill that must be taught, not a natural extension of reading.

**Peter Seixas' "Big Six"** (2013) expanded this into a Canadian assessment framework with six historical thinking concepts: historical significance, primary source evidence, continuity and change, cause and consequence, historical perspectives, and ethical dimensions. Each concept has graduated benchmarks from naive to sophisticated understanding.

**Implication for Petrarca:** The system's knowledge model should eventually distinguish between *knowing facts about* a period and *thinking historically about* it. Currently, Petrarca's curriculum nodes capture declarative knowledge (dates, people, events). A richer model would track whether the user can perform operations like contextualizing (placing an event in its broader setting), identifying cause-and-consequence chains, and comparing perspectives across sources. The "hooks" philosophy already aligns well — hooks are essentially the user's ability to contextualize new information, which is Wineburg's key expert behavior.

### 1.4 Knowledge Organization vs. Knowledge Amount

**Bransford, Brown, & Cocking (2000)**, *How People Learn* (National Academies Press), synthesize decades of cognitive science research into a key principle: "It is not simply general abilities, such as memory or intelligence, nor is it the use of general strategies that differentiate experts from novices. Instead, experts have acquired extensive knowledge that affects what they notice and how they organize, represent, and interpret information."

**Schneider, Korkel, & Weinert (1989)**, "Domain-Specific Knowledge and Memory Performance" (*Journal of Educational Psychology*), demonstrated with children that domain-specific expertise (about soccer) predicted memory performance on soccer-related stories *better than IQ*. Low-IQ soccer experts outperformed high-IQ soccer novices. This proves knowledge organization — not general ability — drives comprehension and recall.

**Ericsson's deliberate practice** (1993) framework adds that expert knowledge structures aren't built through simple exposure but through "highly structured, intentional practice aimed at improving specific aspects of performance."

**Implication for Petrarca:** The system's value proposition is precisely this: it builds organized knowledge structures (via curriculum nodes, temporal hooks, entity networks) that make reading more productive. Tracking the *structure* of what the user knows (which nodes connect to which, how densely linked different domains are) may be more informative than tracking the *amount*.

---

## 2. Free Recall as Knowledge Assessment

### 2.1 The Power of Free Recall Protocols

Free recall — asking someone "tell me everything you know about X" with no prompts — is one of the most powerful assessment methods in cognitive psychology precisely because it reveals *organization*, not just content.

**Key research hierarchy** (from the Petrarca "beyond-flashcards" doc, confirmed by literature):
- **Free recall** (open-ended: "What do you remember about X?") promotes both relational and item-specific processing
- **Cued recall** (prompted: "What was the argument about X?") promotes primarily item-specific processing
- **Recognition** (multiple choice) promotes only familiarity, not recollection

**Tulving's ecphory theory** explains organizational effects in free recall as arising from the interaction of retrieval cues with memory contents. When freely recalling, people reveal their internal organization — what clusters together, what sequences connect, what's central vs. peripheral.

### 2.2 How Recall Structure Changes with Expertise

Research consistently shows that experts recall information in **larger, more organized chunks** than novices:

- **Semantic clustering**: Experts group recalled items by underlying principles; novices group by surface features or temporal order of learning (the same Chi et al. distinction, but visible in recall patterns).
- **Hierarchical structure**: Expert recall exhibits deeper hierarchical organization — they start with high-level categories and drill down, while novices list items more randomly.
- **Relational connections**: Experts spontaneously articulate *connections between* recalled items, while novices tend to list isolated facts.

**Schneider, Korkel, & Weinert (1989, 1990)** showed this with children and soccer knowledge — expert children recalled more soccer-story content, but more importantly, they recalled it in *more organized patterns* that reflected deeper understanding of the game's structure.

### 2.3 Computational Analysis of Free Recall

Recent work has developed computational methods to analyze free recall:

**Semantic network estimation from free recall** (see *Memory & Cognition*, 2026 — Zemla & Austerweil): Free recall of semantically related words reveals the similarity structure of memory. "Estimating semantic networks from free recall provides some potential advantages over other tasks such as semantic fluency, free association, or triadic comparison."

**Semantic clustering analysis**: The tendency to successively recall semantically related items (semantic clustering) can be quantified. Higher semantic clustering indicates more organized knowledge. Models can evaluate whether a person's recall order reflects deep conceptual groupings or surface-level associations.

**Model-based analysis of recall structure**: Researchers use computational models (e.g., Search of Associative Memory, Temporal Context Model) to analyze how semantic information affects recall sequences. These models can detect changes in knowledge organization — e.g., before and after a learning intervention.

### 2.4 The Knowledge Base and Text Recall

**Recht & Leslie (1988)**, "Effect of Prior Knowledge on Good and Poor Readers' Memory of Text" (*Journal of Educational Psychology*), showed that prior knowledge dominated reading ability in predicting recall. High-knowledge poor readers recalled more than low-knowledge good readers — knowledge structure trumps reading skill for comprehension and retention.

**Implication for Petrarca:** The voice dump feature ("tell me everything you know about Sicily") is directly aligned with free recall as a knowledge assessment method. The system could analyze these dumps not just for content coverage (which curriculum nodes are mentioned) but for *structural quality*:
- Do items cluster by theme or period (expert pattern) vs. random order (novice)?
- Are causal connections articulated ("X led to Y because...")?
- Is there hierarchical organization (big picture first, then details)?
- What is the ratio of facts to interpretive/explanatory statements?

This analysis could feed directly into the knowledge model, upgrading nodes from "mentioned" to "anchored" based on the quality of recall, not just its presence.

---

## 3. Knowledge Maps and Concept Maps as Assessment

### 3.1 Novak's Concept Mapping Framework

**Joseph Novak** developed concept maps in the 1970s-80s at Cornell, based on Ausubel's assimilation theory of meaningful learning. Concept maps represent knowledge as a network of concepts (nodes) connected by labeled relationships (links), organized hierarchically.

**Novak & Gowin (1984)** scoring system:
- **Propositions** (concept–link–concept): Each valid proposition scores 1 point
- **Hierarchy levels**: Each valid level scores 5 points
- **Cross-links**: Each valid cross-link (connecting different map segments) scores 10 points
- **Examples**: Each valid example scores 1 point

The heavily weighted cross-links are the key insight — they represent the most meaningful form of knowledge, where concepts from different areas are connected. This maps directly to Petrarca's cross-domain connections.

**Jackson et al. (2024)**, systematic review in *Journal of Engineering Education*, found concept maps are effective for detecting "deep content understandings as well as misconceptions" — they reveal both what students know and how they've mis-connected ideas.

### 3.2 Pathfinder Networks

**Pathfinder network scaling** (Schvaneveldt, 1990) is an alternative to concept mapping that derives knowledge structure from similarity judgments. Students rate the relatedness of concept pairs, and the Pathfinder algorithm converts these ratings into a network representation.

**Goldsmith, Johnson, & Acton (1991)**, "Assessing Structural Knowledge" (*Journal of Educational Psychology*), validated Pathfinder networks as knowledge assessment tools. In a statistics course, the similarity between each student's network and the instructor's network (measured by the C metric — shared links) correlated with exam performance at **r = .74** — a remarkably strong predictor.

**Three Pathfinder metrics** (from Sarwar, 2011):
- **PRX (Proximity)**: How similar is the student's network to the expert's?
- **GTD (Graph-Theoretic Distance)**: How different are the graph structures?
- **PFC (Pathfinder Correlation)**: Correlation between student and expert distance matrices

**Assessing knowledge structure in accounting** (Clariana & Wallace, 2007, *Journal of Accounting Education*): Pathfinder networks were applied to track how accounting students' knowledge structures evolved over a semester, demonstrating that structural similarity to experts increased with learning.

### 3.3 Knowledge Structure Density (KSD)

Knowledge Structure Density refers to the ratio of actual connections to possible connections in a learner's knowledge map. Higher density indicates more interconnected knowledge.

Research from **Legitimation Code Theory** (Maton, 2014) distinguishes:
- **Chains of practice**: Low semantic density, high semantic gravity (procedural knowledge tied to specific contexts)
- **Networks of understanding**: High semantic density, low semantic gravity (conceptual knowledge with rich interconnections)

Mastery requires oscillating between these two structures — knowing both the specific facts and their abstract connections.

### 3.4 Computational Comparison of Knowledge Maps

**Concept Map Analysis** (Cberger, U. Michigan) developed multiple comparison measures:
- **A-measure**: Whether the same concepts are connected by any link (regardless of direction)
- **B-measure**: Whether the same linking propositions are used (regardless of direction)
- **F-measure (full measure)**: Total congruence — concepts, propositions, and directionality

**Similarity flooding algorithm** (Cañas et al., 2005, *Decision Support Systems*): Can match knowledge elements across concept map pairs even when terminology differs, supporting automated comparison of student maps to expert maps.

**Automated concept map generation** is now feasible with LLMs. A 2025 systematic review (arXiv:2509.14554) found that transformer models (BERT, GPT) can generate concept maps from text with increasing accuracy. LLMs can "understand context, generalize beyond literal content, and infer implicit relationships" — overcoming limitations of earlier NLP methods.

**Implication for Petrarca:** The curriculum graph *is* essentially an expert concept map for each domain. Each time the user reads a book or article, the system could generate a "reader concept map" from extracted claims and compare it to the curriculum structure. The gap between these maps is the learning target. Metrics like Pathfinder's PRX could quantify how much the user's knowledge structure resembles the expert structure, providing a single "understanding score" per domain that's more meaningful than counting known facts.

---

## 4. Spaced Retrieval Beyond Flashcards

### 4.1 Elaborative Retrieval Practice

**Karpicke & Blunt (2011)**, "Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping" (*Science*, 331, 772-775): The landmark finding that retrieval practice outperformed concept mapping for learning, even when the final test required creating concept maps. The mechanism: retrieval doesn't just strengthen individual memory traces — it activates and strengthens the entire semantic network around a concept.

**The elaborative retrieval hypothesis** (from Carpenter, 2009): During retrieval, not just the target information but also semantically related information is activated. "The information activated during retrieval may spread to other related concepts and eventually activate an elaborative semantic network with multiple pathways leading to the correct target." Critically, this means that testing on one concept can strengthen memory for *related, untested concepts* — as long as they're well-integrated.

**Roediger & Karpicke (2006)**, "Test-Enhanced Learning: Taking Memory Tests Improves Long-Term Retention" (*Psychological Science*): The crossover interaction — studying produces better performance at 5 minutes, but testing produces substantially better retention at 2 days and 1 week. "Prior testing produced substantially greater retention than studying."

### 4.2 Interleaved Practice for Historical Periods

**Sana & Yan (2022)**, "Interleaving Retrieval Practice Promotes Science Learning": Interleaved quizzes (mixing concept types) produced better learning than blocked quizzes (one type at a time), with participants performing better on interleaved concepts (63% vs. lower for blocked, d = 0.35).

The mechanism: "Mixing up problem types and specimens improves your ability to discriminate between types, identifying the unifying characteristics within a type." For history, this means interleaving questions about different periods/regions forces the learner to actively discriminate between eras and build more precise mental models.

**Bjork & Bjork's "desirable difficulties" framework** (2011): Interleaving is classified as a "desirable difficulty" — it slows initial learning but strengthens long-term retention and transfer. Rohrer & Taylor (2007) found interleaved practice produced 43% better delayed performance.

### 4.3 The Testing Effect for Connected Knowledge

**The forward effect of testing** (Pastotter et al., 2011; PMC3983480): Taking a test on material A actually *enhances* subsequent learning of new material B. Retrieval practice "can facilitate encoding of new material beyond the tested content" — it primes the learning system.

**Spreading activation during retrieval** (Anderson, 1983, *Journal of Verbal Learning and Verbal Behavior*): Collins and Loftus's spreading activation model, extended by Anderson's ACT theory, explains how retrieval strengthens networks. "The level of activation in the network determines the rate and probability of recall." The **SAMPL model** (Spreading Activation and Memory PLasticity) demonstrates that edge weights between strongly co-activated nodes are strengthened during retrieval, while weakly activated connections are pruned.

### 4.4 Retrieval-Induced Forgetting Considerations

**Anderson, Bjork, & Bjork (1994)**, "Remembering Can Cause Forgetting" (*Journal of Experimental Psychology: Learning, Memory, and Cognition*): Retrieving some items from a category can impair recall of other items from that same category. This is a real concern for a system that selectively reviews some curriculum nodes but not others.

**Critical mitigating factors:**
- **Integration during encoding**: When material is encoded as part of a coherent narrative (as in book reading), retrieval-induced forgetting is reduced. "Coherent prose can protect learners from retrieval-induced forgetting and even produce benefits."
- **Delay**: The negative effects of retrieval on non-tested items are strongest immediately and can reverse over longer delays.
- **Category structure**: Well-organized knowledge (expert structure) is more resistant to retrieval-induced forgetting than poorly organized knowledge.

**Chan, McDermott, & Roediger (2006)**, "When does retrieval induce forgetting and when does it induce facilitation?": Found that "the level of integration invoked during encoding and the length of delay between retrieval practice and final test were revealed as critical factors." High integration + delay = facilitation rather than forgetting.

**Implication for Petrarca:** The system's emphasis on connected knowledge (curriculum nodes linked by relationships, temporal hooks, cross-domain connections) actually *protects* against retrieval-induced forgetting. Because the knowledge is encoded as an integrated network rather than a list of isolated facts, reviewing some nodes should strengthen rather than impair recall of related nodes. However, the system should still aim for broad coverage across a domain rather than repeatedly drilling a small subset of nodes.

---

## 5. Longitudinal Knowledge Tracking

### 5.1 Pre/Post Testing Limitations

Traditional pre/post testing has well-documented limitations for longitudinal knowledge assessment:
- **Practice effects**: Taking the same test twice inflates post-test scores regardless of learning
- **Test-retest reliability**: Scores vary across administrations due to measurement error
- **Ceiling/floor effects**: Tests designed for one proficiency level are insensitive at others
- **Classical test theory limitations**: Item difficulties and discrimination are sample-dependent, making cross-time comparisons unreliable

### 5.2 Growth Modeling Approaches

**Longitudinal Item Response Theory (IRT)** models (Wang & Nydick, 2020, *Journal of Educational and Behavioral Statistics*) address these limitations by placing persons and items on the same metric, enabling:
- Administration of *different* test forms at different time points while maintaining comparability
- Modeling individual growth trajectories (not just group averages)
- Accounting for item difficulty in proficiency estimates

**Latent growth curve models** combined with IRT (described in Cambridge *Psychometrika*) can assess growth with categorical outcomes, extended to multidimensional IRT for tracking multiple knowledge dimensions simultaneously.

**Non-linear growth models** (from *Large-scale Assessments in Education*, 2014) are particularly relevant: "Individual estimates based on a non-linear growth model may provide a more accurate representation than parametric approaches, as assuming a linear growth can misrepresent setback phenomena like summer learning loss." Knowledge growth in complex domains is not linear — it has plateaus, breakthroughs, and periods of decay.

### 5.3 Computerized Adaptive Testing (CAT)

CAT dynamically selects questions based on the examinee's responses, efficiently zeroing in on their proficiency level. Key properties:
- Based on **Item Response Theory** (IRT) — items and persons on the same scale
- Each question is selected to maximize information at the current proficiency estimate
- Converges on an accurate estimate with far fewer questions than a fixed test
- **NWEA MAP** provides longitudinal views of student progress using consistent scales

**Dai, Gu, & Zhu (2023)**, "Personalized Recommendation in the Adaptive Learning System: The Role of Adaptive Testing Technology" (*Journal of Educational Computing Research*): Demonstrated that adaptive testing can drive personalized content recommendations by continuously updating the learner model.

### 5.4 Learning Analytics Indicators

The field of learning analytics (defined as "the measurement, collection, analysis and reporting of data about learners and their contexts") provides frameworks for longitudinal tracking:

**Three measurement areas** (from systematic reviews):
1. **Efficiency**: Time on task, resource engagement, quiz scores
2. **Effectiveness**: Knowledge acquisition, collaboration, engagement depth
3. **Outcomes**: Performance on assessments, transfer to new contexts

**Key gap identified**: Most learning analytics research lacks "large-scale, longitudinal, and experimental studies related to its impact on learning/teaching" — making Petrarca's longitudinal tracking genuinely novel if implemented well.

### 5.5 Knowledge Decay in Complex Domains

The classical Ebbinghaus forgetting curve (50% lost in 1 hour, 90% in 7 days) applies primarily to meaningless or isolated information. For complex, integrated knowledge:

- Knowledge well-integrated into prior schemas is **far more resistant** to forgetting
- "Real learning is not about memorizing nonsense words... [memories] operate within richly interconnected networks of significance, contextual embedding, and pre-existing frameworks of meaning"
- **Gist traces** (essential meaning, frameworks, arguments) persist much longer than **verbatim traces** (specific facts, examples, names) — from Brainerd & Reyna's Fuzzy-Trace Theory

**Implication for Petrarca:** The system should model knowledge decay differently for different types of knowledge:
- **Scaffold facts** (dates, key figures, key events): Decay at roughly SRS-predictable rates, but decay is slowed when facts are connected to the scaffold
- **Frameworks/arguments** (Pirenne thesis, causes of Greek colonization): Decay much more slowly; a single well-timed reconnection can restore the full framework
- **Connections** (cross-domain links, temporal parallels): May actually *strengthen* with time if the user encounters related material, even without explicit review

---

## 6. Voice-Based Knowledge Elicitation

### 6.1 Think-Aloud Protocols

**Ericsson & Simon (1993)**, *Protocol Analysis: Verbal Reports as Data* (MIT Press): The foundational methodological text establishing think-aloud protocols as valid cognitive data. Think-aloud involves "participants thinking aloud as they are performing a set of specified tasks" — revealing cognitive processes, not just final products.

Two types:
- **Concurrent verbalization**: Thinking aloud *during* a task
- **Retrospective reporting**: Describing thought processes *after* task completion

For knowledge assessment, the critical variant is **free recall with elaboration** — "tell me everything you know about X and explain the connections" — which combines free recall (section 2) with self-explanation (a proven learning intervention).

### 6.2 NLP Analysis of Verbal Protocols

A highly relevant 2025 paper: **"Think-aloud verbal protocols and natural language processing to capture coherence building across narrative media"** (*Discourse Processes*) demonstrates using NLP to analyze verbal protocols for:
- **Lexical cohesion**: Do participants use consistent terminology? Do they link back to earlier concepts?
- **Semantic cohesion**: Do participants' statements form a coherent mental model?
- **Content overlap**: How much of the source material is represented?

"NLP techniques are suitable for analyzing verbal protocols as a means to assess coherence-building processes."

### 6.3 Measuring Coherence, Completeness, and Accuracy from Speech

**Coh-Metrix** (McNamara et al., 2004, *Behavior Research Methods*): A computational tool analyzing text on 200+ measures of cohesion, language, and readability. Unlike simple readability formulas that rely on word/sentence length, Coh-Metrix is "sensitive to cohesion relations, world knowledge, and language and discourse characteristics." Originally designed for analyzing *texts*, but applicable to analyzing *transcripts* of spoken explanations.

Key Coh-Metrix indices relevant to knowledge assessment from voice dumps:
- **Referential cohesion**: Do successive sentences share concepts? (indicates connected knowledge)
- **Deep cohesion**: Are causal/logical connectives present? (indicates understanding of relationships)
- **LSA (Latent Semantic Analysis) overlap**: How semantically related are adjacent statements?
- **Lexical diversity**: Broader vocabulary suggests richer knowledge representation

**Automated scoring of spoken responses** (Wang et al., 2017, SLATE; Wang et al., 2024, arXiv:2409.07064): Modern systems assess spoken language proficiency across three dimensions:
1. **Delivery**: Pronunciation, fluency, prosody
2. **Language use**: Grammar, lexical choice
3. **Topic development**: Content and coherence — the most relevant for knowledge assessment

The coherence dimension assesses "the level of connectedness and logical flow of different parts in a candidate's response" — directly applicable to evaluating voice knowledge dumps.

### 6.4 Automated Scoring of Scientific Explanations

**Kim et al. (2026)**, "NLP-enabled automated assessment of scientific explanations" (*British Journal of Educational Technology*): Demonstrated that NLP can score scientific explanations while "eliminating linguistic discrimination" — assessing content quality rather than language proficiency. This is important for Petrarca because the user may explain concepts informally or in mixed languages.

### 6.5 Kintsch's Construction-Integration Model

**Walter Kintsch (1988, 1998)**, *Comprehension: A Paradigm for Cognition* (Cambridge): The CI model describes comprehension as a two-phase process:
1. **Construction**: Reader activates memory of text elements and general knowledge (bottom-up, relatively passive)
2. **Integration**: Activated knowledge is integrated, with irrelevant activations suppressed and relevant ones strengthened

The model distinguishes three levels of representation:
- **Surface form**: The exact words/phrasing
- **Textbase**: The explicit propositions stated in the text
- **Situation model**: The mental representation of the *situation described by the text*, integrating text information with prior knowledge

"Deeper comprehension depends upon the construction of a situation model — the representation of the situation described by the text rather than only a mental representation of the text itself."

**Implication for Petrarca:** When analyzing voice dumps, the system should assess which level the user's recall operates at:
- **Surface form recall** ("the book said that...") = weak understanding
- **Textbase recall** (can state the main propositions) = moderate understanding
- **Situation model recall** (can explain *why* things happened, make inferences, connect to other knowledge) = strong understanding

This could be operationalized by checking whether the user's explanation includes: causal language ("because," "led to," "as a result"), counterfactual reasoning ("if X hadn't happened"), perspective-taking ("the Greeks saw this as"), and cross-source connections ("this connects to what I read in...").

---

## 7. Existing Systems for Reader Knowledge Tracking

### 7.1 Knowledge Tracing Models

**Bayesian Knowledge Tracing (BKT)** (Corbett & Anderson, 1994): The foundational model, treating knowledge as a hidden Markov process with binary states ("mastered" / "not mastered") for each skill. Parameters: P(L₀) = prior knowledge, P(T) = probability of learning, P(G) = probability of guessing correctly, P(S) = probability of slipping (knowing but answering wrong).

**Limitations for Petrarca:** BKT assumes binary mastery, which doesn't capture the graduated understanding levels Petrarca needs (unknown → mentioned → engaged → anchored). It also requires explicit response data (correct/incorrect on questions), which doesn't capture the signals Petrarca gets from reading behavior, voice dumps, and natural recall.

**Deep Knowledge Tracing (DKT)** (Piech et al., 2015, Stanford): Uses LSTM recurrent neural networks to model knowledge state as a continuous hidden vector. Produced a 25% improvement over BKT on the ASSISTments dataset (AUC = 0.86 vs 0.69). Key advantage: DKT doesn't require pre-defined skill labels — it can discover latent knowledge components from interaction data.

**Extensions of DKT** (from the 2023 survey, arXiv:2105.15106v4):
1. **Memory-aware knowledge tracing**: Explicitly models forgetting
2. **Attentive knowledge tracing**: Uses attention mechanisms to weight relevant prior interactions
3. **Graph-based knowledge tracing**: Models prerequisite relationships between skills
4. **Hybrid BKT-LSTM**: Combines interpretability of BKT with sequence modeling of neural networks

### 7.2 SPARFA: Sparse Factor Analysis

**Lan et al. (2014)**, "Sparse Factor Analysis for Learning and Content Analytics" (*JMLR*, 15, 1771-1812): SPARFA estimates learner knowledge of underlying concepts from binary response data alone (correct/incorrect). From this "limited and quantized data," SPARFA automatically discovers:
- Abstract "concepts" underlying the domain
- A graph linking each question to concepts
- Question intrinsic difficulty
- Each student's knowledge profile across concepts

**SPARFA-Trace** (Lan & Studer, 2014, KDD): Extends SPARFA to track knowledge over time, jointly tracing:
- Learner concept knowledge evolution
- Knowledge state transitions from learning resources
- Forgetting effects

**Relevance to Petrarca:** SPARFA's approach of discovering latent concepts from response data parallels Petrarca's curriculum node generation. However, SPARFA requires structured response data (questions with correct answers), while Petrarca primarily gets signals from reading behavior and free recall. A hybrid approach could use the structured review questions to calibrate the knowledge model while using reading/recall signals for continuous updates.

### 7.3 Intelligent Tutoring for Reading Comprehension

**iSTART** (McNamara et al., 2004, *Behavior Research Methods*): Interactive Strategy Training for Active Reading and Thinking. Trains readers to use self-explanation strategies: comprehension monitoring, bridging inferences, elaboration from prior knowledge. Students using iSTART produced "higher self-explanation and inference-based comprehension scores."

iSTART is the closest existing system to what Petrarca aims to do, but it focuses on *teaching reading strategies* rather than *tracking knowledge state across sources*. It works within a single text, not across a reading history.

### 7.4 Intelligent Textbooks and Reading Analytics

**Advances in Intelligent Textbooks** (Springer, 2022) describes systems that incorporate knowledge tracing into reading platforms:
- Models use both **reading data** (time on page, highlighting, scrolling) and **performance data** (quiz responses) for improved BKT
- Results show "models using two-view data significantly outperformed models using only reading data or quiz performance data"
- Reading behaviors like highlighting can explain about 13% of variance in quiz performance

### 7.5 Open Learner Models

**Bull & Kay (2016)**, "Open Learner Models as Drivers for Metacognitive Processes" (in Azevedo & Aleven, *International Handbook of Metacognition and Learning Technologies*): Open learner models make the system's model of the learner's knowledge *visible to the learner*. Research shows this supports metacognition — students who can see what the system thinks they know develop better self-regulation.

**Next-TELL independent open learner model** (2013, Springer): Built from multiple data sources over a five-week university course. "Independent open learner models built from multiple sources of data may have much to offer in supporting students' understanding of their learning."

### 7.6 Knowledge Graphs in Education

**Systematic review of knowledge graph construction in education** (PMC10847940, 2024): Knowledge graphs in education serve for "course metadata enrichment, knowledge graph construction, and prerequisite-aware course recommendation." LLMs can generate "high-quality knowledge concepts and accurate inter-conceptual relations."

**Cognitive Network Science** (Siew et al., from *Journal of Learning Analytics*, ERIC EJ1345166): Uses network science methods to study cognitive and language systems. Can "augment insights gained from knowledge networks to measure knowledge representations that learners acquire and develop." Quantifying these representations "could provide new, more nuanced ways of measuring student learning outcomes to complement commonly used benchmarks."

**Structural indicators** from network analysis include: number of nodes, number of layers, overall width, maximum layer width, centrality measures, clustering coefficients. Research identified 19 structural indicators as feature vectors for cluster analysis of knowledge maps.

### 7.7 Gap: No Existing System Does What Petrarca Aims To Do

After extensive search, **no existing system tracks a reader's knowledge state across multiple books and articles over months, using the combination of reading behavior, structured review, and free recall that Petrarca proposes.** The closest systems are:
- **Knowledge tracing models** (BKT, DKT, SPARFA): Track knowledge over time but require structured question-answer interactions, not reading
- **Intelligent textbooks**: Track reading behavior but within a single text, not across a reading history
- **Concept mapping assessment**: Captures knowledge structure but as a snapshot, not continuously
- **Open learner models**: Show knowledge state but rely on traditional assessment data

Petrarca's combination of (1) curriculum-node-based knowledge organization, (2) cross-source knowledge accumulation, (3) voice-based free recall assessment, and (4) natural spacing through reading represents a genuinely novel approach.

---

## 8. Synthesis: Implications for Petrarca

### What the Research Most Strongly Supports

1. **Knowledge organization matters more than knowledge amount.** (Chi et al., 1981; How People Learn, 2000; Schneider et al., 1989). Petrarca's curriculum node structure captures this — the system should prioritize tracking *how* nodes connect, not just *how many* the user knows.

2. **Free recall reveals knowledge structure.** (Tulving; Zemla & Austerweil, 2026; Recht & Leslie, 1988). Voice dumps are a direct implementation of free recall protocols. The system should analyze not just what's mentioned but *recall order, clustering, causal language, and cross-references*.

3. **Retrieval strengthens networks, not just items.** (Karpicke & Blunt, 2011; Anderson's spreading activation; SAMPL model). Reviewing one curriculum node can strengthen related nodes through spreading activation — the system doesn't need to review every node to maintain the network.

4. **Integrated knowledge resists retrieval-induced forgetting.** (Chan et al., 2006). Petrarca's emphasis on connections (temporal hooks, cross-domain links, entity networks) actually protects the knowledge from the negative effects of selective retrieval.

5. **The spacing effect works through natural reading.** (From the existing beyond-flashcards research doc). Reading new articles that touch on previously-learned concepts provides natural spaced retrieval with superior contextual variation compared to artificial SRS.

### Concrete Research-Backed Enhancements

**For the knowledge model:**
- Track knowledge *structure density* per domain (ratio of actual connections to possible connections between known nodes)
- Distinguish verbatim knowledge (specific facts, will decay fast) from gist knowledge (frameworks, will persist) based on Fuzzy-Trace Theory
- Model knowledge as a continuous spectrum rather than discrete levels, following DKT's approach

**For review/assessment:**
- Use elaborative retrieval (connection prompts, explanation prompts) rather than cued recall
- Interleave review across domains/periods rather than blocking by topic
- Implement CAT-like adaptive difficulty — start with broad "what do you know about X?" and drill into specific areas based on response quality

**For voice dumps:**
- Apply Coh-Metrix-style analysis to transcripts: referential cohesion, deep cohesion, causal connectives, LSA overlap
- Assess situation model quality (Kintsch) — does the user explain *why*, not just *what*?
- Compare recall organization to curriculum structure using adapted Pathfinder metrics

**For longitudinal tracking:**
- Use IRT-style growth modeling rather than simple score tracking
- Model non-linear growth (plateaus, breakthroughs, decay periods)
- Track structure evolution: how does the user's concept map change over months?

---

## Key References

### Expert-Novice Knowledge Organization
- Chi, M. T. H., Feltovich, P., & Glaser, R. (1981). "Categorization and Representation of Physics Problems by Experts and Novices." *Cognitive Science*, 5, 121-152.
- Glaser, R., & Chi, M. T. H. (1988). "Overview of Expertise Research." CMU Technical Report.
- Bransford, J., Brown, A., & Cocking, R. (2000). *How People Learn*. National Academies Press.
- Schneider, W., Korkel, J., & Weinert, F. E. (1989). "Domain-Specific Knowledge and Memory Performance." *Journal of Educational Psychology*.

### Historical Thinking
- Wineburg, S. (2001). *Historical Thinking and Other Unnatural Acts*. Temple University Press.
- Seixas, P. (2006). "Benchmarks of Historical Thinking: A Framework for Assessment in Canada."
- Seixas, P. & Morton, T. (2013). *The Big Six: Historical Thinking Concepts*.

### Free Recall and Memory Organization
- Zemla, J. C. & Austerweil, J. L. (2026). "Free Recall of Semantically Related Words Reveals Similarity Structure." *Memory & Cognition*.
- Recht, D. R. & Leslie, L. (1988). "Effect of Prior Knowledge on Good and Poor Readers' Memory of Text." *Journal of Educational Psychology*.
- Tulving, E. (1983). *Elements of Episodic Memory*. Oxford University Press.

### Concept Maps and Knowledge Structure
- Novak, J. D. & Gowin, D. B. (1984). *Learning How to Learn*. Cambridge University Press.
- Goldsmith, T. E., Johnson, P. J., & Acton, W. H. (1991). "Assessing Structural Knowledge." *Journal of Educational Psychology*.
- Schvaneveldt, R. W. (1990). *Pathfinder Associative Networks*. Ablex Publishing.

### Retrieval Practice
- Karpicke, J. D. & Blunt, J. R. (2011). "Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping." *Science*, 331, 772-775.
- Roediger, H. L. & Karpicke, J. D. (2006). "Test-Enhanced Learning." *Psychological Science*, 17, 249-255.
- Anderson, M. C., Bjork, R. A., & Bjork, E. L. (1994). "Remembering Can Cause Forgetting." *Journal of Experimental Psychology: Learning, Memory, and Cognition*.
- Chan, J. C. K., McDermott, K. B., & Roediger, H. L. (2006). "Retrieval-Induced Facilitation." *Journal of Experimental Psychology: General*.

### Spreading Activation
- Anderson, J. R. (1983). "A Spreading Activation Theory of Memory." *Journal of Verbal Learning and Verbal Behavior*.
- Collins, A. M. & Loftus, E. F. (1975). "A Spreading-Activation Theory of Semantic Processing." *Psychological Review*.

### Knowledge Tracing
- Corbett, A. T. & Anderson, J. R. (1994). "Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge." *User Modeling and User-Adapted Interaction*.
- Piech, C. et al. (2015). "Deep Knowledge Tracing." *Advances in Neural Information Processing Systems*.
- Lan, A. S. et al. (2014). "Sparse Factor Analysis for Learning and Content Analytics." *JMLR*, 15, 1771-1812.

### Text Comprehension and NLP
- Kintsch, W. (1998). *Comprehension: A Paradigm for Cognition*. Cambridge University Press.
- McNamara, D. S. et al. (2004). "Coh-Metrix: Analysis of Text on Cohesion and Language." *Behavior Research Methods*.
- McNamara, D. S. et al. (2004). "iSTART: Interactive Strategy Training for Active Reading and Thinking." *Behavior Research Methods*.

### Longitudinal Assessment
- Wang, C. & Nydick, S. W. (2020). "On Longitudinal Item Response Theory Models: A Didactic." *Journal of Educational and Behavioral Statistics*.
- Lee, M. P. (2023). "Knowledge Tracing Over Time: A Longitudinal Analysis." *Educational Data Mining*.

### Voice/Verbal Protocol Analysis
- Ericsson, K. A. & Simon, H. A. (1993). *Protocol Analysis: Verbal Reports as Data*. MIT Press.
- "Think-aloud verbal protocols and natural language processing to capture coherence building across narrative media." (2025). *Discourse Processes*.

---

## Sources

- [Concept Inventory — Wikipedia](https://en.wikipedia.org/wiki/Concept_inventory)
- [Chi, Feltovich, Glaser (1981) — Wiley](https://onlinelibrary.wiley.com/doi/10.1207/s15516709cog0502_2)
- [Glaser & Chi (1988) — CMU PDF](https://www.cmu.edu/teaching/resources/Research/cognitive/GlaserChi1988.pdf)
- [How People Learn — National Academies](https://www.nationalacademies.org/read/9853/chapter/5)
- [Wineburg — Historical Thinking](https://www.dedhammuseum.org/wp-content/uploads/2022/12/Thinking-Like-a-Historian.pdf)
- [Seixas — Benchmarks of Historical Thinking](https://historicalthinking.ca/sites/default/files/files/docs/Framework_EN.pdf)
- [Free Recall Reveals Similarity Structure — Springer](https://link.springer.com/article/10.3758/s13421-026-01851-z)
- [Semantic Organization in Free Recall — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5358688/)
- [Cognitive Network Models — ERIC](https://files.eric.ed.gov/fulltext/EJ1345166.pdf)
- [Schneider, Korkel, Weinert — ResearchGate](https://www.researchgate.net/publication/38138539_Domain-Specific_Knowledge_and_Memory_Performance)
- [Novak Concept Mapping — Overview](https://www.researchgate.net/publication/233985290_CONCEPT_MAP-BASED_KNOWLEDGE_ASSESSMENT_TASKS_AND_THEIR_SCORING_CRITERIA_AN_OVERVIEW)
- [Pathfinder Networks — ResearchGate](https://www.researchgate.net/publication/2409203_Using_Pathfinder_Networks_to_Examine_Structural_Knowledge)
- [Structural Assessment of Knowledge — Springer](https://link.springer.com/rwe/10.1007/978-3-319-17727-4_23-1)
- [Concept Map Computational Comparison — U. Michigan](https://public.websites.umich.edu/~cberger/compmapanalysis.htm)
- [Automated Concept Map Generation — Systematic Review](https://arxiv.org/pdf/2509.14554)
- [Karpicke & Blunt (2011) — Science](https://www.science.org/doi/10.1126/science.1199327)
- [Roediger & Karpicke (2006) — Sage](https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x)
- [Retrieval-Induced Forgetting — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0079742114000061)
- [Spreading Activation — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0022537183902013)
- [SAMPL Model — bioRxiv](https://www.biorxiv.org/content/10.1101/778563v1.full)
- [Knowledge Tracing Survey — arXiv](https://arxiv.org/html/2105.15106v4)
- [Deep Knowledge Tracing — Stanford](https://stanford.edu/~cpiech/bio/papers/deepKnowledgeTracing.pdf)
- [SPARFA — JMLR](https://jmlr.org/papers/volume15/lan14a/lan14a.pdf)
- [SPARFA-Trace — Cornell](https://www.csl.cornell.edu/~studer/papers/14KDD-sparfatrace.pdf)
- [iSTART — Springer](https://link.springer.com/article/10.3758/BF03195567)
- [Coh-Metrix — Springer](https://link.springer.com/article/10.3758/BF03195564)
- [Kintsch CI Model — PDF](https://verbs.colorado.edu/~mpalmer/Ling7800/Kintsch.pdf)
- [Think-Aloud and NLP Coherence — Taylor & Francis](https://www.tandfonline.com/doi/full/10.1080/0163853X.2025.2577634)
- [NLP Spoken Assessment Coherence — arXiv](https://arxiv.org/html/2409.07064)
- [Longitudinal IRT Models — Sage](https://journals.sagepub.com/doi/10.3102/1076998619882026)
- [CAT Survey — arXiv](https://arxiv.org/html/2404.00712v2)
- [Open Learner Models Multiple Sources — Springer](https://link.springer.com/chapter/10.1007/978-3-642-39112-5_21)
- [Knowledge Graphs in Education — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10847940/)
- [Intelligent Textbooks — Springer](https://link.springer.com/chapter/10.1007/978-3-031-09687-7_15)
- [NLP Scientific Explanation Assessment — Wiley](https://bera-journals.onlinelibrary.wiley.com/doi/full/10.1111/bjet.13596)
- [Interleaved Retrieval Practice — PDF](https://pdf.retrievalpractice.org/spacing/InterleavedRetrievalPracticePromotesScienceLearning_SanaYan_2022.pdf)
