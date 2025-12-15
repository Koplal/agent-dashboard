# Prompt Enhancement System

> **Version:** 2.3.0
> **Status:** Production
> **Tier:** 0 (Pre-execution)

The Prompt Enhancement System provides tools to optimize prompts before task execution, ensuring higher quality outputs from Claude. It consists of two specialized agents and two slash commands.

---

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Agents](#agents)
  - [prompt-enhancer](#prompt-enhancer)
  - [prompt-validator](#prompt-validator)
- [Slash Commands](#slash-commands)
  - [/project](#project-command)
  - [/enhance](#enhance-command)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Integration with Agent Tiers](#integration-with-agent-tiers)

---

## Overview

Prompt quality directly impacts output quality. The Prompt Enhancement System addresses this by:

1. **Pre-execution optimization** - Transform vague requests into structured prompts
2. **Quality scoring** - Evaluate prompts against best practices before execution
3. **Workflow standardization** - Consistent project initiation and enhancement patterns

### When to Use

| Situation | Recommended Tool |
|-----------|------------------|
| Starting a new project | `/project` command |
| Enhancing a specific request | `/enhance` command |
| Programmatic prompt optimization | `prompt-enhancer` agent |
| Evaluating existing prompts | `prompt-validator` agent |

---

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                 PROMPT ENHANCEMENT SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐        ┌─────────────────┐                 │
│  │ prompt-enhancer │        │ prompt-validator│                 │
│  │    (Sonnet)     │        │    (Haiku)      │                 │
│  │                 │        │                 │                 │
│  │ Transforms      │        │ Scores prompts  │                 │
│  │ vague → clear   │        │ 1-5 on criteria │                 │
│  └────────┬────────┘        └────────┬────────┘                 │
│           │                          │                           │
│           └──────────┬───────────────┘                           │
│                      │                                           │
│  ┌───────────────────┴───────────────────────────────┐          │
│  │              SLASH COMMANDS                        │          │
│  │  ┌─────────────────┐    ┌─────────────────┐       │          │
│  │  │   /project      │    │   /enhance      │       │          │
│  │  │                 │    │                 │       │          │
│  │  │ Full project    │    │ Single request  │       │          │
│  │  │ workflow        │    │ enhancement     │       │          │
│  │  └─────────────────┘    └─────────────────┘       │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agents

### prompt-enhancer

**Tier:** 0 (Pre-execution)
**Model:** Sonnet
**Tools:** Read, Write, Bash, Grep, Glob

The `prompt-enhancer` agent transforms vague or incomplete requests into well-structured, optimized prompts before task execution.

#### Enhancement Process

1. **Intent Analysis** - Identify task type, complexity, and missing elements
2. **Strategic Clarification** - Ask 1-5 targeted questions (never more)
3. **Prompt Construction** - Build structured prompt with all components
4. **Present and Confirm** - Show enhanced prompt for user approval

#### Prompt Structure

The agent builds prompts with these components:

```markdown
## Role
[Expert persona matching the domain]

## Context
[Background information + WHY this matters]

## Task
[Clear instructions using imperative verbs]

## Constraints
- Format: [Specific requirements]
- Technical: [Language, framework]
- Scope: [Included/excluded]

## Output Format
[Exact structure expected]

## Success Criteria
- [Measurable outcomes]
```

#### When to Use

| Use For | Skip For |
|---------|----------|
| New feature development | Simple factual questions |
| Complex multi-step tasks | Clear, specific requests |
| Ambiguous requests | Bug fixes with exact locations |
| High-stakes outputs | Continuations of existing work |

### prompt-validator

**Tier:** 0 (Pre-execution)
**Model:** Haiku
**Tools:** Read, Grep, Glob

The `prompt-validator` agent scores prompts against Claude 4.x best practices and suggests improvements.

#### Evaluation Criteria

| Criterion | Weight | What It Measures |
|-----------|--------|------------------|
| Clarity | 25% | Intent clarity, ambiguity, specificity |
| Completeness | 25% | Context, constraints, success criteria |
| Structure | 20% | Organization, sections, flow |
| Actionability | 15% | Executability, clear next steps |
| Model Fit | 15% | Optimization for target model |

#### Grading Scale

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 4.5-5.0 | Excellent - ready to execute |
| B | 3.5-4.4 | Good - minor improvements possible |
| C | 2.5-3.4 | Acceptable - should be improved |
| D | 1.5-2.4 | Poor - needs significant work |
| F | 1.0-1.4 | Failing - rewrite required |

#### Output Format

The validator produces a structured report:

```markdown
# Prompt Quality Evaluation

**Prompt:** [First 100 chars...]

## Scores

| Criterion | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Clarity | X/5 | 25% | X.XX |
| Completeness | X/5 | 25% | X.XX |
| Structure | X/5 | 20% | X.XX |
| Actionability | X/5 | 15% | X.XX |
| Model Fit | X/5 | 15% | X.XX |
| **Total** | | | **X.XX/5.00** |

## Grade: [A/B/C/D/F]

## Strengths
- [What works well]

## Issues Found
1. [Issue] → [Specific fix]

## Improved Version
[If score < 4.0]
```

---

## Slash Commands

Slash commands are installed to `~/.claude/commands/` during setup.

### /project Command

**Purpose:** Structured workflow for starting new projects.

**Usage:**
```
/project Build a REST API for user management
```

**Workflow:**

1. **Analyze** - Determine if scope, requirements, and output are clear
2. **Clarify** - Ask 1-5 questions if anything is unclear
3. **Plan** - Create structured project plan with phases
4. **Execute** - Work through each phase with progress updates
5. **Deliver** - Present results with usage instructions

**Plan Structure:**
```markdown
### Project: [Title]

**Goal:** [One sentence]

**Requirements:**
- [From user's answers]

**Phases:**
1. [Phase name] - [What and how]
2. [Phase name] - [What and how]
3. [Phase name] - [What and how]

**Success Criteria:**
- [Completion markers]
- [Quality markers]
```

### /enhance Command

**Purpose:** Enhance a specific request before execution.

**Usage:**
```
/enhance Add dark mode to the settings page
```

**Workflow:**

1. **Analyze** - Check what's missing (language, scope, format, constraints)
2. **Clarify** - Ask targeted questions if critical info is missing
3. **Build** - Create optimized prompt structure
4. **Confirm** - Show enhanced prompt for approval
5. **Execute** - Perform the actual work when confirmed

**Prompt Structure:**
```markdown
### Task
[Clear description with imperative verbs]

### Requirements
[From answers + inferred context]

### Constraints
- Format: [Specific format]
- Technical: [Language, framework]
- Scope: [Boundaries]

### Output Format
[Exact structure expected]

### Success Criteria
- [Completion markers]
- [Excellence markers]
```

---

## Usage Examples

### Example 1: Using /project for a New Feature

**User input:**
```
/project Add authentication to my Express app
```

**Claude response:**
```
Before I plan this project, I need to clarify a few things:

1. What authentication method do you prefer? (JWT, sessions, OAuth)
2. Do you need user registration, or just login?
3. Should I include password reset functionality?
4. What database are you using for user storage?
```

**After answers, Claude creates:**
```markdown
### Project: Express Authentication System

**Goal:** Add JWT-based authentication with registration, login, and password reset.

**Requirements:**
- JWT tokens with 24h expiry
- User registration with email verification
- Password reset via email
- MongoDB for user storage

**Phases:**
1. User Model - Create MongoDB schema with bcrypt password hashing
2. Auth Routes - Implement /register, /login, /logout endpoints
3. JWT Middleware - Create authentication middleware for protected routes
4. Password Reset - Add /forgot-password and /reset-password endpoints
5. Testing - Add integration tests for all auth flows

**Success Criteria:**
- All auth endpoints return proper status codes
- Passwords are hashed before storage
- JWT tokens include user ID and expiry
- Protected routes reject invalid tokens
```

### Example 2: Using /enhance for a Specific Task

**User input:**
```
/enhance Write a function to validate email addresses
```

**Claude analyzes and asks:**
```
To ensure the best result, I need to clarify:

1. What programming language?
2. How strict should validation be? (basic format vs. RFC 5322 compliant)
3. Should it check if the domain exists (DNS lookup)?
```

**After answers, Claude presents:**
```markdown
Here's the enhanced prompt:

### Task
Write a TypeScript function that validates email addresses with moderate strictness.

### Requirements
- Check format matches standard email pattern
- Verify TLD exists (no DNS lookup)
- Handle edge cases: plus addressing, subdomains

### Constraints
- Format: Single function, exported
- Technical: TypeScript, no external dependencies
- Scope: Format validation only, no DNS

### Output Format
- Function with JSDoc comments
- Unit tests covering edge cases
- Example usage

### Success Criteria
- Passes all standard email formats
- Rejects obvious invalid formats
- Returns boolean (not throws)

Ready to execute? (yes/adjust)
```

### Example 3: Using prompt-validator

**Evaluating a prompt:**
```
Please validate this prompt:

"Make my code better"
```

**Validator output:**
```markdown
# Prompt Quality Evaluation

**Prompt:** Make my code better

## Scores

| Criterion | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Clarity | 1/5 | 25% | 0.25 |
| Completeness | 1/5 | 25% | 0.25 |
| Structure | 1/5 | 20% | 0.20 |
| Actionability | 2/5 | 15% | 0.30 |
| Model Fit | 2/5 | 15% | 0.30 |
| **Total** | | | **1.30/5.00** |

## Grade: F

## Strengths
- None identified

## Issues Found
1. No code provided → Include the code to review
2. "Better" undefined → Specify: performance, readability, security?
3. No language specified → State the programming language
4. No constraints → Define what changes are acceptable

## Improved Version
"Review the following TypeScript function for performance
improvements. Focus on reducing time complexity while maintaining
readability. Do not change the function signature.

[code here]

Explain each change and its impact."
```

---

## Best Practices

### For Prompt Enhancement

1. **Don't skip clarification** - Taking time to ask questions produces better results
2. **Be specific about success** - Vague criteria lead to vague outputs
3. **Include constraints** - Scope boundaries prevent over-engineering
4. **Specify output format** - Claude follows structure when given one

### For Prompt Validation

1. **Validate before high-stakes tasks** - Production code, client work
2. **Target score of 4.0+** - Below this, consider using /enhance
3. **Address all issues** - Don't ignore validator feedback
4. **Re-validate after changes** - Confirm improvements worked

### Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Over-questioning | More than 5 questions overwhelms | Max 5, often 2-3 enough |
| Restrictive roles | "You are ONLY a..." limits capability | Enable, don't restrict |
| Vague success | "Make it good" is unmeasurable | Specific, observable criteria |
| Assumed context | Assuming Claude knows your project | Always make context explicit |
| Negative instructions | "Don't use X" | "Use Y instead" |

---

## Integration with Agent Tiers

The Prompt Enhancement System operates at **Tier 0**, meaning it runs before the main agent tier hierarchy:

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0: PRE-EXECUTION                                          │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ prompt-enhancer │    │ prompt-validator│                     │
│  │    (Sonnet)     │    │    (Haiku)      │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           └──────────┬───────────┘                               │
│                      ▼                                           │
├─────────────────────────────────────────────────────────────────┤
│  TIER 1: STRATEGIC (Opus)                                       │
│  orchestrator, synthesis, critic, planner                       │
├─────────────────────────────────────────────────────────────────┤
│  TIER 2: ANALYSIS (Sonnet)                                      │
│  researcher, perplexity-researcher, implementer, panel judges   │
├─────────────────────────────────────────────────────────────────┤
│  TIER 3: EXECUTION (Haiku)                                      │
│  web-search-researcher, summarizer, test-writer, validator      │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow Integration

The enhancement system integrates naturally with the TDD workflow:

1. **Before SPEC phase** - Use `/project` or `prompt-enhancer` to clarify requirements
2. **Before any phase** - Use `prompt-validator` to ensure task clarity
3. **For complex tasks** - Enhanced prompts lead to better specifications

### Cost Considerations

| Agent | Model | Cost Tier |
|-------|-------|-----------|
| prompt-enhancer | Sonnet | $$ (moderate) |
| prompt-validator | Haiku | $ (low) |

- Use `prompt-validator` first (cheap) to check if enhancement is needed
- Use `prompt-enhancer` when score < 4.0 or for complex tasks
- Enhancement cost is offset by reduced iterations and better outputs

---

## Installation

The Prompt Enhancement System is included with Agent Dashboard v2.3.0+.

**Automatic Installation:**
```bash
./scripts/install.sh
```

This installs:
- Agent definitions to `~/.claude/dashboard/agents/`
- Slash commands to `~/.claude/commands/`

**Verify Installation:**
```bash
# Check agents
ls ~/.claude/dashboard/agents/ | grep prompt

# Check commands
ls ~/.claude/commands/
```

---

## Summary

| Component | Purpose | Model | When to Use |
|-----------|---------|-------|-------------|
| `prompt-enhancer` | Transform vague → clear | Sonnet | Complex or ambiguous tasks |
| `prompt-validator` | Score prompt quality | Haiku | Before high-stakes execution |
| `/project` | Structured project start | - | New projects |
| `/enhance` | Quick request enhancement | - | Single task enhancement |

The Prompt Enhancement System ensures you get the best possible outputs by investing in prompt quality before execution.
