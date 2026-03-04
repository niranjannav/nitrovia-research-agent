"""Metrics calculator for analytics reports.

All functions are pure (no side effects, no DB calls). Input is a list of
AnalyticsRecord objects. Output is structured comparison objects used by
the LangGraph workflow and passed as context to Claude for report generation.

Supports all required time comparisons:
  - WoW   : This week vs previous week
  - SWLM  : Same week last month
  - MTD   : Month-to-date vs same period last month
  - MoM   : This full month vs previous full month
  - SMLY  : Same month last year
  - YTD   : Year-to-date vs same period last year
  - QoQ   : This quarter vs previous quarter
  - SQLY  : Same quarter last year
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class ComparisonResult:
    """Result of a single time-based comparison."""
    label: str               # e.g. "This Week vs Previous Week"
    period: str              # e.g. "2025-W04"
    current: float
    previous: float
    change_abs: float        # current - previous
    change_pct: float        # percentage change (None-safe)
    direction: str           # 'up' | 'down' | 'flat'

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "period": self.period,
            "current": round(self.current, 2),
            "previous": round(self.previous, 2),
            "change_abs": round(self.change_abs, 2),
            "change_pct": round(self.change_pct, 1),
            "direction": self.direction,
        }


@dataclass
class BreakdownItem:
    """One item in a dimensional breakdown (channel, product, team, etc.)."""
    label: str
    current: float
    previous: float
    change_pct: float
    direction: str
    share_pct: float = 0.0   # share of total for current period


@dataclass
class BreakdownResult:
    """Dimensional breakdown for a given period."""
    dimension: str           # e.g. "channel", "salesperson", "product_code"
    metric: str              # e.g. "revenue", "quantity_litres"
    period_label: str
    items: list[BreakdownItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "metric": self.metric,
            "period_label": self.period_label,
            "items": [
                {
                    "label": i.label,
                    "current": round(i.current, 2),
                    "previous": round(i.previous, 2),
                    "change_pct": round(i.change_pct, 1),
                    "direction": i.direction,
                    "share_pct": round(i.share_pct, 1),
                }
                for i in sorted(self.items, key=lambda x: x.current, reverse=True)
            ],
        }


@dataclass
class TopNResult:
    """Top-N ranked items by a metric."""
    metric: str
    direction: str           # 'top' or 'bottom'
    period_label: str
    items: list[dict] = field(default_factory=list)  # {label, value, rank}


@dataclass
class SalesMetrics:
    """All computed metrics for a Sales analytics report."""

    as_of_date: date
    primary_metric: str      # 'revenue' or 'quantity_litres'

    # Time comparisons (each is a ComparisonResult)
    wow: ComparisonResult | None = None
    swlm: ComparisonResult | None = None
    mtd_vs_smtd: ComparisonResult | None = None
    mom: ComparisonResult | None = None
    smly: ComparisonResult | None = None
    ytd_vs_stly: ComparisonResult | None = None
    qoq: ComparisonResult | None = None
    sqly: ComparisonResult | None = None

    # Channel breakdown
    channel_breakdown: BreakdownResult | None = None

    # Team performance
    team_breakdown: BreakdownResult | None = None

    # Top products
    top_products: TopNResult | None = None
    bottom_products: TopNResult | None = None

    # Growers and decliners (vs same period last month)
    growing_products: list[BreakdownItem] = field(default_factory=list)
    declining_products: list[BreakdownItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _comp(c: ComparisonResult | None) -> dict | None:
            return c.to_dict() if c else None

        return {
            "as_of_date": self.as_of_date.isoformat(),
            "primary_metric": self.primary_metric,
            "time_comparisons": {
                "wow": _comp(self.wow),
                "swlm": _comp(self.swlm),
                "mtd_vs_smtd": _comp(self.mtd_vs_smtd),
                "mom": _comp(self.mom),
                "smly": _comp(self.smly),
                "ytd_vs_stly": _comp(self.ytd_vs_stly),
                "qoq": _comp(self.qoq),
                "sqly": _comp(self.sqly),
            },
            "channel_breakdown": self.channel_breakdown.to_dict() if self.channel_breakdown else None,
            "team_breakdown": self.team_breakdown.to_dict() if self.team_breakdown else None,
            "top_products": self.top_products.__dict__ if self.top_products else None,
            "bottom_products": self.bottom_products.__dict__ if self.bottom_products else None,
            "growing_products": [
                {"label": i.label, "change_pct": round(i.change_pct, 1), "current": round(i.current, 2)}
                for i in sorted(self.growing_products, key=lambda x: x.change_pct, reverse=True)[:10]
            ],
            "declining_products": [
                {"label": i.label, "change_pct": round(i.change_pct, 1), "current": round(i.current, 2)}
                for i in sorted(self.declining_products, key=lambda x: x.change_pct)[:10]
            ],
        }


# ── Core metric accessor ─────────────────────────────────────────────────────

def _get_metric(record, metric: str) -> float:
    """Safely get a numeric metric from a record dict or AnalyticsRecord."""
    if isinstance(record, dict):
        val = record.get(metric, 0) or 0
    else:
        val = getattr(record, metric, None) or 0
    return float(val)


def _sum_metric(records: list, metric: str) -> float:
    return sum(_get_metric(r, metric) for r in records)


def _make_comparison(
    label: str,
    period: str,
    current: float,
    previous: float,
) -> ComparisonResult:
    change_abs = current - previous
    if previous == 0:
        change_pct = 100.0 if current > 0 else 0.0
    else:
        change_pct = (change_abs / abs(previous)) * 100

    direction = "up" if change_abs > 0 else ("down" if change_abs < 0 else "flat")
    return ComparisonResult(
        label=label,
        period=period,
        current=current,
        previous=previous,
        change_abs=change_abs,
        change_pct=change_pct,
        direction=direction,
    )


# ── Date helpers ─────────────────────────────────────────────────────────────

def _week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _quarter_start(d: date) -> date:
    q_month = ((d.month - 1) // 3) * 3 + 1
    return d.replace(month=q_month, day=1)


def _year_start(d: date) -> date:
    return d.replace(month=1, day=1)


def _filter_between(records: list, start: date, end: date) -> list:
    """Filter records to those with record_date in [start, end)."""
    return [
        r for r in records
        if start <= _record_date(r) < end
    ]


def _record_date(r) -> date:
    if isinstance(r, dict):
        d = r.get("record_date")
        return d if isinstance(d, date) else date.fromisoformat(str(d))
    return r.record_date


# ── Public comparison functions ──────────────────────────────────────────────

def calculate_wow(records: list, metric: str, as_of: date) -> ComparisonResult:
    """This week vs previous week."""
    this_start = _week_start(as_of)
    prev_start = this_start - timedelta(weeks=1)

    current = _sum_metric(_filter_between(records, this_start, this_start + timedelta(weeks=1)), metric)
    previous = _sum_metric(_filter_between(records, prev_start, prev_start + timedelta(weeks=1)), metric)

    return _make_comparison(
        label="This Week vs Previous Week",
        period=f"{this_start.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_swlm(records: list, metric: str, as_of: date) -> ComparisonResult:
    """Same week last month."""
    this_start = _week_start(as_of)
    week_of_month = (as_of.day - 1) // 7  # 0-based week index within month

    # Same week number in the previous month
    prev_month_first = (_month_start(as_of).replace(day=1) - timedelta(days=1)).replace(day=1)
    swlm_start = prev_month_first + timedelta(weeks=week_of_month)
    swlm_start = _week_start(swlm_start)

    current = _sum_metric(_filter_between(records, this_start, this_start + timedelta(weeks=1)), metric)
    previous = _sum_metric(_filter_between(records, swlm_start, swlm_start + timedelta(weeks=1)), metric)

    return _make_comparison(
        label="This Week vs Same Week Last Month",
        period=f"{this_start.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_mtd_vs_smtd(records: list, metric: str, as_of: date) -> ComparisonResult:
    """Month-to-date vs same period (days 1–N) last month."""
    month_start = _month_start(as_of)
    day_of_month = as_of.day

    # Same number of days into last month
    prev_month = (month_start - timedelta(days=1)).replace(day=1)
    prev_end = prev_month.replace(day=min(day_of_month, _days_in_month(prev_month)))

    current = _sum_metric(_filter_between(records, month_start, as_of + timedelta(days=1)), metric)
    previous = _sum_metric(_filter_between(records, prev_month, prev_end + timedelta(days=1)), metric)

    return _make_comparison(
        label=f"MTD (Day 1–{day_of_month}) vs Same Period Last Month",
        period=f"{month_start.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_mom(records: list, metric: str, as_of: date) -> ComparisonResult:
    """This full month vs previous full month."""
    this_month = _month_start(as_of)
    prev_month = (this_month - timedelta(days=1)).replace(day=1)

    current = _sum_metric(_filter_between(records, this_month, (this_month.replace(month=this_month.month % 12 + 1) if this_month.month < 12 else this_month.replace(year=this_month.year + 1, month=1))), metric)
    prev_next = (prev_month.replace(month=prev_month.month % 12 + 1) if prev_month.month < 12 else prev_month.replace(year=prev_month.year + 1, month=1))
    previous = _sum_metric(_filter_between(records, prev_month, prev_next), metric)

    return _make_comparison(
        label=f"{this_month.strftime('%B %Y')} vs {prev_month.strftime('%B %Y')}",
        period=f"{this_month.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_smly(records: list, metric: str, as_of: date) -> ComparisonResult:
    """Same month last year."""
    this_month = _month_start(as_of)
    smly = this_month.replace(year=this_month.year - 1)

    this_next = _next_month(this_month)
    smly_next = _next_month(smly)

    current = _sum_metric(_filter_between(records, this_month, this_next), metric)
    previous = _sum_metric(_filter_between(records, smly, smly_next), metric)

    return _make_comparison(
        label=f"{this_month.strftime('%B %Y')} vs {smly.strftime('%B %Y')}",
        period=f"{this_month.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_ytd_vs_stly(records: list, metric: str, as_of: date) -> ComparisonResult:
    """Year-to-date vs same period last year."""
    year_start = _year_start(as_of)
    stly_start = year_start.replace(year=year_start.year - 1)
    stly_end = as_of.replace(year=as_of.year - 1) + timedelta(days=1)

    current = _sum_metric(_filter_between(records, year_start, as_of + timedelta(days=1)), metric)
    previous = _sum_metric(_filter_between(records, stly_start, stly_end), metric)

    return _make_comparison(
        label=f"YTD {as_of.year} vs Same Period {as_of.year - 1}",
        period=f"{year_start.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_qoq(records: list, metric: str, as_of: date) -> ComparisonResult:
    """This quarter vs previous quarter."""
    q_start = _quarter_start(as_of)
    prev_q_end = q_start - timedelta(days=1)
    prev_q_start = _quarter_start(prev_q_end)

    current = _sum_metric(_filter_between(records, q_start, _next_quarter(q_start)), metric)
    previous = _sum_metric(_filter_between(records, prev_q_start, q_start), metric)

    q_num = (q_start.month - 1) // 3 + 1
    prev_q_num = (prev_q_start.month - 1) // 3 + 1

    return _make_comparison(
        label=f"Q{q_num} {q_start.year} vs Q{prev_q_num} {prev_q_start.year}",
        period=f"{q_start.isoformat()}",
        current=current,
        previous=previous,
    )


def calculate_sqly(records: list, metric: str, as_of: date) -> ComparisonResult:
    """Same quarter last year."""
    q_start = _quarter_start(as_of)
    sqly_start = q_start.replace(year=q_start.year - 1)

    current = _sum_metric(_filter_between(records, q_start, _next_quarter(q_start)), metric)
    previous = _sum_metric(_filter_between(records, sqly_start, _next_quarter(sqly_start)), metric)

    q_num = (q_start.month - 1) // 3 + 1
    return _make_comparison(
        label=f"Q{q_num} {q_start.year} vs Q{q_num} {q_start.year - 1}",
        period=f"{q_start.isoformat()}",
        current=current,
        previous=previous,
    )


# ── Breakdown functions ──────────────────────────────────────────────────────

def breakdown_by(
    records: list,
    metric: str,
    dimension: str,
    current_start: date,
    current_end: date,
    previous_start: date,
    previous_end: date,
    period_label: str = "",
) -> BreakdownResult:
    """Compute a dimensional breakdown and compare current vs previous period."""
    current_records = _filter_between(records, current_start, current_end)
    previous_records = _filter_between(records, previous_start, previous_end)

    def group_by_dim(recs: list) -> dict[str, float]:
        groups: dict[str, float] = {}
        for r in recs:
            key = (str(getattr(r, dimension, None) or r.get(dimension, "Unknown")) if isinstance(r, dict) else str(getattr(r, dimension, None) or "Unknown")).strip() or "Unknown"
            groups[key] = groups.get(key, 0) + _get_metric(r, metric)
        return groups

    current_groups = group_by_dim(current_records)
    previous_groups = group_by_dim(previous_records)
    total_current = sum(current_groups.values()) or 1

    # Union of all keys
    all_keys = set(current_groups) | set(previous_groups)
    items: list[BreakdownItem] = []

    for key in all_keys:
        cur = current_groups.get(key, 0)
        prev = previous_groups.get(key, 0)
        if prev == 0:
            pct = 100.0 if cur > 0 else 0.0
        else:
            pct = ((cur - prev) / abs(prev)) * 100
        direction = "up" if cur > prev else ("down" if cur < prev else "flat")
        items.append(BreakdownItem(
            label=key,
            current=cur,
            previous=prev,
            change_pct=pct,
            direction=direction,
            share_pct=(cur / total_current) * 100,
        ))

    return BreakdownResult(
        dimension=dimension,
        metric=metric,
        period_label=period_label,
        items=items,
    )


def top_n(
    records: list,
    metric: str,
    dimension: str,
    n: int,
    period_start: date,
    period_end: date,
    direction: str = "top",
    period_label: str = "",
) -> TopNResult:
    """Return the top or bottom N items by metric within a period."""
    period_records = _filter_between(records, period_start, period_end)

    groups: dict[str, float] = {}
    for r in period_records:
        key = str(getattr(r, dimension, None) or "Unknown") if not isinstance(r, dict) else str(r.get(dimension, "Unknown"))
        groups[key] = groups.get(key, 0) + _get_metric(r, metric)

    sorted_items = sorted(
        groups.items(),
        key=lambda x: x[1],
        reverse=(direction == "top"),
    )[:n]

    return TopNResult(
        metric=metric,
        direction=direction,
        period_label=period_label,
        items=[
            {"rank": i + 1, "label": label, "value": round(value, 2)}
            for i, (label, value) in enumerate(sorted_items)
        ],
    )


# ── High-level Sales metrics builder ────────────────────────────────────────

def compute_sales_metrics(
    records: list,
    as_of: date,
    primary_metric: str = "revenue",
) -> SalesMetrics:
    """Compute the full set of Sales analytics metrics.

    Args:
        records: All accumulated AnalyticsRecord objects for this user
        as_of: The reference date (usually today or end of reporting period)
        primary_metric: 'revenue' or 'quantity_litres'

    Returns:
        SalesMetrics with all comparisons populated
    """
    m = primary_metric
    metrics = SalesMetrics(as_of_date=as_of, primary_metric=m)

    # Time comparisons
    try:
        metrics.wow = calculate_wow(records, m, as_of)
    except Exception as e:
        logger.warning(f"WoW calculation failed: {e}")

    try:
        metrics.swlm = calculate_swlm(records, m, as_of)
    except Exception as e:
        logger.warning(f"SWLM calculation failed: {e}")

    try:
        metrics.mtd_vs_smtd = calculate_mtd_vs_smtd(records, m, as_of)
    except Exception as e:
        logger.warning(f"MTD calculation failed: {e}")

    try:
        metrics.mom = calculate_mom(records, m, as_of)
    except Exception as e:
        logger.warning(f"MoM calculation failed: {e}")

    try:
        metrics.smly = calculate_smly(records, m, as_of)
    except Exception as e:
        logger.warning(f"SMLY calculation failed: {e}")

    try:
        metrics.ytd_vs_stly = calculate_ytd_vs_stly(records, m, as_of)
    except Exception as e:
        logger.warning(f"YTD calculation failed: {e}")

    try:
        metrics.qoq = calculate_qoq(records, m, as_of)
    except Exception as e:
        logger.warning(f"QoQ calculation failed: {e}")

    try:
        metrics.sqly = calculate_sqly(records, m, as_of)
    except Exception as e:
        logger.warning(f"SQLY calculation failed: {e}")

    # Breakdown periods: this month vs previous month
    this_month = _month_start(as_of)
    prev_month = (this_month - timedelta(days=1)).replace(day=1)
    this_month_end = _next_month(this_month)
    prev_month_end = _next_month(prev_month)

    try:
        metrics.channel_breakdown = breakdown_by(
            records, m, "channel",
            current_start=this_month, current_end=this_month_end,
            previous_start=prev_month, previous_end=prev_month_end,
            period_label=f"{this_month.strftime('%B %Y')} vs {prev_month.strftime('%B %Y')}",
        )
    except Exception as e:
        logger.warning(f"Channel breakdown failed: {e}")

    try:
        metrics.team_breakdown = breakdown_by(
            records, m, "salesperson",
            current_start=this_month, current_end=this_month_end,
            previous_start=prev_month, previous_end=prev_month_end,
            period_label=f"{this_month.strftime('%B %Y')} vs {prev_month.strftime('%B %Y')}",
        )
    except Exception as e:
        logger.warning(f"Team breakdown failed: {e}")

    try:
        metrics.top_products = top_n(
            records, m, "product_name", 10,
            period_start=this_month, period_end=this_month_end,
            direction="top",
            period_label=this_month.strftime("%B %Y"),
        )
    except Exception as e:
        logger.warning(f"Top products failed: {e}")

    try:
        metrics.bottom_products = top_n(
            records, m, "product_name", 10,
            period_start=this_month, period_end=this_month_end,
            direction="bottom",
            period_label=this_month.strftime("%B %Y"),
        )
    except Exception as e:
        logger.warning(f"Bottom products failed: {e}")

    # Growing vs declining products (MoM)
    try:
        product_bd = breakdown_by(
            records, m, "product_name",
            current_start=this_month, current_end=this_month_end,
            previous_start=prev_month, previous_end=prev_month_end,
        )
        metrics.growing_products = [i for i in product_bd.items if i.direction == "up"]
        metrics.declining_products = [i for i in product_bd.items if i.direction == "down"]
    except Exception as e:
        logger.warning(f"Product growth/decline analysis failed: {e}")

    return metrics


# ── Internal date utils ──────────────────────────────────────────────────────

def _next_month(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


def _next_quarter(d: date) -> date:
    q_month = d.month + 3
    if q_month > 12:
        return d.replace(year=d.year + 1, month=q_month - 12, day=1)
    return d.replace(month=q_month, day=1)


def _days_in_month(d: date) -> int:
    return (_next_month(d) - timedelta(days=1)).day
