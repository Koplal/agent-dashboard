# Pre-Testing Tasks Implementation Plan

**Created:** 2025-12-25
**Branch:** experiment/neuro-symbolic
**Version Target:** 2.6.0

## Executive Summary

This plan addresses three critical pre-testing tasks for the experiment/neuro-symbolic branch:
1. **Token Counting Unification** - Consolidate scattered implementations
2. **Documentation Update** - Document all NESY modules comprehensively
3. **Version Numbering Alignment** - Synchronize versions across codebase

---

## Task 1: Token Counting Unification

### Current State Analysis

The codebase has a well-designed centralized token counter at `src/token_counter.py` with a 4-tier fallback system:
1. Xenova/claude-tokenizer (HuggingFace) - ~95%+ accuracy
2. Anthropic API count_tokens - 100% accuracy
3. tiktoken cl100k_base - ~70-85% accuracy
4. Character estimation - ~60-70% accuracy

However, three files have duplicate implementations that bypass the centralized module.

### Files Requiring Modification

#### 1.1 `hooks/send_event.py` (HIGH PRIORITY)
**Current Issue:** Lines 43-67 contain standalone tiktoken implementation.

**Change Required:**
- Remove inline `count_tokens()` function (lines 56-66)
- Remove `get_tokenizer_info()` function (lines 69-74)
- Add import: `from src.token_counter import count_tokens, get_tokenizer_info`
- Handle import path for hook usage context (may need path adjustment or fallback)

**Risk:** Hooks run from `~/.claude/dashboard/hooks/` which may not have access to `src` module.

**Mitigation Options:**
- Option A: Add `sys.path.insert(0, DASHBOARD_DIR)` before import
- Option B: Keep minimal fallback but prefer centralized import when available
- Option C: Copy token_counter.py to hooks directory during install

**Recommended:** Option B - graceful degradation

#### 1.2 `src/compression_gate.py` (MEDIUM PRIORITY)
**Current Issue:** Lines 36-43 duplicate tiktoken initialization.

**Change Required:**
- Remove tiktoken import and initialization (lines 36-43)
- Add import: `from src.token_counter import count_tokens as _count_tokens`
- Update `count_tokens()` method (line 184) to delegate to centralized function

#### 1.3 `src/workflow_engine.py` (LOW PRIORITY - Already Good)
**Current State:** Already imports from token_counter with inline fallback.
**Change Required:** None - current implementation is correct pattern.

### Implementation Order

1. Update `compression_gate.py` (no deployment concerns)
2. Update `hooks/send_event.py` (requires testing deployed hook)
3. Verify all NESY modules use centralized counting if they need to calculate tokens

### Testing Requirements

- [ ] Run `tests/test_token_counter.py`
- [ ] Run `tests/test_compression_gate.py`
- [ ] Run `tests/test_send_event.py`
- [ ] Manual test: Verify hooks still work after deployment

---

## Task 2: Documentation Update

### Documentation Gaps Identified

1. **README.md** - Missing NESY modules section
2. **CHANGELOG.md** - Missing v2.6.0 entry for NESY implementation
3. **Repository Structure** - Outdated in README
4. **Architecture Documentation** - No NESY integration diagrams
5. **Module Docstrings** - Already good (Version: 2.6.0 in all modules)

### Files Requiring Modification

#### 2.1 `README.md` - MAJOR UPDATE

**Add New Section: "Neurosymbolic Modules" after Panel Judge Workflow**

```markdown
## Neurosymbolic Modules (v2.6.0)

The experiment/neuro-symbolic branch introduces 9 advanced modules for formal verification,
knowledge management, and learning capabilities.

### Module Overview

| Module | Directory | Purpose | Key Features |
|--------|-----------|---------|--------------|
| NESY-001 | `src/validators/` | Output Validation | Pydantic schemas, retry generation |
| NESY-002 | `src/constraints/` | Grammar-Constrained Generation | Schema enforcement, tool_use |
| NESY-003 | `src/judges/` | Heterogeneous Judge Panel | Diversified evaluation, consensus |
| NESY-004 | `src/knowledge/` | Knowledge Graph | Entity extraction, semantic search |
| NESY-005 | `src/verification/` | Z3 Constraint Solver | Formal verification, SMT solving |
| NESY-006 | `src/ledger/` | Progress Tracking | Task ledger, loop detection |
| NESY-007 | `src/specifications/` | Formal DSL | Agent behavior specification |
| NESY-008 | `src/learning/` | Neurosymbolic Learning | Rule extraction, effectiveness |
| NESY-009 | `src/audit/` | Audit Trail | Hash chains, compliance reports |
```

