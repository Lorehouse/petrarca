# Knowledge Elicitation — Iteration Notes from First Real Session

**Date**: 2026-03-16
**Context**: First real 20Q session on Ancient Greece (37/67 nodes assessed). Rich feedback on format, calibration, and design.

---

## Key Insights from the Session

### 1. Learning While Being Tested
A well-designed assessment should leave the user knowing MORE than when they started. The card descriptions, even when not clicked, prime recall and can reactivate latent knowledge. This is a known effect in learning sciences (the "testing effect" — retrieval practice strengthens memory even when no feedback is given).

Maximum case: Alif's reading experience where every interaction is simultaneously a test and a learning moment. We don't want that intensity here (the user shouldn't spend most of their time in this interface), but we shouldn't dismiss the learning-while-testing opportunity.

### 2. Curriculum Design Research Needed
There's a rich tradition of curriculum design with specific learning outcomes. Sources to investigate:
- **Learning at Scale conferences** (L@S)
- **CMU's learning science research** (LearnLab, PSLC, Knowledge Components)
- **Backwards design** (Wiggins & McTighe — "Understanding by Design")
- **Pre-designed curricula**: Open-source textbooks, MOOCs, AP/IB syllabi
- These could serve as high-quality templates for curriculum node structure

### 3. Graduated Depth Probing ("Points" System)
An interesting alternative to the flat 5-level scale — graduated questions of increasing specificity:

```
Pericles:
  Level 1: Can you place him roughly? (Athens, 500-300 BC)
  Level 2: Do you know his role? (General, statesman, Golden Age)
  Level 3: Can you name specific achievements? (Parthenon, democratic reforms)
  Level 4: Can you discuss his political strategy and legacy?
  Level 5: Can you compare his approach to other democratic leaders?
```

**Problem**: Knowledge doesn't go linearly. You might have deeply studied one of Plato's works without knowing basic biographical facts. But the graduated approach still has value — even "Pericles was an important person in Athens somewhere between 500 and 300 BC" is better than nothing as a hook.

### 4. Latent Knowledge vs Active Knowledge
Key distinction from the session:
- **Active knowledge**: Can recall and explain right now
- **Latent knowledge**: Read about it, it's "in there somewhere," would recognize and re-learn much faster than learning from scratch
- Example: Alcibiades — "I probably wouldn't be able to say almost anything. But probably a lot of it is still latent and if I read about him again, it might be much easier"
- The 20Q scale doesn't capture this distinction well. "Heard of" could mean either "literally just heard the name" or "read a whole novel featuring this person but can't recall details"

### 5. Guided Voice Dump (Prompted Depth Probe)
Instead of a free-form voice dump, generate specific prompts based on the 20Q results:

"Based on your initial survey, I'd like to explore some areas more deeply. Can you tell me:
- What works of Plato have you read?
- What do you know about the Theory of Forms?
- What do you know about Neoplatonism?
- How would you connect Plato to Socrates and Aristotle?"

This is more structured than a raw dump but more natural than a quiz. It probes *depth* where the 20Q found *breadth*.

### 6. Multiple Domains to Test
The format should be tested across different domains to see if the calibration problems are consistent:
- Ancient Greece (done — baseline)
- Roman Republic (books already in system)
- Alexander the Great (rated "know deeply" — good for testing depth probing)
- Charlemagne / European Middle Ages (less reading, more gaps expected)
- Renaissance / Romanticism (different kind of knowledge — cultural movements vs political history)

---

## Design Iterations to Try

### Iteration A: Description-First + Learning Outcomes
- Show the description by default (not hidden)
- Add 3-5 specific learning outcomes per node as checkboxes
- User checks what they can do → this gives multi-dimensional assessment
- More work per question but more accurate signal

### Iteration B: Graduated Depth (Auto-Drill)
- Start with broad recognition ("Can you place this in time and space?")
- If yes, drill: "Can you name key people/events?"
- If yes, drill: "Can you explain the significance?"
- Stop when user says no → depth level determined automatically
- Faster per-question than checkboxes, but still captures depth

### Iteration C: Comparative Mode
- "Which do you know more about: Plato or the Sophists?"
- Research says relative judgments are more reliable than absolute
- Gives two data points per question
- Could sort all nodes by relative ranking

### Iteration D: Prompted Voice Dump
- After the breadth scan (20Q), pick 3-5 topics the user rated "know_basics" or higher
- Generate specific prompts for each
- User records voice responses
- LLM extracts specific knowledge claims and maps to curriculum
- Most rich signal, highest effort

### Iteration E: Pre-designed Curriculum Templates
- Research and find high-quality existing curricula (AP, IB, university syllabi, textbook TOCs)
- Use these as templates instead of LLM generation
- Potentially much better node descriptions and learning outcomes
- Limited to domains where good curricula exist

---

## What Should We Do Next?

**Research sprint**: Deep dive into learning sciences, curriculum design, automated tutoring (CMU, L@S, ITS conferences) for question format innovations. Also search for existing high-quality curricula.

**Quick iteration**: Rebuild the HTML card UI with Iteration B (graduated depth) for 1-2 topics and compare the signal quality vs the flat 5-level scale.

**New domain test**: Generate curriculum for Roman Republic or Charlemagne/Middle Ages and run the assessment to see if calibration problems persist across domains.
