from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from observability.dashboard import build_dashboard
from observability.quality import build_freshness_report
from observability.reporting import generate_corruption_report
from observability.self_healing import rebuild_from_raw_snapshot, run_quality_gate_with_self_healing
from pipelines.phase1 import run_phase1_pipeline, save_clean_artifacts
from retrieval.index import LocalEmbeddingIndex

COMPARED_METRICS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _log(step: str, message: str) -> None:
    print(f"[phase2] {step:<10} {message}")


def _ensure_baseline(settings: Settings) -> tuple[pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    paths = settings.paths
    required = (paths.clean_json, paths.baseline_metrics, paths.baseline_answers, paths.eval_testset)
    if not all(path.exists() for path in required):
        _log("baseline", "baseline artifacts missing -> running phase 1 first")
        run_phase1_pipeline(settings)
    clean_df = pd.DataFrame(read_json(paths.clean_json))
    return clean_df, read_json(paths.baseline_metrics), read_json(paths.baseline_answers)


def _index_and_evaluate(
    df: pd.DataFrame,
    settings: Settings,
    embeddings_path,
    metrics_path,
    answers_path,
) -> tuple[LocalEmbeddingIndex, EvaluationBundle]:
    index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
    bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset, metrics_path, answers_path)
    return index, bundle


def repair_from_raw_snapshot(settings: Settings) -> tuple[pd.DataFrame, bool]:
    """Idempotent repair: rebuild clean data tu raw snapshot (lineage anchor), khong goi lai API.

    Chay cleaning 2 lan tren cung snapshot va so sanh de chung minh repair la idempotent,
    sau do ghi de artifacts `*_repaired` bang ban sach.
    """
    repaired, idempotent = rebuild_from_raw_snapshot(settings)
    save_clean_artifacts(repaired, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)
    return repaired, idempotent


def _print_comparison(baseline: dict, corrupted: dict, repaired: dict, gates: dict[str, Any]) -> None:
    header = f"{'Metric':<22}{'Baseline':>12}{'Corrupted':>12}{'Repaired':>12}"
    print("\n" + header)
    print("-" * len(header))
    for key in COMPARED_METRICS:
        print(f"{key:<22}{baseline.get(key, 0):>12.3f}{corrupted.get(key, 0):>12.3f}{repaired.get(key, 0):>12.3f}")
    print(f"{'quality_gate':<22}" + "".join(f"{('PASS' if gates[s] else 'FAIL'):>12}" for s in gates) + "\n")


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Baseline -> Corrupt -> Evaluate -> Repair -> Evaluate -> Compare."""
    paths = settings.paths

    # 1. Baseline (dung lai ket qua phase 1).
    clean_df, baseline_metrics, baseline_answers = _ensure_baseline(settings)
    baseline_quality = read_json(paths.baseline_quality_report) if paths.baseline_quality_report.exists() else None
    _log("baseline", f"{len(clean_df)} rows, hit_rate={baseline_metrics['retrieval_hit_rate']:.3f}")

    # 2-3. Corrupt + save artifacts.
    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    save_clean_artifacts(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    _log("corrupt", f"{len(clean_df)} -> {len(corrupted_df)} rows, log -> {paths.corruption_log}")

    # 4. Index corrupted data va evaluate. Pipeline chay "thanh cong" du du lieu hong (silent failure).
    _, corrupted_bundle = _index_and_evaluate(
        corrupted_df, settings, paths.corrupted_embeddings_json, paths.corrupted_metrics, paths.corrupted_answers
    )
    corrupted_metrics = corrupted_bundle.summary
    _log("evaluate", f"corrupted hit_rate={corrupted_metrics['retrieval_hit_rate']:.3f} "
                     f"token_f1={corrupted_metrics['mean_token_f1']:.3f} (no exception raised)")

    # 5-6. Self-healing quality gate: phat hien corrupted data FAIL -> tu dong repair tu raw snapshot
    #      (leo thang sang re-fetch API neu snapshot cung FAIL) -> validate lai truoc khi index.
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )
    healing = run_quality_gate_with_self_healing(
        corrupted_df, settings, "corrupted", repaired_report_name="repaired"
    )
    corrupted_quality, repaired_quality = healing.initial_quality, healing.final_quality
    repaired_df, idempotent = healing.df, bool(healing.idempotent)
    save_clean_artifacts(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    _log("quality", f"corrupted gate={corrupted_quality['success']} failed={corrupted_quality['failed_expectations']}")
    _log("self-heal", f"auto action={healing.action} -> {len(repaired_df)} rows, gate={repaired_quality['success']} "
                      f"(idempotent={idempotent}, log -> {paths.self_healing_log.name})")

    # 7. Evaluate repaired dataset.
    _, repaired_bundle = _index_and_evaluate(
        repaired_df, settings, paths.repaired_embeddings_json, paths.repaired_metrics, paths.repaired_answers
    )
    repaired_metrics = repaired_bundle.summary
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )
    _log("evaluate", f"repaired hit_rate={repaired_metrics['retrieval_hit_rate']:.3f} gate={repaired_quality['success']}")

    # 8. Comparison report.
    gates = {
        "baseline": bool(baseline_quality and baseline_quality.get("success")),
        "corrupted": corrupted_quality["success"],
        "repaired": repaired_quality["success"],
    }
    _print_comparison(baseline_metrics, corrupted_metrics, repaired_metrics, gates)
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        baseline_quality=baseline_quality,
        corruption_log=read_json(paths.corruption_log),
        answers={
            "baseline": baseline_answers,
            "corrupted": corrupted_bundle.answers,
            "repaired": repaired_bundle.answers,
        },
        repair_info={
            "source": paths.raw_records_json.relative_to(paths.project_dir).as_posix(),
            "rows": len(repaired_df),
            "idempotent": idempotent,
            "trigger": "automatically by the failed quality gate",
            "action": healing.action,
        },
    )
    _log("report", str(paths.comparison_report))
    build_dashboard(settings)
    _log("dashboard", str(paths.dashboard_html))

    return {
        "baseline": baseline_metrics,
        "corrupted": corrupted_metrics,
        "repaired": repaired_metrics,
        "quality_gates": gates,
        "repair_idempotent": idempotent,
        "self_healing_action": healing.action,
    }


def main() -> None:
    """Chay corruption -> evaluate -> repair -> compare flow (xem `run_corruption_flow_pipeline`)."""
    run_corruption_flow_pipeline(load_settings())
