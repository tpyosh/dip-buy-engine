from __future__ import annotations

from .models import MonthlyComputation, PortfolioWarning
from .portfolio_metrics import format_pct
from .utils import month_key


def render_chatgpt_prompt(computation: MonthlyComputation, template_text: str) -> str:
    lines: list[str] = [template_text.strip(), "", "## 1. 前提"]
    snapshot = computation.snapshot
    resolved_buckets = computation.metadata.get("resolved_buckets", {})
    classification_audit = computation.metadata.get("classification_audit", [])
    classification_reason_map = {item["symbol"]: item.get("reason") for item in classification_audit}

    lines.extend(
        [
            f"- snapshot_date: {snapshot.snapshot_date.isoformat()}",
            f"- currency_base: {snapshot.currency_base}",
            f"- total_assets_jpy: {snapshot.total_assets_jpy}",
            f"- liquidity_target_jpy: {snapshot.liquidity_target_jpy or 'null'}",
            f"- holdings_count: {len(snapshot.holdings)}",
            f"- 半導体エクスポージャ(Direct): {format_pct(computation.exposure_breakdown.get('direct_semiconductor_exposure_pct'))}",
            f"- AIインフラ感応度(Indirect): {format_pct(computation.exposure_breakdown.get('indirect_ai_infra_exposure_pct'))}",
        ]
    )

    lines.extend(["", "## 2. この月の snapshot 要約"])
    lines.extend(build_portfolio_summary(snapshot.holdings, resolved_buckets, classification_reason_map))

    lines.extend(["", "## 3. 現在の資産配分"])
    lines.extend(build_bucket_allocation_table(computation.bucket_allocations))

    lines.extend(["", "## 4. 対象銘柄ごとの候補"])
    lines.extend(build_candidate_table(computation.candidate_orders))

    lines.extend(["", "## 5. コア定額買い判定材料"])
    lines.extend(build_core_buy_materials(computation.core_buy_materials))

    lines.extend(["", "## 5-2. Core積立設定（毎月固定）"])
    lines.extend(build_core_recurring_contributions(computation.metadata.get("core_recurring_contributions", {})))

    lines.extend(["", "## 5-3. 暗号資産積立設定（毎週固定）"])
    lines.extend(build_crypto_weekly_dca(computation.metadata.get("core_recurring_contributions", {})))

    lines.extend(["", "## 6. SOX 判定材料"])
    lines.extend(build_sox_materials(computation.sox_buy_signal))

    lines.extend(["", "## 7. 半導体エクスポージャ内訳"])
    lines.extend(build_exposure_breakdown(computation.exposure_breakdown))

    lines.extend(["", "## 8. 長期シナリオ点検対象"])
    lines.extend(build_long_term_thesis_targets_table(computation.long_term_thesis_targets))

    lines.extend(["", "## 9. ChatGPTへの長期シナリオレビュー依頼"])
    lines.extend(build_long_term_review_request())

    lines.extend(["", "## 10. 警告一覧"])
    lines.extend(build_validation_warnings(computation.warnings))

    lines.extend(
        [
            "",
            "## 11. 生成ロジック上の分離データ",
        ]
    )
    lines.extend(build_review_partition_section(computation))

    lines.extend(
        [
            "",
            "## 12. ChatGPT に期待する出力形式",
            "以下の見出しを維持してください。",
            "月次の執行判断と、四半期単位のルール見直し提案は明確に分離してください。",
            "月次の注文判断・資金配分判断を、四半期ルール見直しセクションに混ぜないでください。",
            "【要約】",
            "- 3〜6行程度で短くまとめる",
            "- 今月の最重要判断",
            "- コア / サテライトの優先順位",
            "- SOXの判定",
            "- ルール改善の要否",
            "- 『今月何をする月か』が一目で分かる内容にする",
            "",
            "【今月の指値提案】",
            "- 各銘柄について 0段以上の任意段数で提案してよい",
            "- 0段の場合は『今月は見送り』と明記する",
            "- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する",
            "- Python 候補より段数を増やした場合も、その理由を明記する",
            "- 減段理由テンプレートの例: `ルール上の判断: bucket_over_target のため浅い段を見送る`",
            "- 減段理由テンプレートの例: `今月の裁量判断: core 補強を優先するため段数を減らす`",
            "",
            "【コア定額買い方針レビュー】",
            "- コアは今月最低いくら買うべきか",
            "- 安ければ追加でどの程度厚くする考え方が妥当か",
            "- コアとサテライトの資金配分優先順位",
            "- 既存の毎月固定積立（Core積立設定）を前提に評価すること",
            "- 固定積立を維持するか、減額/停止すべきかを明示すること（必要な場合のみ）",
            "- ルール上の判断と今月の裁量判断を分けて説明すること",
            "",
            "【SOX投信判定】",
            "- 買う / 買わない",
            "- 理由",
            "",
            "【ポートフォリオ診断】",
            "- 現在の偏り",
            "- 注意点",
            "- 今月の補強優先順位",
            "- 暗号資産の週次積立（BTC/ETH/XRP）を前提に、維持/減額/停止の要否を明示すること",
            "",
            "【長期シナリオレビュー】",
            "- 対象銘柄ごとに、現在の長期仮説に大きな変化があるかを書く",
            "- Webで確認した主要事実と、そこからの推論を分けて書く",
            "- 判定区分は `継続保有でよい` / `要監視` / `仮説弱化` を使う",
            "- 売却を即断せず、なぜその判定にしたかを書く",
            "- 大きな変化が見当たらない場合は『大きな変化なし』と簡潔に書く",
            "",
            "【四半期ルール見直し】",
            "- このセクションでは、四半期単位で見直すべき構造的なルール変更だけを書くこと",
            "- 月次の執行判断、今月の注文可否、今月だけの資金配分判断はここに混ぜないこと",
            "- 維持してよいルール / 改善した方がよいルール / 追加した方がよい制約 / スクリプト修正が望ましい点を整理すること",
            "- 改善提案は、明確な問題・矛盾・欠落・ノイズ・仕様不足がある場合のみ挙げること",
            "- 大きな問題がない場合は『大きなルール変更提案なし』と明記してよい",
            "- ハルシネーション防止のため、推測で問題点や改善案を作らないこと",
            "- must には月次判断に実害があるものだけを入れること",
            "",
            "【Codex向け修正要約】",
            "- このセクションの本文全体を、必ず単一の ```md コードブロックで出力すること",
            "- コードブロック外に Codex向け修正要約を書かないこと",
            "- 問題がない場合でもコードブロックは省略せず、`must: なし` のように明記すること",
            "- must / should / nice_to_have は空欄不可だが、該当なしの場合は `なし` と書いてよい",
            "- 出力例:",
            "```md",
            "must:",
            "- なし",
            "",
            "should:",
            "- なし",
            "",
            "nice_to_have:",
            "- なし",
            "",
            "修正目的:",
            "- 大きな修正提案なし",
            "",
            "変更すべき仕様:",
            "- なし",
            "",
            "影響範囲:",
            "- なし",
            "",
            "推奨テスト:",
            "- なし",
            "```",
        ]
    )

    lines.extend(
        [
            "",
            "## 13. 必須の月次・四半期レビュー観点",
            "- 毎月の運用レビューと四半期ごとのルール変更レビューを分離して評価してください。",
            "- 四半期ルール見直しセクションには、月次の執行判断を混ぜないでください。",
            "- 半導体エクスポージャの合算管理が妥当か確認してください。",
            "- PLTR の浅い押し目候補抑制ロジックの是非を評価してください。",
            "- 指値段数は各銘柄 0段以上の任意とし、1段しか出さない場合はその理由を明記してください。",
            "- コアについては『毎月一定額買う / 安ければ追加で厚く買う』という運用思想の妥当性も評価してください。",
            "- Core積立設定（毎月固定）は既に実行される前提として扱い、同じ強化提案の反復は避けてください。",
            "- ただし長期シナリオ悪化やリスク管理上の妥当性がある場合は、固定積立の減額・停止提案を明示してください。",
            "- 暗号資産の週次積立（BTC/ETH/XRP）も既に実行される前提で扱い、必要時のみ変更提案してください。",
            "- コア不足と現金過多が同時発生している場合、押し目買いルール設計に問題がないかもレビューしてください。",
            "- 中長期投資前提のため、短期トレンドやテクニカル悪化を売却理由にしない前提でレビューしてください。",
            "- ただし、長期シナリオ・政策前提・技術前提・競争優位の前提が崩れた可能性がある場合は、その有無をWebベースで点検してください。",
            "- 大きな変化が見当たらない場合は、無理に懸念を作らず『大きな変化なし』としてください。",
            "- 事実と推論を分けて記述してください。",
            "- 大きな問題がない場合は、無理に改善提案を作らないでください。",
            "- ハルシネーション防止のため、明確な根拠がある改善提案のみを挙げてください。",
            "- must / should / nice_to_have は空欄不可ですが、該当なしの場合は `なし` と明記してください。",
            "- Codex向け修正要約は必ず md コードブロックで出力してください。",
            "- ルール改善が不要な場合は、その旨を明記してください。",
            "",
            "## 14. 必須の Codex 向け修正要約観点",
            "- must / should / nice_to_have は必ず埋めてください。",
            "- 空欄は不可ですが、該当なしの場合は `なし` と明記してください。",
            "- 【Codex向け修正要約】 全体を単一の ```md コードブロックで出力してください。",
            "- monthly review と quarterly rule review を分けて整理してください。",
            "- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。",
            "",
            f"月次キー: {month_key(snapshot.snapshot_date)}",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_portfolio_summary(
    holdings: list,
    resolved_buckets: dict[str, str],
    classification_reason_map: dict[str, str | None],
) -> list[str]:
    lines: list[str] = []
    for holding in holdings:
        effective_bucket = resolved_buckets.get(holding.symbol, holding.asset_class)
        bucket_label = effective_bucket
        if effective_bucket != holding.asset_class:
            reason = classification_reason_map.get(holding.symbol, "-")
            bucket_label = f"{effective_bucket} (raw={holding.asset_class}, reason={reason})"
        lines.append(
            "- "
            f"{holding.symbol} | {bucket_label} | value_jpy={holding.market_value_jpy} | "
            f"price={holding.current_price if holding.current_price is not None else 'null'} | "
            f"quantity={holding.quantity if holding.quantity is not None else 'null'}"
        )
    return lines


def build_bucket_allocation_table(bucket_allocations: list) -> list[str]:
    lines = [
        "| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for allocation in bucket_allocations:
        lines.append(
            f"| {allocation.bucket} | {allocation.market_value_jpy} | {format_pct(allocation.actual_pct)} | "
            f"{format_pct(allocation.target_pct) if allocation.target_pct is not None else '-'} | "
            f"{format_pct(allocation.delta_pct) if allocation.delta_pct is not None else '-'} |"
        )
    return lines


def build_candidate_table(candidate_orders: list) -> list[str]:
    lines = [
        "| symbol | bucket | current_price | base_price | drawdown_rule | limit_price | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for candidate in candidate_orders:
        lines.append(
            f"| {candidate.symbol} | {candidate.bucket} | {format_value(candidate.current_price)} | "
            f"{format_value(candidate.base_price)} | {candidate.drawdown_rule} | {format_value(candidate.limit_price)} | "
            f"{candidate.shares} | {format_value(candidate.estimated_cost_jpy)} | "
            f"{'yes' if candidate.suppressed else 'no'} | {candidate.suppressed_reason_code or '-'} | "
            f"{candidate.suppressed_reason_text or '-'} | {candidate.note_for_chatgpt or '-'} |"
        )
    return lines


def build_core_buy_materials(core_buy_materials: dict) -> list[str]:
    lines = [
        f"- core_actual_pct: {format_pct(core_buy_materials.get('core_actual_pct'))}",
        f"- core_target_pct: {format_pct(core_buy_materials.get('core_target_pct'))}",
        f"- core_delta_pct: {format_pct(core_buy_materials.get('core_delta_pct'))}",
        f"- liquidity_actual_pct: {format_pct(core_buy_materials.get('liquidity_actual_pct'))}",
        f"- liquidity_target_pct: {format_pct(core_buy_materials.get('liquidity_target_pct'))}",
        f"- cash_excess_pct: {format_pct(core_buy_materials.get('cash_excess_pct'))}",
        f"- core_bucket_total_jpy: {core_buy_materials.get('core_bucket_total_jpy')}",
        f"- monthly_core_budget_policy: {core_buy_materials.get('monthly_core_budget_policy')}",
        f"- monthly_core_buy_budget_min_jpy: {core_buy_materials.get('monthly_core_buy_budget_min_jpy')}",
        f"- monthly_core_buy_budget_max_jpy: {core_buy_materials.get('monthly_core_buy_budget_max_jpy')}",
        f"- monthly_core_budget_tier: {core_buy_materials.get('monthly_core_budget_tier')}",
        f"- recommended_monthly_core_buy_budget_jpy: {core_buy_materials.get('recommended_monthly_core_buy_budget_jpy')}",
        f"- monthly_core_budget_override_active: {core_buy_materials.get('monthly_core_budget_override_active')}",
        f"- monthly_core_budget_override_reason: {core_buy_materials.get('monthly_core_budget_override_reason') or '-'}",
        f"- portfolio_management_mode: {core_buy_materials.get('portfolio_management_mode')}",
        f"- rebalance_mode_active: {core_buy_materials.get('rebalance_mode_active')}",
        f"- rebalance_mode_reason: {core_buy_materials.get('rebalance_mode_reason') or '-'}",
        "| symbol | quantity | value_jpy | current_price | reference_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in core_buy_materials.get("core_constituents", []):
        lines.append(
            f"| {item['symbol']} | {format_value(item['quantity'])} | {item['value_jpy']} | "
            f"{format_value(item['current_price'])} | {item['reference_symbol'] or '-'} | "
            f"{format_value(item['reference_current_price'])} | {format_value(item['recent_high_21d'])} | "
            f"{format_value(item['recent_high_63d'])} | {format_value(item['drawdown_pct_from_recent_high'])} |"
        )
    return lines


def build_core_recurring_contributions(recurring_config: dict) -> list[str]:
    plans = recurring_config.get("plans", [])
    lines = [
        f"- total_monthly_jpy: {recurring_config.get('total_monthly_jpy', 'null')}",
        "| day_of_month | fund_name | amount_jpy | settlement_type | account_type | distribution_course |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    if not plans:
        lines.append("| - | - | - | - | - | - |")
    for plan in plans:
        lines.append(
            f"| {plan.get('day_of_month', '-')} | {plan.get('fund_name', '-')} | {plan.get('amount_jpy', '-')} | "
            f"{plan.get('settlement_type', '-')} | {plan.get('account_type', '-')} | {plan.get('distribution_course', '-')} |"
        )

    guidance = recurring_config.get("review_guidance", [])
    if guidance:
        lines.append("- review_guidance:")
        for item in guidance:
            lines.append(f"  - {item}")
    return lines


def build_crypto_weekly_dca(recurring_config: dict) -> list[str]:
    plans = recurring_config.get("crypto_weekly_dca", [])
    lines = [
        "| symbol | amount_jpy_per_week |",
        "| --- | ---: |",
    ]
    if not plans:
        lines.append("| - | - |")
    for plan in plans:
        lines.append(f"| {plan.get('symbol', '-')} | {plan.get('amount_jpy_per_week', '-')} |")

    guidance = recurring_config.get("crypto_review_guidance", [])
    if guidance:
        lines.append("- crypto_review_guidance:")
        for item in guidance:
            lines.append(f"  - {item}")
    return lines


def build_sox_materials(sox_buy_signal: dict) -> list[str]:
    return [
        f"- proxy_symbol: {sox_buy_signal.get('proxy_symbol')}",
        f"- current_price: {format_value(sox_buy_signal.get('current_price'))}",
        f"- recent_high_21d: {format_value(sox_buy_signal.get('recent_high_21d'))}",
        f"- recent_high_63d: {format_value(sox_buy_signal.get('recent_high_63d'))}",
        f"- drawdown_pct_from_21d_high: {format_value(sox_buy_signal.get('drawdown_pct_from_21d_high'))}",
        f"- drawdown_pct_from_63d_high: {format_value(sox_buy_signal.get('drawdown_pct_from_63d_high'))}",
        f"- buy_zone_rule_text: {sox_buy_signal.get('buy_zone_rule_text')}",
        f"- within_buy_zone_boolean: {sox_buy_signal.get('within_buy_zone_boolean')}",
        f"- near_boundary_boolean: {sox_buy_signal.get('near_boundary_boolean')}",
        f"- monthly_buy_budget_jpy: {sox_buy_signal.get('monthly_buy_budget_jpy')}",
        f"- related_bucket_actual_pct: {format_pct(sox_buy_signal.get('related_bucket_actual_pct'))}",
        f"- related_bucket_target_pct: {format_pct(sox_buy_signal.get('related_bucket_target_pct'))}",
        f"- semiconductor_exposure_total_pct: {format_pct(sox_buy_signal.get('semiconductor_exposure_total_pct'))}",
        f"- priority_lowered_boolean: {sox_buy_signal.get('priority_lowered_boolean')}",
        f"- priority_lowered_reason: {sox_buy_signal.get('priority_lowered_reason') or '-'}",
    ]


def build_exposure_breakdown(exposure_breakdown: dict) -> list[str]:
    lines = [
        f"- direct_semiconductor_exposure_pct: {format_pct(exposure_breakdown.get('direct_semiconductor_exposure_pct'))}",
        f"- direct_semiconductor_exposure_jpy: {exposure_breakdown.get('direct_semiconductor_exposure_jpy')}",
        f"- indirect_ai_infra_exposure_pct: {format_pct(exposure_breakdown.get('indirect_ai_infra_exposure_pct'))}",
        f"- indirect_ai_infra_exposure_jpy: {exposure_breakdown.get('indirect_ai_infra_exposure_jpy')}",
        "| symbol | value_jpy | bucket | exposure_type | in_direct | in_indirect | inclusion_reason |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for item in exposure_breakdown.get("breakdown", []):
        lines.append(
            f"| {item['symbol']} | {item['value_jpy']} | {item['bucket']} | {item['exposure_type']} | "
            f"{item['included_in_direct_semiconductor_exposure']} | "
            f"{item['included_in_indirect_ai_infra_exposure']} | "
            f"{item['inclusion_reason']} |"
        )
    return lines


def build_review_partition_section(computation: MonthlyComputation) -> list[str]:
    monthly = computation.monthly_execution_outputs or {}
    quarterly = computation.quarterly_rule_review_outputs or {}
    return [
        "- monthly_execution_outputs:",
        f"  - portfolio_management_mode: {monthly.get('portfolio_management_mode')}",
        f"  - monthly_core_budget_tier: {monthly.get('monthly_core_budget_tier')}",
        f"  - recommended_monthly_core_buy_budget_jpy: {monthly.get('recommended_monthly_core_buy_budget_jpy')}",
        f"  - candidate_count: {monthly.get('candidate_count')}",
        f"  - crypto_weekly_dca_total_jpy: {monthly.get('crypto_weekly_dca_total_jpy')}",
        "- quarterly_rule_review_outputs:",
        f"  - classification_override_count: {quarterly.get('classification_override_count')}",
        f"  - core_reference_missing_symbols: {quarterly.get('core_reference_missing_symbols')}",
        f"  - direct_semiconductor_exposure_pct: {format_pct(quarterly.get('direct_semiconductor_exposure_pct'))}",
        f"  - indirect_ai_infra_exposure_pct: {format_pct(quarterly.get('indirect_ai_infra_exposure_pct'))}",
    ]


def build_long_term_thesis_targets_table(long_term_thesis_targets: list[dict]) -> list[str]:
    if not long_term_thesis_targets:
        return ["- 対象銘柄はありません"]

    lines = [
        "| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for item in long_term_thesis_targets:
        key_risks = item.get("key_risk_if_thesis_breaks", [])
        lines.append(
            f"| {item['symbol']} | {item['bucket']} | {item['current_value_jpy']} | "
            f"{format_pct(item['portfolio_pct'])} | {item['thesis_id']} | "
            f"{normalize_text(item['long_term_thesis_summary'])} | {normalize_text('; '.join(key_risks))} | "
            f"{item['review_priority']} | {item['web_review_required']} |"
        )
    return lines


def build_long_term_review_request() -> list[str]:
    return [
        "- この投資方針は中長期前提であり、短期トレンドやテクニカル悪化だけでは売却判断しません。",
        "- ただし、長期の成長ストーリー・構造的需要シナリオ・政策前提・競争優位の前提が崩れた場合は再評価余地があります。",
        "- 上の対象銘柄について、最新のWeb情報を調査した上で、長期シナリオに変化がないかレビューしてください。",
        "- Webで確認した事実と、そこからの推論を分けて記述してください。",
        "- 価格やチャートではなく、事業 / 技術 / 政策 / 競争環境 / 需要構造の変化を主に見てください。",
        "- 大きな変化が見当たらない場合は、無理に懸念を捏造せず『大きな変化なし』としてください。",
        "- 根拠が弱い場合は『判断材料不足』と言ってかまいません。",
        "- 売却判断そのものを断定せず、`継続保有でよい` / `要監視` / `仮説弱化` の区分で返してください。",
        "- Web調査を使い、長期視点で判断してください。",
    ]


def build_validation_warnings(warnings: list[PortfolioWarning]) -> list[str]:
    if not warnings:
        return ["- warning はありません"]
    return [f"- [{warning.severity}] {warning.code}: {warning.message}" for warning in warnings]


def format_value(value) -> str:
    if value is None:
        return "null"
    return str(value)


def normalize_text(value: str | None) -> str:
    if not value:
        return "-"
    return " ".join(str(value).split())
