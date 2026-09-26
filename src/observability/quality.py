from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run data quality checks using Great Expectations 1.x ephemeral context."""
    context = gx.get_context(mode="ephemeral")
    data_source_name = f"papers_source_{report_name}"
    data_asset_name = f"papers_asset_{report_name}"
    batch_def_name = f"papers_batch_{report_name}"
    suite_name = f"papers_suite_{report_name}"

    data_source = context.data_sources.add_pandas(name=data_source_name)
    data_asset = data_source.add_dataframe_asset(name=data_asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_def_name)

    suite = gx.ExpectationSuite(name=suite_name)
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=15, max_value=30))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20))
    context.suites.add(suite)

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(name=f"papers_val_{report_name}", data=batch_def, suite=suite)
    )
    validation_results = validation_definition.run(batch_parameters={"dataframe": df})

    report_payload: dict[str, Any] = {
        "report_name": report_name,
        "success": bool(validation_results.success),
        "suite_name": suite_name,
        "statistics": validation_results.statistics if hasattr(validation_results, "statistics") else {},
        "results": [
            {
                "expectation_type": r.expectation_config.type if hasattr(r, "expectation_config") else "",
                "success": bool(r.success),
                "result": r.result if hasattr(r, "result") else {},
            }
            for r in getattr(validation_results, "results", [])
        ],
    }

    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"quality_suite_{report_name}.json"

    ensure_parent(report_path)
    write_json(report_path, report_payload)
    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Calculate Freshness SLA report based on age_days and publication date."""
    target_path = Path(report_path)
    latest_published = str(df["published"].max()) if not df.empty and "published" in df else ""
    oldest_published = str(df["published"].min()) if not df.empty and "published" in df else ""

    total_rows = len(df)
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df else 0
    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    # Freshness SLA: Cảnh báo is_fresh = False nếu tỷ lệ bài báo có age_days > 180 vượt quá 25%
    is_fresh = bool(stale_ratio <= 0.25)

    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }

    ensure_parent(target_path)
    write_json(target_path, payload)
    return payload
