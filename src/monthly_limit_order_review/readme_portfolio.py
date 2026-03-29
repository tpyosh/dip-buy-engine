from __future__ import annotations

import math
from pathlib import Path

from .portfolio_metrics import format_pct
from .utils import ensure_parent

README_MARKER_START = "<!-- portfolio-piechart:start -->"
README_MARKER_END = "<!-- portfolio-piechart:end -->"
README_SECTION_TITLE = "## Latest Portfolio Snapshot"
README_IMAGE_PATH = "docs/portfolio_allocation_latest.svg"
PIE_COLORS = {
    "core": "#2E86AB",
    "jun_core": "#F6C85F",
    "satellite_core": "#6F4E7C",
    "satellite": "#CA472F",
    "pension": "#45A29E",
    "liquidity": "#7FBC41",
    "other": "#9E9E9E",
}
BUCKET_ORDER = [
    "core",
    "jun_core",
    "satellite_core",
    "satellite",
    "pension",
    "liquidity",
    "other",
]
SVG_WIDTH = 720
SVG_HEIGHT = 440
SVG_CENTER_X = 220
SVG_CENTER_Y = 210
SVG_RADIUS = 140


def build_bucket_summary(bucket_allocations: list, *, include_zero_buckets: bool = True) -> list[dict]:
    allocation_map = {allocation.bucket: allocation for allocation in bucket_allocations}
    summary: list[dict] = []
    for bucket in BUCKET_ORDER:
        allocation = allocation_map.get(bucket)
        market_value_jpy = allocation.market_value_jpy if allocation is not None else 0
        actual_pct = allocation.actual_pct if allocation is not None else None
        if not include_zero_buckets and market_value_jpy == 0:
            continue
        summary.append(
            {
                "bucket": bucket,
                "market_value_jpy": market_value_jpy,
                "pct": actual_pct,
            }
        )
    return summary


def build_portfolio_pie_svg(bucket_summary: list[dict]) -> str:
    total_value = sum(item["market_value_jpy"] for item in bucket_summary if item["market_value_jpy"] > 0)
    slices = [item for item in bucket_summary if item["market_value_jpy"] > 0]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Portfolio Allocation</title>',
        '<desc id="desc">Bucket-level portfolio allocation pie chart.</desc>',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        '<text x="32" y="44" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#111827">Portfolio Allocation</text>',
    ]
    if total_value <= 0:
        lines.append('<text x="32" y="90" font-family="Arial, sans-serif" font-size="16" fill="#374151">No non-zero buckets available.</text>')
        lines.append("</svg>")
        return "\n".join(lines)

    start_angle = -90.0
    for item in slices:
        fraction = float(item["market_value_jpy"] / total_value)
        sweep_angle = 360.0 * fraction
        end_angle = start_angle + sweep_angle
        path = describe_pie_slice(
            cx=SVG_CENTER_X,
            cy=SVG_CENTER_Y,
            radius=SVG_RADIUS,
            start_angle=start_angle,
            end_angle=end_angle,
        )
        lines.append(
            f'<path d="{path}" fill="{PIE_COLORS[item["bucket"]]}" stroke="#ffffff" stroke-width="2" />'
        )
        start_angle = end_angle

    legend_x = 420
    legend_y = 92
    legend_step = 38
    for index, item in enumerate(slices):
        y = legend_y + index * legend_step
        lines.append(f'<rect x="{legend_x}" y="{y - 14}" width="16" height="16" rx="3" fill="{PIE_COLORS[item["bucket"]]}" />')
        lines.append(
            f'<text x="{legend_x + 26}" y="{y}" font-family="Arial, sans-serif" font-size="15" fill="#111827">'
            f'{item["bucket"]} ({format_pct(item["pct"]) if item["pct"] is not None else "0.00%"})'
            f"</text>"
        )

    lines.append("</svg>")
    return "\n".join(lines)


