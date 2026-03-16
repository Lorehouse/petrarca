# Learning Science for Knowledge Mapping: Practical Research Report

**Date**: 2026-03-16
**Purpose**: Actionable findings from learning science, curriculum design, and assessment research to improve our 20Q knowledge mapping format. Eight research areas synthesized into concrete design recommendations.

---

## 1. The Testing Effect: Assessment AS Learning

### Core Finding

Tests cause learning, not just measure it. Roediger & Karpicke's landmark 2006 study showed students who took practice tests remembered 50% more than students who studied repeatedly. Testing once produced better retention than studying four times. This effect has been replicated hundreds of times across ages, materials, and contexts.

### Key Mechanisms

**Retrieval practice strengthens memory**: The act of trying to recall information strengthens the memory trace, even when retrieval fails. This is called "test-potentiated learning" — unsuccessful retrieval attempts enhance the effectiveness of subsequent restudy (Arnold & McDermott, 2013).

**The forward effect of testing**: Taking a test on material A improves subsequent learning of material B. Testing doesn't just consolidate what was tested — it potentiates future learning (Pastotter & Bauml, 2014).

**Works for conceptual knowledge, not just facts**: Retrieval practice enhances higher-order thinking when assessments require analysis, evaluation, or synthesis. "Exams requiring higher order thinking skills encourage greater conceptual understanding" (Jensen et al., 2014). When students practice applying content at a high cognitive level, there is improved retention of those high-level processes, and even transfer to nontested items.

### What This Means for Our 20Q System

Our assessment should be explicitly designed to TEACH, not just measure. Every question in the 20Q session is a learning opportunity. Specific implications:

1. **Show descriptions after answering, not before.** The sequence should be: question → user answers → reveal description. This creates a retrieval attempt (even if the user says "don't know") followed by feedback. The card-flip UI idea from our iteration notes is exactly right — it mimics the test-then-feedback cycle that maximizes learning.

2. **"Test-potentiated learning" validates the breadth-first scan.** Even shallow engagement with a topic name ("Have you heard of the Ionian Revolt?") creates a retrieval cue that makes subsequent reading about it more effective. The 20Q session is priming the user's memory for future encounters.

3. **Include brief "micro-lessons" in the card reveals.** When the user says "Never heard of it," the revealed description should be a 2-3 sentence hook — not just a definition, but something memorable and connective. Research shows that even brief exposure after a failed retrieval attempt produces stronger encoding than the same exposure without the retrieval attempt.

4. **The "desirable difficulty" principle applies.** Conditions that slow apparent learning (struggle, uncertainty) tend to optimize long-term retention (Bjork & Bjork, 2011). Don't make questions too easy. A question the user has to think about before answering is more valuable than one they can answer instantly.

### Practical Question Design Principle

The optimal question makes the user *try to recall* before revealing the answer. Not "Here's what the Ionian Revolt is — did you know that?" but rather "What do you know about how the Persian Wars started?" followed by a reveal that either confirms or fills in their knowledge.

---

## 2. CMU Knowledge Components Framework

### The KLI Framework

Koedinger, Corbett, and Perfetti's Knowledge-Learning-Instruction (KLI) framework from CMU's Pittsburgh Science of Learning Center provides the most rigorous decomposition of "what someone knows." They define three types of knowledge components (KCs):

**Facts**: Direct associations that cannot be reasoned through. "Pi is the ratio of a circle's circumference to its diameter." In history: "The Battle of Marathon was in 490 BCE."

**Skills**: Adaptable mappings from varied conditions to varied responses, where the mapping is nonverbal. In history: being able to read a primary source and identify bias, or place an event in its chronological context without looking it up.

**Principles**: Like skills, they map varied conditions to varied responses, but the mapping has verbal rationale. In history: "Imperial overextension leads to decline" or "Democratic institutions emerge when economic conditions create a literate middle class."

### How This Applies to Our Curriculum Nodes

Each curriculum node should be decomposed into these three types. For "Pericles and the Athenian Golden Age":

- **Facts**: When he lived (~495-429 BCE), his role (strategos, dominant politician), key events (building program, Peloponnesian War beginning)
- **Skills**: Can place him in the sequence of Athenian leaders, can connect his policies to broader Greek politics, can read a Thucydides passage about him in context
- **Principles**: How democratic leadership works when one person dominates, the relationship between imperial power and cultural flourishing, the tension between democracy and empire

