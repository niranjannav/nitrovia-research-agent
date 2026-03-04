"""Analytics data service.

Handles persistence and querying of normalized analytics records in the
domain-specific SQL tables (sales_records, etc.).

The service is generic at the query level — domain-specific tables are
identified by domain string. Insertion maps AnalyticsRecord fields to
the correct columns per domain.
"""

import logging
from datetime import date, timedelta
from typing import Any

from app.services.generic_data_extractor import AnalyticsRecord
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

# Map domain -> table name
_DOMAIN_TABLES = {
    "sales": "sales_records",
    "finance": "finance_records",
    # "production": "production_records",  # added in future migration
    # "qa": "qa_records",
}


class AnalyticsDataService:
    """Inserts extracted records into domain tables and queries them back."""

    def ingest(
        self,
        upload_id: str,
        user_id: str,
        domain: str,
        records: list[AnalyticsRecord],
    ) -> int:
        """Bulk-insert AnalyticsRecord objects into the domain table.

        Existing records for the same upload_id are deleted first (idempotent
        re-upload). Returns the number of rows inserted.
        """
        table = _get_table(domain)
        supabase = get_supabase_client()

        # Delete any existing rows for this upload (idempotent)
        supabase.table(table).delete().eq("upload_id", upload_id).execute()

        if not records:
            logger.warning(f"No records to insert for upload_id={upload_id}")
            return 0

        rows = [_record_to_row(r, upload_id, user_id, domain) for r in records]

        # Supabase accepts up to 500 rows per insert; batch if needed
        batch_size = 400
        total_inserted = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i: i + batch_size]
            result = supabase.table(table).insert(batch).execute()
            if result.data:
                total_inserted += len(result.data)

        logger.info(
            f"Ingested {total_inserted} rows into {table} "
            f"(upload_id={upload_id})"
        )
        return total_inserted

    def query_sales(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        channel: str | None = None,
        salesperson: str | None = None,
        product_code: str | None = None,
    ) -> list[dict]:
        """Query sales records within a date range with optional filters.

        Returns a list of dicts (one per row) — keeping raw dicts avoids
        re-instantiating dataclasses in the metrics layer.
        """
        supabase = get_supabase_client()

        query = (
            supabase.table("sales_records")
            .select("*")
            .eq("user_id", user_id)
            .gte("record_date", start_date.isoformat())
            .lte("record_date", end_date.isoformat())
        )

        if channel:
            query = query.eq("channel", channel)
        if salesperson:
            query = query.eq("salesperson", salesperson)
        if product_code:
            query = query.eq("product_code", product_code)

        result = query.execute()
        rows = result.data or []

        # Deserialise record_date strings to date objects
        for row in rows:
            if isinstance(row.get("record_date"), str):
                try:
                    row["record_date"] = date.fromisoformat(row["record_date"])
                except ValueError:
                    pass

        return rows

    def query_all_for_metrics(
        self,
        user_id: str,
        domain: str,
        as_of: date,
        lookback_years: int = 2,
    ) -> list[dict]:
        """Query all records needed to compute the full metrics suite.

        Fetches records from `lookback_years` years ago up to as_of date.
        This covers WoW, MoM, SMLY, YTD, QoQ, SQLY comparisons.
        """
        start_date = as_of.replace(year=as_of.year - lookback_years, month=1, day=1)

        if domain == "sales":
            return self.query_sales(user_id, start_date, as_of)
        else:
            # Generic fallback for other domains (table must exist)
            table = _get_table(domain)
            supabase = get_supabase_client()
            result = (
                supabase.table(table)
                .select("*")
                .eq("user_id", user_id)
                .gte("record_date", start_date.isoformat())
                .lte("record_date", as_of.isoformat())
                .execute()
            )
            return result.data or []

    def get_monthly_trend(
        self,
        user_id: str,
        domain: str,
        metric: str,
        months: int = 12,
        as_of: date | None = None,
    ) -> list[dict]:
        """Return monthly aggregated values for a metric, for trend line charts.

        Returns list of {"month": "2025-01", "value": 123456.78}
        """
        as_of = as_of or date.today()
        start_date = (as_of.replace(day=1) - timedelta(days=1)).replace(day=1)
        for _ in range(months - 1):
            start_date = (start_date - timedelta(days=1)).replace(day=1)

        if domain == "sales":
            rows = self.query_sales(user_id, start_date, as_of)
        else:
            rows = self.query_all_for_metrics(user_id, domain, as_of, lookback_years=2)

        # Group by month
        monthly: dict[str, float] = {}
        for row in rows:
            d = row.get("record_date")
            if isinstance(d, str):
                d = date.fromisoformat(d)
            if d is None:
                continue
            key = d.strftime("%Y-%m")
            monthly[key] = monthly.get(key, 0) + float(row.get(metric, 0) or 0)

        # Return sorted list
        return [
            {"month": k, "value": round(v, 2)}
            for k, v in sorted(monthly.items())
        ]

    def mark_upload_complete(
        self, upload_id: str, row_count: int
    ) -> None:
        supabase = get_supabase_client()
        supabase.table("analytics_uploads").update({
            "status": "completed",
            "row_count": row_count,
        }).eq("id", upload_id).execute()

    def mark_upload_failed(
        self, upload_id: str, error: str
    ) -> None:
        supabase = get_supabase_client()
        supabase.table("analytics_uploads").update({
            "status": "failed",
            "error_message": error[:500],
        }).eq("id", upload_id).execute()

    def create_upload_record(
        self,
        user_id: str,
        domain: str,
        mapping_id: str | None,
        period_start: date,
        period_end: date,
        file_name: str,
        storage_path: str,
    ) -> str:
        """Insert an analytics_uploads row and return its UUID."""
        supabase = get_supabase_client()
        result = (
            supabase.table("analytics_uploads")
            .insert({
                "user_id": user_id,
                "domain": domain,
                "mapping_id": mapping_id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "file_name": file_name,
                "storage_path": storage_path,
                "status": "pending",
            })
            .execute()
        )
        if not result.data:
            raise RuntimeError("Failed to create analytics_uploads record")
        return result.data[0]["id"]

    def ingest_finance(
        self,
        upload_id: str,
        user_id: str,
        records: list[AnalyticsRecord],
    ) -> int:
        """Bulk-insert finance records into finance_records table.

        Uses the same idempotent pattern as ingest() — deletes existing rows
        for this upload_id first, then inserts fresh data.
        Returns the number of rows inserted.
        """
        supabase = get_supabase_client()
        supabase.table("finance_records").delete().eq("upload_id", upload_id).execute()

        if not records:
            logger.warning(f"No finance records to insert for upload_id={upload_id}")
            return 0

        rows = [_finance_record_to_row(r, upload_id, user_id) for r in records]

        batch_size = 400
        total_inserted = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i: i + batch_size]
            result = supabase.table("finance_records").insert(batch).execute()
            if result.data:
                total_inserted += len(result.data)

        logger.info(
            f"Ingested {total_inserted} finance rows (upload_id={upload_id})"
        )
        return total_inserted

    def query_finance(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Query finance_records within a date range."""
        supabase = get_supabase_client()
        result = (
            supabase.table("finance_records")
            .select("*")
            .eq("user_id", user_id)
            .gte("record_date", start_date.isoformat())
            .lte("record_date", end_date.isoformat())
            .order("record_date")
            .execute()
        )
        rows = result.data or []
        for row in rows:
            if isinstance(row.get("record_date"), str):
                try:
                    row["record_date"] = date.fromisoformat(row["record_date"])
                except ValueError:
                    pass
        return rows

    def query_all_finance_for_metrics(
        self,
        user_id: str,
        lookback_years: int = 5,
    ) -> list[dict]:
        """Return finance records for last N years (for metrics computation)."""
        end_date = date.today()
        start_date = end_date.replace(year=end_date.year - lookback_years, month=1, day=1)
        return self.query_finance(user_id, start_date, end_date)

    def set_upload_mapping(self, upload_id: str, mapping_id: str) -> None:
        """Patch the mapping_id on an existing upload record."""
        supabase = get_supabase_client()
        supabase.table("analytics_uploads").update({
            "mapping_id": mapping_id,
        }).eq("id", upload_id).execute()
        logger.info(f"Upload {upload_id} linked to mapping {mapping_id}")

    def list_uploads(
        self,
        user_id: str,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        supabase = get_supabase_client()
        query = (
            supabase.table("analytics_uploads")
            .select("id, domain, file_name, period_start, period_end, status, row_count, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if domain:
            query = query.eq("domain", domain)
        return query.execute().data or []


# ── Private helpers ──────────────────────────────────────────────────────────

def _get_table(domain: str) -> str:
    table = _DOMAIN_TABLES.get(domain)
    if not table:
        raise ValueError(
            f"Unknown analytics domain '{domain}'. "
            f"Valid domains: {list(_DOMAIN_TABLES.keys())}"
        )
    return table


def _record_to_row(
    record: AnalyticsRecord,
    upload_id: str,
    user_id: str,
    domain: str,
) -> dict:
    """Convert an AnalyticsRecord to a DB row dict for the domain table."""
    base = {
        "upload_id": upload_id,
        "user_id": user_id,
        "record_date": record.record_date.isoformat(),
    }

    if domain == "sales":
        return {
            **base,
            "product_code": record.product_code,
            "product_name": record.product_name,
            "customer_code": record.customer_code,
            "customer_name": record.customer_name,
            "channel": record.channel,
            "region": record.region,
            "salesperson": record.salesperson,
            "team": record.team,
            "quantity_units": _safe_float(record.quantity_units),
            "quantity_litres": _safe_float(record.quantity_litres),
            "revenue": _safe_float(record.revenue),
        }

    # Default fallback (future domains)
    return {**base, "data": record.extra}


def _finance_record_to_row(
    record: AnalyticsRecord,
    upload_id: str,
    user_id: str,
) -> dict:
    """Convert an AnalyticsRecord to a finance_records DB row dict."""
    return {
        "upload_id": upload_id,
        "user_id": user_id,
        "record_date": record.record_date.isoformat(),
        "revenue": _safe_float(record.revenue),
        "cogs": _safe_float(record.cogs),
        "gross_profit": _safe_float(record.gross_profit),
        "gross_profit_pct": _safe_float(record.gross_profit_pct),
        "other_income": _safe_float(record.other_income),
        "operating_expenses": _safe_float(record.operating_expenses),
        "operating_profit": _safe_float(record.operating_profit),
        "ebit": _safe_float(record.ebit),
        "ebitda": _safe_float(record.ebitda),
        "net_income": _safe_float(record.net_income),
        "litres_sold": _safe_float(record.litres_sold),
        "revenue_per_litre": _safe_float(record.revenue_per_litre),
        "cost_per_litre": _safe_float(record.cost_per_litre),
        "total_assets": _safe_float(record.total_assets),
        "total_liabilities": _safe_float(record.total_liabilities),
        "total_equity": _safe_float(record.total_equity),
        "operating_cash_flow": _safe_float(record.operating_cash_flow),
        "investing_cash_flow": _safe_float(record.investing_cash_flow),
        "financing_cash_flow": _safe_float(record.financing_cash_flow),
        "net_cash_flow": _safe_float(record.net_cash_flow),
    }


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
