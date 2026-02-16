"""Pydantic models for LLM structured outputs with validation.

These models are used with Anthropic's structured outputs feature to ensure
the LLM returns valid, non-empty content. They are separate from the API
schemas to allow for stricter validation during generation.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class LLMSubsection(BaseModel):
    """A subsection of a report section.

    Note: Flat structure (no nested subsections) for JSON schema compatibility
    with Anthropic's structured outputs.
    """

    title: str = Field(
        ...,
        description="Subsection title - must be descriptive and non-empty",
    )
    content: str = Field(
        ...,
        description="Subsection content - must contain substantive text",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Subsection title cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Subsection content cannot be empty")
        if len(v.strip()) < 30:
            raise ValueError("Subsection content must be at least 30 characters")
        return v


class LLMReportSection(BaseModel):
    """A section of an LLM-generated report with content validation."""

    title: str = Field(
        ...,
        description="Section title - must be descriptive and non-empty",
    )
    content: str = Field(
        ...,
        description="Section content - must contain substantive text with analysis",
    )
    subsections: list[LLMSubsection] = Field(
        default_factory=list,
        description="Optional subsections for detailed breakdowns",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Section title cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Section content cannot be empty")
        if len(v.strip()) < 50:
            raise ValueError("Section content must be at least 50 characters")
        return v


class LLMGeneratedReport(BaseModel):
    """LLM-generated report structure with comprehensive validation.

    Used with Anthropic's structured outputs to ensure the LLM returns
    a complete, valid report with actual content.
    """

    title: str = Field(
        ...,
        description="Report title - must be descriptive and capture the main topic",
    )
    executive_summary: str = Field(
        ...,
        description="Executive summary - 2-3 paragraphs summarizing key insights",
    )
    sections: list[LLMReportSection] = Field(
        ...,
        description="Main report sections with detailed analysis",
    )
    key_findings: list[str] = Field(
        ...,
        description="Key findings from the analysis - specific and actionable insights",
    )
    recommendations: list[str] = Field(
        ...,
        description="Actionable recommendations based on the findings",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Source documents referenced in the report",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Report title cannot be empty")
        return v.strip()

    @field_validator("executive_summary")
    @classmethod
    def executive_summary_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Executive summary cannot be empty")
        if len(v.strip()) < 100:
            raise ValueError("Executive summary must be at least 100 characters")
        return v

    @field_validator("key_findings")
    @classmethod
    def findings_not_empty(cls, v: list[str]) -> list[str]:
        # Filter out empty strings
        return [f.strip() for f in v if f and f.strip()]

    @field_validator("recommendations")
    @classmethod
    def recommendations_not_empty(cls, v: list[str]) -> list[str]:
        # Filter out empty strings
        return [r.strip() for r in v if r and r.strip()]

    @model_validator(mode="after")
    def validate_content_requirements(self) -> "LLMGeneratedReport":
        """Validate that the report has sufficient content."""
        if len(self.sections) < 1:
            raise ValueError("Report must have at least 1 section")
        if len(self.key_findings) < 2:
            raise ValueError("Report must have at least 2 key findings")
        if len(self.recommendations) < 1:
            raise ValueError("Report must have at least 1 recommendation")
        return self


class LLMPresentationSlide(BaseModel):
    """A slide in an LLM-generated presentation."""

    type: Literal[
        "title", "section", "content", "key_findings",
        "stat_callout", "comparison", "timeline", "chart",
        "recommendations", "closing",
    ] = Field(
        ...,
        description="Slide type determining the layout",
    )
    title: str = Field(
        ...,
        description="Slide title - required for all slide types",
    )
    subtitle: str | None = Field(
        default=None,
        description="Optional subtitle (primarily for title slides)",
    )
    bullets: list[str] | None = Field(
        default=None,
        description="Bullet points for content slides (max 6 recommended)",
    )
    findings: list[str] | None = Field(
        default=None,
        description="Key findings list (for key_findings slide type)",
    )
    items: list[str] | None = Field(
        default=None,
        description="Recommendation items (for recommendations slide type)",
    )
    # stat_callout fields
    stat_value: str | None = Field(
        default=None,
        description="The headline statistic/metric (e.g., '$4.2M', '97%', '3x growth')",
    )
    stat_context: str | None = Field(
        default=None,
        description="Context line explaining the stat's significance",
    )
    # comparison fields
    left_items: list[str] | None = Field(
        default=None,
        description="Left column items for comparison slides",
    )
    right_items: list[str] | None = Field(
        default=None,
        description="Right column items for comparison slides",
    )
    left_label: str | None = Field(
        default=None,
        description="Label for the left comparison column",
    )
    right_label: str | None = Field(
        default=None,
        description="Label for the right comparison column",
    )
    # timeline fields
    events: list[dict[str, str]] | None = Field(
        default=None,
        description="Timeline events as [{date: '...', description: '...'}]",
    )
    # chart fields
    chart_type: str | None = Field(
        default=None,
        description="Chart type: 'bar', 'horizontal_bar', 'line', 'pie'",
    )
    chart_title: str | None = Field(
        default=None,
        description="Chart title/caption",
    )
    data_labels: list[str] | None = Field(
        default=None,
        description="Labels for chart data points",
    )
    data_values: list[float] | None = Field(
        default=None,
        description="Numeric values for chart data points",
    )
    contact: str | None = Field(
        default=None,
        description="Contact information (for closing slides)",
    )
    notes: str | None = Field(
        default=None,
        description="Speaker notes providing additional context",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Slide title cannot be empty")
        return v.strip()


class LLMGeneratedPresentation(BaseModel):
    """LLM-generated presentation structure with validation."""

    title: str = Field(
        ...,
        description="Presentation title",
    )
    slides: list[LLMPresentationSlide] = Field(
        ...,
        description="Presentation slides in order",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Presentation title cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_slides(self) -> "LLMGeneratedPresentation":
        """Validate presentation has required structure."""
        if len(self.slides) < 3:
            raise ValueError("Presentation must have at least 3 slides")

        # Check for title slide
        slide_types = [s.type for s in self.slides]
        if "title" not in slide_types:
            raise ValueError("Presentation must have a title slide")

        return self
