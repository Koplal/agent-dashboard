"""
Grammar-Constrained Generation for Local Models.

Provides constrained generation using the Outlines library for
local transformer models, enabling 100% valid structured outputs.

This is optional and intended for high-volume, cost-sensitive
scenarios where Claude API costs are prohibitive.

Version: 2.6.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


# Check if Outlines is available
OUTLINES_AVAILABLE = False
try:
    import outlines
    OUTLINES_AVAILABLE = True
except ImportError:
    logger.debug("outlines package not installed - local model support disabled")


@dataclass
class LocalGenerationResult:
    """
    Result from local model generation.

    Attributes:
        success: Whether generation succeeded
        output: Generated output (validated)
        raw_text: Raw text from model
        model_used: Model that generated output
        generation_time_ms: Time taken
        tokens_generated: Number of tokens generated
        error: Error message if failed
    """
    success: bool
    output: Optional[Any] = None
    raw_text: Optional[str] = None
    model_used: Optional[str] = None
    generation_time_ms: int = 0
    tokens_generated: int = 0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        output_data = None
        if self.output is not None:
            if isinstance(self.output, BaseModel):
                output_data = self.output.model_dump()
            elif isinstance(self.output, dict):
                output_data = self.output
            else:
                output_data = str(self.output)

        return {
            "success": self.success,
            "output": output_data,
            "raw_text": self.raw_text,
            "model_used": self.model_used,
            "generation_time_ms": self.generation_time_ms,
            "tokens_generated": self.tokens_generated,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class GrammarConstrainedGenerator:
    """
    Grammar-constrained generation using local models.

    Uses the Outlines library to enforce exact schema conformance
    by manipulating token logits during generation.

    Benefits:
    - 100% schema conformance (no retries needed)
    - Cost-effective for high-volume generation
    - Runs locally without API calls

    Limitations:
    - Requires Outlines and a local transformer model
    - Model quality may be lower than Claude
    - GPU recommended for reasonable performance

    Example:
        generator = GrammarConstrainedGenerator()

        # Generate JSON matching schema
        result = generator.generate_json(
            prompt="Analyze this code for security issues",
            schema=SecurityAnalysis
        )

        # Generate text matching regex
        result = generator.generate_regex(
            prompt="Generate an email address",
            pattern=r"[a-z]+@[a-z]+[.][a-z]+"
        )
    """

    # Default model for local generation
    DEFAULT_MODEL = "microsoft/Phi-3-mini-4k-instruct"

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: str = "auto",
        load_on_init: bool = False,
    ):
        """
        Initialize the grammar-constrained generator.

        Args:
            model_name: HuggingFace model name/path
            device: Device to run on ("auto", "cpu", "cuda")
            load_on_init: Whether to load model immediately
        """
        if not OUTLINES_AVAILABLE:
            logger.warning(
                "Outlines not installed. Install with: pip install outlines"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self._model = None
        self._tokenizer = None

        # Statistics
        self.generations_attempted = 0
        self.generations_succeeded = 0
        self.total_tokens = 0

        if load_on_init and OUTLINES_AVAILABLE:
            self._load_model()

    def _load_model(self) -> None:
        """Load the transformer model."""
        if not OUTLINES_AVAILABLE:
            raise RuntimeError("Outlines not installed")

        if self._model is not None:
            return

        logger.info(f"Loading model: {self.model_name}")
        try:
            from outlines import models
            self._model = models.transformers(
                self.model_name,
                device=self.device if self.device != "auto" else None,
            )
            logger.info(f"Model loaded: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def is_available(self) -> bool:
        """Check if local generation is available."""
        return OUTLINES_AVAILABLE

    def generate_json(
        self,
        prompt: str,
        schema: Type[T],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LocalGenerationResult:
        """
        Generate JSON conforming exactly to a Pydantic schema.

        Args:
            prompt: Generation prompt
            schema: Pydantic model class defining structure
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LocalGenerationResult with validated output
        """
        import time
        start_time = time.time()

        self.generations_attempted += 1

        if not OUTLINES_AVAILABLE:
            return LocalGenerationResult(
                success=False,
                error="Outlines not installed",
            )

        try:
            self._load_model()

            from outlines import generate

            generator = generate.json(self._model, schema)

            # Generate with schema constraint
            if temperature > 0:
                result = generator(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            else:
                result = generator(prompt, max_tokens=max_tokens)

            # Result is already validated by Outlines
            self.generations_succeeded += 1
            elapsed_ms = int((time.time() - start_time) * 1000)

            return LocalGenerationResult(
                success=True,
                output=result,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"JSON generation failed: {e}")
            return LocalGenerationResult(
                success=False,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
                error=str(e),
            )

    def generate_regex(
        self,
        prompt: str,
        pattern: str,
        max_tokens: int = 256,
    ) -> LocalGenerationResult:
        """
        Generate text matching a regex pattern.

        Args:
            prompt: Generation prompt
            pattern: Regex pattern to match
            max_tokens: Maximum tokens to generate

        Returns:
            LocalGenerationResult with matching text
        """
        import time
        start_time = time.time()

        self.generations_attempted += 1

        if not OUTLINES_AVAILABLE:
            return LocalGenerationResult(
                success=False,
                error="Outlines not installed",
            )

        try:
            self._load_model()

            from outlines import generate

            generator = generate.regex(self._model, pattern)
            result = generator(prompt, max_tokens=max_tokens)

            self.generations_succeeded += 1
            elapsed_ms = int((time.time() - start_time) * 1000)

            return LocalGenerationResult(
                success=True,
                output=result,
                raw_text=result,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Regex generation failed: {e}")
            return LocalGenerationResult(
                success=False,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
                error=str(e),
            )

    def generate_choice(
        self,
        prompt: str,
        options: List[str],
    ) -> LocalGenerationResult:
        """
        Generate a selection from fixed options.

        Args:
            prompt: Generation prompt
            options: List of valid options

        Returns:
            LocalGenerationResult with selected option
        """
        import time
        start_time = time.time()

        self.generations_attempted += 1

        if not OUTLINES_AVAILABLE:
            return LocalGenerationResult(
                success=False,
                error="Outlines not installed",
            )

        if not options:
            return LocalGenerationResult(
                success=False,
                error="No options provided",
            )

        try:
            self._load_model()

            from outlines import generate

            generator = generate.choice(self._model, options)
            result = generator(prompt)

            self.generations_succeeded += 1
            elapsed_ms = int((time.time() - start_time) * 1000)

            return LocalGenerationResult(
                success=True,
                output=result,
                raw_text=result,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Choice generation failed: {e}")
            return LocalGenerationResult(
                success=False,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
                error=str(e),
            )

    def generate_format(
        self,
        prompt: str,
        format_string: str,
        max_tokens: int = 256,
    ) -> LocalGenerationResult:
        """
        Generate text following a format string pattern.

        Format string uses {} placeholders that will be filled.

        Args:
            prompt: Generation prompt
            format_string: Format pattern like "Name: {}, Age: {}"
            max_tokens: Maximum tokens

        Returns:
            LocalGenerationResult with formatted text
        """
        import time
        start_time = time.time()

        self.generations_attempted += 1

        if not OUTLINES_AVAILABLE:
            return LocalGenerationResult(
                success=False,
                error="Outlines not installed",
            )

        try:
            self._load_model()

            from outlines import generate

            generator = generate.format(self._model, format_string)
            result = generator(prompt, max_tokens=max_tokens)

            self.generations_succeeded += 1
            elapsed_ms = int((time.time() - start_time) * 1000)

            return LocalGenerationResult(
                success=True,
                output=result,
                raw_text=str(result),
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Format generation failed: {e}")
            return LocalGenerationResult(
                success=False,
                model_used=self.model_name,
                generation_time_ms=elapsed_ms,
                error=str(e),
            )

    def unload_model(self) -> None:
        """Unload the model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Model unloaded")

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        success_rate = (
            self.generations_succeeded / self.generations_attempted
            if self.generations_attempted > 0
            else 0.0
        )

        return {
            "outlines_available": OUTLINES_AVAILABLE,
            "model_name": self.model_name,
            "model_loaded": self._model is not None,
            "generations_attempted": self.generations_attempted,
            "generations_succeeded": self.generations_succeeded,
            "success_rate": success_rate,
            "total_tokens": self.total_tokens,
        }


