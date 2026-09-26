# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Tô Huy Thông |
| MSSV | 2A202602608 |
| Khóa/Lớp | K4/L3B |
| Tên nhóm | Manngusidan |
| Vai trò chính | Trưởng nhóm — Pipeline Integrator |
| Repository | https://github.com/thong0609/K4-L3B-DAY10-Manngusidan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline Pipeline | `src/pipelines/phase1.py` — `run_phase1_pipeline()` | Settings, raw records | `data/reports/phase1_report.md`, `baseline_metrics.json` | Hoàn thành |
| Corruption Flow | `src/pipelines/corruption_flow.py` — `run_corruption_flow_pipeline()` | Clean dataset, eval set | `data/reports/corruption_report.md`, bảng 3-state | Hoàn thành |
| Cấu hình hệ thống | `core/config.py`, `core/utils.py` | Environment variables, config | Đối tượng `Settings`, utility functions | Hoàn thành |
| Quản lý dự án & Tích hợp | Repository GitHub | Code từ các thành viên | Nhánh `main` nhất quán, artifact đầy đủ | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug UnicodeEncodeError (ký tự `→` trong PowerShell cp1258) | `corruption_flow.py` | Thay bằng `->` và `[UP]/[DOWN]`, pipeline chạy thành công |
| Fix TypeError khi tính date range (str - str) | `_build_phase1_report()` | Dùng `pd.to_datetime()` để convert trước khi tính |
| Hỗ trợ kiểm tra PYTHONPATH và version Python | Toàn bộ nhóm | Xác định cần dùng `.venv\Scripts\python.exe` thay vì `python` hệ thống (3.10 vs 3.12) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Kết nối Ingest → Clean → Index → Evaluate → Quality → Report | `phase1.py` | Pipeline chạy end-to-end, exit code 0 | `python script/run_phase1.py` |
| Kết nối Corrupt → Re-index → Evaluate → Repair → Compare | `corruption_flow.py` | Bảng 3-state in ra console + file report | `python script/run_corruption_flow.py` |
| Thiết lập cấu hình hệ thống & đường dẫn artifacts | `core/config.py`, `core/utils.py` | Quản lý path và setting linh hoạt | Đọc file code |
| Kiểm tra tính nhất quán & theo dõi Contributor tracking | GitHub branch `main` | Source code tích hợp, không conflict | Xem lịch sử commit GitHub |
| Sinh báo cáo markdown chi tiết Phase 1 | `data/reports/phase1_report.md` | 113 dòng, 6 section, đầy đủ số liệu | Xem file trực tiếp |
| Sinh báo cáo so sánh 3 trạng thái | `data/reports/corruption_report.md` | Bảng Baseline/Corrupted/Repaired với delta | Xem file trực tiếp |

Output cụ thể tôi tạo ra:

File `data/reports/phase1_report.md` gồm 6 section: Dataset Summary, Freshness SLA, GX Quality Gates (từng expectation), RAG Metrics (có cột diễn giải), Pipeline Architecture (ASCII diagram), Artifacts Generated. File này được sinh tự động mỗi lần chạy `run_phase1.py`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline Integrator phải kết nối các module độc lập (ingestion, cleaning, retrieval, evaluation, observability) thành một luồng thực thi nhất quán, đảm bảo artifacts được tạo đúng thứ tự và đường dẫn, không bị overwrite lẫn nhau giữa baseline/corrupted/repaired.

### Cách triển khai

`phase1.py::main()` thực hiện theo thứ tự:

1. Load settings từ `.env` qua `load_settings()`
2. Kiểm tra `raw_records_path.exists()` và `settings.refresh_source` để quyết định load local hay fetch API
3. Gọi `build_clean_dataframe()` với `run_date` để tính `age_days` nhất quán
4. Lưu 2 format (CSV + JSON) vào `data/clean/`
5. Gọi `LocalEmbeddingIndex.build()` với `embeddings_output_path` cố định → ChromaDB collection `papers-baseline`
6. Kiểm tra `eval_path.exists()` để tránh regenerate test set (giữ nhất quán khi so sánh)
7. Gọi `evaluate_pipeline()` → ghi `baseline_metrics.json` + `baseline_answers.json`
8. Gọi `run_data_quality_checks()` (GX 1.x ephemeral) + `build_freshness_report()`
9. Gọi `_build_phase1_report()` → ghi markdown report

`corruption_flow.py::main()` mở rộng thêm 3 collection ChromaDB riêng biệt (`papers-corrupted`, `papers-repaired`) và dùng **cùng** `eval_path` để so sánh 3 trạng thái là khách quan.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings` (load từ `.env`), `data/raw/crossref_records.json` |
| Output | `data/clean/papers_clean.csv`, `data/chroma/`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `retrieval.index`, `evaluation.metrics`, `observability.quality` |
| Module sử dụng output | `corruption_flow.py` đọc `data/clean/papers_clean.json` làm đầu vào |
| Điều kiện lỗi cần xử lý | `FileNotFoundError` khi `clean_json` chưa tồn tại (corruption flow yêu cầu phase1 chạy trước) |

### Cách xác minh

```powershell
$env:PYTHONPATH = "src"; .venv\Scripts\python.exe script/run_phase1.py
```

- **Kết quả mong đợi:** In ra `PHASE 1 COMPLETE!`, file `data/reports/phase1_report.md` được tạo
- **Kết quả thực tế:** ✅ Hit Rate 100%, GX success=True, is_fresh=True, report 113 dòng
- **Artifact:** `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi chạy `corruption_flow.py`, cần quyết định có rebuild ChromaDB index cho baseline hay dùng lại index đã có.
- **Các phương án đã cân nhắc:**
  1. Rebuild index baseline mỗi lần chạy corruption flow → tốn thời gian nhưng đảm bảo nhất quán.
  2. Load metrics baseline từ file JSON đã có, chỉ build 2 index mới (corrupted + repaired).
- **Phương án đã chọn:** Phương án 2 — load `baseline_metrics.json` sẵn có, chỉ build index cho corrupted và repaired.
- **Lý do:** Tránh tốn thời gian rebuild + gọi Gemini API đánh giá lại baseline. Đảm bảo số liệu baseline dùng trong báo cáo là chính xác từ Phase 1.
- **Bằng chứng:** Bảng so sánh cho kết quả Baseline = Repaired = 100% Hit Rate, chứng minh repair đã phục hồi hoàn toàn về trạng thái baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` khi chạy `run_corruption_flow.py` trên PowerShell
- **Lệnh tái hiện:** `python script/run_corruption_flow.py` → crash ngay tại dòng `print("BASELINE → CORRUPT → REPAIR")`
- **Nguyên nhân gốc:** Windows PowerShell mặc định dùng code page cp1258 (tiếng Việt), không encode được ký tự Unicode `→` (U+2192) và các emoji `🔴↓`, `🟢↑`, `➡️`
- **Cách xử lý:** Thay toàn bộ ký tự Unicode đặc biệt bằng ASCII tương đương: `→` thành `->`, `🔴↓` thành `[DOWN]`, `🟢↑` thành `[UP]`
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` → exit code 0, in đầy đủ bảng so sánh 3 trạng thái
- **Điều học được:** Khi viết pipeline dùng trên Windows, tránh dùng emoji/ký tự Unicode trong `print()`. Nếu cần, set `PYTHONIOENCODING=utf-8` hoặc dùng `sys.stdout.reconfigure(encoding='utf-8')`.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu từ Crossref đến vector index:** `crossref_response.json` (raw API format) → `parse_crossref_payload()` loại bỏ JATS XML, parse date-parts → `crossref_records.json` (PaperRecord) → `build_clean_dataframe()` tính age_days + text_for_embedding → `LocalEmbeddingIndex.build()` encode bằng MiniLM-L6-v2 → lưu vào ChromaDB PersistentClient.

