#!/usr/bin/env python3
"""
token_counter.py - Accurate token counting for Claude models

Provides tiered token counting with automatic fallback:
  1. Xenova/claude-tokenizer (HuggingFace) - Fast, local, ~95%+ accurate
  2. Anthropic API count_tokens - 100% accurate, requires API key
  3. tiktoken cl100k_base - ~70-85% accurate fallback
  4. Character estimation - Emergency fallback (~4 chars/token)

Usage:
    from src.token_counter import count_tokens, get_tokenizer_info

    tokens = count_tokens("Hello, world!")
    info = get_tokenizer_info()  # Returns which tokenizer is active

Dependencies:
    - transformers + tokenizers (recommended): pip install transformers tokenizers
    - tiktoken (fallback): pip install tiktoken
    - anthropic (optional API): pip install anthropic

Version: 2.2.1
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TokenizerTier(Enum):
    """Available tokenizer tiers in order of preference."""
    CLAUDE_HF = "claude-hf"          # Xenova/claude-tokenizer (HuggingFace)
    ANTHROPIC_API = "anthropic-api"  # Official Anthropic API
    TIKTOKEN = "tiktoken"            # OpenAI tiktoken fallback
    CHARACTER = "character"          # Character-based estimation


@dataclass
class TokenizerInfo:
    """Information about the active tokenizer."""
    tier: TokenizerTier
    name: str
    accuracy: str
    requires_network: bool
    is_available: bool
    error: Optional[str] = None


# =============================================================================
# TOKENIZER INITIALIZATION
# =============================================================================

# Tier 1: HuggingFace Claude Tokenizer (RECOMMENDED)
_claude_hf_tokenizer = None
_CLAUDE_HF_AVAILABLE = False
_claude_hf_error = None

try:
    from transformers import GPT2TokenizerFast
    _claude_hf_tokenizer = GPT2TokenizerFast.from_pretrained(
        'Xenova/claude-tokenizer',
        local_files_only=False
    )
    _CLAUDE_HF_AVAILABLE = True
    logger.info("Claude HuggingFace tokenizer loaded successfully")
except ImportError as e:
    _claude_hf_error = f"transformers not installed: {e}"
    logger.debug(f"HuggingFace tokenizer not available: {_claude_hf_error}")
except Exception as e:
    _claude_hf_error = f"Failed to load tokenizer: {e}"
    logger.warning(f"HuggingFace tokenizer failed: {_claude_hf_error}")


# Tier 2: Anthropic API Client
_anthropic_client = None
_ANTHROPIC_API_AVAILABLE = False
_anthropic_error = None

try:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
        _ANTHROPIC_API_AVAILABLE = True
        logger.info("Anthropic API client initialized")
    else:
        _anthropic_error = "ANTHROPIC_API_KEY not set"
        logger.debug("Anthropic API not available: no API key")
except ImportError as e:
    _anthropic_error = f"anthropic package not installed: {e}"
    logger.debug(f"Anthropic API not available: {_anthropic_error}")
except Exception as e:
    _anthropic_error = f"Failed to initialize client: {e}"
    logger.warning(f"Anthropic API failed: {_anthropic_error}")


# Tier 3: tiktoken Fallback
_tiktoken_encoding = None
_TIKTOKEN_AVAILABLE = False
_tiktoken_error = None

try:
    import tiktoken
    _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
    _TIKTOKEN_AVAILABLE = True
    logger.info("tiktoken fallback loaded (cl100k_base)")
except ImportError as e:
    _tiktoken_error = f"tiktoken not installed: {e}"
    logger.debug(f"tiktoken not available: {_tiktoken_error}")
except Exception as e:
    # Network errors can occur when downloading encoding files
    _tiktoken_error = f"Failed to load encoding: {e}"
    logger.warning(f"tiktoken failed: {_tiktoken_error}")


# =============================================================================
# PUBLIC API
# =============================================================================

def count_tokens(
    text: str,
    model: str = "claude-sonnet-4-5",
    prefer_api: bool = False,
    force_tier: Optional[TokenizerTier] = None
) -> int:
    """
    Count tokens in text using the best available tokenizer.

    Args:
        text: Input text to tokenize
        model: Claude model name (used for API calls)
        prefer_api: If True, prefer Anthropic API over local tokenizer
        force_tier: Force a specific tokenizer tier (for testing)

    Returns:
        Estimated token count

    Examples:
        >>> count_tokens("Hello, world!")
        4
        >>> count_tokens("Hello", prefer_api=True)  # Uses API if available
        1
    """
    if not text:
        return 0

    # Force specific tier if requested
    if force_tier:
        return _count_with_tier(text, force_tier, model)

    # Tier selection based on preference
    if prefer_api and _ANTHROPIC_API_AVAILABLE:
        result = _count_with_anthropic_api(text, model)
        if result is not None:
            return result

    # Tier 1: HuggingFace Claude tokenizer (default preference)
    if _CLAUDE_HF_AVAILABLE:
        return _count_with_claude_hf(text)

    # Tier 2: Anthropic API (if not already tried)
    if _ANTHROPIC_API_AVAILABLE and not prefer_api:
        result = _count_with_anthropic_api(text, model)
        if result is not None:
            return result

    # Tier 3: tiktoken fallback
    if _TIKTOKEN_AVAILABLE:
        return _count_with_tiktoken(text)

    # Tier 4: Character estimation
    return _count_with_characters(text)


def count_tokens_batch(
    texts: List[str],
    model: str = "claude-sonnet-4-5"
) -> List[int]:
    """
    Count tokens for multiple texts efficiently.

    Args:
        texts: List of input texts
        model: Claude model name

    Returns:
        List of token counts corresponding to each input text
    """
    return [count_tokens(text, model) for text in texts]


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-sonnet-4-5"
) -> float:
    """
    Estimate API cost based on token counts.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Claude model name

    Returns:
        Estimated cost in USD
    """
    # Pricing per million tokens (as of 2025)
    PRICING = {
        "opus": {"input": 15.0, "output": 75.0},
        "sonnet": {"input": 3.0, "output": 15.0},
        "haiku": {"input": 0.25, "output": 1.25},
    }

    # Determine tier from model name
    model_lower = model.lower()
    if "opus" in model_lower:
        tier = "opus"
    elif "haiku" in model_lower:
        tier = "haiku"
    else:
        tier = "sonnet"  # Default to sonnet

    prices = PRICING[tier]
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]

    return input_cost + output_cost


def get_tokenizer_info() -> TokenizerInfo:
    """
    Get information about the currently active tokenizer.

    Returns:
        TokenizerInfo with details about the active tokenizer
    """
    if _CLAUDE_HF_AVAILABLE:
        return TokenizerInfo(
            tier=TokenizerTier.CLAUDE_HF,
            name="Xenova/claude-tokenizer",
            accuracy="~95%+",
            requires_network=False,
            is_available=True
        )
    elif _ANTHROPIC_API_AVAILABLE:
        return TokenizerInfo(
            tier=TokenizerTier.ANTHROPIC_API,
            name="Anthropic API count_tokens",
            accuracy="100%",
            requires_network=True,
            is_available=True
        )
    elif _TIKTOKEN_AVAILABLE:
        return TokenizerInfo(
            tier=TokenizerTier.TIKTOKEN,
            name="tiktoken (cl100k_base)",
            accuracy="~70-85%",
            requires_network=False,
            is_available=True
        )
    else:
        return TokenizerInfo(
            tier=TokenizerTier.CHARACTER,
            name="Character estimation",
            accuracy="~60-70%",
            requires_network=False,
            is_available=True,
            error="No tokenizer libraries installed"
        )


def get_all_tokenizers_status() -> Dict[str, TokenizerInfo]:
    """
    Get status of all tokenizer tiers.

    Returns:
        Dictionary mapping tier names to their status
    """
    return {
        "claude-hf": TokenizerInfo(
            tier=TokenizerTier.CLAUDE_HF,
            name="Xenova/claude-tokenizer",
            accuracy="~95%+",
            requires_network=False,
            is_available=_CLAUDE_HF_AVAILABLE,
            error=_claude_hf_error
        ),
        "anthropic-api": TokenizerInfo(
            tier=TokenizerTier.ANTHROPIC_API,
            name="Anthropic API count_tokens",
            accuracy="100%",
            requires_network=True,
            is_available=_ANTHROPIC_API_AVAILABLE,
            error=_anthropic_error
        ),
        "tiktoken": TokenizerInfo(
            tier=TokenizerTier.TIKTOKEN,
            name="tiktoken (cl100k_base)",
            accuracy="~70-85%",
            requires_network=False,
            is_available=_TIKTOKEN_AVAILABLE,
            error=_tiktoken_error
        ),
        "character": TokenizerInfo(
            tier=TokenizerTier.CHARACTER,
            name="Character estimation",
            accuracy="~60-70%",
            requires_network=False,
            is_available=True,
            error=None
        ),
    }


# =============================================================================
# INTERNAL FUNCTIONS
# =============================================================================

def _count_with_tier(text: str, tier: TokenizerTier, model: str) -> int:
    """Count tokens using a specific tier."""
    if tier == TokenizerTier.CLAUDE_HF:
        if not _CLAUDE_HF_AVAILABLE:
            raise RuntimeError(f"Claude HF tokenizer not available: {_claude_hf_error}")
        return _count_with_claude_hf(text)
    elif tier == TokenizerTier.ANTHROPIC_API:
        if not _ANTHROPIC_API_AVAILABLE:
            raise RuntimeError(f"Anthropic API not available: {_anthropic_error}")
        result = _count_with_anthropic_api(text, model)
        if result is None:
            raise RuntimeError("Anthropic API call failed")
        return result
    elif tier == TokenizerTier.TIKTOKEN:
        if not _TIKTOKEN_AVAILABLE:
            raise RuntimeError(f"tiktoken not available: {_tiktoken_error}")
        return _count_with_tiktoken(text)
    else:
        return _count_with_characters(text)


def _count_with_claude_hf(text: str) -> int:
    """Count tokens using HuggingFace Claude tokenizer."""
    return len(_claude_hf_tokenizer.encode(text))


def _count_with_anthropic_api(text: str, model: str) -> Optional[int]:
    """Count tokens using Anthropic API."""
    try:
        response = _anthropic_client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}]
        )
        return response.input_tokens
    except Exception as e:
        logger.warning(f"Anthropic API token count failed: {e}")
        return None


def _count_with_tiktoken(text: str) -> int:
    """Count tokens using tiktoken (OpenAI tokenizer)."""
    return len(_tiktoken_encoding.encode(text))


def _count_with_characters(text: str) -> int:
    """Estimate tokens from character count (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


# =============================================================================
# COMPATIBILITY ALIASES
# =============================================================================

# For backward compatibility with existing code
estimate_tokens = count_tokens


if __name__ == "__main__":
    # Quick test
    test_text = "Hello, world! This is a test of the Claude tokenizer."

    print("Token Counter Status")
    print("=" * 50)

    for name, info in get_all_tokenizers_status().items():
        status = "+" if info.is_available else "-"
        print(f"{status} {name}: {info.name}")
        if info.error:
            print(f"    Error: {info.error}")

    print()
    print(f"Active tokenizer: {get_tokenizer_info().name}")
    print(f"Test text: {test_text!r}")
    print(f"Token count: {count_tokens(test_text)}")
