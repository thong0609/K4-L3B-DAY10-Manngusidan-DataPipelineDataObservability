# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 — L3B |
| Tên nhóm | Manngusidan |
| Repository | https://github.com/thong0609/K4-L3B-DAY10-Manngusidan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Tô Huy Thông | 2A202602608 | Trưởng nhóm / Pipeline Integrator | `core/`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| 2 | Trần Gia Khánh | 2A202602689 | Data Foundation & Recovery | `ingestion/crossref.py`, `ingestion/cleaning.py`, `data/raw/`, repair từ raw snapshot |
| 3 | Đinh Văn Bình | 2A202602830 | RAG & Vector Index | `retrieval/index.py`, `retrieval/embeddings.py`, 3 collection ChromaDB |
| 4 | Ngô Đinh Minh Nhật | 2A202602569 | Observability & Evaluation | `observability/quality.py`, `evaluation/testset.py`, `observability/reporting.py`, `ingestion/corruption.py` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline Baseline → Corruption → Repair. Ingestion đọc Crossref (API có retry/backoff cho 429/5xx, mặc định dùng lại snapshot `data/raw/` làm lineage anchor để kết quả tái lập được), parse 24 bài báo, loại bỏ thẻ JATS và chuẩn hóa thành `PaperRecord`. Cleaning sinh 24 dòng sạch với `age_days` và `text_for_embedding` 5 phần; dữ liệu được index vào ChromaDB (`papers-baseline`, MiniLM-L6-v2). Bộ test 10 câu phủ 4 dạng (`summary` 3, `authors` 3, `date` 2, `categories` 2). Baseline đạt hit rate 1.0 và token F1 1.0; Quality Gate GX 1.x (4 expectation) và Freshness SLA đều PASS (stale 1/24 = 4.17%).

Bộ corruption tiêm 6 loại lỗi (seed 42) làm 24 → 22 dòng. Pipeline trên dữ liệu bẩn **không hề báo lỗi** nhưng hit rate giảm còn 0.8, token F1 còn 0.9 (silent failure). Corruption ảnh hưởng rõ nhất đến agent là `truncate_title` (làm hỏng exact-title lookup → trả lời sai ngày) và `drop_latest_records` (mất tài liệu ground truth). Quality Gate bắt được lỗi: `unique(paper_id)` FAIL (6 dòng), `summary` length FAIL (3 dòng), freshness FAIL (stale 40.91% > 25%). Repair rebuild từ `data/raw/crossref_records.json` (idempotent) phục hồi 100% mọi chỉ số và gate PASS trở lại.

Giới hạn chính: LLM judge (Gemini) bị hết quota (429), nên `judge_accuracy`/`mean_judge_score` đến từ heuristic fallback dựa trên token F1, không phải đánh giá LLM thực.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (REFRESH_SOURCE=1) hoặc snapshot data/raw/crossref_response.json
    -> parse_crossref_payload -> data/raw/crossref_records.json
    -> build_clean_dataframe -> data/clean/papers_clean.{csv,json}
    -> MiniLM embedding + ChromaDB (papers-baseline)
    -> build_test_set (data/eval/test_set.json) -> evaluate_pipeline (baseline)
    -> GX 1.x quality gate + freshness SLA (data/quality/)
    -> corrupt_clean_dataframe (6 lỗi, seed 42) -> papers-corrupted -> re-evaluate
    -> repair_from_raw_snapshot -> papers-repaired -> re-evaluate
    -> corruption_report.md (Baseline vs Corrupted vs Repaired)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref `/works` hoặc snapshot | Retry 3 lần (backoff 2s, 4s) cho 429/5xx, fallback snapshot, parse DOI/title/abstract/author/subject/date | `data/raw/crossref_response.json`, `crossref_records.json` | Trần Gia Khánh |
