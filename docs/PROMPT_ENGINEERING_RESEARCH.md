# Prompt Engineering Research Analysis

**Version:** 1.0.0
**Last Updated:** 2025-12-18
**Source:** Critical Analysis of Cognitive Architectures Report

This document summarizes peer-reviewed research findings that inform the agent-dashboard's design decisions. All recommendations are evidence-based with citations to original papers.

---

## Executive Summary

The agent-dashboard architecture aligns with validated prompt engineering research. Key design principles are supported by empirical evidence:

- **External verification** over self-correction (ICLR 2024)
- **Explicit constraints** over elaborate personas (multiple studies)
- **Few-shot examples** over role descriptions (Learn Prompting, ACL 2024)
- **Iteration limits** with escalation protocols (NeurIPS 2024)

---

## Validated Techniques (Implemented)

### 1. External Verification Architecture

**Research Support:** Huang et al., ICLR 2024 - "Large Language Models Cannot Self-Correct Reasoning Yet"

> "LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction."

**Implementation:** Agent-dashboard routes outputs through external verification agents (critic, research-judge, validator, panel-coordinator) rather than relying on self-correction loops.

**Evidence Strength:** Strong (peer-reviewed, replicated findings)

---

### 2. Constraint-Based Prompting

**Research Support:** Multiple AI lab documentation (Anthropic, OpenAI, Google)

Explicit constraints ("NEVER include", "MUST contain", "CANNOT exceed") produce more reliable outputs than capability descriptions ("You are an expert who...").

**Implementation:** All 22 agents use standardized ALWAYS/NEVER constraint format with 62+ explicit constraints.

**Evidence Strength:** Strong (consistent across vendors)

---

### 3. Few-Shot Examples Over Role Descriptions

**Research Support:**
- Learn Prompting study: 2-shot Chain-of-Thought outperformed 12+ role prompt variations
- ACL 2024: Persona variables explain <10% variance in objective NLP datasets

**Implementation:** 22+ few-shot examples across agent definitions. Role descriptions kept minimal; constraints and examples prioritized.

**Evidence Strength:** Moderate-Strong (empirical studies, consistent findings)

---

### 4. Iteration Limits with Escalation

**Research Support:**
- Reflexion paper (Shinn et al., NeurIPS 2023): "after only four trials... the agent does not show signs of improvement"
- Self-refinement research shows exponential decay after 2-3 iterations

**Implementation:**
| Agent | Limit | Escalation |
|-------|-------|------------|
| Orchestrator | 5 rounds | Human review |
| Implementer | 50 iterations | Failure analysis |
| Critic | 3 rounds | Approve with caveats |
| Web-search | 10 queries | Partial results |

**Evidence Strength:** Strong (multiple studies confirm diminishing returns)

---

### 5. Structured XML Formatting

**Research Support:** Research shows 15-20% improvement in response quality with structured formatting versus plain text.

**Implementation:** Agent definitions use consistent markdown structure with clear sections for constraints, examples, and output formats.

**Evidence Strength:** Moderate (vendor documentation, practical validation)

---

### 6. Test-Driven Iteration (Reflexion Pattern)

**Research Support:** Shinn et al., NeurIPS 2023 - Reflexion

The technique works with **external feedback signals** (compiler errors, test execution, environment feedback). Critical: external feedback is the enabling factor.

**Implementation:** Implementer agent uses test execution results as feedback loop, not self-assessment.

**Evidence Strength:** Strong (peer-reviewed, specific to code tasks)

---

## Anti-Patterns Avoided

### 1. Constitutional AI Mislabeling

**Issue:** Constitutional AI (Bai et al., 2022) is a **training methodology** requiring model weight modification through RLAIF. It cannot be replicated at inference time.

**Decision:** Agent-dashboard uses "constraint-based validation" terminology, not "Constitutional AI."

---

### 2. Tree of Thoughts for Routine Tasks

**Research:** Katz et al., NeurIPS 2024 - "Thought of Search"

> "The proposed methods are prohibitively inefficient, expensive... the same tasks can be solved with 100% accuracy using only 2-4 LLM calls."

ToT requires 5-20x API calls with marginal benefit outside specific puzzle domains.

