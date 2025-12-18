# Agent Dashboard - Project Context

## Agent Definitions

**IMPORTANT:** Before spawning any subagent using the Task tool, you MUST:

1. **Check `agents/` directory** for a matching agent definition file
2. **Use the `model` specified** in the agent's frontmatter (opus, sonnet, haiku)
3. **Follow the agent's tier structure:**
   - Tier 1 (Opus): orchestrator, synthesis, critic, planner - Use for complex coordination, synthesis, and critical analysis
   - Tier 2 (Sonnet): researcher, perplexity-researcher, research-judge, claude-md-auditor, implementer, panel-coordinator, judge-*, prompt-enhancer - Use for specialized tasks
   - Tier 3 (Haiku): web-search-researcher, summarizer, installer, validator, test-writer, prompt-validator - Use for quick, focused tasks

4. **Always pass the correct model parameter** when calling Task tool:
   ```
   Task(subagent_type="orchestrator", model="opus", ...)
   Task(subagent_type="researcher", model="sonnet", ...)
   Task(subagent_type="summarizer", model="haiku", ...)
   ```

5. **Read the agent definition file** to understand the agent's:
   - Role and responsibilities
   - Available tools
   - Expected output format
   - Anti-patterns to avoid

## Project Structure

- `src/web_server.py` - Main Flask dashboard with embedded HTML/CSS/JS
- `hooks/send_event.py` - Event sender for Claude Code hooks
- `hooks/run_hook.py` - Cross-platform hook wrapper
- `agents/` - Agent definition files (markdown with frontmatter)
- `docs/` - Technical documentation

## Development Notes

- Dashboard uses SQLite persistence at `~/.claude/agent_dashboard.db`
- CSS uses Tokyo Night color scheme with CSS variables
- Frontend uses vanilla JavaScript (no frameworks)
- Hooks must handle errors silently to not break Claude Code