**Update Repository Structure Section:**
Add all new directories under `src/`:
```
├── src/
│   ├── audit/              # NESY-009: Audit trail with hash chaining
│   ├── constraints/        # NESY-002: Grammar-constrained generation
│   ├── judges/             # NESY-003: Heterogeneous judge panel
│   ├── knowledge/          # NESY-004: Knowledge graph layer
│   ├── learning/           # NESY-008: Neurosymbolic learning
│   ├── ledger/             # NESY-006: Progress ledger
│   ├── schemas/            # Pydantic output schemas
│   ├── specifications/     # NESY-007: Formal specification DSL
│   ├── validators/         # NESY-001: Output validators
│   └── verification/       # NESY-005: Z3 symbolic verification
├── specs/                  # Formal specification files (.spec)
```

#### 2.2 `CHANGELOG.md` - ADD v2.6.0 ENTRY

**Add at top of file:**

```markdown
## [2.6.0] - 2025-12-25

### Neurosymbolic Architecture (experiment/neuro-symbolic branch)

Major implementation of 9 neurosymbolic modules providing formal verification,
knowledge management, and learning capabilities.

#### NESY-001: Pydantic Output Validators (`src/validators/`)
- Output validation with Pydantic schemas
- Automatic retry prompt generation
- Field-level verification

#### NESY-002: Grammar-Constrained Generation (`src/constraints/`)
- Schema enforcement using Claude's tool_use feature
- Tool schema registry
- Optional local model support via Outlines

#### NESY-003: Heterogeneous Judge Panel (`src/judges/`)
- Diversified judge configurations (adversarial, rubric, domain-expert, skeptic, end-user)
- Consensus calculation with weighted voting
- Escalation handling

#### NESY-004: Knowledge Graph (`src/knowledge/`)
- Entity and claim storage
- Semantic search with embeddings
- Contradiction detection
- SQLite backend with FTS5

#### NESY-005: Z3 Constraint Solver (`src/verification/`)
- Formal verification with Z3 theorem prover
- Claim classification (logical, mathematical, empirical)
- Hybrid verification combining symbolic and LLM evaluation

#### NESY-006: Progress Ledger (`src/ledger/`)
- Task lifecycle tracking
- Loop detection
- Runtime metrics

#### NESY-007: Formal Specification Language (`src/specifications/`)
- Custom DSL for agent behavior constraints
- AST representation and parsing
- Specification-enforced agent wrapper
- Limit enforcement (timeout, tool calls)

#### NESY-008: Neurosymbolic Learning (`src/learning/`)
- Rule extraction from successful executions
- Effectiveness tracking with Bayesian updates
- Semantic search for rule matching
- Learning orchestrator

#### NESY-009: Audit Trail Infrastructure (`src/audit/`)
- Tamper-evident hash chaining
- Multiple storage backends (file, SQLite, memory)
- Compliance report generation
- Query engine with filters

### Changed
- Version bumped to 2.6.0 across all modules
- Added 21 test files for NESY modules
- Added formal specification files in `specs/` directory
```

#### 2.3 `docs/IMPLEMENTATION.md` - UPDATE VERSION

**Line 1:** Change `v2.4.1` to `v2.6.0`
**Add section:** Neurosymbolic module installation and configuration

#### 2.4 Create New File: `docs/NESY-ARCHITECTURE.md`

**Content should include:**
- Architecture overview diagram
- Module dependencies
- Configuration options
- Integration patterns
- Example usage for each module

### Implementation Order

1. Update `CHANGELOG.md` (simple addition)
2. Update `README.md` (add NESY section, update structure)
3. Update `docs/IMPLEMENTATION.md` (version update, add NESY guide)
4. Create `docs/NESY-ARCHITECTURE.md` (comprehensive new document)

---

## Task 3: Version Numbering Alignment

### Discrepancies Found

