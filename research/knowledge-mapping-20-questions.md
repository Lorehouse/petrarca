# Adaptive Knowledge Mapping via Binary-Search Questioning

**Research Report — March 2026**

A comprehensive survey of related work, theoretical foundations, and implementation approaches for rapidly mapping personal knowledge through adaptive self-report questioning ("20 Questions for Knowledge").

---

## 1. The Idea in Brief

The core concept: use a "20 Questions" style binary search to rapidly map what a person knows about a topic. Not testing (right/wrong), but self-report — "Have you heard about the Persian Wars?" → Yes → "Do you know about the major battles?" → Yes → "Are you familiar with the Ionian Revolt that preceded them?" → No → gap identified.

The goal is to build a **personal knowledge model** efficiently — understanding what someone knows, at what level of depth, across a domain like ancient history. The system would use an LLM to dynamically generate questions, select them for maximum information gain, and construct a structured model of what the user knows and doesn't know.

This report surveys seven areas of related work, identifies what is genuinely novel, and recommends implementation approaches.

---

## 2. Knowledge Space Theory (Doignon & Falmagne)

### 2.1 Core Framework

Knowledge Space Theory (KST), introduced by Jean-Paul Doignon and Jean-Claude Falmagne in 1985, provides the most directly relevant mathematical framework. The theory formalizes a domain of knowledge as a set of items Q (problems, concepts, skills) and models a learner's **knowledge state** as the subset of Q that the learner has mastered.

Key definitions:
- **Knowledge state**: The complete set of items an individual can solve (or, in our case, knows about)
- **Knowledge structure**: The collection of all possible knowledge states — crucially, not all subsets of Q are valid states, because prerequisite relationships constrain what combinations are possible
- **Knowledge space**: A knowledge structure that is closed under union (if two states are possible, their union is also possible)
- **Learning space**: A knowledge space where you can always learn "one more thing" (every state has a single-item extension to another valid state)

### 2.2 Prerequisite Relationships and Surmise Systems

The power of KST comes from encoding prerequisite dependencies. If mastering item B requires first mastering item A, then no valid knowledge state can contain B without A. This constraint dramatically reduces the number of possible states.

A **surmise system** formalizes this: for each item q, it specifies which subsets of other items could serve as prerequisites. For example, knowing about the Ionian Revolt might require knowing about either (a) the Persian Empire's expansion OR (b) Greek colonial history — alternative prerequisite paths.

For our "20 Questions" system, this is directly applicable: knowledge of historical topics has natural prerequisite structure. You cannot meaningfully "know about" the Battle of Thermopylae without some awareness of the Persian Wars. The surmise system captures these dependencies.

### 2.3 ALEKS: The Most Successful KST Implementation

ALEKS (Assessment and LEarning in Knowledge Spaces) is the commercial realization of KST, used by millions of students in mathematics, chemistry, and statistics. Its assessment algorithm is the closest existing system to our proposed approach:

- An **adaptive assessment** uses Markovian procedures to identify a student's knowledge state in approximately **25-30 questions** — even when the underlying knowledge space contains tens of thousands of possible states
- After each answer, ALEKS updates the probability distribution over all possible knowledge states using the prerequisite structure to make inferences (if a student can solve a hard problem, they likely know the prerequisites)
- The algorithm selects the **next question for maximum discrimination** — asking the question that most effectively splits the remaining possible knowledge states
- A practical demonstration: 24 questions sufficed to pinpoint one student's knowledge state among **57,147 possible ones** — the entropy dropped to a critical low level and further questions would not be informative

### 2.4 Computational Challenges

For most real ALEKS knowledge structures, there are too many states to enumerate even with modern computing. ALEKS addresses this by partitioning the item set into several subsets and running assessment in parallel on these subsets. This partitioning approach is directly relevant to our system — we could assess knowledge of different sub-domains (Greek history, Persian history, military history) in parallel.

### 2.5 Applicability to Self-Report

KST was designed for tested knowledge (right/wrong answers to problems), but the mathematical framework applies equally well to self-reported familiarity. The prerequisite structure and adaptive assessment algorithm are agnostic to how each item's mastery is determined. KST has been extended to psychological assessment using questionnaires, with knowledge space theory jointly with formal concept analysis proposed for developing efficient adaptive tools for psychological assessment. The key insight: the prerequisite graph constrains the search space regardless of whether the signal is "solved correctly" or "self-reports familiarity."

### 2.6 Key References
- Doignon, J.-P. & Falmagne, J.-C. (1999/2011). *Knowledge Spaces* / *Learning Spaces*. Springer-Verlag.
- Falmagne, J.-C., Albert, D., Doble, C., Eppstein, D., & Hu, X. (2013). *Knowledge Spaces: Applications in Education*. Springer.
- Falmagne, J.-C. (2012). "The Assessment of Knowledge, in Theory and in Practice." ALEKS white paper.

---

## 3. Computerized Adaptive Testing (CAT) and Item Response Theory

### 3.1 Item Response Theory (IRT) Basics

IRT provides the standard psychometric framework for adaptive testing. The 3-parameter logistic (3PL) model characterizes each test item by three parameters:

