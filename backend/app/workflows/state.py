"""Workflow state definitions for LangGraph.

Defines the state that flows through the report generation workflow,
including input, intermediate data, and output.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TypedDict

from app.models.document import ParsedDocument
from app.models.schemas import GeneratedPresentation, GeneratedReport


class WorkflowStep(Enum):
    """Steps in the report generation workflow."""

    PENDING = "pending"
    PARSING = "parsing"
    INDEXING = "indexing"
    BUILDING_CONTEXT = "building_context"
    GENERATING_REPORT = "generating_report"
    GENERATING_PRESENTATION = "generating_presentation"
    RENDERING = "rendering"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentContext:
    """Parsed document with token count."""

    file_name: str
    content: str
    token_count: int


@dataclass
class PreparedContext:
    """Prepared context ready for LLM."""

    documents: list[DocumentContext]
    total_tokens: int
    was_summarized: bool
    combined_content: str


@dataclass
class FileRegistryEntry:
    """Metadata about an uploaded file (no parsed content)."""

    file_id: str
    file_name: str
    file_type: str  # extension, e.g. ".pdf"
    file_size: int  # bytes
    storage_path: str  # Supabase storage path
    mime_type: str = ""


@dataclass
class OutputFile:
    """Generated output file metadata."""

    format: str
    storage_path: str
    download_url: Optional[str] = None
    expires_at: Optional[str] = None


@dataclass
class TokenBudget:
    """Token budget tracker to enforce per-call and cumulative limits.

    Constraints:
    - max_per_call: No single LLM call should exceed this (40% of 200K = 80K)
    - max_cumulative: Total tokens across ALL calls in the workflow
    """

    max_per_call: int = 80_000
    max_cumulative: int = 400_000
    cumulative_input: int = 0
    cumulative_output: int = 0

    @property
    def cumulative_used(self) -> int:
        return self.cumulative_input + self.cumulative_output

    @property
    def remaining(self) -> int:
        return self.max_cumulative - self.cumulative_used

    def can_afford(self, estimated_tokens: int) -> bool:
        return self.cumulative_used + estimated_tokens <= self.max_cumulative

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.cumulative_input += input_tokens
        self.cumulative_output += output_tokens

    def get_file_token_limit(self, total_files: int) -> int:
        """Adaptive per-file token limit based on file count and remaining budget."""
        # Reserve 20K for system prompts, agent reasoning, synthesis, downstream
        available = max(self.remaining - 20_000, 10_000)
        per_file = available // max(total_files, 1)
        return max(1_500, min(per_file, 6_000))


@dataclass
class TokenMetrics:
    """Token usage metrics for a workflow run."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class StepTiming:
    """Timing information for a workflow step."""

    step: WorkflowStep
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class ReportWorkflowState(TypedDict, total=False):
    """State definition for the report generation workflow.

    This TypedDict defines all state that flows through the LangGraph workflow.
    Using TypedDict allows LangGraph to track state mutations and provide
    better debugging/observability.
    """

    # Input (set at workflow start)
    report_id: str
    user_id: str
    config: dict[str, Any]  # Report configuration from database

    # Parsed documents
    documents: list[tuple[str, str]]  # (filename, content) tuples (backward compat)
    parsed_documents: list[ParsedDocument]  # Structured parsed documents with metadata

    # File registry & research notes (agent-based pipeline)
    file_registry: list[Any]
    research_notes: str

    # Research planning
    research_questions: list[str]  # Expanded questions from title + prompt

    # Prepared context
    prepared_context: Optional[PreparedContext]

    # Generated content
    generated_report: Optional[GeneratedReport]
    generated_presentation: Optional[GeneratedPresentation]

    # Output files
    output_files: list[OutputFile]

    # Progress tracking
    current_step: WorkflowStep
    progress: int  # 0-100
    status_message: str

    # Error tracking
    errors: list[str]
    failed: bool

    # Budget & Metrics
    token_budget: TokenBudget
    token_metrics: TokenMetrics
    step_timings: list[StepTiming]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


def create_initial_state(
    report_id: str,
    user_id: str,
    config: dict[str, Any],
) -> ReportWorkflowState:
    """Create initial workflow state.

    Args:
        report_id: Report UUID
        user_id: User UUID
        config: Report configuration

    Returns:
        Initial workflow state
    """
    return ReportWorkflowState(
        report_id=report_id,
        user_id=user_id,
        config=config,
        file_registry=[],
        research_notes="",
        documents=[],
        parsed_documents=[],
        research_questions=[],
        prepared_context=None,
        generated_report=None,
        generated_presentation=None,
        output_files=[],
        current_step=WorkflowStep.PENDING,
        progress=0,
        status_message="Initializing...",
        errors=[],
        failed=False,
        token_budget=TokenBudget(),
        token_metrics=TokenMetrics(),
        step_timings=[],
        started_at=datetime.utcnow(),
        completed_at=None,
    )


def update_progress(
    state: ReportWorkflowState,
    step: WorkflowStep,
    progress: int,
    message: str,
) -> ReportWorkflowState:
    """Update workflow progress.

    Args:
        state: Current state
        step: Current step
        progress: Progress percentage (0-100)
        message: Status message

    Returns:
        Updated state
    """
    return {
        **state,
        "current_step": step,
        "progress": progress,
        "status_message": message,
    }


def mark_step_complete(
    state: ReportWorkflowState,
    step: WorkflowStep,
    started_at: datetime,
) -> ReportWorkflowState:
    """Mark a workflow step as complete with timing.

    Args:
        state: Current state
        step: Completed step
        started_at: When the step started

    Returns:
        Updated state with timing info
    """
    completed_at = datetime.utcnow()
    duration = (completed_at - started_at).total_seconds()

    timing = StepTiming(
        step=step,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration,
    )

    timings = list(state.get("step_timings", []))
    timings.append(timing)

    return {
        **state,
        "step_timings": timings,
    }


def add_error(
    state: ReportWorkflowState,
    error: str,
) -> ReportWorkflowState:
    """Add an error to the workflow state.

    Args:
        state: Current state
        error: Error message

    Returns:
        Updated state with error
    """
    errors = list(state.get("errors", []))
    errors.append(error)

    return {
        **state,
        "errors": errors,
    }


def mark_failed(
    state: ReportWorkflowState,
    error: str,
) -> ReportWorkflowState:
    """Mark the workflow as failed.

    Args:
        state: Current state
        error: Error message

    Returns:
        Updated state marked as failed
    """
    return {
        **add_error(state, error),
        "failed": True,
        "current_step": WorkflowStep.FAILED,
        "completed_at": datetime.utcnow(),
    }


def update_token_metrics(
    state: ReportWorkflowState,
    input_tokens: int,
    output_tokens: int,
    cost: float = 0.0,
) -> ReportWorkflowState:
    """Update token usage metrics and budget tracker.

    Args:
        state: Current state
        input_tokens: Additional input tokens
        output_tokens: Additional output tokens
        cost: Additional cost

    Returns:
        Updated state with metrics
    """
    current = state.get("token_metrics", TokenMetrics())

    updated_metrics = TokenMetrics(
        total_input_tokens=current.total_input_tokens + input_tokens,
        total_output_tokens=current.total_output_tokens + output_tokens,
        estimated_cost=current.estimated_cost + cost,
    )

    # Also update the budget tracker
    budget = state.get("token_budget", TokenBudget())
    budget.record_usage(input_tokens, output_tokens)

    return {
        **state,
        "token_metrics": updated_metrics,
        "token_budget": budget,
    }
