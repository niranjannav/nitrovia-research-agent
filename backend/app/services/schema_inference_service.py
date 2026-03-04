"""Schema inference service.

Uses Claude to analyse an Excel workbook structure (from SheetScanner) and
produce a SchemaMapping JSON that tells the GenericDataExtractor how to pull
records from any format of Excel file.

The mapping is saved to the database and reused for all future uploads of the
same format, so the expensive AI inference call happens only once per format.
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from app.llm.gateway import create_gateway_from_settings
from app.llm.config import TaskType
from app.services.sheet_scanner import SheetSummary
from app.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

# ── Prompt loading ──────────────────────────────────────────────────────────

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "schema_inference.txt"
_PROMPT_TEMPLATE: str | None = None


def _load_prompt() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        try:
            _PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"schema_inference.txt not found at {_PROMPT_PATH}, using fallback")
            _PROMPT_TEMPLATE = _FALLBACK_PROMPT
    return _PROMPT_TEMPLATE


_FALLBACK_PROMPT = """
Analyse the following Excel workbook structure and produce a SchemaMapping JSON object.
The domain is: {domain}

Workbook structure:
{sheet_summary}

Return ONLY valid JSON with these fields:
- domain, mapping_name, confidence, notes
- source_sheets (list of transactional sheet names)
- header_row (integer)
- column_roles (dict mapping standard field names to exact Excel column headers)
- time_structure (type, columns, year_source, year_value)
- derived_fields (optional)
- lookup_sheet (optional)
- exclude_sheets (list)
- warnings (list)
"""

# ── Domain context definitions ──────────────────────────────────────────────

DOMAIN_CONTEXT: dict[str, str] = {
    "sales": (
        "This is a sales data workbook tracking product sales by customer, channel, "
        "and salesperson. Key metrics are: quantity sold (units), litres sold, and "
        "revenue. Channels include: Dealers, POS (Point of Sale), Firm, HMD "
        "(Home Delivery), Wholesale, Export."
    ),
    "production": (
        "This is a production data workbook tracking milk collection from farms, "
        "processing volumes, and order fulfilment. Key metrics are: litres received, "
        "litres processed, and orders fulfilled. Data is segmented by product category "
        "(Fresh Milk, Mtindi, Yogurt) and SKU."
    ),
    "qa": (
        "This is a quality assurance workbook tracking quality cases (complaints, "
        "incidents) by region, category, and time period. Categories include: "
        "Spillage, Spoilage, Expired. Each row represents a quality case or a "
        "count of cases."
    ),
    "finance": (
        "This is a financial data workbook covering revenue, cost of goods sold, "
        "gross margin, and operating costs. It may contain a profit & loss structure "
        "with GL codes or account names."
    ),
}

FIELD_DEFINITIONS: dict[str, str] = {
    "sales": """
Standard field names to map from Excel columns:
- product_code: item/product identifier code
- product_name: descriptive product name
- customer_code: customer/account identifier code
- customer_name: customer or account name
- salesperson: name of the sales representative
- team: team or group name the salesperson belongs to
- region: geographic region code or name
- channel: sales channel (Dealers, POS, Firm, HMD, Wholesale, Export)
  NOTE: channel is often DERIVED from customer_code prefix — describe this in derived_fields
- quantity_units: quantity sold in product units
- quantity_litres: quantity sold converted to litres
  NOTE: litres are often in a companion sheet — describe in secondary_metric_sheets
- revenue: sales revenue amount
""",
    "production": """
Standard field names to map from Excel columns:
- product_code: item/SKU identifier code
- product_name: product name
- category: product category (Fresh Milk, Mtindi, Yogurt, etc.)
- source_name: farm or supplier name (for milk collection)
- region: geographic region
- quantity_received_litres: litres of raw milk received/collected
- quantity_processed_litres: litres processed
- orders_fulfilled: number or volume of orders fulfilled
""",
    "qa": """
Standard field names to map from Excel columns:
- case_id: unique case identifier
- case_date: date the case was reported
- region: geographic region
- category: case category (Spillage, Spoilage, Expired)
- product_code: product involved
- product_name: product name
- description: case description
- source: where the case originated (customer, distributor, etc.)
- case_count: number of cases (if this is a summary row)
""",
    "finance": """
