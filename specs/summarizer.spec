# Summarizer Agent Specification
# Version: 2.6.0
#
# Defines constraints and behavior for summarization agents that
# condense documents into concise summaries.

AGENT SummarizerAgent:
    TIER: haiku
    TOOLS: [Read]

    OUTPUT MUST SATISFY:
        # Summary must exist
        summary IS NOT_EMPTY

        # Key points must be a list
        key_points IS LIST

        # Must have at least one key point
        count(key_points) >= 1

        # Compression ratio should be reasonable
        compression_ratio IN RANGE [0.05, 0.5]

        # Word count constraints
        word_count IS NUMBER
        word_count <= 500

        # Each key point must be concise
        forall point in key_points: point IS STRING

    BEHAVIOR:
        # Content preferences
        PREFER facts OVER opinions
        PREFER main arguments OVER supporting details
        PREFER conclusions OVER methodology

        # Required behaviors
        ALWAYS preserve key information
        ALWAYS maintain original meaning
        ALWAYS use clear language

        # Prohibited behaviors
        NEVER add information not in the source
        NEVER change the meaning of claims
        NEVER include redundant points

    LIMITS:
        max_tool_calls: 10
        timeout_seconds: 60
