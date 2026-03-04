"""Finance metrics calculator.

Mirrors the pattern of metrics_calculator.py — pure functions, no DB calls.
Computes MoM and YTD comparisons for key P&L, balance sheet and cash flow KPIs.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from app.services.metrics_calculator import ComparisonResult

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class FinanceMetrics:
    """All computed finance metrics for a reporting period."""

    as_of_date: date

    # P&L comparisons (MoM + YTD vs STLY)
    revenue: ComparisonResult | None
    gross_profit_pct: ComparisonResult | None
    ebitda: ComparisonResult | None
    operating_profit: ComparisonResult | None
    net_income: ComparisonResult | None
    operating_cash_flow: ComparisonResult | None

    # Point-in-time balance sheet (latest record)
    total_assets: float
    total_liabilities: float
    total_equity: float
    debt_to_equity: float

    # Volume KPIs
    litres_sold: ComparisonResult | None
    revenue_per_litre: float | None

    record_count: int

    def to_dict(self) -> dict:
        def _cr(cr: ComparisonResult | None) -> dict | None:
            return cr.to_dict() if cr else None

        return {
            "as_of_date": self.as_of_date.isoformat(),
            "revenue": _cr(self.revenue),
            "gross_profit_pct": _cr(self.gross_profit_pct),
            "ebitda": _cr(self.ebitda),
            "operating_profit": _cr(self.operating_profit),
            "net_income": _cr(self.net_income),
            "operating_cash_flow": _cr(self.operating_cash_flow),
            "total_assets": round(self.total_assets, 2),
            "total_liabilities": round(self.total_liabilities, 2),
            "total_equity": round(self.total_equity, 2),
            "debt_to_equity": round(self.debt_to_equity, 4),
            "litres_sold": _cr(self.litres_sold),
            "revenue_per_litre": (
                round(self.revenue_per_litre, 4) if self.revenue_per_litre else None
            ),
            "record_count": self.record_count,
        }


# ── Public entry point ────────────────────────────────────────────────────────

def compute_finance_metrics(
    records: list[dict],
    as_of: date,
) -> FinanceMetrics:
    """Compute FinanceMetrics from a list of finance_records dicts.

    Args:
        records: Rows from finance_records table (each has record_date + metric cols)
        as_of: The reference date for the report (usually today or end of last month)

    Returns:
        FinanceMetrics dataclass
    """
    if not records:
        return _empty_metrics(as_of)

    # Normalise record_date to date objects
    parsed: list[dict] = []
    for row in records:
        d = row.get("record_date")
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except ValueError:
                continue
        if isinstance(d, date):
            parsed.append({**row, "record_date": d})

    if not parsed:
        return _empty_metrics(as_of)

    # Determine this month and last month
    this_month_start = as_of.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    # Same month last year
    try:
        smly_start = this_month_start.replace(year=this_month_start.year - 1)
        smly_end = smly_start.replace(
            month=smly_start.month + 1, day=1
        ) - timedelta(days=1) if smly_start.month < 12 else smly_start.replace(
            month=12, day=31
        )
    except ValueError:
        smly_start = this_month_start
        smly_end = this_month_start

    this_month_rows = [
        r for r in parsed
        if this_month_start <= r["record_date"] <= as_of
    ]
    last_month_rows = [
        r for r in parsed
        if last_month_start <= r["record_date"] <= last_month_end
    ]

    # Latest record for point-in-time balance sheet
    latest = max(parsed, key=lambda r: r["record_date"])

    total_assets = _safe_float(latest.get("total_assets"))
    total_liabilities = _safe_float(latest.get("total_liabilities"))
    total_equity = _safe_float(latest.get("total_equity"))
    debt_to_equity = (
        total_liabilities / total_equity
        if total_equity and total_equity != 0
        else 0.0
    )

    return FinanceMetrics(
        as_of_date=as_of,
        revenue=_compare_metric(this_month_rows, last_month_rows, "revenue", "MoM Revenue"),
        gross_profit_pct=_compare_metric(
            this_month_rows, last_month_rows, "gross_profit_pct", "MoM Gross Profit %"
        ),
        ebitda=_compare_metric(this_month_rows, last_month_rows, "ebitda", "MoM EBITDA"),
        operating_profit=_compare_metric(
            this_month_rows, last_month_rows, "operating_profit", "MoM Operating Profit"
        ),
        net_income=_compare_metric(
            this_month_rows, last_month_rows, "net_income", "MoM Net Income"
        ),
        operating_cash_flow=_compare_metric(
            this_month_rows, last_month_rows, "operating_cash_flow", "MoM Operating Cash Flow"
        ),
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        debt_to_equity=debt_to_equity,
        litres_sold=_compare_metric(
            this_month_rows, last_month_rows, "litres_sold", "MoM Litres Sold"
        ),
        revenue_per_litre=_avg(this_month_rows, "revenue_per_litre"),
        record_count=len(parsed),
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _sum(rows: list[dict], field: str) -> float:
    return sum(_safe_float(r.get(field)) for r in rows)


def _avg(rows: list[dict], field: str) -> float | None:
    vals = [_safe_float(r.get(field)) for r in rows if r.get(field) is not None]
    return sum(vals) / len(vals) if vals else None


def _compare_metric(
    current_rows: list[dict],
    previous_rows: list[dict],
    field: str,
    label: str,
) -> ComparisonResult | None:
    """Build a ComparisonResult for a metric across two time periods."""
    if not current_rows and not previous_rows:
        return None

    current = _sum(current_rows, field) if field != "gross_profit_pct" else _avg(current_rows, field) or 0.0
    previous = _sum(previous_rows, field) if field != "gross_profit_pct" else _avg(previous_rows, field) or 0.0

    change_abs = current - previous
    change_pct = (change_abs / previous * 100) if previous != 0 else 0.0
    direction = "up" if change_abs > 0 else ("down" if change_abs < 0 else "flat")

    return ComparisonResult(
        label=label,
        period="current_month",
        current=current,
        previous=previous,
        change_abs=change_abs,
        change_pct=change_pct,
        direction=direction,
    )


def _empty_metrics(as_of: date) -> FinanceMetrics:
    return FinanceMetrics(
        as_of_date=as_of,
        revenue=None,
        gross_profit_pct=None,
        ebitda=None,
        operating_profit=None,
        net_income=None,
        operating_cash_flow=None,
        total_assets=0.0,
        total_liabilities=0.0,
        total_equity=0.0,
        debt_to_equity=0.0,
        litres_sold=None,
        revenue_per_litre=None,
        record_count=0,
    )
