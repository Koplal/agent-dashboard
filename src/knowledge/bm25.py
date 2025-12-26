"""
BM25 Three-Way Hybrid Search for Knowledge Graph.

Implements BM25 keyword search with Reciprocal Rank Fusion (RRF) for
combining keyword, vector, and graph search results.

P1-002: Three-Way Hybrid Retrieval
- Vector similarity (weight 0.4)
- Graph expansion (weight 0.3)  
- BM25 keyword matching (weight 0.3)

Version: 2.8.0
"""

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Set, Callable

from .graph import GraphStorageBackend, KGClaim, Entity, EntityType


# =============================================================================
# English Stopwords (avoid NLTK dependency)
# =============================================================================

ENGLISH_STOPWORDS = frozenset([
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "to", "was", "were", "will", "with", "this", "but", "they",
    "have", "had", "what", "when", "where", "who", "which", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "just", "should", "now", "do", "does",
    "did", "doing", "would", "could", "might", "must", "shall", "may",
    "about", "above", "after", "again", "against", "am", "any", "because",
    "been", "before", "being", "below", "between", "cannot", "down", "during",
    "further", "her", "here", "hers", "herself", "him", "himself", "his", "i", "if",
    "into", "me", "my", "myself", "off", "once", "our", "ours",
    "ourselves", "out", "over", "she", "them", "themselves",
    "then", "there", "these", "those", "through", "under",
    "until", "up", "we", "you", "your",
    "yours", "yourself", "yourselves",
])


# =============================================================================
# Porter Stemmer (simplified implementation, no NLTK dependency)
# =============================================================================

class PorterStemmer:
    """Simplified Porter stemmer for English words."""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    def stem(self, word: str) -> str:
        """Stem a word using Porter algorithm rules."""
        if word in self._cache:
            return self._cache[word]
        
        if len(word) <= 2:
            return word
        
        original = word
        word = word.lower()
        
        # Step 1a
        if word.endswith("sses"):
            word = word[:-2]
        elif word.endswith("ies"):
            word = word[:-2]
        elif word.endswith("ss"):
            pass
        elif word.endswith("s"):
            word = word[:-1]
        
        # Step 1b
        if word.endswith("eed"):
            if len(word) > 4:
                word = word[:-1]
        elif word.endswith("ed"):
            if self._has_vowel(word[:-2]):
                word = word[:-2]
                word = self._step1b_fix(word)
        elif word.endswith("ing"):
            if self._has_vowel(word[:-3]):
                word = word[:-3]
                word = self._step1b_fix(word)
        
        # Step 1c
        if word.endswith("y") and len(word) > 2 and self._has_vowel(word[:-1]):
            word = word[:-1] + "i"
        
        # Step 2
        step2_map = {
            "ational": "ate", "tional": "tion", "enci": "ence",
            "anci": "ance", "izer": "ize", "abli": "able",
            "alli": "al", "entli": "ent", "eli": "e", "ousli": "ous",
            "ization": "ize", "ation": "ate", "ator": "ate",
            "alism": "al", "iveness": "ive", "fulness": "ful",
            "ousness": "ous", "aliti": "al", "iviti": "ive",
            "biliti": "ble",
        }
        for suffix, replacement in step2_map.items():
            if word.endswith(suffix) and len(word) - len(suffix) > 1:
                word = word[:-len(suffix)] + replacement
                break
        
        # Step 3
        step3_map = {
            "icate": "ic", "ative": "", "alize": "al",
            "iciti": "ic", "ical": "ic", "ful": "", "ness": "",
        }
        for suffix, replacement in step3_map.items():
            if word.endswith(suffix) and len(word) - len(suffix) > 1:
                word = word[:-len(suffix)] + replacement
                break
        
        # Step 4
        step4_suffixes = [
            "al", "ance", "ence", "er", "ic", "able", "ible", "ant",
            "ement", "ment", "ent", "ion", "ou", "ism", "ate", "iti",
            "ous", "ive", "ize",
        ]
        for suffix in step4_suffixes:
            if word.endswith(suffix) and len(word) - len(suffix) > 2:
                if suffix == "ion" and len(word) > 4 and word[-4] in "st":
                    word = word[:-3]
                elif suffix != "ion":
                    word = word[:-len(suffix)]
                break
        
        # Step 5
        if word.endswith("e"):
            if len(word) > 3:
                word = word[:-1]
        if word.endswith("ll") and len(word) > 3:
            word = word[:-1]
        
        self._cache[original] = word
        return word
    
    def _has_vowel(self, word: str) -> bool:
        return any(c in "aeiou" for c in word)
    
    def _step1b_fix(self, word: str) -> str:
        if word.endswith(("at", "bl", "iz")):
            return word + "e"
        if len(word) >= 2 and word[-1] == word[-2] and word[-1] not in "lsz":
            return word[:-1]
        return word


