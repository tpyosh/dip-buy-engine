from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .models import CoreSpotBuyScheduleItem, ReviewFeedback
from .storage import load_yaml

DEFAULT_CORE_SPOT_BUY_EVENT_CONFIG = {
    "enabled": True,
    "calendar_id": "primary",
    "timezone": "Asia/Tokyo",
    "default_start_time": "09:00",
    "duration_minutes": 15,
    "title_prefix": "Coreスポット買い",
    "transparency": "transparent",
    "visibility": "private",
    "reminders": {
        "use_default": False,
        "overrides": [
            {"method": "popup", "minutes": 60},
        ],
    },
}


def load_core_spot_buy_event_config(project_root: Path) -> dict:
    config_path = project_root / "config/google_calendar.yaml"
    if not config_path.exists():
        return dict(DEFAULT_CORE_SPOT_BUY_EVENT_CONFIG)
    payload = load_yaml(config_path)
    configured = payload.get("core_spot_buy_events", payload)
    return merge_event_config(DEFAULT_CORE_SPOT_BUY_EVENT_CONFIG, configured)


def merge_event_config(defaults: dict, overrides: dict | None) -> dict:
    merged = dict(defaults)
    for key, value in (overrides or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_event_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_core_spot_buy_calendar_event_drafts(
    feedback: ReviewFeedback,
    *,
    review_target_month: str,
    source_review_path: str | Path | None = None,
    config: dict | None = None,
) -> list[dict[str, Any]]:
    event_config = merge_event_config(DEFAULT_CORE_SPOT_BUY_EVENT_CONFIG, config)
    if not event_config.get("enabled", True):
        return []
    plan = feedback.core_spot_buy_plan
    if plan is None or not plan.schedule:
        return []

    grouped_items = group_schedule_items_by_date(plan.schedule)
    timezone = str(event_config["timezone"])
    zone_info = ZoneInfo(timezone)
    start_clock = parse_clock_time(str(event_config["default_start_time"]))
    duration = timedelta(minutes=int(event_config["duration_minutes"]))

    drafts: list[dict[str, Any]] = []
    for execution_date, items in grouped_items.items():
        day_total = sum(item.amount_jpy for item in items)
        start_at = datetime.combine(execution_date, start_clock, tzinfo=zone_info)
        end_at = start_at + duration
        request = {
            "calendar_id": event_config.get("calendar_id", "primary"),
            "title": f"{event_config.get('title_prefix', 'Coreスポット買い')} {format_jpy(day_total)}",
            "start_time": start_at.isoformat(timespec="seconds"),
            "end_time": end_at.isoformat(timespec="seconds"),
            "timezone_str": timezone,
            "attendees": [],
            "add_google_meet": False,
            "description": build_core_spot_buy_event_description(
                review_target_month=review_target_month,
                source_review_path=source_review_path,
                account_type=plan.account_type,
                items=items,
                day_total=day_total,
            ),
            "transparency": event_config.get("transparency", "transparent"),
            "visibility": event_config.get("visibility", "private"),
            "reminders": event_config.get("reminders"),
        }
        drafts.append(
            {
                "event_key": f"core_spot_buy:{review_target_month}:{execution_date.isoformat()}",
                "execution_date": execution_date,
                "review_target_month": review_target_month,
                "day_total_jpy": day_total,
                "schedule_items": [
                    {
                        "fund_name": item.fund_name,
                        "amount_jpy": item.amount_jpy,
                        "raw_text": item.raw_text,
                    }
                    for item in items
                ],
                "google_calendar_request": request,
            }
        )
    return drafts


def group_schedule_items_by_date(
    schedule: list[CoreSpotBuyScheduleItem],
) -> OrderedDict[date, list[CoreSpotBuyScheduleItem]]:
    grouped: OrderedDict[date, list[CoreSpotBuyScheduleItem]] = OrderedDict()
    for item in schedule:
        if item.execution_date is None:
            continue
        grouped.setdefault(item.execution_date, []).append(item)
    return grouped


def parse_clock_time(value: str) -> time:
    parts = value.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid default_start_time: {value}")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def build_core_spot_buy_event_description(
    *,
    review_target_month: str,
    source_review_path: str | Path | None,
    account_type: str | None,
    items: list[CoreSpotBuyScheduleItem],
    day_total: int,
) -> str:
    lines = [
        f"{review_target_month} 月次レビューで決めた core スポット買いの手動発注リマインダーです。",
        "自動発注ではありません。証券会社で内容を確認してから手動で実行してください。",
        "",
        f"account_type: {account_type or '-'}",
        f"day_total_jpy: {day_total}",
        "",
        "内訳:",
    ]
    for item in items:
        lines.append(f"- {item.fund_name}: {format_jpy(item.amount_jpy)}")
    if source_review_path is not None:
        lines.extend(["", f"source_review: {source_review_path}"])
    return "\n".join(lines)


def format_jpy(value: int) -> str:
    return f"{value:,}円"