Standard field names to map from Excel columns (P&L / Balance Sheet / Cash Flow):
- revenue: total revenue / sales
- cogs: cost of goods sold
- gross_profit: revenue minus COGS
- gross_profit_pct: gross profit as a percentage of revenue
- other_income: other income / non-operating income
- operating_expenses: total operating expenses
- operating_profit: operating profit / EBIT proxy
- ebit: earnings before interest and tax
- ebitda: EBIT plus depreciation and amortisation
- net_income: net income / net profit after tax
- litres_sold: volume of product sold in litres
- revenue_per_litre: revenue divided by litres sold
- cost_per_litre: COGS divided by litres sold
- total_assets: total assets (Balance Sheet)
- total_liabilities: total liabilities (Balance Sheet)
- total_equity: shareholders equity (Balance Sheet)
- operating_cash_flow: cash from operations (Cash Flow Statement)
- investing_cash_flow: cash from investing activities
- financing_cash_flow: cash from financing activities
- net_cash_flow: net change in cash position

For transposed_financial sheets, use row_label_map to map row labels to standard fields.
""",
}


# ── Pydantic schema for structured LLM output ────────────────────────────────

class TimeStructure(BaseModel):
    type: str
    columns: list[str] = Field(default_factory=list)
    year_source: str = "unknown"
    year_value: int | None = None
    # dual_metric_wide_monthly fields
    metric_blocks: list[dict] | None = None
    # transposed_financial fields
    label_column: str | None = None
    row_label_map: dict | None = None
    date_header_row: int | None = None


class DerivedField(BaseModel):
    from_col: str = Field(alias="from")
    method: str
    prefix_length: int | None = None
    pattern: str | None = None
    map: dict[str, str] | None = None
    lookup_sheet: str | None = None
    lookup_key_col: str | None = None
    lookup_value_col: str | None = None
    companion_sheet_pattern: str | None = None
    value: str | None = None

    class Config:
        populate_by_name = True


class SchemaMapping(BaseModel):
    domain: str
    mapping_name: str
    confidence: float = 0.0
    notes: str = ""
    source_sheets: list[str]
    header_row: int = 1
    column_roles: dict[str, str]
    time_structure: TimeStructure
    derived_fields: dict[str, DerivedField] = Field(default_factory=dict)
    lookup_sheet: str | None = None
    secondary_metric_sheets: dict[str, str] = Field(default_factory=dict)
    exclude_sheets: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Service ──────────────────────────────────────────────────────────────────

class SchemaInferenceService:
    """Infers SchemaMapping from an Excel workbook structure using Claude."""

    async def infer(
        self,
        sheet_summary: SheetSummary,
        domain: str,
    ) -> SchemaMapping:
        """Call Claude to infer a SchemaMapping from the workbook structure.

        Args:
            sheet_summary: Output of SheetScanner.scan()
            domain: Analytics domain ('sales' | 'production' | 'qa' | 'finance')

        Returns:
            Validated SchemaMapping

        Raises:
            ValueError: If Claude returns invalid JSON or the domain is unknown
        """
        if domain not in DOMAIN_CONTEXT:
            raise ValueError(
                f"Unknown domain '{domain}'. "
                f"Valid values: {list(DOMAIN_CONTEXT.keys())}"
            )

        prompt_template = _load_prompt()
        sheet_summary_json = json.dumps(sheet_summary.to_dict(), indent=2)

        # Trim sheet summary if very large to avoid token overflow
        if len(sheet_summary_json) > 40_000:
            sheet_summary_json = sheet_summary_json[:40_000] + "\n... (truncated)"

        prompt = prompt_template.format(
            domain=domain,
            domain_context=DOMAIN_CONTEXT[domain],
            field_definitions=FIELD_DEFINITIONS.get(domain, ""),
            sheet_summary=sheet_summary_json,
        )

        gateway = create_gateway_from_settings()

        try:
            result, usage = await gateway.generate_structured(
                task=TaskType.CLASSIFICATION,
                output_schema=SchemaMapping,
                messages=[{"role": "user", "content": prompt}],
                system_prompt=(
                    "You are a precise data analyst. You return ONLY valid JSON "
                    "matching the requested schema. Never include prose or markdown."
                ),
                temperature=0.1,
                max_tokens=4096,
            )
            logger.info(
                f"Schema inferred for domain='{domain}', "
                f"confidence={result.confidence:.2f}, "
                f"tokens_used={usage.total_tokens}"
            )
            return result

        except Exception as e:
            logger.error(f"Schema inference failed: {e}")
            raise ValueError(f"Schema inference failed: {e}") from e

    def save_mapping(
        self,
        user_id: str,
        domain: str,
        mapping: SchemaMapping,
        confirmed: bool = False,
    ) -> str:
        """Persist a SchemaMapping to the database.

        Returns:
            The UUID of the saved mapping record.
        """
        supabase = get_supabase_client()

        mapping_dict = mapping.model_dump(mode="json")

        result = (
            supabase.table("analytics_schema_mappings")
            .insert({
                "user_id": user_id,
                "domain": domain,
                "mapping_name": mapping.mapping_name,
                "mapping": mapping_dict,
                "confirmed_by_user": confirmed,
            })
            .execute()
        )

        if not result.data:
            raise RuntimeError("Failed to save schema mapping to database")

        mapping_id = result.data[0]["id"]
        logger.info(f"Schema mapping saved: id={mapping_id}, domain={domain}")
        return mapping_id

    def get_mapping(self, user_id: str, domain: str) -> SchemaMapping | None:
        """Fetch the most recent confirmed mapping for a user+domain.

        Returns None if no confirmed mapping exists.
        """
        supabase = get_supabase_client()

        result = (
            supabase.table("analytics_schema_mappings")
            .select("*")
            .eq("user_id", user_id)
            .eq("domain", domain)
            .eq("confirmed_by_user", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        mapping_data = result.data[0]["mapping"]
        return SchemaMapping.model_validate(mapping_data)

    def get_mapping_by_id(self, mapping_id: str) -> SchemaMapping | None:
        """Fetch a mapping by its UUID."""
        supabase = get_supabase_client()

        result = (
            supabase.table("analytics_schema_mappings")
            .select("mapping")
            .eq("id", mapping_id)
            .single()
            .execute()
        )

        if not result.data:
            return None

        return SchemaMapping.model_validate(result.data["mapping"])

    def confirm_mapping(self, mapping_id: str, user_id: str) -> None:
        """Mark a mapping as confirmed by the user."""
        supabase = get_supabase_client()

        supabase.table("analytics_schema_mappings").update({
            "confirmed_by_user": True,
        }).eq("id", mapping_id).eq("user_id", user_id).execute()

        logger.info(f"Schema mapping confirmed: id={mapping_id}")

    def auto_confirm(
        self,
        mapping: SchemaMapping,
        user_id: str,
        domain: str,
    ) -> str:
        """Save and immediately confirm a mapping without user review.

        Used by the silent auto-infer flow on upload. Returns the new mapping UUID.
        """
        import datetime as _dt
        timestamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
        mapping.mapping_name = f"Auto-{domain}-{timestamp}"
        mapping_id = self.save_mapping(
            user_id=user_id,
            domain=domain,
            mapping=mapping,
            confirmed=True,
        )
        logger.info(f"Schema mapping auto-confirmed: id={mapping_id}, domain={domain}")
        return mapping_id

    def update_mapping(
        self,
        mapping_id: str,
        user_id: str,
        mapping: SchemaMapping,
    ) -> None:
        """Replace an existing mapping's JSON content (e.g. after user correction)."""
        supabase = get_supabase_client()

        supabase.table("analytics_schema_mappings").update({
            "mapping": mapping.model_dump(mode="json"),
            "mapping_name": mapping.mapping_name,
            "updated_at": "now()",
        }).eq("id", mapping_id).eq("user_id", user_id).execute()

        logger.info(f"Schema mapping updated: id={mapping_id}")