# =============================================================================
# Tokenizer Configuration and Class
# =============================================================================

@dataclass
class TokenizerConfig:
    """Configuration for text tokenization."""
    lowercase: bool = True
    remove_stopwords: bool = True
    use_stemming: bool = True
    language: str = "english"


class Tokenizer:
    """Text tokenizer with stopword removal and stemming."""
    
    def __init__(self, config: Optional[TokenizerConfig] = None):
        self.config = config or TokenizerConfig()
        self._stemmer = PorterStemmer() if self.config.use_stemming else None
        self._stopwords = ENGLISH_STOPWORDS if self.config.remove_stopwords else frozenset()
    
    def tokenize(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        
        tokens = re.findall(r"\w+", text)
        
        result = []
        for token in tokens:
            if self.config.lowercase:
                token = token.lower()
            
            if token in self._stopwords:
                continue
            
            if self._stemmer:
                token = self._stemmer.stem(token)
            
            result.append(token)
        
        return result


# =============================================================================
# BM25 Configuration
# =============================================================================

def _tokenize(text: str) -> List[str]:
    """Simple tokenizer for backward compatibility."""
    return re.findall(r"\w+", text.lower())


@dataclass
class BM25Config:
    """Configuration for BM25 index and two-way hybrid retrieval."""
    k1: float = 1.5
    b: float = 0.75
    rrf_k: int = 60
    vector_weight: float = 0.6
    keyword_weight: float = 0.4

    def __post_init__(self):
        if self.k1 < 0:
            raise ValueError("k1 must be non-negative")
        if not 0 <= self.b <= 1:
            raise ValueError("b must be between 0 and 1")
        if self.rrf_k <= 0:
            raise ValueError("rrf_k must be positive")


# =============================================================================
# Three-Way Hybrid Configuration (P1-002)
# =============================================================================

@dataclass
class ThreeWayHybridConfig:
    """Configuration for three-way hybrid retrieval."""
    k1: float = 1.5
    b: float = 0.75
    rrf_k: int = 60
    vector_weight: float = 0.4
    graph_weight: float = 0.3
    bm25_weight: float = 0.3
    max_hops: int = 2
    min_similarity: float = 0.3
    min_graph_score: float = 0.1
    use_stemming: bool = True
    use_stopwords: bool = True

    def __post_init__(self):
        if self.k1 < 0:
            raise ValueError("k1 must be non-negative")
        if not 0 <= self.b <= 1:
            raise ValueError("b must be between 0 and 1")
        if self.rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        if self.vector_weight < 0:
            raise ValueError("vector_weight must be non-negative")
        if self.graph_weight < 0:
            raise ValueError("graph_weight must be non-negative")
        if self.bm25_weight < 0:
            raise ValueError("bm25_weight must be non-negative")
        if self.max_hops <= 0:
            raise ValueError("max_hops must be positive")


# =============================================================================
# BM25 Index (enhanced with tokenizer support)
# =============================================================================

class BM25Index:
    """BM25 inverted index for keyword search."""
    
    def __init__(
        self,
        config: Optional[BM25Config] = None,
        tokenizer: Optional[Tokenizer] = None,
    ):
        self.config = config or BM25Config()
        self.tokenizer = tokenizer
        self.documents: Dict[str, List[str]] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.term_doc_freqs: Dict[str, int] = defaultdict(int)
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.n_docs: int = 0
    
    def _process_text(self, text: str) -> List[str]:
        if self.tokenizer:
            return self.tokenizer.tokenize(text)
        return _tokenize(text)

    def add_document(self, doc_id: str, text: str) -> None:
        tokens = self._process_text(text)
        self.documents[doc_id] = tokens
        self.doc_lengths[doc_id] = len(tokens)
        seen_terms: Set[str] = set()
        for token in tokens:
            self.inverted_index[token][doc_id] = self.inverted_index[token].get(doc_id, 0) + 1
            if token not in seen_terms:
                self.term_doc_freqs[token] += 1
                seen_terms.add(token)
        self.n_docs = len(self.documents)
        self.avg_doc_length = sum(self.doc_lengths.values()) / max(self.n_docs, 1)
    
    def bulk_index(self, documents: List[Tuple[str, str]]) -> int:
        for doc_id, text in documents:
            self.add_document(doc_id, text)
        return len(documents)

    def search(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        query_tokens = self._process_text(query)
        scores: Dict[str, float] = defaultdict(float)
        
        for term in query_tokens:
            if term not in self.inverted_index:
                continue
            df = self.term_doc_freqs[term]
            idf = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1.0)
            for doc_id, tf in self.inverted_index[term].items():
                doc_len = self.doc_lengths[doc_id]
                numerator = tf * (self.config.k1 + 1)
                denominator = tf + self.config.k1 * (1 - self.config.b + self.config.b * doc_len / max(self.avg_doc_length, 1))
                scores[doc_id] += idf * numerator / denominator
        
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:limit]

    def get_document_count(self) -> int:
        return self.n_docs


