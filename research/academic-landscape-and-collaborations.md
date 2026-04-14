# Academic Landscape: Researchers and Directions Relevant to Petrarca

*Compiled April 2026. For each researcher/group: name, institution, key work, and specific relevance to Petrarca's approach.*

---

## 1. Knowledge Tracing Researchers

### Chris Piech — Stanford University
- **Role**: Assistant Professor (Teaching) of CS and Education
- **Key work**: "Deep Knowledge Tracing" (NeurIPS 2015) — foundational paper using RNNs to model student knowledge evolution from interaction sequences. Recent work (2024): TeachNow (spontaneous 1:1 help in massive courses), handwritten code recognition, and effective error messages at scale. Co-founded Code in Place (free global CS course, 1000+ volunteer teachers).
- **Petrarca relevance**: DKT is the foundation of all modern knowledge tracing. Piech's framing — predicting what a student knows from their interaction history — maps directly to Petrarca's challenge of inferring what a reader knows from reading history + voice recall. His recent focus on learning at scale with personalized feedback aligns with Petrarca's one-user-at-scale problem. However, his work is STEM-focused (CS education), so the pitch would be: "Here's DKT applied to reading comprehension across history/humanities — a domain with no clear knowledge components."
- **Links**: [Stanford profile](https://web.stanford.edu/~cpiech/bio/index.html), [Google Scholar](https://scholar.google.com/citations?user=fpT49d8AAAAJ)

### Kenneth Koedinger — Carnegie Mellon University
- **Role**: Professor of HCI and Psychology, founding director of Pittsburgh Science of Learning Center
- **Key work**: The Knowledge-Learning-Instruction (KLI) Framework (Cognitive Science, 2012) — taxonomizes knowledge types, learning processes, and instructional methods. Draws on 400,000+ hours of human learning data. Developed Cognitive Tutor algebra software.
- **Petrarca relevance**: KLI's three knowledge types — (a) memory/fluency, (b) induction/refinement, (c) understanding/sense-making — map directly to Petrarca's knowledge levels (unknown → mentioned → engaged → anchored). KLI argues that different knowledge types need different instructional methods, which validates Petrarca's principle of "comprehension before memory" and using elaborative retrieval rather than flashcards. Koedinger's extensive empirical work on knowledge components could inform how Petrarca defines curriculum nodes.
- **Links**: [PACT Center](http://pact.cs.cmu.edu/), [KLI Framework paper](http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf)

### Ryan Baker — University of Pennsylvania
- **Role**: Professor, Penn Center for Learning Analytics
- **Key work**: Educational data mining methods for student modeling. Recent (2025): "Fairness of Bayesian Knowledge Tracing for Math Learners of Different Reading Ability" (EDM, Best Paper nominee) — explicitly linking reading ability to KT fairness. Also work on algorithmic bias in BKT.
- **Petrarca relevance**: Baker's work on the intersection of reading ability and knowledge tracing is directly relevant. His 2025 paper showing that BKT is unfair across different reading abilities implies that standard KT models don't adequately capture comprehension — exactly the problem Petrarca solves by tracking reading-level knowledge states rather than quiz performance. His methods for detecting disengaged learners could inform Petrarca's engagement metrics.
- **Links**: [Publications](https://learninganalytics.upenn.edu/ryanbaker/publications.html), [Google Scholar](https://scholar.google.com/citations?user=hvs8PEoAAAAJ)

### Qi Liu & Enhong Chen — University of Science and Technology of China (USTC)
- **Role**: School of Computer Science, Anhui Province Key Lab of Big Data Analysis
- **Key work**: Comprehensive knowledge tracing survey (IEEE TLT, 2024) covering BKT, logistic models, and deep learning models. NeuralCD cognitive diagnosis framework (IEEE TKDE, 2022). Computerized Adaptive Testing via Collaborative Ranking (NeurIPS 2024). Open-sourced EduData and EduKTM libraries.
- **Petrarca relevance**: Their survey is the definitive reference for the field. Their cognitive diagnosis work — which estimates student mastery of individual knowledge components from response patterns — could be adapted for Petrarca's curriculum-node-based knowledge estimation. Their open-source tools could serve as baselines for comparing Petrarca's approach.
- **Links**: [Qi Liu homepage](http://staff.ustc.edu.cn/~qiliuql/), [Enhong Chen homepage](http://staff.ustc.edu.cn/~cheneh/)

### Andrew Lan — UMass Amherst
- **Role**: Associate Professor, Manning College of Information and Computer Sciences
- **Key work**: GENCAT (Feb 2026) — Generative Computerized Adaptive Testing using LLMs for both response modeling and question selection. Develops a Generative Item Response Theory (GIRT) model that predicts/generates student open-ended responses, not just correctness. BOBCAT (IJCAI 2021). SPARFA (JMLR 2014, with Waters, Studer & Baraniuk) — Sparse Factor Analysis discovering latent concepts from binary response data. Won grand prize in U.S. Dept. of Education's Automated Scoring Challenge for reading comprehension.
- **GENCAT detail**: GIRT gives each student a latent knowledge vector, interpolates between learned "TRUE" and "FALSE" embeddings to condition a Llama-3.2-1B backbone. Training: SFT then DPO alignment. Three question selection strategies: uncertainty-based, diversity-based (best early), information-based (Fisher Information). Up to 4.32% AUC improvement at early testing stages (t=5). **Code status: repo listed as `github.com/umass-ml4ed/GENCAT` in paper but NOT yet public** (the lab's 25 public repos don't include it as of April 2026).
- **SPARFA-Trace** (KDD 2014): Extends SPARFA to temporal tracking using message-passing Kalman filter. Jointly traces learner knowledge over time, models transitions from learning resources, includes forgetting. Code: `bpaassen/sparfae` on GitHub (third-party Python implementation).
- **Petrarca relevance**: **Highest-priority contact.** GENCAT is the closest existing system to Petrarca's voice assessment approach. SPARFA-Trace could validate whether Petrarca's hand-crafted curriculum node structure matches the latent structure in actual review performance. His automated scoring of reading comprehension directly addresses voice-based knowledge assessment.
- **Links**: [Homepage](https://people.umass.edu/~andrewlan/), [GENCAT paper](https://arxiv.org/abs/2602.20020), [umass-ml4ed GitHub](https://github.com/umass-ml4ed)

### Jean-Claude Falmagne & Jean-Paul Doignon — UC Irvine / Université Libre de Bruxelles
- **Role**: Founders of Knowledge Space Theory (KST)
- **Key work**: *Knowledge Spaces* (1999), *Learning Spaces* (Springer, 2011). ALEKS (Assessment and LEarning in Knowledge Spaces) — commercial adaptive learning system using KST, serving 4-5 million students annually. The core innovation: model a domain as a collection of feasible "knowledge states" (sets of items a learner could plausibly know), assess by Bayesian half-split selection (pick the question where P(states containing it) ≈ 0.5), converge in ~25 questions even with millions of possible states.
- **Algorithm detail**: Continuous Markov Procedure — start with uniform probability over feasible states, Bayesian update after each response incorporating careless error (β) and lucky guess (η) rates, terminate when max(P(K)) > threshold.
- **Petrarca relevance**: The curriculum prerequisite edges already define a knowledge space. KST's adaptive assessment algorithm could be used for the "discovery probe" feature — assessing 466 uncovered nodes efficiently by exploiting prerequisite structure to infer states from a small number of probes. **Limitation:** KST assumes binary mastery; Petrarca needs graduated levels (unknown → mentioned → engaged → anchored).
- **Code**: R package `kst` on CRAN (canonical implementation, actively maintained). Python: `milansegedinac/kst` on GitHub (dormant since 2016). No mature Python implementation.
- **Links**: [ALEKS KST explanation](https://www.aleks.com/about_aleks/knowledge_space_theory), [Wikipedia: Knowledge Space](https://en.wikipedia.org/wiki/Knowledge_space)

### Jarrett Ye — Creator of FSRS (Free Spaced Repetition Scheduler)
- **Role**: Independent researcher; FSRS is now the default scheduler in Anki
- **Key work**: FSRS-6 (2025-2026) — 21-parameter scheduler using DSR model (Difficulty, Stability, Retrievability). Uses a **power forgetting curve** (not exponential) with trainable shape parameter. Published "A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition Scheduling" (ACM KDD) and "Optimizing Spaced Repetition Schedule by Capturing the Dynamics of Memory" (IEEE TKDE).
- **Algorithm**: Stability S = interval where R drops to 90%. Forgetting: R(t,S) = (1 + factor·t/S)^(-w20). After successful recall: S'_r = S·[e^(w8·(11-D)·S^(-w9)·(e^(w10·(1-R))-1)·...) + 1]. Key insight: stability saturation (S^(-w9)) means high-stability memories resist further increases.
- **Petrarca relevance**: FSRS is the most mature open-source scheduling algorithm. py-fsrs (`pip install fsrs`, v6.3.1, March 2026) includes an optimizer that trains parameters on your review history. **Critical limitation for Petrarca:** FSRS treats each item in isolation — no concept of knowledge type, semantic relationships, or partial knowledge. Binary recall only. To differentiate by type, use separate parameter presets per knowledge type (showed up to 16.9% RMSE reduction).
- **Code**: `open-spaced-repetition/fsrs4anki` (3,872 stars), `open-spaced-repetition/py-fsrs` (402 stars), `open-spaced-repetition/fsrs-rs` (Rust with Python bindings)
- **Links**: [GitHub org](https://github.com/open-spaced-repetition), [Benchmark](https://github.com/open-spaced-repetition/srs-benchmark)

### Knowledge Tracing with Forgetting
- **Key researchers**: Multiple groups working on DKT-Forget variants
- **Key work**: "Is there a better way to forget? Modelling memory decay in deep knowledge tracing" (Knowledge-Based Systems, 2025) — ablation study comparing Ebbinghaus decay, sigmoid, and inverse decay functions. KVFKT (COLING 2025) incorporating forgetting. Forgetting-aware models now represent ~9.5% of all KT studies.
- **Petrarca relevance**: Critical for Petrarca's "real decay exists" principle. These models add temporal decay features (time since last interaction, number of interactions per knowledge component) which map directly to Petrarca's "time since last read about this topic" signals. The finding that Ebbinghaus curves underperform sigmoid/inverse decay in some scenarios could inform Petrarca's knowledge level decay model.

### Philip Pavlik — University of Memphis
- **Role**: Faculty, Institute of Intelligent Systems
- **Key work**: ACT-R model of the spacing effect — a memory model where decay rate depends on current activation at time of practice (not a fixed rate). This produces the spacing effect naturally. Developed optimal practice scheduling algorithms that dynamically maximize learning by balancing temporal spacing benefits against failure costs.
- **Petrarca relevance**: Pavlik's activation-based decay model is more sophisticated than standard forgetting curves and could replace Petrarca's current knowledge level degradation approach. His optimization of practice scheduling based on long-term gain per unit of practice time aligns with Petrarca's need to decide when to resurface topics — except Petrarca's "practice" is reading articles rather than flashcards, making the scheduling problem novel.
- **Links**: [CV](https://umwa.memphis.edu/fcv/viewcv.php?personUUID=ppavlik)

---

## 2. Free Recall and Knowledge Structure Researchers

### Jeffrey Zemla — Syracuse University (and Joseph Austerweil — UW-Madison)
- **Role**: Zemla: Department of Psychology. Austerweil: Department of Psychology, UW-Madison.
- **Key work**: SNAFU (Semantic Network and Fluency Utility) — Python tool with six network estimation methods: First Edge, Naive Random Walk, Pathfinder, Correlation-based, **U-INVITE** (maximum likelihood censored random walk — assumes fluency responses follow a random walk on the semantic network), Hierarchical U-INVITE. Metrics: cluster switches, cluster sizes, perseverations, intrusions, word frequency, age-of-acquisition. Published in *Behavior Research Methods* 52, 1681-1699 (2020). Also: "Free recall of semantically related words reveals similarity structure" (*Memory & Cognition*, 2026).
- **Code**: `AusterweilLab/snafu-py` on GitHub — actively maintained (v2.6.7, Jan 2026, 397 commits, 25 stars). Install: `pip install git+https://github.com/AusterweilLab/snafu-py`. **Not on PyPI** (the `snafu` PyPI package is unrelated).
- **Adaptation needed for Petrarca**: SNAFU expects discrete items from a known vocabulary (like animal names in category fluency tasks). Voice transcripts contain sentences. Preprocessing: extract named entities and curriculum concepts from transcripts, treat them as "items" in recall order, then use U-INVITE or Pathfinder to estimate semantic network structure. Compare to curriculum graph.
- **Petrarca relevance**: **Directly applicable with adaptation.** Individual-level (not just group) network estimation is crucial for Petrarca's single-user model. The U-INVITE method is most promising — it models recall as a censored random walk, which is a reasonable model for how someone narrates what they know about a topic.
- **Links**: [SNAFU paper](https://pubmed.ncbi.nlm.nih.gov/32128696/), [GitHub](https://github.com/AusterweilLab/snafu-py), [Semantic networks from recall](https://link.springer.com/article/10.3758/s13421-026-01851-z)

### Roger Schvaneveldt — New Mexico State University (Emeritus)
- **Role**: Created Pathfinder network scaling
- **Key work**: *Pathfinder Associative Networks* (Ablex, 1990). The PFNET algorithm derives knowledge structure from similarity judgments: takes an N×N proximity matrix, prunes any direct link where a shorter indirect path exists (using Minkowski r-metric with max path length q). PFNet(N-1, ∞) produces the sparsest network. The MST-Pathfinder variant (Quirin et al., 2008) runs in O(N² log N).
- **Petrarca relevance**: Pathfinder is the theoretical basis for comparing learner knowledge structure to expert structure. We don't need raw proximity judgments — we can derive the learner's network from voice recall (which nodes are mentioned, which connections articulated) and compare to the curriculum graph.
- **Code**: Pathfinder 9.0 (commercial, not open source). R: `SemNeT` CRAN package includes `PF()` function. Python: SNAFU includes Pathfinder as one of six network estimation methods. No standalone Python PFNET library exists, but straightforward to implement via NetworkX.

### Timothy Goldsmith, Paul Johnson & William Acton — University of New Mexico
- **Key work**: "Assessing Structural Knowledge" (*Journal of Educational Psychology*, 1991). Validated Pathfinder networks as knowledge assessment tools: similarity between each student's network and the instructor's network (measured by C metric — shared links) correlated with exam performance at **r = .74**. This is among the strongest predictive validities ever found for a structural knowledge measure.
- **Three metrics**: PRX (Proximity Correlation — Pearson on raw ratings), GTD (Graph-Theoretic Distance — correlation of shortest-path distances), PFC (Pathfinder Closeness — Jaccard on per-node neighborhoods).
- **Petrarca relevance**: **The most important single finding for Petrarca's growth measurement.** The curriculum graph IS the expert network. The gap between the learner's demonstrated structure (from voice recall + review performance) and the curriculum graph, measured by PFC or edge overlap, is the single best metric of learning. Tracking this over time = tracking knowledge growth.

### Michael Kahana — University of Pennsylvania
- **Role**: Professor, Department of Psychology; Director, Computational Memory Lab
- **Key work**: Temporal Context Model (TCM) — explains how temporal context at encoding drives recall order and clustering. Context Maintenance and Retrieval (CMR/CMR2) models — generalize temporal context to include semantic knowledge and multi-list memory accumulation.
- **Petrarca relevance**: Kahana's models explain why readers recall events in temporal order and cluster related concepts together during free recall. The CMR model's idea that "memory accumulates across multiple lists" maps to Petrarca's cross-source knowledge integration — reading book A, then article B, then article C creates layered temporal-semantic associations. His data archive of free recall experiments could be used to validate Petrarca's voice analysis.
- **Links**: [Computational Memory Lab](https://memory.psych.upenn.edu/), [Publications](https://memory.psych.upenn.edu/Publications)

### Jeremy Manning — Dartmouth College
- **Role**: Director, Contextual Dynamics Lab
- **Key work**: Geometric models of how experiences become memories. "Naturalistic Free Recall" dataset (Scientific Data, 2024) — 229 participants listened to spoken narratives and freely recalled them, with high-fidelity transcriptions. Uses hidden Markov models for event segmentation of recall, word-embedding trajectories to model narrative memory.
- **Petrarca relevance**: **Extremely relevant.** Manning's Naturalistic Free Recall dataset is the closest existing research to what Petrarca does with voice knowledge dumps. His automated scoring method (using LLMs for event segmentation and embedding-based recall scoring) could be directly applied to score Petrarca's voice recalls. The finding that recalls preserve "coarse spatial properties (essential narrative elements) but not fine-scale details" validates Petrarca's approach of tracking conceptual knowledge rather than verbatim facts.
- **Links**: [Faculty page](https://faculty-directory.dartmouth.edu/jeremy-r-manning), [Naturalistic Free Recall dataset](https://www.nature.com/articles/s41597-024-04082-6)

### Bjorn Herrmann — University of Toronto / Rotman Research Institute
- **Key work**: "Language-Agnostic Automated Assessment of Listeners' Speech Recall Using Large Language Models" (2025) — fully automated pipeline using GPT-4o and LaBSE embeddings to score free recall of stories across 10 languages. Demonstrated that LLM prompt-engineering and text-embedding approaches can reliably score naturalistic speech recall.
- **Petrarca relevance**: **Directly applicable methodology.** Herrmann's pipeline (story → listen → free recall → automated LLM scoring) is almost exactly Petrarca's voice assessment workflow (articles/books → read → voice dump → LLM assessment). His dual approach (embedding similarity + LLM prompt scoring) could be implemented in Petrarca immediately. The finding that prompt-engineering approaches offer "superior interpretability with wider dynamic ranges" favors Petrarca's LLM-based assessment over pure embedding similarity.
- **Links**: [PMC paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12125525/)

---

## 3. Concept Mapping and Knowledge Graph Researchers

### Joseph Novak — Cornell University (Emeritus)
- **Role**: Developer of the concept mapping framework (1970s-80s), based on Ausubel's assimilation theory
- **Key work**: *Learning How to Learn* (Cambridge, 1984, with Gowin). Created the concept map scoring system: propositions (1 pt), hierarchy levels (5 pts), cross-links (10 pts), examples (1 pt). The heavily weighted cross-links are the key insight — they represent the most meaningful form of knowledge.
- **Petrarca relevance**: Cross-links between different curriculum areas (cross-domain connections) should be scored more heavily than within-domain connections. The 10:1 weighting of cross-links vs. propositions validates Petrarca's emphasis on temporal hooks and cross-domain connections as the highest-value knowledge. Jackson et al. (2024, *J. Engineering Education*) confirmed concept maps detect "deep content understandings as well as misconceptions."

### Alberto Canas — Institute for Human and Machine Cognition (IHMC)
- **Role**: Former Associate Director, IHMC
- **Key work**: CmapTools — the dominant concept mapping software, used worldwide. "Semantic Scoring Rubric for Concept Maps" — automated assessment of concept map quality. Expert Skeleton Concept Maps for scaffolding learning.
- **Petrarca relevance**: Canas's work on automated concept map assessment (comparing student maps to expert reference maps) parallels Petrarca's comparison of user knowledge states against curriculum structures. The "skeleton concept map" idea — providing partial expert structures for students to complete — is analogous to Petrarca's curriculum nodes acting as scaffolding that gets filled in through reading.
- **Links**: [CmapTools](https://cmap.ihmc.us/), [Research publications](https://cmap.ihmc.us/publications/research-publications.php)

### Educational Knowledge Graph Construction (Multiple Groups, 2024)
- **Key work**: "ACE: AI-Assisted Construction of Educational Knowledge Graphs with Prerequisite Relations" (JEDM, 2024) — uses ML + expert knowledge to build prerequisite graphs. CourseKG — knowledge graph from course information. K12EduKG — automatic KG construction using NER on curriculum standards.
- **Petrarca relevance**: These groups are solving Petrarca's curriculum generation problem from the opposite direction — they extract knowledge graphs from educational materials, while Petrarca generates curriculum nodes from Opus then maps articles to them. The prerequisite relation work is directly relevant to ordering Petrarca's curriculum nodes. The finding that "students who study concept pairs in prerequisite order have better success rates" validates Petrarca's curriculum-based approach.

### LLM-Assisted Knowledge Graph Completion for Curriculum (Jan 2025)
- **Key paper**: "LLM-Assisted Knowledge Graph Completion for Curriculum and Domain Modelling in Personalized Higher Education Recommendations" (arXiv 2501.12300)
- **Petrarca relevance**: This paper uses LLMs to complete educational knowledge graphs for curriculum modeling — essentially automating what Petrarca does manually with Opus-generated curriculum nodes. The personalized recommendation aspect aligns with Petrarca's feed ranking.

---

## 4. Reading Science and Comprehension Researchers

### Sam Wineburg — Stanford University
- **Role**: Margaret Jacks Professor of Education and Professor of History
- **Key work**: "Historical Thinking and Other Unnatural Acts" (2001, Ness Award winner). Created the "Reading Like a Historian" curriculum (14M+ downloads). Founded Stanford History Education Group (SHEG). Research on how historians read: sourcing, contextualization, corroboration, close reading.
- **Petrarca relevance**: Wineburg's core finding — that historical thinking is an "unnatural act" requiring explicit scaffolding — validates Petrarca's entire approach. His four strategies (sourcing, contextualization, corroboration, close reading) map to Petrarca's knowledge tracking: the system can track whether a reader is developing these skills across sources. His curriculum approach (structured document analysis) parallels Petrarca's curriculum nodes for historical domains. Potential collaboration: could Petrarca help readers develop historical thinking skills across self-selected reading?
- **Links**: [SHEG](https://sheg.stanford.edu/)

### Ivar Braten — University of Oslo, Norway
- **Role**: Emeritus Professor of Educational Psychology; Fellow of AERA and Society for Text and Discourse; Reading Hall of Fame member
- **Key work**: Pioneering research on epistemic cognition in multiple document literacy. Studies how readers' beliefs about knowledge affect how they integrate conflicting sources. "Epistemic Cognition when Students Read Multiple Documents Containing Conflicting Scientific Evidence" — think-aloud methodology with 51 Norwegian undergraduates.
- **Petrarca relevance**: **Norwegian researcher — natural geographic connection.** Braten's work on how readers integrate conflicting sources is exactly what Petrarca tracks. His finding that reading conflicting documents "led to changes in epistemic beliefs" and "better comprehension performance" suggests Petrarca should deliberately surface conflicting sources. His epistemic cognition dimensions (certainty/simplicity of knowledge, justification sources) could become additional dimensions in Petrarca's user knowledge model.
- **Links**: [UiO profile](https://www.uv.uio.no/iped/english/people/aca/ivarbr/), [Research.com profile](https://research.com/u/ivar-braten)

### Jean-Francois Rouet — University of Poitiers (Emeritus)
- **Key work**: MD-TRACE model (Multiple-Document Task-based Relevance Assessment and Content Extraction) — a cognitive process model with 5 steps: task model construction, information needs assessment, document selection/processing/integration, task product construction, product quality assessment.
- **Petrarca relevance**: MD-TRACE provides the cognitive theory for what Petrarca instrumentalizes. Rouet's model says readers construct a "task model" that guides reading — Petrarca's curriculum nodes serve this role. His "information needs assessment" (comparing prior knowledge against task demands) is exactly what Petrarca's knowledge state tracking enables. The model's emphasis on source evaluation maps to Petrarca's article metadata and entity tracking.

### M. Anne Britt — Northern Illinois University
- **Key work**: Documents Model framework — how readers build integrated representations from multiple sources, incorporating both content (intertext model) and source information. Co-developed with Rouet.
- **Petrarca relevance**: The Documents Model's distinction between "integrated situation model" (content integration) and "intertext model" (source metadata integration) maps directly to Petrarca's two-layer tracking: claim-level knowledge (content) and article-level metadata (source). Petrarca could operationalize the Documents Model by tracking how a user's integrated situation model grows across readings.

### Alexandra List — Penn State University
- **Key work**: "Integrating prior knowledge and multiple texts: expanding the Documents Model Framework" (Reading and Writing, 2025). Novel framework for how learners represent prior knowledge alongside multiple texts — along two dimensions: (1) whether they integrate or separate texts, (2) whether they use prior knowledge assimilatively or critically.
- **Petrarca relevance**: **Very recent and directly applicable.** List's 2025 framework provides exactly the theory Petrarca needs for modeling how readers integrate new articles with prior knowledge. Her distinction between "assimilative" (using prior knowledge to absorb new info) and "critical" (using prior knowledge to question/resist new info) integration could inform Petrarca's knowledge assessment — does the user's voice recall show assimilation or critical engagement?
- **Links**: [Penn State profile](https://ed.psu.edu/directory/dr-alexandra-list), [2025 paper](https://link.springer.com/article/10.1007/s11145-025-10641-z)

### Danielle McNamara — Arizona State University
- **Role**: Regents Professor (2026), Executive Director of the Learning Engineering Institute
- **Key work**: iSTART (Interactive Strategy Training for Active Reading and Thinking) — game-based ITS for reading comprehension. Coh-Metrix — text analysis tool (100+ measures of cohesion, syntax, semantics). "Chasing Theory with Technology" (Discourse Processes, 2021).
- **Petrarca relevance**: McNamara's iSTART system is the closest existing system to Petrarca's reading comprehension support. Coh-Metrix could be applied to Petrarca's articles to predict which texts need more scaffolding. Her finding that iSTART particularly helps "lower knowledge readers" through strategy instruction validates Petrarca's approach of building scaffold knowledge before deep reading. The Learning Engineering Institute's mission of "applying science of learning and AI to improve educational technology at scale" makes ASU a natural partner.
- **Links**: [ASU news](https://news.asu.edu/20260219-science-and-technology-regents-professor-recognized-pioneer-educational-technology)

### Art Graesser — University of Memphis / University of Oxford
- **Role**: Professor, Department of Psychology and Institute of Intelligent Systems; Honorary Research Fellow, Oxford
- **Key work**: AutoTutor — intelligent tutoring system using natural language dialogue for science education. Expectation-misconception tailored discourse framework. Recent (2023): work on adult literacy ITS, conversational assessment in ITS.
- **Petrarca relevance**: AutoTutor's dialogue framework (expectation vs. misconception detection via semantic analysis) could inform Petrarca's voice assessment — comparing user recall against expected knowledge components and detecting misconceptions. Graesser's finding that "question asking and answering" drives deep comprehension aligns with Petrarca's elaborative retrieval approach over flashcards.
- **Links**: [Homepage](https://sites.google.com/site/graesserart/home), [2023-2024 publications](https://sites.google.com/site/graesserart/publications/2023-2024)

---

## 5. Spaced Repetition and Memory Researchers

### Robert & Elizabeth Bjork — UCLA (Bjork Learning and Forgetting Lab)
- **Key work**: "Desirable difficulties" framework — conditions that slow initial learning but enhance long-term retention: spacing, interleaving, retrieval practice, varying conditions. The theory that we confuse "performance" (short-term) with "learning" (long-term) is central to modern learning science.
- **Petrarca relevance**: Bjork's framework is the theoretical foundation for Petrarca's design principle #3 ("comprehension before memory"). The insight that fluent processing feels like learning but isn't explains why highlighting everything feels productive but doesn't work — validating Petrarca's dim-familiar-don't-hide approach. The Bjorks' distinction between "storage strength" and "retrieval strength" could inform how Petrarca models knowledge decay: reading increases storage strength, while voice recall exercises retrieval strength.
- **Links**: [Bjork Lab](https://bjorklab.psych.ucla.edu/research/), [Publications](https://bjorklab.psych.ucla.edu/robert-a-bjork-publications/)

### Jeffrey Karpicke — Purdue University
- **Role**: Professor, Department of Psychological Sciences
- **Key work**: "Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping" (*Science*, 2011). Definitive review chapter: "Retrieval-based learning" (2025, in Wixted's *Learning and Memory*, 3rd ed., Vol. 4). The **episodic context account** (Karpicke, Lehman & Aue, 2014): retrieval practice works by forcing context reinstatement → context updating → better future retrieval cues. This explains why free recall > cued recall > recognition, and why spaced retrieval beats massed retrieval.
- **Latest (2025)**: Fordyce, Redick, Bedwell & Karpicke, "Individual differences in working memory and the benefit of retrieval practice" (*J. Memory & Language*, 144) — retrieval practice benefits **all learners regardless of working memory capacity**. The benefit is robust, not an individual-differences artifact.
- **The elaborative retrieval hypothesis** (Carpenter, 2009, extended by Karpicke): During retrieval, semantically related information is activated — testing one concept can strengthen memory for *related, untested concepts* if they're well-integrated. This means reviewing one curriculum node should strengthen related nodes through spreading activation.
- **Petrarca relevance**: Karpicke's work validates voice-based free recall as both the best assessment AND the best learning mechanism. The episodic context account explains why encountering concepts in varied contexts (different articles/books) strengthens memory more than identical reviews. The elaborative retrieval hypothesis validates Petrarca's connected curriculum: reviewing one node benefits its neighbors. **No computational tools from his lab** — his contribution is theoretical and empirical.
- **Links**: [Purdue Learning Lab](https://learninglab.psych.purdue.edu/), [Publications](https://learninglab.psych.purdue.edu/publications/)

### Charles Brainerd & Valerie Reyna — Cornell University
- **Role**: Brainerd: Professor of Human Development. Reyna: Professor of Human Development, Co-Director of Cornell's Center for Behavioral Economics and Decision Research.
- **Key work**: Fuzzy-Trace Theory (FTT) — memory encodes experiences into two parallel, independent traces: **verbatim** (exact surface details) and **gist** (semantic meaning, patterns, bottom-line interpretations). Key principles: (1) parallel storage, (2) dissociated retrieval, (3) differential survival — verbatim decays faster, (4) gist preference — people preferentially rely on gist when possible. The 2025 MINERVA2 integration (Chang, Johns & Brainerd, *Psychological Review*, 132(4)) is the first computational operationalization: gist as distributional semantic vectors, verbatim as holographic word-form vectors.
- **Decay rates**: FTT literature does NOT provide specific half-life numbers (e.g., "14 days vs 45 days"). It operates qualitatively: verbatim traces become substantially inaccessible within days-to-a-week; gist traces persist weeks-to-months. Within ~1 week, recognition is "mainly based on gist." As verbatim decays, true memory decreases but false memory increases (because gist supports confabulation while verbatim suppresses it).
- **Petrarca relevance**: **Foundational for type-differentiated scheduling.** Dates/names/specific numbers are verbatim traces → short intervals, frequent review. Frameworks/mental models/causal chains are gist traces → longer intervals, reactivation prompts. The existing key_facts `type` field (date/event/person/connection/significance) maps directly to the FTT distinction. Use qualitative principle to set initial parameters, then calibrate from actual review data.
- **Links**: [Brainerd faculty page](https://www.human.cornell.edu/people/cb299), [Reyna faculty page](https://www.human.cornell.edu/people/vr53)

### Katherine Rawson & John Dunlosky — Kent State University
- **Role**: Rawson: Professor of Psychology. Dunlosky: Professor of Psychology, former editor of *J. Experimental Psychology: General*.
- **Key work**: "Successive Relearning: An Underexplored but Potent Technique" (*Current Directions in Psychological Science*, 2022). Protocol: practice until correct, then practice again in spaced sessions until correct again. Key findings: (1) **Three relearning sessions may be sufficient** for maximal benefits. (2) Recalling items once across 3 spaced sessions > recalling each item 3 times in one session (by 2×). (3) Retention at 1 month: 68% with successive relearning vs 11% baseline. (4) **The "relearning override" effect**: extra effort to learn deeply initially doesn't persist — better to spend time on additional spaced encounters.
- **Petrarca relevance**: The relearning override finding validates Petrarca's article-based resurfacing model — encountering concepts through different articles/books is more effective than deep-drilling on first contact. The "3 sessions sufficient" finding suggests the review system should aim for 3 well-spaced encounters per node rather than continuous drilling.
- **Links**: [Rawson profile](https://www.kent.edu/psychology/profile/katherine-rawson), [Dunlosky profile](https://www.kent.edu/psychology/profile/john-dunlosky)

### Walter Kintsch — University of Colorado (Emeritus)
- **Role**: Former director of the Institute of Cognitive Science at CU Boulder
- **Key work**: Construction-Integration (CI) model (*Comprehension: A Paradigm for Cognition*, Cambridge, 1998). Defines three levels of text representation: **surface form** (exact words), **textbase** (explicit propositions), **situation model** (integrated mental representation combining text with prior knowledge). The CI model describes comprehension as: (1) construction — activate text elements and general knowledge, (2) integration — irrelevant activations suppressed, relevant ones strengthened.
- **Petrarca relevance**: Kintsch's three levels map directly to voice recall assessment: surface form recall ("the book said...") = weak; textbase recall (correct propositions) = moderate; situation model recall (explains *why*, makes inferences, connects to other knowledge) = strong. Operationalized by checking for causal language, counterfactual reasoning, perspective-taking, cross-source connections.

### Nate Kornell — Williams College
- **Role**: Professor of Cognitive Psychology
- **Key work**: Spacing effects in concept/category learning (with Bjork). Key finding: spacing helps induction even though participants believe massing is more effective — a metacognitive illusion. Research on how failed tests potentiate subsequent study.
- **Petrarca relevance**: Kornell's work on spacing in category learning (not just word pairs) is more applicable to Petrarca than standard spacing research. His finding that people mistakenly prefer massed study supports Petrarca's design: the system should space reading across topics even if users want to binge one topic. His work on failed tests as beneficial aligns with Petrarca's approach of not penalizing incorrect voice recalls.
- **Links**: [Williams homepage](https://sites.williams.edu/nk2/)

### Burr Settles / Duolingo Research Team
- **Role**: Head of Research & AI, Duolingo
- **Key work**: Half-Life Regression (HLR) model (*ACL*, 2016) — `p = 2^(-Δ/h)` where `log(h) = θ · x` (half-life is a linear function of item features). Features: times_reviewed, times_correct, item difficulty tags. Improved daily retention by 12%. BirdBrain — proprietary model estimating exercise difficulty + learner proficiency, processing ~1B exercises/day.
- **HLR advantage over FSRS for Petrarca**: The feature vector explicitly includes per-item properties. Since key_facts have `type` (date/event/person/connection/significance), HLR could learn different decay rates per type automatically. Simpler than full FSRS (no 21 parameters), directly trainable.
- **Code**: `github.com/duolingo/halflife-regression` (open source). Not pip-installable but provides the algorithm.
- **Petrarca relevance**: HLR is the most practical scheduling alternative for Petrarca's needs — simpler than FSRS, directly accommodates knowledge type via feature vectors. BirdBrain's dual estimation maps to jointly modeling article complexity and user knowledge.
- **Links**: [HLR repo](https://github.com/duolingo/halflife-regression), [HLR paper](https://aclanthology.org/P16-1174/), [BirdBrain blog](https://blog.duolingo.com/learning-how-to-help-you-learn-introducing-birdbrain/)

---

## 6. Andy Matuschak's Network

### Andy Matuschak — Independent Researcher (Patreon-funded)
- **Key work**: The "mnemonic medium" — embedding spaced repetition review within narrative prose (Quantum Country, with Michael Nielsen). "How can we develop transformative tools for thought?" (2019, with Nielsen). "Exorcising us of the Primer" (July 2024) — significant pivot critiquing authoritarian learning tools.
- **2024-2026 developments**: "How Might We Learn?" (2024) — 6-part AI-augmented learning framework (tractable immersion, guidance in action, synthesized dynamic media, contextualized study, dynamic practice, social connection). **Salience prompts** concept: distinct from retrieval prompts — designed to keep ideas top-of-mind so you notice opportunities to apply them, not just recallable on demand. Matuschak notes "the scheduling is probably all wrong" for salience prompts in current SRS. **Comprehension-before-memory pivot**: "What seems like a problem of forgetting is sometimes a problem of never having understood."
- **Orbit status**: 1,810 stars, last commit October 2024 (multiblock question/answer support). Only 4 commits in 2024, none in 2025-2026. Development appears stalled. Matuschak admitted it consumed research time: "we've learned surprisingly little about [core questions] since their introduction — mostly because I've been focused on building Orbit." **Cautionary tale for Petrarca: experiments before infrastructure.**
- **Petrarca relevance**: Matuschak's trajectory validates Petrarca's design choices (dynamic questions, voice recall, comprehension-first). The salience prompts distinction suggests curriculum framework nodes (e.g., "causes of Roman decline") should be scheduled differently from factual items — you want them to *activate when relevant*, not just be recallable. Key differences from Petrarca: Matuschak embeds author-written prompts; Petrarca auto-generates tracking from unmodified sources. Matuschak uses flashcards; Petrarca uses voice-based free recall.
- **Links**: [Notes](https://notes.andymatuschak.org/Mnemonic_medium), [Orbit repo](https://github.com/andymatuschak/orbit), [Primer essay](https://andymatuschak.org/primer/), [How Might We Learn?](https://andymatuschak.org/hmwl/)

### Michael Nielsen — Independent Researcher
- **Key work**: Co-author of Quantum Country, co-author of "How can we develop transformative tools for thought?" Wrote extensively about making memory systems widespread.
- **Petrarca relevance**: Nielsen's writing on "how to make memory systems widespread" directly addresses Petrarca's UX challenge. His observation that existing SRS tools have tiny user bases because they require too much upfront effort validates Petrarca's automatic approach (no prompt writing needed).
- **Links**: [Memory systems essay](https://michaelnotebook.com/mmsw/)

### Ink & Switch — Independent Research Lab
- **Key work**: Research on local-first software, tools for thought, end-user programming. Recent projects: Embark (reorganizing personal computing), dynamic environments for creative work. Occasional presence at academic conferences (CHI, etc.).
- **Petrarca relevance**: Ink & Switch's local-first philosophy aligns with Petrarca's server-first-but-offline-capable architecture. Their research on "tools for thought" broadly encompasses the design space Petrarca occupies. Their Embark project's idea of "separating data, functions, and interfaces" could inform Petrarca's architecture.
- **Links**: [inkandswitch.com](https://www.inkandswitch.com/)

### CHI 2025/2026 Tools for Thought Workshop Community
- **Key event**: "Tools for Thought: Research and Design for Understanding, Protecting, and Augmenting Human Cognition with Generative AI" — CHI 2025 workshop (April 26, 2025). 56 researchers, 34 papers/portfolios. Microsoft Research co-organized. CHI 2026 workshop announced.
- **Key papers**: "Augmenting Expert Cognition in the Age of Generative AI" (document-centric knowledge work), "AI, Help Me Think—but for Myself" (LLM cognitive support).
- **Petrarca relevance**: **Primary venue for presenting Petrarca's work.** This workshop is exactly the right audience. The synthesis paper (arXiv 2508.21036) frames the field as "understanding, protecting, and augmenting human cognition with GenAI" — Petrarca is a concrete implementation of all three goals applied to reading. Submitting to CHI 2026 workshop would be ideal.
- **Links**: [Workshop site](https://ai-tools-for-thought.github.io/workshop/), [Synthesis paper](https://arxiv.org/html/2508.21036v1)

---

## 7. AI and LLM for Education Researchers

### GENCAT Framework (Wanyong Feng & Andrew Lan, UMass Amherst)
- **Key paper**: "GENCAT: Generative Computerized Adaptive Testing" (arXiv, Feb 2026)
- **Innovation**: Uses LLMs to model and generate open-ended student responses, not just predict correctness. Two-step training: supervised fine-tuning then Direct Preference Optimization.
- **Petrarca relevance**: **Most directly applicable recent research.** GENCAT's core insight — that open-ended responses contain much richer information about knowledge state than binary correct/incorrect — is Petrarca's fundamental design principle. The DPO alignment step for matching predicted responses to actual knowledge states could be used to train Petrarca's voice assessment model.

### Panos Ipeirotis & George Rizakos — NYU Stern School of Business
- **Role**: Ipeirotis: Professor of Data Science. Rizakos: Research associate.
- **Key work**: "AI Oral Exams via Council of LLMs" (arXiv:2603.18221, March 2026). Developed a system where an ElevenLabs AI agent conducts ~25-minute voice exams, transcripts are graded independently by Claude, Gemini, and ChatGPT on a rubric, then models enter a **deliberation round** seeing each other's scores and critiques. Post-deliberation: 60% of ratings within 1 point, 29% exact match, Krippendorff's α = 0.86. Cost: $0.42/student vs ~$750 human.
- **Key finding**: Gemini dropped scores by 2 points on average after seeing Claude's criticism of specific gaps — the deliberation round is where real calibration happens.
- **Petrarca relevance**: **Directly implementable for voice sweep scoring.** The council approach (independent scoring → deliberation → synthesis) could replace single-model scoring for monthly knowledge sweeps, providing more reliable longitudinal measurements. Even a 2-model version (Claude + Gemini) with cross-review would improve consistency. The rubric-based approach maps to Petrarca's curriculum-node-based scoring.
- **Links**: [Paper](https://arxiv.org/abs/2603.18221), [Ipeirotis homepage](https://www.stern.nyu.edu/faculty/bio/panos-ipeirotis)

### Marti Hearst — UC Berkeley
- **Role**: Professor, School of Information and CS Division; former ACL President; CHI Academy member; ACM Fellow
- **Key work**: Semantic Reader Project (AI-powered interactive reading interfaces for scholarly documents). Co-founded ACM Learning@Scale conference. Research in NLP for education, information visualization, digital humanities.
- **Petrarca relevance**: Hearst's Semantic Reader Project — augmenting scholarly documents with AI-powered interactive reading interfaces — is the closest academic project to Petrarca's reading experience design. Her combination of NLP + HCI + education uniquely positions her to appreciate Petrarca's approach. Her digital humanities interest (digital poetry, text analysis) means she'd understand Petrarca's humanities-focused application domain.
- **Links**: [Homepage](https://people.ischool.berkeley.edu/~hearst/), [Publications](https://people.ischool.berkeley.edu/~hearst/publications.html)

### LLM-Based Automated Scoring (Emerging Field, 2024-2025)
- **Key papers**: "AutoSCORE: Enhancing Automated Scoring with Multi-Agent LLMs" (2025). "One Model to Score Them All: Unified Scoring of Learning Strategies with LLMs" (EDM 2025). "Principled Design of Interpretable Automated Scoring" (2025). Systematic review of 49 peer-reviewed LLMPAA studies.
- **Key findings**: Multi-task fine-tuning outperforms single-task for scoring generalization. GPT-4 and fine-tuned BERT achieve high agreement with human raters for reading comprehension scoring (QWK up to 0.99). Main challenge: opaque reasoning behind scores.
- **Petrarca relevance**: This literature validates Petrarca's approach of using LLMs to assess voice recall quality. The finding that multi-task training helps means Petrarca could train a single model to score recall across all curriculum domains. The interpretability challenge maps to Petrarca's need to explain knowledge assessments to the user.

### AI Tutors for History/Humanities
- **Key developments**: ChatGPT Study Mode prompting students to "reason with evidence and perspective." Humy.ai targeting history teachers. HelloHistory.ai for education.
- **Limitations identified**: AI tutors for history "cannot surprise us with new historical arguments" and "cannot substitute for rigorous historical methods." Subjects like math show greater improvement than writing or history with AI tutoring.
- **Petrarca relevance**: The finding that AI tutoring works less well for history/humanities than STEM supports Petrarca's approach of scaffolding knowledge rather than tutoring directly. Petrarca's value proposition is not "AI teaches you history" but "AI tracks what you're learning from your own reading."

---

## 8. Personal Knowledge Management Researchers

### Academic PKM Research
- **Key framework**: Personal Information Management Effectiveness (PIME) — two dimensions: motivation (proactiveness, sharing, transparency, formality) and capability (sensing, collecting, organizing, processing, maintaining). PIME accounts for 41% of variance in knowledge worker job performance.
- **Key finding**: 68% of people who adopt a PKM tool abandon it within 6 months (Forte Labs, 2021). The missing piece is a framework for deciding what to capture, how to organize, and when to use.
- **Petrarca relevance**: The 68% abandonment rate for PKM tools validates Petrarca's "system manages your memory" approach — Petrarca eliminates the meta-cognitive overhead that kills other PKM systems. The PIME framework's "maintaining" capability dimension is exactly what Petrarca automates through its knowledge tracking and review system.

### Niklas Luhmann / Zettelkasten Academic Community
- **Context**: Luhmann's 90,000-card slip-box produced 70 books and 400 scholarly articles. Modern digital implementations (Obsidian, Roam, etc.) attempt to recreate the connection-making benefits.
- **Petrarca relevance**: Petrarca's curriculum nodes + entity links function as an automated Zettelkasten — each article's claims are connected to curriculum nodes (like Zettelkasten cross-references) without requiring manual linking. This "Zettelkasten without the work" angle could resonate with the PKM community.

---

## 9. Open Research Questions Petrarca Could Address

### 1. Measuring knowledge growth in complex domains longitudinally
- **Current gap**: "Most informal science learning research has been limited in both duration and scope, designed to document results of short-term experiences" (Diserens et al., 2021). Attribution, attrition, data collection, and analytic approaches remain unsolved challenges.
- **Petrarca contribution**: Continuous tracking of a single user's reading and voice recalls over months/years, with curriculum-aligned knowledge state evolution, provides exactly the longitudinal data the field lacks. N=1 but with unprecedented depth and duration.

### 2. Whether natural spacing through reading produces measurable retention effects
- **Current gap**: Spacing effect research uses controlled lab conditions with word pairs or simple materials. No studies examine whether the natural spacing that occurs from reading different articles about related topics produces measurable retention benefits.
- **Petrarca contribution**: Petrarca logs exact reading times and knowledge assessments, enabling analysis of whether natural inter-article spacing on the same curriculum node correlates with better retention in voice recalls. This would be a genuinely novel finding.

### 3. Voice-based knowledge assessment validity
- **Current gap**: Herrmann (2025) validated automated free recall scoring for short stories. No validation exists for knowledge assessment from unconstrained voice dumps about complex learned topics.
- **Petrarca contribution**: Petrarca could validate voice-based assessment by comparing LLM-scored voice recalls against structured quiz performance on the same topics, establishing convergent validity for this novel assessment modality.

### 4. Cross-source knowledge integration in informal learning
- **Current gap**: Multiple-text comprehension research (Braten, Rouet, Britt, List) studies controlled reading of 4-6 pre-selected documents. No studies examine how self-directed readers integrate knowledge across dozens of self-selected sources over weeks.
- **Petrarca contribution**: Petrarca tracks exactly which articles and books a user reads and can measure how knowledge integration (via voice recall and curriculum node progress) develops across sources — naturalistic multiple-document comprehension at scale.

### 5. Curriculum-based knowledge organization for self-directed learners
- **Current gap**: Educational knowledge graphs are built for formal education (courses, textbooks). No systems organize knowledge for self-directed reading across heterogeneous sources.
- **Petrarca contribution**: Petrarca's Opus-generated curriculum nodes represent a novel approach to organizing informal learning. The question is whether LLM-generated curricula align with actual knowledge acquisition patterns.

### 6. How LLMs can assess understanding from free recall
- **Current gap**: GENCAT (Lan, 2026) and LLMPAA research focus on written short answers to specific questions. No research examines LLM assessment of unconstrained free recall for knowledge modeling.
- **Petrarca contribution**: Petrarca's voice → transcript → LLM assessment pipeline represents a new modality for knowledge assessment. Validating this against traditional measures would be publishable research.

### 7. Temporal hooks as a retention mechanism
- **Current gap**: The importance of temporal anchoring for historical knowledge is well-established pedagogically but not empirically measured at scale.
- **Petrarca contribution**: Petrarca's key_facts system tracks temporal associations (dates, events). Analysis of whether temporal-hook-rich content correlates with better voice recall could provide empirical evidence for this pedagogical principle.

---

## 10. Potential Venues for Publication and Funding

### Academic Conferences (by fit)
1. **CHI Tools for Thought Workshop (2026)** — Best immediate venue. Directly aligned community.
2. **Learning Analytics and Knowledge (LAK)** — Premier venue for learning analytics systems.
3. **ACM Learning@Scale** — Co-founded by Marti Hearst. Perfect for Petrarca's approach.
4. **International Conference on Educational Data Mining (EDM)** — For knowledge tracing innovations.
5. **Artificial Intelligence in Education (AIED)** — For LLM-based assessment work.
6. **Society for Text and Discourse** — For multiple-text comprehension and knowledge integration.
7. **Annual Meeting of the Cognitive Science Society** — For voice recall and knowledge structure work.

### Journals (by fit)
1. **Journal of Educational Psychology** — For empirical studies of knowledge growth through reading.
2. **Computers & Education** — For system description + evaluation papers.
3. **British Journal of Educational Technology** — For the design/implementation angle.
4. **Reading and Writing** — For multiple-text comprehension aspects.
5. **Journal of Memory and Language** — For voice recall assessment validation.
6. **Educational Technology Research and Development** — For system design papers.
7. **International Journal of Human-Computer Interaction** — For interaction design aspects.
8. **Discourse Processes** — For the comprehension monitoring angle.
9. **Learning and Instruction** — For the learning science angle.
10. **IEEE Transactions on Learning Technologies** — For the technical knowledge tracing aspects.
11. **Journal of Educational Data Mining (JEDM)** — For knowledge tracing methodology.

### Funding Programs
1. **NSF — IUSE (Improving Undergraduate STEM Education)** — Could frame Petrarca as a tool for improving reading comprehension of STEM-adjacent content.
2. **NSF — Cyberlearning and Future Learning Technologies** — Directly relevant. Petrarca is a novel cyberlearning system.
3. **EU Erasmus+ Forward-Looking Projects (Topic 7, 2025-2026)** — "Ethical and effective use of generative AI in education." Petrarca is a concrete case study. Grant agreements scheduled for February 2026.
4. **EU Erasmus+ 2026 Policy Experimentation (T03)** — "AI-powered Personalised Learning Pathways for Basic Skills."
5. **EU Horizon Europe Cluster 4 (2026)** — Trustworthy AI services calls closing April 15, 2026.
6. **Jacobs Foundation** — Funds learning science research. Focuses on evidence-based approaches.
7. **Spencer Foundation** — Funds educational research broadly.
8. **Schmidt Sciences** — Funds "hard problems in science and technology" including learning.
9. **Templeton Foundation** — Has funded work on intellectual virtues and learning.

### Potential Collaboration Models
1. **Andrew Lan (UMass)** — Adapt GENCAT for reading assessment. Joint paper on open-ended knowledge tracing from voice recall. Also: apply SPARFA-Trace to validate curriculum node structure against actual review performance.
2. **Jeremy Manning (Dartmouth)** — Apply his Naturalistic Free Recall methods to Petrarca's voice data. Joint dataset/analysis paper.
3. **Jeffrey Zemla (Syracuse)** — Apply SNAFU network estimation to Petrarca's voice transcripts. Compare user knowledge networks against curriculum structures using U-INVITE method.
4. **Panos Ipeirotis (NYU)** — Adapt Council of LLMs scoring for knowledge sweep assessment. Joint paper on multi-model deliberation for domain knowledge assessment (vs. his course-exam use case).
5. **Alexandra List (Penn State)** — Use Petrarca's data to study her multiple-text integration framework longitudinally in a naturalistic setting.
6. **Ivar Braten (Oslo)** — Natural geographic connection (Norwegian). Study epistemic cognition in Petrarca's reading patterns.
7. **Danielle McNamara (ASU)** — Apply Coh-Metrix to Petrarca's article corpus. Integrate iSTART-style strategy instruction.
8. **Ryan Baker (UPenn)** — Apply his EDM methods to Petrarca's interaction logs.
9. **Jarrett Ye (FSRS)** — Collaborate on type-differentiated scheduling; contribute Petrarca's review data as a non-flashcard benchmark for FSRS evaluation.
10. **CHI Tools for Thought Workshop organizers (Microsoft Research et al.)** — Submit Petrarca as a system paper to CHI 2026 workshop.

---

## Priority Contact List (Ranked by Relevance)

| Priority | Researcher | Institution | Why |
|----------|-----------|-------------|-----|
| 1 | Andrew Lan | UMass Amherst | GENCAT = LLM-based open-ended knowledge assessment. SPARFA-Trace for temporal tracking. Won NCES scoring challenge. |
| 2 | Jeremy Manning | Dartmouth | Naturalistic Free Recall dataset + automated scoring. Closest to Petrarca's voice assessment. |
| 3 | Jeffrey Zemla | Syracuse | SNAFU for estimating knowledge networks from recall data. Actively maintained Python code. |
| 4 | Panos Ipeirotis | NYU Stern | Council of LLMs for oral exam scoring. α=0.86 reliability. $0.42/student. |
| 5 | Alexandra List | Penn State | 2025 framework for prior knowledge + multiple text integration. |
| 6 | Ivar Braten | U of Oslo | Multiple document comprehension + epistemic cognition. Norwegian. |
| 7 | Danielle McNamara | ASU | iSTART + Coh-Metrix. Learning Engineering Institute director. |
| 8 | Marti Hearst | UC Berkeley | Semantic Reader + Learning@Scale founder. |
| 9 | Chris Piech | Stanford | DKT originator. Education AI focus. |
| 10 | Ryan Baker | UPenn | EDM methods + KT fairness across reading ability. |
| 11 | Bjorn Herrmann | U of Toronto | LLM-based automated speech recall scoring across languages. |

---

## Highest-Value Research Papers for Petrarca (Must-Read)

1. Feng & Lan (2026). "GENCAT: Generative Computerized Adaptive Testing." arXiv 2602.20020.
2. Goldsmith, Johnson & Acton (1991). "Assessing Structural Knowledge." *J. Educational Psychology*. [Pathfinder r=.74]
3. Ipeirotis & Rizakos (2026). "AI Oral Exams via Council of LLMs." arXiv 2603.18221.
4. Herrmann (2025). "Language-Agnostic Automated Assessment of Listeners' Speech Recall Using LLMs." PMC12125525.
5. Manning et al. (2024). "The Naturalistic Free Recall Dataset." *Scientific Data*.
6. Karpicke (2025). "Retrieval-based learning." In Wixted, *Learning and Memory*, 3rd ed. [Definitive review]
7. Rawson & Dunlosky (2022). "Successive Relearning." *Current Directions in Psychological Science*. [3 sessions sufficient]
8. List (2025). "Integrating prior knowledge and multiple texts." *Reading and Writing*.
9. Zemla & Austerweil (2020). "SNAFU." *Behavior Research Methods*, 52. [Tool paper]
10. Chang, Johns & Brainerd (2025). "True and false recognition in MINERVA2." *Psychological Review*, 132(4). [Computational FTT]
11. Liu et al. (2024). "A Survey of Knowledge Tracing." *IEEE TLT*.
12. CHI 2025 Tools for Thought Workshop synthesis (2025). arXiv 2508.21036.
13. Settles & Meeder (2016). "A Trainable Spaced Repetition Model." *ACL*. [Duolingo HLR]
