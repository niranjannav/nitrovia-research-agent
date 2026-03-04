"""Chart generator service.

Produces matplotlib charts as base64-encoded PNG strings for embedding
in PDF and PPTX report outputs.

All functions are pure (no side effects). They accept structured data
(dicts, lists) and return base64 PNG strings.

Available charts:
  - bar_comparison     : Single grouped bar comparing two periods
  - grouped_bar        : Multi-series grouped bar (e.g. channels over months)
  - line_trend         : Line chart for time-series trends
  - horizontal_bar     : Horizontal bar for top-N ranked items
  - donut              : Donut/pie for share breakdowns
"""

import base64
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Brand colour palette (can be overridden per call)
_PRIMARY = "#1E40AF"       # Deep blue
_SECONDARY = "#3B82F6"     # Mid blue
_ACCENT = "#F59E0B"        # Amber
_UP_COLOR = "#10B981"      # Green for growth
_DOWN_COLOR = "#EF4444"    # Red for decline
_NEUTRAL = "#6B7280"       # Grey
_BG = "#FFFFFF"
_GRID = "#E5E7EB"

_CHANNEL_COLORS = {
    "Dealers": "#1E40AF",
    "POS": "#3B82F6",
    "Firm": "#F59E0B",
    "HMD": "#10B981",
    "Wholesale": "#8B5CF6",
    "Export": "#6B7280",
}


def _fig_to_base64(fig) -> str:
    """Render a matplotlib figure to a base64-encoded PNG string."""
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150, facecolor=_BG)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return encoded


def _setup_axes(ax, title: str) -> None:
    """Apply consistent styling to an axes object."""
    ax.set_title(title, fontsize=13, fontweight="bold", color="#111827", pad=12)
    ax.set_facecolor(_BG)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_GRID)
    ax.spines["bottom"].set_color(_GRID)
    ax.tick_params(colors="#6B7280", labelsize=9)
    ax.yaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.5)
    ax.set_axisbelow(True)