# =============================================================================
# Reciprocal Rank Fusion
# =============================================================================

def reciprocal_rank_fusion(
    rankings: List[List[Tuple[str, float]]],
    k: int = 60,
    weights: Optional[List[float]] = None,
) -> List[Tuple[str, float]]:
    """Combine multiple rankings using Reciprocal Rank Fusion."""
    if not rankings:
        return []
    if weights is None:
        weights = [1.0] * len(rankings)
    
    fused_scores: Dict[str, float] = defaultdict(float)
    for ranking, weight in zip(rankings, weights):
        for rank, (doc_id, _) in enumerate(ranking, start=1):
            fused_scores[doc_id] += weight / (k + rank)
    
    sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results


# =============================================================================
# Three-Way Retrieval Result (P1-002)
# =============================================================================

@dataclass
class ThreeWayRetrievalResult:
    """Result from three-way hybrid retrieval."""
    claim: KGClaim
    combined_score: float
    vector_score: float
    graph_score: float
    bm25_score: float
    retrieval_path: str
    hop_distance: int
    rrf_rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "combined_score": self.combined_score,
            "vector_score": self.vector_score,
            "graph_score": self.graph_score,
            "bm25_score": self.bm25_score,
            "retrieval_path": self.retrieval_path,
            "hop_distance": self.hop_distance,
            "rrf_rank": self.rrf_rank,
        }


# =============================================================================
# Hybrid BM25 Retriever (existing two-way)
# =============================================================================

class HybridBM25Retriever:
    """Two-way hybrid retriever combining vector and BM25 search."""
    
    def __init__(
        self,
        storage,
        embedding_fn,
        config: Optional[BM25Config] = None,
    ):
        self.storage = storage
        self.embedding_fn = embedding_fn
        self.config = config or BM25Config()
        self.bm25_index = BM25Index(self.config)
        self._indexed_claims: set = set()

    def index_claim(self, claim):
        if claim.claim_id not in self._indexed_claims:
            self.bm25_index.add_document(claim.claim_id, claim.text)
            self._indexed_claims.add(claim.claim_id)

    def index_all_claims(self):
        for claim_id in list(self.storage.claims.keys()):
            claim = self.storage.get_claim(claim_id)
            if claim:
                self.index_claim(claim)

    def retrieve(self, query: str, limit: int = 10) -> List[Tuple[Any, float]]:
        bm25_results = self.bm25_index.search(query, limit=limit * 2)
        query_embedding = self.embedding_fn(query)
        vector_results = self.storage.find_claims_by_embedding(query_embedding, limit=limit * 2, min_similarity=0.0)
        vector_ranking = [(c.claim_id, s) for c, s in vector_results]
        fused = reciprocal_rank_fusion(
            [vector_ranking, bm25_results],
            k=self.config.rrf_k,
            weights=[self.config.vector_weight, self.config.keyword_weight],
        )
        results = []
        for claim_id, score in fused[:limit]:
            claim = self.storage.get_claim(claim_id)
            if claim:
                results.append((claim, score))
        return results


# =============================================================================
# Three-Way Hybrid Retriever V2 (P1-002)
# =============================================================================

EmbeddingFunction = Callable[[str], List[float]]


