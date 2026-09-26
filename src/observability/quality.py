from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json

MIN_ROWS = 5
MAX_ROWS = 5000
REQUIRED_COLUMNS = ("paper_id", "title", "text_for_embedding")
MIN_SUMMARY_CHARS = 30
MAX_STALE_RATIO = 0.25


def _build_expectations() -> list[gx.expectations.Expectation]:
    expectations: list[gx.expectations.Expectation] = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=MIN_ROWS, max_value=MAX_ROWS),
    ]
    expectations += [gx.expectations.ExpectColumnValuesToNotBeNull(column=column) for column in REQUIRED_COLUMNS]
    expectations += [
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=MIN_SUMMARY_CHARS),
    ]
    return expectations


def _summarize_result(result) -> dict[str, Any]:
    payload = result.to_json_dict()
    config = payload.get("expectation_config") or {}
    details = payload.get("result") or {}
    return {
        "expectation": config.get("type"),
        "column": (config.get("kwargs") or {}).get("column"),
        "success": bool(payload.get("success")),
        "observed_value": details.get("observed_value"),
        "unexpected_count": details.get("unexpected_count"),
        "unexpected_percent": details.get("unexpected_percent"),
        "partial_unexpected_list": details.get("partial_unexpected_list"),
    }


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Freshness SLA: fail neu ty le bai bao cu (age_days > threshold) vuot qua 25%."""
    threshold = settings.freshness_threshold_days
    total_rows = int(len(df))
    ages = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df else pd.Series(dtype=float)
    stale_rows = int((ages > threshold).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0

    published = pd.to_datetime(df["published"], errors="coerce") if "published" in df else pd.Series(dtype="datetime64[ns]")
    latest = published.max()
    oldest = published.min()
    return {
        "threshold_days": threshold,
        "max_stale_ratio": MAX_STALE_RATIO,
        "latest_published": latest.strftime("%Y-%m-%d") if pd.notna(latest) else None,
        "oldest_published": oldest.strftime("%Y-%m-%d") if pd.notna(oldest) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": total_rows > 0 and stale_ratio <= MAX_STALE_RATIO,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay GX 1.x expectations + freshness SLA, ghi report vao `data/quality/`.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name=f"papers_{report_name}_suite"))
    for expectation in _build_expectations():
        suite.add_expectation(expectation)
    validation = batch.validate(suite)

    checks = [_summarize_result(result) for result in validation.results]
    freshness = evaluate_freshness_sla(df, settings)
    expectations_passed = bool(validation.success)

    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "gx_version": gx.__version__,
        "row_count": int(len(df)),
        "success": expectations_passed and freshness["is_fresh"],
        "expectations_success": expectations_passed,
        "failed_expectations": [check["expectation"] for check in checks if not check["success"]],
        "checks": checks,
        "freshness": freshness,
    }
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, report)
    report["report_path"] = str(report_path)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report va ghi JSON ra `report_path`."""
    payload = {"generated_at": now_utc().isoformat(), **evaluate_freshness_sla(df, settings)}
    write_json(report_path, payload)
    return payload
