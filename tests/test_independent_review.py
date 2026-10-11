from __future__ import annotations

import shutil
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from monthly_limit_order_review.cli import handle_monthly_run
from monthly_limit_order_review.independent_review import (
    build_independent_review_input,
    mark_review_superseded,
    render_independent_review,
    write_independent_review,
)
from monthly_limit_order_review.storage import load_yaml, write_yaml


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime(2026, 10, 11, 0, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
SNAPSHOT = "data/normalized/snapshot_2026_10.yaml"


@pytest.fixture
def review_repository(tmp_path: Path) -> Path:
    refs = [SNAPSHOT, "prompts/templates/independent_review_template.md"]
    for pointer_ref, path_key in [
        ("financial/current.yaml", "active_record_path"),
        ("holdings/current.yaml", "active_record_path"),
        ("strategy/current.yaml", "active_strategy_path"),
        ("plans/recurring/current.yaml", "active_record_path"),
    ]:
        refs.extend([pointer_ref, load_yaml(ROOT / pointer_ref)[path_key]])
    for ref in refs:
        destination = tmp_path / ref
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / ref, destination)
    return tmp_path


def build(root: Path) -> dict:
    return build_independent_review_input(root, root / SNAPSHOT, requested_at=STAMP)


def test_current_facts_and_user_directions_are_sufficient_without_history(review_repository: Path) -> None:
    root = review_repository
    payload = build(root)
    template = (root / "prompts/templates/independent_review_template.md").read_text()
    prompt = render_independent_review(payload, template)
    assert not (root / "transactions").exists()
    assert not (root / "strategy/theses").exists()
    assert not (root / "plans/2026").exists()
    assert payload["account_type_gate"] == {"status": "complete", "checked_holding_count": 14}
    assert payload["portfolio_snapshot"]["total_assets_jpy"] == 37695573
    assert len(payload["portfolio_snapshot"]["holdings"]) == 17
    assert "目的・生活上の制約・趣味の意向は守り" in prompt
    assert "配分・銘柄・上限は必要なら提案し直して" in prompt
    assert "{{" not in prompt
    assert "添付は不要" in prompt
    assert "統合の後、さらに別の依頼で" in prompt
    assert "過去の回答を参照させない" in prompt
    assert "inline_response_schema" not in prompt
    assert "固定乱数シード" not in prompt
    embedded = yaml.safe_load(prompt.split("```yaml\n", 1)[1].split("\n```", 1)[0])
    assert embedded == payload


def test_prior_advice_and_execution_changes_do_not_change_review_input(review_repository: Path) -> None:
    root = review_repository
    before = build(root)
    strategy_ref = load_yaml(root / "strategy/current.yaml")["active_strategy_path"]
    strategy = load_yaml(root / strategy_ref)
    strategy["approval_ref"] = "decisions/POISON_OLD_REVIEW.md"
    strategy["legacy_review_summary"] = "POISON_OLD_RECOMMENDATION"
    strategy["allocation"]["target_groups"]["active_hobby"]["target_components"] = {"POISON_OLD_SELECTION": 1}
    write_yaml(root / strategy_ref, strategy)
    metadata_ref = load_yaml(root / "holdings/current.yaml")["active_record_path"]
    metadata = load_yaml(root / metadata_ref)
    metadata["execution_context"] = {"old_plan": "POISON_OLD_TASK"}
    metadata["holdings"]["MSFT"]["execution_status"] = {"old_assessment": "POISON_OLD_VERDICT"}
    write_yaml(root / metadata_ref, metadata)
    raw = load_yaml(root / SNAPSHOT)
    raw["source_evidence"]["related_plan_ref"] = "POISON_PLAN.yaml"
    raw["normalization_notes"].append("POISON_HISTORY_SUMMARY")
    raw["candidate_orders"] = ["POISON_ORDER"]
    write_yaml(root / SNAPSHOT, raw)
    after = build(root)
    assert before == after
    assert "POISON" not in yaml.safe_dump(after)
    assert "active_plan" not in yaml.safe_dump(after)


def test_unknowns_and_conflicting_observations_are_preserved(review_repository: Path) -> None:
    payload = build(review_repository)
    holdings = {holding["symbol"]: holding for holding in payload["portfolio_snapshot"]["holdings"]}
    fund = holdings["RAKUTEN_PLUS_ALL_COUNTRY_1"]
    assert fund["quantity"] == 1162027
    assert fund["broker_observation"]["quantity"] == 1212957
    assert fund["acquired_on"] is None
    cash = holdings["LIQUIDITY"]
    assert cash["market_value_jpy"] == 2245005
    assert cash["broker_observation"]["jpy_deposit_jpy"] == 0
    assert "qty" not in fund


def test_missing_account_blocks_all_artifacts(review_repository: Path) -> None:
    root = review_repository
    raw = load_yaml(root / SNAPSHOT)
    for holding in raw["holdings"]:
        if holding["symbol"] == "PLTR":
            holding["symbol"] = "UNCLASSIFIED_SECURITY"
            holding["account_type"] = None
    write_yaml(root / SNAPSHOT, raw)
    output = root / "out/review_request.md"
    with pytest.raises(ValueError, match="blocked_missing_account_types"):
        write_independent_review(root, root / SNAPSHOT, output=output)
    assert not output.parent.exists()


def test_template_cannot_silently_omit_embedded_input(review_repository: Path) -> None:
    payload = build(review_repository)
    template = (review_repository / "prompts/templates/independent_review_template.md").read_text()
    with pytest.raises(ValueError, match="missing"):
        render_independent_review(payload, template.replace("{{REVIEW_INPUT_YAML}}", ""))


def test_artifacts_do_not_overwrite_and_superseding_preserves_prompt(review_repository: Path) -> None:
    root = review_repository
    old = write_independent_review(root, root / SNAPSHOT, output=root / "old/review_request.md")
    original = old.read_bytes()
    with pytest.raises(FileExistsError):
        write_independent_review(root, root / SNAPSHOT, output=old)
    assert original == old.read_bytes()
    new = write_independent_review(root, root / SNAPSHOT, output=root / "new/review_request.md")
    mark_review_superseded(old.parent, new)
    assert old.read_bytes() == original
    assert "再送しない" in old.with_name("README.md").read_text()


def test_monthly_alias_uses_fresh_generation_without_market_fetch(review_repository: Path, monkeypatch) -> None:
    root = review_repository
    monkeypatch.setattr("monthly_limit_order_review.cli.get_project_root", lambda: root)
    def forbidden(*args, **kwargs):
        raise AssertionError("Old monthly computation must not run")
    monkeypatch.setattr("monthly_limit_order_review.cli.compute_monthly", forbidden)
    result = handle_monthly_run(Namespace(snapshot=SNAPSHOT))
    assert result == 0
    assert len(list((root / "reports/generated/on_demand").glob("*/*/review_request.md"))) == 1
    assert not (root / "reports/generated/monthly").exists()


def test_duplicate_stable_ids_are_rejected(review_repository: Path) -> None:
    root = review_repository
    raw = load_yaml(root / SNAPSHOT)
    raw["holdings"][2]["symbol"] = raw["holdings"][1]["symbol"]
    write_yaml(root / SNAPSHOT, raw)
    with pytest.raises(ValueError, match="Duplicate holding symbols"):
        build(root)