**Decision:** Not implemented. Orchestrator uses simpler delegation patterns.

---

### 3. Elaborate Role Personas

**Research:**
- Shanahan et al. paper (often cited for role prompting) is conceptual/philosophical, not empirical
- Learn Prompting: "Idiot" and "Genius" personas performed similarly on factual tasks

**Decision:** Agent definitions use minimal role statements. Token budget invested in examples and constraints.

---

### 4. Unbounded Self-Correction Loops

**Research:** ICLR 2024 findings show self-correction without external feedback leads to:
- Sycophantic behavior (flipping correct answers to incorrect)
- Diminishing returns after 2-3 iterations
- Performance degradation

**Decision:** All iteration patterns have hard limits with escalation protocols.

---

## Techniques Evaluated but Not Implemented

### Chain-of-Verification (CoVe)

**Status:** Not implemented (cost/benefit analysis)

**Research:** Dhuliawala et al., 2023 - Valid technique but:
- Requires N+3 inference calls (6-8x API overhead)
- Validated for factual accuracy, not reasoning synthesis
- ICLR 2024 counter-research shows failure on reasoning tasks

**Decision:** External verification agents provide similar benefit with lower overhead.

---

### Tree of Thoughts (ToT)

**Status:** Not implemented (prohibitive costs)

**Research:** Yao et al., 2023 - 74% vs 4% improvement on Game of 24, but:
- ~100 API calls per task
- NeurIPS 2024 critique: "unsound, incomplete, and prohibitively inefficient"
- Benefits don't transfer from puzzles to software architecture decisions

**Decision:** Simpler multi-option analysis used instead.

---

## Research References

### Primary Sources (Peer-Reviewed)

1. **Huang et al., ICLR 2024** - "Large Language Models Cannot Self-Correct Reasoning Yet"
   - Key finding: Self-correction degrades without external feedback
   - Impact: Validates external verification architecture

2. **Shinn et al., NeurIPS 2023** - "Reflexion: Language Agents with Verbal Reinforcement Learning"
   - Key finding: External feedback signals enable iterative improvement
   - Impact: Validates test-driven iteration pattern

3. **Katz et al., NeurIPS 2024** - "Thought of Search: Planning with Language Models Through The Lens of Efficiency"
   - Key finding: ToT is prohibitively inefficient; 2-4 calls achieve 100% with code generation
   - Impact: Validates decision not to implement ToT

4. **Bai et al., 2022** - "Constitutional AI: Harmlessness from AI Feedback" (arXiv:2212.08073)
   - Key finding: CAI is training methodology, not inference technique
   - Impact: Clarifies terminology usage

5. **Dhuliawala et al., 2023** - "Chain-of-Verification Reduces Hallucination" (arXiv:2309.11495)
   - Key finding: CoVe effective for factual verification, high API cost
   - Impact: Informs cost/benefit analysis

### Secondary Sources

- Learn Prompting empirical studies on role prompting
- ACL 2024 persona variance analysis
- Anthropic, OpenAI, Google official prompting documentation

---

## Alignment Summary

| Design Decision | Research Support | Implementation |
|-----------------|------------------|----------------|
| External verification agents | ICLR 2024 (strong) | critic, validator, research-judge, panel |
| Constraint-based prompting | Multiple sources (strong) | 62+ ALWAYS/NEVER constraints |
| Few-shot examples | Learn Prompting, ACL 2024 (moderate) | 22+ examples across agents |
| Iteration limits | NeurIPS 2023, multiple (strong) | All agents have hard limits |
| No self-correction loops | ICLR 2024 (strong) | External feedback only |
| No ToT implementation | NeurIPS 2024 (strong) | Simpler patterns used |
| Minimal role personas | Multiple studies (moderate) | Examples prioritized |

---

## Recommendations for Future Development

1. **Maintain external verification** - Research consistently validates this pattern
2. **Prioritize examples over personas** when adding new agents
3. **Track API costs** for any multi-call patterns
4. **Require iteration limits** on all new agents
5. **Cite research** when proposing new techniques

---

*This document is based on the Critical Analysis of Cognitive Architectures Report and should be updated as new peer-reviewed research becomes available.*