class HybridRetrieverV2:
    """Three-way hybrid retriever combining vector, graph, and BM25 search."""

    def __init__(
        self,
        storage: GraphStorageBackend,
        embedding_fn: EmbeddingFunction,
        config: Optional[ThreeWayHybridConfig] = None,
        tokenizer: Optional[Tokenizer] = None,
    ):
        self.storage = storage
        self.embedding_fn = embedding_fn
        self.config = config or ThreeWayHybridConfig()
        
        if tokenizer is None:
            tokenizer_config = TokenizerConfig(
                use_stemming=self.config.use_stemming,
                remove_stopwords=self.config.use_stopwords,
            )
            tokenizer = Tokenizer(tokenizer_config)
        
        self.tokenizer = tokenizer
        
        bm25_config = BM25Config(
            k1=self.config.k1,
            b=self.config.b,
            rrf_k=self.config.rrf_k,
        )
        self.bm25_index = BM25Index(bm25_config, tokenizer=tokenizer)
        self._indexed_claims: Set[str] = set()

    def index_documents(self, claims: List[KGClaim]) -> int:
        count = 0
        for claim in claims:
            if claim.claim_id not in self._indexed_claims:
                self.bm25_index.add_document(claim.claim_id, claim.text)
                self._indexed_claims.add(claim.claim_id)
                count += 1
        return count

    def retrieve(
        self,
        query: str,
        limit: int = 10,
    ) -> List[ThreeWayRetrievalResult]:
        if not query or not query.strip():
            return []
        
        query_embedding = self.embedding_fn(query)
        vector_results = self._vector_search(query_embedding, limit * 2)
        
        seed_claims = []
        for claim_id, _ in vector_results:
            claim = self.storage.get_claim(claim_id)
            if claim:
                seed_claims.append(claim)
        graph_results = self._graph_expand(seed_claims, limit * 2)
        
        bm25_results = self._bm25_search(query, limit * 2)
        
        vector_scores: Dict[str, float] = {doc_id: score for doc_id, score in vector_results}
        graph_scores: Dict[str, Tuple[int, float]] = {}
        for claim_id, hop_distance, score in graph_results:
            if claim_id not in graph_scores:
                graph_scores[claim_id] = (hop_distance, score)
        bm25_scores: Dict[str, float] = {doc_id: score for doc_id, score in bm25_results}
        
        rankings = [
            [(doc_id, score) for doc_id, score in vector_results],
            [(claim_id, score) for claim_id, _, score in graph_results],
            bm25_results,
        ]
        weights = [self.config.vector_weight, self.config.graph_weight, self.config.bm25_weight]
        fused = reciprocal_rank_fusion(rankings, k=self.config.rrf_k, weights=weights)
        
        results: List[ThreeWayRetrievalResult] = []
        for rank, (claim_id, combined_score) in enumerate(fused[:limit], start=1):
            claim = self.storage.get_claim(claim_id)
            if not claim:
                continue
            
            v_score = vector_scores.get(claim_id, 0.0)
            hop_dist, g_score = graph_scores.get(claim_id, (0, 0.0))
            b_score = bm25_scores.get(claim_id, 0.0)
            
            path = self._compute_retrieval_path(
                claim_id in vector_scores,
                claim_id in graph_scores,
                claim_id in bm25_scores,
            )
            
            result = ThreeWayRetrievalResult(
                claim=claim,
                combined_score=combined_score,
                vector_score=v_score,
                graph_score=g_score,
                bm25_score=b_score,
                retrieval_path=path,
                hop_distance=hop_dist,
                rrf_rank=rank,
            )
            results.append(result)
        
        return results

    def _vector_search(
        self,
        query_embedding: List[float],
        limit: int,
    ) -> List[Tuple[str, float]]:
        results = self.storage.find_claims_by_embedding(
            embedding=query_embedding,
            limit=limit,
            min_similarity=self.config.min_similarity,
        )
        return [(claim.claim_id, score) for claim, score in results]

    def _graph_expand(
        self,
        seed_claims: List[KGClaim],
        limit: int,
    ) -> List[Tuple[str, int, float]]:
        if not seed_claims:
            return []
        
        max_hops = self.config.max_hops
        min_graph_score = self.config.min_graph_score
        
        seed_ids = {c.claim_id for c in seed_claims}
        seed_entities: Set[Tuple[str, EntityType]] = set()
        
        for claim in seed_claims:
            for entity in claim.entities:
                seed_entities.add((entity.name, entity.entity_type))
        
        results: List[Tuple[str, int, float]] = []
        visited_claims: Set[str] = set(seed_ids)
        current_entities = seed_entities
        current_hop = 1
        
        while current_hop <= max_hops and current_entities and len(results) < limit:
            next_entities: Set[Tuple[str, EntityType]] = set()
            
            for entity_name, entity_type in current_entities:
                claims = self.storage.find_claims_by_entity(entity_name, entity_type)
                
                for claim in claims:
                    if claim.claim_id in visited_claims:
                        continue
                    
                    visited_claims.add(claim.claim_id)
                    
                    claim_entities = {(e.name, e.entity_type) for e in claim.entities}
                    overlap = len(seed_entities & claim_entities)
                    max_entities = max(len(seed_entities), len(claim_entities), 1)
                    overlap_ratio = overlap / max_entities
                    
                    graph_score = (1.0 / (1.0 + current_hop)) * overlap_ratio
                    
                    if graph_score >= min_graph_score:
                        results.append((claim.claim_id, current_hop, graph_score))
                    
                    for entity in claim.entities:
                        next_entities.add((entity.name, entity.entity_type))
            
            current_entities = next_entities - seed_entities
            current_hop += 1
        
        return results[:limit]

    def _bm25_search(self, query: str, limit: int) -> List[Tuple[str, float]]:
        return self.bm25_index.search(query, limit=limit)

    def _compute_retrieval_path(
        self,
        has_vector: bool,
        has_graph: bool,
        has_bm25: bool,
    ) -> str:
        if has_vector and has_graph and has_bm25:
            return "all"
        
        paths = []
        if has_vector:
            paths.append("vector")
        if has_graph:
            paths.append("graph")
        if has_bm25:
            paths.append("bm25")
        
        return "+".join(paths) if paths else "unknown"
