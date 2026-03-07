from __future__ import annotations

import re
from decimal import Decimal

from .models import ReviewFeedback, ReviewOrderProposal
from .utils import to_optional_decimal

SECTION_HEADINGS = {
    "monthly_proposals": ["今月の指値提案", "指値提案"],
    "sox_decision": ["SOX投信判定", "SOX判定"],
    "portfolio_diagnosis": ["ポートフォリオ診断", "資産配分診断"],
    "rule_review": ["ルール改善レビュー", "改善レビュー"],
    "codex_summary": ["Codex向け修正要約", "Codex 向け修正要約", "修正要約"],
}


def parse_review_feedback(review_text: str) -> ReviewFeedback:
    sections = split_sections(review_text)
    parser_warnings = [
        f"Section not found: {section_name}"
        for section_name in SECTION_HEADINGS
        if not sections.get(section_name)
    ]
    monthly_text = sections.get("monthly_proposals", "")
    codex_text = sections.get("codex_summary", "")

    must, should, nice_to_have = extract_priority_lists(codex_text)
    if not any([must, should, nice_to_have]):
        parser_warnings.append("Priority lists were not extracted from Codex summary.")

    return ReviewFeedback(
        raw_text=review_text,
        sections=sections,
        order_proposals=extract_order_proposals(monthly_text),
        sox_decision=extract_sox_decision(sections.get("sox_decision", "")),
        portfolio_diagnosis=extract_bullets(sections.get("portfolio_diagnosis", "")),
        rule_review=extract_bullets(sections.get("rule_review", "")),
        must=must,
        should=should,
        nice_to_have=nice_to_have,
        parser_warnings=parser_warnings,
    )


def split_sections(review_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {name: [] for name in SECTION_HEADINGS}
    current: str | None = None
    for raw_line in review_text.splitlines():
        line = raw_line.rstrip()
        heading = detect_heading(line)
        if heading is not None:
            current = heading
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def detect_heading(line: str) -> str | None:
    normalized = line.strip().lstrip("#").strip()
    normalized = normalized.strip("【】").strip()
    for canonical_name, candidates in SECTION_HEADINGS.items():
        for candidate in candidates:
            if normalized.startswith(candidate):
                return canonical_name
    return None


def extract_order_proposals(section_text: str) -> list[ReviewOrderProposal]:
    proposals: list[ReviewOrderProposal] = []
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith(("-", "*")):
            continue
        symbol_match = re.search(r"\b([A-Z][A-Z0-9_]{1,})\b", line)
        if not symbol_match:
            continue
        symbol = symbol_match.group(1)
        shares_match = re.search(r"(\d+)\s*(?:株|shares?)", line, flags=re.IGNORECASE)
        recommended_shares = int(shares_match.group(1)) if shares_match else None

        price_match = re.search(
            r"(?:指値|価格|price|@|:)\s*([0-9]+(?:\.[0-9]+)?)\s*(USD|JPY)?",
            line,
            flags=re.IGNORECASE,
        )
        if price_match is None:
            all_numbers = re.findall(r"[0-9]+(?:\.[0-9]+)?", line)
            recommended_price = to_optional_decimal(all_numbers[0]) if all_numbers else None
        else:
            recommended_price = to_optional_decimal(price_match.group(1))

        reason = line
        if "理由" in line:
            reason = line.split("理由", maxsplit=1)[-1].lstrip(" :：")
        proposals.append(
            ReviewOrderProposal(
                symbol=symbol,
                recommended_price=recommended_price,
                recommended_shares=recommended_shares,
                reason=reason.strip(),
            )
        )
    return proposals


def extract_sox_decision(section_text: str) -> str | None:
    normalized = section_text.replace(" ", "")
    if "買わない" in normalized or "見送り" in normalized:
        return "買わない"
    if "買う" in normalized:
        return "買う"
    return None


def extract_priority_lists(section_text: str) -> tuple[list[str], list[str], list[str]]:
    buckets = {"must": [], "should": [], "nice_to_have": []}
    current_bucket: str | None = None
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower().replace(" ", "")
        for bucket in buckets:
            if lowered.startswith(bucket):
                current_bucket = bucket
                remainder = re.split(r"[:：]", line, maxsplit=1)
                if len(remainder) > 1 and remainder[1].strip():
                    buckets[bucket].append(remainder[1].strip().lstrip("- ").strip())
                break
        else:
            if current_bucket is not None and line.startswith(("-", "*")):
                buckets[current_bucket].append(line.lstrip("-* ").strip())
    return buckets["must"], buckets["should"], buckets["nice_to_have"]


def extract_bullets(section_text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if line.startswith(("-", "*")):
            bullets.append(line.lstrip("-* ").strip())
    return bullets

