from __future__ import annotations

import re
from decimal import Decimal

from .models import MonthlyComputation, PortfolioWarning
from .portfolio_metrics import format_pct
from .utils import month_key


SELF_CONTAINED_HANDOFF_MODE = "self_contained_single_markdown"
UNRESOLVED_LOCAL_REFERENCE_RE = re.compile(
    r"(?i)(?:file://\S+|(?:^|[\s`\"'(])[^`\s\"']+\.csv\b)"
)


def render_chatgpt_prompt(computation: MonthlyComputation, template_text: str) -> str:
    snapshot = computation.snapshot
    resolved_buckets = computation.metadata.get("resolved_buckets", {})
    classification_audit = computation.metadata.get("classification_audit", [])
    classification_reason_map = {item["symbol"]: item.get("reason") for item in classification_audit}
    review_target_month = computation.metadata.get("review_target_month", month_key(snapshot.snapshot_date))
    rendered_template = (
        template_text.replace("{{REVIEW_TARGET_MONTH}}", review_target_month).replace(
            "{{REVIEW_TARGET_MONTH_JP}}",
            review_target_month_to_japanese_month(review_target_month),
        )
    )
    lines: list[str] = [
        rendered_template.strip(),
        "",
        "## 0. 自己完結ハンドオフ",
        f"- handoff_mode: {SELF_CONTAINED_HANDOFF_MODE}",
        "- external_files_required: false",
        "- normalized_snapshot: embedded_below",
        "- active_strategy: embedded_below",
        "- active_plans: embedded_below",
        "- recurring_contribution_observation: embedded_below",
        "- market_references: embedded_below",
        "- computed_metrics_and_warnings: embedded_below",
        "- このMarkdown本文だけをレビュー対象にすること",
        "- 添付ファイル、ローカルファイル、Project/GPTの参照ファイルを探さないこと",
        "- 外部表データの再アップロードを要求しないこと",
        "- 本文にない値は不明として扱い、ゼロや推測値で補完しないこと",
        "",
        "## 0-1. Active plan金額セマンティクス（最優先）",
    ]

    core_buy_materials = computation.core_buy_materials
    lines.extend(
        [
            f"- active_plan_basis_snapshot_date: {core_buy_materials.get('active_plan_basis_snapshot_date') or '-'}",
            f"- active_plan_basis_liquidity_jpy: {core_buy_materials.get('active_plan_basis_liquidity_jpy')}",
            f"- active_plan_basis_planned_amount_jpy: {core_buy_materials.get('active_plan_basis_planned_amount_jpy')}",
            f"- active_plan_current_snapshot_date: {core_buy_materials.get('active_plan_current_snapshot_date') or '-'}",
            f"- active_plan_current_recalculated_amount_jpy: {core_buy_materials.get('active_plan_current_recalculated_amount_jpy')}",
            f"- active_plan_amount_delta_jpy: {core_buy_materials.get('active_plan_amount_delta_jpy')}",
            f"- active_plan_amount_difference_expected: {str(bool(core_buy_materials.get('active_plan_amount_difference_expected'))).lower()}",
            f"- active_plan_historical_basis_must_not_be_overwritten: {str(bool(core_buy_materials.get('active_plan_historical_basis_must_not_be_overwritten'))).lower()}",
            "- basisは承認時の履歴値、current recalculated amountは今回スナップショットによる再計算値であり、同じ意味の重複フィールドではない",
            "- 基準日または現金が異なる場合の差は期待される。差だけを理由に不整合や統一対象と判定しない",
            "- 承認時のbasis値を現在値で上書きしない。今月はcurrent recalculated amountを実行前残高確認付きの計画額として扱う",
            "",
            "## 1. 前提",
        ]
    )

    lines.extend(
        [
            f"- snapshot_date: {snapshot.snapshot_date.isoformat()}",
            f"- review_target_month: {review_target_month}",
            f"- currency_base: {snapshot.currency_base}",
            f"- total_assets_jpy: {snapshot.total_assets_jpy}",
            f"- liquidity_target_jpy: {snapshot.liquidity_target_jpy or 'null'}",
            f"- active_strategy_id: {computation.strategy_summary.get('strategy_id') or '-'}",
            f"- strategy_effective_from: {computation.strategy_summary.get('effective_from') or '-'}",
            f"- active_plan_ids: {computation.strategy_summary.get('active_plan_ids') or []}",
            f"- holdings_count: {len(snapshot.holdings)}",
            "- source_role_snapshot: observed_fact",
            "- source_role_active_strategy: approved_policy",
            "- source_role_active_plan: approved_pending_execution",
            "- source_role_candidate_orders: proposal_only",
            "- source_role_recurring_contributions: observed_setting",
            "- 取引実績、承認済み計画、分析上の提案を相互に読み替えないこと",
            "- スナップショットは Money Forward スクリーンショットを一次情報として Codex が OCR・正規化したものとして扱うこと",
            "- ChatGPT は Money Forward スクリーンショットの読取や OCR を担当しないこと。画像読取は Codex 側で完了済みとして扱い、このプロンプト内の構造化データだけをレビューすること",
            "- Money Forward から貼り付けられたテキストがある場合でも、それは補助情報であり、HTML由来でレイアウト・列・階層・並び順が崩れている可能性がある",
            "- OCR・正規化・前月差分の検証警告は後続の警告一覧に含めているため、投資レビューでは警告を前提条件として扱うこと",
            "- 給与で通常生活費300,000円/月と本人分住宅ローン74,171円/月を賄っており、日常生活費に投資資産の売却を前提としていない",
            "- 給与収入額と毎月の正確な余剰額は未記録であり、推測で補完しないこと",
            "- 住宅ローンはペアローンの世帯当初借入額64,900,000円、本人当初借入額32,450,000円、年1.120%としてリスク評価に含めること。これらは現在残高ではない",
            "- 現在の住宅ローン残高が本文に明示されていない場合は不明とし、当初借入額を現在残高と表現しないこと",
            f"- 半導体エクスポージャ(Direct): {format_pct(computation.exposure_breakdown.get('direct_semiconductor_exposure_pct'))}",
            f"- AIインフラ感応度(Indirect): {format_pct(computation.exposure_breakdown.get('indirect_ai_infra_exposure_pct'))}",
            "- 指値設定は前月末または当月初に実施しうるため、snapshot_date が月末でも翌月の指値設定として解釈してよい",
            "- 指値設定基準値は先月平均ではなく、スクリプト実行時点から直近20営業日（約1ヶ月）の終値平均を使う",
        ]
    )

    lines.extend(["", "## 2. この月の snapshot 要約"])
    lines.extend(build_portfolio_summary(snapshot.holdings, resolved_buckets, classification_reason_map))

    lines.extend(["", "## 3. 現在戦略に基づく資産配分"])
    lines.extend(build_bucket_allocation_table(computation.strategy_allocations))

    lines.extend(["", "## 3-1. 互換用の旧バケット内訳（目標値として使用しない）"])
    lines.extend(build_bucket_allocation_table(computation.bucket_allocations))

    lines.extend(["", "## 4. 対象銘柄ごとの候補"])
    lines.extend(build_candidate_table(computation.candidate_orders))

    lines.extend(["", "## 5. コア定額買い判定材料"])
    lines.extend(build_core_buy_materials(computation.core_buy_materials))

    lines.extend(["", "## 5-1. Coreスポット買い判断材料"])
    lines.extend(build_core_spot_buy_materials(computation.metadata.get("core_spot_buy_materials", {})))

    lines.extend(["", "## 5-2. Core積立設定（毎月固定）"])
    lines.extend(
        build_core_recurring_contributions(
            computation.metadata.get("core_recurring_contributions", {}),
            include_legacy_policy=not bool(
                computation.strategy_summary.get("active_plan_ids")
            ),
        )
    )

    lines.extend(["", "## 5-3. iDeCo積立設定（毎月固定）"])
    lines.extend(build_pension_monthly_dca(computation.metadata.get("core_recurring_contributions", {})))

    lines.extend(["", "## 5-4. 暗号資産積立設定（毎週固定）"])
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
            "- 今月の core スポット買い執行額",
            "- コア / サテライトの優先順位",
            "- SOXの判定",
            "- ルール改善の要否",
            "- 『今月何をする月か』が一目で分かる内容にする",
            "",
            "【今月のcoreスポット買い提案】",
            "- このセクションは毎回必須とする",
            "- 今月の推奨スポット買い総額を、JPY の単一具体額で最初に明示すること",
            "- 承認済みactive planがある場合は、その計画額と実行前残高確認条件を優先し、別の金額を作らないこと",
            "- `多めに` `厚めに` `数十万円` `50〜100万円` のような曖昧表現は禁止",
            "- 定期積立額とcoreスポット買い提案額は別項目として明示し、合算値には内訳を付けること",
            "- 承認済みactive planは計画であって取引実績ではない。注文済み・約定済みと表現しないこと",
            "- active planの商品、配分、口座、execution_method、実行前確認条件を優先し、別案を作らないこと",
            "- broad core不足と未配分現金の是正時も、承認済み趣味枠現金1,000,000円は維持すること",
            "- 根拠のない月650,000円の現金流入を計算や提案に使わないこと",
            "- 配分先内訳を明示すること",
            "- active_plan_execution_method がある場合はその実行方法をそのまま明示すること",
            "- 判断根拠は `相場面` / `ポートフォリオ歪み` / `流動性水準` を分けて書くこと",
            "- その判断が `ルール上の判断` か `今月の裁量判断` かを分離すること",
            "- broad market core 商品を優先し、むやみに新規商品を増やさないこと",
            "- 新規のbroad core購入は、承認済み戦略どおり全世界株式100%とすること",
            "- 既存S&P500は強制売却しないが、通常の新規購入先にはしないこと",
            "- 証券注文、送金、Calendar登録を実行したと表現しないこと",
            "- 債券や低リスク商品を提案してもよいが、core equity のスポット買い額は必ず別途提示すること",
            "- `積立しているからスポット買いは不要` とは結論しないこと",
            "",
            "【今月の指値提案】",
            "- この『今月』は review_target_month を指す。snapshot_date が前月末でも、対象月を取り違えないこと",
            "- 各銘柄について 0段以上の任意段数で提案してよい",
            "- 0段の場合は『今月は見送り』と明記する",
            "- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する",
            "- Python 候補より段数を増やした場合も、その理由を明記する",
            "- 承認済みcore計画の資金を削ってまでテーマ銘柄を買わないこと",
            "- 直接半導体比率が15%を超える間は通常買い増しを行わず、20%超ではリバランスを人間へ提案すること",
            "- 高ボラ単一銘柄は5%を通常上限、8%超をリバランス提案閾値として扱うこと",
            "- MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先すること",
            "- 指値設定基準値はスクリプト実行時点から直近20営業日（約1ヶ月）の終値平均ベースとして扱うこと",
            "- 指値を提案する各段で、直近20営業日（約1ヶ月）の終値平均の実数値を必ず明示すること",
            "- 指値を提案する各段で、その指値が直近20営業日終値平均から何%下かを必ず明示すること",
            "- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` で計算し、マイナス値で表記すること",
            "- 推奨フォーマット例: `指値 450.00 USD（20営業日平均 500.00 USD, 平均比 -10.0%）`",
            "- 減段理由テンプレートの例: `ルール上の判断: bucket_over_target のため浅い段を見送る`",
            "- 減段理由テンプレートの例: `今月の裁量判断: core 補強を優先するため段数を減らす`",
            "",
            "【コア定額買い方針レビュー】",
            "- コアは今月最低いくら買うべきか",
            "- 安ければ追加でどの程度厚くする考え方が妥当か",
            "- コアとサテライトの資金配分優先順位",
            "- 既存の毎月固定積立（Core積立設定）を前提に評価すること",
            "- `plans/recurring/`由来の観測済み積立設定を前提にし、active planの商品配分や取引実績とは分けること",
            "- 積立設定が大きくても、それだけでスポット買い免除にしないこと",
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
            "- iDeCoのオルカン月次積立55,000円はpensionとして前提にし、tradable coreとは分けて評価すること",
            "- 暗号資産の週次積立（BTC/ETH）を前提に、維持/減額/停止の要否を明示すること",
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
            "- must は現行source of truthとの矛盾、算術誤り、危険な外部書込み、またはレビュー出力へ実害がある機械的不整合に限定すること",
            "- 現行source of truthにない新しい運用・安全・ガバナンス方針はshouldの四半期提案とし、承認済み計画を遡及的に無効化しないこと",
            "",
            "【Codex向け修正要約】",
            "- このセクションの本文全体を、必ず単一の ```md コードブロックで出力すること",
            "- コードブロック外に Codex向け修正要約を書かないこと",
            "- 問題がない場合でもコードブロックは省略せず、`must: なし` のように明記すること",
            "- must / should / nice_to_have は空欄不可だが、該当なしの場合は `なし` と書いてよい",
            "- 新規生成物の反映先は `reports/generated/` とし、不変履歴や過去生成物の書換えを依頼しないこと",
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
            "- 現行戦略と生成物の整合性を維持する",
            "",
            "変更すべき仕様:",
            "- 新規生成物は reports/generated に限定する",
            "- data/history と prompts/generated は不変履歴として扱う",
            "",
            "影響範囲:",
            "- reports/generated/",
            "",
            "推奨テスト:",
            "- repository-audit と関連テストを実行する",
            "```",
        ]
    )

    lines.extend(
        [
            "",
            "## 13. 必須の月次・四半期レビュー観点",
            "- 毎月の運用レビューと四半期ごとのルール変更レビューを分離して評価してください。",
            "- 指値設定は前月末または当月初に実施されるため、snapshot_date が月末なら翌月の指値設定として扱ってください。",
            "- 四半期ルール見直しセクションには、月次の執行判断を混ぜないでください。",
            "- 半導体エクスポージャの合算管理が妥当か確認してください。",
            "- PLTR の浅い押し目候補抑制ロジックの是非を評価してください。",
            "- 指値段数は各銘柄 0段以上の任意とし、1段しか出さない場合はその理由を明記してください。",
            "- 指値を出す場合は、各段で直近20営業日（約1ヶ月）の終値平均と平均比の乖離率を併記してください。",
            "- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` に基づくマイナス値で記述してください。",
            "- コアについては『毎月一定額買う / 安ければ追加で厚く買う』という運用思想の妥当性も評価してください。",
            "- 承認済みactive planがある場合は、確認済み利用可能現金から趣味枠現金1,000,000円を控除した額を提示してください。",
            "- 金額はその月の portfolio 歪み、相場状況、流動性水準で変動してよいです。",
            "- 定期積立は観測済み設定、active planは承認済み未実行計画として分離してください。",
            "- 税制、NISA枠、商品仕様を判断に使う場合は公式一次情報の参照日とURLを示してください。",
            "- iDeCo55,000円/月とBTC/ETH週次積立は、承認済み現金再配分計画とは別の継続キャッシュアウトとして表示してください。",
            "- coreスポット買いの提案が rule-based なのか discretionary なのかを明示してください。",
            "- cash_excess_pct が大きいほど、core スポット買い額を増やしてください。",
            "- core_delta_pct が大きいほど、core スポット買い額を増やしてください。",
            "- broad market ベースで明確に下落している月は、core スポット買い額を増やしてください。",
            "- 高値圏でも cash_excess と core不足が大きい場合は、一定額は必ず実行してください。",
            "- 互換用の旧バケットを現行戦略の目標値として使わず、broad_core不足是正を優先してください。",
            "- 既存の broad market core 商品を優先し、新規商品追加は最小限にしてください。",
            "- 債券や低リスク商品を提案する場合でも、core equity スポット買い額そのものは別で必ず提示してください。",
            "- `全部債券` `全部現金維持` は不可です。",
            "- 大口支出情報は未記録として扱い、存在を推測しないでください。",
            "- 給与で通常生活費と本人分住宅ローンを賄えている一方、給与額と毎月余剰額は未記録として扱ってください。",
            "- 住宅ローンは世帯当初借入64,900,000円、本人当初借入32,450,000円、年1.120%、返済初期である点を考慮してください。当初借入額を現在残高と表現しないでください。",
            "- 上記不動産保有により、日本国内不動産セクターへの実質的なエクスポージャが既にある前提で配分やリスクを評価してください。",
            "- Core積立設定（毎月固定）は既に実行される前提として扱い、同じ強化提案の反復は避けてください。",
            "- ただし長期シナリオ悪化やリスク管理上の妥当性がある場合は、固定積立の減額・停止提案を明示してください。",
            "- iDeCoのオルカン月次積立55,000円はpensionとして既に実行される前提で扱い、tradable coreとは分けて評価してください。",
            "- 暗号資産の週次積立（BTC/ETH）も既に実行される前提で扱い、必要時のみ変更提案してください。",
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
            "- 新規生成物は reports/generated/ に限定し、不変履歴の書換えを依頼しないでください。",
            "- monthly review と quarterly rule review を分けて整理してください。",
            "- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。",
            "",
            "## 15. 回答前の必須acceptance check",
            "- 外部ファイル名、添付状況、取得失敗、再アップロード案内が最終回答にない",
            "- active planのbasis値とcurrent recalculated amountの差を、基準日差を無視して不整合や統一対象にしていない",
            "- 現行source of truthにない新しい方針をmustへ入れたり、承認済み計画へ遡及適用したりしていない",
            "- 住宅ローンの当初借入額を現在残高と表現していない",
            "- 定期積立の変更提案には現行戦略の商品名を正確に記載し、ユーザー確認前に変更済みと表現していない",
            "- Webの各主張は、それを直接支える公式一次情報へ重複なしでリンクし、事実と推論を分離している",
            "- 【Codex向け修正要約】のコードブロックを閉じた後に何も追記していない",
            "- 上記を満たさない場合は、回答を送信せず修正してから再点検する",
            "",
            f"指値設定対象月キー: {review_target_month}",
        ]
    )
    prompt = "\n".join(lines).strip() + "\n"
    validate_self_contained_prompt(prompt)
    return prompt


