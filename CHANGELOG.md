# Changelog

All notable changes to Agent Dashboard are documented here.

## [2.5.0] - 2025-12-18

### Agent Optimization (v2.4.0 Agent Definitions)

Major update to all 22 agent definitions based on systematic prompt engineering analysis. All changes approved by 5-judge panel (4.4/5 mean score).

#### Quality-First Enhancements
- **5-Judge Panel Minimum** - Panel evaluations require minimum 5 judges (quality floor)
- **Panel Expansion** - High-stakes evaluations can expand to 7 judges
- **62+ New Constraints** - Standardized ALWAYS/NEVER format across all agents
- **Evidence-Citing Requirements** - All panel judges must cite specific evidence
- **Few-Shot Examples** - 18+ examples added to Tier 1 agents and judges

#### Safety Mechanisms
- **Iteration Limits** - Orchestrator (5), Implementer (50), Critic (3), Web-search (10)
- **Test File Protection** - Implementer detects/rejects test modifications
- **Escalation Protocols** - Timeout handling, scope checkpoints, failure escalation
- **Research Caching** - Documented pattern for 20-30% savings

#### Workflow Improvements
- **Standardized Handoff Schemas** - Researchers output structured JSON
- **Verification Gates** - Planner specs require panel review for security features
- **Unresolvable Conflict Handling** - Synthesis marks irreconcilable conflicts

#### Documentation
- Added Research References section with academic sources
- Updated panel size documentation (5-judge minimum)
- Added internal analysis document links

## [2.4.1] - 2025-12-16

### Features

#### Collapsible Project Grouping
- **Collapsible project sections** - Click project headers to expand/collapse agent lists within each project
- **Expand All / Collapse All buttons** - Quick controls at top of Active Sessions panel for managing all project groups at once
- **Project status indicators** - Color-coded dots showing activity status: active (green, pulsing), idle (yellow), inactive (gray)
- **Enhanced project summary bars** - Display total tokens, costs, execution time, active agent count, and time since last activity
- **Nested scrolling** - Projects container and individual agent lists scroll independently for better navigation
- **State persistence** - Collapse/expand states preserved during real-time WebSocket updates

#### Dynamic Viewport Height
- **100vh height** - Dashboard fills entire browser viewport on any screen size
- **Flexbox distribution** - Panels grow proportionally to fill available space
- **Responsive scaling** - Adapts seamlessly from 1080p to 1440p to 4K displays
- **Mobile-first fallback** - Switches to scrollable layout on small screens (below 768px)

#### UI Layout Improvements
- **Optimized grid columns** - Layout uses 1fr 0.9fr 380px for better agent name display
- **Compact statistics panel** - Sized to fit content only, no wasted space
- **Repositioned Registered Agents** - Placed directly below Statistics with 1rem spacing
- **Color-coded model badges** - Opus (purple), Sonnet (blue), Haiku (green)

#### Subagent Name Extraction
- **subagent_type field extraction** - Backend extracts spawned subagent names from Task tool payloads
- **Proper agent tracking** - Dashboard displays actual subagent names instead of generic claude
- **Model inference** - Subagent model tier extracted when available

### Improvements

#### Backend Enhancements
- **New API endpoint** - GET /api/sessions/grouped returns sessions with project aggregates
- **Project aggregation logic** - Server-side calculation of total tokens, cost, execution time per project
- **Session timing tracking** - start_time field tracks session duration accurately
- **Database index** - Added index on project column for faster grouped queries

#### Frontend Enhancements
- **Smooth CSS transitions** - Animated expand/collapse actions for project groups
- **Styled scrollbars** - Custom scrollbar styling matching dashboard theme
- **Agent usage indicators** - Shows which agents have been active in current session
- **Restart/Shutdown controls** - Buttons in header for dashboard lifecycle management

### Bug Fixes
- **JavaScript quote escaping** - Fixed toggleProject() onclick handler for project names containing apostrophes
- **Python string escaping** - Corrected escaping for JavaScript output in server-side HTML generation
- **Token extraction accuracy** - Improved extraction from tool_response.stdout and tool_response.file.content

### Backend Changes
- Updated web_server.py with grouped sessions endpoint and aggregation logic
- Updated send_event.py with subagent_type extraction from Task tool payloads
- Added extract_subagent_name() function for intelligent agent name detection
- Added project status calculation based on agent activity timestamps

### Commits
- d9e0f8f - expandable and collapsable projects
- 5eef082 - updated token tracking, restart and stop
- 3a52e50 - Dashboard enhancements: token tracking, project totals, model colors, controls
- 8279341 - Dashboard improvements: token accuracy, project grouping, responsive design, dynamic agents

## [2.4.0] - 2025-12-16

### Added

#### Collapsible Project Grouping
- **Collapsible project sections** - Click project headers to expand/collapse agent lists
- **Expand All / Collapse All buttons** - Quick controls at top of Active Sessions panel
- **Project status indicators** - Color-coded dots showing active (green), idle (yellow), inactive (gray)
- **Enhanced project metrics** - Total tokens, cost, execution time, time since last activity
- **Nested scrolling** - Projects container and agent lists scroll independently

#### Backend Enhancements
- **New API endpoint** - `GET /api/sessions/grouped` returns sessions with project aggregates
- **Project aggregation** - Backend calculates total tokens, cost, execution time per project
- **Session timing** - Tracks start_time for accurate duration calculation
- **Database index** - Added index on project column for faster queries

#### UI/UX Improvements
- **State persistence** - Collapse/expand states preserved during real-time data updates
- **Smooth transitions** - CSS animations for expand/collapse actions
- **Status indicators** - Visual project activity status with pulsing animation for active projects
- **Improved scrollbars** - Styled scrollbars matching dashboard theme

### Changed
- Version bumped to 2.4.0
- Updated `web_server.py` with new grouping and aggregation logic
- Updated dashboard HTML/CSS for collapsible sections
- Updated JavaScript state management for UI persistence



## [2.3.0] - 2025-12-14

### Added

#### Prompt Enhancement System
- **agents/prompt-enhancer.md** (Tier 0, Sonnet) - Pre-execution prompt optimizer
- **agents/prompt-validator.md** (Tier 0, Haiku) - Prompt quality scoring
- **docs/PROMPT_ENHANCEMENT.md** - Enhancement system documentation

#### Slash Commands
- **commands/** directory - New directory for slash commands
- **commands/project.md** - Structured project workflow (`/project`)
- **commands/enhance.md** - Prompt enhancement with confirmation (`/enhance`)

#### Installation Updates
- install.sh now installs slash commands to `~/.claude/commands/`
- Added COMMANDS_DIR configuration

### Changed
- Version bumped to 2.3.0
- Agent count updated to 22

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
