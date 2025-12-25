"""
Code Analysis Agent Output Schemas.

Pydantic models for validating code analysis outputs including
code locations, issues, and analysis summaries.

Version: 2.6.0
"""

from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .base import BaseAgentOutput, ConfidenceLevel, Severity


class CodeLocation(BaseModel):
    """Reference to a specific code location.

    Attributes:
        file_path: Path to the file (relative or absolute)
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        start_column: Optional starting column
        end_column: Optional ending column
    """
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9_./:@\\-]+$",
        description="Path to the file"
    )
    start_line: int = Field(
        ge=1,
        description="Starting line number (1-indexed)"
    )
    end_line: int = Field(
        ge=1,
        description="Ending line number (1-indexed)"
    )
    start_column: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional starting column"
    )
    end_column: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional ending column"
    )

    @model_validator(mode="after")
    def validate_line_range(self) -> "CodeLocation":
        """Ensure end_line is >= start_line."""
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) must be >= start_line ({self.start_line})"
            )
        return self

    @model_validator(mode="after")
    def validate_column_range(self) -> "CodeLocation":
        """Ensure column range is valid when on same line."""
        if (
            self.start_column is not None
            and self.end_column is not None
            and self.start_line == self.end_line
            and self.end_column < self.start_column
        ):
            raise ValueError(
                f"end_column ({self.end_column}) must be >= start_column ({self.start_column}) "
                "when on the same line"
            )
        return self


class CodeIssue(BaseModel):
    """Identified code issue with context.

    Attributes:
        issue_type: Category of the issue
        severity: How serious the issue is
        location: Where the issue was found
        description: Explanation of the issue
        suggested_fix: Recommended fix (if available)
        confidence: How confident we are in this finding
        references: Related documentation or standards
        rule_id: Optional rule identifier (e.g., OWASP, PEP8)
    """
    model_config = ConfigDict(extra="forbid")

    issue_type: Literal["bug", "vulnerability", "style", "performance", "maintainability"] = Field(
        description="Category of the issue"
    )
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(
        description="How serious the issue is"
    )
    location: CodeLocation = Field(
        description="Where the issue was found"
    )
    description: str = Field(
        min_length=10,
        max_length=2000,
        description="Explanation of the issue"
    )
    suggested_fix: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Recommended fix (if available)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident we are in this finding"
    )
    references: List[str] = Field(
        default_factory=list,
        description="Related documentation or standards"
    )
    rule_id: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Optional rule identifier (e.g., OWASP-A01, PEP8-E501)"
    )

    @model_validator(mode="after")
    def validate_critical_has_fix(self) -> "CodeIssue":
        """Critical and high severity issues should have suggested fixes."""
        if self.severity in ("critical", "high") and not self.suggested_fix:
            # This is a warning, not an error - we'll allow it but it's not ideal
            pass
        return self


class CodeMetrics(BaseModel):
    """Code quality metrics.

    Attributes:
        lines_of_code: Total lines analyzed
        cyclomatic_complexity: Average cyclomatic complexity
        maintainability_index: Maintainability score (0-100)
        test_coverage: Optional test coverage percentage
        duplicate_lines: Number of duplicate lines found
    """
    model_config = ConfigDict(extra="forbid")

    lines_of_code: int = Field(ge=0)
    cyclomatic_complexity: Optional[float] = Field(default=None, ge=0)
    maintainability_index: Optional[float] = Field(default=None, ge=0, le=100)
    test_coverage: Optional[float] = Field(default=None, ge=0, le=100)
    duplicate_lines: Optional[int] = Field(default=None, ge=0)


class CodeAnalysisOutput(BaseAgentOutput):
    """Complete code analysis output schema.

    Attributes:
        target_files: Files that were analyzed
        issues_found: List of issues discovered
        metrics: Code quality metrics
        summary: High-level summary of findings
        analysis_depth: How thorough the analysis was
        language: Programming language(s) analyzed
        frameworks_detected: Frameworks found in the code
    """
    target_files: List[str] = Field(
        min_length=1,
        description="Files that were analyzed"
    )
    issues_found: List[CodeIssue] = Field(
        default_factory=list,
        description="List of issues discovered"
    )
    metrics: Optional[CodeMetrics] = Field(
        default=None,
        description="Code quality metrics"
    )
    summary: str = Field(
        min_length=20,
        max_length=5000,
        description="High-level summary of findings"
    )
    analysis_depth: Literal["surface", "standard", "deep"] = Field(
        description="How thorough the analysis was"
    )
    language: Optional[str] = Field(
        default=None,
        description="Primary programming language"
    )
    frameworks_detected: List[str] = Field(
        default_factory=list,
        description="Frameworks found in the code"
    )

    @field_validator("issues_found")
    @classmethod
    def sort_by_severity(cls, v: List[CodeIssue]) -> List[CodeIssue]:
        """Sort issues by severity (most severe first)."""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        return sorted(v, key=lambda x: severity_order[x.severity])

    @model_validator(mode="after")
    def validate_deep_has_metrics(self) -> "CodeAnalysisOutput":
        """Deep analysis should include metrics."""
        if self.analysis_depth == "deep" and self.metrics is None:
            raise ValueError("Deep analysis should include code metrics")
        return self

    def get_critical_issues(self) -> List[CodeIssue]:
        """Get only critical and high severity issues."""
        return [i for i in self.issues_found if i.severity in ("critical", "high")]

    def get_issues_by_type(self, issue_type: str) -> List[CodeIssue]:
        """Get issues of a specific type."""
        return [i for i in self.issues_found if i.issue_type == issue_type]

    def get_issues_by_file(self, file_path: str) -> List[CodeIssue]:
        """Get issues in a specific file."""
        return [i for i in self.issues_found if i.location.file_path == file_path]
