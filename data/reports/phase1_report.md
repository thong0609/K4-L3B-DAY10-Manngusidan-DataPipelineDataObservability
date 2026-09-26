# Phase 1 Baseline Report

## 1. Source

| Field | Value |
|---|---|
| source_api | Crossref REST API |
| source_mode | raw_snapshot |
| source_query | agentic retrieval augmented generation large language model |
| source_filter | from-pub-date:2026-03-30,has-abstract:true |
| raw_records | 24 |
| clean_rows | 24 |
| run_date | 2026-09-26T03:27:35.914788+00:00 |
| llm_provider | gemini |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| collection_name | papers-baseline |
| test_set_size | 10 |

## 2. Baseline RAG Evaluation

| Metric | Value |
|---|---|
| Samples | 10 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score (1-5) | 5 |

Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`

## 3. Data Quality Gate (Great Expectations)

**Overall gate:** PASS (expectations: PASS, rows: 24)

| Expectation | Column | Result | Observed | Unexpected |
|---|---|---|---|---|
| expect_table_row_count_to_be_between | - | PASS | 24 | - |
| expect_column_values_to_not_be_null | paper_id | PASS | - | 0 |
| expect_column_values_to_be_unique | paper_id | PASS | - | 0 |
| expect_column_values_to_not_be_null | title | PASS | - | 0 |
| expect_column_values_to_not_be_null | text_for_embedding | PASS | - | 0 |
| expect_column_value_lengths_to_be_between | summary | PASS | - | 0 |

## 4. Freshness SLA

| Field | Value |
|---|---|
| latest_published | 2026-07-22 |
| oldest_published | 2026-03-28 |
| threshold_days | 180 |
| stale_rows | 1 |
| total_rows | 24 |
| stale_ratio | 0.0417 |
| max_stale_ratio | 0.2500 |
| is_fresh | PASS |

## 5. Demo Answers

| Question | Answer | Top retrieved |
|---|---|---|
| What is the summary of the paper 'Agentic Retrieval-Augmented Generation for Knowledge-Intensive Tasks'? | Retrieval-Augmented Generation (RAG) significantly improves large language model accuracy by grounding responses in retrieved passages. | Agentic Retrieval-Augmented Generation for Knowledge-Intensive Tasks |
| Who authored the paper 'Mitigating Ghost Vectors in Dense Retrieval via Idempotent Indexing'? | Duc Vu, Thao Dang | Mitigating Ghost Vectors in Dense Retrieval via Idempotent Indexing |
| When was the paper 'Evaluating Retrieval Precision with Token F1 and LLM Judges' published? | 2026-03-28 | Evaluating Retrieval Precision with Token F1 and LLM Judges |
