# Petrarca: Publishable Experiments and Research Directions

**Created:** 2026-04-04
**Purpose:** Comprehensive survey of experiment designs, research methodologies, measurement tools, publication venues, and productization opportunities for the Petrarca reading knowledge tracking system.

---

## Table of Contents

1. [N=1 Experimental Methodology](#1-n1-experimental-methodology)
2. [Testable Predictions from Learning Science](#2-testable-predictions-from-learning-science)
3. [Measurement Instruments and Protocols](#3-measurement-instruments-and-protocols)
4. [Existing Datasets and Benchmarks](#4-existing-datasets-and-benchmarks)
5. [Novel Research Contributions](#5-novel-research-contributions)
6. [Technology Demonstrations](#6-technology-demonstrations)
7. [Cross-Disciplinary Connections](#7-cross-disciplinary-connections)
8. [Productization Opportunities](#8-productization-opportunities)
9. [Publication Venues](#9-publication-venues)
10. [Experiment Priority Matrix](#10-experiment-priority-matrix)

---

## 1. N=1 Experimental Methodology

### 1.1 The Self-Experimentation Tradition

Petrarca sits in a distinguished tradition. Hermann Ebbinghaus conducted all his foundational memory research (forgetting curve, spacing effect, learning curve) as a single-subject self-experimenter. His rigor -- using nonsense syllables to control for prior knowledge, metronome-paced presentation, systematic interval testing -- established that n=1 research can produce findings of lasting scientific value.

The modern Quantified Self movement has revived this tradition. The key shift is from "quantified self" to "personal science" -- structured self-experimentation with hypothesis testing, not just passive data collection. Platforms like **StudyU** (researcher-facing) and **StudyMe** (individual-facing) now provide open-source mobile apps specifically for conducting n-of-1 trials, with built-in randomization, scheduling, and statistical analysis.

**Key methodological resource:** Karkar et al. (2017), "A Framework for Self-Experimentation in Personalized Health" (PMC6095104), which describes completely randomized single-case designs with permutation-based statistical tests that don't require parametric assumptions.

### 1.2 Applicable Single-Subject Designs

#### A-B-A-B Withdrawal Design
- **Phase A (baseline):** Read without system support -- no dimming, no novelty detection, no review scheduling
- **Phase B (treatment):** Full Petrarca features active
- **Measure:** Knowledge retention at fixed intervals (e.g., 2-week and 6-week delayed tests)
- **Limitation:** Knowledge cannot be "unlearned," so pure withdrawal is impossible. However, you CAN withdraw the *review system* while continuing to read, measuring whether ongoing review maintenance matters for retention.
- **Best for:** Testing whether the review system adds value beyond initial reading

#### Multiple Baseline Design Across Domains
- **This is the strongest design for Petrarca.** With 9 curricula, you can stagger the introduction of system features across domains.
- **Example:** Start Sicily curriculum with full system support in week 1. Start Ancient Greece in week 4 (using Sicily as the treatment baseline). Start Roman Republic in week 8.
- **Measure:** Rate of knowledge acquisition (nodes progressing from unknown to mentioned to engaged to anchored) in each domain
- **If the introduction of system support consistently accelerates knowledge acquisition across domains at the point of introduction,** this provides strong evidence of causal effect without needing to withdraw the intervention
- **Advantage:** No ethical concerns about withdrawing a beneficial treatment
- **Statistical analysis:** Visual analysis of level changes + randomization tests

#### Alternating Treatments Design
- **Alternate between conditions within each study session**
- **Example:** Some review sessions use voice free recall, others use button-based multiple choice. Randomly assign each session.
- **Measure:** Retention accuracy at follow-up for items reviewed under each condition
- **Best for:** Comparing voice vs. button assessment, interleaved vs. blocked review

#### Changing Criterion Design
- **Systematically increase the "difficulty" criterion**
- **Example:** Start with requiring recall of 3 key facts per node to count as "anchored," then increase to 5, then 7
- **Measure:** Whether the system can drive knowledge depth to successively higher levels
- **Best for:** Demonstrating the system can scaffold increasingly deep knowledge

### 1.3 Statistical Methods for N-of-1

Traditional p-values assume group-level sampling. For n=1 time-series data:

1. **Randomization tests:** Permutation-based tests that compare observed treatment effect against all possible random assignments. No distributional assumptions required. Recommended by the self-experimentation framework literature.
2. **Bayesian estimation:** Compute posterior distributions for treatment effects. Particularly powerful when combining evidence across multiple domains (hierarchical models).
3. **Time-series analysis:** ARIMA or interrupted time-series analysis for detecting level/slope changes at treatment introduction points.
4. **Visual analysis + effect size:** For single-case designs, the What Works Clearinghouse (WWC) standards accept visual analysis with quantified effect sizes (Tau-U, percentage of non-overlapping data).

**Software:** R packages `scan` (single-case analysis), `SSDforR`, and `SingleCaseES`. Python: `statsmodels` for interrupted time-series.

### 1.4 Journals That Publish N=1 Studies

| Journal | Focus | Fit for Petrarca |
|---------|-------|-------------------|
| **Single Case in the Social Sciences (SCSS)** | Dedicated to single-case experimental designs across education, psychology, social work | High -- accepts educational technology studies |
| **Journal of Educational Psychology (APA)** | Now explicitly offers modules for N-of-1 designs | High -- flagship journal, very competitive |
| **Journal of Educational Data Mining (JEDM)** | Computational approaches to educational data | High -- free, open access, no APCs |
| **Behavior Research Methods** | Methodology papers with novel measurement approaches | High for measurement/tool papers |
| **Computers in Human Behavior** | Psychological effects of technology on learning | Medium-high -- USD 3,870 APC |
| **Journal of the Learning Sciences** | Deeply theoretical learning research | High if framed around learning theory |
| **Educational Psychologist** | Review and theoretical papers | Good for the "natural spacing" theoretical contribution |

---

## 2. Testable Predictions from Learning Science

### 2.1 Does the Spacing Effect Hold for Complex Domain Knowledge?

**Background:** The spacing effect is robust in lab settings with word lists and simple facts (meta-analysis of 317 studies confirms this). However, ecological validity for complex, interconnected domain knowledge learned from books remains understudied. A 2024 meta-analysis of distributed practice in classroom settings found the effect generalizes but noted the evidence base is thin for naturalistic reading contexts. Petrarca's 9 curricula with 719 nodes tracking knowledge over months would be unprecedented data.

**Experiment design:**
- **Data to collect:** For each curriculum node, record: (a) all exposure timestamps (reading, review, voice recall), (b) the interval between exposures, (c) knowledge state after each exposure
- **Analysis:** Fit a forgetting curve to each node. Compare actual retention to predictions from Ebbinghaus-style models. Test whether FSRS's DSR (Difficulty, Stability, Retrievability) model, designed for flashcards, accurately predicts retention of complex, interconnected historical knowledge.
- **Prediction:** FSRS will overestimate forgetting for well-integrated knowledge (nodes with many cross-references to other known nodes) and underestimate forgetting for isolated facts
- **Novel contribution:** First empirical data on whether flashcard-derived scheduling algorithms work for book-learned domain knowledge
- **Publish in:** Journal of Experimental Psychology: Learning, Memory, and Cognition; or JEDM

### 2.2 Does Interleaving Review Across Domains Improve Retention?

**Background:** Interleaving (mixing different types of problems/topics during practice) improves retention and transfer in lab settings. A study found interleaved physics homework produced 50% improvement on test 1 and 125% improvement on test 2 compared to blocked practice. However, for complex domain knowledge (history, science), the evidence is mixed -- learners may need baseline knowledge before interleaving becomes useful.

**Experiment design (Alternating Treatments):**
- **Condition A (blocked):** Review all Sicily nodes in sequence, then all Ancient Greece nodes
- **Condition B (interleaved):** Randomly mix nodes from different curricula in each review session
- **Measure:** (a) Retention accuracy at 2-week delayed test, (b) Cross-domain connection quality in voice recall (does interleaving produce more cross-curriculum references?)
- **Prediction:** Interleaving will improve retention for nodes that share entities across curricula (e.g., "Syracuse" appears in both Sicily and Ancient Greece curricula) but may not help for unrelated domains
- **Duration:** 8 weeks of alternating blocks
- **Novel contribution:** First test of interleaving across genuinely different knowledge domains in naturalistic reading

### 2.3 Does Voice Free Recall Outperform Button-Based Assessment?

**Background:** Free recall is one of the most powerful learning strategies. It produces a "testing effect" that strengthens memory. However, most spaced repetition systems use recognition (multiple choice) or short written answers. Voice free recall is effortful and generative -- closer to the "desirable difficulty" that Bjork's theory predicts should improve retention. Recent work (2025) shows AI can conduct scalable oral assessments at $0.42/student with Krippendorff's alpha = 0.86, exceeding the 0.80 reliability threshold.

**Experiment design (Alternating Treatments):**
- **Condition A:** Review via voice free recall (current Petrarca voice elicitation)
- **Condition B:** Review via multiple-choice questions (current ML card system)
- **Both conditions:** Same curriculum nodes, same scheduling algorithm, randomly assigned per session
- **Measure:** (a) Retention at 4-week delayed test, (b) Quality of knowledge connections revealed, (c) Time cost per review
- **Prediction:** Voice recall will produce deeper retention (especially for relational knowledge like "how did X influence Y") but take 3-4x longer per item. The time-adjusted benefit is the key question.
- **Novel contribution:** First comparison of voice vs. button assessment for complex domain knowledge tracking
- **Publish in:** LAK or AIED conference, then expand for Computers in Human Behavior

### 2.4 Does Cross-Source Reading Produce Measurable Knowledge Integration?

**Background:** The Documents Model Framework (Perfetti, Britt et al.) predicts that reading multiple texts on the same topic produces two mental representations: (a) an integrated mental model of the content, and (b) an inter-text model mapping how sources relate. Research shows prior knowledge positively predicts ability to integrate across texts, mediated by intratextual comprehension. However, tracking this process over months across books and articles has never been done.

**Experiment design:**
- **Data to collect:** For each curriculum node, track: (a) number of distinct sources (books, articles) that contributed, (b) timestamps of each source contribution, (c) knowledge state progression
- **Analysis:** Compare retention and richness of knowledge for nodes fed by 1 source vs. 2-3 sources vs. 4+ sources. Use voice recall transcripts to count intertextual references (mentions of specific books/articles or cross-source comparisons).
- **Prediction:** Nodes with 2-3 sources will show stronger retention than single-source nodes, even controlling for total exposure time. The Documents Model predicts that source diversity creates richer encoding.
- **Novel contribution:** First longitudinal tracking of cross-source knowledge integration using a personal knowledge system
- **Publish in:** Reading Research Quarterly; Frontiers in Psychology (Educational Psychology section)

### 2.5 Does Curriculum-Based Organization Improve Retention vs. Unstructured Reading?

**Background:** Meta-analyses show scaffolding produces small-to-moderate effect sizes on learning outcomes (g = 0.35-0.38 for metacognitive and strategic scaffolding). But does providing an explicit curriculum structure for personal reading -- where the reader is not a student and there is no instructor -- improve retention compared to reading the same material without organizational scaffolding?

**Experiment design (Multiple Baseline):**
- **Phase 1 (baseline, 6 weeks):** Read books on a new domain (e.g., Roman Republic) without a curriculum. Track knowledge naturally.
- **Phase 2 (treatment):** Generate a curriculum for that domain, map existing knowledge to it, continue reading with curriculum scaffolding active.
- **Measure:** Rate of knowledge state transitions (unknown -> mentioned -> engaged -> anchored) before and after curriculum introduction
- **Prediction:** Curriculum introduction will accelerate the engaged -> anchored transition by providing explicit organizational structure that makes review more targeted
- **Duration:** 12 weeks minimum per domain
- **Novel contribution:** First empirical evidence for the value of curriculum scaffolding in autonomous adult reading

### 2.6 Natural Spacing Through Related Reading

**Background:** This is potentially Petrarca's most original theoretical contribution. Traditional spacing research assumes deliberate re-exposure (flashcard review). But when a reader encounters "Syracuse" in a Sicily book, then again in an Ancient Greece book, then in an article about Mediterranean archaeology -- that's *incidental spacing* through naturalistic reading. The concept of "natural spacing" through related reading across sources has not been studied empirically.

**Experiment design:**
- **Data to collect:** For every concept/entity, log all exposures: (a) deliberate review sessions, (b) incidental encounters while reading new material on related topics
- **Analysis:** Compare retention for concepts that received: (a) only deliberate FSRS review, (b) only incidental natural spacing through reading, (c) both deliberate review + natural spacing
- **Prediction:** Natural spacing through related reading will be as effective as deliberate review for well-connected concepts (those shared across multiple curricula), because the new context provides "desirable difficulty" that strengthens encoding
- **Novel contribution:** First empirical data on incidental spacing through naturalistic reading -- a phenomenon that has been theorized but never measured
- **Publish in:** Cognition; Memory & Cognition; or Educational Psychologist (as a theoretical + empirical paper)

---

## 3. Measurement Instruments and Protocols

### 3.1 Scoring Free Recall Transcripts

**Propositional analysis** is the gold standard for scoring free recall. A proposition is the smallest unit of discourse that retains meaning. Standard protocol:

1. **Identify target propositions:** For each curriculum node, define the set of core propositions (key facts, relationships, dates, causal claims). Petrarca's `key_facts` data already contains 299 structured facts for Sicily Greek period alone.
2. **Score recall transcript:** Award 1 point per correctly recalled proposition (paraphrases and synonyms count). Partial credit for partially correct propositions.
3. **Score relational recall:** Additional credit for correctly linking two propositions with a causal or temporal relationship ("Gelon defeated Carthage at Himera *because* the Carthaginians had allied with Xerxes" = 2 propositions + 1 relational link).
4. **Score intertextual references:** Additional credit for references across sources ("Thucydides describes the Athenian expedition, but the Syracuse book focuses more on Hermocrates' defense").

**Automated scoring with LLMs:** The 2025 "council of LLMs" approach (Claude + Gemini + GPT independently score, then review each other's reasoning) achieved Krippendorff's alpha = 0.86 for oral assessment scoring. This could be adapted for Petrarca's voice recall transcripts:

1. Transcribe voice recall via Soniox API
2. Have 3 LLMs independently score against the node's key_facts checklist
3. Cross-review scores
4. Generate structured feedback on gaps and errors

**Tools:**
- **Coh-Metrix** (soletlab.asu.edu/coh-metrix): Analyzes text on 200+ measures of cohesion, language, and readability. Can measure: referential cohesion (idea overlap across sentences), deep cohesion (causal/intentional connectives), narrativity, syntactic complexity, word concreteness. Apply to recall transcripts to track changes in discourse quality over time.
- **SNAFU** (github.com/AusterweilLab/snafu-py): Semantic Network and Fluency Utility. Open-source Python library for analyzing verbal fluency data and estimating semantic networks. Implements 6 network estimation methods (First Edge, Naive Random Walk, Pathfinder, Correlation-Based, U-INVITE, Hierarchical U-INVITE). Computes cluster sizes, switches, word frequencies, intrusions, perseverations.

### 3.2 Measuring Knowledge Structure Computationally

The central insight from expertise research is that experts don't just know more facts -- they organize knowledge differently. Experts have networks with lower Average Shortest Path Length (ASPL), lower modularity, and more cross-cluster connections. Three approaches to measuring this:

#### Pathfinder Networks (PFNET)
- **Software:** JPathfinder (Java GUI, download from research-collective.com) or Pathfinder 9.0 (NMSU)
- **Input:** Pairwise relatedness ratings between concepts
- **Output:** A pruned network showing only the most important conceptual links
- **Application to Petrarca:** Generate pairwise similarity scores between curriculum nodes using claim embeddings. Compare the reader's knowledge network (based on which nodes they can recall and connect) against the "expert" curriculum structure (the full curriculum graph).
- **Key metric:** Closeness-to-expert index = correlation between reader's PFNET and expert PFNET. Track this metric over months.

#### Semantic Network Analysis from Fluency Data
- **Software:** SNAFU (Python)
- **Protocol:** Give the reader 2 minutes per domain to list all concepts/people/events they can recall. Repeat monthly.
- **Analysis:** Construct semantic networks from fluency data. Measure ASPL, clustering coefficient, and modularity over time.
- **Key finding from literature:** Experts (undergraduates) had lower ASPL and lower modularity than novices (high school students) in domain-specific networks, indicating more efficiently connected and less segregated knowledge.
- **Application:** Track whether Petrarca user's network metrics converge toward expert-like values over months of reading

#### Concept Map Comparison
- **Methods:** Similarity flooding algorithm, or simpler graph edit distance
- **Expert map:** The curriculum itself is an expert-generated concept map (719 nodes with explicit relationships)
- **Reader map:** Generated from voice recall transcripts using LLM extraction of concepts and relationships
- **Scoring:** Count matching nodes, matching links, structural similarity (spoke vs. network vs. chain patterns)
- **Literature finding:** Expert concept maps are characterized by dense networks of higher-order principles, while novice maps have fewer connections and focus on surface content

### 3.3 Calibration and Metacognition

Petrarca already has calibration data (AUROC 0.930 from session 39). This can be extended:

- **AUROC as metacognitive sensitivity:** Measures how well the user's confidence ratings differentiate correct from incorrect responses. Track over time to measure metacognitive improvement.
- **Expected Calibration Error (ECE):** Measures how well confidence matches actual accuracy across confidence bins.
- **Resolution vs. Reliability:** Decompose calibration into the ability to distinguish known from unknown (resolution) and the tendency to be accurate in confidence estimates (reliability).

---

## 4. Existing Datasets and Benchmarks

### 4.1 Knowledge Tracing Datasets

| Dataset | Size | Domain | Relevance |
|---------|------|--------|-----------|
| **XES3G5M** | 5.5M interactions, 18K students, 865 KCs | Math | Largest with KC relations -- could compare KT algorithms |
| **EdNet** | 130M interactions, 780K students | General | Largest overall -- baseline for algorithm comparison |
| **ASSISTments** (2009, 2015) | 300K+ interactions | Math | Most studied benchmark -- established baselines exist |
| **Junyi Academy** | 16M+ interactions | Math | Large-scale, Taiwan-based |

**Gap Petrarca fills:** All existing KT datasets are from math/STEM tutoring systems with short, discrete interactions. There is NO dataset for knowledge tracing in naturalistic reading of complex domain material. Publishing Petrarca's data (anonymized/single-user) would be a novel contribution to the field simply as a dataset paper.

### 4.2 Reading Comprehension Benchmarks

Existing instruments focus on standardized testing (TOEIC, NAEP, state assessments). None are designed for tracking complex domain knowledge growth over months. The Reading Process Rubric from Reading Apprenticeship comes closest, measuring metacognitive reading strategies, but it's designed for classroom observation, not automated tracking.

### 4.3 Historical Knowledge Assessment

The Digital Inquiry Group (Stanford) has developed history assessments focused on historical thinking (sourcing, corroboration, contextualization). These could serve as external validation instruments: administer their assessments before and after a 3-month period of reading with Petrarca.

**Key instruments:**
- History Assessments of Thinking (HAT) -- Stanford
- Historical Perspective Taking instruments (Hartmann & Hasselhorn, 2014)
- Swedish National Test in History -- examines epistemic cognition

### 4.4 Concept Map Scoring Rubrics

Several validated rubrics exist for scoring concept maps:
- **Novak & Gowin (1984):** Original rubric -- score propositions, hierarchy levels, cross-links, examples
- **Expert comparison method:** Score student maps against expert reference maps
- **Graph-theoretic measures:** Node count, link count, density, diameter, clustering coefficient
- **Structure classification (2025, arxiv):** Classify maps as spoke, network, or chain -- these patterns correlate with depth of understanding

---

## 5. Novel Research Contributions

### 5.1 First Longitudinal Knowledge Tracing from Naturalistic Reading

**What makes this novel:** All existing knowledge tracing (BKT, DKT) operates on tutoring system data -- discrete question-answer interactions within a single session or course. Petrarca tracks knowledge acquired through naturalistic book reading over months, with multiple sources contributing to the same knowledge items. This is fundamentally different and there is zero published work on it.

**The paper:** "Knowledge Tracing for the Long Reader: Modeling Knowledge Acquisition from Books Using Curriculum-Based Scaffolds"
- Present the Petrarca data model: curriculum nodes as knowledge components, books as source events, FSRS scheduling adapted for complex knowledge
- Compare BKT, DKT, and FSRS predictions against actual recall performance over 3-6 months
- Show where standard KT models fail (they assume discrete item interactions, not book-length reading episodes)
- Propose modifications: source multiplicity bonus, natural spacing factor, entity cross-reference strength

### 5.2 Voice Free Recall as Continuous Knowledge Assessment

**What makes this novel:** No system uses voice free recall as a *continuous, longitudinal* assessment modality for domain knowledge tracking. Clinical free recall tests (RAVLT, CVLT) are one-shot assessments. Petrarca's voice elicitation provides repeated free recall assessments on the same knowledge domains over months, scored automatically by LLMs against structured key_facts data.

**The paper:** "Tell Me What You Know: LLM-Scored Voice Free Recall for Continuous Knowledge Structure Assessment"
- Present the protocol: curriculum node prompt -> 2-minute free recall -> Soniox transcription -> multi-LLM scoring against key_facts
- Validate LLM scoring against human expert scoring (run a subset of transcripts past a domain expert)
- Show how knowledge structure metrics (propositional density, relational recall, intertextual references) change over months
- Compare voice recall sensitivity vs. multiple-choice testing for detecting partial knowledge

### 5.3 Natural Spacing Through Related Reading

**What makes this novel:** The spacing effect literature assumes deliberate, scheduled re-exposure. But readers of multiple books on related topics get incidental spacing "for free." Petrarca can uniquely measure this because it tracks both deliberate review and incidental re-encounters with concepts across different reading materials.

**The paper:** "The Natural Spacing Effect: Incidental Concept Re-Exposure Through Related Reading as a Retention Mechanism"
- Operationalize natural spacing: when concept X appears in book A (day 0) and article B (day 14), that's a 14-day natural spacing event
- Measure whether concepts that receive natural spacing show lower forgetting rates than concepts that only receive deliberate FSRS review
- Theoretical contribution: extend Bjork's desirable difficulties framework to include "incidental desirable difficulty" from encountering concepts in new contexts
- This could be the highest-impact paper because it extends a major theoretical framework

### 5.4 Curriculum Scaffolding for Autonomous Readers

**What makes this novel:** Scaffolding research focuses on instructor-provided scaffolding in classroom settings. Self-directed adult readers have no instructor. Petrarca's auto-generated curricula (Opus-generated, 50-80 nodes per domain) serve as scaffolding for autonomous reading. No one has studied whether curriculum-as-scaffold improves knowledge organization for self-directed readers.

**The paper:** "Scaffolding Without an Instructor: AI-Generated Curricula as Organizational Scaffolds for Self-Directed Reading"
- Compare knowledge organization before and after curriculum introduction using semantic network metrics
- Show how curriculum structure enables targeted review and gap identification
- Discuss implications for lifelong learning systems

### 5.5 Claim-Level Novelty Detection for Personalized Reading

**What makes this novel:** NLP novelty detection research (see Ghosal et al., 2022 in Computational Linguistics) focuses on document-level or sentence-level novelty against a corpus. Petrarca detects novelty at the *claim* level against the individual reader's *personal knowledge state*. This is a personalized novelty detection problem that has not been addressed in the NLP literature.

**The paper:** "Personal Novelty: Claim-Level Information Novelty Detection Against an Individual Reader's Knowledge Model"
- Define the "personal novelty" problem: given reader knowledge state K and article claims C, compute novelty(c_i | K) for each claim
- Present Petrarca's approach: claim embeddings, similarity against known claims, curriculum node mapping
- Evaluate: does the system's novelty score predict the reader's subjective novelty judgments?
- Show that ~70% novel + 30% familiar articles (the curiosity zone) produce the highest engagement metrics

---

## 6. Technology Demonstrations

### 6.1 Live Voice-to-Knowledge-Map Update (Best for CHI/LAK Demo)

**Setup:** User speaks into the app for 2 minutes about what they know about a topic. In real-time:
1. Voice is transcribed (Soniox streaming)
2. LLM extracts propositions and entities
3. Propositions are matched against curriculum nodes
4. Knowledge map visualization updates live, showing nodes transitioning from unknown (gray) to mentioned (yellow) to engaged (green)
5. Entity cross-references light up connections across curricula

**Impact:** This is visually dramatic and demonstrates the core value proposition: "the system listens to what you know and builds a map of your knowledge."

### 6.2 Knowledge Growth Visualization Over 3-6 Months

**Setup:** Time-lapse visualization of the knowledge map over the full history of system use:
- Animate the 9 curricula (719 nodes) transitioning from mostly-unknown to partially-known
- Show the "spreading activation" pattern: how reading one book on Sicily triggers knowledge growth across related nodes in Ancient Greece and Roman Republic curricula
- Overlay reading events (book completions, article reads) as markers on the timeline
- Show the review system maintaining knowledge that would otherwise decay

**Impact:** Demonstrates longitudinal value in a way no existing reading tool can.

### 6.3 Side-by-Side: Reader Map vs. Expert Curriculum Map

**Setup:** Split-screen display:
- Left: Full curriculum graph (the "expert" knowledge structure) with all 719 nodes
- Right: The reader's current knowledge graph (same nodes, but only known connections visible)
- Highlight: gaps where the curriculum has connections the reader hasn't yet formed
- Animate: as the reader reads more, their graph gradually converges toward the expert structure
- Metric: "Knowledge similarity score" (correlation between reader and expert network metrics)

**Impact:** Makes the abstract concept of "knowledge structure" tangible and measurable.

### 6.4 Real-Time Novelty Detection While Reading

**Setup:** Open an article on a topic the reader has been studying. In real-time:
- Paragraphs with mostly familiar content are dimmed (0.55 opacity)
- New claims are highlighted with margin annotations explaining what's new
- A "delta report" sidebar shows: "3 claims are new to you," "2 claims contradict what you knew," "5 claims add detail to existing knowledge"
- Entity mentions link to the reader's knowledge state for that entity across all curricula

**Impact:** Demonstrates personalized reading experience impossible with traditional tools.

### 6.5 Cross-Source Knowledge Integration Trace

**Setup:** Pick a curriculum node (e.g., "The Battle of Himera") and show:
- Timeline of all sources that contributed to this node: Book A chapter 3 (day 1), Article B (day 15), Book C chapter 7 (day 30), Voice recall session (day 45)
- How the knowledge state evolved with each source contribution
- What each source added that was new vs. reinforcing
- The "natural spacing" pattern: how encountering the same concept across sources produced retention without deliberate review

---

## 7. Cross-Disciplinary Connections

### 7.1 Digital Humanities + Learning Science

Petrarca bridges two fields that rarely interact:
- **Digital humanities** focuses on computational analysis of texts but not on the reader's evolving understanding
- **Learning science** focuses on knowledge acquisition but rarely uses NLP-extracted content representations

**Paper opportunity:** "From Computational Text Analysis to Computational Reader Analysis: Bridging Digital Humanities and Learning Science"
- Show how claim extraction, entity recognition, and curriculum mapping (DH techniques) can be repurposed for learning science (tracking what the reader knows)
- Venue: Digital Humanities (ADHO annual conference), or Computational Humanities Research (CHR)

### 7.2 NLP + Educational Assessment

Petrarca uses several NLP techniques for educational assessment in novel ways:
- Claim extraction from articles -> knowledge state tracking
- Entity cross-referencing across curricula -> knowledge integration measurement
- Voice transcription + propositional analysis -> free recall scoring
- Embedding similarity -> novelty detection and knowledge gap identification

**Paper opportunity:** "NLP Techniques for Personal Knowledge Assessment: Claims, Entities, and Embeddings"
- Venue: ACL Workshop on NLP for Education (BEA), or EMNLP

### 7.3 Knowledge Graphs + Personal Learning

The personal knowledge graph (PKG) research community focuses on structured data about entities and preferences. Petrarca's curriculum-based knowledge model is effectively a personal knowledge graph that tracks not just what concepts exist but *what the user knows about them*.

**Paper opportunity:** "Personal Knowledge Graphs as Learner Models: Tracking Epistemic States Across a Curriculum"
- Venue: International Semantic Web Conference (ISWC), or the LLM-TEXT2KG workshop (4th edition in 2025)

### 7.4 Cognitive Science + Reading Technology

Spreading activation theory (Collins & Loftus, 1975) predicts how activating one concept in memory activates related concepts. Petrarca's entity cross-referencing across curricula is essentially a computational implementation of spreading activation. When the reader reviews "Syracuse" in the Sicily curriculum, related concepts in the Ancient Greece curriculum should receive activation.

**Paper opportunity:** "Spreading Activation in Personal Knowledge Systems: Computational Modeling of Cross-Domain Knowledge Activation Through Reading"
- Use the `spreadr` R package to simulate spreading activation in the curriculum graph
- Compare predictions against actual recall patterns in voice assessment
- Venue: Cognitive Science Society annual conference (CogSci)

---

## 8. Productization Opportunities

### 8.1 Professional Development: Lawyers and Doctors

**Problem:** Continuing Legal Education (CLE) requires 10-15 credits per year in the US. Continuing Medical Education (CME) requires regular updates. Both professions struggle with *maintaining* domain knowledge, not just acquiring it.

**Petrarca adaptation:**
- Replace history curricula with legal/medical knowledge domains
- Track which areas of law/medicine the professional reads about and reviews
- Identify knowledge gaps and decay in critical areas
- Generate targeted review sessions for high-stakes knowledge

**Market size:** The spaced repetition software market is growing, driven by institutional adoption. The World Federation for Medical Education released updated CPD standards in 2024 emphasizing personalized, technology-supported learning.

**Competitive advantage:** Existing CME/CLE systems track completion, not knowledge state. Petrarca's curriculum-mapped knowledge tracking is fundamentally more useful.

### 8.2 Graduate Students Doing Literature Reviews

**Problem:** PhD students read hundreds of papers over 3-5 years. They struggle to: (a) remember what they've read, (b) see connections between papers, (c) identify gaps in their knowledge, (d) maintain knowledge of early-read papers while reading new ones.

**Petrarca adaptation:**
- Claim extraction from research papers -> literature-level knowledge tracking
- Curriculum = the dissertation's conceptual framework
- Novelty detection = identifying what's truly new in each paper vs. what the student already knows
- Voice recall = regular knowledge elicitation about dissertation topics

**Existing tools (partial competitors):** Zotero, Mendeley, Rayyan, Covidence -- all manage references but none track the reader's *knowledge*. Notion and Obsidian manage notes but don't automatically extract or track claims.

**Competitive advantage:** The claim-level tracking and novelty detection are unique. No existing tool tells a grad student "you've read 50 papers but still haven't encountered anything about X."

### 8.3 Lifelong Learners in Complex Domains

**Problem:** Many adults read widely in complex domains (history, science, philosophy) but have no way to: (a) track what they know across books, (b) identify what they're forgetting, (c) systematically fill knowledge gaps.

**This is the core Petrarca user.** Productization means:
- Automated curriculum generation for any domain the user is interested in
- Integration with e-readers (Kindle, Apple Books) for seamless book tracking
- Social features for book clubs to compare knowledge maps
- Voice-based knowledge check-ins as a daily habit

### 8.4 Language Learners Reading in Target Language

**Problem:** Advanced language learners need extensive reading in their target language, but struggle to track vocabulary acquisition and domain knowledge simultaneously.

**Petrarca adaptation:**
- Dual-track knowledge model: language knowledge (vocabulary, grammar) + domain knowledge (what they're reading about)
- Claim extraction in target language -> bilingual knowledge tracking
- Voice recall in target language -> pronunciation + knowledge assessment

### 8.5 Intelligence Analysts

**Problem:** Intelligence analysts must track complex, evolving situations across multiple sources. Cognitive task analysis research shows they struggle with "data fusion and correlation across incidents."

**Petrarca adaptation:**
- Replace curricula with "situation models" (e.g., a conflict, a political crisis)
- Claim extraction from intelligence reports -> situation-level knowledge tracking
- Novelty detection = identifying genuinely new intelligence vs. repeated information
- Entity cross-referencing = tracking actors across multiple situations
- Knowledge decay tracking = identifying when an analyst's understanding of a situation is going stale

**This is a high-value, low-volume market.** The U.S. intelligence community spends heavily on analyst support tools.

---

## 9. Publication Venues

### 9.1 Conference Venues (with deadlines)

| Conference | Focus | Fit | Typical Deadline | Format |
|-----------|-------|-----|------------------|--------|
| **LAK 2026** (Bergen, Norway, Apr 27 - May 1) | Learning Analytics & Knowledge | Excellent | ~Oct 2025 (past) | Full papers (16pp), short papers (10pp), demos, posters |
| **AIED 2026** (Seoul, Jun 29 - Jul 3) | AI in Education | Excellent | ~Feb 2026 | Full papers, late-breaking results, demos |
| **ITS 2026** (Pafos, Cyprus, Jun 1-5) | Intelligent Tutoring Systems | Good | ~Jan 2026 | Full papers, workshops |
| **CHI 2027** (TBD) | Human-Computer Interaction | Good for demo/system | ~Sep 2026 | Full papers, demos, workshops |
| **EDM 2026** | Educational Data Mining | Excellent | ~Feb 2026 | Full papers, short papers |
| **L@S 2026** | Learning at Scale | Good if scaling angle | Variable | Full papers |
| **CogSci 2027** | Cognitive Science | Good for spreading activation/memory | ~Feb 2027 | 6-page papers |
| **CHR 2026** | Computational Humanities Research | Good for DH angle | ~Jul 2026 | Full papers |
| **ISWC 2026** | Semantic Web | Good for knowledge graph angle | ~May 2026 | Full papers |
| **Text2KG Workshop** | LLM + Knowledge Graphs | Good | Varies by venue | Short papers |

### 9.2 Journal Venues

| Journal | Impact | APC | Review Time | Best For |
|---------|--------|-----|-------------|----------|
| **JEDM** | Medium | Free | ~3 months | Knowledge tracing, data model |
| **J. of Educational Psychology** | Very High | None (APA) | 3-6 months | N-of-1 learning study |
| **Computers in Human Behavior** | High | $3,870 | ~20 weeks | System + user study |
| **J. of the Learning Sciences** | Very High | Variable | 3-6 months | Theoretical contribution |
| **Memory & Cognition** | High | Variable | 2-4 months | Natural spacing finding |
| **Behavior Research Methods** | High | Variable | 2-4 months | Measurement tool paper |
| **Reading Research Quarterly** | Very High | Variable | 3-6 months | Multiple text integration |
| **Educational Psychologist** | Very High | Variable | 3-6 months | Theoretical review |
| **Frontiers in Psychology (Edu)** | Medium | $2,950 | 2-3 months | Faster turnaround |
| **Smart Learning Environments** | Medium | Free (OA) | 2-3 months | System description |
| **SCSS** | Low-Medium | Free | 2-3 months | Single-case design study |
| **Int. J. of STEM Education** | High | Free (OA) | 2-3 months | If framing is right |

### 9.3 Recommended Publication Strategy

**Phase 1 (now - 3 months): Conference papers and system descriptions**
1. Submit a demo/poster to **AIED 2026** (if deadline allows) or plan for **LAK 2027**
2. Submit a system paper to **JEDM** describing the knowledge tracing data model
3. Write the "natural spacing" theoretical paper and submit to **Educational Psychologist** or **Memory & Cognition**

**Phase 2 (3-6 months): Empirical studies with accumulated data**
4. Run the voice vs. button alternating treatments experiment, submit to **LAK 2027** or **AIED 2027**
5. Submit the multiple-baseline study across domains to **J. of Educational Psychology** (their N-of-1 module)
6. Submit the cross-source integration study to **Reading Research Quarterly**

**Phase 3 (6-12 months): Novel contributions**
7. Publish the longitudinal knowledge tracing dataset as a dataset paper at **EDM**
8. Submit the LLM-scored voice recall validation paper to **Computers in Human Behavior**
9. Submit the spreading activation / knowledge structure paper to **CogSci**

---

## 10. Experiment Priority Matrix

Ranked by: feasibility with current system, novelty of contribution, and publication potential.

### Tier 1: High feasibility, high impact (start now)

| Experiment | Data Needed | Duration | Where to Publish |
|-----------|-------------|----------|------------------|
| **Natural spacing measurement** | Already being collected (exposure logs across sources) | Retrospective + 3 months prospective | Memory & Cognition, Educational Psychologist |
| **Cross-source knowledge integration** | Already being collected (multiple sources per node) | Retrospective analysis + 3 months | Reading Research Quarterly |
| **Knowledge tracing dataset paper** | Already exists (curriculum nodes, states, review logs) | 1-2 months writing | JEDM, EDM conference |
| **System description paper** | Existing system | 2-3 months writing | AIED, LAK, Smart Learning Environments |

### Tier 2: Requires experimental setup, high novelty

| Experiment | Data Needed | Duration | Where to Publish |
|-----------|-------------|----------|------------------|
| **Voice vs. button assessment** | Alternating treatments design, ~50 sessions | 8-12 weeks | LAK, AIED, Computers in Human Behavior |
| **Interleaving across domains** | Blocked vs. interleaved review sessions | 8 weeks | J. of Experimental Psychology |
| **LLM-scored voice recall validation** | Expert ratings of ~50 transcripts | 4-6 weeks | Behavior Research Methods |
| **Curriculum scaffolding multiple-baseline** | New domain without curriculum, then introduce | 12+ weeks | J. of Educational Psychology |

### Tier 3: Requires significant new development

| Experiment | Data Needed | Duration | Where to Publish |
|-----------|-------------|----------|------------------|
| **Knowledge structure analysis (Pathfinder/SNAFU)** | Monthly fluency tasks + network analysis code | 6+ months | Cognitive Science, CogSci conference |
| **Claim-level novelty validation** | Subjective novelty ratings per paragraph | 3 months | ACL BEA workshop, Computational Linguistics |
| **FSRS calibration for complex knowledge** | Systematic prediction tracking over months | 6+ months | JEDM, User Modeling journal |
| **Spreading activation simulation** | R `spreadr` integration, prediction testing | 3-6 months | Cognitive Science |

---

## Appendix: Key Software Tools

| Tool | Purpose | URL |
|------|---------|-----|
| **SNAFU** | Semantic network analysis from fluency data | github.com/AusterweilLab/snafu-py |
| **JPathfinder** | Pathfinder network scaling (PFNET) | research-collective.com/PFWeb/Download.html |
| **Coh-Metrix** | Discourse coherence analysis (200+ measures) | soletlab.asu.edu/coh-metrix |
| **spreadr** | Spreading activation simulation (R) | CRAN/GitHub |
| **StudyU/StudyMe** | N-of-1 trial platform | hpi.de/lippert/projects/studyu.html |
| **EduKTM** | Knowledge tracing model implementations | GitHub |
| **scan** (R) | Single-case analysis package | CRAN |

---

## Sources

### Single-Subject Research Design
- [Single-Case Designs Technical Documentation (ERIC)](https://files.eric.ed.gov/fulltext/ED510743.pdf)
- [Single Subject Research Basics (UConn)](https://researchbasics.education.uconn.edu/single-subject-research/)
- [Single-Subject Experimental Design for Evidence-Based Practice (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3992321/)
- [Single Case in the Social Sciences Journal](https://journals.shareok.org/singlecasejournal)
- [Journal of Educational Psychology (APA)](https://www.apa.org/pubs/journals/edu/)

### N-of-1 Trials and Personal Science
- [Framework for Self-Experimentation in Personalized Health (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6095104/)
- [Personal Science: Quantified Self to Qualified Self (Ness Labs)](https://nesslabs.com/personal-science)
- [StudyMe: Mobile App for N-of-1 Trials (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9793632/)
- [StudyU Platform (JMIR)](https://www.jmir.org/2022/7/e35884)
- [N-of-1 Trials: Methodological Foundations (2026)](https://bpspubs.onlinelibrary.wiley.com/doi/10.1002/bcp.70382)
- [N-of-1 Research Design and Personal Science](https://www.researchgate.net/publication/321663197_Single_Subject_N-of-1_Research_Design_Data_Processing_and_Personal_Science)

### Spacing, Interleaving, and Desirable Difficulties
- [Distributed Practice Meta-Analysis (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12189222/)
- [Spacing Effect Stands Up to Big Data](https://link.springer.com/article/10.3758/s13428-018-1184-7)
- [Interleaving Enhances Physics Learning (Nature)](https://www.nature.com/articles/s41539-021-00110-x)
- [Desirable Difficulties (Bjork)](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/RBjork_inpress.pdf)
- [Spacing Repetitions Over Long Timescales (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5476736/)

### Multiple Text Comprehension
- [Documents Model Framework (Tandfonline)](https://www.tandfonline.com/doi/full/10.1080/00461520.2017.1328309)
- [Measuring Multiple Text Integration Review (Frontiers)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2018.02294/full)
- [Building Mental Models from Multiple Texts](https://compass.onlinelibrary.wiley.com/doi/10.1111/lnc3.12409)
- [Integrating Prior Knowledge and Multiple Texts (2025)](https://link.springer.com/article/10.1007/s11145-025-10641-z)
- [Prior Knowledge in Multiple Text Comprehension (2024)](https://www.sciencedirect.com/science/article/abs/pii/S1041608024000359)

### Knowledge Structure Assessment
- [Pathfinder Networks for Structural Knowledge](https://www.researchgate.net/publication/2409203_Using_Pathfinder_Networks_to_Examine_Structural_Knowledge)
- [SNAFU: Semantic Network and Fluency Utility (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7406526/)
- [Domain-Specific Knowledge Network Analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC9128323/)
- [Concept Map Scoring Overview](https://www.researchgate.net/publication/220795642_Scoring_concept_maps_an_overview)
- [Concept Map Assessment Through Structure Classification (2025)](https://arxiv.org/html/2503.22741v1)
- [Longitudinal Semantic Network Analysis (2024)](https://www.mdpi.com/2079-3200/12/6/56)
- [Structural Assessment of Knowledge (Springer)](https://link.springer.com/content/pdf/10.1007/978-3-319-17727-4_23-1.pdf)

### Knowledge Tracing and Educational Data Mining
- [XES3G5M Dataset (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/67fc628f17c2ad53621fb961c6bafcaf-Abstract-Datasets_and_Benchmarks.html)
- [Survey of Knowledge Tracing](https://arxiv.org/html/2105.15106v4)
- [Journal of Educational Data Mining](https://jedm.educationaldatamining.org/)
- [EDM 2026 Call for Papers](https://educationaldatamining.org/edm2026/call-for-papers/)

### LLM Assessment and Scoring
- [Scalable Oral Assessments Using Voice AI (2025)](https://arxiv.org/html/2603.18221)
- [LLM-Powered Automatic Grading (EDM 2025)](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.80/index.html)
- [LLM-Powered Automated Assessment: Systematic Review](https://www.mdpi.com/2076-3417/15/10/5683)

### NLP and Novelty Detection
- [Novelty Detection from NLP Perspective (Computational Linguistics)](https://aclanthology.org/2022.cl-1.3/)
- [NEWSCLAIMS Benchmark](https://aclanthology.org/2022.emnlp-main.403.pdf)
- [SciND: Scientific Novelty Detection via Knowledge Graphs](https://link.springer.com/article/10.1007/s00799-023-00386-x)

### Knowledge Graphs and Personal Learning
- [Personal Knowledge Graphs Ecosystem Survey](https://www.sciencedirect.com/science/article/pii/S2666651024000044)
- [LLM-Empowered Knowledge Graph Construction Survey (2025)](https://arxiv.org/html/2510.20345v1)
- [Knowledge Graphs in Education Review](https://www.sciencedirect.com/science/article/pii/S2405844024014142)

### Forgetting and Retention
- [Forgetting Curve in Dental Education (Longitudinal)](https://www.mdpi.com/2227-7102/15/9/1161)
- [Replication of Ebbinghaus' Forgetting Curve (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4492928/)
- [FSRS Algorithm (Technical Principles)](https://www.oreateai.com/blog/technical-principles-and-application-prospects-of-the-free-spaced-repetition-scheduler-fsrs/36ee752bd462235d0d5b903059bc8684)

### Reading Technology and Discourse Analysis
- [Coh-Metrix Tool](https://soletlab.asu.edu/coh-metrix/)
- [Free Recall Scoring Protocols (ERIC)](https://files.eric.ed.gov/fulltext/ED504859.pdf)
- [History Assessments of Thinking (Stanford)](https://ed.stanford.edu/sites/default/files/breakstone-summary.pdf)

### Conferences
- [LAK 2026 (Bergen, Norway)](https://www.solaresearch.org/events/lak/lak26/)
- [AIED 2026 (Seoul)](https://aied-conference.org/2026/call-for-paper)
- [CHI 2026 (Barcelona)](https://chi2026.acm.org/)
- [ITS 2026 (Pafos, Cyprus)](https://iis-international.org/its2026/)

### Professional Development and Markets
- [Spaced Repetition Software Market Report](https://growthmarketreports.com/report/spaced-repetition-software-market)
- [WFME CPD Standards 2024](https://wfme.org/wp-content/uploads/2025/02/WFME-Standards-for-Continuing-Professional-Development_2024_final.pdf)
- [Continuing Legal Education Overview](https://onlinemasteroflegalstudies.com/resources/continuing-legal-education-and-professional-development/)

### Spreading Activation and Cognitive Models
- [Spreading Activation Theory (Wikipedia)](https://en.wikipedia.org/wiki/Spreading_activation)
- [spreadr R Package](https://link.springer.com/article/10.3758/s13428-018-1186-5)
- [Network Approaches to Semantic Memory (Review)](https://onlinelibrary.wiley.com/doi/10.1111/tops.12548)

### Open Learner Models
- [Open Learner Models and Visual Learning Analytics](https://www.researchgate.net/publication/290510384_New_Opportunities_with_Open_Learner_Models_and_Visual_Learning_Analytics)
- [Open Learner Models in Smart Learning Environments](https://www.igi-global.com/gateway/chapter/219035)

### Andy Matuschak / Mnemonic Medium
- [Spaced Repetition Memory System (Matuschak notes)](https://notes.andymatuschak.org/Spaced_repetition_memory_system)
- [Orbit (GitHub)](https://github.com/andymatuschak/orbit)
