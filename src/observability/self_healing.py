"""Bonus B2: quality gate tu dong phat hien loi va tu kich hoat repair (khong can can thiep thu cong).

Chien luoc leo thang khi gate FAIL:
1. `rebuild_from_raw_snapshot`: rebuild clean data tu raw snapshot (lineage anchor, khong goi API).
2. `refetch_source`: neu chinh snapshot cung khong qua gate (vd du lieu da qua cu), goi lai Crossref API.
3. Neu van FAIL: raise `DataQualityGateError` de chan du lieu xau vao serving layer.
Moi su co duoc ghi vao `data/results/self_healing_log.json`.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, read_json, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks


class DataQualityGateError(RuntimeError):
    """Du lieu khong qua quality gate va khong the tu phuc hoi."""


@dataclass
class HealingResult:
    df: pd.DataFrame
    healed: bool
    action: str
    initial_quality: dict[str, Any]
    final_quality: dict[str, Any]
    idempotent: bool | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)


def rebuild_from_raw_snapshot(settings: Settings) -> tuple[pd.DataFrame, bool]:
    """Rebuild clean dataframe tu raw snapshot; chay 2 lan va so sanh de kiem tra tinh idempotent."""
    run_date = now_utc()
    records = load_raw_records(settings.paths.raw_records_json)
    rebuilt = build_clean_dataframe(records, run_date)
    idempotent = rebuilt.equals(build_clean_dataframe(records, run_date))
    return rebuilt, idempotent


def refetch_source(settings: Settings) -> tuple[pd.DataFrame, bool]:
    """Goi lai source API (REFRESH_SOURCE) roi clean; dung khi snapshot cung khong dat chuan."""
    records = fetch_source_records(replace(settings, refresh_source=True))
    return build_clean_dataframe(records, now_utc()), True


def _summary(quality: dict[str, Any]) -> dict[str, Any]:
    freshness = quality.get("freshness") or {}
    return {
        "success": quality.get("success"),
        "failed_expectations": quality.get("failed_expectations", []),
        "is_fresh": freshness.get("is_fresh"),
        "stale_ratio": freshness.get("stale_ratio"),
        "row_count": quality.get("row_count"),
    }


def _append_incident(log_path, incident: dict[str, Any]) -> None:
    history = read_json(log_path) if log_path.exists() else []
    history.append(incident)
    write_json(log_path, history)


def run_quality_gate_with_self_healing(
    df: pd.DataFrame,
    settings: Settings,
    stage: str,
    repaired_report_name: str | None = None,
    allow_refetch: bool = True,
    strategies: list[tuple[str, Callable[[Settings], tuple[pd.DataFrame, bool]]]] | None = None,
) -> HealingResult:
    """Chay quality gate; neu FAIL thi tu dong thu lan luot cac chien luoc repair cho den khi PASS."""
    initial = run_data_quality_checks(df, settings, stage)
    if initial["success"]:
        return HealingResult(df=df, healed=False, action="none", initial_quality=initial, final_quality=initial)

    if strategies is None:
        strategies = [("rebuild_from_raw_snapshot", rebuild_from_raw_snapshot)]
        if allow_refetch:
            strategies.append(("refetch_source", refetch_source))

    report_name = repaired_report_name or f"{stage}_autoheal"
    incident: dict[str, Any] = {
        "detected_at": now_utc().isoformat(),
        "stage": stage,
        "detected": _summary(initial),
        "attempts": [],
    }
    for action, strategy in strategies:
        try:
            candidate, idempotent = strategy(settings)
        except Exception as exc:  # strategy loi (vd mat mang) -> thu chien luoc tiep theo
            incident["attempts"].append({"action": action, "error": f"{type(exc).__name__}: {exc}"})
            continue
        quality = run_data_quality_checks(candidate, settings, report_name)
        incident["attempts"].append({"action": action, "idempotent": idempotent, "result": _summary(quality)})
        if quality["success"]:
            incident.update(resolved=True, action=action, resolved_at=now_utc().isoformat())
            _append_incident(settings.paths.self_healing_log, incident)
            return HealingResult(
                df=candidate,
                healed=True,
                action=action,
                initial_quality=initial,
                final_quality=quality,
                idempotent=idempotent,
                attempts=incident["attempts"],
            )

    incident.update(resolved=False, action="blocked")
    _append_incident(settings.paths.self_healing_log, incident)
    raise DataQualityGateError(
        f"Quality gate failed for '{stage}' and no repair strategy succeeded: "
        f"{initial.get('failed_expectations')} (see {settings.paths.self_healing_log.name})"
    )