2. **Evaluation set và ground-truth:** `build_test_set()` sinh 10 câu hỏi với `ground_truth_doc_ids` là `paper_id` của bài liên quan. `evaluate_pipeline()` dùng `index.search(question)` → lấy `retrieved_doc_ids` → so sánh với `ground_truth_doc_ids` để tính `retrieval_hit`. Ground-truth doc IDs được tạo từ chính dữ liệu đang index nên đảm bảo có thể retrieve được.

3. **Quality checks vs Freshness:** Quality checks (GX 1.x) kiểm tra **cấu trúc dữ liệu** — null, unique, row count, độ dài. Freshness monitoring kiểm tra **tính thời gian** — age_days > threshold. Hai cơ chế bổ sung nhau: GX bắt lỗi schema, Freshness bắt lỗi staleness.

4. **Phải dùng cùng test set:** Nếu test set thay đổi giữa 3 trạng thái, không thể biết chỉ số giảm do data bị corrupt hay do câu hỏi khó hơn. Dùng cùng test set đảm bảo biến duy nhất thay đổi là **chất lượng dữ liệu**.

5. **Repair thành công dựa trên:** `repaired_metrics.json` có `retrieval_hit_rate` = baseline, GX quality check `success=True`, `data/clean/papers_clean_repaired.csv` có đúng 24 rows như baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 100.00% | 60.00% | 100.00% | Giảm 40pp khi corrupt, phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 0.3965 | 0.2105 | 0.3965 | Giảm 47% do summary bị blank/noise, phục hồi đúng |
| `judge_accuracy` | 50.00% | 20.00% | 50.00% | Giảm 30pp — LLM judge nhận ra answer không chính xác |
| `mean_judge_score` | 2.40/5 | ~1.60/5 | 2.40/5 | Phục hồi về đúng baseline |
| Quality checks | PASS (6/6) | FAIL | PASS (6/6) | GX phát hiện đúng data bẩn |
| Freshness status | FRESH (4.17%) | STALE (nhiều hơn) | FRESH (4.17%) | Stale date corruption làm tỷ lệ tăng |

### Kết luận từ số liệu

1. **[6 kịch bản corruption]** → [GX failure, stale ratio tăng, duplicate rows] → [Hit Rate giảm 40pp, Token F1 giảm 47%, Judge Acc giảm 30pp] — đây là Silent Failure vì pipeline không throw exception.

2. **[Re-run `build_clean_dataframe()` từ raw]** → [GX success=True, freshness=FRESH, 24 rows clean] → [Hit Rate phục hồi 100%, Token F1 = 0.3965 = baseline] — Repair thành công hoàn toàn.

Corruption ảnh hưởng rõ nhất: **drop_latest_records** (xóa 20% bài mới nhất) vì làm mất document khỏi index → câu hỏi liên quan bài đó không còn retrieve được, Hit Rate giảm trực tiếp.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data Pipeline:** Idempotent design — mỗi lần chạy lại từ raw source đều cho kết quả sạch như nhau. Đây là nền tảng của self-healing.
2. **Data Observability:** GX 1.x ephemeral context không cần file config phức tạp — có thể tích hợp vào bất kỳ pipeline Python nào trong vài dòng code. Freshness SLA giúp phát hiện lỗi mà schema validation không bắt được.
3. **RAG & Data Quality:** Chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng AI — giảm 47% Token F1 chỉ từ việc corrupt 15-20% records. Đây là lý do Data Observability là thiết yếu trong production AI system.

### Nếu có thêm thời gian

Tích hợp **real-time alerting**: khi GX quality gate fail, tự động gửi Slack/email notification thay vì chỉ ghi file JSON. Có thể đo bằng cách chạy corruption flow và kiểm tra notification được gửi trong vòng <30 giây.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Tô Huy Thông  
**Ngày xác nhận:** 2026-09-26
