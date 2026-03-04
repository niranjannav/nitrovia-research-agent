"""Analytics report workflow.

A linear async pipeline that generates an analytics report from accumulated
structured data. Simpler than the research workflow — no document parsing,
no RAG, no agent. Steps:

1. Fetch records from DB for the requested period
2. Calculate all time-based metrics (WoW, MoM, QoQ, YTD, etc.)
3. Build monthly trend series for line charts
4. Generate charts (base64 PNGs)
5. Call Claude with structured metrics → narrative report
6. Render PDF / PPTX / DOCX
7. Upload output files and mark report complete

Progress is written to the reports table so the existing frontend polling
(GET /reports/{id}/status) works without any changes.
"""

import json
import logging
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from app.llm.config import TaskType
from app.llm.gateway import create_gateway_from_settings
from app.models.schemas import GeneratedReport, ReportSection
from app.services.analytics_data_service import AnalyticsDataService
from app.services.chart_generator import generate_sales_charts, line_trend
from app.services.metrics_calculator import compute_sales_metrics
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent.parent / "prompts"


async def run_analytics_workflow(
    report_id: str,
    user_id: str,
    domain: str,
    as_of: date,
    report_period: str,
    output_formats: list[str],
    primary_metric: str,
    custom_instructions: str | None,
) -> None:
    """Entry point for the analytics report background task."""
    logger.info(
        f"[ANALYTICS] Starting workflow | report_id={report_id} | "
        f"domain={domain} | as_of={as_of} | metric={primary_metric}"
    )

    try:
        await _run(
            report_id=report_id,
            user_id=user_id,
            domain=domain,
            as_of=as_of,
            report_period=report_period,
            output_formats=output_formats,
            primary_metric=primary_metric,
            custom_instructions=custom_instructions,
        )
    except Exception as e:
        logger.error(f"[ANALYTICS] Workflow failed: {e}", exc_info=True)
        _set_report_status(report_id, "failed", progress=0, message=str(e)[:300])


