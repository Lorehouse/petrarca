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
- **Key work**: GENCAT (Feb 2026) — Generative Computerized Adaptive Testing using LLMs for both response modeling and question selection. Develops a Generative Item Response Theory (GIRT) model that predicts/generates student open-ended responses, not just correctness. BOBCAT (IJCAI 2021). Won grand prize in U.S. Dept. of Education's Automated Scoring Challenge for reading comprehension.
- **Petrarca relevance**: **Highest-priority contact.** GENCAT is essentially what Petrarca does: using LLMs to assess open-ended student responses (voice recall in Petrarca's case) rather than just correct/incorrect binary outcomes. His automated scoring of reading comprehension responses directly addresses Petrarca's voice-based knowledge assessment challenge. The GIRT model's approach of predicting the content of student responses (not just correctness) aligns with Petrarca's rich knowledge state tracking.
- **Links**: [Homepage](https://people.umass.edu/~andrewlan/), [GENCAT paper](https://arxiv.org/abs/2602.20020)

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

### Jeffrey Zemla — Syracuse University
- **Role**: Department of Psychology
- **Key work**: SNAFU (Semantic Network and Fluency Utility) — tool for estimating semantic networks from verbal fluency data. "Free recall of semantically related words reveals similarity structure" (Memory & Cognition, 2026). Methods for estimating individual-level semantic networks from free recall, not just group averages.
- **Petrarca relevance**: **Directly applicable.** Zemla's method for estimating semantic networks from free recall data is essentially what Petrarca needs for voice-based knowledge assessment. When a user does a voice dump about Roman history, the order and clustering of concepts they mention reveals their mental knowledge structure. SNAFU could be adapted to analyze Petrarca's voice transcripts, comparing user knowledge networks against expert/curriculum networks. His individual-level (not just group) estimation is crucial for Petrarca's single-user model.
- **Links**: [SNAFU tool](https://pubmed.ncbi.nlm.nih.gov/32128696/), [Semantic networks from free recall](https://link.springer.com/article/10.3758/s13421-026-01851-z)

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
- **Key work**: "Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping" (Science, 2011). Showed retrieval practice is superior to concept mapping for meaningful learning. Documented that students lack metacognitive awareness of testing benefits.
- **Petrarca relevance**: Karpicke's work validates Petrarca's voice-based free recall as the assessment mechanism — it's literally retrieval practice. However, his finding that retrieval practice beats concept mapping creates a tension with Petrarca's curriculum-as-concept-map approach. Resolution: Petrarca uses curriculum structure for organization but voice recall for assessment, combining both strengths. His finding about students' poor metacognition about testing supports Petrarca's "system manages your memory" principle.
- **Links**: [Purdue Learning Lab](https://learninglab.psych.purdue.edu/)

### Nate Kornell — Williams College
- **Role**: Professor of Cognitive Psychology
- **Key work**: Spacing effects in concept/category learning (with Bjork). Key finding: spacing helps induction even though participants believe massing is more effective — a metacognitive illusion. Research on how failed tests potentiate subsequent study.
- **Petrarca relevance**: Kornell's work on spacing in category learning (not just word pairs) is more applicable to Petrarca than standard spacing research. His finding that people mistakenly prefer massed study supports Petrarca's design: the system should space reading across topics even if users want to binge one topic. His work on failed tests as beneficial aligns with Petrarca's approach of not penalizing incorrect voice recalls.
- **Links**: [Williams homepage](https://sites.williams.edu/nk2/)

### Burr Settles / Duolingo Research Team
- **Role**: Head of Research & AI, Duolingo
- **Key work**: Half-Life Regression (HLR) model (ACL, 2016) — combines psycholinguistic theory with ML, estimates memory half-life per item. BirdBrain — proprietary model that simultaneously estimates exercise difficulty and learner proficiency, processing ~1B exercises/day. Improved daily engagement by 12%.
- **Petrarca relevance**: HLR provides a concrete, implementable model for Petrarca's knowledge decay tracking. Rather than Petrarca's current knowledge levels (unknown → mentioned → engaged → anchored), HLR would assign each curriculum node a half-life that evolves with reading exposure. BirdBrain's dual estimation (content difficulty + learner state) maps to Petrarca's need to jointly model article complexity and user knowledge. However, Duolingo operates on discrete vocabulary items; Petrarca's challenge is adapting this to fluid conceptual knowledge.
- **Links**: [Blog post on BirdBrain](https://blog.duolingo.com/learning-how-to-help-you-learn-introducing-birdbrain/), [HLR paper](https://research.duolingo.com/papers/settles.acl16.pdf)

---

## 6. Andy Matuschak's Network

### Andy Matuschak — Independent Researcher
- **Key work**: The "mnemonic medium" — embedding spaced repetition review within narrative prose (Quantum Country, with Michael Nielsen). "How can we develop transformative tools for thought?" (2019, with Nielsen). Concept of "timeful texts" — texts with an authored time dimension.
- **Petrarca relevance**: Matuschak's work is the most direct intellectual ancestor of Petrarca. Key differences: Matuschak embeds author-written prompts within text; Petrarca auto-generates knowledge tracking from unmodified articles. Matuschak uses flashcard-style prompts; Petrarca uses voice-based free recall. Matuschak's insight that the mnemonic medium creates "ongoing contact with material" is exactly Petrarca's review system design. His finding that "exponential returns in memory stability" are achievable with review validates the approach. His struggle with downstream impact measurement (failed university experiments) suggests Petrarca's rich logging could provide the data he needs.
- **Links**: [Notes](https://notes.andymatuschak.org/Mnemonic_medium), [Timeful texts](https://notes.andymatuschak.org/zAb9R6nYuTyN6PBC4rQY9aY), [Impact through intimacy](https://andymatuschak.org/impact-through-intimacy/)

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
1. **Andrew Lan (UMass)** — Adapt GENCAT for reading assessment. Joint paper on open-ended knowledge tracing from voice recall.
2. **Jeremy Manning (Dartmouth)** — Apply his Naturalistic Free Recall methods to Petrarca's voice data. Joint dataset/analysis paper.
3. **Jeffrey Zemla (Syracuse)** — Apply SNAFU network estimation to Petrarca's voice transcripts. Compare user knowledge networks against curriculum structures.
4. **Alexandra List (Penn State)** — Use Petrarca's data to study her multiple-text integration framework longitudinally in a naturalistic setting.
5. **Ivar Braten (Oslo)** — Natural geographic connection (Norwegian). Study epistemic cognition in Petrarca's reading patterns.
6. **Danielle McNamara (ASU)** — Apply Coh-Metrix to Petrarca's article corpus. Integrate iSTART-style strategy instruction.
7. **Ryan Baker (UPenn)** — Apply his EDM methods to Petrarca's interaction logs.
8. **CHI Tools for Thought Workshop organizers (Microsoft Research et al.)** — Submit Petrarca as a system paper to CHI 2026 workshop.

---

## Priority Contact List (Ranked by Relevance)

| Priority | Researcher | Institution | Why |
|----------|-----------|-------------|-----|
| 1 | Andrew Lan | UMass Amherst | GENCAT = LLM-based open-ended knowledge assessment. Won NCES reading comprehension scoring challenge. |
| 2 | Jeremy Manning | Dartmouth | Naturalistic Free Recall dataset + automated scoring. Closest to Petrarca's voice assessment. |
| 3 | Jeffrey Zemla | Syracuse | SNAFU for estimating knowledge networks from recall data. |
| 4 | Alexandra List | Penn State | 2025 framework for prior knowledge + multiple text integration. |
| 5 | Ivar Braten | U of Oslo | Multiple document comprehension + epistemic cognition. Norwegian. |
| 6 | Danielle McNamara | ASU | iSTART + Coh-Metrix. Learning Engineering Institute director. |
| 7 | Marti Hearst | UC Berkeley | Semantic Reader + Learning@Scale founder. |
| 8 | Chris Piech | Stanford | DKT originator. Education AI focus. |
| 9 | Ryan Baker | UPenn | EDM methods + KT fairness across reading ability. |
| 10 | Bjorn Herrmann | U of Toronto | LLM-based automated speech recall scoring across languages. |

---

## Highest-Value Research Papers for Petrarca (Must-Read)

1. Feng & Lan (2026). "GENCAT: Generative Computerized Adaptive Testing." arXiv 2602.20020.
2. Herrmann (2025). "Language-Agnostic Automated Assessment of Listeners' Speech Recall Using LLMs." PMC12125525.
3. Manning et al. (2024). "The Naturalistic Free Recall Dataset." Scientific Data.
4. List (2025). "Integrating prior knowledge and multiple texts: expanding the Documents Model Framework." Reading and Writing.
5. Zemla (2026). "Free recall of semantically related words reveals similarity structure." Memory & Cognition.
6. Liu et al. (2024). "A Survey of Knowledge Tracing: Models, Variants, and Applications." IEEE TLT.
7. CHI 2025 Tools for Thought Workshop synthesis (2025). arXiv 2508.21036.
8. "Is there a better way to forget? Modelling memory decay in DKT." Knowledge-Based Systems (2025).
