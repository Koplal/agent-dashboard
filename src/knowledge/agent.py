"""
Knowledge Graph Enhanced Research Agent.

Provides integration between research agents and the knowledge graph
for enhanced context and knowledge accumulation.

Version: 2.6.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable

from .graph import KGClaim, Entity, EntityType
from .manager import ResearchKnowledgeGraph

logger = logging.getLogger(__name__)


@runtime_checkable
class ResearchAgentProtocol(Protocol):
    """Protocol for research agents."""

    async def research(self, query: str) -> Any:
        """Execute research query."""
        ...


@dataclass
class ResearchClaim:
    """
    A claim extracted from research output.

    Attributes:
        text: The claim text
        confidence: Confidence score
        sources: Source information
    """
    text: str
    confidence: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ResearchOutput:
    """
    Output from a research agent.

    Attributes:
        claims: Extracted claims
        summary: Research summary
        agent_id: Agent that produced the output
        metadata: Additional metadata
    """
    claims: List[ResearchClaim] = field(default_factory=list)
    summary: str = ""
    agent_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class KGEnhancedResearchAgent:
    """
    Research agent with knowledge graph integration.

    Wraps a base research agent to:
    1. Augment queries with existing knowledge
    2. Store new findings in the knowledge graph
    3. Track provenance across research sessions

    Example:
        from src.knowledge import ResearchKnowledgeGraph, KGEnhancedResearchAgent

        kg = ResearchKnowledgeGraph()
        base_agent = MyResearchAgent()  # Your research agent

        enhanced = KGEnhancedResearchAgent(base_agent, kg)
        output = await enhanced.research("What is RAG?", session_id="session-123")
    """

    def __init__(
        self,
        base_agent: Any,
        knowledge_graph: ResearchKnowledgeGraph,
        max_context_claims: int = 5,
        min_context_similarity: float = 0.5,
    ):
        """
        Initialize the enhanced agent.

        Args:
            base_agent: The underlying research agent
            knowledge_graph: Knowledge graph for storage/retrieval
            max_context_claims: Maximum claims to include in context
            min_context_similarity: Minimum similarity for context claims
        """
        self.agent = base_agent
        self.kg = knowledge_graph
        self.max_context_claims = max_context_claims
        self.min_context_similarity = min_context_similarity

    async def research(
        self,
        query: str,
        session_id: str,
        include_existing_knowledge: bool = True,
        store_findings: bool = True,
    ) -> ResearchOutput:
        """
        Execute research with knowledge graph enhancement.

        Args:
            query: Research query
            session_id: Session identifier for tracking
            include_existing_knowledge: Whether to include prior knowledge
            store_findings: Whether to store findings in knowledge graph

        Returns:
            ResearchOutput with claims and summary
        """
        # Check knowledge graph for existing knowledge
        context_from_kg = ""
        if include_existing_knowledge:
            existing = self.kg.find_related_claims(
                query,
                limit=self.max_context_claims,
                min_similarity=self.min_context_similarity,
            )

            if existing.claims:
                context_from_kg = self._format_existing_knowledge(existing.claims)

        # Augment query with existing knowledge
        if context_from_kg:
            augmented_query = f"""{query}

EXISTING KNOWLEDGE (from previous research):
{context_from_kg}