class MockGrammarConstrainedGenerator(GrammarConstrainedGenerator):
    """
    Mock generator for testing without local models.

    Returns predefined or default responses.
    """

    def __init__(
        self,
        mock_responses: Optional[Dict[str, Any]] = None,
        should_succeed: bool = True,
    ):
        """
        Initialize mock generator.

        Args:
            mock_responses: Predefined responses
            should_succeed: Whether generations should succeed
        """
        super().__init__(load_on_init=False)
        self.mock_responses = mock_responses or {}
        self.should_succeed = should_succeed

    def is_available(self) -> bool:
        """Always available for testing."""
        return True

    def _load_model(self) -> None:
        """No-op for mock."""
        pass

    def generate_json(
        self,
        prompt: str,
        schema: Type[T],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LocalGenerationResult:
        """Generate mock JSON response."""
        import time
        start_time = time.time()

        self.generations_attempted += 1

        if not self.should_succeed:
            return LocalGenerationResult(
                success=False,
                model_used="mock",
                error="Mock failure",
            )

        schema_name = schema.__name__
        if schema_name in self.mock_responses:
            try:
                validated = schema.model_validate(self.mock_responses[schema_name])
                self.generations_succeeded += 1
                elapsed_ms = int((time.time() - start_time) * 1000)

                return LocalGenerationResult(
                    success=True,
                    output=validated,
                    model_used="mock",
                    generation_time_ms=elapsed_ms,
                )
            except Exception as e:
                return LocalGenerationResult(
                    success=False,
                    model_used="mock",
                    error=str(e),
                )

        # Return empty success for testing
        self.generations_succeeded += 1
        elapsed_ms = int((time.time() - start_time) * 1000)

        return LocalGenerationResult(
            success=True,
            output=None,
            model_used="mock",
            generation_time_ms=elapsed_ms,
        )

    def generate_regex(
        self,
        prompt: str,
        pattern: str,
        max_tokens: int = 256,
    ) -> LocalGenerationResult:
        """Generate mock regex match."""
        self.generations_attempted += 1

        if not self.should_succeed:
            return LocalGenerationResult(
                success=False,
                model_used="mock",
                error="Mock failure",
            )

        self.generations_succeeded += 1
        return LocalGenerationResult(
            success=True,
            output="mock_match",
            raw_text="mock_match",
            model_used="mock",
        )

    def generate_choice(
        self,
        prompt: str,
        options: List[str],
    ) -> LocalGenerationResult:
        """Generate mock choice."""
        self.generations_attempted += 1

        if not self.should_succeed or not options:
            return LocalGenerationResult(
                success=False,
                model_used="mock",
                error="Mock failure or no options",
            )

        self.generations_succeeded += 1
        return LocalGenerationResult(
            success=True,
            output=options[0],
            raw_text=options[0],
            model_used="mock",
        )
