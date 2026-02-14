"""Research agent node — multi-run with progress.md for context management.

Splits research into 3 phases to prevent unbounded context growth:
1. Planning (haiku): Review files, create analysis strategy
2. File Analysis (sonnet, per-file): Read each file with tools, write findings to progress.md
3. Synthesis (sonnet): Compile progress.md into final research notes

Each file analysis run starts with a fresh conversation. progress.md serves
as persistent memory between runs, keeping peak per-call context under 80K
and total cumulative under 400K tokens.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic_ai import Agent, RunContext
from pydantic_ai_litellm import LiteLLMModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.llm import GatewayConfig, ModelGateway, TaskType
from app.llm.token_counter import TokenCounter
from app.services.code_executor import execute_python_code
from app.services.document_parser import ParserFactory
from app.services.supabase import get_supabase_client
from app.workflows.state import (
    FileRegistryEntry,
    ReportWorkflowState,
    TokenBudget,
    WorkflowStep,
    mark_failed,
    mark_step_complete,
    update_progress,
    update_token_metrics,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Tool output limits (Strategy 3)
MAX_CODE_OUTPUT_CHARS = 4_000
MAX_SEARCH_MATCHES = 10


@dataclass
class ResearchDeps:
    """Dependencies available to the research agent's tools."""

    report_id: str
    user_id: str
    file_registry: list[FileRegistryEntry]
    upload_bucket: str
    temp_dir: str
    file_token_limit: int = 4_000  # Adaptive, set by budget tracker

    # Caches to avoid re-downloading/re-parsing
    _file_cache: dict[str, str] = field(default_factory=dict)
    _download_cache: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / f"{name}.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    logger.warning(f"Prompt file not found: {prompt_path}")
    return ""


def _build_file_list(file_registry: list[FileRegistryEntry]) -> str:
    """Build a minimal formatted file listing (names only)."""
    if not file_registry:
        return "(no files available)"
    return "\n".join(f"- {e.file_name}" for e in file_registry)


def _build_file_list_with_details(file_registry: list[FileRegistryEntry]) -> str:
    """Build detailed file listing with types and sizes."""
    if not file_registry:
        return "(no files available)"
    lines = []
    for e in file_registry:
        size_kb = e.file_size / 1024
        lines.append(f"- {e.file_name} (type: {e.file_type}, size: {size_kb:.1f} KB)")
    return "\n".join(lines)


def _format_loaded_skills(loaded_skills: list[dict[str, str]]) -> str:
    """Format pre-loaded skills for system prompt."""
    if not loaded_skills:
        return ""
    parts = ["ANALYSIS SKILLS:", ""]
    for skill in loaded_skills:
        parts.append(f"### {skill['name']}")
        parts.append(skill["content"])
        parts.append("")
    return "\n".join(parts)


def _find_file(
    registry: list[FileRegistryEntry], file_name: str
) -> Optional[FileRegistryEntry]:
    """Find a file in the registry by name (case-insensitive)."""
    file_name_lower = file_name.lower()
    for entry in registry:
        if entry.file_name.lower() == file_name_lower:
            return entry
    # Try partial match
    for entry in registry:
        if file_name_lower in entry.file_name.lower():
            return entry
    return None


async def _download_file(
    deps: ResearchDeps, entry: FileRegistryEntry
) -> str:
    """Download a file from Supabase storage to temp directory."""
    if entry.file_name in deps._download_cache:
        return deps._download_cache[entry.file_name]

    supabase = get_supabase_client()

    local_path = Path(deps.temp_dir) / entry.file_name
    local_path.parent.mkdir(parents=True, exist_ok=True)

    file_data = supabase.storage.from_(deps.upload_bucket).download(
        entry.storage_path
    )
    local_path.write_bytes(file_data)

    local_str = str(local_path)
    deps._download_cache[entry.file_name] = local_str

    logger.info(f"[RESEARCH] Downloaded: {entry.file_name} → {local_str}")
    return local_str


# ---------------------------------------------------------------------------
# Progress file management
# ---------------------------------------------------------------------------

def _read_progress(progress_path: Path) -> str:
    """Read current progress.md content."""
    if progress_path.exists():
        return progress_path.read_text(encoding="utf-8")
    return ""


def _write_progress(progress_path: Path, content: str) -> None:
    """Write progress.md content."""
    progress_path.write_text(content, encoding="utf-8")


def _append_findings(progress_path: Path, file_name: str, findings: str) -> None:
    """Append findings for a file to progress.md."""
    current = _read_progress(progress_path)
    updated = f"{current}\n\n### {file_name}\n{findings}"
    _write_progress(progress_path, updated.strip())