### The Q-Matrix Insight

CMU's tutoring systems use a "Q-matrix" that maps each assessment item to the specific knowledge components it tests. The quality of the entire diagnostic system depends on correct Q-matrix specification. For our system, this means: **every question must explicitly target specific KCs, and we should know which KCs a yes/no answer provides evidence about.**

Currently our 20Q questions probe at the "node" level ("Do you know about Pericles?"). The KLI framework suggests we should probe at the KC level: "Can you name when Pericles lived?" (fact), "Could you explain why Pericles is considered so important?" (principle), "If you were reading Thucydides' account of the plague, would you know who was in charge of Athens?" (skill).

### Actionable: KC-Tagged Questions

For each curriculum node, generate 2-3 questions at different KC types. The graduated depth probing (Iteration B from our notes) maps naturally:

- Level 1 (Fact): "Can you place Pericles in time and place?"
- Level 2 (Fact+Skill): "Can you name his key achievements?"
- Level 3 (Principle): "Can you explain why his era is called the 'Golden Age'?"
- Level 4 (Principle+Skill): "Can you discuss the tension between Athenian democracy and imperial power under Pericles?"

This is more informative than our current 5-point familiarity scale because each level probes a qualitatively different type of knowledge.

---

## 3. Learning at Scale (L@S) and Recent Research

### L@S 2024: "Scaling Learning in the Age of AI"

The 2024 conference (Georgia Tech, July 2024) focused heavily on LLM integration with educational systems. Key relevant themes:

**LLM-based knowledge tracing**: Research at this frontier shows LLMs can identify knowledge components in dialogue turns and track mastery per KC across conversations. The approach significantly outperforms traditional knowledge tracing methods. However, short interactions (~4 turn pairs in Khanmigo dialogues) limit reliable KC mastery estimation. Our system needs longer sessions — the 15-25 question target is justified here.

**HTN-Based Tutors**: A new intelligent tutoring framework using Hierarchical Task Networks allows flexible encoding of different problem-solving strategies while providing hierarchical knowledge organization. This adaptive granularity of scaffolding is relevant to our graduated depth approach.

**Cold-start problem**: Active research area — how to assess a learner with no prior interaction data. Recent approaches use LLMs to leverage semantic features of questions/concepts, enabling the system to handle previously unseen topics. Our system faces this exact problem: every new domain is a cold start. The finding that LLM-based approaches can solve cold-start problems in as few as 5 dialogue turns (INTERACT, ACL 2025) is directly encouraging.

### GENCAT: The Closest System to Ours (February 2026)

GENCAT (Generative Computerized Adaptive Testing) combines LLMs with CAT:
- Develops a Generative Item Response Theory (GIRT) model
- Predicts/generates student open-ended responses, not just correctness
- Uses supervised fine-tuning + Direct Preference Optimization (DPO)
- Three question selection algorithms based on uncertainty, linguistic diversity, and information of sampled responses

GENCAT is the closest existing work to our system, but still focuses on **testing** (assessing correctness) rather than **self-reported knowledge mapping**. Our self-report approach remains genuinely novel.

### Actionable Takeaway

The field is converging on LLM-driven adaptive assessment. Our approach (LLM generates questions, selects based on information gain, interprets free-text responses) is well-aligned with the research frontier. The key differentiator is that we're mapping self-reported knowledge for personal benefit, not testing for institutional assessment.

---

## 4. Curriculum Design: Backward Design and Learning Outcomes

### Understanding by Design (UbD)

Wiggins and McTighe's backward design framework has three phases:

1. **Identify desired results**: What should students understand? (Big ideas and essential questions)
2. **Determine acceptable evidence**: How will we know they understand? (Assessment design)
3. **Plan learning experiences**: How will they learn? (Instruction)

The key innovation: start with the **assessment**, not the content. This inverts normal practice (cover content, then test) and is directly relevant to our system — we're designing the assessment first, then using it to guide reading.

### Big Ideas and Essential Questions

UbD distinguishes between:
- **Worth being familiar with**: Background knowledge, terminology
- **Important to know and do**: Core facts, concepts, skills
- **Enduring understanding**: Transferable big ideas that connect concepts