| Cleaning | `PaperRecord` list | Chuẩn hóa whitespace, parse ngày, `age_days`, dedup `paper_id`, lọc dòng thiếu field | `data/clean/papers_clean.{csv,json}` | Trần Gia Khánh |
| Embedding/index | Clean dataframe | `all-MiniLM-L6-v2`, Chroma cosine, 1 collection/trạng thái | `data/chroma/`, `data/embeddings/*.json` | Đinh Văn Bình |
| Evaluation | Clean dataframe | 10 câu, 4 dạng, hit rate + token F1 + judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Ngô Đinh Minh Nhật |
| Observability | Dataframe mỗi trạng thái | GX 1.x ephemeral context, 4 expectation + freshness SLA | `data/quality/*_quality_report.json`, `*freshness_report.json` | Ngô Đinh Minh Nhật |
| Corruption/repair | Clean dataframe / raw snapshot | 6 corruption có log; repair rebuild idempotent từ raw | `data/results/corruption_log.json`, `data/clean/papers_clean_{corrupted,repaired}.*` | Ngô Đinh Minh Nhật / Trần Gia Khánh |
| Orchestration | Settings | Nối các bước, 3 collection tách biệt, in bảng so sánh | `data/reports/phase1_report.md`, `corruption_report.md` | Tô Huy Thông |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-3.6-flash` (quota hết → judge dùng heuristic fallback) |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 (`max_results=24`) |
| Retrieval `top_k` | 4 |
| Freshness threshold | `age_days > 180`, tối đa 25% stale |
| Random seed | 42 (corruption) |

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Đặt `REFRESH_SOURCE=1` để gọi lại Crossref API thay vì dùng snapshot; `REFRESH_TEST_SET=1` để sinh lại test set.

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công (exit 0) | 2026-09-26 10:33 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công (exit 0) | 2026-09-26 10:39 | `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API `https://api.crossref.org/works` (snapshot `data/raw/crossref_response.json`) |
| Query/filter | `query="agentic retrieval augmented generation large language model"`, `filter=from-pub-date:<today-180d>,has-abstract:true`, `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot offline đi kèm repo (được dùng cho mọi lần chạy nộp bài) |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | 3 lần, sleep 2s → 4s cho 429/500/502/503/504 và lỗi mạng; hết retry thì fallback snapshot |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | str (DOI, lowercase) | Có | Khóa duy nhất / document ID | Bỏ record; dedup theo khóa này |
| `title` | str | Có | Tiêu đề | Bỏ record |
| `summary` | str | Có | Abstract đã bỏ thẻ JATS/HTML | Bỏ record nếu rỗng |
| `authors` | list[str] | Không | "given family" | Để list rỗng |
| `categories` | list[str] | Không | Crossref `subject` | Để list rỗng; `primary_category` = phần tử đầu |
| `published` | str `YYYY-MM-DD` | Có | Ngày xuất bản (published → online → print → issued → created) | Bỏ record nếu không parse được |
| `updated` | str `YYYY-MM-DD` | Không | indexed/deposited | Fallback = `published` |
| `age_days` | int | Có (sinh ra) | `(run_date - published).days` | — |
| `text_for_embedding` | str | Có (sinh ra) | Title/Authors/Published/Categories/Summary | — |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | --: | --- |
| Loại thẻ `<jats:p>`, unescape HTML, gộp whitespace | Validity | 24 (mọi abstract trong snapshot có thẻ JATS) | `data/clean/papers_clean.json` không còn `<jats` |
| Loại record thiếu DOI/title/abstract/ngày | Completeness | 0 | 24 raw → 24 clean |
| Dedup theo `paper_id` (giữ bản `updated` mới nhất) | Uniqueness | 0 trên dữ liệu sạch | GX `unique(paper_id)` PASS |
| Chuẩn hóa ngày về ISO | Consistency | 24 | Cột `published` trong `papers_clean.csv` |

`text_for_embedding` ghép 5 dòng `Title: … / Authors: … / Published: … / Categories: … / Summary: …` để embedding chứa cả metadata dùng cho câu hỏi authors/date/categories. Document ID là DOI viết thường (ổn định giữa các lần chạy và giữa 3 trạng thái). `age_days` tính theo ngày UTC của lần chạy.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| Các `question_type` | summary (3), authors (3), date (2), categories (2) |
| Ground-truth document ID | DOI của paper sinh ra câu hỏi; 10 paper khác nhau, chọn rải đều trên danh sách sort theo `paper_id` (deterministic) |
| Embedding model | `all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB cosine: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | Gemini (`gemini-3.6-flash`) — bị 429, judge dùng heuristic fallback |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (sha1 `1ad06a21…`) |