def validate_self_contained_prompt(prompt: str) -> None:
    required_markers = (
        f"handoff_mode: {SELF_CONTAINED_HANDOFF_MODE}",
        "external_files_required: false",
        "normalized_snapshot: embedded_below",
        "active_strategy: embedded_below",
        "active_plans: embedded_below",
        "market_references: embedded_below",
        "active_plan_amount_difference_expected:",
        "active_plan_historical_basis_must_not_be_overwritten:",
        "## 15. 回答前の必須acceptance check",
    )
    missing = [marker for marker in required_markers if marker not in prompt]
    if missing:
        raise ValueError(
            "Self-contained review prompt is missing embedded-source markers: "
            + ", ".join(missing)
        )
    unresolved = UNRESOLVED_LOCAL_REFERENCE_RE.findall(prompt)
    if unresolved:
        raise ValueError(
            "Self-contained review prompt contains unresolved local references: "
            + ", ".join(item.strip() for item in unresolved)
        )


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
        optional_parts = []
        if getattr(holding, "source_category", None):
            optional_parts.append(f"source_category={holding.source_category}")
        if getattr(holding, "institution", None):
            optional_parts.append(f"institution={holding.institution}")
        if getattr(holding, "account_type", None):
            optional_parts.append(f"account_type={holding.account_type}")
        if getattr(holding, "profit_loss_jpy", None) is not None:
            optional_parts.append(f"profit_loss_jpy={holding.profit_loss_jpy}")
        if getattr(holding, "notes", None):
            optional_parts.append(f"notes={normalize_text(holding.notes)}")
        optional_text = f" | {' | '.join(optional_parts)}" if optional_parts else ""
        lines.append(
            "- "
            f"{holding.symbol} | {bucket_label} | value_jpy={holding.market_value_jpy} | "
            f"price={holding.current_price if holding.current_price is not None else 'null'} | "
            f"quantity={holding.quantity if holding.quantity is not None else 'null'}"
            f"{optional_text}"
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
        "| symbol | bucket | current_price | snapshot_price_source_date | market_candidate_price_source_date | base_price | avg20_base_price | drawdown_rule | limit_price | avg20_gap_pct | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt | explanation |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for candidate in candidate_orders:
        lines.append(
            f"| {candidate.symbol} | {candidate.bucket} | {format_value(candidate.current_price)} | "
            f"{format_value(getattr(candidate, 'snapshot_price_source_date', None))} | "
            f"{format_value(getattr(candidate, 'market_candidate_price_source_date', None))} | "
            f"{format_value(candidate.base_price)} | {format_value(candidate.avg20_base_price)} | "
            f"{candidate.drawdown_rule} | {format_value(candidate.limit_price)} | {format_value(candidate.avg20_gap_pct)} | "
            f"{candidate.shares} | {format_value(candidate.estimated_cost_jpy)} | "
            f"{'yes' if candidate.suppressed else 'no'} | {candidate.suppressed_reason_code or '-'} | "
            f"{candidate.suppressed_reason_text or '-'} | {candidate.note_for_chatgpt or '-'} | "
            f"{normalize_text(str(candidate.explanation) if candidate.explanation else '-')} |"
        )
    availability_notes = build_candidate_availability_notes(candidate_orders)
    if availability_notes:
        lines.extend(["", "Candidate availability notes:"])
        lines.extend(availability_notes)
    return lines


def build_candidate_availability_notes(candidate_orders: list) -> list[str]:
    notes: list[str] = []
    symbols = sorted({candidate.symbol for candidate in candidate_orders})
    for symbol in symbols:
        symbol_candidates = [candidate for candidate in candidate_orders if candidate.symbol == symbol]
        if not symbol_candidates:
            continue
        has_eligible = any(not candidate.suppressed for candidate in symbol_candidates)
        has_bucket_over_target_suppression = any(
            candidate.suppressed_reason_code == "bucket_over_target_shallow_suppressed"
            for candidate in symbol_candidates
        )
        has_deep_candidate = any(
            "deep_drawdown_candidate" in (candidate.note_for_chatgpt or "")
            for candidate in symbol_candidates
        )
        if has_eligible or not has_bucket_over_target_suppression or has_deep_candidate:
            continue
        notes.append(
            f"- {symbol}: 今月は eligible deep candidate なし。"
            "bucket over target のため浅い候補は suppressed され、設定済み候補に deep threshold 以下の段がありません。"
        )
    return notes


def build_core_buy_materials(core_buy_materials: dict) -> list[str]:
    lines = [
        f"- strategy_id: {core_buy_materials.get('strategy_id') or '-'}",
        f"- active_plan_id: {core_buy_materials.get('active_plan_id') or '-'}",
        f"- active_plan_status: {core_buy_materials.get('active_plan_status') or '-'}",
        f"- active_plan_account_type: {core_buy_materials.get('active_plan_account_type') or '-'}",
        f"- active_plan_execution_amount_rule: {core_buy_materials.get('active_plan_execution_amount_rule') or '-'}",
        f"- active_plan_target_group: {core_buy_materials.get('active_plan_target_group') or '-'}",
        f"- active_plan_product: {core_buy_materials.get('active_plan_product') or '-'}",
        f"- active_plan_product_allocation_pct: {format_numeric_pct(core_buy_materials.get('active_plan_product_allocation_pct'))}",
        f"- active_plan_execution_method: {core_buy_materials.get('active_plan_execution_method') or '-'}",
        f"- active_plan_requires_pretrade_balance_confirmation: {core_buy_materials.get('active_plan_requires_pretrade_balance_confirmation')}",
        f"- active_plan_user_executes_order_manually: {core_buy_materials.get('active_plan_user_executes_order_manually')}",
        f"- active_plan_basis_snapshot_date: {core_buy_materials.get('active_plan_basis_snapshot_date') or '-'}",
        f"- active_plan_basis_liquidity_jpy: {core_buy_materials.get('active_plan_basis_liquidity_jpy')}",
        f"- active_plan_basis_planned_amount_jpy: {core_buy_materials.get('active_plan_basis_planned_amount_jpy')}",
        f"- active_plan_current_snapshot_date: {core_buy_materials.get('active_plan_current_snapshot_date') or '-'}",
        f"- active_plan_current_recalculated_amount_jpy: {core_buy_materials.get('active_plan_current_recalculated_amount_jpy')}",
        f"- active_plan_amount_delta_jpy: {core_buy_materials.get('active_plan_amount_delta_jpy')}",
        f"- active_plan_amount_difference_expected: {str(bool(core_buy_materials.get('active_plan_amount_difference_expected'))).lower()}",
        f"- active_plan_historical_basis_must_not_be_overwritten: {str(bool(core_buy_materials.get('active_plan_historical_basis_must_not_be_overwritten'))).lower()}",
        f"- core_actual_pct: {format_pct(core_buy_materials.get('core_actual_pct'))}",
        f"- core_target_pct: {format_pct(core_buy_materials.get('core_target_pct'))}",
        f"- core_delta_pct: {format_pct(core_buy_materials.get('core_delta_pct'))}",
        f"- liquidity_actual_pct: {format_pct(core_buy_materials.get('liquidity_actual_pct'))}",
        f"- liquidity_target_pct: {format_pct(core_buy_materials.get('liquidity_target_pct'))}",
        f"- cash_excess_pct: {format_pct(core_buy_materials.get('cash_excess_pct'))}",
        f"- unallocated_liquidity_jpy: {core_buy_materials.get('unallocated_liquidity_jpy')}",
        f"- reserved_hobby_cash_jpy: {core_buy_materials.get('reserved_hobby_cash_jpy')}",
        f"- core_bucket_total_jpy: {core_buy_materials.get('core_bucket_total_jpy')}",
        f"- monthly_core_budget_policy: {core_buy_materials.get('monthly_core_budget_policy')}",
        f"- monthly_core_buy_budget_min_jpy: {core_buy_materials.get('monthly_core_buy_budget_min_jpy')}",
        f"- monthly_core_buy_budget_max_jpy: {core_buy_materials.get('monthly_core_buy_budget_max_jpy')}",
        f"- monthly_core_budget_tier: {core_buy_materials.get('monthly_core_budget_tier')}",
        f"- monthly_core_budget_band: {core_buy_materials.get('monthly_core_budget_band')}",
        f"- recommended_monthly_core_buy_budget_jpy: {core_buy_materials.get('recommended_monthly_core_buy_budget_jpy')}",
        f"- monthly_core_budget_override_active: {core_buy_materials.get('monthly_core_budget_override_active')}",
        f"- monthly_core_budget_override_reason: {core_buy_materials.get('monthly_core_budget_override_reason') or '-'}",
        f"- portfolio_management_mode: {core_buy_materials.get('portfolio_management_mode')}",
        f"- rebalance_mode_active: {core_buy_materials.get('rebalance_mode_active')}",
        f"- rebalance_mode_reason: {core_buy_materials.get('rebalance_mode_reason') or '-'}",
        f"- date_based_core_budget_override_active: {core_buy_materials.get('date_based_core_budget_override_active')}",
        f"- nisa_growth_quota_status: {core_buy_materials.get('nisa_growth_quota_status')}",
        f"- taxable_core_spot_buy_required: {core_buy_materials.get('taxable_core_spot_buy_required')}",
        f"- core_spot_buy_account_type: {core_buy_materials.get('core_spot_buy_account_type') or '-'}",
        f"- fixed_core_auto_invest_jpy: {core_buy_materials.get('fixed_core_auto_invest_jpy')}",
        f"- baseline_total_core_deployment_target_jpy: {core_buy_materials.get('baseline_total_core_deployment_target_jpy')}",
        f"- baseline_core_spot_buy_jpy: {core_buy_materials.get('baseline_core_spot_buy_jpy')}",
        f"- hard_cap_core_spot_buy_jpy: {core_buy_materials.get('hard_cap_core_spot_buy_jpy')}",
        f"- spot_buy_bands: {core_buy_materials.get('spot_buy_bands')}",
        f"- satellite_interaction_policy: {core_buy_materials.get('satellite_interaction_policy')}",
        f"- core_budget_explanation: {core_buy_materials.get('explanation')}",
        "| symbol | quantity | value_jpy | current_price | reference_symbol | suggested_proxy_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |",
        "| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in core_buy_materials.get("core_constituents", []):
        lines.append(
            f"| {item['symbol']} | {format_value(item['quantity'])} | {item['value_jpy']} | "
            f"{format_value(item['current_price'])} | {item['reference_symbol'] or '-'} | "
            f"{item.get('suggested_proxy_symbol') or '-'} | "
            f"{format_value(item['reference_current_price'])} | {format_value(item['recent_high_21d'])} | "
            f"{format_value(item['recent_high_63d'])} | {format_value(item['drawdown_pct_from_recent_high'])} |"
        )
    return lines


def build_core_spot_buy_materials(spot_buy_materials: dict) -> list[str]:
    lines = [
        f"- strategy_id: {spot_buy_materials.get('strategy_id') or '-'}",
        f"- active_plan_id: {spot_buy_materials.get('active_plan_id') or '-'}",
        f"- active_plan_status: {spot_buy_materials.get('active_plan_status') or '-'}",
        f"- active_plan_account_type: {spot_buy_materials.get('active_plan_account_type') or '-'}",
        f"- active_plan_execution_amount_rule: {spot_buy_materials.get('active_plan_execution_amount_rule') or '-'}",
        f"- active_plan_target_group: {spot_buy_materials.get('active_plan_target_group') or '-'}",
        f"- active_plan_product: {spot_buy_materials.get('active_plan_product') or '-'}",
        f"- active_plan_product_allocation_pct: {format_numeric_pct(spot_buy_materials.get('active_plan_product_allocation_pct'))}",
        f"- active_plan_execution_method: {spot_buy_materials.get('active_plan_execution_method') or '-'}",
        f"- active_plan_requires_pretrade_balance_confirmation: {spot_buy_materials.get('active_plan_requires_pretrade_balance_confirmation')}",
        f"- active_plan_user_executes_order_manually: {spot_buy_materials.get('active_plan_user_executes_order_manually')}",
        f"- broad_core_actual_pct: {format_pct(spot_buy_materials.get('broad_core_actual_pct'))}",
        f"- broad_core_target_pct: {format_pct(spot_buy_materials.get('broad_core_target_pct'))}",
        f"- active_hobby_actual_pct: {format_pct(spot_buy_materials.get('active_hobby_actual_pct'))}",
        f"- active_hobby_target_pct: {format_pct(spot_buy_materials.get('active_hobby_target_pct'))}",
        f"- reserved_hobby_cash_jpy: {spot_buy_materials.get('reserved_hobby_cash_jpy')}",
        f"- unallocated_liquidity_jpy: {spot_buy_materials.get('unallocated_liquidity_jpy')}",
        f"- liquidity_actual_pct: {format_pct(spot_buy_materials.get('liquidity_actual_pct'))}",
        f"- liquidity_target_pct: {format_pct(spot_buy_materials.get('liquidity_target_pct'))}",
        f"- cash_excess_pct: {format_pct(spot_buy_materials.get('cash_excess_pct'))}",
        f"- core_actual_pct: {format_pct(spot_buy_materials.get('core_actual_pct'))}",
        f"- core_target_pct: {format_pct(spot_buy_materials.get('core_target_pct'))}",
        f"- core_delta_pct: {format_pct(spot_buy_materials.get('core_delta_pct'))}",
        f"- jun_core_actual_pct: {format_pct(spot_buy_materials.get('jun_core_actual_pct'))}",
        f"- jun_core_target_pct: {format_pct(spot_buy_materials.get('jun_core_target_pct'))}",
        f"- jun_core_delta_pct: {format_pct(spot_buy_materials.get('jun_core_delta_pct'))}",
        f"- nisa_growth_quota_status: {spot_buy_materials.get('nisa_growth_quota_status')}",
        f"- nisa_exhaustion_adjustment_reason: {spot_buy_materials.get('nisa_exhaustion_adjustment_reason') or '-'}",
        f"- taxable_core_spot_buy_required: {spot_buy_materials.get('taxable_core_spot_buy_required')}",
        f"- account_type: {spot_buy_materials.get('core_spot_buy_account_type') or '-'}",
        f"- taxable_account_note: {spot_buy_materials.get('taxable_account_note') or '-'}",
        f"- tax_note: {spot_buy_materials.get('tax_note') or '-'}",
        f"- fixed_core_auto_invest_amount_jpy: {spot_buy_materials.get('fixed_core_auto_invest_amount_jpy')}",
        f"- current_monthly_core_auto_invest_amount_jpy: {spot_buy_materials.get('current_monthly_core_auto_invest_amount_jpy')}",
        f"- annualized_core_auto_invest_amount_jpy: {spot_buy_materials.get('annualized_core_auto_invest_amount_jpy')}",
        f"- recommended_taxable_core_spot_buy_jpy: {spot_buy_materials.get('recommended_taxable_core_spot_buy_jpy')}",
        f"- recommended_monthly_core_buy_budget_jpy: {spot_buy_materials.get('recommended_monthly_core_buy_budget_jpy')}",
        f"- total_monthly_core_deployment_jpy: {spot_buy_materials.get('total_monthly_core_deployment_jpy')}",
        f"- baseline_total_core_deployment_target_jpy: {spot_buy_materials.get('baseline_total_core_deployment_target_jpy')}",
        f"- baseline_core_spot_buy_jpy: {spot_buy_materials.get('baseline_core_spot_buy_jpy')}",
        f"- hard_cap_core_spot_buy_jpy: {spot_buy_materials.get('hard_cap_core_spot_buy_jpy')}",
        f"- monthly_core_budget_band: {spot_buy_materials.get('monthly_core_budget_band')}",
        f"- spot_buy_bands: {spot_buy_materials.get('spot_buy_bands')}",
        f"- core_spot_buy_allocation_rule: {spot_buy_materials.get('core_spot_buy_allocation_rule')}",
        f"- date_based_override_active: {spot_buy_materials.get('date_based_override_active')}",
        f"- active_date_based_override: {spot_buy_materials.get('active_date_based_override') or '-'}",
        f"- configuration_warnings: {spot_buy_materials.get('configuration_warnings') or []}",
        f"- current_cash_jpy: {spot_buy_materials.get('current_cash_jpy')}",
        f"- bond_like_holdings_present: {spot_buy_materials.get('bond_like_holdings_present')}",
        f"- bond_like_holdings: {spot_buy_materials.get('bond_like_holdings')}",
        f"- emergency_fund_managed_separately: {spot_buy_materials.get('emergency_fund_managed_separately')}",
        f"- near_term_large_expense: {spot_buy_materials.get('near_term_large_expense')}",
        f"- real_estate_exposure_present: {spot_buy_materials.get('real_estate_exposure_present')}",
        f"- real_estate_use: {spot_buy_materials.get('real_estate_use')}",
        f"- mortgage_status: {spot_buy_materials.get('mortgage_status')}",
        f"- liquidity_comment: {spot_buy_materials.get('liquidity_comment')}",
        "| reference_symbol | one_month_return_pct | three_month_return_pct | one_month_drawdown_from_high_pct | three_month_drawdown_from_high_pct |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    stats = spot_buy_materials.get("major_core_proxy_stats", [])
    if not stats:
        lines.append("| - | null | null | null | null |")
    for item in stats:
        lines.append(
            f"| {item.get('reference_symbol', '-')} | {format_value(item.get('one_month_return_pct'))} | "
            f"{format_value(item.get('three_month_return_pct'))} | "
            f"{format_value(item.get('one_month_drawdown_from_high_pct'))} | "
            f"{format_value(item.get('three_month_drawdown_from_high_pct'))} |"
        )
    lines.append("- portfolio_risk_bucket_summary:")
    for item in spot_buy_materials.get("portfolio_risk_bucket_summary", []):
        lines.append(
            f"  - {item.get('bucket')}: actual_pct={format_pct(item.get('actual_pct'))}, "
            f"target_pct={format_pct(item.get('target_pct'))}, delta_pct={format_pct(item.get('delta_pct'))}"
        )
    return lines


def build_core_recurring_contributions(
    recurring_config: dict,
    *,
    include_legacy_policy: bool = True,
) -> list[str]:
    plans = recurring_config.get("plans", [])
    lines = [
        "- source_role: observed_setting",
        f"- total_monthly_jpy: {recurring_config.get('total_monthly_jpy', 'null')}",
        f"- monthly_core_auto_invest_amount_jpy: {recurring_config.get('monthly_core_auto_invest_amount_jpy', recurring_config.get('total_monthly_jpy', 'null'))}",
        f"- nisa_growth_quota_status: {recurring_config.get('nisa_growth_quota_status')}",
        f"- configuration_warnings: {recurring_config.get('configuration_warnings') or []}",
        "| day_of_month | fund_name | amount_jpy | settlement_type | account_type | distribution_course |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    if include_legacy_policy:
        lines[4:4] = [
            f"- taxable_core_spot_buy_required: {recurring_config.get('taxable_core_spot_buy_required', False)}",
            f"- core_spot_buy_account_type: {recurring_config.get('core_spot_buy_account_type') or '-'}",
            f"- date_based_override_active: {recurring_config.get('date_based_override_active')}",
            f"- active_date_based_override: {recurring_config.get('active_date_based_override') or '-'}",
            f"- taxable_account_note: {recurring_config.get('taxable_account_note') or '-'}",
            f"- tax_note: {recurring_config.get('tax_note') or '-'}",
            f"- nisa_exhaustion_adjustment_reason: {recurring_config.get('nisa_exhaustion_adjustment_reason') or '-'}",
            f"- baseline_total_core_deployment_target_jpy: {recurring_config.get('baseline_total_core_deployment_target_jpy')}",
            f"- rebalance_mode_core_spot_buy_reference_jpy: {recurring_config.get('rebalance_mode_core_spot_buy_reference_jpy')}",
        ]
    if not plans:
        lines.append("| - | - | - | - | - | - |")
    for plan in plans:
        lines.append(
            f"| {plan.get('day_of_month', '-')} | {plan.get('fund_name', '-')} | {plan.get('amount_jpy', '-')} | "
            f"{plan.get('settlement_type', '-')} | {plan.get('account_type', '-')} | {plan.get('distribution_course', '-')} |"
        )

    guidance = (
        recurring_config.get("review_guidance", [])
        if include_legacy_policy
        else [
            "この設定はplans/recurring由来の観測済み設定であり、取引実績ではない",
            "証券会社での変更確認までは、実際に変更・停止・約定したとみなさない",
            "承認済み現金再配分計画の商品配分や実行額とは分離して評価する",
        ]
    )
    if guidance:
        lines.append("- review_guidance:")
        for item in guidance:
            lines.append(f"  - {item}")
    return lines


def build_pension_monthly_dca(recurring_config: dict) -> list[str]:
    plans = recurring_config.get("pension_monthly_dca", [])
    lines = [
        f"- pension_monthly_dca_total_jpy: {recurring_config.get('pension_monthly_dca_total_jpy', 'null')}",
        f"- annualized_pension_dca_jpy: {recurring_config.get('annualized_pension_dca_jpy', 'null')}",
        f"- annualized_pension_dca_pct_of_total_assets: {format_pct(recurring_config.get('annualized_pension_dca_pct_of_total_assets'))}",
        "| symbol | fund_name | amount_jpy_per_month | account_type | asset_class |",
        "| --- | --- | ---: | --- | --- |",
    ]
    if not plans:
        lines.append("| - | - | - | - | - |")
    for plan in plans:
        lines.append(
            f"| {plan.get('symbol', '-')} | {plan.get('fund_name', '-')} | "
            f"{plan.get('amount_jpy_per_month', '-')} | {plan.get('account_type', '-')} | "
            f"{plan.get('asset_class', '-')} |"
        )

    guidance = recurring_config.get("pension_review_guidance", [])
    if guidance:
        lines.append("- pension_review_guidance:")
        for item in guidance:
            lines.append(f"  - {item}")
    return lines


def build_crypto_weekly_dca(recurring_config: dict) -> list[str]:
    plans = recurring_config.get("crypto_weekly_dca", [])
    lines = [
        f"- crypto_weekly_dca_total_jpy: {recurring_config.get('crypto_weekly_dca_total_jpy', 'null')}",
        f"- annualized_crypto_dca_jpy: {recurring_config.get('annualized_crypto_dca_jpy', 'null')}",
        f"- annualized_crypto_dca_pct_of_total_assets: {format_pct(recurring_config.get('annualized_crypto_dca_pct_of_total_assets'))}",
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
        f"- routine_additions_allowed: {sox_buy_signal.get('routine_additions_allowed')}",
        f"- rebalance_proposal_required: {sox_buy_signal.get('rebalance_proposal_required')}",
        f"- semiconductor_preferred_max_pct: {format_pct(sox_buy_signal.get('semiconductor_preferred_max_pct'))}",
        f"- semiconductor_rebalance_proposal_above_pct: {format_pct(sox_buy_signal.get('semiconductor_rebalance_proposal_above_pct'))}",
        f"- monthly_buy_budget_jpy: {sox_buy_signal.get('monthly_buy_budget_jpy')}",
        f"- related_bucket_actual_pct: {format_pct(sox_buy_signal.get('related_bucket_actual_pct'))}",
        f"- related_bucket_target_pct: {format_pct(sox_buy_signal.get('related_bucket_target_pct'))}",
        f"- semiconductor_exposure_total_pct: {format_pct(sox_buy_signal.get('semiconductor_exposure_total_pct'))}",
        f"- priority_lowered_boolean: {sox_buy_signal.get('priority_lowered_boolean')}",
        f"- priority_lowered_reason: {sox_buy_signal.get('priority_lowered_reason') or '-'}",
        f"- explanation: {sox_buy_signal.get('explanation')}",
    ]


def build_exposure_breakdown(exposure_breakdown: dict) -> list[str]:
    lines = [
        f"- direct_cap_monitor_pct: {format_pct(exposure_breakdown.get('direct_semiconductor_exposure_pct'))}",
        f"- direct_cap_monitor_jpy: {exposure_breakdown.get('direct_semiconductor_exposure_jpy')}",
        f"- direct_plus_indirect_watch_metric_pct: {format_pct(exposure_breakdown.get('combined_semiconductor_ai_infra_watch_pct'))}",
        f"- direct_plus_indirect_watch_metric_jpy: {exposure_breakdown.get('combined_semiconductor_ai_infra_watch_jpy')}",
        f"- direct_semiconductor_exposure_pct: {format_pct(exposure_breakdown.get('direct_semiconductor_exposure_pct'))}",
        f"- indirect_ai_infra_exposure_pct: {format_pct(exposure_breakdown.get('indirect_ai_infra_exposure_pct'))}",
        f"- indirect_ai_infra_exposure_jpy: {exposure_breakdown.get('indirect_ai_infra_exposure_jpy')}",
        f"- combined_semiconductor_ai_infra_watch_pct: {format_pct(exposure_breakdown.get('combined_semiconductor_ai_infra_watch_pct'))}",
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
    raw_cash_normalization = quarterly.get("cash_normalization_months_estimate")
    cash_normalization = raw_cash_normalization if isinstance(raw_cash_normalization, dict) else {}
    return [
        "- strategy_context:",
        f"  - strategy_id: {computation.strategy_summary.get('strategy_id')}",
        f"  - effective_from: {computation.strategy_summary.get('effective_from')}",
        f"  - active_plan_ids: {computation.strategy_summary.get('active_plan_ids')}",
        f"  - reserved_hobby_cash_jpy: {computation.strategy_summary.get('reserved_hobby_cash_jpy')}",
        f"  - unallocated_liquidity_jpy: {computation.strategy_summary.get('unallocated_liquidity_jpy')}",
        "- monthly_execution_outputs:",
        "  - source_role: calculated_review_material_not_transaction_record",
        f"  - review_target_month: {monthly.get('review_target_month')}",
        f"  - nisa_growth_quota_status: {monthly.get('nisa_growth_quota_status')}",
        f"  - fixed_core_auto_invest_amount_jpy: {monthly.get('fixed_core_auto_invest_amount_jpy')}",
        f"  - taxable_core_spot_buy_required: {monthly.get('taxable_core_spot_buy_required')}",
        f"  - recommended_taxable_core_spot_buy_jpy: {monthly.get('recommended_taxable_core_spot_buy_jpy')}",
        f"  - core_spot_buy_account_type: {monthly.get('core_spot_buy_account_type') or '-'}",
        f"  - portfolio_management_mode: {monthly.get('portfolio_management_mode')}",
        f"  - monthly_core_budget_tier: {monthly.get('monthly_core_budget_tier')}",
        f"  - recommended_monthly_core_buy_budget_jpy: {monthly.get('recommended_monthly_core_buy_budget_jpy')}",
        f"  - monthly_total_core_deployment_jpy: {monthly.get('monthly_total_core_deployment_jpy')}",
        f"  - candidate_count: {monthly.get('candidate_count')}",
        f"  - pension_monthly_dca_total_jpy: {monthly.get('pension_monthly_dca_total_jpy')}",
        f"  - annualized_pension_dca_jpy: {monthly.get('annualized_pension_dca_jpy')}",
        f"  - annualized_pension_dca_pct_of_total_assets: {format_pct(monthly.get('annualized_pension_dca_pct_of_total_assets'))}",
        f"  - crypto_weekly_dca_total_jpy: {monthly.get('crypto_weekly_dca_total_jpy')}",
        f"  - annualized_crypto_dca_jpy: {monthly.get('annualized_crypto_dca_jpy')}",
        f"  - annualized_crypto_dca_pct_of_total_assets: {format_pct(monthly.get('annualized_crypto_dca_pct_of_total_assets'))}",
        f"  - taxable_account_note: {monthly.get('taxable_account_note') or '-'}",
        f"  - nisa_exhaustion_adjustment_reason: {monthly.get('nisa_exhaustion_adjustment_reason') or '-'}",
        "- quarterly_rule_review_outputs:",
        f"  - no_change: {quarterly.get('no_change')}",
        f"  - classification_override_count: {quarterly.get('classification_override_count')}",
        f"  - core_reference_missing_symbols: {quarterly.get('core_reference_missing_symbols')}",
        f"  - core_reference_proxy_suggestions: {quarterly.get('core_reference_proxy_suggestions')}",
        f"  - tradable_core_pct: {format_pct(quarterly.get('tradable_core_pct'))}",
        f"  - effective_core_including_pension_pct: {format_pct(quarterly.get('effective_core_including_pension_pct'))}",
        "  - cash_normalization_months_estimate:",
        f"    - gross_deployment_months: {cash_normalization.get('gross_deployment_months')}",
        f"    - net_cash_reduction_months: {cash_normalization.get('net_cash_reduction_months')}",
        f"    - assumed_monthly_cash_inflow_jpy: {cash_normalization.get('assumed_monthly_cash_inflow_jpy')}",
        f"    - net_cash_reduction_jpy: {cash_normalization.get('net_cash_reduction_jpy')}",
        f"  - direct_cap_monitor_pct: {format_pct(quarterly.get('direct_semiconductor_exposure_pct'))}",
        f"  - direct_plus_indirect_watch_metric_pct: {format_pct(quarterly.get('combined_semiconductor_ai_infra_watch_pct'))}",
        f"  - direct_semiconductor_exposure_pct: {format_pct(quarterly.get('direct_semiconductor_exposure_pct'))}",
        f"  - combined_semiconductor_ai_infra_watch_pct: {format_pct(quarterly.get('combined_semiconductor_ai_infra_watch_pct'))}",
        f"  - indirect_ai_infra_exposure_pct: {format_pct(quarterly.get('indirect_ai_infra_exposure_pct'))}",
    ]


def build_long_term_thesis_targets_table(long_term_thesis_targets: list[dict]) -> list[str]:
    if not long_term_thesis_targets:
        return ["- 対象銘柄はありません"]

    lines = [
        "| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | thesis_status | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in long_term_thesis_targets:
        key_risks = item.get("key_risk_if_thesis_breaks", [])
        lines.append(
            f"| {item['symbol']} | {item['bucket']} | {item['current_value_jpy']} | "
            f"{format_pct(item['portfolio_pct'])} | {item['thesis_id']} | {item.get('thesis_status')} | "
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


def format_numeric_pct(value) -> str:
    if value is None:
        return "null"
    return format_pct(Decimal(str(value)))


def normalize_text(value: str | None) -> str:
    if not value:
        return "-"
    return " ".join(str(value).split())


def review_target_month_to_japanese_month(review_target_month: str) -> str:
    month = int(review_target_month.split("_")[1])
    return f"{month}月"