For our curriculum nodes, this suggests a three-tier structure:
- **Tier 1 (Enduring)**: "How did democratic institutions emerge and evolve in ancient Athens?" — this is the kind of question that makes knowledge generative
- **Tier 2 (Important)**: Specific events, figures, dates, institutions
- **Tier 3 (Familiar)**: Contextual details, minor figures, historiographic debates

### Writing Learning Outcomes with Bloom's Verbs

The "student should be able to..." format, using Bloom's revised taxonomy verbs, gives us a precise vocabulary for assessment:

| Level | Verb | History Example |
|-------|------|-----------------|
| Remember | identify, list, name | Name the major city-states involved in the Peloponnesian War |
| Understand | explain, compare, summarize | Explain why the Peloponnesian War weakened Greece |
| Apply | demonstrate, illustrate, use | Use the Peloponnesian War to illustrate how interstate rivalry undermines collective defense |
| Analyze | differentiate, organize, relate | Analyze Thucydides' account for bias based on his Athenian background |
| Evaluate | assess, argue, justify | Evaluate whether Athens' Sicilian Expedition was strategically justified |
| Create | design, formulate, construct | Construct an argument about parallels between Athens' imperial overreach and modern examples |

### Actionable: Rewrite Node Descriptions as Learning Outcomes

Instead of our current node descriptions (encyclopedic summaries), rewrite them as learning outcomes. For "The Peloponnesian War":

**Current**: "The devastating conflict between Athens and Sparta (431-404 BCE) that reshaped the Greek world..."

