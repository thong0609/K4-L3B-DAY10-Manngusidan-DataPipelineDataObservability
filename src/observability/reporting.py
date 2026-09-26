from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|")


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines += ["| " + " | ".join(_fmt(cell) for cell in row) + " |" for row in rows]
    return lines


def _metrics_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    labels = {
        "samples": "Samples",
        "retrieval_hit_rate": "Retrieval hit rate",
        "mean_token_f1": "Mean token F1",
        "judge_accuracy": "Judge accuracy",
        "mean_judge_score": "Mean judge score (1-5)",
    }
    return [[label, metrics.get(key)] for key, label in labels.items()]


def _quality_lines(quality: dict[str, Any]) -> list[str]:
    lines = [f"**Overall gate:** {_fmt(quality.get('success'))} "
             f"(expectations: {_fmt(quality.get('expectations_success'))}, rows: {quality.get('row_count')})", ""]
    rows = [
        [check.get("expectation"), check.get("column"), check.get("success"),
         check.get("observed_value"), check.get("unexpected_count")]
        for check in quality.get("checks", [])
    ]
    return lines + _table(["Expectation", "Column", "Result", "Observed", "Unexpected"], rows)


def _freshness_rows(freshness: dict[str, Any]) -> list[list[Any]]:
    keys = ["latest_published", "oldest_published", "threshold_days", "stale_rows",
            "total_rows", "stale_ratio", "max_stale_ratio", "is_fresh"]
    return [[key, freshness.get(key)] for key in keys]


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    source_rows = [
        [key, value] for key, value in source_summary.items() if key != "demo"
    ]
    lines = ["# Phase 1 Baseline Report", "", "## 1. Source", ""]
    lines += _table(["Field", "Value"], source_rows)
    lines += ["", "## 2. Baseline RAG Evaluation", ""]
    lines += _table(["Metric", "Value"], _metrics_rows(metrics))
    ragas = metrics.get("ragas")
    if ragas:
        lines += ["", f"Ragas: `{ragas}`"]
    lines += ["", "## 3. Data Quality Gate (Great Expectations)", ""]
    lines += _quality_lines(quality)
    lines += ["", "## 4. Freshness SLA", ""]
    lines += _table(["Field", "Value"], _freshness_rows(freshness))
    demo = source_summary.get("demo") or []
    if demo:
        lines += ["", "## 5. Demo Answers", ""]
        lines += _table(
            ["Question", "Answer", "Top retrieved"],
            [[item["question"], item["answer"], (item.get("retrieved_titles") or ["-"])[0]] for item in demo],
        )
    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    corruption_log: dict[str, Any] | None = None,
    answers: dict[str, list[dict[str, Any]]] | None = None,
    repair_info: dict[str, Any] | None = None,
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    states = {"Baseline": baseline_metrics, "Corrupted": corrupted_metrics, "Repaired": repaired_metrics}
    lines = ["# Corruption Impact Report: Baseline vs Corrupted vs Repaired", ""]

    # 1. Metrics 3 trang thai.
    lines += ["## 1. RAG Performance (3 states)", ""]
    metric_rows = []
    for key, label in METRIC_LABELS.items():
        base, bad, fixed = (float(m.get(key) or 0.0) for m in states.values())
        metric_rows.append([label, base, bad, fixed, _signed(bad - base), _recovery(base, bad, fixed)])
    lines += _table(["Metric", "Baseline", "Corrupted", "Repaired", "Δ Corrupted", "Recovery"], metric_rows)

    # 2. Quality gate.
    lines += ["", "## 2. Data Quality Gate (Great Expectations 1.x)", ""]
    qualities = {"Baseline": baseline_quality or {}, "Corrupted": corrupted_quality, "Repaired": repaired_quality}
    lines += _table(
        ["Check", *qualities],
        [["**Overall gate**", *(q.get("success") if q else None for q in qualities.values())]]
        + [[check_key, *(_check_status(q, check_key) for q in qualities.values())] for check_key in _check_keys(qualities)],
    )

    # 3. Freshness.
    lines += ["", "## 3. Freshness SLA", ""]
    freshness = {"Corrupted": corrupted_freshness, "Repaired": repaired_freshness}
    lines += _table(
        ["Field", *freshness],
        [[key, *(f.get(key) for f in freshness.values())]
         for key in ("latest_published", "oldest_published", "stale_rows", "total_rows", "stale_ratio", "is_fresh")],
    )

    # 4. Corruption log.
    if corruption_log:
        lines += ["", "## 4. Injected Corruptions", ""]
        lines += [f"Rows: {corruption_log.get('input_rows')} → {corruption_log.get('output_rows')} "
                  f"(seed={corruption_log.get('seed')}), affected papers: {len(corruption_log.get('affected_paper_ids', []))}", ""]
        lines += _table(["Corruption", "Events"], [[k, v] for k, v in corruption_log.get("corruption_counts", {}).items()])

    # 5. Breakdown theo question type + cau hoi bi hong.
    if answers:
        lines += ["", "## 5. Breakdown by Question Type (hit rate / token F1)", ""]
        types = sorted({item["question_type"] for items in answers.values() for item in items})
        lines += _table(
            ["Question type", *(state.title() for state in answers)],
            [[qtype, *(_type_score(items, qtype) for items in answers.values())] for qtype in types],
        )
        degraded = [
            [item["id"], item["question_type"], item["retrieval_hit"], item["token_f1"],
             _short(item["ground_truth"]), _short(item["answer"])]
            for item in answers.get("corrupted", [])
            if not item["retrieval_hit"] or item["token_f1"] < 0.999
        ]
        lines += ["", "### Questions degraded on corrupted data", ""]
        lines += _table(["ID", "Type", "Hit", "Token F1", "Ground truth", "Corrupted answer"], degraded) if degraded else ["None."]

    # 6. Phan tich.
    lines += ["", "## 6. Analysis", ""]
    lines += _analysis(baseline_metrics, corrupted_metrics, repaired_metrics, corrupted_quality, repaired_quality,
                       corrupted_freshness, repair_info)
    write_text(report_path, "\n".join(lines) + "\n")