- **Difficulty (b)**: The ability level at which a test-taker has a 50% chance of answering correctly
- **Discrimination (a)**: How steeply the probability of success changes around the difficulty threshold — high discrimination means the item cleanly separates those who know from those who don't
- **Guessing (c)**: The probability of getting the item right by chance (relevant for multiple-choice, less so for self-report)

The test-taker's latent ability is represented as θ (theta), estimated and updated after each response. The probability of a correct response follows a logistic curve: P(correct) = c + (1-c) × sigmoid(a(θ-b)).

### 3.2 Information-Based Item Selection

The core of CAT is selecting the next item for maximum information gain. Several criteria have been developed:

- **Maximum Fisher Information (MFI)**: Select the item whose Fisher information is highest at the current θ estimate. Fisher information is proportional to the square of the item's discrimination parameter at that point — items that most sharply distinguish the current ability estimate provide the most information.
- **Kullback-Leibler (KL) Information**: Measures the expected information gain as a divergence between posterior distributions before and after observing the response. More robust than MFI when θ is imprecisely estimated.
- **Bayesian approaches**: Minimize the expected posterior variance of θ, or equivalently maximize the expected reduction in entropy of the θ distribution.
- **Maximin criterion**: Select items that maximize the minimum information across a range of plausible θ values, making the selection robust to estimation uncertainty.

### 3.3 Limitations of Standard CAT for Knowledge Mapping

Standard CAT estimates a **single latent dimension** (θ) — it tells you "how much" someone knows but not "what specifically." Our system needs a **multidimensional model**: you might know a lot about Greek political history but little about military campaigns. Multidimensional IRT (MIRT) exists but is computationally expensive and doesn't naturally represent the structured, hierarchical nature of domain knowledge.

The key distinction: CAT asks "how much do you know?" while we ask "what do you know?" This is why KST's discrete knowledge states are more appropriate than IRT's continuous ability parameter — though IRT's item selection principles still apply.

### 3.4 GENCAT: LLM + CAT Convergence (February 2026)

A very recent paper (February 2026) introduces **GENCAT** (Generative Computerized Adaptive Testing), which directly combines LLMs with CAT:

- Develops a **Generative Item Response Theory (GIRT)** model that predicts/generates student open-ended responses, not just correctness
- Uses supervised fine-tuning followed by Direct Preference Optimization (DPO) to align predicted responses with student knowledge
- Introduces three question selection algorithms based on uncertainty, linguistic diversity, and information of sampled student responses

GENCAT is the closest existing work to our proposed system in the CAT literature, though it still focuses on testing (assessing correctness) rather than self-reported knowledge mapping.

### 3.5 Key References
- Lord, F.M. (1980). *Applications of Item Response Theory to Practical Testing Problems*. Erlbaum.
- van der Linden, W.J. & Glas, C.A.W. (Eds.) (2010). *Elements of Adaptive Testing*. Springer.
- GENCAT: https://arxiv.org/abs/2602.20020 (February 2026)

---

## 4. LLMs for Knowledge Assessment and Socratic Tutoring

### 4.1 LLM-Generated Assessment Items

Research from 2024-2025 has extensively explored using LLMs to generate assessment questions:

