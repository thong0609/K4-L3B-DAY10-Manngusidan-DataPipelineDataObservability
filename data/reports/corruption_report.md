# Corruption Impact Report: Baseline vs Corrupted vs Repaired

## 1. RAG Performance (3 states)

| Metric | Baseline | Corrupted | Repaired | Δ Corrupted | Recovery |
|---|---|---|---|---|---|
| Retrieval hit rate | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100% |
| Mean token F1 | 1.0000 | 0.9000 | 1.0000 | -0.1000 | 100% |
| Judge accuracy | 1.0000 | 0.9000 | 1.0000 | -0.1000 | 100% |
| Mean judge score (1-5) | 5.0000 | 4.6000 | 5.0000 | -0.4000 | 100% |

## 2. Data Quality Gate (Great Expectations 1.x)

| Check | Baseline | Corrupted | Repaired |
|---|---|---|---|
| **Overall gate** | PASS | FAIL | PASS |
| expect_table_row_count_to_be_between(table) | PASS (24) | PASS (22) | PASS (24) |
| expect_column_values_to_not_be_null(paper_id) | PASS | PASS | PASS |
| expect_column_values_to_be_unique(paper_id) | PASS | FAIL (6) | PASS |
| expect_column_values_to_not_be_null(title) | PASS | PASS | PASS |
| expect_column_values_to_not_be_null(text_for_embedding) | PASS | PASS | PASS |
| expect_column_value_lengths_to_be_between(summary) | PASS | FAIL (3) | PASS |

## 3. Freshness SLA

| Field | Corrupted | Repaired |
|---|---|---|
| latest_published | 2026-06-11 | 2026-07-22 |
| oldest_published | 2025-04-30 | 2026-03-28 |
| stale_rows | 9 | 1 |
| total_rows | 22 | 24 |
| stale_ratio | 0.4091 | 0.0417 |
| is_fresh | FAIL | PASS |

## 4. Injected Corruptions

Rows: 24 → 22 (seed=42), affected papers: 21

| Corruption | Events |
|---|---|
| drop_latest_records | 5 |
| blank_summary | 3 |
| inject_noise | 3 |
| truncate_title | 3 |
| stale_date | 7 |
| duplicate_rows | 3 |

## 5. Breakdown by Question Type (hit rate / token F1)

| Question type | Baseline | Corrupted | Repaired |
|---|---|---|---|
| authors | 1.00 / 1.00 (n=3) | 1.00 / 1.00 (n=3) | 1.00 / 1.00 (n=3) |
| categories | 1.00 / 1.00 (n=2) | 0.50 / 1.00 (n=2) | 1.00 / 1.00 (n=2) |
| date | 1.00 / 1.00 (n=2) | 0.50 / 0.50 (n=2) | 1.00 / 1.00 (n=2) |
| summary | 1.00 / 1.00 (n=3) | 1.00 / 1.00 (n=3) | 1.00 / 1.00 (n=3) |

### Questions degraded on corrupted data

| ID | Type | Hit | Token F1 | Ground truth | Corrupted answer |
|---|---|---|---|---|---|
| eval_003 | date | FAIL | 0.0000 | 2026-03-28 | 2026-06-05 |
| eval_004 | categories | FAIL | 1.0000 | Multi-Agent Systems, Artificial Intelligence | Multi-Agent Systems, Artificial Intelligence |

## 6. Analysis

- **Silent failure:** the corrupted pipeline completed without any exception, yet retrieval hit rate fell by 20.00% and mean token F1 by 10.00%. Nothing in the serving path signals the damage.
- **Observability catches it:** the GX gate on corrupted data returned `FAIL` (failed: expect_column_values_to_be_unique, expect_column_value_lengths_to_be_between); freshness stale ratio 40.91% vs SLA 25% → is_fresh=`False`.
- **Repair:** rebuilt 24 rows from the raw snapshot `data/raw/crossref_records.json` without calling the API (idempotent=True).
- **Recovery:** repaired hit rate 100.00% / token F1 100.00% vs baseline 100.00% / 100.00%; repaired quality gate `PASS`.