METRIC_LABELS = {
    "retrieval_hit_rate": "Retrieval hit rate",
    "mean_token_f1": "Mean token F1",
    "judge_accuracy": "Judge accuracy",
    "mean_judge_score": "Mean judge score (1-5)",
}


def _signed(value: float) -> str:
    return f"{value:+.4f}"


def _recovery(base: float, bad: float, fixed: float) -> str:
    drop = base - bad
    if abs(drop) < 1e-9:
        return "n/a (no drop)"
    return f"{(fixed - bad) / drop:.0%}"


def _check_key(check: dict[str, Any]) -> str:
    return f"{check.get('expectation')}({check.get('column') or 'table'})"


def _check_keys(qualities: dict[str, dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for quality in qualities.values():
        for check in quality.get("checks", []):
            if _check_key(check) not in keys:
                keys.append(_check_key(check))
    return keys


def _check_status(quality: dict[str, Any], key: str) -> str:
    for check in quality.get("checks", []):
        if _check_key(check) == key:
            status = "PASS" if check.get("success") else "FAIL"
            detail = check.get("unexpected_count")
            detail = check.get("observed_value") if detail is None else detail
            return f"{status} ({detail})" if detail not in (None, 0) else status
    return "-"


def _type_score(items: list[dict[str, Any]], qtype: str) -> str:
    rows = [item for item in items if item["question_type"] == qtype]
    if not rows:
        return "-"
    hit = sum(1 for item in rows if item["retrieval_hit"]) / len(rows)
    f1 = sum(item["token_f1"] for item in rows) / len(rows)
    return f"{hit:.2f} / {f1:.2f} (n={len(rows)})"


def _short(text: Any, limit: int = 70) -> str:
    value = str(text or "").replace("\n", " ")
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _analysis(
    baseline: dict[str, Any],
    corrupted: dict[str, Any],
    repaired: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repair_info: dict[str, Any] | None,
) -> list[str]:
    hit_drop = baseline["retrieval_hit_rate"] - corrupted["retrieval_hit_rate"]
    f1_drop = baseline["mean_token_f1"] - corrupted["mean_token_f1"]
    lines = [
        f"- **Silent failure:** the corrupted pipeline completed without any exception, yet retrieval hit rate fell by "
        f"{hit_drop:.2%} and mean token F1 by {f1_drop:.2%}. Nothing in the serving path signals the damage.",
        f"- **Observability catches it:** the GX gate on corrupted data returned "
        f"`{_fmt(corrupted_quality.get('success'))}` (failed: {', '.join(corrupted_quality.get('failed_expectations') or ['none'])}); "
        f"freshness stale ratio {corrupted_freshness.get('stale_ratio'):.2%} vs SLA {corrupted_freshness.get('max_stale_ratio'):.0%} "
        f"→ is_fresh=`{corrupted_freshness.get('is_fresh')}`.",
    ]
    if repair_info:
        lines.append(
            f"- **Repair:** rebuilt {repair_info.get('rows')} rows from the raw snapshot `{repair_info.get('source')}` "
            f"without calling the API (idempotent={repair_info.get('idempotent')})."
        )
    lines.append(
        f"- **Recovery:** repaired hit rate {repaired['retrieval_hit_rate']:.2%} / token F1 {repaired['mean_token_f1']:.2%} "
        f"vs baseline {baseline['retrieval_hit_rate']:.2%} / {baseline['mean_token_f1']:.2%}; "
        f"repaired quality gate `{_fmt(repaired_quality.get('success'))}`."
    )
    return lines
