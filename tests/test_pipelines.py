"""End-to-end: phase1 -> corruption flow -> self-healing -> reports -> dashboard (mock LLM, khong mang)."""
from __future__ import annotations

import pytest

from core.utils import read_json
import pipelines.corruption_flow as corruption_flow
import pipelines.phase1 as phase1
from observability.dashboard import build_dashboard, collect_dashboard_data, render_dashboard


@pytest.fixture
def phase1_result(settings, frozen_now):
    return phase1.run_phase1_pipeline(settings)


def test_phase1_produces_baseline_artifacts(phase1_result, settings):
    paths = settings.paths
    assert phase1_result["metrics"]["retrieval_hit_rate"] == 1.0
    assert phase1_result["quality"]["success"] is True
    assert phase1_result["source"]["self_healing_action"] == "none"
    for path in (paths.clean_csv, paths.clean_json, paths.eval_testset, paths.baseline_metrics,
                 paths.baseline_quality_report, paths.freshness_report, paths.baseline_report, paths.demo_answers):
        assert path.exists(), path
    report = paths.baseline_report.read_text(encoding="utf-8")
    assert "## 2. Baseline RAG Evaluation" in report and "Retrieval hit rate" in report


def test_phase1_reuses_valid_test_set(phase1_result, settings, frozen_now):
    first = read_json(settings.paths.eval_testset)
    phase1.run_phase1_pipeline(settings)
    assert read_json(settings.paths.eval_testset) == first


def test_corruption_flow_self_heals_and_reports(phase1_result, settings, frozen_now):
    result = corruption_flow.run_corruption_flow_pipeline(settings)
    assert result["quality_gates"] == {"baseline": True, "corrupted": False, "repaired": True}
    assert result["self_healing_action"] == "rebuild_from_raw_snapshot"
    assert result["repaired"]["retrieval_hit_rate"] == result["baseline"]["retrieval_hit_rate"]
    assert result["corrupted"]["retrieval_hit_rate"] < result["baseline"]["retrieval_hit_rate"]

    report = settings.paths.comparison_report.read_text(encoding="utf-8")
    assert "| Metric | Baseline | Corrupted | Repaired |" in report
    assert "triggered automatically by the failed quality gate" in report
    assert "D:\\" not in report and "C:\\" not in report
    [incident] = read_json(settings.paths.self_healing_log)
    assert incident["resolved"] and incident["stage"] == "corrupted"

    html = settings.paths.dashboard_html.read_text(encoding="utf-8")
    assert "Data Observability Dashboard" in html and "rebuild_from_raw_snapshot" in html


def test_corruption_flow_runs_phase1_when_baseline_missing(settings, frozen_now, monkeypatch):
    calls = []
    real = corruption_flow.run_phase1_pipeline
    monkeypatch.setattr(corruption_flow, "run_phase1_pipeline", lambda cfg: calls.append(1) or real(cfg))
    corruption_flow.run_corruption_flow_pipeline(settings)
    assert calls == [1]


def test_repair_from_raw_snapshot_is_idempotent(settings, frozen_now):
    df, idempotent = corruption_flow.repair_from_raw_snapshot(settings)
    assert idempotent and len(df) == 24 and settings.paths.repaired_clean_json.exists()


def test_dashboard_handles_missing_artifacts_and_escapes(settings):
    data = collect_dashboard_data(settings)
    assert all(not state["available"] for state in data["states"].values())
    data["corruption_counts"] = {"<script>x</script>": 1}
    html = render_dashboard(data)
    assert "<script>x</script>" not in html and "No clean data found" in html
    assert build_dashboard(settings).exists()


def test_entrypoints_use_loaded_settings(settings, monkeypatch, frozen_now):
    import observability.dashboard as dashboard

    for module in (phase1, corruption_flow, dashboard):
        monkeypatch.setattr(module, "load_settings", lambda: settings)
    phase1.main()
    corruption_flow.main()
    dashboard.main()
    assert settings.paths.comparison_report.exists()
