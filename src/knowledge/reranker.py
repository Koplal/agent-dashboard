"""
Cross-Encoder Re-Ranking for Knowledge Graph.

Implements re-ranking of candidate documents using cross-encoder models
for improved retrieval precision.

P3-002: Cross-Encoder Re-Ranking
- Cross-encoder scoring for query-document pairs
- Graceful fallback when sentence-transformers unavailable
- Integration with HybridRetrieverV2

Version: 2.8.0
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Any, Dict

# Check for optional dependencies
try:
    from sentence_transformers import CrossEncoder
    CROSSENCODER_AVAILABLE = True
except ImportError:
    CrossEncoder = None
    CROSSENCODER_AVAILABLE = False


@dataclass
class ReRankerConfig:
    """Configuration for cross-encoder re-ranking."""
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    batch_size: int = 32
    show_progress: bool = False
    max_length: int = 512
    top_k: int = 10
    
    def __post_init__(self):
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_length <= 0:
            raise ValueError("max_length must be positive")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")


@dataclass
class ReRankResult:
    """Result of re-ranking a candidate."""
    original_index: int
    text: str
    score: float
    new_rank: int
    
    def to_dict(self) -> Dict:
        return {
            "original_index": self.original_index,
            "text": self.text,
            "score": self.score,
            "new_rank": self.new_rank,
        }


class ReRanker:
    """Cross-encoder re-ranker for improved retrieval precision."""
    
    def __init__(self, config: Optional[ReRankerConfig] = None):
        self.config = config or ReRankerConfig()
        self._model = None
        self._use_crossencoder = CROSSENCODER_AVAILABLE
    
    def _load_model(self) -> None:
        """Lazy load the cross-encoder model."""
        if self._model is None and self._use_crossencoder:
            self._model = CrossEncoder(
                self.config.model_name,
                max_length=self.config.max_length,
            )
    
    def rerank(
        self,
        query: str,
        candidates: List[str],
        top_k: Optional[int] = None,
    ) -> List[ReRankResult]:
        """Re-rank candidates using cross-encoder."""
        if not query or not query.strip():
            return []
        if not candidates:
            return []
        
        top_k = top_k or  self.config.top_k
        
        if self._use_crossencoder:
            return self._rerank_crossencoder(query, candidates, top_k)
        else:
            return self._rerank_fallback(query, candidates, top_k)
    
    def _rerank_crossencoder(
        self,
        query: str,
        candidates: List[str],
        top_k: int,
    ) -> List[ReRankResult]:
        """Re-rank using cross-encoder model."""
        self._load_model()
        
        # Create query-candidate pairs
        pairs = [[query, c] for c in candidates]
        
        # Get scores
        scores = self._model.predict(
            pairs,
            batch_size=self.config.batch_size,
            show_progress_bar=self.config.show_progress,
        )
        
        # Create results with original indices
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for new_rank, (orig_idx, score) in enumerate(indexed_scores[:top_k], start=1):
            results.append(ReRankResult(
                original_index=orig_idx,
                text=candidates[orig_idx],
                score=float(score),
                new_rank=new_rank,
            ))
        
        return results
    
    def _rerank_fallback(
        self,
        query: str,
        candidates: List[str],
        top_k: int,
    ) -> List[ReRankResult]:
        """Fallback: Simple word overlap scoring."""
        query_words = set(query.lower().split())
        
        scores = []
        for i, candidate in enumerate(candidates):
            cand_words = set(candidate.lower().split())
            overlap = len(query_words & cand_words)
            union = len(query_words | cand_words)
            jaccard = overlap / union if union > 0 else 0.0
            scores.append((i, jaccard))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for new_rank, (orig_idx, score) in enumerate(scores[:top_k], start=1):
            results.append(ReRankResult(
                original_index=orig_idx,
                text=candidates[orig_idx],
                score=score,
                new_rank=new_rank,
            ))
        
        return results
    
    def rerank_batch(
        self,
        queries: List[str],
        candidate_lists: List[List[str]],
        top_k: Optional[int] = None,
    ) -> List[List[ReRankResult]]:
        """Re-rank multiple query-candidate sets."""
        if len(queries) != len(candidate_lists):
            raise ValueError("queries and candidate_lists must have same length")
        
        return [
            self.rerank(query, candidates, top_k)
            for query, candidates in zip(queries, candidate_lists)
        ]
