from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from .storage import load_yaml


class StrategyPolicyError(ValueError):
    """Raised when the current strategy pointer or policy is invalid."""


def load_current_strategy(project_root: Path) -> dict:
    return load_current_strategy_context(project_root)["strategy"]


def load_current_strategy_context(project_root: Path) -> dict:
    root = project_root.resolve()
    pointer_path = root / "strategy/current.yaml"
    pointer = load_yaml(pointer_path)

    active_strategy_path = pointer.get("active_strategy_path")
    if not active_strategy_path:
        raise StrategyPolicyError("strategy/current.yaml must define active_strategy_path")

    strategy_path = (root / str(active_strategy_path)).resolve()
    if not strategy_path.is_relative_to(root):
        raise StrategyPolicyError("active_strategy_path must stay within the repository")

    strategy = load_yaml(strategy_path)
    if pointer.get("active_strategy_id") != strategy.get("strategy_id"):
        raise StrategyPolicyError(
            "strategy/current.yaml active_strategy_id does not match the referenced strategy"
        )

    validate_strategy_policy(strategy)
    active_plans = [
        _load_repo_relative_yaml(root, path, field="active_plan_paths")
        for path in pointer.get("active_plan_paths", [])
    ]
    return {
        "pointer": pointer,
        "strategy": strategy,
        "active_plans": active_plans,
    }


def validate_strategy_policy(strategy: dict) -> None:
    errors: list[str] = []

    if strategy.get("status") != "active":
        errors.append("strategy status must be active")

    target_groups = strategy.get("allocation", {}).get("target_groups", {})
    if not target_groups:
        errors.append("allocation.target_groups must not be empty")
    else:
        target_sum = sum(
            (_decimal(group.get("target_pct"), f"{name}.target_pct", errors) for name, group in target_groups.items()),
            start=Decimal("0"),
        )
        if target_sum != Decimal("1"):
            errors.append(f"allocation target_pct values must sum to 1, got {target_sum}")

    broad_core = target_groups.get("broad_core", {})
    broad_target = _decimal(broad_core.get("target_pct"), "broad_core.target_pct", errors)
    broad_trigger = _decimal(
        broad_core.get("rebalance_proposal_below_pct"),
        "broad_core.rebalance_proposal_below_pct",
        errors,
    )
    if broad_trigger > broad_target:
        errors.append("broad_core rebalance trigger must be at or below target")

    active_hobby = target_groups.get("active_hobby", {})
    hobby_target = _decimal(active_hobby.get("target_pct"), "active_hobby.target_pct", errors)
    hobby_trigger = _decimal(
        active_hobby.get("rebalance_proposal_above_pct"),
        "active_hobby.rebalance_proposal_above_pct",
        errors,
    )
    if hobby_trigger < hobby_target:
        errors.append("active_hobby rebalance trigger must be at or above target")

    semiconductor = strategy.get("risk_limits", {}).get("direct_themes", {}).get("semiconductor", {})
    semi_preferred_max = _decimal(
        semiconductor.get("preferred_max_pct"),
        "semiconductor.preferred_max_pct",
        errors,
    )
    semi_trigger = _decimal(
        semiconductor.get("rebalance_proposal_above_pct"),
        "semiconductor.rebalance_proposal_above_pct",
        errors,
    )
    if semi_trigger < semi_preferred_max:
        errors.append("semiconductor rebalance trigger must be at or above preferred max")

    high_volatility = strategy.get("risk_limits", {}).get("high_volatility_single_security", {})
    high_vol_preferred_max = _decimal(
        high_volatility.get("preferred_max_pct"),
        "high_volatility_single_security.preferred_max_pct",
        errors,
    )
    high_vol_trigger = _decimal(
        high_volatility.get("rebalance_proposal_above_pct"),
        "high_volatility_single_security.rebalance_proposal_above_pct",
        errors,
    )
    if high_vol_trigger < high_vol_preferred_max:
        errors.append("high-volatility rebalance trigger must be at or above preferred max")

    approval_required = strategy.get("automation", {}).get("human_approval_required_for_all_trades")
    if approval_required is not True:
        errors.append("human approval must be required for all trades")

    if errors:
        raise StrategyPolicyError("; ".join(errors))


def _decimal(value, field: str, errors: list[str]) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        errors.append(f"{field} must be a decimal")
        return Decimal("0")
    if number < 0 or number > 1:
        errors.append(f"{field} must be between 0 and 1")
    return number


def _load_repo_relative_yaml(root: Path, relative_path: str, *, field: str) -> dict:
    path = (root / str(relative_path)).resolve()
    if not path.is_relative_to(root):
        raise StrategyPolicyError(f"{field} entries must stay within the repository")
    return load_yaml(path)
