from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import MonthlyComputation
from .portfolio import format_pct
from .utils import month_key, quantize


def build_monthly_review_prompt(computation: MonthlyComputation, template_text: str) -> str:
    snapshot = computation.snapshot
    grouped_candidates: dict[str, list] = defaultdict(list)
    for candidate in computation.candidate_orders:
        grouped_candidates[candidate.symbol].append(candidate)

    lines: list[str] = [template_text.strip(), "", "## 1. 前提"]
    lines.extend(
        [
            f"- snapshot_date: {snapshot.snapshot_date.isoformat()}",
            f"- currency_base: {snapshot.currency_base}",
            f"- total_assets_jpy: {snapshot.total_assets_jpy}",
            f"- liquidity_target_jpy: {snapshot.liquidity_target_jpy or 'null'}",
            f"- holdings_count: {len(snapshot.holdings)}",
            f"- 半導体エクスポージャ: {format_pct(computation.semi_exposure_pct)}",
        ]
    )

    lines.extend(["", "## 2. この月の snapshot 要約"])
    for holding in snapshot.holdings:
        lines.append(
            "- "
            f"{holding.symbol} | {holding.asset_class} | value_jpy={holding.market_value_jpy} | "
            f"price={holding.current_price if holding.current_price is not None else 'null'} | "
            f"quantity={holding.quantity if holding.quantity is not None else 'null'}"
        )

    lines.extend(["", "## 3. 現在の資産配分", "| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |", "| --- | ---: | ---: | ---: | ---: |"])
    for allocation in computation.bucket_allocations:
        lines.append(
            f"| {allocation.bucket} | {allocation.market_value_jpy} | {format_pct(allocation.actual_pct)} | "
            f"{format_pct(allocation.target_pct) if allocation.target_pct is not None else '-'} | "
            f"{format_pct(allocation.delta_pct) if allocation.delta_pct is not None else '-'} |"
        )

    lines.extend(["", "## 4. 対象銘柄ごとの候補", "| symbol | current_price | base_price | drawdown_pct | limit_price | shares | est_cost_jpy | suppressed |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
    for symbol in sorted(grouped_candidates):
        for candidate in grouped_candidates[symbol]:
            suppression = ", ".join(candidate.suppression_reasons) if candidate.suppression_reasons else "-"
            lines.append(
                f"| {candidate.symbol} | {candidate.current_price} | {candidate.base_price} | "
                f"{candidate.drawdown_pct}% | {candidate.limit_price} | {candidate.shares} | "
                f"{candidate.estimated_cost_jpy if candidate.estimated_cost_jpy is not None else '-'} | "
                f"{'yes: ' + suppression if candidate.suppressed else 'no'} |"
            )

    sox = computation.sox_buy_signal
    lines.extend(
        [
            "",
            "## 5. SOX 判定材料",
            f"- proxy_symbol: {sox['proxy_symbol']}",
            f"- current_price: {sox['current_price']}",
            f"- recent_high_63d: {sox['recent_high_63d']}",
            f"- drawdown_pct: {sox['drawdown_pct']}%",
            f"- buy_zone: {sox['buy_zone_min_pct']}% to {sox['buy_zone_max_pct']}%",
            f"- within_buy_zone: {sox['within_buy_zone']}",
            f"- monthly_buy_budget_jpy: {sox['monthly_buy_budget_jpy']}",
        ]
    )

    lines.extend(["", "## 6. 警告一覧"])
    if computation.warnings:
        for warning in computation.warnings:
            lines.append(f"- [{warning.severity}] {warning.code}: {warning.message}")
    else:
        lines.append("- warning はありません")

    lines.extend(
        [
            "",
            "## 7. ChatGPT に期待する出力形式",
            "以下の見出しを維持してください。",
            "【今月の指値提案】",
            "- 銘柄ごとの推奨指値",
            "- 推奨株数",
            "- 提案理由",
            "",
            "【SOX投信判定】",
            "- 買う / 買わない",
            "- 理由",
            "",
            "【ポートフォリオ診断】",
            "- 現在の偏り",
            "- 注意点",
            "- 今月の補強優先順位",
            "",
            "【ルール改善レビュー】",
            "- 維持してよいルール",
            "- 改善した方がよいルール",
            "- 追加した方がよい制約",
            "- スクリプト修正が望ましい点",
            "",
            "【Codex向け修正要約】",
            "- must",
            "- should",
            "- nice_to_have",
            "- 修正目的",
            "- 変更すべき仕様",
            "- 影響範囲",
            "- 推奨テスト",
        ]
    )

    lines.extend(
        [
            "",
            "## 8. 必須のルール改善レビュー",
            "- 毎月の運用と四半期ごとのルール変更を分離してレビューしてください。",
            "- 半導体エクスポージャの合算管理が妥当か確認してください。",
            "- PLTR の浅い押し目候補抑制ロジックの是非も評価してください。",
            "",
            "## 9. 必須の Codex 向け修正要約",
            "- must / should / nice_to_have を必ず埋めてください。",
            "- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。",
            "",
            f"月次キー: {month_key(snapshot.snapshot_date)}",
        ]
    )
    return "\n".join(lines).strip() + "\n"