- **Automated question generation** across educational contexts: LLMs can generate varied question types (MCQ, short answer, essay prompts) adapted to different learning objectives. A systematic review of 49 peer-reviewed studies (2018-2024) documents widespread application in reading comprehension, language education, and computer science.
- **Quality comparison with human-authored items**: Studies in medical education comparing ChatGPT-generated and expert-created MCQs find comparable quality, with students unable to reliably distinguish AI-generated from human-authored questions.
- **Competence-based item generation**: LLMs can generate assessment items aligned to specific competence frameworks (e.g., Bloom's taxonomy levels), enabling fine-grained assessment of different knowledge depths.
- **Multi-agent automatic item generation**: A recent framework (2025) proposes using multiple LLM agents for psychological test item generation, with specialized agents for item drafting, review, bias detection, and calibration.

### 4.2 Socratic Tutoring Systems

Several systems implement Socratic-style adaptive questioning with LLMs:

- **Khanmigo** (Khan Academy, 2024): The most prominent deployed system. Rather than providing answers, it guides learners through questions, using Socratic dialogue to develop understanding. Incorporates student interests from chat history to personalize interactions. Deployed across 260+ U.S. school districts.
- **SocraticLM** (2024): Achieves a "Thought-Provoking" teaching paradigm, actively engaging students in problem-solving through guided questioning, mimicking a real classroom teacher.
- **MedTutor-R1** (2025): Medical education tutor using reinforcement learning with a three-axis rubric to refine adaptive Socratic strategies. Instruction-tuned for personalized medical teaching.
- **LPITutor** (2025): LLM-based personalized intelligent tutoring using RAG and prompt engineering, demonstrating improved academic performance.

### 4.3 Key Limitation: Testing vs. Mapping

All these systems focus on **teaching and testing** — they assess whether a student understands a specific concept and guide them toward understanding. None attempt to **map** existing knowledge rapidly. The distinction matters:
- Teaching systems assume the student is *learning* and needs guidance
- Our system assumes the user already *has* knowledge and wants to efficiently *report* it

This is a genuine gap in the literature.

### 4.4 Key References
- "The Future of Learning in the Age of Generative AI" (2024): https://arxiv.org/html/2410.09576v1
- "Large Language Model-Powered Automated Assessment" (2025): https://www.mdpi.com/2076-3417/15/10/5683
- SocraticLM: https://openreview.net/forum?id=qkoZgJhxsA
- MedTutor-R1: https://arxiv.org/html/2512.05671v1

---

## 5. Expert Knowledge Elicitation

### 5.1 Classical Techniques

Knowledge engineering has developed systematic methods for extracting what an expert knows. The most relevant for our purposes:

**Structured Interview**: The knowledge engineer plans and directs the session with prepared questions, producing structured transcripts. This is essentially what our system automates — but with an AI interviewer that adapts in real-time.

**Repertory Grid Technique**: The most commonly used construct elicitation method. The expert is presented with entities and asked to describe similarities and differences, revealing their conceptual structure. Originally developed by George Kelly (1955) for personal construct psychology. The grid captures how individuals perceive and differentiate aspects of their world — precisely what we want to model.

**Concept Mapping**: Experts create visual networks of interconnected concepts, externalizing their understanding of a domain. The resulting map reveals not just what they know but how they organize it. Concept maps show hierarchical relationships and cross-links, directly corresponding to a knowledge graph.

**Concept Sorting**: Domain concepts on cards are sorted into piles based on shared attributes, revealing the expert's conceptual organization. This is an efficient technique that our system could emulate through questions like "Would you group the Peloponnesian War more with Greek internal politics or with the broader Greco-Persian conflicts?"

**Twenty Questions Method**: Explicitly listed in knowledge elicitation taxonomies — the expert answers questions posed by the knowledge engineer to determine how they gather and organize information. Three techniques were directly compared in a case study: structured interview, twenty questions, and card sort.

### 5.2 Applicability to Self-Knowledge Elicitation

Classical knowledge elicitation was designed for expert-to-engineer transfer, but the techniques adapt naturally to self-report knowledge mapping:
- The "expert" and the person being mapped are the same person
- The "knowledge engineer" is the AI system
- The goal shifts from transferring knowledge to *modeling* it
- The repertory grid's focus on personal constructs is especially relevant — how does *this person* organize their understanding?

### 5.3 Key References
- Cooke, N.J. (1994). "Varieties of Knowledge Elicitation Techniques." *Int J of Human-Computer Studies*.
- Smart, P. (2015). "Knowledge Elicitation: Methods, Tools and Techniques."
- Shaw, M.L.G. & Gaines, B.R. (1987). "Comparing knowledge elicitation techniques: a case study." *AI Review*.

---

## 6. Personal Knowledge Modeling and Knowledge Tracing

### 6.1 Knowledge Tracing: From Education to Personal Models

Knowledge tracing algorithms infer an individual's "knowledge state" during learning — the exact set of concepts mastered. The main approaches:

**Bayesian Knowledge Tracing (BKT)**: Models mastery as a hidden Markov process with binary states (mastered/not mastered). Four parameters: initial knowledge probability, learning rate, slip rate (error when mastered), guess rate (correct when not mastered). Simple, interpretable, but limited to single-skill tracking.

**Deep Knowledge Tracing (DKT)**: Uses LSTM neural networks to model knowledge evolution, achieving AUC of 0.85 vs. BKT's 0.68. Does not require explicitly encoded domain concepts, allowing multivariate inputs and learning long-term dependencies. More powerful but less interpretable.

**SPARFA** (Sparse Factor Analysis for Learning and Content Analytics): Automatically discovers latent "concepts" underlying a domain from student response data. Estimates which concepts each question involves, the difficulty of each question, and each student's knowledge profile. SPARFA's ability to discover structure from data is particularly relevant — we could use it to discover the natural structure of a domain from user responses.

**DKVMN** (Dynamic Key-Value Memory Networks): Uses external memory to store and update knowledge states, allowing fine-grained tracking of multiple concepts simultaneously.

### 6.2 Personal Knowledge Graphs for Learners

Recent research (2024) has explored Personal Knowledge Graphs (PKGs) for learner modeling:

- Students actively construct PKGs by marking concepts as "did not understand (DNU)" while interacting with learning platforms (LAK 2024 paper)
- Graph neural networks create transparent learner knowledge state models from PKGs (UMAP 2024)
- The approach addresses the key limitation of opaque learner models by giving students control over their knowledge representation

The UMAP 2024 paper "LLMs for Knowledge Modeling" proposes constructing user knowledge models from academic records using NLP — extracting concepts from lesson records via named entity recognition and ChatGPT prompt engineering. This is the closest existing work to building a comprehensive model of what someone knows, though it works from documents rather than interactive assessment.

### 6.3 Duolingo's Approach

Duolingo provides a practical reference for adaptive knowledge modeling at scale:
- Computer-adaptive placement test determines CEFR level (A1-C2) through questions that adjust difficulty based on performance
- ML/NLP models automatically align items to proficiency levels, matching expert CEFR judgments
- The placement test efficiently maps a learner's position along a well-defined progression scale

The limitation for our purposes: Duolingo models knowledge along a single dimension (language proficiency level). Historical knowledge has much more complex topology — you might know advanced details about Athenian democracy but nothing about the Hellenistic period.

### 6.4 Familiarity Scales in Psychology

Self-reported familiarity scales are well-established in psychology research:
- **Five-stage familiarity scale**: Never Heard of It → Heard of It → Know a Little → Know a Fair Amount → Know It Well
- The Faculty Self-Reported Assessment Survey (FRAS) validates this approach, showing strong consistency and reliability for differentiating knowledge levels through self-report
- However, the **Dunning-Kruger effect** presents a challenge: people with low ability tend to overestimate their knowledge. Research suggests this is partly due to metacognitive deficits (not knowing what you don't know) and partly rational Bayesian updating from overly optimistic priors. For domains like history, where there is no "performance" to calibrate against, self-report accuracy depends heavily on how specific the questions are.

**Mitigation strategy**: Ask about increasingly specific facts rather than general familiarity. "Do you know about ancient Greece?" is susceptible to overconfidence. "Can you describe the Long Walls connecting Athens to Piraeus?" is much harder to falsely claim familiarity with.

### 6.5 Key References
- Corbett, A.T. & Anderson, J.R. (1995). "Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge." *User Modeling and User-Adapted Interaction*.
- Piech, C. et al. (2015). "Deep Knowledge Tracing." *NeurIPS*.
- Lan, A.S. et al. (2014). "Sparse Factor Analysis for Learning and Content Analytics." *JMLR*.
- "Learner Modeling and Recommendation using Personal Knowledge Graphs" (LAK 2024)
- "LLMs for Knowledge Modeling" (UMAP 2024): https://dl.acm.org/doi/10.1145/3631700.3665231

---

## 7. Information-Theoretic Question Selection

### 7.1 The "20 Questions" Information Theory Connection

The game of 20 Questions is the canonical example in information theory. Shannon showed that optimal play corresponds to a **Huffman code**: each question should ideally split the remaining possibilities in half, yielding one bit of information per question.

For a domain with N possible knowledge states, optimal binary search requires approximately log₂(N) questions. With 57,147 possible states (ALEKS's math example), that's ~16 questions. ALEKS achieves identification in ~24 questions, which is near-optimal given noisy responses.

### 7.2 Beyond Simple Binary Search

Pure half-splitting is optimal only when all states are equally probable. In practice:

- **Prior knowledge matters**: If we have a prior distribution over knowledge states (e.g., "most people who know about the Persian Wars also know about Thermopylae"), the optimal question splits the probability mass, not the state count
- **Hierarchical structure**: Domain knowledge has tree/DAG structure (topics → subtopics → specific facts). Optimal questioning should exploit this structure — ask about a topic before drilling into subtopics
- **Noisy responses**: Self-report is noisy (people may over- or under-estimate familiarity). The optimal strategy must be robust to error, which favors Bayesian approaches over deterministic binary search
- **"Guess Who?" analysis**: Research on optimal strategy in Guess Who? (Arxiv 2022) shows that beyond binary search, there are strategic considerations about when to ask specific vs. general questions

### 7.3 Active Learning: The ML Framework

Machine learning's **active learning** framework directly addresses our question selection problem:

**Uncertainty Sampling**: Select the item about which the model is most uncertain. Simple, effective, and the most natural analog to our problem — ask about the concept where we're least sure whether the user knows it.

**Expected Model Change**: Select the item that would cause the greatest change to the model if we knew the answer. This is more computationally expensive but can be more efficient in structured domains.

**Query by Committee**: Maintain multiple hypotheses about the user's knowledge state, and ask the question on which the hypotheses disagree most.

**Pool-Based vs. Query Synthesis**: Pool-based active learning selects from a fixed set of possible queries. **Query synthesis** generates new queries not in the original pool. Our LLM-based system would use query synthesis — the LLM generates questions on the fly, not drawn from a fixed bank.

### 7.4 Bayesian Optimal Experiment Design

The most theoretically grounded framework is Bayesian optimal experiment design:
- Maintain a posterior distribution P(knowledge_state | responses_so_far)
- For each candidate question q, compute the expected posterior after observing each possible response
- Select the question that maximizes the expected reduction in entropy (equivalently, maximizes the expected KL divergence between prior and posterior)
- This naturally handles: hierarchical structure (through the prior), noisy responses (through the likelihood model), and non-uniform state probabilities

### 7.5 Application to Our System

The information-theoretic framework suggests:
1. **Start with a prior**: Use the domain's prerequisite structure to define initial state probabilities. For ancient history, someone who knows nothing about Greece probably doesn't know about Thermopylae.
2. **Ask the maximally discriminating question**: The question that most evenly splits the posterior probability mass over knowledge states.
3. **Update the posterior**: After each self-report response, update beliefs about all related concepts using the prerequisite graph (if they know about Thermopylae, they probably know about the Persian Wars generally).
4. **Terminate when entropy is low enough**: Stop when the model is confident about the user's knowledge state.

### 7.6 Key References
- Settles, B. (2012). "Active Learning." *Synthesis Lectures on AI and ML*. (The definitive survey)
- Houlsby, N. et al. (2011). "Bayesian Active Learning for Classification and Preference Learning." https://arxiv.org/abs/2012.10695
- Nakamura, R. et al. (2015). "Optimal Strategy in Guess Who? Beyond Binary Search." https://arxiv.org/abs/1509.03327

---

## 8. LLM-Generated Domain Structure

### 8.1 Automated Knowledge Graph Construction

A critical component of our system is generating the prerequisite structure of a domain. Recent work (2024-2025) shows LLMs can do this effectively:

- LLMs can construct domain ontologies from natural language descriptions, including hierarchical topic structures and prerequisite relationships
- The OntoKGen pipeline (December 2024) uses an adaptive iterative Chain of Thought to extract ontologies interactively
- "How Well Do LLMs Predict Prerequisite Skills?" (2025) demonstrates that modern LLMs can infer prerequisite relationships from skill names and descriptions alone in zero-shot settings, with performance aligning with expert-defined competence hierarchies
- The ACE system constructs educational knowledge graphs with prerequisite relations using AI assistance

### 8.2 Practical Implication

This means we can use an LLM to:
1. Generate a hierarchical topic structure for any domain (e.g., "Ancient Greek History")
2. Identify prerequisite relationships between topics
3. Estimate which topics are commonly known vs. obscure
4. Dynamically refine the structure based on user responses

This is a significant enabler — we don't need hand-crafted domain models. The LLM *is* the domain expert.

---

## 9. Theoretical Frameworks for Knowledge Depth

### 9.1 Bloom's Taxonomy

Bloom's taxonomy provides a natural depth scale for knowledge assessment:
1. **Remember**: Can recall facts ("The Battle of Marathon was in 490 BCE")
2. **Understand**: Can explain concepts ("Marathon showed hoplite superiority over Persian infantry")
3. **Apply**: Can use knowledge in new contexts ("The Marathon example illustrates how terrain advantages offset numerical inferiority")
4. **Analyze**: Can break down relationships ("Compare the strategic situations at Marathon, Thermopylae, and Salamis")
5. **Evaluate**: Can make judgments ("Was the Greek strategy at Thermopylae sound?")
6. **Create**: Can synthesize novel arguments ("How does the Persian Wars narrative challenge Huntington's clash of civilizations thesis?")

Our self-report questions should probe at different Bloom levels to gauge depth, not just breadth.

### 9.2 Zone of Proximal Development

Vygotsky's Zone of Proximal Development (ZPD) describes the gap between what a learner can do independently and what they can achieve with guidance. For our system, the ZPD maps to the **knowledge frontier** — the boundary between what the user knows and what they're ready to learn.

Identifying this frontier is precisely what our system does. The ZPD framework suggests that the most valuable output of knowledge mapping is not a static model but an **action plan**: "Here are the topics at your knowledge frontier, where a small amount of reading would connect to and extend what you already know."

### 9.3 Concept Inventories

Concept inventories (like the Force Concept Inventory in physics) offer a relevant design pattern:
- They test specific conceptual understanding, not computational ability
- Distractors are chosen based on common misconceptions
- They reveal not just "wrong" but "wrong in a particular way that reveals a specific misunderstanding"

For self-report knowledge mapping, we could design questions that probe for common patterns of partial knowledge — "most people who know about the Peloponnesian War know about the Athenian plague but not about the Sicilian Expedition."

---

## 10. Related Systems and Novel Combinations

### 10.1 Belief Graphs with Reasoning Zones (October 2025)

A recent theoretical paper (Nikooroo, 2025) introduces "Belief Graphs with Reasoning Zones" — a graph-theoretic framework where:
- Beliefs are nodes in a directed, signed, weighted graph
- Edges encode support and contradiction relationships
- **Credibility** (external, a priori trust) is distinguished from **confidence** (internal, structure-aware valuation)
- **Reasoning zones** are high-confidence, structurally balanced subgraphs where classical inference is safe

This framework could model personal knowledge: each concept is a node, edges encode prerequisite and association relationships, and the user's familiarity determines node confidence. "Reasoning zones" correspond to coherent areas of knowledge.

### 10.2 Curiosity-Driven Exploration

Research on computational curiosity (Pathak et al., 2017; Gottlieb et al., 2013) reveals a key insight: curiosity is maximized not at total novelty but at the boundary of known and unknown — the "learning progress" heuristic. Agents are most curious about topics where they're making progress in understanding, not about topics they know nothing about (too hard) or everything about (boring).

This directly maps to our knowledge frontier identification: the most interesting topics for a user are those at the **edge** of their knowledge graph, where they have enough context to be curious but enough gaps to learn.

### 10.3 What Hasn't Been Done

After thorough search, I found **no existing system** that combines all of these elements:
1. LLM-generated domain structure (topic hierarchies with prerequisites)
2. Adaptive self-report questioning (not testing)
3. Information-theoretic question selection
4. Personal knowledge graph construction
5. Interactive, conversational interface

Individual pieces exist — ALEKS does (2, 3) with hand-crafted structure; GENCAT does (2, 3) with LLM-generated questions; personal knowledge graphs exist for learning platforms; LLMs can generate domain ontologies. But the specific combination — using an LLM to both generate the domain structure and conduct an adaptive conversational interview to map self-reported knowledge — appears to be novel.

---

## 11. What Is Novel About This Idea

### 11.1 Genuinely Novel Elements

1. **Self-report knowledge mapping (not testing)**: All existing adaptive assessment systems test knowledge through problems. Self-report ("Do you know about X?") is faster, works for any domain, doesn't require constructing test items with correct answers, and maps to a different use case (personal knowledge modeling vs. grading).

2. **LLM as both domain expert and interviewer**: Existing systems separate the domain model (hand-crafted by experts) from the assessment algorithm (fixed procedure). Using an LLM for both allows the system to work on any domain without prior setup and to generate natural conversational questions.

3. **Knowledge mapping for personal benefit, not institutional assessment**: All existing systems (ALEKS, Duolingo, CAT-based tests) serve institutional purposes (grading, placement, credentialing). Our system serves the individual — "I want to understand what I know so I can decide what to read next."

4. **Integration with a content system**: The knowledge map feeds directly into content recommendation and reading prioritization — connecting assessment to action.

### 11.2 Elements That Have Precedent

1. **Adaptive question selection for efficient assessment** — well-established in CAT and KST
2. **LLM-generated questions** — active research area (GENCAT, educational item generation)
3. **Personal knowledge graphs** — emerging in education research (UMAP 2024, LAK 2024)
4. **Binary search on structured domains** — classical information theory
5. **Knowledge elicitation via structured questioning** — decades of knowledge engineering research

---

## 12. Recommended Implementation Approach

### 12.1 Architecture

The system would have three layers:

**Layer 1: Domain Structure Generation**
- Given a domain (e.g., "Ancient Greek History, 800-323 BCE"), use an LLM to generate:
  - A hierarchical topic tree (eras → events → details)
  - Prerequisite relationships (DAG structure)
  - Estimated difficulty/obscurity levels (prior probabilities of knowing each topic)
  - Natural groupings (political, military, cultural, philosophical tracks)
- Output: A knowledge space in the KST sense, with nodes annotated with metadata

**Layer 2: Adaptive Questioning Engine**
- Maintain a probability distribution over knowledge states (which combination of topics the user knows)
- Use the prerequisite graph to constrain valid states (KST approach)
- Select each question using a Bayesian information gain criterion:
  - For each candidate question, compute expected posterior entropy
  - Select the question that maximizes expected entropy reduction
  - Implement a multi-level Bloom's taxonomy probe: start with "Have you heard of X?" (Remember), then optionally "Could you explain the significance of X?" (Understand)
- Use the LLM to generate natural-sounding questions from topic nodes
- Handle noisy self-report with probabilistic updates (treat "Yes, I know about this" as P(knows) ≈ 0.85, not 1.0)

**Layer 3: Knowledge Model**
- Store the resulting knowledge map as a personal knowledge graph:
  - Nodes = topics/concepts
  - Node attributes = familiarity level (unknown / heard-of / know-well), depth (Bloom level), confidence, last-assessed timestamp
  - Edges = prerequisite, association, part-of relationships
- Identify the **knowledge frontier**: topics where the user has partial knowledge or strong prerequisites but gaps
- Connect to content recommendation: "Based on your knowledge of the Persian Wars but not the Ionian Revolt, here are articles about the Ionian Revolt that would connect to what you already know"

### 12.2 Question Selection Algorithm

```
PROCEDURE SelectNextQuestion(posterior, topic_graph, asked_so_far):
  candidates = topics NOT in asked_so_far

  FOR each candidate topic t:
    # Expected information gain
    p_knows = PosteriorProbability(user knows t)

    # If user says "yes, I know this":
    posterior_yes = UpdatePosterior(posterior, t=known)
    entropy_yes = Entropy(posterior_yes)

    # If user says "no, I don't know this":
    posterior_no = UpdatePosterior(posterior, t=unknown)
    entropy_no = Entropy(posterior_no)

    # Expected entropy after asking about t
    expected_entropy[t] = p_knows * entropy_yes + (1-p_knows) * entropy_no

    # Information gain = current entropy - expected entropy
    info_gain[t] = Entropy(posterior) - expected_entropy[t]

  RETURN argmax(info_gain)
```

The `UpdatePosterior` function propagates information through the prerequisite graph — if the user doesn't know about the Persian Wars, they almost certainly don't know about Thermopylae, so we can skip that question.

### 12.3 Handling Depth

Instead of pure binary (know/don't know), use a small set of response options:
1. "Never heard of it"
2. "I've heard the name"
3. "I know the basics"
4. "I could explain it to someone"
5. "I know this in depth"

Map these to a graded familiarity model. The question selection algorithm should probe depth only when breadth is established — first determine which topics the user has heard of, then probe depth on the topics they claim to know.

### 12.4 Dealing with Dunning-Kruger

Self-report accuracy improves dramatically with specific questions. Strategies to mitigate overconfidence:
- Ask about increasingly specific aspects rather than general topics
- Occasionally include "calibration probes" — topics that sound plausible but are fabricated (e.g., "the Treaty of Philocrates" is real; "the Treaty of Megacleon" is not). Users who claim familiarity with fabricated topics are probably overestimating.
- Frame questions to make "I don't know" easy and natural — avoid any sense of testing or judgment
- Use the Bloom's hierarchy: escalate from "Have you heard of X?" to "Could you briefly describe what X is about?" for topics they claim to know well

### 12.5 LLM Prompt Structure

The LLM serves multiple roles:

**Domain generation prompt**: "Generate a hierarchical knowledge map for {domain}. For each topic, provide: name, parent topic, prerequisite topics, estimated obscurity (1-5), and a brief description. Structure as a DAG where edges represent 'should know before' relationships."

**Question generation prompt**: "Given that the user {knows/doesn't know} about {known_topics}, generate a natural conversational question probing their familiarity with {target_topic}. The question should be specific enough to distinguish genuine familiarity from vague awareness. Frame it as curiosity, not a test."

**Inference prompt**: "Given the user's response '{response}' to the question about {topic}, estimate their familiarity level (1-5) and extract any specific knowledge claims they made."

### 12.6 Practical Estimates

Based on ALEKS's empirical results and information-theoretic bounds:
- A domain with ~100 major topics could be mapped in **20-30 questions** (fewer if the prerequisite graph is dense)
- Each question takes ~5-10 seconds to answer → a complete domain mapping in **2-5 minutes**
- The system should reach 80% confidence about the knowledge state after ~15 questions, with diminishing returns thereafter
- A "quick scan" mode (10 questions, broad strokes) and "deep map" mode (30+ questions, detailed mapping) could serve different use cases

---

## 13. Open Questions and Risks

1. **Self-report validity**: How accurate is self-reported familiarity? The Dunning-Kruger literature suggests significant calibration issues, especially for low-knowledge individuals. Empirical testing needed.

2. **Domain structure quality**: How good are LLM-generated prerequisite graphs? The 2025 prerequisite prediction paper is encouraging, but domain-specific evaluation is needed.

3. **Engagement**: Will users tolerate 20-30 questions? The conversational framing is critical — it should feel like a discussion, not a survey.

4. **Granularity vs. efficiency trade-off**: Finer-grained mapping requires more questions. What's the right resolution for practical use?

5. **Temporal decay**: Knowledge fades. How do we model knowledge decay in a self-reported system? FSRS-style scheduling of reassessment?

6. **Cross-domain connections**: Real knowledge is networked across domains. How do we handle the user who knows about Thermopylae through a movie but not through historical study?

7. **Novel domain bootstrapping**: For domains the LLM knows less about, the generated structure may be less reliable. Need fallback strategies.

---

## 14. Conclusion

The "20 Questions for Knowledge" idea sits at a genuine intersection of several well-developed fields — Knowledge Space Theory, Computerized Adaptive Testing, active learning, knowledge elicitation, and LLM-based education tools. Each field contributes essential building blocks:

- **KST** provides the mathematical framework for knowledge states, prerequisites, and adaptive assessment
- **CAT/IRT** provides information-theoretic item selection algorithms
- **Active learning** provides the pool-based vs. synthesis-based question generation paradigm
- **Knowledge elicitation** validates the structured interview approach
- **LLM research** provides domain structure generation, natural question phrasing, and response interpretation

The novel contribution is the specific combination: **LLM-driven adaptive self-report knowledge mapping for personal benefit**. No existing system combines all these elements. The closest is ALEKS (adaptive assessment with knowledge spaces) and GENCAT (LLM + CAT), but both are testing systems for institutional purposes, not self-report systems for personal knowledge modeling.

The most promising implementation approach combines KST's prerequisite-based knowledge states with Bayesian information-theoretic question selection and LLM-generated domain structures and questions. The practical goal — mapping a domain in 2-5 minutes of conversational interaction — is achievable based on ALEKS's demonstrated efficiency (24 questions to identify 1 state among 57,147 possibilities).

For Petrarca specifically, this system would transform the reading experience: instead of manually curating reading lists, a 3-minute conversation about ancient history would let the system identify your knowledge frontier and surface articles that fill specific gaps or build on established understanding.

---

## Sources

### Knowledge Space Theory
- [Research Behind ALEKS - Knowledge Space Theory](https://www.aleks.com/about_aleks/knowledge_space_theory)
- [Knowledge Space - Wikipedia](https://en.wikipedia.org/wiki/Knowledge_space)
- [Knowledge Spaces and Learning Spaces (arXiv)](https://arxiv.org/abs/1511.06757)
- [The Assessment of Knowledge, in Theory and in Practice (Falmagne)](https://www.aleks.com/about_aleks/Science_Behind_ALEKS.pdf)
- [A practical perspective on knowledge space theory: ALEKS and its data](https://www.sciencedirect.com/science/article/abs/pii/S0022249621000134)
- [Knowledge Spaces (Springer)](https://link.springer.com/book/10.1007/978-3-642-58625-5)
- [KST, FCA, and Computerized Psychological Assessment](https://link.springer.com/article/10.3758/BRM.42.1.342)

### Computerized Adaptive Testing
- [Components of the item selection algorithm in CAT](https://pmc.ncbi.nlm.nih.gov/articles/PMC5968224/)
- [GENCAT: Generative Computerized Adaptive Testing](https://arxiv.org/abs/2602.20020)
- [Three-parameter IRT (3PL) model](https://assess.com/three-parameter-irt-3pl-model/)
- [Item Response Theory - Wikipedia](https://en.wikipedia.org/wiki/Item_response_theory)
- [Comparison of CAT Item Selection Criteria](https://pmc.ncbi.nlm.nih.gov/articles/PMC2791416/)

### LLMs for Assessment and Tutoring
- [The Future of Learning in the Age of Generative AI](https://arxiv.org/html/2410.09576v1)
- [Large Language Model-Powered Automated Assessment: A Systematic Review](https://www.mdpi.com/2076-3417/15/10/5683)
- [SocraticLM: Exploring Socratic Personalized Teaching with LLMs](https://openreview.net/forum?id=qkoZgJhxsA)
- [MedTutor-R1: Socratic Personalized Medical Teaching](https://arxiv.org/html/2512.05671v1)
- [Khanmigo: Khan Academy's AI-powered tutor](https://www.khanmigo.ai/)
- [LPITutor: LLM-based personalized intelligent tutoring](https://pmc.ncbi.nlm.nih.gov/articles/PMC12453719/)
- [AI-Powered Automatic Item Generation for Psychological Tests](https://link.springer.com/article/10.1007/s10869-025-10067-y)

### Knowledge Elicitation
- [Knowledge Elicitation Methods (WPI)](http://web.cs.wpi.edu/Research/aidg/KE-Rpt98.html)
- [Knowledge Elicitation: Methods, Tools and Techniques (Smart)](http://paulsmart.cognosys.co.uk/pubs/2015/Knowledge%20Elicitation.pdf)
- [Comparing knowledge elicitation techniques: a case study](https://link.springer.com/article/10.1007/BF00142925)
- [Repertory grid technique for knowledge elicitation](https://link.springer.com/article/10.1007/BF02169662)

### Personal Knowledge Modeling and Knowledge Tracing
- [Learner Modeling using Personal Knowledge Graphs (LAK 2024)](https://dl.acm.org/doi/10.1145/3636555.3636881)
- [Transparent Learner Knowledge State Modeling using PKGs and GNNs (UMAP 2024)](https://dl.acm.org/doi/10.1145/3631700.3665230)
- [LLMs for Knowledge Modeling (UMAP 2024)](https://dl.acm.org/doi/10.1145/3631700.3665231)
- [A Survey of Knowledge Tracing: Models, Variants, and Applications](https://arxiv.org/html/2105.15106v4)
- [Deep Knowledge Tracing (Piech et al.)](https://stanford.edu/~cpiech/bio/papers/deepKnowledgeTracing.pdf)
- [SPARFA: Sparse Factor Analysis for Learning and Content Analytics](https://jmlr.org/papers/v15/lan14a.html)
- [Bayesian Knowledge Tracing - Wikipedia](https://en.wikipedia.org/wiki/Bayesian_Knowledge_Tracing)
- [Machine Learning-Driven Language Assessment (Duolingo)](https://research.duolingo.com/papers/settles.tacl20.pdf)

### Information Theory and Active Learning
- [Active Learning Literature Survey (Settles)](https://burrsettles.com/pub/settles.activelearning.pdf)
- [An Information-Theoretic Framework for Unifying Active Learning Problems](https://arxiv.org/abs/2012.10695)
- [Optimal Strategy in "Guess Who?": Beyond Binary Search](https://arxiv.org/abs/1509.03327)
- [Twenty (Short) Questions (Combinatorica)](https://link.springer.com/article/10.1007/s00493-018-3803-4)
- [Bayesian Information Gain to Design Interaction](https://telecom-paris.hal.science/hal-03323514/document)

### Domain Structure and Prerequisites
- [How Well Do LLMs Predict Prerequisite Skills?](https://arxiv.org/html/2507.18479v1)
- [ACE: AI-Assisted Construction of Educational Knowledge Graphs with Prerequisite Relations](https://jedm.educationaldatamining.org/index.php/JEDM/article/view/737)
- [LLM-Assisted Ontology and Knowledge Graph Construction](https://arxiv.org/abs/2403.08345)
- [Leveraging LLM for Automated Ontology Extraction](https://arxiv.org/abs/2412.00608)

### Related Frameworks
- [Belief Graphs with Reasoning Zones (Nikooroo, 2025)](https://arxiv.org/abs/2510.10042)
- [Computational mechanisms of curiosity and goal-directed exploration](https://elifesciences.org/articles/41703)
- [Humans monitor learning progress in curiosity-driven exploration](https://www.nature.com/articles/s41467-021-26196-w)
- [Concept Inventory - Wikipedia](https://en.wikipedia.org/wiki/Concept_inventory)
- [Zone of Proximal Development](https://www.simplypsychology.org/zone-of-proximal-development.html)
- [Dunning-Kruger effect - Wikipedia](https://en.wikipedia.org/wiki/Dunning%E2%80%93Kruger_effect)
- [Bloom's Taxonomy - Wikipedia](https://en.wikipedia.org/wiki/Bloom's_taxonomy)
- [User Modeling in the Era of LLMs](https://arxiv.org/pdf/2312.11518)
- [PersonalLLM (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/a730abbcd6cf4a371ca9545db5922442-Paper-Conference.pdf)
