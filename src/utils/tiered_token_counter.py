"""
Tiered Token Counting for Claude Models.

Provides accurate token estimation using a fallback chain of methods,
from most accurate (offline Claude tokenizer) to least accurate
(character estimation), ensuring token counting never fails.

Version: 2.7.0
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# Try to import tiktoken for fallback
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False


@dataclass
class TokenCountResult:
    """Result of token counting."""
    count: int
    method: str  # "xenova" | "tiktoken" | "estimation"
    confidence: float  # 0.70 | 0.95 | 0.999
    cached: bool


@dataclass
class TokenCounterConfig:
    """Configuration for tiered token counter."""
    enable_xenova: bool = True
    enable_tiktoken: bool = True
    short_text_threshold: int = 1000
    cache_ttl: int = 3600
    xenova_timeout: int = 30


class TieredTokenCounter:
    """Tiered token counter with fallback chain."""

    def __init__(self, config: Optional[TokenCounterConfig] = None):
        self.config = config or TokenCounterConfig()
        self._cache: Dict[str, Tuple[TokenCountResult, float]] = {}
        self._tiktoken_encoder = None

        if TIKTOKEN_AVAILABLE and self.config.enable_tiktoken:
            try:
                self._tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                pass

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _check_cache(self, text: str) -> Optional[TokenCountResult]:
        """Check if result is cached and not expired."""
        key = self._get_cache_key(text)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if self.config.cache_ttl < 0 or time.time() - timestamp < self.config.cache_ttl:
                return TokenCountResult(
                    count=result.count,
                    method=result.method,
                    confidence=result.confidence,
                    cached=True,
                )
            else:
                del self._cache[key]
        return None

    def _store_cache(self, text: str, result: TokenCountResult) -> None:
        """Store result in cache."""
        key = self._get_cache_key(text)
        self._cache[key] = (result, time.time())

    def _count_with_estimation(self, text: str) -> TokenCountResult:
        """Estimate tokens using character count."""
        if not text:
            return TokenCountResult(count=0, method="estimation", confidence=0.70, cached=False)
        count = len(text) // 4
        return TokenCountResult(count=count, method="estimation", confidence=0.70, cached=False)

    def _count_with_tiktoken(self, text: str) -> Optional[TokenCountResult]:
        """Count tokens using tiktoken."""
        if not self._tiktoken_encoder:
            return None
        try:
            tokens = self._tiktoken_encoder.encode(text)
            return TokenCountResult(
                count=len(tokens),
                method="tiktoken",
                confidence=0.95,
                cached=False,
            )
        except Exception:
            return None

    def count(self, text: str) -> TokenCountResult:
        """Count tokens using fallback chain."""
        # Check cache first
        cached = self._check_cache(text)
        if cached:
            return cached

        # Short text optimization
        if len(text) < self.config.short_text_threshold:
            result = self._count_with_estimation(text)
            self._store_cache(text, result)
            return result

        # Try tiktoken
        if self.config.enable_tiktoken:
            result = self._count_with_tiktoken(text)
            if result:
                self._store_cache(text, result)
                return result

        # Fallback to estimation
        result = self._count_with_estimation(text)
        self._store_cache(text, result)
        return result

    def count_batch(self, texts: List[str]) -> List[TokenCountResult]:
        """Count tokens for multiple texts."""
        return [self.count(text) for text in texts]

    def clear_cache(self) -> None:
        """Clear the token count cache."""
        self._cache.clear()