def describe_pie_slice(*, cx: int, cy: int, radius: int, start_angle: float, end_angle: float) -> str:
    if end_angle - start_angle >= 359.999:
        return (
            f"M {cx} {cy} m {-radius} 0 "
            f"a {radius} {radius} 0 1 0 {radius * 2} 0 "
            f"a {radius} {radius} 0 1 0 {-radius * 2} 0"
        )

    start_x = cx + radius * math.cos(math.radians(start_angle))
    start_y = cy + radius * math.sin(math.radians(start_angle))
    end_x = cx + radius * math.cos(math.radians(end_angle))
    end_y = cy + radius * math.sin(math.radians(end_angle))
    large_arc_flag = 1 if end_angle - start_angle > 180 else 0
    return (
        f"M {cx} {cy} "
        f"L {start_x:.4f} {start_y:.4f} "
        f"A {radius} {radius} 0 {large_arc_flag} 1 {end_x:.4f} {end_y:.4f} Z"
    )


def build_readme_image_markdown(image_path: str = README_IMAGE_PATH) -> str:
    return f"![Portfolio Allocation]({image_path})"


def build_bucket_summary_table(bucket_summary: list[dict]) -> str:
    lines = [
        "| bucket | market_value_jpy | pct |",
        "| --- | ---: | ---: |",
    ]
    for item in bucket_summary:
        pct = format_pct(item["pct"]) if item["pct"] is not None else "0.00%"
        lines.append(f'| {item["bucket"]} | {item["market_value_jpy"]} | {pct} |')
    return "\n".join(lines)


def build_readme_portfolio_section(
    *,
    snapshot_date: str,
    total_assets_jpy,
    bucket_summary: list[dict],
    image_path: str = README_IMAGE_PATH,
) -> str:
    return "\n".join(
        [
            README_MARKER_START,
            README_SECTION_TITLE,
            "",
            f"- snapshot_date: {snapshot_date}",
            f"- total_assets_jpy: {total_assets_jpy}",
            "",
            build_readme_image_markdown(image_path),
            "",
            build_bucket_summary_table(bucket_summary),
            README_MARKER_END,
        ]
    )


def update_readme_portfolio_section(
    readme_text: str,
    *,
    snapshot_date: str,
    total_assets_jpy,
    bucket_summary: list[dict],
    image_path: str = README_IMAGE_PATH,
) -> str:
    rendered_section = build_readme_portfolio_section(
        snapshot_date=snapshot_date,
        total_assets_jpy=total_assets_jpy,
        bucket_summary=bucket_summary,
        image_path=image_path,
    )
    if README_MARKER_START in readme_text and README_MARKER_END in readme_text:
        start_index = readme_text.index(README_MARKER_START)
        end_index = readme_text.index(README_MARKER_END) + len(README_MARKER_END)
        return f"{readme_text[:start_index]}{rendered_section}{readme_text[end_index:]}"

    insert_after = "\n## 目的\n"
    if insert_after in readme_text:
        index = readme_text.index(insert_after)
        return f"{readme_text[:index]}{rendered_section}\n\n{readme_text[index:]}"
    return f"{readme_text.rstrip()}\n\n{rendered_section}\n"


def refresh_readme_portfolio(
    *,
    readme_path: Path,
    snapshot_date: str,
    total_assets_jpy,
    bucket_allocations: list,
    image_output_path: Path | None = None,
) -> str:
    bucket_summary = build_bucket_summary(bucket_allocations)
    resolved_image_path = image_output_path or readme_path.parent / README_IMAGE_PATH
    ensure_parent(resolved_image_path)
    resolved_image_path.write_text(build_portfolio_pie_svg(bucket_summary), encoding="utf-8")
    updated_text = update_readme_portfolio_section(
        readme_path.read_text(encoding="utf-8"),
        snapshot_date=snapshot_date,
        total_assets_jpy=total_assets_jpy,
        bucket_summary=bucket_summary,
        image_path=str(resolved_image_path.relative_to(readme_path.parent)),
    )
    readme_path.write_text(updated_text, encoding="utf-8")
    return updated_text
