"""
Leiden Community Detection for Knowledge Graph.

Detects topically coherent clusters within the knowledge graph using
the Leiden algorithm for community detection.

Version: 2.7.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any, Tuple
from collections import defaultdict

try:
    import igraph as ig
    IGRAPH_AVAILABLE = True
except ImportError:
    ig = None
    IGRAPH_AVAILABLE = False

try:
    import leidenalg
    LEIDENALG_AVAILABLE = True
except ImportError:
    leidenalg = None
    LEIDENALG_AVAILABLE = False


@dataclass
class CommunityConfig:
    """Configuration for community detection."""
    resolution: float = 1.0
    min_community_size: int = 2
    seed: Optional[int] = None
    generate_labels: bool = False

    def __post_init__(self):
        if self.resolution < 0:
            raise ValueError("resolution must be non-negative")
        if self.min_community_size < 1:
            raise ValueError("min_community_size must be at least 1")


@dataclass
class Community:
    """A detected community in the knowledge graph."""
    community_id: str
    members: List[str]
    size: int
    label: Optional[str] = None
    parent_id: Optional[str] = None


@dataclass
class CommunityHierarchy:
    """Hierarchical structure of communities."""
    root: Community
    levels: List[List[Community]]
    total_communities: int

    def get_level(self, depth: int) -> List[Community]:
        """Get communities at a specific depth level."""
        if 0 <= depth < len(self.levels):
            return self.levels[depth]
        return []


@dataclass
class CommunityDetectionResult:
    """Result of community detection."""
    communities: List[Community]
    hierarchy: Optional[CommunityHierarchy]
    modularity: float
    resolution: float
    algorithm: str = "leiden"



class CommunityDetector:
    """Detects communities in knowledge graphs using Leiden algorithm."""

    def __init__(self):
        self._id_to_name: Dict[int, str] = {}
        self._name_to_id: Dict[str, int] = {}

    def _build_igraph(self, backend) -> "ig.Graph":
        """Build an igraph Graph from storage backend."""
        if not IGRAPH_AVAILABLE:
            # Return a fallback empty graph when igraph is not installed
            class FallbackGraph:
                def vcount(self): return 0
                def ecount(self): return 0
                @property
                def es(self): return FallbackEdgeSeq()
            class FallbackEdgeSeq:
                def attributes(self): return []
            return FallbackGraph()

        # Collect all entities from claims
        entity_pairs: Dict[Tuple[str, str], int] = defaultdict(int)
        entities: Set[str] = set()

        for claim_id, claim in getattr(backend, "claims", {}).items():
            claim_entities = [e.name for e in claim.entities]
            entities.update(claim_entities)
            # Create edges between co-occurring entities
            for i, e1 in enumerate(claim_entities):
                for e2 in claim_entities[i+1:]:
                    key = tuple(sorted([e1, e2]))
                    entity_pairs[key] += 1

        if not entities:
            return ig.Graph()

        # Build graph
        entity_list = sorted(entities)
        self._name_to_id = {name: idx for idx, name in enumerate(entity_list)}
        self._id_to_name = {idx: name for name, idx in self._name_to_id.items()}

        g = ig.Graph()
        g.add_vertices(len(entity_list))
        g.vs["name"] = entity_list

        edges = []
        weights = []
        for (e1, e2), weight in entity_pairs.items():
            edges.append((self._name_to_id[e1], self._name_to_id[e2]))
            weights.append(weight)

        if edges:
            g.add_edges(edges)
            g.es["weight"] = weights

        return g

    def detect(self, backend, config: Optional[CommunityConfig] = None) -> CommunityDetectionResult:
        """Detect communities in the knowledge graph."""
        config = config or CommunityConfig()

        graph = self._build_igraph(backend)

        if graph.vcount() == 0:
            return CommunityDetectionResult(
                communities=[],
                hierarchy=None,
                modularity=0.0,
                resolution=config.resolution,
            )

        # Single node case
        if graph.vcount() == 1:
            name = self._id_to_name.get(0, "node-0")
            community = Community(
                community_id="c-0",
                members=[name],
                size=1,
            )
            hierarchy = CommunityHierarchy(
                root=community,
                levels=[[community]],
                total_communities=1,
            )
            return CommunityDetectionResult(
                communities=[community],
                hierarchy=hierarchy,
                modularity=0.0,
                resolution=config.resolution,
            )

        # Run Leiden algorithm if available
        if LEIDENALG_AVAILABLE and IGRAPH_AVAILABLE:
            partition = leidenalg.find_partition(
                graph,
                leidenalg.RBConfigurationVertexPartition,
                resolution_parameter=config.resolution,
                seed=config.seed,
            )
            membership = partition.membership
            modularity = partition.modularity
        else:
            # Fallback: each connected component is a community
            components = graph.connected_components()
            membership = components.membership
            modularity = 0.0

        # Build communities from membership
        community_members: Dict[int, List[str]] = defaultdict(list)
        for node_id, comm_id in enumerate(membership):
            name = self._id_to_name.get(node_id, f"node-{node_id}")
            community_members[comm_id].append(name)

        communities = []
        for comm_id, members in community_members.items():
            if len(members) >= config.min_community_size or len(community_members) == 1:
                label = None
                if config.generate_labels and members:
                    label = f"Community-{comm_id}"
                communities.append(Community(
                    community_id=f"c-{comm_id}",
                    members=members,
                    size=len(members),
                    label=label,
                ))

        # Merge small communities if needed
        if config.min_community_size > 1:
            small = [c for c in communities if c.size < config.min_community_size]
            large = [c for c in communities if c.size >= config.min_community_size]
            for sc in small:
                if large:
                    large[0].members.extend(sc.members)
                    large[0].size = len(large[0].members)
            communities = large if large else communities

        # Build hierarchy (simple single-level for now)
        if communities:
            all_members = []
            for c in communities:
                all_members.extend(c.members)
            root = Community(
                community_id="root",
                members=all_members,
                size=len(all_members),
            )
            hierarchy = CommunityHierarchy(
                root=root,
                levels=[[root], communities],
                total_communities=len(communities) + 1,
            )
        else:
            hierarchy = None

        return CommunityDetectionResult(
            communities=communities,
            hierarchy=hierarchy,
            modularity=modularity,
            resolution=config.resolution,
        )