def bar_comparison(
    labels: list[str],
    current_values: list[float],
    previous_values: list[float],
    title: str,
    current_label: str = "Current",
    previous_label: str = "Previous",
    value_format: str = "{:,.0f}",
) -> str:
    """Grouped bar chart comparing current vs previous period.

    Args:
        labels: Category labels (x-axis)
        current_values: Values for current period
        previous_values: Values for previous period
        title: Chart title
        current_label: Legend label for current period
        previous_label: Legend label for previous period
        value_format: Format string for value labels on bars

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    x = np.arange(len(labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.2), 5))
    fig.patch.set_facecolor(_BG)

    bars1 = ax.bar(x - width / 2, current_values, width, label=current_label, color=_PRIMARY, alpha=0.9)
    bars2 = ax.bar(x + width / 2, previous_values, width, label=previous_label, color=_NEUTRAL, alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30 if len(labels) > 5 else 0, ha="right")

    # Value labels on bars
    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h * 1.01,
                value_format.format(h),
                ha="center", va="bottom", fontsize=7.5, color=_PRIMARY,
            )

    _setup_axes(ax, title)
    ax.legend(fontsize=9, framealpha=0.5)
    plt.tight_layout()

    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def grouped_bar(
    categories: list[str],
    series: dict[str, list[float]],
    title: str,
    value_format: str = "{:,.0f}",
    color_map: dict[str, str] | None = None,
) -> str:
    """Multi-series grouped bar chart (e.g. multiple channels over months).

    Args:
        categories: X-axis category labels
        series: Dict of series_name -> list of values (same length as categories)
        title: Chart title
        value_format: Format string for values
        color_map: Optional mapping of series_name -> hex colour

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    n_series = len(series)
    n_cats = len(categories)
    width = min(0.8 / n_series, 0.25)
    x = np.arange(n_cats)

    default_colors = [_PRIMARY, _SECONDARY, _ACCENT, _UP_COLOR, "#8B5CF6", _NEUTRAL]
    color_map = color_map or {}

    fig, ax = plt.subplots(figsize=(max(8, n_cats * 1.1), 5))
    fig.patch.set_facecolor(_BG)

    for i, (series_name, values) in enumerate(series.items()):
        color = color_map.get(series_name) or _CHANNEL_COLORS.get(series_name) or default_colors[i % len(default_colors)]
        offset = (i - n_series / 2 + 0.5) * width
        ax.bar(x + offset, values, width, label=series_name, color=color, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30 if n_cats > 5 else 0, ha="right")
    _setup_axes(ax, title)
    ax.legend(fontsize=9, framealpha=0.5, loc="upper right")
    plt.tight_layout()

    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def line_trend(
    dates: list[str],
    series: dict[str, list[float]],
    title: str,
    value_format: str = "{:,.0f}",
    color_map: dict[str, str] | None = None,
) -> str:
    """Line chart for time-series data.

    Args:
        dates: X-axis date/period labels
        series: Dict of series_name -> list of values
        title: Chart title
        value_format: Format string
        color_map: Optional mapping of series_name -> hex colour

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    default_colors = [_PRIMARY, _ACCENT, _UP_COLOR, _SECONDARY, "#8B5CF6", _NEUTRAL]
    color_map = color_map or {}

    fig, ax = plt.subplots(figsize=(max(8, len(dates) * 0.8), 5))
    fig.patch.set_facecolor(_BG)

    for i, (name, values) in enumerate(series.items()):
        color = color_map.get(name) or default_colors[i % len(default_colors)]
        ax.plot(dates, values, marker="o", linewidth=2, markersize=5, label=name, color=color)
        # Annotate last point
        if values:
            ax.annotate(
                value_format.format(values[-1]),
                xy=(dates[-1], values[-1]),
                xytext=(4, 4), textcoords="offset points",
                fontsize=8, color=color,
            )

    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=30 if len(dates) > 6 else 0, ha="right")
    _setup_axes(ax, title)
    if len(series) > 1:
        ax.legend(fontsize=9, framealpha=0.5)
    plt.tight_layout()

    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def horizontal_bar(
    labels: list[str],
    values: list[float],
    title: str,
    value_format: str = "{:,.0f}",
    color_by_sign: bool = False,
) -> str:
    """Horizontal bar chart (ideal for top-N product rankings).

    Args:
        labels: Bar labels (y-axis)
        values: Bar values (x-axis)
        title: Chart title
        value_format: Format string for values
        color_by_sign: If True, colour positive bars green and negative bars red

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Truncate long labels
    labels = [str(l)[:35] + "…" if len(str(l)) > 35 else str(l) for l in labels]

    colors = (
        [_UP_COLOR if v >= 0 else _DOWN_COLOR for v in values]
        if color_by_sign
        else [_PRIMARY] * len(values)
    )

    fig_height = max(4, len(labels) * 0.45)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    fig.patch.set_facecolor(_BG)

    bars = ax.barh(labels, values, color=colors, alpha=0.85)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + abs(bar.get_width()) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            value_format.format(val),
            va="center", ha="left", fontsize=8, color="#374151",
        )

    ax.invert_yaxis()
    ax.set_facecolor(_BG)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_GRID)
    ax.spines["bottom"].set_color(_GRID)
    ax.tick_params(colors="#6B7280", labelsize=9)
    ax.xaxis.grid(True, color=_GRID, linestyle="--", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=13, fontweight="bold", color="#111827", pad=12)
    plt.tight_layout()

    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def donut(
    labels: list[str],
    values: list[float],
    title: str,
    color_map: dict[str, str] | None = None,
) -> str:
    """Donut chart for share breakdowns (e.g. revenue by channel).

    Args:
        labels: Segment labels
        values: Segment values (will be normalised to percentages)
        title: Chart title
        color_map: Optional mapping of label -> hex colour

    Returns:
        Base64-encoded PNG string
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    default_colors = [_PRIMARY, _SECONDARY, _ACCENT, _UP_COLOR, "#8B5CF6", _NEUTRAL, "#F87171"]
    color_map = color_map or {}
    colors = [
        color_map.get(l) or _CHANNEL_COLORS.get(l) or default_colors[i % len(default_colors)]
        for i, l in enumerate(labels)
    ]

    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor(_BG)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct="%1.1f%%",
        colors=colors,
        wedgeprops={"width": 0.55, "edgecolor": _BG, "linewidth": 2},
        startangle=90,
        pctdistance=0.75,
    )

    for autotext in autotexts:
        autotext.set_fontsize(8.5)
        autotext.set_color("white")

    ax.legend(
        wedges, labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=min(3, len(labels)),
        fontsize=8.5,
        framealpha=0.5,
    )
    ax.set_title(title, fontsize=13, fontweight="bold", color="#111827", pad=12)
    plt.tight_layout()

    result = _fig_to_base64(fig)
    plt.close(fig)
    return result


def generate_sales_charts(metrics_dict: dict) -> dict[str, str]:
    """Generate all standard Sales report charts from a SalesMetrics dict.

    Args:
        metrics_dict: Output of SalesMetrics.to_dict()

    Returns:
        Dict of chart_name -> base64_png_string
    """
    charts: dict[str, str] = {}

    # 1. WoW comparison bar
    wow = metrics_dict.get("time_comparisons", {}).get("wow")
    if wow:
        try:
            charts["wow_bar"] = bar_comparison(
                labels=["Revenue"],
                current_values=[wow["current"]],
                previous_values=[wow["previous"]],
                title=wow["label"],
                current_label="This Week",
                previous_label="Previous Week",
            )
        except Exception as e:
            logger.warning(f"WoW chart failed: {e}")

    # 2. Channel breakdown donut
    channel_bd = metrics_dict.get("channel_breakdown")
    if channel_bd and channel_bd.get("items"):
        try:
            items = channel_bd["items"]
            charts["channel_donut"] = donut(
                labels=[i["label"] for i in items],
                values=[i["current"] for i in items],
                title=f"Revenue by Channel — {channel_bd.get('period_label', '')}",
            )
            charts["channel_comparison"] = bar_comparison(
                labels=[i["label"] for i in items],
                current_values=[i["current"] for i in items],
                previous_values=[i["previous"] for i in items],
                title=f"Channel Performance — {channel_bd.get('period_label', '')}",
            )
        except Exception as e:
            logger.warning(f"Channel charts failed: {e}")

    # 3. Top products horizontal bar
    top_prods = metrics_dict.get("top_products")
    if top_prods and top_prods.get("items"):
        try:
            items = top_prods["items"]
            charts["top_products_bar"] = horizontal_bar(
                labels=[i["label"] for i in items],
                values=[i["value"] for i in items],
                title=f"Top 10 Products — {top_prods.get('period_label', '')}",
            )
        except Exception as e:
            logger.warning(f"Top products chart failed: {e}")

    # 4. Team performance bar
    team_bd = metrics_dict.get("team_breakdown")
    if team_bd and team_bd.get("items"):
        try:
            items = sorted(team_bd["items"], key=lambda x: x["current"], reverse=True)[:12]
            changes = [i["change_pct"] for i in items]
            charts["team_performance"] = horizontal_bar(
                labels=[i["label"] for i in items],
                values=changes,
                title=f"Team Performance (% Change) — {team_bd.get('period_label', '')}",
                value_format="{:+.1f}%",
                color_by_sign=True,
            )
        except Exception as e:
            logger.warning(f"Team chart failed: {e}")

    # 5. MoM time series line (requires full monthly series — best built in workflow)
    return charts


def generate_finance_charts(
    metrics_dict: dict,
    trend_dates: list[str],
    trend_values: list[float],
) -> dict[str, str]:
    """Generate standard finance charts.

    Returns a dict of chart_name -> base64 PNG string.
    """
    charts: dict[str, str] = {}

    # 1. Revenue trend line
    if trend_dates and trend_values:
        try:
            charts["revenue_trend"] = line_trend(
                dates=trend_dates,
                series={"Revenue": trend_values},
                title="Revenue Trend",
            )
        except Exception as e:
            logger.warning(f"Finance revenue trend chart failed: {e}")

    # 2. P&L comparison bar (current vs previous)
    pl_metrics = ["revenue", "gross_profit", "ebitda", "net_income"]
    current_vals = []
    previous_vals = []
    labels = []
    for key in pl_metrics:
        m = metrics_dict.get(key)
        if m and isinstance(m, dict):
            labels.append(key.replace("_", " ").title())
            current_vals.append(m.get("current", 0))
            previous_vals.append(m.get("previous", 0))

    if labels:
        try:
            charts["pl_comparison"] = grouped_bar(
                categories=labels,
                series={"Previous Period": previous_vals, "Current Period": current_vals},
                title="P&L Comparison — Current vs Previous Period",
            )
        except Exception as e:
            logger.warning(f"Finance P&L comparison chart failed: {e}")

    # 3. Balance sheet bar
    bs_fields = {
        "Total Assets": metrics_dict.get("total_assets", 0),
        "Total Liabilities": metrics_dict.get("total_liabilities", 0),
        "Total Equity": metrics_dict.get("total_equity", 0),
    }
    if any(v for v in bs_fields.values()):
        try:
            charts["balance_sheet"] = bar_comparison(
                labels=["Assets", "Liabilities", "Equity"],
                current_values=[
                    metrics_dict.get("total_assets", 0),
                    metrics_dict.get("total_liabilities", 0),
                    metrics_dict.get("total_equity", 0),
                ],
                previous_values=[0, 0, 0],
                title="Balance Sheet Position",
                current_label="Current",
                previous_label="",
            )
        except Exception as e:
            logger.warning(f"Finance balance sheet chart failed: {e}")

    return charts
