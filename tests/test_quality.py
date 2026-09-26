from __future__ import annotations

import pandas as pd

from core.utils import read_json
from observability.quality import build_freshness_report, evaluate_freshness_sla, run_data_quality_checks


def test_clean_data_passes_gate_and_writes_report(clean_df, settings):
    result = run_data_quality_checks(clean_df, settings, "unit")
    assert result["success"] is True
    assert result["failed_expectations"] == []
    assert len(result["checks"]) == 6
    assert read_json(settings.paths.quality_dir / "unit_quality_report.json")["success"] is True


def test_duplicates_and_short_summaries_fail(clean_df, settings):
    bad = pd.concat([clean_df, clean_df.head(2)], ignore_index=True)
    bad.loc[:2, "summary"] = "short"
    result = run_data_quality_checks(bad, settings, "unit")
    assert result["success"] is False
    assert set(result["failed_expectations"]) == {
        "expect_column_values_to_be_unique",
        "expect_column_value_lengths_to_be_between",
    }


def test_null_title_and_small_table_fail(clean_df, settings):
    tiny = clean_df.head(3).copy()
    tiny.loc[0, "title"] = None
    failed = set(run_data_quality_checks(tiny, settings, "unit")["failed_expectations"])
    assert {"expect_table_row_count_to_be_between", "expect_column_values_to_not_be_null"} <= failed


def test_stale_data_fails_freshness_only(clean_df, settings):
    stale = clean_df.copy()
    stale.loc[: len(stale) // 2, "age_days"] = 999
    result = run_data_quality_checks(stale, settings, "unit")
    assert result["expectations_success"] is True
    assert result["freshness"]["is_fresh"] is False
    assert result["success"] is False


def test_freshness_sla_boundaries(clean_df, settings):
    fresh = evaluate_freshness_sla(clean_df, settings)
    assert fresh["is_fresh"] is True and fresh["total_rows"] == 24
    assert fresh["latest_published"] >= fresh["oldest_published"]
    empty = evaluate_freshness_sla(pd.DataFrame(), settings)
    assert empty["is_fresh"] is False and empty["latest_published"] is None


def test_build_freshness_report_writes_json(clean_df, settings):
    path = settings.paths.freshness_report
    payload = build_freshness_report(clean_df, settings, path)
    assert read_json(path)["stale_rows"] == payload["stale_rows"]
    assert "generated_at" in payload
