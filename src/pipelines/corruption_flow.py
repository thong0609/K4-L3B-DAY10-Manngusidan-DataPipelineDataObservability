from __future__ import annotations

import logging
import pandas as pd

from core.config import load_settings
from core.utils import ensure_parent, now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run full Corruption -> Observability Detection -> Idempotent Repair -> Compare Pipeline."""
    settings = load_settings()
    logger.info("Starting Data Corruption & Idempotent Repair Flow...")

    # 1. Load baseline metrics & clean dataset
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        raise RuntimeError("Baseline metrics or clean dataset missing. Please run `python script/run_phase1.py` first.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    logger.info("Loaded baseline data (%d rows) and metrics.", len(clean_df))

    # 2. Inject synthetic data corruption (6 scenarios)
    logger.info("Injecting 6 synthetic data corruption scenarios...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    ensure_parent(settings.paths.corrupted_clean_json)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    logger.info("Saved corrupted dataframe (%d rows) to %s", len(corrupted_df), settings.paths.corrupted_clean_json)

    # 3. Build corrupted Chroma index & evaluate
    logger.info("Building ChromaDB collection '%s' with corrupted records...", settings.corrupted_collection_name)
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)

    logger.info("Evaluating RAG performance on corrupted dataset...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    # 4. Observability: Run Data Quality Gate & Freshness on Corrupted Data
    logger.info("Running GX 1.x quality checks on corrupted dataset...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    logger.info("Corrupted Quality Gate Success: %s | Freshness: %s",
                corrupted_quality.get("success"), corrupted_freshness.get("is_fresh"))

    # 5. Idempotent Repair from immutable raw snapshot
    logger.info("Initiating Idempotent Repair from raw snapshot: %s", settings.paths.raw_records_json)
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    ensure_parent(settings.paths.repaired_clean_json)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    logger.info("Repaired dataframe rebuilt (%d rows) without side-effects.", len(repaired_df))

    # 6. Build repaired Chroma index & evaluate
    logger.info("Building ChromaDB collection '%s' with repaired records...", settings.repaired_collection_name)
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)

    logger.info("Evaluating RAG performance on repaired dataset...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    # 7. Observability: Run Data Quality Gate & Freshness on Repaired Data
    logger.info("Running GX 1.x quality checks on repaired dataset...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)

    # 8. Generate 3-State Markdown Comparison Report
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    logger.info("Comparison report generated at: %s", settings.paths.comparison_report)

    # 9. Print 3-state summary table to console
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0) * 100
    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0) * 100
    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0) * 100

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0) * 100
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0) * 100
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0) * 100

    c_gx = "PASS" if corrupted_quality.get("success") else "FAIL"
    r_gx = "PASS" if repaired_quality.get("success") else "FAIL"

    c_fr = "FRESH" if corrupted_freshness.get("is_fresh") else "STALE"
    r_fr = "FRESH" if repaired_freshness.get("is_fresh") else "STALE"

    print("\n========================= 3-STATE COMPARISON REPORT =========================")
    print(f"{'Metric / Criteria':<30} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 75)
    print(f"{'Data Quality Gate (GX 1.x)':<30} | {'PASS':<12} | {c_gx:<12} | {r_gx:<12}")
    print(f"{'Freshness SLA':<30} | {'FRESH':<12} | {c_fr:<12} | {r_fr:<12}")
    print(f"{'Retrieval Hit Rate':<30} | {f'{b_hit:.1f}%':<12} | {f'{c_hit:.1f}%':<12} | {f'{r_hit:.1f}%':<12}")
    print(f"{'Mean Token F1':<30} | {f'{b_f1:.1f}%':<12} | {f'{c_f1:.1f}%':<12} | {f'{r_f1:.1f}%':<12}")
    print("=============================================================================\n")
