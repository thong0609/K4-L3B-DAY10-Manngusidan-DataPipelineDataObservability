from __future__ import annotations

import logging

from core.config import load_settings
from core.utils import ensure_parent, now_utc
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Run baseline pipeline end-to-end: ingestion -> cleaning -> index -> eval -> GX & freshness."""
    settings = load_settings()
    logger.info("Starting Phase 1 Baseline Pipeline...")

    # 1. Load or fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        logger.info("Fetching raw records from API/source...")
        records = fetch_source_records(settings)
    else:
        logger.info("Loading raw records from local snapshot: %s", settings.paths.raw_records_json)
        records = load_raw_records(settings.paths.raw_records_json)
    logger.info("Total raw records: %d", len(records))

    # 2. Clean data
    clean_df = build_clean_dataframe(records, now_utc())
    ensure_parent(settings.paths.clean_json)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    logger.info("Saved clean dataframe (%d rows) to %s and %s", len(clean_df), settings.paths.clean_json, settings.paths.clean_csv)

    # 3. Build Chroma index
    logger.info("Building ChromaDB collection '%s' with MiniLM embeddings...", settings.baseline_collection_name)
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)

    # 4. Generate or load evaluation test set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        logger.info("Generating evaluation benchmark test set...")
        build_test_set(clean_df, settings.paths.eval_testset)
    logger.info("Evaluation test set ready at: %s", settings.paths.eval_testset)

    # 5. Evaluate baseline pipeline
    logger.info("Evaluating baseline pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    logger.info("Baseline Metrics: Hit Rate = %.2f%%, Mean Token F1 = %.2f%%",
                bundle.summary["retrieval_hit_rate"] * 100, bundle.summary["mean_token_f1"] * 100)

    # 6. Run Data Quality Gate (GX 1.x) and Freshness SLA
    logger.info("Running Great Expectations 1.x quality checks...")
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    logger.info("Quality check success = %s", quality.get("success"))

    logger.info("Computing Freshness SLA report...")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    logger.info("Freshness SLA is_fresh = %s", freshness.get("is_fresh"))

    # 7. Generate Phase 1 markdown report
    source_summary = {
        "source_api": settings.source_api,
        "total_raw_records": len(records),
        "cleaned_records": len(clean_df),
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    logger.info("Phase 1 report generated at: %s", settings.paths.baseline_report)
    print("\n--- PHASE 1 BASELINE COMPLETED SUCCESSFULLY ---")
    print(f"Retrieval Hit Rate: {bundle.summary['retrieval_hit_rate'] * 100:.1f}%")
    print(f"Mean Token F1:      {bundle.summary['mean_token_f1'] * 100:.1f}%")
    print(f"Data Quality Pass:  {quality.get('success')}")
    print(f"Freshness SLA Pass: {freshness.get('is_fresh')}")
    print("------------------------------------------------\n")
