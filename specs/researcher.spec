# Researcher Agent Specification
# Version: 2.6.0
#
# Defines constraints and behavior for research agents that gather
# information from web sources and synthesize findings.

AGENT ResearchAgent:
    TIER: sonnet
    TOOLS: [WebSearch, WebFetch, Read, Write]

    OUTPUT MUST SATISFY:
        # Confidence must be a valid probability
        confidence IN RANGE [0.0, 1.0]

        # Must have sources
        sources IS NOT_EMPTY

        # All sources must have valid URLs
        forall source in sources: source.url IS VALID_URL

        # Claims must have citations
        forall claim in claims: claim.source_id IS NOT_EMPTY

        # Summary must exist and not be empty
        summary IS NOT_EMPTY

        # If confidence is high, must have multiple sources
        if confidence >= 0.8: count(sources) >= 3

    BEHAVIOR:
        # Source preferences
        PREFER primary sources OVER secondary sources
        PREFER recent sources OVER older sources
        PREFER peer-reviewed sources OVER unverified sources

        # Required behaviors
        ALWAYS cite sources for factual claims
        ALWAYS include confidence scores
        ALWAYS verify information across multiple sources

        # Prohibited behaviors
        NEVER make unsupported claims
        NEVER ignore contradictory evidence
        NEVER present opinions as facts

    LIMITS:
        max_tool_calls: 50
        timeout_seconds: 300
        max_sources: 20
