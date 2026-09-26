from __future__ import annotations

import pytest

from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe
from observability.self_healing import (
    DataQualityGateError,
    rebuild_from_raw_snapshot,
    refetch_source,
    run_quality_gate_with_self_healing,
)


def test_clean_data_needs_no_healing(clean_df, settings, frozen_now):
    result = run_quality_gate_with_self_healing(clean_df, settings, "unit")
    assert result.healed is False and result.action == "none"
    assert result.df is clean_df
    assert not settings.paths.self_healing_log.exists()


def test_corrupted_data_is_repaired_automatically(clean_df, settings, frozen_now):
    corrupted = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    result = run_quality_gate_with_self_healing(corrupted, settings, "corrupted", repaired_report_name="repaired")
    assert result.initial_quality["success"] is False
    assert result.healed and result.action == "rebuild_from_raw_snapshot"
    assert result.final_quality["success"] is True and result.idempotent is True
    assert len(result.df) == 24
    [incident] = read_json(settings.paths.self_healing_log)
    assert incident["resolved"] is True and incident["detected"]["success"] is False
    assert (settings.paths.quality_dir / "repaired_quality_report.json").exists()


def test_escalates_to_next_strategy(clean_df, settings, frozen_now):
    def broken(_settings):
        raise ConnectionError("snapshot unreadable")

    def still_bad(_settings):
        return clean_df.head(2), True

    result = run_quality_gate_with_self_healing(
        clean_df.head(2), settings, "unit",
        strategies=[("broken", broken), ("still_bad", still_bad), ("rebuild", rebuild_from_raw_snapshot)],
    )
    assert result.action == "rebuild"
    assert [a["action"] for a in result.attempts] == ["broken", "still_bad", "rebuild"]
    assert "ConnectionError" in result.attempts[0]["error"]


def test_blocks_when_no_strategy_succeeds(clean_df, settings, frozen_now):
    with pytest.raises(DataQualityGateError, match="no repair strategy succeeded"):
        run_quality_gate_with_self_healing(clean_df.head(2), settings, "unit", strategies=[])
    [incident] = read_json(settings.paths.self_healing_log)
    assert incident["resolved"] is False and incident["action"] == "blocked"


def test_escalates_to_refetch_when_records_snapshot_is_broken(clean_df, settings, frozen_now, monkeypatch):
    # crossref_records.json hong -> rebuild FAIL -> refetch (API bi chan -> fallback raw response) -> PASS.
    import ingestion.crossref as crossref

    monkeypatch.setattr(crossref.time, "sleep", lambda _: None)
    settings.paths.raw_records_json.write_text("[]", encoding="utf-8")
    result = run_quality_gate_with_self_healing(clean_df.head(2), settings, "unit")
    assert result.action == "refetch_source" and len(result.df) == 24
    actions = [a["action"] for a in read_json(settings.paths.self_healing_log)[0]["attempts"]]
    assert actions == ["rebuild_from_raw_snapshot", "refetch_source"]


def test_allow_refetch_false_blocks(clean_df, settings, frozen_now):
    settings.paths.raw_records_json.write_text("[]", encoding="utf-8")
    with pytest.raises(DataQualityGateError):
        run_quality_gate_with_self_healing(clean_df.head(2), settings, "unit", allow_refetch=False)


def test_refetch_source_uses_api_path(settings, monkeypatch):
    import observability.self_healing as healing

    seen = {}

    def fake_fetch(cfg):
        seen["refresh"] = cfg.refresh_source
        from ingestion.crossref import load_raw_records

        return load_raw_records(settings.paths.raw_records_json)

    monkeypatch.setattr(healing, "fetch_source_records", fake_fetch)
    df, _ = refetch_source(settings)
    assert seen["refresh"] is True and len(df) == 24