Build upon existing knowledge where relevant. Avoid redundant research.
"""
        else:
            augmented_query = query

        # Execute research
        output = await self._execute_research(augmented_query)

        # Store new findings in knowledge graph
        if store_findings and output.claims:
            await self._store_findings(output, session_id, query)

        return output

    def _format_existing_knowledge(self, claims: List[Dict[str, Any]]) -> str:
        """Format existing claims as context."""
        lines = []
        for claim in claims:
            confidence = claim.get("confidence", 0)
            similarity = claim.get("similarity", 0)
            text = claim.get("text", "")
            lines.append(f"- {text} (confidence: {confidence:.2f}, relevance: {similarity:.2f})")
        return "\n".join(lines)

    async def _execute_research(self, query: str) -> ResearchOutput:
        """Execute research using the base agent."""
        try:
            # Try to call the agent's research method
            if hasattr(self.agent, "research"):
                result = await self.agent.research(query)

                # Try to convert result to ResearchOutput
                if isinstance(result, ResearchOutput):
                    return result
                elif isinstance(result, dict):
                    return self._dict_to_output(result)
                elif isinstance(result, str):
                    return ResearchOutput(
                        summary=result,
                        claims=[ResearchClaim(text=result, confidence=0.7)],
                        agent_id=getattr(self.agent, "agent_id", "unknown"),
                    )
                else:
                    return ResearchOutput(
                        summary=str(result),
                        agent_id=getattr(self.agent, "agent_id", "unknown"),
                    )
            else:
                # Fallback: try calling agent directly
                result = await self.agent(query)
                return ResearchOutput(
                    summary=str(result) if result else "",
                    agent_id=getattr(self.agent, "agent_id", "unknown"),
                )

        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            return ResearchOutput(
                summary=f"Research failed: {str(e)}",
                agent_id=getattr(self.agent, "agent_id", "unknown"),
                metadata={"error": str(e)},
            )

    def _dict_to_output(self, result: Dict[str, Any]) -> ResearchOutput:
        """Convert dictionary result to ResearchOutput."""
        claims = []
        for claim_data in result.get("claims", []):
            if isinstance(claim_data, dict):
                claims.append(ResearchClaim(
                    text=claim_data.get("text", claim_data.get("claim_text", "")),
                    confidence=claim_data.get("confidence", 0.0),
                    sources=claim_data.get("sources", []),
                ))
            elif isinstance(claim_data, str):
                claims.append(ResearchClaim(text=claim_data, confidence=0.7))

        return ResearchOutput(
            claims=claims,
            summary=result.get("summary", ""),
            agent_id=result.get("agent_id", "unknown"),
            metadata=result.get("metadata", {}),
        )

    async def _store_findings(
        self,
        output: ResearchOutput,
        session_id: str,
        query: str,
    ) -> List[str]:
        """Store research findings in knowledge graph."""
        stored_ids = []

        # Extract topics from query
        topics = self.kg.topic_extractor.extract(query)

        for claim in output.claims:
            if not claim.text:
                continue

            # Get source info
            source_url = ""
            source_title = ""
            pub_date = None

            if claim.sources:
                source = claim.sources[0]
                source_url = source.get("url", "")
                source_title = source.get("title", "")
                pub_date_str = source.get("publication_date")
                if pub_date_str:
                    try:
                        from datetime import datetime
                        pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

            # Use session as source if no URL
            if not source_url:
                source_url = f"session://{session_id}"
                source_title = f"Research session {session_id}"

            # Extract entities from claim
            entities = self.kg.entity_extractor.extract(claim.text)

            # Combine claim topics with query topics
            claim_topics = self.kg.topic_extractor.extract(claim.text)
            all_topics = list(set(topics + claim_topics))

            # Store claim
            claim_id = self.kg.add_claim(
                text=claim.text,
                confidence=claim.confidence,
                source_url=source_url,
                source_title=source_title,
                publication_date=pub_date.isoformat() if pub_date else None,
                agent_id=output.agent_id,
                session_id=session_id,
                entities=entities,
                topics=all_topics,
            )
            stored_ids.append(claim_id)

            logger.debug(f"Stored claim {claim_id} from research")

        return stored_ids

    def get_session_summary(self, session_id: str) -> str:
        """Get a summary of knowledge from a session."""
        claims = self.kg.find_claims_by_session(session_id)

        if not claims:
            return "No knowledge recorded in this session."

        lines = [f"Session {session_id} knowledge summary:"]
        lines.append(f"Total claims: {len(claims)}")
        lines.append("")

        # Group by topic
        by_topic: Dict[str, List[KGClaim]] = {}
        for claim in claims:
            for topic in claim.topics:
                if topic not in by_topic:
                    by_topic[topic] = []
                by_topic[topic].append(claim)

        for topic, topic_claims in sorted(by_topic.items()):
            lines.append(f"## {topic.title()}")
            for claim in topic_claims[:3]:  # Limit per topic
                lines.append(f"- {claim.text[:100]}...")
            if len(topic_claims) > 3:
                lines.append(f"  ... and {len(topic_claims) - 3} more")
            lines.append("")

        return "\n".join(lines)


class MockResearchAgent:
    """Mock research agent for testing."""

    def __init__(self, agent_id: str = "mock-researcher"):
        self.agent_id = agent_id

    async def research(self, query: str) -> ResearchOutput:
        """Return mock research output."""
        return ResearchOutput(
            claims=[
                ResearchClaim(
                    text=f"Mock claim about: {query[:50]}",
                    confidence=0.8,
                    sources=[{"url": "https://example.com", "title": "Mock Source"}],
                ),
            ],
            summary=f"Mock research summary for: {query[:100]}",
            agent_id=self.agent_id,
        )
