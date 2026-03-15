# Knowledge Elicitation via Adaptive Questioning: Research Report

**Date**: 2026-03-15
**Purpose**: Practical research for building a "20 Questions"-style system that rapidly maps what a user knows about broad domains (history, humanities, etc.) through conversational interaction.

---

## 1. The Information Theory of Good Questions

### Shannon's Foundational Insight

The 20 Questions game is the physical instantiation of Shannon's entropy. Given a distribution over N possible states, the average number of yes/no questions needed to identify the true state is bounded by H (entropy) and H+1. An optimal strategy is given by a Huffman code: each question reveals one bit of the codeword for the answer.

**The key number**: with 20 binary questions, you can distinguish among 2^20 = 1,048,576 possibilities. Each question that perfectly bisects the remaining hypothesis space eliminates half the candidates.

### What Makes a Question "Good"

A good question maximizes **information gain** — the reduction in entropy (uncertainty) after hearing the answer:

```
Information Gain = H(before) - H(after)
```

The optimal question splits the remaining possibility space as close to 50/50 as possible. In decision tree terms (ID3/C4.5 algorithms), each node selects the attribute with the highest information gain.

**Practical implication for knowledge elicitation**: A question like "Do you know about the Roman Republic?" is *bad* — it's too broad and the answer barely narrows the space. A question like "Can you explain the significance of the Gracchi brothers' land reforms?" is *better* — a "yes" implies knowledge of late Republican politics, social conflict, and institutional mechanisms; a "no" cleanly excludes that branch.

### Akinator's Bayesian Approach

Akinator (the "mind-reading genie") uses a fuzzy Bayesian system, not strict binary elimination:

1. **Knowledge base**: Each character has probability weights for many attributes (not just yes/no)
2. **Bayesian updates**: Each answer updates probabilities using Bayes' theorem — "yes" increases probability for matching characters, "no" decreases it, but never to zero (allows for user error)
3. **Question selection**: Picks the question that best splits the remaining high-probability characters
4. **Learning**: Every session refines the probability mappings — when users confirm "bald cartoon scientist" = Rick Sanchez, that link strengthens

**Key insight for us**: Akinator succeeds because it tolerates noise. Users give wrong answers, answers are ambiguous, knowledge is fuzzy. A strict binary tree would break; Bayesian updates degrade gracefully. Our system must handle the same ambiguity — people think they know things they don't, and they know things they can't articulate.

### Active Learning and BALD

In machine learning, the equivalent problem is **Bayesian Active Learning by Disagreement (BALD)**: given a model with uncertainty, select the data point (question) that maximizes expected information gain about model parameters. The greedy strategy (always pick the single best next question) is provably near-optimal under certain conditions.

**Actionable**: We don't need to plan an entire question tree in advance. A greedy strategy — always asking the single most informative question given current beliefs — is nearly as good as the globally optimal strategy.

---

## 2. How Adaptive Learning Systems Model Knowledge

### Knowledge Space Theory (ALEKS)

ALEKS (Assessment and Learning in Knowledge Spaces) is the most theoretically grounded approach, based on Doignon & Falmagne's Knowledge Space Theory (1985):

- **Domain**: A finite set Q of concepts/skills/topics
- **Knowledge state**: A subset of Q representing what a learner knows — NOT a single score, but a specific *set* of items
- **Knowledge space**: The collection K of all feasible knowledge states (not all 2^|Q| subsets are valid — prerequisite relationships constrain which combinations are possible)
- **Assessment**: Start with an item contained in ~50% of remaining feasible knowledge states. If answered correctly, eliminate all states that don't contain it. Repeat until one state remains.

**Critical numbers**: Despite potentially millions of knowledge states, ALEKS converges to a student's state in approximately **25-30 questions** over **60-90 minutes**. About 4-5 million students use it annually.

**What this means for us**: Knowledge Space Theory proves you can assess a complex, structured domain with ~25 adaptive questions. The key is having the right *structure* — knowing which knowledge states are feasible constrains the search space enormously.

### Duolingo's Half-Life Regression

Duolingo models each learnable item with a **half-life** — the time until the probability of recall drops to 50%. Their Half-Life Regression (HLR) model:

- p = 2^(-t/h) where p = recall probability, t = time since last seen, h = half-life
- Half-life is predicted by features: word difficulty, number of exposures, time since last exposure, user history
- **Result**: 9.5% increase in retention for practice, nearly half the prediction error of the Leitner system

**Relevance**: For our system, we don't need to model decay of *recall* (we're not testing if users can remember facts), but we could model decay of *claimed knowledge confidence* — people's sense of "how well do I know this?" degrades over time if not refreshed.

### Khan Academy's Mastery Model

Khan Academy uses a simpler but effective model:

- **Knowledge graph**: Skills connected by prerequisite relationships
- **Mastery levels**: Not Attempted → Familiar → Proficient → Mastered
- **Adaptive practice**: Difficulty adjusts based on performance — correct answers lead to harder items, incorrect to easier ones
- **Mastery challenges**: Periodically re-assess skills, accounting for time elapsed since last review

**Key pattern**: The prerequisite graph is crucial. If you know skill B, and A is a prerequisite of B, you almost certainly know A. This lets you infer knowledge without testing it directly.

### Knewton's Knowledge Graph

Knewton built a comprehensive knowledge graph mapping how concepts relate — prerequisites, co-requisites, and laterals. This graph drives personalized content recommendations and learning trajectories. The graph structure itself is the student model's backbone.

### Cognitive Diagnostic Models (CDMs)

CDMs are the psychometric formalization closest to what we want:

- **Attributes**: Binary latent variables (mastered/not mastered) for specific cognitive skills
- **Q-matrix**: Maps each test item to the attributes it requires — a binary matrix of items × attributes
- **Attribute profile**: A binary vector describing which attributes a student has mastered
- **Models**: DINA (conjunctive — need ALL required attributes), DINO (compensatory — need ANY required attribute), and generalizations

**The Q-matrix is key**: It encodes "this question tests these specific knowledge components." The quality of the entire diagnostic system depends on correct Q-matrix specification. For us, this means: we need to know what each question *probes*.

---

## 3. Hierarchical Knowledge Structures in History/Humanities

### How Historians Organize Knowledge

Historical knowledge resists the clean hierarchies of math/science. Two competing approaches from Basil Bernstein's framework:

**Hierarchical (chronological)**: Eras → periods → events → people/actions
- Ancient History → Classical Greece → Peloponnesian War → Alcibiades' defection to Sparta
- Typically 4-6 levels deep
- Problem: implies fixed start-to-finish progression

**Horizontal (thematic)**: Themes/topics as parallel strands
- "Trade and Commerce" across all periods
- "Religious Conflict" as a thread from antiquity to modernity
- Problem: hard to establish logical ordering, risk of duplication

**What historians actually do**: Use periodization as the primary skeleton, with thematic threads running through it. A period is defined by dominant themes + landmark events at boundaries. Periods can be decades or centuries depending on context.

### Natural Chunks of Historical Knowledge

From curriculum design research and Wikipedia's category structure, the natural hierarchy for history looks like:

1. **Civilization/Region** (Western, Chinese, Islamic, etc.)
2. **Era** (Ancient, Medieval, Early Modern, Modern) — ~4-6 major divisions
3. **Period** (e.g., "Late Roman Republic", "High Middle Ages") — ~20-40 per civilization
4. **Theme within period** (politics, culture, economy, military, religion) — ~3-6 per period
5. **Events/Concepts** (specific wars, reforms, movements, figures) — ~5-20 per theme
6. **Specific facts/claims** (dates, outcomes, causal relationships) — unbounded

**Estimated total for "Ancient History" as a domain**:
- ~5 major civilizations × ~4 eras × ~5 themes × ~10 key events = ~1,000 knowledge nodes at the "event" level
- With 20 questions that each bisect the space, you could theoretically assess ~2^20 = 1M nodes — far more than needed

### Key Concepts in Historical Understanding

Historical literacy involves not just facts but **second-order concepts**:
- **Change and continuity**: Understanding what changed and what persisted
- **Cause and effect**: Why events happened
- **Significance**: Why certain events matter
- **Evidence and interpretation**: How we know what we know
- **Perspective and empathy**: Understanding actors in their context

**Implication**: A good knowledge elicitation system should probe these second-order concepts, not just "do you know about X?" Questions like "What do you think caused the fall of the Roman Republic?" reveal far more about knowledge depth than "Have you heard of Julius Caesar?"