# ---------------------------------------------------------------------------
# Phase 1: Planning (haiku — cheap, fast)
# ---------------------------------------------------------------------------

async def _run_planning_phase(
    state: ReportWorkflowState,
    gateway: ModelGateway,
    progress_path: Path,
) -> tuple[str, int, int]:
    """Create an analysis strategy for the uploaded files.

    Returns:
        (plan_text, input_tokens, output_tokens)
    """
    config = state["config"]
    file_registry = state["file_registry"]

    system_prompt = (
        "You are a research planning agent. Given a list of uploaded files "
        "and user instructions, create a brief analysis plan.\n\n"
        "Output a numbered list of files in the order they should be analyzed, "
        "with 1-2 bullet points per file describing what to look for.\n"
        "Keep your response concise — under 500 words."
    )

    user_message = (
        f"REPORT TITLE: {config.get('title', 'Research Report')}\n"
        f"DETAIL LEVEL: {config.get('detail_level', 'standard')}\n"
        f"USER INSTRUCTIONS: {config.get('custom_instructions', 'Analyze the provided documents')}\n\n"
        f"AVAILABLE FILES:\n{_build_file_list_with_details(file_registry)}\n\n"
        f"Create an analysis plan for these files."
    )

    plan_text, usage = await gateway.generate_text(
        task=TaskType.CLASSIFICATION,  # Routes to haiku
        messages=[{"role": "user", "content": user_message}],
        system_prompt=system_prompt,
        max_tokens=1000,
    )

    # Write initial progress.md with the plan
    initial_progress = f"# Research Progress\n\n## Analysis Plan\n{plan_text}\n\n## Findings\n"
    _write_progress(progress_path, initial_progress)

    logger.info(
        f"[RESEARCH] Planning complete: {usage.input_tokens} in, "
        f"{usage.output_tokens} out"
    )

    return plan_text, usage.input_tokens, usage.output_tokens


# ---------------------------------------------------------------------------
# Phase 2: Per-file analysis (sonnet with tools)
# ---------------------------------------------------------------------------

