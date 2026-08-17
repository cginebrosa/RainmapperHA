"""Persistent, bounded repair queue for gaps in official weather history."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "official_weather_gap_repair_v1"
OFFICIAL_SOURCES = frozenset({"aemet", "meteocat"})
MAX_BLOCK_DAYS = 15
MAX_BACKOFF_DAYS = 7
STATE_FILENAME = "official-weather-gap-repair.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "active": False,
        "updated_at": None,
        "checked_through": {},
        "pending": [],
        "last_resolved": [],
    }


def state_path(data_dir: Path) -> Path:
    return Path(data_dir) / "weather-history" / STATE_FILENAME


def load_state(data_dir: Path) -> dict[str, Any]:
    path = state_path(data_dir)
    if not path.is_file():
        return empty_state()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported official weather repair state: {path}")
    if not isinstance(payload.get("pending"), list):
        raise ValueError(f"Invalid official weather repair pending queue: {path}")
    return payload


def write_state(data_dir: Path, state: dict[str, Any]) -> None:
    path = state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    payload["schema_version"] = SCHEMA_VERSION
    payload["active"] = bool(payload.get("pending"))
    payload["updated_at"] = utc_now().isoformat()
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _group_days(days: Iterable[date], max_days: int = MAX_BLOCK_DAYS) -> list[tuple[date, date]]:
    ordered = sorted(set(days))
    groups: list[tuple[date, date]] = []
    if not ordered:
        return groups
    start = previous = ordered[0]
    for current in ordered[1:]:
        group_length = (previous - start).days + 1
        if current != previous + timedelta(days=1) or group_length >= max_days:
            groups.append((start, previous))
            start = current
        previous = current
    groups.append((start, previous))
    return groups


def _item_id(source: str, start: date, end: date) -> str:
    return f"{source}:{start.isoformat()}:{end.isoformat()}"


def enqueue_missing_days(
    state: dict[str, Any],
    source: str,
    missing_days: Iterable[date],
    *,
    detected_at: datetime | None = None,
) -> dict[str, Any]:
    if source not in OFFICIAL_SOURCES:
        raise ValueError(f"Unsupported official source: {source}")
    detected_at = detected_at or utc_now()
    result = json.loads(json.dumps(state))
    pending = result.setdefault("pending", [])
    already_queued: set[date] = set()
    for item in pending:
        if item.get("source") != source:
            continue
        already_queued.update(
            _days(date.fromisoformat(item["start_date"]), date.fromisoformat(item["end_date"]))
        )
    additions = set(missing_days) - already_queued
    for start, end in _group_days(additions):
        pending.append(
            {
                "id": _item_id(source, start, end),
                "source": source,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "scope": "network_day",
                "status": "pending",
                "attempts": 0,
                "detected_at": detected_at.isoformat(),
                "last_attempt_at": None,
                "next_retry_at": detected_at.isoformat(),
                "last_error": None,
            }
        )
    pending.sort(key=lambda item: (item["start_date"], item["source"], item["end_date"]))
    result["active"] = bool(pending)
    return result


def next_due(
    state: dict[str, Any],
    *,
    now: datetime | None = None,
    source: str | None = None,
) -> dict[str, Any] | None:
    now = now or utc_now()
    candidates = []
    for item in state.get("pending", []):
        if source is not None and item.get("source") != source:
            continue
        retry = datetime.fromisoformat(item["next_retry_at"])
        if retry.tzinfo is None:
            retry = retry.replace(tzinfo=timezone.utc)
        if retry <= now:
            candidates.append(item)
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item["start_date"], item["source"]))


def record_attempt(
    state: dict[str, Any],
    item_id: str,
    *,
    recovered_days: Iterable[date] = (),
    error: str | None = None,
    attempted_at: datetime | None = None,
) -> dict[str, Any]:
    attempted_at = attempted_at or utc_now()
    result = json.loads(json.dumps(state))
    pending = result.get("pending", [])
    index = next((position for position, item in enumerate(pending) if item.get("id") == item_id), None)
    if index is None:
        raise KeyError(f"Unknown official weather repair item: {item_id}")
    item = pending.pop(index)
    expected = set(
        _days(date.fromisoformat(item["start_date"]), date.fromisoformat(item["end_date"]))
    )
    recovered = expected.intersection(set(recovered_days))
    remaining = expected - recovered
    attempts = int(item.get("attempts", 0)) + 1
    if not remaining:
        resolved = dict(item)
        resolved.update(
            {
                "status": "resolved",
                "attempts": attempts,
                "last_attempt_at": attempted_at.isoformat(),
                "resolved_at": attempted_at.isoformat(),
                "last_error": None,
            }
        )
        history = result.setdefault("last_resolved", [])
        history.insert(0, resolved)
        del history[20:]
    else:
        backoff_days = min(2 ** max(0, attempts - 1), MAX_BACKOFF_DAYS)
        for start, end in _group_days(remaining):
            retry = dict(item)
            retry.update(
                {
                    "id": _item_id(item["source"], start, end),
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "status": "retry_wait",
                    "attempts": attempts,
                    "last_attempt_at": attempted_at.isoformat(),
                    "next_retry_at": (attempted_at + timedelta(days=backoff_days)).isoformat(),
                    "last_error": error or "provider_returned_no_rows_for_expected_day",
                }
            )
            pending.append(retry)
    pending.sort(key=lambda value: (value["start_date"], value["source"], value["end_date"]))
    result["active"] = bool(pending)
    return result


def detection_window(
    state: dict[str, Any],
    source: str,
    reference_day: date,
    *,
    overlap_days: int = 7,
    initial_lookback_days: int = 30,
) -> tuple[date, date] | None:
    """Return unseen closed days older than the runner's normal overlap."""
    if source not in OFFICIAL_SOURCES:
        raise ValueError(f"Unsupported official source: {source}")
    if overlap_days < 0 or initial_lookback_days <= 0:
        raise ValueError("Invalid official weather detection window")
    end = reference_day - timedelta(days=overlap_days + 1)
    previous = state.get("checked_through", {}).get(source)
    start = (
        date.fromisoformat(previous) + timedelta(days=1)
        if previous
        else end - timedelta(days=initial_lookback_days - 1)
    )
    return None if start > end else (start, end)


def observed_network_days(
    data_dir: Path,
    source: str,
    start: date,
    end: date,
) -> set[date]:
    from rainmapper_core.weather_history_dataset import iter_weather_history

    observed: set[date] = set()
    for batch in iter_weather_history(
        data_dir,
        columns=["local_date"],
        sources={source},
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        allow_unbounded=False,
    ):
        observed.update(
            date(int(value[:4]), int(value[4:6]), int(value[6:8]))
            for value in map(str, batch.column("local_date").to_pylist())
        )
    return observed


def detect_and_enqueue_network_gaps(
    state: dict[str, Any],
    data_dir: Path,
    source: str,
    reference_day: date,
    *,
    overlap_days: int = 7,
    initial_lookback_days: int = 30,
) -> tuple[dict[str, Any], list[date]]:
    """Queue source-wide missing days and advance the persistent audit cursor."""
    window = detection_window(
        state,
        source,
        reference_day,
        overlap_days=overlap_days,
        initial_lookback_days=initial_lookback_days,
    )
    if window is None:
        return state, []
    start, end = window
    expected = set(_days(start, end))
    missing = sorted(expected - observed_network_days(data_dir, source, start, end))
    result = enqueue_missing_days(state, source, missing)
    result.setdefault("checked_through", {})[source] = end.isoformat()
    return result, missing
