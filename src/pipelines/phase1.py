from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report
from observability.reporting import generate_phase1_report
from observability.self_healing import run_quality_gate_with_self_healing
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

DEMO_QUESTION_COUNT = 3


def _log(step: str, message: str) -> None:
    print(f"[phase1] {step:<10} {message}")


def _load_or_fetch_records(settings: Settings) -> tuple[list[PaperRecord], str]:
    """Chi goi API khi REFRESH_SOURCE=1 hoac chua co snapshot; mac dinh dung lai raw snapshot."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings), "crossref_api"
    return load_raw_records(settings.paths.raw_records_json), "raw_snapshot"


def save_clean_artifacts(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _load_or_build_test_set(df: pd.DataFrame, settings: Settings) -> list[dict[str, Any]]:
    path = settings.paths.eval_testset
    if path.exists() and not settings.refresh_test_set:
        test_set = read_json(path)
        known_ids = set(df["paper_id"])
        # Test set cu chi dung lai duoc neu moi doc ground truth van con trong corpus.
        if test_set and all(set(item["ground_truth_doc_ids"]) <= known_ids for item in test_set):
            return test_set
    return build_test_set(df, path)


def _run_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> list[dict[str, Any]]:
    demo = []
    for item in test_set[:DEMO_QUESTION_COUNT]:
        result = answer_question(item["question"], settings=settings, index=index)
        demo.append(
            {
                "question": item["question"],
                "answer": result.answer,
                "retrieved_titles": result.retrieved_titles,
            }
        )
    write_json(settings.paths.demo_answers, demo)
    return demo


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Baseline pipeline: Ingest -> Clean -> Index -> Testset -> Evaluate -> Quality gate -> Report."""
    run_date = now_utc()

    # 1. Ingest
    records, source_mode = _load_or_fetch_records(settings)
    _log("ingest", f"{len(records)} raw records ({source_mode})")

    # 2. Clean
    df = build_clean_dataframe(records, run_date)
    save_clean_artifacts(df, settings.paths.clean_csv, settings.paths.clean_json)
    _log("clean", f"{len(df)} clean rows -> {settings.paths.clean_csv}")

    # 2b. Quality gate truoc khi index: FAIL -> tu dong repair (bonus B2), khong index du lieu xau.
    healing = run_quality_gate_with_self_healing(df, settings, "baseline", repaired_report_name="baseline")
    if healing.healed:
        df = healing.df
        save_clean_artifacts(df, settings.paths.clean_csv, settings.paths.clean_json)
    quality = healing.final_quality
    _log("gate", f"success={quality['success']} self_heal_action={healing.action}")

    # 3. Index ChromaDB
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    _log("index", f"{len(index.documents)} docs in Chroma collection '{index.collection_name}'")

    # 4. Test set
    test_set = _load_or_build_test_set(df, settings)
    _log("testset", f"{len(test_set)} questions -> {settings.paths.eval_testset}")

    # 5. Evaluate baseline RAG
    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    _log("evaluate", f"hit_rate={metrics['retrieval_hit_rate']:.3f} token_f1={metrics['mean_token_f1']:.3f}")

    # 6. Freshness report (quality gate da chay o buoc 2b)
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    _log("quality", f"success={quality['success']} is_fresh={freshness['is_fresh']}")

    demo = _run_demo(settings, index, test_set)

    source_summary = {
        "source_api": settings.source_api,
        "source_mode": source_mode,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": len(df),
        "run_date": run_date.isoformat(),
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "test_set_size": len(test_set),
        "self_healing_action": healing.action,
        "demo": demo,
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, metrics, quality, freshness)
    _log("report", str(settings.paths.baseline_report))

    return {
        "source": source_summary,
        "metrics": metrics,
        "quality": quality,
        "freshness": freshness,
    }


def main() -> None:
    """Chay baseline pipeline end-to-end (xem `run_phase1_pipeline`)."""
    run_phase1_pipeline(load_settings())
