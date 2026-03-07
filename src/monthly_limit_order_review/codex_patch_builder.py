from __future__ import annotations

from collections import defaultdict

from .models import CodexPatchRequest, ProposalDiff, ReviewFeedback

KEYWORD_TARGETS = {
    "半導体": [
        "src/monthly_limit_order_review/portfolio.py",
        "config/portfolio_policy.yaml",
        "tests/test_portfolio.py",
    ],
    "PLTR": [
        "src/monthly_limit_order_review/rules.py",
        "src/monthly_limit_order_review/portfolio.py",
        "tests/test_rules.py",
        "tests/test_portfolio.py",
    ],
    "ルール": [
        "src/monthly_limit_order_review/rules.py",
        "config/buy_rules.yaml",
        "tests/test_rules.py",
    ],
    "プロンプト": [
        "src/monthly_limit_order_review/prompt_builder.py",
        "prompts/templates/monthly_review_template.md",
        "tests/test_prompt_builder.py",
    ],
    "Codex": [
        "src/monthly_limit_order_review/codex_patch_builder.py",
        "tests/test_codex_patch_builder.py",
    ],
    "差分": [
        "src/monthly_limit_order_review/diff_analyzer.py",
        "tests/test_diff_analyzer.py",
    ],
    "レビュー": [
        "src/monthly_limit_order_review/review_parser.py",
        "tests/test_review_parser.py",
    ],
    "CLI": [
        "src/monthly_limit_order_review/cli.py",
        "README.md",
    ],
}


def build_codex_patch_request(
    snapshot_month: str,
    review_feedback: ReviewFeedback,
    diffs: list[ProposalDiff],
) -> CodexPatchRequest:
    objectives = [
        "ChatGPT の改善提案を、既存の CLI 月次ワークフローを壊さずに反映する。",
        "Python 候補値と ChatGPT 提案との差分保存を継続しつつ、レビュー品質を高める。",
    ]
    prioritized_items = [
        ("must", item) for item in review_feedback.must
    ] + [
        ("should", item) for item in review_feedback.should
    ] + [
        ("nice_to_have", item) for item in review_feedback.nice_to_have
    ]

    target_files = infer_target_files(item for _, item in prioritized_items)
    spec_diffs = [f"{priority}: {item}" for priority, item in prioritized_items]
    if diffs:
        spec_diffs.extend(
            f"diff_observation: {diff.symbol} price_delta={diff.price_diff_pct if diff.price_diff_pct is not None else 'n/a'}"
            for diff in diffs
            if diff.price_diff_pct is not None or diff.candidate_removed
        )

    tests_to_update = infer_tests(target_files)
    backward_compatibility_notes = [
        "自動発注は追加しない。",
        "YAML 入力と CLI ベースの運用を維持する。",
        "既存の生成物パス規約を変更する場合は README とテストも更新する。",
    ]

    return CodexPatchRequest(
        snapshot_month=snapshot_month,
        must=review_feedback.must,
        should=review_feedback.should,
        nice_to_have=review_feedback.nice_to_have,
        objectives=objectives,
        target_files=target_files,
        spec_diffs=spec_diffs,
        tests_to_update=tests_to_update,
        backward_compatibility_notes=backward_compatibility_notes,
    )


def build_codex_patch_prompt(
    template_text: str,
    patch_request: CodexPatchRequest,
    diffs: list[ProposalDiff],
) -> str:
    lines: list[str] = [template_text.strip(), "", "現在の問題:"]
    if patch_request.spec_diffs:
        lines.extend(f"- {item}" for item in patch_request.spec_diffs)
    else:
        lines.append("- 改善提案の具体項目が不足しているため、レビュー抽出ロジックの見直しが必要です。")

    lines.extend(["", "修正目的:"])
    lines.extend(f"- {item}" for item in patch_request.objectives)

    lines.extend(["", "優先度別修正要求:"])
    lines.extend(_render_priority_block("must", patch_request.must))
    lines.extend(_render_priority_block("should", patch_request.should))
    lines.extend(_render_priority_block("nice_to_have", patch_request.nice_to_have))

    lines.extend(["", "修正対象ファイル:"])
    lines.extend(f"- {path}" for path in patch_request.target_files)

    lines.extend(["", "仕様差分:"])
    lines.extend(f"- {item}" for item in patch_request.spec_diffs)

    lines.extend(["", "追加 / 更新テスト:"])
    lines.extend(f"- {item}" for item in patch_request.tests_to_update)

    lines.extend(["", "後方互換性の注意点:"])
    lines.extend(f"- {item}" for item in patch_request.backward_compatibility_notes)

    if diffs:
        lines.extend(["", "Python 候補 vs ChatGPT 提案の差分:"])
        for diff in diffs:
            lines.append(
                "- "
                f"{diff.symbol}: python_price={diff.python_price} | chatgpt_price={diff.chatgpt_price} | "
                f"price_diff_pct={diff.price_diff_pct} | python_shares={diff.python_shares} | "
                f"chatgpt_shares={diff.chatgpt_shares} | removed={diff.candidate_removed}"
            )

    return "\n".join(lines).strip() + "\n"


def infer_target_files(items: list[str] | tuple[str, ...] | object) -> list[str]:
    resolved: set[str] = set()
    for item in items:
        for keyword, targets in KEYWORD_TARGETS.items():
            if keyword.lower() in item.lower():
                resolved.update(targets)
    if not resolved:
        resolved.update(
            {
                "src/monthly_limit_order_review/cli.py",
                "src/monthly_limit_order_review/prompt_builder.py",
                "src/monthly_limit_order_review/review_parser.py",
                "tests/test_prompt_builder.py",
                "tests/test_review_parser.py",
            }
        )
    return sorted(resolved)


def infer_tests(target_files: list[str]) -> list[str]:
    tests: set[str] = set(path for path in target_files if path.startswith("tests/"))
    for path in target_files:
        if path.endswith("/portfolio.py"):
            tests.add("tests/test_portfolio.py")
        if path.endswith("/rules.py"):
            tests.add("tests/test_rules.py")
        if path.endswith("/review_parser.py"):
            tests.add("tests/test_review_parser.py")
        if path.endswith("/diff_analyzer.py"):
            tests.add("tests/test_diff_analyzer.py")
        if path.endswith("/prompt_builder.py"):
            tests.add("tests/test_prompt_builder.py")
    return sorted(tests)


def _render_priority_block(priority: str, items: list[str]) -> list[str]:
    if not items:
        return [f"- {priority}: none"]
    rendered = [f"- {priority}:"]
    rendered.extend(f"  - {item}" for item in items)
    return rendered

