# BÁO CÁO PHA 1: BASELINE DATA PIPELINE & OBSERVABILITY

## 1. Tổng Quan Nguồn Dữ Liệu (Data Ingestion)
- **Nguồn dữ liệu:** Crossref REST API
- **Tổng số bản ghi thu thập:** 24
- **Số bản ghi sau tiền xử lý (Cleaned):** 24
- **Mô hình Vector Embedding:** MiniLM (`all-MiniLM-L6-v2`)
- **Vector Database:** ChromaDB (Collection: `papers-baseline`)

## 2. Kiểm Định Chất Lượng Dữ Liệu (Data Quality Gate - Great Expectations 1.x)
- **Trạng thái kiểm định GX:** **`PASSED`**
- **Bộ quy tắc (Expectation Suite):** `papers_suite_baseline`
- **Chi tiết kiểm tra:**
  - Table row count between 15 and 30: **PASS**
  - Unique & Non-null `paper_id`: **PASS**
  - Non-null `title`: **PASS**
  - Minimum summary length (>= 20 chars): **PASS**

## 3. SLA Độ Tươi Mới (Freshness SLA)
- **Trạng thái SLA:** **`FRESH`** (Ngưỡng cảnh báo: > 25% bài báo > 180 ngày)
- **Ngày xuất bản mới nhất:** `2026-09-15`
- **Ngày xuất bản cũ nhất:** `2026-04-01`
- **Số bản ghi quá hạn (> 180 ngày):** `0 / 24` (0.0%)

## 4. Hiệu Năng RAG Benchmark (Baseline Evaluation)
- **Số câu hỏi đánh giá:** 10 câu (phủ 4 nhóm: summary, authors, date, categories)
- **Retrieval Hit Rate:** **`100.0%`**
- **Mean Token F1:** **`80.0%`**
- **Judge Accuracy:** **`80.0%`**