def _create_file_analysis_agent(
    system_prompt: str,
) -> Agent[ResearchDeps, str]:
    """Create a pydantic-ai agent for single-file analysis with tools."""
    model = LiteLLMModel("anthropic/claude-sonnet-4-20250514")

    agent: Agent[ResearchDeps, str] = Agent(
        model,
        deps_type=ResearchDeps,
        output_type=str,
        system_prompt=system_prompt,
    )

    @agent.tool
    async def read_file(ctx: RunContext[ResearchDeps], file_name: str) -> str:
        """Read and parse a source file to extract its text content.

        Args:
            file_name: Name of the file to read (must match a file in the registry).
        """
        deps = ctx.deps
        entry = _find_file(deps.file_registry, file_name)
        if not entry:
            available = [e.file_name for e in deps.file_registry]
            return f"File not found: '{file_name}'. Available: {', '.join(available)}"

        cache_key = entry.file_name
        if cache_key in deps._file_cache:
            content = deps._file_cache[cache_key]
        else:
            try:
                local_path = await _download_file(deps, entry)
                file_bytes = Path(local_path).read_bytes()
                content = ParserFactory.parse_file(file_bytes, entry.file_type)
                deps._file_cache[cache_key] = content
            except Exception as e:
                logger.error(f"[RESEARCH] Failed to read {file_name}: {e}")
                return f"Error reading '{file_name}': {e}"

        # Adaptive truncation based on budget (Strategy 2)
        counter = TokenCounter()
        token_count = counter.count_tokens(content, "claude-sonnet-4")
        limit = deps.file_token_limit

        logger.info(
            f"[RESEARCH] Read file: {file_name} "
            f"({len(content)} chars, ~{token_count} tokens, limit: {limit})"
        )

        if token_count > limit:
            ratio = limit / token_count
            truncate_chars = int(len(content) * ratio * 0.95)
            truncated = content[:truncate_chars]
            return (
                f"{truncated}\n\n"
                f"... (truncated: ~{limit} of ~{token_count} tokens)\n"
                f"Use search_file() to find specific sections."
            )

        return content

    @agent.tool
    async def search_file(
        ctx: RunContext[ResearchDeps], file_name: str, query: str
    ) -> str:
        """Search for specific content within a source file.

        Args:
            file_name: Name of the file to search.
            query: Search term or phrase to find in the file.
        """
        deps = ctx.deps
        entry = _find_file(deps.file_registry, file_name)
        if not entry:
            available = [e.file_name for e in deps.file_registry]
            return f"File not found: '{file_name}'. Available: {', '.join(available)}"

        try:
            cache_key = entry.file_name
            if cache_key in deps._file_cache:
                content = deps._file_cache[cache_key]
            else:
                local_path = await _download_file(deps, entry)
                file_bytes = Path(local_path).read_bytes()
                content = ParserFactory.parse_file(file_bytes, entry.file_type)
                deps._file_cache[cache_key] = content

            query_lower = query.lower()
            lines = content.split("\n")
            matches = []
            context_window = 3

            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    start = max(0, i - context_window)
                    end = min(len(lines), i + context_window + 1)
                    match_block = "\n".join(lines[start:end])
                    matches.append(f"[Line {i+1}]:\n{match_block}")

            if not matches:
                return f"No matches for '{query}' in {file_name}."

            result = f"Found {len(matches)} match(es) for '{query}' in {file_name}:\n\n"
            for match in matches[:MAX_SEARCH_MATCHES]:
                result += f"{match}\n---\n"

            if len(matches) > MAX_SEARCH_MATCHES:
                result += f"\n... and {len(matches) - MAX_SEARCH_MATCHES} more matches."

            logger.info(
                f"[RESEARCH] Searched {file_name} for '{query}': "
                f"{len(matches)} matches"
            )
            return result

        except Exception as e:
            logger.error(f"[RESEARCH] Search failed in {file_name}: {e}")
            return f"Error searching '{file_name}': {e}"

    @agent.tool
    async def run_python_code(ctx: RunContext[ResearchDeps], code: str) -> str:
        """Execute Python code for data analysis or calculations.

        Available libraries: pandas, openpyxl, fitz (PyMuPDF), json, csv, math, statistics, re.
        Must print results to stdout.

        Args:
            code: Python code to execute.
        """
        deps = ctx.deps
        logger.info(f"[RESEARCH] Executing Python code ({len(code)} chars)")

        result = await execute_python_code(
            code=code,
            working_dir=deps.temp_dir,
        )

        if result["success"]:
            output = result["output"]
            # Cap output size (Strategy 3)
            if len(output) > MAX_CODE_OUTPUT_CHARS:
                output = (
                    output[:MAX_CODE_OUTPUT_CHARS]
                    + f"\n... (truncated, {len(result['output'])} total chars)"
                )
            return f"Code executed successfully:\n{output}"
        else:
            error_msg = result["error"] or "Unknown error"
            partial = result.get("output", "")
            response = f"Code execution failed:\nError: {error_msg}"
            if partial:
                response += f"\nPartial output: {partial[:1000]}"
            return response

    return agent


async def _run_file_analysis(
    deps: ResearchDeps,
    agent: Agent[ResearchDeps, str],
    file_entry: FileRegistryEntry,
    progress_path: Path,
    analysis_guidance: str,
) -> tuple[int, int]:
    """Analyze a single file and append findings to progress.md.

    Each call to agent.run() starts a fresh conversation — no context
    accumulation from previous files. progress.md provides continuity.

    Returns:
        (estimated_input_tokens, estimated_output_tokens)
    """
    progress_content = _read_progress(progress_path)

    user_message = (
        f"Analyze the file '{file_entry.file_name}' ({file_entry.file_type}).\n\n"
        f"ANALYSIS GUIDANCE:\n{analysis_guidance}\n\n"
        f"ACCUMULATED FINDINGS SO FAR:\n{progress_content}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Read the file using read_file('{file_entry.file_name}')\n"
        f"2. If the file is large or truncated, use search_file() for specific data\n"
        f"3. If data analysis is needed, use run_python_code()\n"
        f"4. Output ONLY your key findings as concise bullet points\n"
        f"5. Include specific numbers, data points, and quotes\n"
        f"6. Do NOT repeat findings already in the accumulated notes above\n"
    )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    async def run_with_retry():
        return await agent.run(user_message, deps=deps)

    result = await run_with_retry()
    findings = result.output

    # Append findings to progress.md
    _append_findings(progress_path, file_entry.file_name, findings)

    # Estimate tokens (conservative approximation)
    counter = TokenCounter()
    est_input = counter.count_tokens(user_message, "claude-sonnet-4") + 3_000  # system prompt overhead
    est_output = counter.count_tokens(findings, "claude-sonnet-4")

    logger.info(
        f"[RESEARCH] File analysis complete: {file_entry.file_name} "
        f"(~{est_input} in, ~{est_output} out, findings: {len(findings)} chars)"
    )

    return est_input, est_output


