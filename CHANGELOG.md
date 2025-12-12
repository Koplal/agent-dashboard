# Changelog

All notable changes to Agent Dashboard are documented here.

## [2.2.1] - 2025-12-11

### Added
- **docs/EXAMPLE_USAGE.md** - Comprehensive usage guide with:
  - Complete workflow examples using plain language prompts
  - Multi-agent parallel execution walkthrough
  - Hook troubleshooting guide with common issues and solutions
  - Command-line reference for all operations
- Panel Judge Workflow documentation section in README
- New "Panel Judges" subsection in Agent Registry with 6 agents:
  - `panel-coordinator` - Orchestrates evaluation panels
  - `judge-technical` - Technical accuracy evaluation
  - `judge-completeness` - Coverage and gap analysis
  - `judge-practicality` - Real-world usefulness evaluation
  - `judge-adversarial` - Stress-testing and vulnerability finding
  - `judge-user` - End-user perspective evaluation
- Missing src/ modules documented in repository structure:
  - token_counter.py, validation.py, compression_gate.py
  - panel_selector.py, synthesis_validator.py
- test_token_counter.py added to test suite documentation

### Fixed
- Agent count updated from 14 to 20 across all documentation
- Dockerfile version label updated from 2.1.0 to 2.2.1
- Test file count updated from 8 to 9 in repository structure
- aiohttp version requirement corrected from >=3.8.0 to >=3.9.0
- All version strings updated to 2.2.1 across codebase

## [2.2.0] - 2025-12-11

### Changed
- Updated test count from 61 to 225 (actual count across 8 test files)
- Improved cross-platform documentation for Windows/macOS/Linux
- Standardized Python command references for cross-platform compatibility
- Enhanced docstrings across all source modules
- Unified validation layer terminology (Six-Layer Validation)

### Added
- CHANGELOG.md for version tracking
- Comprehensive test coverage table in README
- Cross-platform Python invocation guidance
- Version field added to all agent YAML frontmatter
- Tier field added to all agent definitions

### Fixed
- Corrected test count discrepancy in documentation
- Fixed hardcoded `python3` references that fail on Windows
- Standardized validation terminology to "Six-Layer Validation"

## [2.1.0] - Previous Release

### Added
- TDD Workflow Integration
- Test Immutability enforcement
- 7-Phase TDD Workflow (SPEC → TEST_DESIGN → TEST_IMPL → IMPLEMENT → VALIDATE → REVIEW → DELIVER)
- TODO/Mock Detection in validation
- VS Code Integration instructions
- Panel judges for quality evaluation
- Enhanced agent definitions with TDD-focused roles
- Circuit breaker pattern for cost governance

### Changed
- Reorganized agent registry into 3 tiers (Opus/Sonnet/Haiku)
- Improved compression gate with token budgeting
- Enhanced synthesis validator with loop counter logic

## [2.0.0] - Initial Public Release

### Added
- Multi-agent workflow orchestration engine
- Real-time terminal dashboard (Rich TUI)
- Web dashboard with WebSocket updates
- 14 specialized agents across 3 model tiers
- SQLite-based event persistence
- Cost tracking and budget enforcement
- Handoff schema validation
- Compression gating between agent tiers