Test set được giữ nguyên để mọi thay đổi metric chỉ đến từ dữ liệu (corruption/repair), không đến từ câu hỏi. Pipeline phase 1 chỉ sinh lại test set khi một ground-truth DOI không còn trong corpus hoặc khi đặt `REFRESH_TEST_SET=1`.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 24 items |
| Cleaned dataset | `data/clean/` | Có | 24 dòng (+ bản corrupted 22 dòng, repaired 24 dòng) |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/` | Có | 3 collection |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | |
| Quality/freshness | `data/quality/` | Có | baseline/corrupted/repaired |
| Baseline report | `data/reports/phase1_report.md` | Có | |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | --: | --- |
| `retrieval_hit_rate` | 1.0 | Cả 10 câu đều retrieve đúng DOI (QA ưu tiên exact-title lookup rồi mới semantic search) |
| `mean_token_f1` | 1.0 | QA trích xuất trực tiếp từ metadata nên khớp tuyệt đối ground truth |
| `judge_accuracy` | 1.0 | Heuristic fallback (F1 ≥ 0.5 → correct), không phải LLM judge |
| `mean_judge_score` | 5 | Heuristic fallback (F1 ≥ 0.95 → 5) |
| Ragas | N/A | Không bật `RUN_RAGAS=1` (chậm, và LLM đang hết quota) |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `ExpectTableRowCountToBeBetween` | Completeness (volume) | 5 – 5000 dòng | PASS (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` × 3 | Completeness | `paper_id`, `title`, `text_for_embedding` không null | PASS | idem |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` duy nhất | PASS | idem |
| `ExpectColumnValueLengthsToBeBetween` | Validity | `summary` ≥ 30 ký tự | PASS | idem |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean dataframe trước khi index (`age_days`) |
| Timestamp mới nhất | 2026-07-22 (cũ nhất 2026-03-28) |
| Ngưỡng freshness | `age_days > 180` là stale; tối đa 25% stale |
| Trạng thái baseline | Fresh |
| Lý do | 1/24 bài stale = 4.17% < 25% (`data/quality/freshness_report.json`) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | --: | --- | --- | --- |
| `drop_latest_records` | Bỏ 20% bài có `published` mới nhất | 5 | Row count giảm, latest_published lùi | latest 2026-07-22 → 2026-06-11; eval_004 mất ground truth (hit FAIL) | Rebuild từ raw snapshot |
| `blank_summary` | `summary = ""` | 3 | `summary` length FAIL | GX length FAIL (3 dòng); không trúng câu summary nào | idem |
| `inject_noise` | Chèn chuỗi rác vào giữa và cuối summary | 3 | Khó phát hiện bằng 4 expectation (độ dài vẫn hợp lệ) | Không bị GX bắt; embedding bị nhiễu | idem |
| `truncate_title` | Cắt title còn 7 ký tự | 3 | Không có expectation độ dài title | eval_003 exact lookup hỏng → trả lời sai ngày (F1 = 0) | idem |
| `stale_date` | `published` lùi 365 ngày, `age_days` +365 | 7 | Freshness FAIL | stale 40.91% > 25% → `is_fresh = False` | idem |
| `duplicate_rows` | Nhân đôi dòng đã bị làm bẩn | 3 | `unique(paper_id)` FAIL | GX unique FAIL (6 giá trị trùng) | idem (dedup + rebuild) |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi seed, số dòng vào/ra (24 → 22), số lượng theo từng loại, danh sách 21 `paper_id` bị ảnh hưởng và từng event với giá trị `before`/`after`.

Repair không sửa từng dòng lỗi mà rebuild toàn bộ từ `data/raw/crossref_records.json` — bản thô được lưu trước mọi bước biến đổi — nên không phụ thuộc vào việc phát hiện đủ mọi lỗi và không cần gọi lại API. Hàm `repair_from_raw_snapshot` chạy cleaning hai lần trên cùng snapshot và so sánh kết quả để chứng minh idempotent (`idempotent=True`), sau đó dữ liệu repaired phải qua lại Quality Gate (PASS) trước khi index vào `papers-repaired`.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | --: | --: | --: | --: | --: | --- |
| `retrieval_hit_rate` | 1.0 | 0.8 | 1.0 | -0.2 | 100% | eval_003 (title bị cắt) và eval_004 (paper bị drop) miss |
| `mean_token_f1` | 1.0 | 0.9 | 1.0 | -0.1 | 100% | Chỉ eval_003 sai; eval_004 đúng "nhờ may mắn" |
| `judge_accuracy` | 1.0 | 0.9 | 1.0 | -0.1 | 100% | Heuristic fallback, bám theo token F1 |
| `mean_judge_score` | 5.0 | 4.6 | 5.0 | -0.4 | 100% | Heuristic fallback |
| Quality checks pass/fail | 6/6 PASS | 4/6 PASS | 6/6 PASS | -2 check | 100% | unique + summary length FAIL |
| Freshness status | Fresh (4.17%) | Stale (40.91%) | Fresh (4.17%) | +36.7 điểm % stale | 100% | |

Kết luận nhân quả (đối chiếu `data/results/corruption_log.json` với `corrupted_answers.json`):

1. `truncate_title` trên paper `…1805` → không có expectation cho độ dài title nên gate không bắt riêng lỗi này → QA không tìm được exact title, semantic search trả về `…1817` → eval_003 (date) sai: hit FAIL, token F1 = 0.
2. `drop_latest_records` loại paper `…1808` → latest_published lùi về 2026-06-11 → eval_004 (categories) hit FAIL, nhưng câu trả lời vẫn đúng vì paper `…1820` có cùng categories: token F1 không phát hiện được retrieval sai — chỉ hit rate lộ ra.
3. `blank_summary`, `inject_noise`, `stale_date` rơi vào các paper mà câu hỏi không dùng trường bị hỏng (ví dụ eval_005/eval_009 hỏi summary của paper bị `stale_date`) → metric agent không đổi, nhưng GX/freshness vẫn FAIL. Đây chính là silent corruption: chỉ observability phát hiện được.
4. Repair từ raw snapshot → gate 6/6 PASS, freshness 4.17% → cả 4 metric agent trở về baseline.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Câu hỏi `authors`/`categories` trong test set luôn nhận câu trả lời là câu tóm tắt; ngoài ra khi chạy lại ingestion thì test set không còn câu `categories`.
- **Nguyên nhân:** (1) `retrieval/qa.py` chọn trường trả lời theo cụm từ khóa (`"who authored"`, `"what categories"`, `"when was"`); template ban đầu dùng "Who are the authors…" nên rơi vào nhánh summary. (2) Crossref API live không trả `subject` cho các bài mới, nên gọi lại API ghi đè snapshot bằng dữ liệu không có categories.
- **Cách xử lý:** Đồng bộ template câu hỏi với từ khóa của `qa.py`; `fetch_source_records` mặc định dùng lại snapshot (chỉ gọi API khi `REFRESH_SOURCE=1`); `build_test_set` fallback sang dạng câu hỏi khác kèm cảnh báo khi thiếu dữ liệu.
- **Cách xác minh:** `python script/run_phase1.py` → `data/eval/test_set.json` có đủ 4 dạng; baseline token F1 = 1.0.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| LLM judge hết quota (429) → heuristic fallback | `judge_*` chỉ phản ánh token F1 | Dùng provider khác/quota mới, chạy lại và so sánh `judge_accuracy` với heuristic |
| 4 expectation không bắt `inject_noise` và `truncate_title` | Lỗi làm sai câu trả lời vẫn lọt gate | Thêm expectation độ dài `title` ≥ 15 và regex cấm ký tự rác trong `summary`; kỳ vọng corrupted gate FAIL thêm 2 check |
| Corruption chọn dòng ngẫu nhiên, ít trùng với 10 paper trong test set | Mức sụt metric agent nhỏ (hit 0.8) so với mức hỏng dữ liệu (21/24 paper) | Tăng số câu hỏi hoặc đo theo từng paper bị ảnh hưởng |
| QA trích xuất trực tiếp metadata (không sinh bằng LLM) | Baseline luôn 1.0, khó đánh giá chất lượng sinh câu trả lời | Bật agent LLM + Ragas (`RUN_RAGAS=1`) khi có quota |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế. 
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