**Proposed**:
- Can identify the main participants and timeline (431-404 BCE)
- Can explain the underlying causes (Athenian imperialism, Spartan fear)
- Can describe key turning points (plague of Athens, Sicilian Expedition, Lysander's victory)
- Can analyze Thucydides as both participant and historian
- Can evaluate the war's impact on Greek political structures

This format directly supports graduated depth probing — each outcome IS a depth level.

---

## 5. Graduated Depth Assessment

### How Adaptive Systems Handle Multi-Dimensional Depth

**Branching adaptive assessment** is well-established: the system starts with a general question, and based on the response, branches to more specific or more general questions. If you answer correctly, the algorithm raises its ability estimate and gives you a harder question. If you miss it, the estimate drops and you get an easier one. Each answer informs the next step, creating a customized assessment path.

This is exactly our "Iteration B" design — but the research provides additional guidance:

### The ZPD and Dynamic Assessment

Vygotsky's Zone of Proximal Development provides the theoretical frame. Dynamic assessment uses a **test-teach-retest** approach: probe what students can do with graduated hints and support to reveal their ZPD boundaries.

Applied to our system:
- **Level 1 probe**: "Have you heard of the Ionian Revolt?"
- If yes, **Level 2 probe**: "Can you explain what triggered it?"
- If yes, **Level 3 probe**: "How does it connect to the larger pattern of Greek-Persian conflict?"
- If no at any level, that's the boundary — the ZPD edge.

Research on scaffolding says effective support is **contingent** (offered when needed), **graduated** (ranging from minimal hints to direct help), and **reversible** (withdrawn as competence consolidates).

### Practical Formative Assessment Thresholds

Research on ZPD-informed assessment provides concrete thresholds:
- Less than 35% correct → content is ABOVE the ZPD (too hard, skip this branch)
- 36-69% correct → content is IN the ZPD (this is the frontier — focus here)
- Greater than 70% correct → content is BELOW the ZPD (already known, move on)

For our self-report system, this maps to:
- User says "never heard of it" for most sub-topics → above their ZPD, don't drill deeper
- User knows some sub-topics but not others → their frontier, interesting zone
- User knows most sub-topics → below their ZPD, skip or probe for depth/misconceptions

### Multidimensional IRT (MIRT)

Standard CAT estimates a single dimension ("how much do you know?"). MIRT extends to multiple correlated dimensions — you might know a lot about Greek political history but little about military campaigns. The research says MIRT is computationally expensive but can be approximated by partitioning the domain into sub-dimensions and assessing each in parallel. This is exactly what our hierarchical approach does — we assess different branches of the curriculum independently, which is an efficient approximation to full MIRT.

### Actionable: Implement Auto-Drill with Stop Conditions

```
For each curriculum node:
  Ask Level 1 (recognition/placement)
  If "no" → mark as UNKNOWN, stop, propagate to children
  If "yes" → ask Level 2 (key people/events)
    If "no" → mark as HEARD_OF, stop
    If "yes" → ask Level 3 (significance/connections)
      If "no" → mark as KNOWS_BASICS
      If "yes" → mark as KNOWS_WELL

For each curriculum BRANCH:
  If >70% children are UNKNOWN → skip remaining children
  If >70% children are KNOWS_WELL → mark branch as strong, move on
  If mixed → this is the frontier, explore further
```

This is more efficient than asking the same 5-level scale for every node, and produces a richer signal.

---

## 6. Self-Assessment in Humanities

### Historical Thinking Assessment

Peter Seixas' Benchmarks of Historical Thinking (University of British Columbia) defines six core concepts that ARE what it means to "know history":

1. **Historical significance**: Why does this event/person/development matter?
2. **Evidence**: How do we know what happened? What sources exist?
3. **Continuity and change**: What changed, what persisted, what is the pattern?
4. **Cause and consequence**: Why did things happen this way?
5. **Historical perspectives**: How did people at the time see things differently?
6. **Ethical dimension**: How do we make moral judgments about the past?

These are "second-order concepts" — they are not content knowledge but the SKILLS of historical thinking. A person can know many facts about ancient Greece but lack the ability to evaluate sources or think about historical perspective.

### Implications for Our System

Our curriculum nodes currently model CONTENT knowledge (facts, events, people). Seixas' framework suggests we should ALSO assess historical thinking skills. The practical question: can the user not just recall what happened, but reason about it historically?

This maps to the KLI framework's distinction between facts, skills, and principles. Our graduated depth probing naturally gets at this:
- Level 1-2: Facts (recall, recognition)
- Level 3: Skills (explanation, connection)
- Level 4: Principles (evaluation, significance, perspective)

### The Dunning-Kruger Problem and Calibration

Research on self-assessment in humanities is sobering. A meta-analysis of 20 studies found physicians were unable to reliably self-assess their knowledge in 13/20 studies. Self-assessment correlates more strongly with motivation and satisfaction than with actual cognitive learning.

However, self-assessment accuracy increases with:
- **Greater domain expertise** (experts have better metacognition)
- **More specific questions** ("Rate your knowledge of the Peloponnesian War" is better than "Rate your knowledge of ancient Greece")
- **Relative/comparative judgments** ("Which do you know more about: A or B?" is more reliable than "How well do you know A?")
- **Practice with feedback** (calibration improves with experience)

### Confidence-Based Marking (CBM)

A highly relevant technique from medical education: students answer questions AND rate their confidence. Scoring rewards calibrated confidence — being right with high confidence scores highest, being right with low confidence scores less, being wrong with high confidence scores worst. CBM was found to be MORE efficient than traditional tests because it needs fewer items to estimate knowledge level.

For our system, this suggests: don't just ask "Do you know about X?" — ask "How confident are you that you could explain X?" The confidence signal is independently informative.

### Fabricated Concept Probes

Our existing idea of including plausible-sounding but fabricated topics ("the Treaty of Megacleon") is validated by research. Users who claim familiarity with fabricated topics are demonstrably overestimating across the board. This technique is used in vocabulary research (the "foil words" method) and produces reliable calibration signals.

### Actionable Design Changes

1. **Use comparative questions for routing**: "Which do you know more about: Greek philosophy or Greek political history?" — gives two data points per question and is more reliable than absolute ratings
2. **Include 1-2 calibration probes per session**: Fabricated but plausible topics. If the user claims knowledge, flag all their self-reports as potentially inflated
3. **Frame for specificity**: Never ask "Do you know about ancient Greece?" — always ask about specific, assessable topics
4. **Add confidence to claimed knowledge**: For topics rated "know well," ask "Could you explain this to someone?" — the act of imagining the explanation improves calibration

---

## 7. High-Quality Open Curricula for History

### AP Frameworks (College Board)

The most structured, freely available history curricula:

**AP World History: Modern** — 9 units across 4 periods (1200-present):
- Period 1 (1200-1450): The Global Tapestry, Networks of Exchange
- Period 2 (1450-1750): Land-Based Empires, Transoceanic Interconnections
- Period 3 (1750-1900): Revolutions, Consequences of Industrialization
- Period 4 (1900-present): Global Conflict, Cold War and Decolonization, Globalization

**AP European History** — 9 units with six thematic threads (Interaction with the World, Development of Culture, State Building, Social Organization, National/European Identity, Technology/Exchange). Each unit has specific learning objectives like: "Explain how capitalism has developed as an economic system" or "Explain the causes and consequences of economic inequality."

**Key structural insight**: AP frameworks organize content at two levels simultaneously: chronological units AND thematic threads that run across all units. This dual organization (chronological + thematic) matches exactly the "Civilization game map" metaphor from our vision doc.

### IB History (International Baccalaureate)

The 2026 revised IB History syllabus is structured around:
- **Paired Case Studies**: Source-based analysis with inquiry questions
- **Global Themes**: Schools select one overarching theme and build case studies within it
- **Regional In-Depth Topics**: Focus on one of four world regions

Built around four key historical concepts that encourage "thinking like historians." More flexible than AP but less granular — better for our thematic approach than for detailed node generation.

### Machine-Readable Standards: CASE and Common Standards Project

**CASE (Competencies and Academic Standards Exchange)**: 1EdTech's open standard provides machine-readable JSON/CSV formats for academic standards, accessible via REST API. Wisconsin's Department of Public Instruction has published its Social Studies Framework in CASE format. This means structured, downloadable curriculum data exists for social studies standards.

**Common Standards Project**: Open-source project with standards for all 50 US states, available as JSON via API (commonstandardsproject.com). Includes the C3 Framework (College, Career, and Civic Life) for social studies. The JSON format includes hierarchical identifiers, descriptions, and grade-level mappings.

### Actionable: Use AP Frameworks as Curriculum Templates

For our first implementation:

1. **Download the AP World History and AP European History Course and Exam Description PDFs** from College Board
2. **Extract the unit structure, key concepts, and learning objectives** — these are already organized at the right granularity level for our curriculum nodes
3. **Use the thematic threads** as cross-cutting tags on nodes (a node about "The French Revolution" would be tagged with State Building, Social Organization, and National Identity)
4. **Supplement with IB's "inquiry questions"** — they make excellent prompts for depth probing
5. **For machine-readable data**, query the Common Standards Project API for state social studies standards as a supplementary source

This gives us professionally designed, validated curriculum structures without needing to rely solely on LLM generation. The AP structure specifically is: 9 units, ~4-8 key concepts per unit, ~3-5 learning objectives per concept = roughly 150-300 assessable nodes per domain. That is the right granularity.

---

## 8. Innovative Question Formats

### Beyond the 5-Point Likert Scale

Research identifies several formats that work better than a simple familiarity rating for self-assessment of conceptual knowledge:

**Very Short Answer Questions (VSAQs)**: Require 1-5 word constructed responses. Research shows VSAQs are more discriminating than multiple choice, reduce guessing to zero, and change student learning behavior — students study differently when they know they'll need to produce rather than recognize answers. For our system: instead of "Do you know about the Peloponnesian War?" ask "In 1-2 words, what was the Peloponnesian War?" — the effort of producing even a minimal answer is far more diagnostic than a self-report.

**Comparative/Ranking Tasks**: "Rank these three events chronologically: Persian Wars, Peloponnesian War, Alexander's conquests." This tests structural knowledge (temporal ordering) without requiring factual recall. Thurstone (1927) showed people can compare two items reliably even when they cannot rate them absolutely. Research consistently shows relative judgments are more accurate than absolute ratings for self-assessment.

**Concept Connection Tasks**: "How are these two things related: Socrates and Athenian democracy?" This probes for understanding of relationships, not just recognition of individual concepts. Concept mapping research shows that the connections people draw between concepts are the most diagnostic indicator of understanding depth.

**"Explain to me" Prompts**: Generative responses (free recall, explanations) produce stronger learning effects than recognition responses (yes/no, multiple choice). Even a brief attempt to explain strengthens memory. For our system, occasional open-ended prompts ("Tell me what you know about...") produce both better assessment data and stronger learning.

**Confidence-Weighted Responses**: Pair any answer with a confidence rating. Certainty-Based Marking research shows this needs fewer items to estimate knowledge level than traditional assessment. The confidence signal is independently informative about metacognitive calibration.

### Drag-and-Drop Timelines

Timeline interactions (dragging events to their correct position on a timeline) test temporal ordering knowledge — a fundamental historical skill. This format:
- Tests structural knowledge, not just factual recall
- Is engaging and interactive (appeals to visual learners)
- Provides rich diagnostic data (which events are out of order reveals specific gaps)
- Has natural difficulty scaling (fewer events = easier, more events = harder)

For our web UI, a simple timeline ordering task (5-7 events) could replace 3-4 individual recognition questions while providing richer data about temporal understanding.

### Comparative Judgment (Thurstone/ACJ)

Adaptive Comparative Judgment presents two items and asks "which is X?" (e.g., "which happened first?", "which was more significant?", "which do you know more about?"). This format:
- Is cognitively easy (comparing two things is natural)
- Produces reliable rankings
- Gives two data points per question
- Is robust to individual rating biases

For our system, this could work for routing: "Which period do you know more about: Classical Greece or Hellenistic Greece?" — efficiently directs the assessment toward the area of greater uncertainty.

### The "Card-Flip with Revision" Pattern

Our existing card-flip idea (question → answer → revise) is well-supported by research. It combines:
1. Retrieval attempt (testing effect)
2. Feedback (test-potentiated learning)
3. Self-calibration (confidence updating)
4. Micro-learning (exposure to new information)

This is the single most evidence-supported interaction pattern for our use case.

---

## Synthesis: Concrete Recommendations for Iterating on 20Q

### Priority 1: Restructure Questions Around Learning Outcomes

**Replace encyclopedic node descriptions with specific learning outcomes** using Bloom's verbs. Each node gets 3-5 outcomes at increasing depth. The graduated depth probe asks about these outcomes in sequence.

Before:
> "The Peloponnesian War (431-404 BCE) was a devastating conflict between Athens and Sparta..."

After:
> - Can identify the main participants and approximate dates (Remember)
> - Can explain the key causes — Athenian imperialism, Spartan alliance fear (Understand)
> - Can describe major turning points — plague, Sicily, Lysander (Understand)
> - Can analyze why Athens lost despite economic advantages (Analyze)
> - Can evaluate Thucydides as both source and participant (Evaluate)

### Priority 2: Implement Auto-Drill with Stop Conditions

Replace the flat 5-level scale with graduated probing:

1. Start with Level 1 (recognition/placement) for all nodes in a branch
2. For nodes rated "yes," auto-drill to Level 2 (key details)
3. Continue drilling until the user says "no" — that's their depth boundary
4. Skip remaining children when >70% of a branch is unknown
5. This is more efficient AND produces richer signal than the current format

### Priority 3: Use AP/IB Frameworks as Curriculum Templates

Stop relying solely on LLM generation for curriculum structure. Use AP World History and AP European History frameworks as high-quality templates:
- Extract unit structure, key concepts, learning objectives from official PDFs
- Each AP "key concept" maps to a curriculum node
- Each AP "learning objective" maps to an assessable outcome within that node
- Supplement with IB inquiry questions for depth probing

For machine-readable standards, query the Common Standards Project API.

### Priority 4: Add Comparative Questions for Routing

Before drilling into any branch, use 2-3 comparative questions to route efficiently:
- "Which period do you know more about: Classical Greece or Hellenistic Greece?"
- "Between political history and cultural/intellectual history, where is your knowledge stronger?"

Research shows these are more reliable than absolute ratings and give two data points per question.

### Priority 5: Include Calibration Probes

Add 2-3 fabricated-but-plausible topics per domain session. If the user claims familiarity, apply a global deflation factor to their self-reports. This is a validated technique from vocabulary research.

### Priority 6: Card-Flip with Micro-Learning

After every answer, show a brief (2-3 sentence) description that either confirms or expands the user's knowledge. This turns the assessment into a learning experience (testing effect + feedback). For topics the user doesn't know, make the reveal a "hook" — something surprising or connective that makes them want to learn more.

### Priority 7: Mix Question Formats

Don't use the same format for every question. Mix:
- Recognition questions (fast, breadth): "Have you heard of..."
- Comparative questions (routing, reliable): "Which do you know more about..."
- VSAQ-style (diagnostic, depth): "In a few words, what was..."
- Timeline ordering (structural, engaging): "Put these in order..."
- Confidence-weighted (calibration): "How confident are you that you could explain..."

Research shows varying question format improves both engagement and diagnostic accuracy.

### Priority 8: Explicitly Design for the Testing Effect

The entire 20Q session should be conceived as a learning experience, not just measurement. Design choices:
- Questions before reveals (creates retrieval attempt)
- Brief, memorable descriptions in reveals (feedback after retrieval)
- Surprising connections in descriptions (primes future learning)
- After the session, offer a "Here's what you might not have known" summary (consolidates new information)

---

## Key Numbers to Remember

| Finding | Number | Source |
|---------|--------|--------|
| Testing vs. restudying retention advantage | 50% better | Roediger & Karpicke 2006 |
| ALEKS convergence on knowledge state | ~24 questions among 57,147 states | Falmagne 2012 |
| CAT items needed for target precision | 10-25 items | van der Linden & Glas 2010 |
| Cold-start useful model in dialogue | 5 turns | INTERACT, ACL 2025 |
| Spacing benefit on retention | 10-30% improvement | meta-analysis, 254 studies |
| AP World History assessable nodes | ~150-300 | College Board CED |
| CBM efficiency vs. traditional testing | Fewer items needed | Gardner-Medwin et al. |
| Self-assessment accuracy with specific questions | Moderate correlation with actual knowledge | Knowledge survey research |
| ZPD formative assessment threshold | 36-69% correct = frontier zone | NWEA research |

---

## Sources

### Testing Effect and Retrieval Practice
- [Test-Enhanced Learning (Roediger & Karpicke 2006)](https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x)
- [The Power of Testing Memory](http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PPS.pdf)
- [Testing Effect on High-Level Cognitive Skills](https://www.lifescied.org/doi/10.1187/cbe.19-10-0193)
- [Test-Potentiated Learning: Direct and Indirect Effects](https://pmc.ncbi.nlm.nih.gov/articles/PMC3764602/)
- [Retrieval Practice Forward Effect](https://pmc.ncbi.nlm.nih.gov/articles/PMC3983480/)
- [The Testing Effect — Overview (ScienceDirect)](https://www.sciencedirect.com/topics/psychology/testing-effect)
- [Creating Desirable Difficulties to Enhance Learning (Bjork & Bjork)](https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/04/EBjork_RBjork_2011.pdf)

### CMU Knowledge Components and KLI Framework
- [KLI Framework (Koedinger, Corbett, Perfetti 2012)](https://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf)
- [KLI Framework Technical Report](https://pact.cs.cmu.edu/pubs/PSLC-Theory-Framework-Tech-Rep.pdf)
- [Cognitive Tutor: Applied Research in Mathematics Education](https://pact.cs.cmu.edu/koedinger/pubs/Ritter%20Anderson%20Koedinger%20Corbett%202007.pdf)
- [Pittsburgh Science of Learning Center](https://hcii.cmu.edu/pslc-pittsburgh-science-learning-center)
- [LearnLab](https://learnlab.org/)

### Learning at Scale and Recent Research
- [L@S 2024 Proceedings](https://dl.acm.org/doi/proceedings/10.1145/3657604)
- [Exploring Knowledge Tracing in Tutor-Student Dialogues (LAK 2025)](https://learninganalytics.upenn.edu/ryanbaker/Dialogue_KT_LAK_25-2.pdf)
- [The Future of Learning in the Age of Generative AI](https://arxiv.org/html/2410.09576v1)
- [LLM-Powered Automated Assessment: Systematic Review](https://www.mdpi.com/2076-3417/15/10/5683)
- [Evaluating LLM-Generated Q&A Tests](https://arxiv.org/html/2505.06591v1)

### Curriculum Design and Learning Outcomes
- [Understanding by Design Framework (ASCD)](https://files.ascd.org/staticfiles/ascd/pdf/siteASCD/publications/UbD_WhitePaper0312.pdf)
- [Backward Design and Learning Objectives (UVM)](https://www.uvm.edu/ctl/backward-design-and-learning-objectives)
- [Bloom's Taxonomy Action Verbs (Salisbury)](https://www.salisbury.edu/administration/academic-affairs/instructional-design-delivery/articles/blooms-taxonomy-action-verbs.aspx)
- [Using Bloom's Taxonomy to Write Learning Objectives (Arkansas)](https://tips.uark.edu/using-blooms-taxonomy/)
- [Backward Design Framework (UC Merced)](https://teach.ucmerced.edu/pedagogy-guides/backwards-design)

### Graduated Depth and Adaptive Assessment
- [Computerized Adaptive Testing: A Complete Guide](https://assess.com/computerized-adaptive-testing/)
- [Types of Computer Adaptive Testing (TAO)](https://www.taotesting.com/blog/how-to-use-types-of-computer-adaptive-testing/)
- [Power of Adaptive Testing: Branching](https://www.youtestme.com/power-of-adaptive-testing-branching-in-question/)
- [ZPD: The Power of Just Right (NWEA)](https://www.nwea.org/blog/2025/the-zone-of-proximal-development-zpd-the-power-of-just-right/)
- [Scaffolded Assessment and ZPD (Edutopia)](https://www.edutopia.org/article/supporting-middle-school-students-zone-proximal-development/)
- [Multidimensional CAT for Patient-Reported Outcomes](https://pmc.ncbi.nlm.nih.gov/articles/PMC5874279/)

### Self-Assessment in Humanities
- [Benchmarks of Historical Thinking (Seixas)](https://historicalthinking.ca/sites/default/files/files/docs/Framework_EN.pdf)
- [Historical Thinking Assessment](https://www.eu-jer.com/the-development-of-historical-thinking-assessment-to-examine-students-skills-in-analyzing-the-causality-of-historical-events)
- [Structural Differentiation of Knowledge for History Curriculum](https://www.tandfonline.com/doi/full/10.1080/00220272.2025.2455687)
- [Dunning-Kruger Effect (Wikipedia)](https://en.wikipedia.org/wiki/Dunning%E2%80%93Kruger_effect)
- [Confidence-Based Marking as Self-Assessment Tool](https://pmc.ncbi.nlm.nih.gov/articles/PMC3604960/)
- [Certainty-Based Marking for Reflective Learning](https://www.researchgate.net/publication/228648846_Certainty-Based_Marking_CBM_for_reflective_learning_and_proper_knowledge_assessment)

### Open Curricula and Machine-Readable Standards
- [AP World History Course (College Board)](https://apcentral.collegeboard.org/courses/ap-world-history)
- [AP European History Course and Exam Description](https://apcentral.collegeboard.org/media/pdf/ap-european-history-course-and-exam-description.pdf)
- [IB History in the Diploma Programme](https://www.ibo.org/programmes/diploma-programme/curriculum/individuals-and-societies/history/)
- [IB History 2026 New Curriculum Guide](https://myibsource.com/a/blog/the-new-ib-diploma-history-first-teaching-2026-whats-changing-why-it-matters-and-how-to-get-ready)
- [CASE Standard (1EdTech)](https://www.1edtech.org/standards/case)
- [CASE Network 2](https://www.1edtech.org/program/casenetwork2)
- [Common Standards Project API (GitHub)](https://github.com/commonstandardsproject/api)

### Innovative Question Formats
- [VSAQs: A Viable Alternative to Multiple Choice](https://pmc.ncbi.nlm.nih.gov/articles/PMC7203787/)
- [Battle of Question Formats: VSAQs vs MCQs](https://link.springer.com/article/10.1186/s12909-024-06538-0)
- [Comparative Judgment in Educational Assessment (Nature)](https://www.nature.com/research-intelligence/nri-topic-summaries-v9/comparative-judgement-in-educational-assessment)
- [Adaptive Comparative Judgment (Wikipedia)](https://en.wikipedia.org/wiki/Adaptive_comparative_judgement)
- [Free Recall Enhances Subsequent Learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC3766950/)
- [Concept Mapping for Assessment](https://pmc.ncbi.nlm.nih.gov/articles/PMC9755387/)
- [Pairwise Comparison in Psychology](https://en.wikipedia.org/wiki/Pairwise_comparison_(psychology))
