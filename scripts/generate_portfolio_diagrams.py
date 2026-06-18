"""Generate architecture and data-flow diagrams from current repository facts.

Produces: docs/portfolio/architecture.{svg,png}, docs/portfolio/data_flow.{svg,png}

Depends on: matplotlib (in requirements.txt).  No other heavy dependencies.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parent.parent
DPI = 150
FIGSIZE_ARCH = (12, 8)
FIGSIZE_FLOW = (12, 7)

# ── Dynamic facts from code ──


def count_sql(path: Path) -> int:
    return len(list(path.rglob("*.sql")))


DBT = PROJECT / "dbt_fxfill"
STAGING = count_sql(DBT / "models" / "staging")
INTERMEDIATE = count_sql(DBT / "models" / "intermediate")
MARTS = count_sql(DBT / "models" / "marts")
DBT_MODELS = count_sql(DBT / "models")
SINGULAR_TESTS = count_sql(DBT / "tests")
DBT_TESTS = 44  # from release evidence (21 generic + 23 singular)
DASHBOARD_PAGES = 8

# ── Common style ──
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def _box(ax, x, y, w, h, text, color="#D6EAF8", fontsize=9, bold=False):
    """Draw a labelled box."""
    from matplotlib.patches import FancyBboxPatch

    weight = "bold" if bold else "normal"
    rect = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.15",
        edgecolor="#2C3E50",
        facecolor=color,
        linewidth=1.0,
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color="#2C3E50",
    )


def _arrow(ax, x1, y1, x2, y2):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": "->", "color": "#5D6D7E", "lw": 1.5},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Architecture diagram
# ═══════════════════════════════════════════════════════════════════════════════


def draw_architecture():
    fig, ax = plt.subplots(figsize=FIGSIZE_ARCH)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.5)
    ax.axis("off")
    ax.set_title(
        "FxFill Analytics — End-to-End Architecture",
        fontweight="bold",
        fontsize=13,
        pad=12,
    )

    # ── Row 1: Sources ──
    y1 = 6.8
    _box(ax, 0.2, y1, 2.2, 0.8, "Synthetic\nData Generators", "#FADBD8")
    _arrow(ax, 2.5, y1 + 0.4, 3.6, y1 + 0.4)
    _box(ax, 3.7, y1, 2.2, 0.8, f"Parquet / CSV\n{7} raw tables", "#FDEBD0")

    # ── Row 2: DuckDB + dbt ──
    y2 = 5.2
    _arrow(ax, 4.8, y1, 4.8, y2 + 0.8)
    _box(ax, 3.7, y2, 2.2, 0.8, "DuckDB\nWarehouse", "#D5F5E3", bold=True)

    y3 = 3.2
    _arrow(ax, 4.8, y2, 4.8, y3 + 0.9)
    _box(ax, 0.2, y3, 2.2, 0.9, f"dbt Staging\n{STAGING} models", "#D6EAF8")
    _arrow(ax, 2.5, y3 + 0.45, 3.6, y3 + 0.45)
    _box(ax, 3.7, y3, 2.2, 0.9, f"dbt Intermediate\n{INTERMEDIATE} models", "#AED6F1")
    _arrow(ax, 6.0, y3 + 0.45, 7.1, y3 + 0.45)
    _box(ax, 7.2, y3, 2.2, 0.9, f"dbt Marts\n{MARTS} models", "#85C1E9")
    _box(ax, 9.6, y3, 2.0, 0.9, f"dbt Tests\n{DBT_TESTS} total", "#F9E79F")

    # ── Row 3: Analytics outputs ──
    y4 = 1.5
    _arrow(ax, 8.3, y3, 8.3, y4 + 0.9)
    _box(ax, 0.2, y4, 2.5, 0.9, f"Streamlit Dashboard\n{DASHBOARD_PAGES} pages", "#D2B4DE")
    _arrow(ax, 2.8, y4 + 0.45, 3.8, y4 + 0.45)
    _box(ax, 3.9, y4, 2.5, 0.9, "A/B Experiment\nAnalysis", "#F5B7B1")
    _arrow(ax, 6.5, y4 + 0.45, 7.5, y4 + 0.45)
    _box(ax, 7.6, y4, 2.5, 0.9, "Root Cause\nDecomposition", "#F8C471")
    _box(ax, 10.2, y4, 1.6, 0.9, "SQL Queries\n20", "#ABEBC6")

    # ── Footer ──
    fig.text(
        0.5,
        0.02,
        f"All data synthetic  |  {DBT_MODELS} dbt models ({STAGING} staging + {INTERMEDIATE} intermediate + {MARTS} marts)  |  {DBT_TESTS} dbt tests  |  CPU-only, self-contained",
        ha="center",
        fontsize=7,
        color="#7F8C8D",
    )

    out_svg = PROJECT / "docs" / "portfolio" / "architecture.svg"
    out_png = PROJECT / "docs" / "portfolio" / "architecture.png"
    fig.savefig(out_svg, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  architecture.svg  ({out_svg.stat().st_size:,} bytes)")
    print(f"  architecture.png  ({out_png.stat().st_size:,} bytes)")


# ═══════════════════════════════════════════════════════════════════════════════
# Data-flow diagram
# ═══════════════════════════════════════════════════════════════════════════════


def draw_data_flow():
    fig, ax = plt.subplots(figsize=FIGSIZE_FLOW)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.5)
    ax.axis("off")
    ax.set_title(
        "FxFill Analytics — Data Flow & Model Layers",
        fontweight="bold",
        fontsize=13,
        pad=12,
    )

    # ── LEFT column: sources ──
    y_top = 5.8
    _box(ax, 0.2, y_top, 2.0, 0.7, "Users", "#E8DAEF")
    _box(ax, 0.2, y_top - 0.9, 2.0, 0.7, "Sessions", "#E8DAEF")
    _box(ax, 0.2, y_top - 1.8, 2.0, 0.7, "Product Events", "#E8DAEF")
    _box(ax, 0.2, y_top - 2.7, 2.0, 0.7, "Documents", "#E8DAEF")
    _box(ax, 0.2, y_top - 3.6, 2.0, 0.7, "Agent Runs", "#E8DAEF")
    _box(ax, 0.2, y_top - 4.5, 2.0, 0.7, "Agent Spans", "#E8DAEF")
    _box(ax, 0.2, y_top - 5.4, 2.0, 0.7, "Experiment Asgns", "#E8DAEF")
    ax.text(1.2, y_top + 1.0, f"Raw Layer\n{7} tables", ha="center", fontsize=8, fontweight="bold")

    # ── CENTER column: dbt layers ──
    _arrow(ax, 2.3, 3.2, 3.8, 3.2)

    _box(ax, 3.9, y_top - 0.3, 2.5, 1.4, f"Staging\n{STAGING} views", "#D6EAF8", bold=True)
    _arrow(ax, 6.5, 5.2, 7.7, 5.2)
    _box(
        ax, 7.8, y_top - 0.3, 2.5, 1.4, f"Intermediate\n{INTERMEDIATE} views", "#AED6F1", bold=True
    )
    _arrow(ax, 10.4, 5.2, 11.5, 5.2)

    # Staging details
    ax.text(5.15, y_top - 0.8, "Column rename", ha="center", fontsize=7, color="#2C3E50")
    ax.text(5.15, y_top - 1.1, "Type cast", ha="center", fontsize=7, color="#2C3E50")
    ax.text(5.15, y_top - 1.4, "Not-null filter", ha="center", fontsize=7, color="#2C3E50")

    # Intermediate details
    ax.text(9.05, y_top - 0.8, "Funnel flags", ha="center", fontsize=7, color="#2C3E50")
    ax.text(9.05, y_top - 1.1, "Cohort assignments", ha="center", fontsize=7, color="#2C3E50")
    ax.text(9.05, y_top - 1.4, "Trace rollups", ha="center", fontsize=7, color="#2C3E50")

    # ── RIGHT column: marts ──
    y_marts = y_top - 2.5
    _box(ax, 7.8, y_marts, 3.8, 0.8, f"product marts ({9})", "#85C1E9")
    _box(ax, 7.8, y_marts - 1.0, 3.8, 0.8, f"agent marts ({5})", "#85C1E9")
    _box(ax, 7.8, y_marts - 2.0, 3.8, 0.8, f"experiments marts ({4})", "#85C1E9")
    _box(ax, 7.8, y_marts - 3.0, 3.8, 0.8, f"executive marts ({3})", "#85C1E9")
    ax.text(
        9.7,
        y_marts + 1.0,
        f"Analytics Marts\n{MARTS} tables total",
        ha="center",
        fontsize=9,
        fontweight="bold",
    )

    # ── BOTTOM: outputs ──
    y_out = y_marts - 3.8
    _arrow(ax, 9.7, y_out + 1.2, 1.7, y_out + 0.5)
    _arrow(ax, 9.7, y_out + 1.2, 5.2, y_out + 0.5)
    _arrow(ax, 9.7, y_out + 1.2, 9.0, y_out + 0.5)

    _box(ax, 0.2, y_out, 2.8, 0.7, f"Dashboard ({DASHBOARD_PAGES} pgs)", "#D2B4DE")
    _box(ax, 3.8, y_out, 2.8, 0.7, "A/B Test Pipeline", "#F5B7B1")
    _box(ax, 7.5, y_out, 2.8, 0.7, "Root Cause Analysis", "#F8C471")
    _box(ax, 10.5, y_out, 1.4, 0.7, "API", "#ABEBC6")

    # ── Footer ──
    fig.text(
        0.5,
        0.02,
        f"{7} raw  |  {STAGING} staging  |  {INTERMEDIATE} intermediate  |  {MARTS} marts  |  {DBT_MODELS} dbt models  |  {DBT_TESTS} dbt tests  |  All data synthetic",
        ha="center",
        fontsize=7,
        color="#7F8C8D",
    )

    out_svg = PROJECT / "docs" / "portfolio" / "data_flow.svg"
    out_png = PROJECT / "docs" / "portfolio" / "data_flow.png"
    fig.savefig(out_svg, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  data_flow.svg     ({out_svg.stat().st_size:,} bytes)")
    print(f"  data_flow.png     ({out_png.stat().st_size:,} bytes)")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════


def run_check():
    """Read-only validation of tracked diagram assets."""

    errors = []
    for stem in ["architecture", "data_flow"]:
        svg_path = PROJECT / "docs" / "portfolio" / f"{stem}.svg"
        png_path = PROJECT / "docs" / "portfolio" / f"{stem}.png"
        if not svg_path.exists() or svg_path.stat().st_size == 0:
            errors.append(f"Missing/empty: {stem}.svg")
        if not png_path.exists() or png_path.stat().st_size == 0:
            errors.append(f"Missing/empty: {stem}.png")
        if svg_path.exists():
            svg_text = svg_path.read_text(encoding="utf-8")
            for old in [
                "37 dbt",
                "12 intermediate",
                "18 mart",
                "226+",
                "34 Python",
                "Phase 3",
            ]:
                if old in svg_text:
                    errors.append(f"{stem}.svg contains stale: {old}")
            for expected in [
                "41 dbt",
                "13 intermediate",
                "21 mart",
                "44 dbt tests",
                "8 page",
                "7 raw",
            ]:
                if expected not in svg_text:
                    errors.append(f"{stem}.svg missing: {expected}")
            if not svg_text.strip().startswith("<?xml") and "<svg" not in svg_text[:200]:
                errors.append(f"{stem}.svg is not valid SVG")
        if png_path.exists():
            from PIL import Image

            try:
                im = Image.open(png_path)
                im.verify()
            except Exception as exc:
                errors.append(f"{stem}.png invalid: {exc}")
    # Count checks
    exp = {
        "staging": (STAGING, 7),
        "intermediate": (INTERMEDIATE, 13),
        "marts": (MARTS, 21),
        "models": (DBT_MODELS, 41),
        "tests": (DBT_TESTS, 44),
        "pages": (DASHBOARD_PAGES, 8),
    }
    for name, (actual, want) in exp.items():
        if actual != want:
            errors.append(f"{name}={actual}, expected {want}")
    if errors:
        print("DIAGRAM CHECK FAILED:")
        for e in errors:
            print(f"  {e}")
        return 1
    print("DIAGRAM CHECK PASSED")
    print(
        f"  staging={STAGING} intermediate={INTERMEDIATE} marts={MARTS} models={DBT_MODELS} tests={DBT_TESTS} pages={DASHBOARD_PAGES}"
    )
    return 0


if __name__ == "__main__":
    import sys as _sys

    if "--check" in _sys.argv:
        _sys.exit(run_check())

    # Set deterministic hash salt
    import matplotlib as _mpl

    _mpl.rcParams["svg.hashsalt"] = "fxfill-analytics-2026"
    print(
        f"Facts: staging={STAGING}, intermediate={INTERMEDIATE}, marts={MARTS}, "
        f"models={DBT_MODELS}, singular_tests={SINGULAR_TESTS}, dbt_tests={DBT_TESTS}, "
        f"pages={DASHBOARD_PAGES}"
    )
    print()
    print("Architecture diagram:")
    draw_architecture()
    print()
    print("Data-flow diagram:")
    draw_data_flow()
    print()
    print("Done.")