| File | Current | Target |
|------|---------|--------|
| `pyproject.toml` | 2.5.3 | **2.6.0** |
| `docs/IMPLEMENTATION.md` | 2.4.1 | **2.6.0** |
| `CHANGELOG.md` | 2.5.2 (latest) | Add **2.6.0** entry |

### Files Requiring Modification

#### 3.1 `pyproject.toml` (CRITICAL)
**Line 8:** Change `version = "2.5.3"` to `version = "2.6.0"`
**Line 1 comment:** Update from `v2.5.2` to `v2.6.0`

#### 3.2 `docs/IMPLEMENTATION.md`
**Line 1:** Change `v2.4.1` to `v2.6.0`

#### 3.3 Verify Consistency
All other files already show `2.6.0`:
- `src/__version__.py` ✓
- `README.md` header ✓
- All NESY `__init__.py` files ✓
- All agent definitions ✓

### Implementation Order

1. Update `pyproject.toml` (single line change)
2. Update `docs/IMPLEMENTATION.md` (version in title)
3. Run verification: `grep -r "version" --include="*.py" --include="*.toml" | grep -v "2.6.0"`

---

## Order of Operations

### Phase 1: Version Alignment (5 minutes)
- [ ] Update `pyproject.toml` version to 2.6.0
- [ ] Update `docs/IMPLEMENTATION.md` version to 2.6.0
- [ ] Verify no other version mismatches

### Phase 2: Token Counting Unification (30 minutes)
- [ ] Update `src/compression_gate.py` to use centralized token_counter
- [ ] Update `hooks/send_event.py` with graceful import pattern
- [ ] Run token-related tests

### Phase 3: Documentation (60 minutes)
- [ ] Update `CHANGELOG.md` with v2.6.0 entry
- [ ] Update `README.md` with NESY modules section
- [ ] Update repository structure in README
- [ ] Update `docs/IMPLEMENTATION.md` with NESY content
- [ ] Create `docs/NESY-ARCHITECTURE.md`

### Phase 4: Verification (15 minutes)
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify hook functionality manually
- [ ] Check documentation renders correctly

---

## Potential Risks and Mitigations

### Risk 1: Hook Import Path Issues
**Risk:** `send_event.py` runs from `~/.claude/dashboard/hooks/` which may not have `src` in path.
**Mitigation:** Use try/except with fallback to standalone implementation.

### Risk 2: Breaking Existing Token Counting
**Risk:** Changing token counting could affect cost tracking.
**Mitigation:** Run comparison tests before and after changes.

### Risk 3: Documentation-Code Drift
**Risk:** Documentation may become outdated again.
**Mitigation:** Add version checks in CI/CD or commit hooks.

---

## Testing Requirements After Changes

### Automated Tests
```bash
# Run all tests
pytest tests/ -v

# Specific test suites
pytest tests/test_token_counter.py -v
pytest tests/test_compression_gate.py -v
pytest tests/test_send_event.py -v
pytest tests/test_ledger.py -v
pytest tests/test_audit.py -v
```

### Manual Tests
- [ ] Start dashboard: `agent-dashboard --web`
- [ ] Trigger a Claude Code task with hooks enabled
- [ ] Verify events appear with accurate token counts
- [ ] Check dashboard shows correct version (2.6.0)

### Documentation Tests
- [ ] Verify README renders correctly on GitHub
- [ ] Check all internal links work
- [ ] Verify NESY module imports work as documented

---

## Critical Files Summary

| File | Task | Change |
|------|------|--------|
| `pyproject.toml` | Version | 2.5.3 → 2.6.0 |
| `hooks/send_event.py` | Token | Remove duplicate, add import |
| `src/compression_gate.py` | Token | Remove duplicate, delegate |
| `README.md` | Docs | Add NESY section, update structure |
| `CHANGELOG.md` | Docs | Add v2.6.0 entry |
| `docs/IMPLEMENTATION.md` | Version + Docs | Update version, add NESY guide |
| `docs/NESY-ARCHITECTURE.md` | Docs | Create new file |

---

## Sign-Off

| Task | Completed | Verified | Date |
|------|-----------|----------|------|
| Version Alignment | [ ] | [ ] | |
| Token Unification | [ ] | [ ] | |
| Documentation | [ ] | [ ] | |
| Final Testing | [ ] | [ ] | |