# ---------------------------------------------------------------------------
# Phase 3: Synthesis (sonnet — quality matters for final output)
# ---------------------------------------------------------------------------

async def _run_synthesis(
    gateway: ModelGateway,
    state: ReportWorkflowState,
    progress_path: Path,
) -> tuple[str, int, int]:
    """Compile progress.md into polished research notes.

    Returns:
        (research_notes, input_tokens, output_tokens)
    """
    config = state["config"]
    progress_content = _read_progress(progress_path)

    system_prompt = (
        "You are a research synthesizer. Compile the accumulated research findings "
        "into well-organized research notes for a report writer.\n\n"
        "OUTPUT FORMAT:\n"
        "## Key Findings\nList the most important discoveries.\n\n"
        "## Detailed Notes\nOrganized by topic/theme with specific data points.\n\n"
        "## Data & Statistics\nNumerical findings, calculations, results.\n\n"
        "## Source References\nWhich files provided which information.\n\n"
        "## Recommendations for Report\nSuggestions for report structure.\n\n"
        "Be thorough but concise. Preserve all specific numbers and evidence. "
        "Do not fabricate — only include what is present in the findings."
    )

    user_message = (
        f"REPORT TITLE: {config.get('title', 'Research Report')}\n"
        f"DETAIL LEVEL: {config.get('detail_level', 'standard')}\n\n"
        f"RESEARCH FINDINGS:\n{progress_content}\n\n"
        f"Synthesize these findings into polished research notes."
    )

    research_notes, usage = await gateway.generate_text(
        task=TaskType.RESEARCH,  # Sonnet for quality
        messages=[{"role": "user", "content": user_message}],
        system_prompt=system_prompt,
        max_tokens=5000,
    )

    logger.info(
        f"[RESEARCH] Synthesis complete: {usage.input_tokens} in, "
        f"{usage.output_tokens} out, notes: {len(research_notes)} chars"
    )

    return research_notes, usage.input_tokens, usage.output_tokens


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def research_agent_node(state: ReportWorkflowState) -> ReportWorkflowState:
    """Multi-run research agent with progress.md for context management.

    Phases:
    1. Planning (haiku): Create analysis strategy → ~3K tokens
    2. File Analysis (sonnet, per-file): Analyze each file → ~10K tokens/file
    3. Synthesis (sonnet): Compile into research notes → ~12K tokens

    The agent:
    1. Reviews available files and user instructions
    2. Plans which files to read and what to look for
    3. Uses tools (read_file, search_file, run_python_code) per-file
    4. Writes findings to progress.md after each file
    5. Synthesizes all findings into research_notes

    Args:
        state: Current workflow state (must have file_registry populated)

    Returns:
        Updated state with research_notes populated
    """
    report_id = state["report_id"]
    started_at = datetime.utcnow()
    file_registry = state.get("file_registry", [])
    budget = state.get("token_budget", TokenBudget())

    logger.info(
        f"[WORKFLOW] Report {report_id} | RESEARCH | "
        f"Starting multi-run research with {len(file_registry)} files "
        f"(budget remaining: {budget.remaining})"
    )

    state = update_progress(
        state,
        WorkflowStep.RESEARCHING,
        15,
        "Research agent analyzing documents...",
    )

    if not file_registry:
        return mark_failed(state, "No files registered for research")

    try:
        # Create gateway for planning and synthesis phases
        gateway_config = GatewayConfig(
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=getattr(settings, "openai_api_key", None),
        )
        gateway = ModelGateway(gateway_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            progress_path = Path(temp_dir) / "progress.md"

            supabase = get_supabase_client()
            supabase.table("reports").update({
                "progress": 18,
            }).eq("id", report_id).execute()

            # === Phase 1: Planning ===
            plan_text, plan_in, plan_out = await _run_planning_phase(
                state, gateway, progress_path,
            )
            budget.record_usage(plan_in, plan_out)

            logger.info(
                f"[RESEARCH] Budget after planning: "
                f"used={budget.cumulative_used}, remaining={budget.remaining}"
            )

            state = update_progress(
                state,
                WorkflowStep.RESEARCHING,
                20,
                "Analysis plan created, reading files...",
            )

            # === Phase 2: Per-file analysis ===
            loaded_skills = state.get("loaded_skills", [])
            skill_context = _format_loaded_skills(loaded_skills)

            file_analysis_system = (
                "You are a research analyst. Your task is to analyze a single file "
                "and extract key findings.\n\n"
                "Focus on:\n"
                "- Specific numbers, metrics, and data points\n"
                "- Key conclusions and insights\n"
                "- Notable patterns or anomalies\n"
                "- Relevant quotes or statements\n\n"
                "Output ONLY concise bullet points of findings. "
                "Do NOT include raw data dumps or reproduce file content verbatim.\n"
                "Keep findings under 800 words.\n\n"
                f"{skill_context}"
            )

            # Adaptive file token limit based on budget (Strategy 2)
            file_token_limit = budget.get_file_token_limit(len(file_registry))
            logger.info(
                f"[RESEARCH] Adaptive file token limit: {file_token_limit} "
                f"(for {len(file_registry)} files, budget remaining: {budget.remaining})"
            )

            agent = _create_file_analysis_agent(file_analysis_system)

            deps = ResearchDeps(
                report_id=report_id,
                user_id=state["user_id"],
                file_registry=file_registry,
                upload_bucket=settings.upload_bucket,
                temp_dir=temp_dir,
                file_token_limit=file_token_limit,
            )

            total_file_in = 0
            total_file_out = 0

            for i, entry in enumerate(file_registry):
                progress_pct = 20 + int((i / len(file_registry)) * 25)
                state = update_progress(
                    state,
                    WorkflowStep.RESEARCHING,
                    progress_pct,
                    f"Analyzing {entry.file_name} ({i+1}/{len(file_registry)})...",
                )

                supabase.table("reports").update({
                    "progress": progress_pct,
                }).eq("id", report_id).execute()

                try:
                    est_in, est_out = await _run_file_analysis(
                        deps, agent, entry, progress_path, plan_text,
                    )
                    budget.record_usage(est_in, est_out)
                    total_file_in += est_in
                    total_file_out += est_out

                    logger.info(
                        f"[RESEARCH] Budget after {entry.file_name}: "
                        f"used={budget.cumulative_used}, remaining={budget.remaining}"
                    )

                    # Safety valve: stop if budget is too tight for synthesis + report
                    if not budget.can_afford(30_000):
                        logger.warning(
                            f"[RESEARCH] Budget tight ({budget.remaining} remaining), "
                            f"skipping remaining {len(file_registry) - i - 1} files"
                        )
                        _append_findings(
                            progress_path, "(budget limit)",
                            f"Skipped files due to token budget: "
                            f"{', '.join(e.file_name for e in file_registry[i+1:])}"
                        )
                        break

                except Exception as e:
                    error_str = str(e).lower()
                    if "rate" in error_str and "limit" in error_str:
                        logger.error(
                            f"[RESEARCH] Rate limit on {entry.file_name}: {e}"
                        )
                        return mark_failed(state, f"Rate limit exceeded: {str(e)}")

                    logger.error(
                        f"[RESEARCH] Failed to analyze {entry.file_name}: {e}"
                    )
                    _append_findings(
                        progress_path, entry.file_name,
                        f"(analysis failed: {str(e)[:200]})",
                    )

            # === Phase 3: Synthesis ===
            state = update_progress(
                state,
                WorkflowStep.RESEARCHING,
                45,
                "Synthesizing research findings...",
            )

            supabase.table("reports").update({
                "progress": 45,
            }).eq("id", report_id).execute()

            research_notes, synth_in, synth_out = await _run_synthesis(
                gateway, state, progress_path,
            )
            budget.record_usage(synth_in, synth_out)

            logger.info(
                f"[WORKFLOW] Report {report_id} | RESEARCH | "
                f"Complete. Notes: {len(research_notes)} chars, "
                f"budget used: {budget.cumulative_used}/{budget.max_cumulative}"
            )

        # Update state
        state = {
            **state,
            "research_notes": research_notes,
            "token_budget": budget,
        }

        # Track total token usage for the research phase
        total_in = plan_in + total_file_in + synth_in
        total_out = plan_out + total_file_out + synth_out
        state = update_token_metrics(state, total_in, total_out)

        # Update progress in database
        supabase.table("reports").update({
            "progress": 50,
        }).eq("id", report_id).execute()

        state = mark_step_complete(state, WorkflowStep.RESEARCHING, started_at)
        return update_progress(
            state, WorkflowStep.RESEARCHING, 50, "Research complete"
        )

    except Exception as e:
        logger.error(f"[WORKFLOW] Report {report_id} | RESEARCH | Error: {e}")
        return mark_failed(state, f"Research agent failed: {str(e)}")