async def _run(
    report_id: str,
    user_id: str,
    domain: str,
    as_of: date,
    report_period: str,
    output_formats: list[str],
    primary_metric: str,
    custom_instructions: str | None,
) -> None:
    supabase = get_supabase_client()
    data_service = AnalyticsDataService()

    # ── Step 1: Fetch data ────────────────────────────────────────────────
    _set_report_status(report_id, "processing", progress=5, message="Fetching analytics data…")

    records = data_service.query_all_for_metrics(
        user_id=user_id,
        domain=domain,
        as_of=as_of,
        lookback_years=2,
    )

    if not records:
        raise ValueError(
            f"No data found for domain '{domain}' up to {as_of}. "
            "Please upload data first via POST /analytics/upload."
        )

    logger.info(f"[ANALYTICS] Fetched {len(records)} records for domain={domain}")
    _set_report_status(report_id, "processing", progress=15, message="Calculating metrics…")

    # ── Step 2: Calculate metrics ─────────────────────────────────────────
    if domain == "sales":
        metrics = compute_sales_metrics(records, as_of, primary_metric)
        metrics_dict = metrics.to_dict()
    elif domain == "finance":
        from app.services.finance_metrics_calculator import compute_finance_metrics
        # Use records fetched in Step 1 (already from finance_records table)
        finance_metrics = compute_finance_metrics(records, as_of)
        metrics_dict = finance_metrics.to_dict()
    else:
        # Generic placeholder for future domains
        metrics_dict = {"domain": domain, "as_of": as_of.isoformat(), "records_count": len(records)}

    _set_report_status(report_id, "processing", progress=30, message="Building trend series…")

    # ── Step 3: Monthly trend series (for line charts) ────────────────────
    if domain == "finance":
        # Build finance trend from queried finance records
        from datetime import timedelta as _td
        start_date = as_of.replace(year=as_of.year - 2, month=1, day=1)
        finance_trend_rows = data_service.query_finance(user_id, start_date, as_of)
        monthly_finance: dict[str, float] = {}
        for row in finance_trend_rows:
            d = row.get("record_date")
            if isinstance(d, str):
                try:
                    from datetime import date as _d
                    d = _d.fromisoformat(d)
                except ValueError:
                    continue
            if d:
                key = d.strftime("%Y-%m")
                monthly_finance[key] = monthly_finance.get(key, 0) + float(row.get("revenue") or 0)
        trend_dates = sorted(monthly_finance.keys())
        trend_values = [monthly_finance[k] for k in trend_dates]
    else:
        trend = data_service.get_monthly_trend(
            user_id=user_id,
            domain=domain,
            metric=primary_metric,
            months=24,
            as_of=as_of,
        )
        trend_dates = [t["month"] for t in trend]
        trend_values = [t["value"] for t in trend]

    _set_report_status(report_id, "processing", progress=40, message="Generating charts…")

    # ── Step 4: Generate charts ───────────────────────────────────────────
    charts: dict[str, str] = {}

    if domain == "sales":
        try:
            charts = generate_sales_charts(metrics_dict)
        except Exception as e:
            logger.warning(f"[ANALYTICS] Chart generation partially failed: {e}")

        # Monthly trend line chart
        if trend_dates and trend_values:
            try:
                charts["revenue_trend"] = line_trend(
                    dates=trend_dates,
                    series={primary_metric.replace("_", " ").title(): trend_values},
                    title=f"{primary_metric.replace('_', ' ').title()} Trend — Last 24 Months",
                )
            except Exception as e:
                logger.warning(f"[ANALYTICS] Trend chart failed: {e}")

    elif domain == "finance":
        from app.services.chart_generator import generate_finance_charts
        try:
            charts = generate_finance_charts(metrics_dict, trend_dates, trend_values)
        except Exception as e:
            logger.warning(f"[ANALYTICS] Finance chart generation failed: {e}")

    _set_report_status(report_id, "processing", progress=55, message="Generating report narrative…")

    # ── Step 5: Generate report narrative with Claude ────────────────────
    generated_report = await _generate_narrative(
        domain=domain,
        metrics_dict=metrics_dict,
        primary_metric=primary_metric,
        as_of=as_of,
        report_period=report_period,
        custom_instructions=custom_instructions,
        chart_names=list(charts.keys()),
    )

    _set_report_status(report_id, "processing", progress=75, message="Rendering report files…")

    # ── Step 6: Render outputs ────────────────────────────────────────────
    output_files = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Write chart images to temp dir for renderer access
        chart_paths: dict[str, str] = {}
        for chart_name, b64_png in charts.items():
            import base64
            chart_file = tmp_path / f"{chart_name}.png"
            chart_file.write_bytes(base64.b64decode(b64_png))
            chart_paths[chart_name] = str(chart_file)

        for fmt in output_formats:
            try:
                file_path = await _render_output(
                    fmt=fmt,
                    generated_report=generated_report,
                    chart_paths=chart_paths,
                    tmp_path=tmp_path,
                    domain=domain,
                )
                if file_path:
                    # Upload to Supabase Storage
                    storage_path = f"generated-reports/{user_id}/{report_id}/{domain}_analytics.{fmt}"
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()

                    mime = {
                        "pdf": "application/pdf",
                        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    }.get(fmt, "application/octet-stream")

                    supabase.storage.from_("generated-reports").upload(
                        path=storage_path,
                        file=file_bytes,
                        file_options={"content-type": mime},
                    )

                    signed = supabase.storage.from_("generated-reports").create_signed_url(
                        path=storage_path,
                        expires_in=86400 * 7,
                    )
                    download_url = signed.get("signedURL", "")

                    output_files.append({
                        "format": fmt,
                        "storage_path": storage_path,
                        "download_url": download_url,
                    })

            except Exception as e:
                logger.error(f"[ANALYTICS] Render failed for format={fmt}: {e}")

    # ── Step 7: Finalise report ───────────────────────────────────────────
    _set_report_status(report_id, "processing", progress=95, message="Finalising…")

    report_content = generated_report.model_dump(mode="json")
    report_content["analytics_metrics"] = metrics_dict

    supabase.table("reports").update({
        "status": "completed",
        "progress": 100,
        "current_step": "completed",
        "generated_content": report_content,
        "output_files": output_files,
    }).eq("id", report_id).execute()

    logger.info(
        f"[ANALYTICS] Workflow complete | report_id={report_id} | "
        f"files={len(output_files)}"
    )