---

## 4. LLM-Based Tutoring and Assessment (2023-2025)

### Knowledge Tracing in Dialogue (LAK 2025)

The most directly relevant recent work: researchers annotated Khanmigo (Khan Academy's GPT-4 tutor) dialogues with correctness labels and Common Core standards as knowledge components (KCs). Their LLMKT approach:

- Uses GPT-4o to identify KCs in each dialogue turn
- Tracks mastery per KC across the conversation
- **Significantly outperforms** existing knowledge tracing methods for predicting response correctness

**Limitation**: Dialogues average only ~4 turn pairs — too short for reliable KC mastery estimation. Without sufficient history, the system struggles with KCs seen for the first time.

### INTERACT Framework (ACL 2025)

INTERACT (INTERactive learning for Adaptive Concept Transfer) demonstrates that **question-driven learning** works for LLMs themselves:

- A "student" LLM asks questions of a "teacher" LLM to learn about topics
- Student models trained with Direct Preference Optimization learn to ask *better* questions
- **25% improvement** over static learning
- Cold-start models match baselines in as few as **5 dialogue turns**

**Direct relevance**: The same architecture could work in reverse — an LLM "teacher" asking questions of a human "student" to build a knowledge model. The insight about 5 turns being sufficient for cold-start is encouraging.

### Multi-Agent Socratic Teaching (EMNLP 2025)

A multi-agent framework where different agents handle different pedagogical functions. Key finding: pedagogically informed "Tutor Prompts" emphasizing Socratic questioning significantly outperform basic prompts for GPT-4o.

### Khanmigo in Practice

- Uses GPT-4 with Socratic method — tutors ask questions at nearly every dialogue turn
- Students engaged in richer dialogue
- **However**: No measurable improvement in test outcomes in some studies, and many students found Socratic AI "less helpful" than direct answers
- **Lesson**: Pure Socratic questioning can be *annoying*. Our system should mix question types — some probing, some confirming, some informative.

---

## 5. Self-Reported Knowledge: When Can You Trust It?

### The Core Problem

The Dunning-Kruger effect (1999) describes the systematic tendency of low-ability individuals to overestimate their ability. But the picture is more nuanced:

**When self-assessment is UNRELIABLE**:
- Novices in a domain (lack metacognitive framework to judge what they don't know)
- Abstract/conceptual domains (hard to introspect)
- High-stakes situations (motivation to overestimate)
- General/broad questions ("How well do you know ancient history?" — too vague to calibrate)

**When self-assessment is MORE RELIABLE**:
- People with domain expertise (metacognitive skills improve with experience)
- Specific, concrete topics ("Can you explain how the Roman Senate worked?" — easier to calibrate)
- After repeated self-reflection (accuracy improves with practice)
- For *relative* judgments ("Do you know more about Roman than Greek history?" — comparative is better than absolute)

### Key Research Findings

- A meta-analysis of 20 studies found **physicians were unable to reliably self-assess** their knowledge compared to objective measures in 13/20 studies
- **Self-assessment correlates more strongly with motivation and satisfaction than with actual cognitive learning** — people report knowing more about topics they find interesting
- Self-assessment accuracy **increases with greater experience** in the domain and with better understanding of the domain's structure
- **Knowledge surveys** (where students rate confidence in ability to answer specific questions, without answering them) correlate moderately with actual test performance

### Practical Implications

1. **Don't rely solely on self-report**. Use it as a starting point, then probe with specific questions.
2. **Use concrete, specific prompts**. "Rate your knowledge of the Peloponnesian War" is better than "Rate your knowledge of ancient Greece."
3. **Comparative/relative questions work better** than absolute ones. "Which do you know more about: Roman Republic or Roman Empire?"
4. **Confidence calibration improves with feedback**. If you occasionally test claimed knowledge and show results, people learn to self-assess more accurately.
5. **Familiarity ≠ understanding**. The standard familiarity scale (Never heard of it → Know it well) captures recognition but not depth. Use Bloom's taxonomy-inspired levels: "Could you recognize it?" / "Could you explain it?" / "Could you teach it?"

### A Hybrid Approach

The most effective strategy combines:
- **Self-report for breadth**: "Which of these 20 topics have you studied?" (fast, covers ground)
- **Probing questions for depth**: "You said you know about the Punic Wars — what was the strategic significance of Hannibal crossing the Alps?" (verifies claims)
- **Calibration feedback**: "Based on your answers, your knowledge of Roman military history seems stronger than you reported" (improves future self-reports)

---

## 6. Rapid Domain Assessment Techniques

### Computerized Adaptive Testing (CAT)

CAT is the gold standard for rapid assessment, based on Item Response Theory (IRT):

- Start with a medium-difficulty item
- If correct, give a harder item; if wrong, give an easier one
- Continue until uncertainty in ability estimate drops below threshold
- **Typically half as many questions as a fixed test, with equal or better accuracy**
- Real-world: 3-minute reading assessments (ROAR-CAT) achieve high correlation with 15-minute proctored tests; 8-minute psychopathology screens match structured clinical interviews

**Key number**: CAT typically achieves target precision in **10-25 items** for unidimensional traits. For multidimensional assessment (multiple knowledge areas), you need more — but the adaptive routing keeps it efficient.

### Concept Inventories

Concept inventories are criterion-referenced tests designed to detect specific misconceptions, not just measure overall ability:

- **Force Concept Inventory (FCI)**: The original (1985/1992) — 30 questions about Newtonian mechanics, each wrong answer maps to a specific misconception
- Answers are designed from extensive research on common misunderstandings
- Pre-test scores reveal specific holes in understanding, not just "how much they know"
- Exist for physics, chemistry, biology, computer science, statistics, and more

**Relevance**: For humanities knowledge, we could build "concept inventories" not for misconceptions but for **knowledge gaps**. Instead of "which wrong answer did they pick?" it's "which related concept do they not recognize?"

### Knowledge Elicitation Techniques (from Expert Systems)

Classical knowledge elicitation methods from AI/expert systems research:

- **Structured interview**: Direct questioning in a systematic order
- **Card sorting**: Present domain concepts and have the expert group them (reveals their mental organization)
- **Laddering**: Build a hierarchy by asking "what's above/below/next to this?" — moves up, down, and across the knowledge structure
- **Protocol analysis**: Think-aloud while performing a task
- **Repertory grid**: Compare/contrast triads of concepts to elicit distinguishing dimensions

**Most relevant for us**: **Laddering** — start from a concept the user claims to know, then move up ("What broader topic does this fall under?"), down ("What are the key sub-topics?"), and across ("What other events from the same period do you know?"). This naturally maps the user's knowledge structure.

---

## 7. Prior Art and Related Tools

### Assessment-Focused Tools

- **ALEKS**: The closest existing system to what we want — full knowledge state assessment through adaptive questioning. But domain-limited (math, chemistry, accounting) and test-like, not conversational.
- **Duolingo placement test**: Rapidly assesses language level through adaptive questions. Converges in ~15-20 minutes.
- **Khanmigo**: GPT-4-based tutor that tracks knowledge components through dialogue. Limited by short interaction lengths.
- **Adaface conversational assessments**: Uses chatbot-style interaction for skill assessment in hiring. Adjusts difficulty in real-time.

### Knowledge Mapping Tools

- **TheBrain**: Personal knowledge graph tool since the 1990s. Users build graphs spanning decades. Dynamic visual interface re-centers on any node. Scales to 500K+ items. But it's manual — you build the graph yourself.
- **Obsidian/Roam/Logseq**: Note-taking tools with graph views showing connections between notes. The graph *emerges* from your notes, but doesn't represent "what you know" — just "what you wrote."
- **InfraNodus**: Network text analysis tool that visualizes knowledge as a graph. Can analyze your notes to find gaps (missing connections between clusters).
- **Knowing.app**: New entrant (2025-2026) focused specifically on graph-based personal knowledge management with AI integration.

### Research Prototypes

- **INTERACT** (2024): LLM student-teacher framework where question-driven learning achieves 25% improvement in 5 dialogue turns. Closest to our proposed approach but designed for LLM learning, not human knowledge mapping.
- **PersonalLLM** (ICLR 2025): Benchmark for personalizing LLM responses to individual users by accumulating interaction history and discovering patterns across users.
- **Steve** (2025): LLM-powered chatbot for career skill assessment through conversational interaction.

### What's Missing (Our Opportunity)

No existing tool combines:
1. **Adaptive questioning** (like ALEKS/CAT) to efficiently probe knowledge
2. **Conversational interface** (like Khanmigo) that feels natural, not test-like
3. **Knowledge visualization** (like TheBrain) to show the user what they know
4. **Domain flexibility** (unlike ALEKS, which is limited to STEM)
5. **Integration with reading** (connecting assessed knowledge to reading recommendations)

---

## 8. Synthesis: Designing Our Knowledge Elicitation System

### Architecture Recommendation

Based on all the research, here is a practical design:

#### Layer 1: Domain Structure (the "Q-matrix")

Pre-define a hierarchical knowledge structure for each domain. For "Ancient History":

```
Level 0: Ancient History (root)
Level 1: Mesopotamia, Egypt, Greece, Rome, Persia, India, China  (~7 nodes)
Level 2: Periods (e.g., Roman Republic, Roman Empire, etc.)      (~30-50 nodes)
Level 3: Themes (politics, culture, military, religion, economy)  (~150-250 nodes)
Level 4: Key concepts/events/people                               (~500-1500 nodes)
```

This can be generated by an LLM from curriculum outlines, Wikipedia category structures, or textbook tables of contents. It doesn't need to be perfect — it's a scaffold for questioning, not a definitive ontology.

#### Layer 2: Belief State (Bayesian knowledge model)

For each node in the hierarchy, maintain a probability distribution:

```
P(knows | evidence so far)
```

Initialize with priors based on hierarchical position:
- If user says they studied a topic, set prior higher for all descendants
- If user doesn't know a child concept, reduce probability for siblings
- Prerequisite/co-occurrence relationships propagate beliefs (if you know about the Punic Wars, you probably know who Hannibal was)

Update using Bayes' theorem after each question, with tolerance for noise (like Akinator).

#### Layer 3: Question Selection (greedy information gain)

At each step, select the question that maximizes expected information gain over the *entire* belief state (not just one node). In practice:

1. Find the region of highest uncertainty (nodes closest to P=0.5)
2. Select a question that probes that region
3. Prefer questions that also discriminate between neighboring nodes

**Question types** (mix these — don't be monotonous):
- **Recognition**: "Have you heard of the Gracchi brothers?" (fast, low-depth)
- **Explanation**: "Can you briefly explain what the Gracchi reforms were about?" (medium depth, hard to fake)
- **Connection**: "How does the Gracchi crisis relate to the later fall of the Republic?" (high depth, reveals understanding)
- **Comparison**: "Which do you know more about: Greek philosophy or Roman law?" (efficient routing, self-report calibrated by relative judgment)
- **Sorting**: "Put these in chronological order: Punic Wars, Persian Wars, Peloponnesian War" (tests structural knowledge)

#### Layer 4: LLM Conversation Engine

Use an LLM (Gemini Flash or Claude) to:
1. **Generate natural questions** from the structured question templates + current belief state
2. **Evaluate free-text answers** — when the user explains something, the LLM assesses correctness and depth
3. **Provide conversational scaffolding** — "Interesting! You know quite a bit about Roman politics. Let me ask about something different..."
4. **Handle tangents gracefully** — if the user volunteers extra information, update the model accordingly

#### Layer 5: Convergence and Output

**Target**: Map knowledge state to useful precision in **15-25 questions** (based on ALEKS convergence data and CAT research).

**Output**: Not a single score, but a knowledge *map*:
- Color-coded visualization of the domain hierarchy
- Green = strong knowledge, yellow = partial, gray = unknown, red = tested-and-failed
- Natural language summary: "You have strong knowledge of Roman political history, especially the late Republic. You're less familiar with Roman cultural/literary history and with the early Empire. You know about Greek philosophy but haven't studied Greek political structures in depth."

### Specific Design Decisions

**1. Start broad, go deep**
Begin with Level 1 (civilizations) — "Which of these areas have you studied?" Then drill into the most uncertain/interesting area. Don't try to cover everything at once.

**2. Mix self-report with probing**
Use self-report for the initial broad sweep (fast, covers ground), then verify the most important claims with specific questions. Research shows self-report is unreliable for novices but improves with domain knowledge — so trust it more when the user has already demonstrated expertise.

**3. Use relative judgments**
"Which do you know more about: A or B?" is more reliable than "How well do you know A?" on a 1-5 scale. It also gives you two data points for the cost of one question.

**4. Leverage prerequisite structure**
If someone knows about "Justinian's Corpus Juris Civilis," you can infer they know about the Byzantine Empire, late Roman law, and probably the fall of Rome. Propagate knowledge upward and to co-requisites.

**5. Make it feel like a conversation, not a test**
Research shows students find Socratic questioning annoying when it feels like an interrogation. Mix in informational nuggets: "The Gracchi brothers are actually one of the most fascinating turning points — their land reforms basically started the chain of events that ended the Republic. But before that period, do you know about..."

**6. 15-question target**
Based on:
- ALEKS: 25-30 questions for fine-grained assessment
- CAT: 10-25 items for target precision
- INTERACT: 5 turns for cold-start matching
- Our domain is broader but we need less precision (knowledge map, not placement test)

Aim for **15 questions to useful resolution, 25 for detailed mapping**.

**7. Use the output for reading recommendations**
The whole point: connect knowledge gaps to Petrarca's article library. "You know a lot about Roman politics but not much about Roman culture — here are 3 articles that would fill that gap." This closes the loop between knowledge elicitation and the app's core value proposition.

### How an LLM Conversation Might Flow

```
System: "I'd love to understand what you already know about ancient history,
         so I can surface the most interesting new content for you. This should
         take about 5 minutes."

System: "Let's start broad — which ancient civilizations have you studied or
         read about? Greece, Rome, Egypt, Mesopotamia, Persia, India, China?"

User:   "Mainly Greece and Rome. Some Egypt. Never really studied the others."

System: "Great. Between Greek and Roman history, which would you say you know
         more about?"

User:   "Probably Roman, especially the Republic and Empire transition."

System: "That's a rich period. Can you tell me briefly what you think were the
         main causes of the Republic's fall?"

User:   "The expansion of Rome made the old senatorial system unworkable.
         Military commanders like Marius, Sulla, Pompey, Caesar gained too
         much personal power. The Gracchi tried reforms but were killed..."

System: "That's a really solid understanding — you've got the structural causes
         and the key actors. You mentioned the Gracchi, which many people miss.
         Let me ask about a different angle: how much do you know about Roman
         cultural and intellectual life? Cicero, Virgil, that world?"

User:   "I've read some Cicero. Know the name Virgil but haven't read the
         Aeneid."

System: "Interesting — so you know the political Cicero but maybe less the
         literary culture. One more Roman question: the eastern Empire after
         476 — Byzantine history. Familiar?"

User:   "A little. I know about Justinian and Theodora, the Hagia Sophia.
         Not much beyond that."
```

After ~8 questions, the system has a rough map: strong on late Roman Republic, moderate on Roman Empire, light on Byzantine, moderate on Greek philosophy (inferred from mentioning studying Greece), unknown on Greek politics, minimal on Egypt/Mesopotamia/others. The remaining 7-17 questions can drill into the uncertain areas.

---

## Key Takeaways

1. **~25 adaptive questions suffice** to map a complex domain (proven by ALEKS at scale with 5M students/year)
2. **Greedy information gain** (always ask the most informative next question) is near-optimal — no need for elaborate planning
3. **Bayesian belief propagation** through a prerequisite/hierarchy graph lets you infer much from little
4. **Self-report works for breadth, probing for depth** — combine both
5. **Relative judgments > absolute ratings** for self-assessment accuracy
6. **LLMs can evaluate free-text answers** and update knowledge models from dialogue (LAK 2025)
7. **5 dialogue turns** is enough for a cold-start model to be useful (INTERACT, ACL 2025)
8. **The domain structure (Q-matrix) is the hardest part** — invest time in building good hierarchies
9. **Make it conversational, not test-like** — mix question types, add information, handle tangents
10. **Connect to action** — the output should drive reading recommendations, not just produce a map

---

## Sources

- [Shannon's 20 Questions and Entropy](https://arxiv.org/abs/1611.01655)
- [Optimal Sets of Questions for Twenty Questions](https://arxiv.org/html/2106.01737)
- [Building Akinator with Bayes Theorem](https://medium.com/analytics-vidhya/building-akinator-with-python-using-bayes-theorem-216253c98daa)
- [Akinator Algorithm Explained](https://medium.com/@cristian.nedelcu/top-ai-models-explain-how-akinator-works-d395f5a03807)
- [Knowledge Space Theory - ALEKS](https://www.aleks.com/about_aleks/knowledge_space_theory)
- [Knowledge Spaces and Learning Spaces](https://arxiv.org/abs/1511.06757)
- [Introduction to Knowledge Space Theory](https://medium.com/adapted/introduction-to-knowledge-space-theory-ce4fd91ae1ae)
- [The Science Behind ALEKS](https://www.aleks.com/about_aleks/Science_Behind_ALEKS.pdf)
- [Duolingo Half-Life Regression](https://research.duolingo.com/papers/settles.acl16.pdf)
- [How Duolingo's AI Learns What You Need](https://spectrum.ieee.org/duolingo)
- [Khan Academy Mastery Levels](https://support.khanacademy.org/hc/en-us/articles/5548760867853)
- [Knowledge Space Theory Practical Perspective](https://www.sciencedirect.com/science/article/abs/pii/S0022249621000134)
- [Cognitive Diagnostic Models](https://www.cambridgeassessment.org.uk/Images/701443-cognitive-diagnostic-models-and-how-they-can-be-useful.pdf)
- [Events and Periods as Concepts for Organizing Historical Knowledge](https://escholarship.org/uc/item/4111f1fw)
- [Knowledge Structures and School History](https://public-history-weekly.org/7-2019-13/knowledge-structures/)
- [Structural Differentiation of Knowledge for History Curriculum](https://www.tandfonline.com/doi/full/10.1080/00220272.2025.2455687)
- [Exploring Knowledge Tracing in Tutor-Student Dialogues (LAK 2025)](https://learninganalytics.upenn.edu/ryanbaker/Dialogue_KT_LAK_25-2.pdf)
- [INTERACT: Interactive Question-Driven Learning (ACL 2025)](https://arxiv.org/abs/2412.11388)
- [Multi-Agent Socratic Teaching (EMNLP 2025)](https://aclanthology.org/2025.findings-emnlp.888.pdf)
- [LLM Agents for Education](https://arxiv.org/html/2503.11733v1)
- [Training LLM-based Tutors](https://arxiv.org/html/2503.06424v1)
- [Can LLMs Match Tutoring System Adaptivity?](https://arxiv.org/html/2504.05570v1)
- [Dunning-Kruger Effect](https://en.wikipedia.org/wiki/Dunning%E2%80%93Kruger_effect)
- [Self-Assessment of Knowledge: Cognitive vs Affective](https://journals.aom.org/doi/10.5465/amle.9.2.zqr169)
- [Knowledge Surveys: Students' Ability to Self-Assess](https://files.eric.ed.gov/fulltext/EJ890708.pdf)
- [Familiarity Scale](https://www.monash.edu/business/marketing/marketing-dictionary/f/familiarity-scale)
- [Computerized Adaptive Testing Guide](https://assess.com/computerized-adaptive-testing/)
- [ROAR-CAT Rapid Reading Assessment](https://impact.stanford.edu/article/roar-cat-rapid-online-assessment-reading-ability-computerized-adaptive-testing)
- [Concept Inventory - Wikipedia](https://en.wikipedia.org/wiki/Concept_inventory)
- [Force Concept Inventory](https://www.physport.org/assessments/FCI)
- [Knowledge Elicitation Methods](https://web.cs.wpi.edu/~jburge/thesis/kematrix.html)
- [Bayesian Active Learning by Disagreement](https://arxiv.org/pdf/1112.5745)
- [Active Learning Literature Survey (Settles)](https://burrsettles.com/pub/settles.activelearning.pdf)
- [PersonalLLM (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/a730abbcd6cf4a371ca9545db5922442-Paper-Conference.pdf)
- [Wikipedia Category Ontology Framework](https://ceur-ws.org/Vol-2721/paper576.pdf)
- [TheBrain and Knowledge Graph Tools](https://www.atlasworkspace.ai/blog/knowledge-graph-tools)
- [Personal Knowledge Graphs](https://medium.com/data-science/personal-knowledge-graphs-9a23a0b099af)
- [Information Gain in Decision Trees](https://en.wikipedia.org/wiki/Information_gain_(decision_tree))
