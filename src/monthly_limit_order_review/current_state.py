from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal

from .models import Holding, PortfolioSnapshot


def build_current_state_projection(
    snapshot: PortfolioSnapshot,
    holding_metadata_record: dict,
    transaction_ledger: dict,
) -> tuple[PortfolioSnapshot, dict]:
    """Overlay confirmed post-snapshot full exits without rewriting history.

    Sale proceeds remain provisional until settlement and tax details are known.
    Unknown deductions are never silently converted to zero: the numeric amount is
    explicitly labelled as gross proceeds less *confirmed* deductions only.
    """

    projected = deepcopy(snapshot)
    metadata_by_symbol = holding_metadata_record.get("holdings", {})
    transactions = transaction_ledger.get("transactions", [])
    retained: list[Holding] = []
    adjustments: list[dict] = []
    warnings: list[str] = []
    proceeds_total = Decimal("0")
    removed_value_total = Decimal("0")
    aggregate_exit_transactions = {
        str(transaction.get("transaction_id")): transaction
        for transaction in transactions
        if _is_confirmed_post_snapshot_aggregate_exit(
            transaction,
            snapshot_date=snapshot.snapshot_date,
        )
    }
    aggregate_removed_symbols: dict[str, list[str]] = {
        transaction_id: [] for transaction_id in aggregate_exit_transactions
    }
    aggregate_removed_values: dict[str, Decimal] = {
        transaction_id: Decimal("0") for transaction_id in aggregate_exit_transactions
    }

    for holding in projected.holdings:
        aggregate_transaction_id = next(
            (
                transaction_id
                for transaction_id, transaction in aggregate_exit_transactions.items()
                if holding.symbol in transaction.get("symbols", [])
            ),
            None,
        )
        if aggregate_transaction_id is not None:
            removed_value_total += holding.market_value_jpy
            aggregate_removed_symbols[aggregate_transaction_id].append(holding.symbol)
            aggregate_removed_values[aggregate_transaction_id] += holding.market_value_jpy
            continue

        metadata = metadata_by_symbol.get(holding.symbol, {})
        execution = metadata.get("execution_status", {}) if isinstance(metadata, dict) else {}
        position_quantity = execution.get("position_quantity")
        execution_as_of = _optional_date(execution.get("as_of"))

        if (
            position_quantity != 0
            or execution_as_of is None
            or execution_as_of <= snapshot.snapshot_date
            or holding.quantity in (None, Decimal("0"))
        ):
            retained.append(holding)
            continue

        matching_sales = [
            transaction
            for transaction in transactions
            if _is_confirmed_post_snapshot_sale(
                transaction,
                symbol=holding.symbol,
                snapshot_date=snapshot.snapshot_date,
            )
        ]
        confirmed_sale_quantity = sum(
            (_decimal(transaction.get("quantity")) for transaction in matching_sales),
            start=Decimal("0"),
        )
        if confirmed_sale_quantity != holding.quantity:
            warnings.append(
                f"{holding.symbol}: latest metadata says exited, but confirmed post-snapshot "
                f"sale quantity {confirmed_sale_quantity} does not match snapshot quantity "
                f"{holding.quantity}; position was not projected."
            )
            retained.append(holding)
            continue

        has_confirmed_jpy_proceeds_basis = all(
            transaction.get("net_proceeds_jpy") is not None
            or transaction.get("gross_proceeds_jpy") is not None
            for transaction in matching_sales
        )
        gross_proceeds = sum(
            (_decimal(transaction.get("gross_proceeds_jpy")) for transaction in matching_sales),
            start=Decimal("0"),
        )
        confirmed_fees = sum(
            (
                _decimal(transaction.get("fee_jpy"))
                for transaction in matching_sales
                if transaction.get("fee_jpy") is not None
            ),
            start=Decimal("0"),
        )
        confirmed_taxes = sum(
            (
                _decimal(transaction.get("tax_jpy"))
                for transaction in matching_sales
                if transaction.get("tax_jpy") is not None
            ),
            start=Decimal("0"),
        )
        all_net_proceeds_confirmed = all(
            transaction.get("net_proceeds_jpy") is not None
            for transaction in matching_sales
        )
        confirmed_net_proceeds = sum(
            (_decimal(transaction.get("net_proceeds_jpy")) for transaction in matching_sales),
            start=Decimal("0"),
        )
        if not has_confirmed_jpy_proceeds_basis:
            provisional_proceeds = holding.market_value_jpy
            provisional_amount_definition = (
                "snapshot market value carrying placeholder pending confirmed JPY-equivalent "
                "sale proceeds; not a sale-proceeds estimate"
            )
        else:
            provisional_proceeds = (
                confirmed_net_proceeds
                if all_net_proceeds_confirmed
                else gross_proceeds - confirmed_fees - confirmed_taxes
            )
            provisional_amount_definition = (
                "confirmed net_proceeds_jpy when available; otherwise gross proceeds "
                "less only confirmed fee_jpy and tax_jpy"
            )
        unknown_deductions = sorted(
            {
                field
                for transaction in matching_sales
                for field in ("fee_jpy", "tax_jpy", "net_proceeds_jpy")
                if transaction.get(field) is None
            }
        )

        removed_value_total += holding.market_value_jpy
        proceeds_total += provisional_proceeds
        adjustments.append(
            {
                "symbol": holding.symbol,
                "snapshot_quantity": _number(holding.quantity),
                "projected_quantity": 0,
                "snapshot_market_value_jpy": _number(holding.market_value_jpy),
                "gross_proceeds_jpy": (
                    _number(gross_proceeds) if has_confirmed_jpy_proceeds_basis else None
                ),
                "confirmed_fees_jpy": _number(confirmed_fees),
                "confirmed_taxes_jpy": _number(confirmed_taxes),
                "confirmed_net_proceeds_jpy": (
                    _number(confirmed_net_proceeds)
                    if all_net_proceeds_confirmed
                    else None
                ),
                "provisional_proceeds_jpy": _number(provisional_proceeds),
                "provisional_amount_definition": provisional_amount_definition,
                "unknown_deductions": unknown_deductions,
                "transaction_refs": [
                    f"transactions/ledger.yaml#{transaction['transaction_id']}"
                    for transaction in matching_sales
                ],
                "execution_status_as_of": execution_as_of.isoformat(),
            }
        )

    for transaction_id, transaction in aggregate_exit_transactions.items():
        removed_symbols = aggregate_removed_symbols[transaction_id]
        if not removed_symbols:
            continue
        reported_proceeds = _decimal(transaction.get("reported_proceeds_total_jpy"))
        proceeds_total += reported_proceeds
        adjustments.append(
            {
                "symbol": str(transaction.get("symbol")),
                "symbols": removed_symbols,
                "adjustment_type": "user_reported_aggregate_full_exit",
                "snapshot_market_value_jpy": _number(
                    aggregate_removed_values[transaction_id]
                ),
                "gross_proceeds_jpy": None,
                "confirmed_fees_jpy": 0,
                "confirmed_taxes_jpy": 0,
                "provisional_proceeds_jpy": _number(reported_proceeds),
                "provisional_amount_definition": (
                    "user-reported aggregate yen proceeds; not classified as gross or net"
                ),
                "unknown_deductions": [
                    "gross_proceeds_jpy",
                    "fee_jpy",
                    "net_proceeds_jpy",
                    "per_asset_proceeds",
                ],
                "transaction_refs": [
                    f"transactions/ledger.yaml#{transaction_id}"
                ],
                "execution_status_as_of": str(
                    transaction.get("execution_confirmed_at")
                )[:10],
            }
        )

    if adjustments:
        retained.append(
            Holding(
                symbol="POST_SNAPSHOT_SALE_PROCEEDS",
                name="スナップショット後の売却代金（暫定）",
                asset_class="liquidity",
                quantity=None,
                avg_cost=None,
                current_price=None,
                market_value_jpy=proceeds_total,
                currency="JPY",
                source_category="売却代金（受渡待ちを含む）",
                institution="複数証券会社",
                account_type="取引台帳集約（暫定）",
                valuation_jpy=proceeds_total,
                notes=(
                    "取引台帳の確認済み売却代金を現在状態へ集約。"
                    "未確認控除または集約報告があるため純受取額ではない。"
                ),
            )
        )

    projected.holdings = retained
    projected.total_assets_jpy = (
        snapshot.total_assets_jpy - removed_value_total + proceeds_total
    )
    projected.category_totals_jpy = {}
    projected.validation_notes.append(
        "Current-state projection overlays confirmed post-snapshot full exits; "
        "historical snapshot remains unchanged."
    )
    if any(adjustment["unknown_deductions"] for adjustment in adjustments):
        projected.warnings.append(
            "Post-snapshot sale proceeds are provisional because some fees, taxes, "
            "or net proceeds are not yet confirmed."
        )
    projected.warnings.extend(warnings)

    report = {
        "projection_type": "confirmed_post_snapshot_full_exit_overlay",
        "source_snapshot_date": snapshot.snapshot_date.isoformat(),
        "historical_snapshot_mutated": False,
        "adjustments": adjustments,
        "removed_snapshot_market_value_jpy": _number(removed_value_total),
        "provisional_sale_proceeds_jpy": _number(proceeds_total),
        "source_total_assets_jpy": _number(snapshot.total_assets_jpy),
        "projected_total_assets_jpy": _number(projected.total_assets_jpy),
        "is_provisional": any(
            adjustment["unknown_deductions"] for adjustment in adjustments
        ),
        "warnings": warnings,
    }
    return projected, report


def _is_confirmed_post_snapshot_sale(
    transaction: dict,
    *,
    symbol: str,
    snapshot_date: date,
) -> bool:
    if (
        transaction.get("status") != "confirmed"
        or transaction.get("transaction_type") != "sell"
        or str(transaction.get("symbol")) != symbol
    ):
        return False
    event_date = _optional_date(transaction.get("trade_date")) or _optional_date(
        transaction.get("execution_confirmed_at")
    )
    return event_date is not None and event_date > snapshot_date


def _is_confirmed_post_snapshot_aggregate_exit(
    transaction: dict,
    *,
    snapshot_date: date,
) -> bool:
    symbols = transaction.get("symbols")
    if (
        transaction.get("status") != "confirmed"
        or transaction.get("transaction_type") != "sell"
        or not isinstance(symbols, list)
        or not symbols
        or transaction.get("balance_after_sale_jpy") != 0
        or transaction.get("reported_proceeds_total_jpy") is None
    ):
        return False
    event_date = _optional_date(transaction.get("trade_date")) or _optional_date(
        transaction.get("execution_confirmed_at")
    )
    return event_date is not None and event_date > snapshot_date


def _optional_date(value) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value)[:10])


def _decimal(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)