# ── Report narrative generation ───────────────────────────────────────────────

async def _generate_narrative(
    domain: str,
    metrics_dict: dict,
    primary_metric: str,
    as_of: date,
    report_period: str,
    custom_instructions: str | None,
    chart_names: list[str],
) -> GeneratedReport:
    """Call Claude with structured metrics to produce an analytical narrative."""

    prompt_file = _PROMPT_DIR / f"{domain}_analytics.txt"
    if prompt_file.exists():
        prompt_template = prompt_file.read_text(encoding="utf-8")
    else:
        prompt_template = _FALLBACK_PROMPT

    metrics_json = json.dumps(metrics_dict, indent=2, default=str)
    if len(metrics_json) > 60_000:
        metrics_json = metrics_json[:60_000] + "\n... (truncated)"

    prompt = prompt_template.format(
        domain=domain,
        primary_metric=primary_metric,
        as_of_date=as_of.isoformat(),
        report_period=report_period,
        metrics_json=metrics_json,
        chart_names=", ".join(chart_names),
        custom_instructions=custom_instructions or "No additional instructions.",
    )

    gateway = create_gateway_from_settings()

    report, usage = await gateway.generate_structured(
        task=TaskType.REPORT_GENERATION,
        output_schema=GeneratedReport,
        messages=[{"role": "user", "content": prompt}],
        system_prompt=(
            "You are an expert business analyst specialising in dairy industry analytics. "
            "Produce precise, actionable analytical reports with clear data references. "
            "All numbers must match the provided metrics JSON exactly."
        ),
        temperature=0.3,
        max_tokens=8000,
    )

    logger.info(
        f"[ANALYTICS] Narrative generated | domain={domain} | "
        f"tokens={usage.total_tokens}"
    )
    return report


# ── Rendering ─────────────────────────────────────────────────────────────────

async def _render_output(
    fmt: str,
    generated_report: GeneratedReport,
    chart_paths: dict[str, str],
    tmp_path: Path,
    domain: str,
) -> str | None:
    """Render the report to a file and return the file path."""
    output_file = tmp_path / f"analytics_report.{fmt}"

    try:
        if fmt == "pdf":
            from app.services.analytics_renderer import AnalyticsPDFRenderer
            renderer = AnalyticsPDFRenderer()
            pdf_bytes = renderer.render(generated_report, chart_paths=chart_paths)
            output_file.write_bytes(pdf_bytes.read())

        elif fmt == "docx":
            from app.services.docx_renderer import DocxRenderer
            renderer = DocxRenderer()
            docx_bytes = renderer.render(generated_report)
            output_file.write_bytes(docx_bytes.read())

        elif fmt == "pptx":
            from app.services.analytics_renderer import AnalyticsPPTXRenderer
            renderer = AnalyticsPPTXRenderer()
            pptx_bytes = renderer.render(generated_report, chart_paths=chart_paths)
            output_file.write_bytes(pptx_bytes.read())

        else:
            logger.warning(f"Unknown output format: {fmt}")
            return None

        return str(output_file)

    except Exception as e:
        logger.error(f"[ANALYTICS] Render error for {fmt}: {e}", exc_info=True)
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_report_status(
    report_id: str,
    status: str,
    progress: int,
    message: str,
) -> None:
    supabase = get_supabase_client()
    try:
        supabase.table("reports").update({
            "status": status,
            "progress": progress,
            "current_step": message,
        }).eq("id", report_id).execute()
    except Exception as e:
        logger.warning(f"Failed to update report status: {e}")


_FALLBACK_PROMPT = """
You are an expert business analyst. Generate a comprehensive {domain} analytics report.

Report period: {report_period} ending {as_of_date}
Primary metric: {primary_metric}

Structured metrics (JSON):
{metrics_json}

Charts available: {chart_names}

Additional instructions: {custom_instructions}

Produce a report with:
1. Executive summary (key highlights, top 3 insights)
2. Time comparison analysis (WoW, MoM, QoQ where available)
3. Channel/team/product breakdown analysis
4. Trend analysis
5. Specific, actionable recommendations (at least 5)

Reference exact numbers from the metrics JSON. Be precise and business-focused.
"""
