# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Ngô Đinh Minh Nhật |
| MSSV | 2A202602569 |
| Khóa/Lớp | K4 — L3B |
| Tên nhóm | Manngusidan |
| Vai trò chính | Observability & Evaluation |
| Repository | https://github.com/thong0609/K4-L3B-DAY10-Manngusidan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Quality Gate (GX 1.x) | `src/observability/quality.py` — `run_data_quality_checks` | Clean/corrupted/repaired dataframe | `data/quality/{baseline,corrupted,repaired}_quality_report.json`, dict `{"success": bool, ...}` | Hoàn thành |
| Freshness SLA | `src/observability/quality.py` — `evaluate_freshness_sla`, `build_freshness_report` | Dataframe có `age_days`, `published` | `data/quality/*freshness_report.json`, cờ `is_fresh` | Hoàn thành |
| Benchmark test set | `src/evaluation/testset.py` — `build_test_set` | `data/clean/papers_clean.json` | `data/eval/test_set.json` (10 câu, 4 dạng) | Hoàn thành |
| Data corruption suite | `src/ingestion/corruption.py` — `corrupt_clean_dataframe` | Clean dataframe | Corrupted dataframe, `data/results/corruption_log.json` | Hoàn thành |
| Báo cáo | `src/observability/reporting.py` — `generate_phase1_report`, `generate_corruption_report` | Metrics, quality, freshness, answers, corruption log | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

Phần của tôi nằm giữa dữ liệu và đánh giá: nhận clean dataframe từ phần Ingestion/Cleaning (Trần Gia Khánh), sinh test set mà phần RAG (Đinh Văn Bình) dùng để đo retrieval, và cung cấp quality gate, corruption và report mà pipeline điều phối (Tô Huy Thông) gọi trong `phase1.py` và `corruption_flow.py`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug tích hợp test set ↔ QA | `retrieval/qa.py` (Đinh Văn Bình) | Đồng bộ template câu hỏi với từ khóa của `qa.py`; câu `authors`/`categories` trả về đúng trường (baseline token F1 = 1.0) |
| Phát hiện dữ liệu live thiếu `categories` | `ingestion/crossref.py` (Trần Gia Khánh) | Đề xuất dùng snapshot mặc định, chỉ gọi API khi `REFRESH_SOURCE=1` |
| Bật đánh giá Ragas | `evaluation/metrics.py` | Sửa lỗi `dict(result)` (`KeyError: 0`) với ragas 0.3.1, cài `pillow` còn thiếu, thêm `RunConfig` chống timeout; từng metric chạy được trên 1 mẫu, nhưng lần chạy đầy đủ bị chặn bởi quota Gemini free tier (20 request/ngày/model) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Cài GX 1.x ephemeral context + 4 expectation | `quality.py` | Baseline 6/6 check PASS; corrupted FAIL `unique(paper_id)` (6) và `summary` length (3) | `data/quality/baseline_quality_report.json`, `corrupted_quality_report.json` |
| Freshness SLA (`age_days > 180`, tối đa 25%) | `quality.py` | Baseline 1/24 = 4.17% → fresh; corrupted 9/22 = 40.91% → `is_fresh=False` | `data/quality/freshness_report.json`, `corrupted_freshness_report.json` |
| Sinh test set 10 câu | `testset.py` | summary 3, authors 3, date 2, categories 2; 10 paper khác nhau | `data/eval/test_set.json` |
| Tiêm 6 loại corruption | `corruption.py` | 24 → 22 dòng, 21 paper bị ảnh hưởng, log `before`/`after` | `data/results/corruption_log.json` |
| Báo cáo 3 trạng thái | `reporting.py` | Bảng metric + recovery, bảng GX, freshness, breakdown theo dạng câu hỏi, danh sách câu bị suy giảm | `data/reports/corruption_report.md` |

Output cụ thể: bảng Quality Gate trong `data/reports/corruption_report.md` cho thấy gate chuyển PASS → FAIL → PASS qua 3 trạng thái, và phần "Questions degraded on corrupted data" chỉ ra đúng 2 câu bị ảnh hưởng (eval_003, eval_004).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu hỏng không làm pipeline RAG crash: index vẫn build, agent vẫn trả lời, chỉ có chất lượng giảm (silent failure). Phần của tôi cần (1) phát hiện dữ liệu hỏng trước khi đưa vào vector store, (2) có bộ câu hỏi cố định để đo chất lượng giảm bao nhiêu, và (3) tạo lỗi có kiểm soát để chứng minh hai điều trên.

### Cách triển khai

- **Quality gate:** mỗi lần chạy tạo một GX ephemeral context mới (`add_pandas` → `add_dataframe_asset` → `add_batch_definition_whole_dataframe`), gom expectation vào một `ExpectationSuite` rồi `batch.validate(suite)`. Có 6 kiểm tra từ 4 loại expectation: row count 5–5000; not null cho `paper_id`, `title`, `text_for_embedding`; unique `paper_id`; `summary` ≥ 30 ký tự. Mỗi kết quả được rút gọn thành `expectation/column/success/unexpected_count/observed_value` để ghi JSON và đưa vào report.
- **Freshness:** đếm dòng có `age_days > settings.freshness_threshold_days` (180), tính `stale_ratio`, `is_fresh = stale_ratio ≤ 0.25`. `success` cuối cùng = expectations PASS **và** `is_fresh`.
- **Test set:** sort paper theo `paper_id`, chọn 10 vị trí rải đều (`i * n/10`) để deterministic và phủ toàn corpus; dạng câu hỏi xoay vòng summary → authors → date → categories. Ground truth lấy trực tiếp từ dữ liệu sạch (câu đầu của summary, `authors_joined`, `published`, `categories_joined`); `ground_truth_doc_ids` là DOI. Nếu không còn paper nào có dữ liệu cho một dạng (ví dụ không có categories) thì chuyển sang dạng khác và in cảnh báo.
- **Corruption:** bỏ 20% bài mới nhất trước, sau đó dùng `numpy.random.default_rng(42)` hoán vị các dòng còn lại và chia thành các tập **rời nhau** cho blank summary / noise / truncate title / stale date, để mỗi lỗi truy vết độc lập; cuối cùng nhân đôi một số dòng và rebuild `text_for_embedding` để embedding phản ánh đúng dữ liệu bẩn. Tỉ lệ stale chọn 35% để chắc chắn vượt SLA 25%.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Dataframe có các cột `paper_id`, `title`, `summary`, `text_for_embedding`, `published`, `age_days`, `authors_joined`, `categories_joined` |
| Output | Quality: dict `{success, expectations_success, failed_expectations, checks, freshness, report_path}`; test set: list 10 dict `{id, question_type, question, ground_truth, ground_truth_doc_ids}`; corruption: dataframe cùng schema + JSON log |
| Module phụ thuộc | `ingestion/cleaning.py` (schema + `_build_embedding_text`), `core/config.py` (ngưỡng freshness, đường dẫn), `core/utils.py` |
| Module sử dụng output | `pipelines/phase1.py`, `pipelines/corruption_flow.py`, `evaluation/metrics.py` (đọc test set) |
| Điều kiện lỗi cần xử lý | Dataframe < 10 paper (raise), paper thiếu authors/categories (bỏ qua hoặc fallback dạng câu hỏi), cột `age_days` không phải số (coerce), dataframe rỗng (`is_fresh=False`) |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res[\"success\"]}')"
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Quality check = True trên dữ liệu sạch; 10 câu hỏi; gate FAIL trên corrupted và PASS trên repaired.
- **Kết quả thực tế:** `Quality check status = True`; `Sinh được 10 câu hỏi test`; corruption flow exit 0, gate PASS / FAIL / PASS.
- **Artifact/log:** `data/quality/`, `data/eval/test_set.json`, `data/results/corruption_log.json`, `data/reports/corruption_report.md`.

Tôi cũng tự kiểm thử gate bằng một dataframe làm bẩn thủ công (thêm 2 dòng trùng, 3 summary "short", 9 dòng `age_days = 400`, 1 title null): gate trả `success=False` với 3 expectation FAIL và `is_fresh=False`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Freshness có thuộc về quality gate hay chỉ là cảnh báo riêng?
- **Các phương án đã cân nhắc:** (1) `success` chỉ phản ánh 4 expectation, freshness là báo cáo riêng; (2) `success = expectations AND is_fresh`, đồng thời vẫn trả riêng `expectations_success` và khối `freshness`.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Với RAG, dữ liệu cũ gây câu trả lời lỗi thời giống như dữ liệu sai schema, nên pipeline không nên index nó khi chưa được xem xét. Giữ riêng `expectations_success` giúp report vẫn phân biệt được "sai cấu trúc" với "cũ".
- **Bằng chứng quyết định phù hợp:** Corruption `stale_date` không làm FAIL expectation nào, chỉ freshness bắt được (40.91% > 25%). Nếu chọn phương án 1, lỗi này không làm gate đổi trạng thái.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ValueError: No remaining paper has usable data for a 'categories' question.`
- **Lệnh hoặc bước tái hiện:** Chạy lệnh kiểm tra bước 2 (`fetch_source_records`) khi có mạng, sau đó chạy `build_test_set` trên clean data mới.
- **Nguyên nhân gốc:** Crossref API live không trả trường `subject` cho các bài mới, nên cả 24 paper đều có `categories = []`. Lệnh kiểm tra bước 2 ghi đè snapshot mẫu (vốn có categories) bằng dữ liệu live.
- **Cách xử lý:** (1) `build_test_set` thử lần lượt các dạng câu hỏi khác khi dạng ưu tiên không có dữ liệu và in cảnh báo thay vì crash; (2) phối hợp sửa `fetch_source_records` để mặc định dùng lại snapshot, chỉ gọi API khi `REFRESH_SOURCE=1`; (3) khôi phục snapshot bằng `git checkout -- data/raw`.
- **Cách xác minh sau khi sửa:** Trên dữ liệu live: 10 câu (summary 5, authors 3, date 2) kèm cảnh báo; trên snapshot: 10 câu đủ 4 dạng.
- **Điều học được:** Nguồn dữ liệu bên ngoài có thể thay đổi schema thực tế mà không báo lỗi; artifact đánh giá phải gắn với một snapshot cố định thì kết quả mới tái lập được.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Crossref trả JSON gốc, được lưu nguyên vào `data/raw/crossref_response.json` rồi parse thành `PaperRecord` (`crossref_records.json`). Cleaning chuẩn hóa text, tính `age_days`, dedup, ghép `text_for_embedding`; chuỗi này được embed bằng MiniLM-L6-v2 và lưu vào ChromaDB kèm metadata (DOI, title, authors, categories, published).
2. Mỗi câu hỏi có DOI của paper sinh ra nó. Retrieval hit = DOI đó có nằm trong top-k tài liệu truy xuất hay không; token F1 so khớp câu trả lời với ground truth; judge chấm 1–5 (trong lần chạy này là heuristic fallback vì Gemini hết quota).
3. Quality checks kiểm tra cấu trúc và tính hợp lệ tại một thời điểm (số dòng, null, trùng, độ dài). Freshness đo tuổi dữ liệu so với thời điểm chạy: dữ liệu có thể hợp lệ hoàn toàn nhưng vẫn quá cũ, như corruption `stale_date`.
4. Nếu câu hỏi thay đổi thì không biết metric thay đổi vì dữ liệu hay vì câu hỏi. Giữ cùng test set (và cùng seed corruption) để sự khác biệt chỉ đến từ trạng thái dữ liệu.
5. Repair thành công khi: gate repaired PASS (`repaired_quality_report.json`), freshness trở về 4.17%, và `repaired_metrics.json` bằng baseline (hit rate 1.0, token F1 1.0), cùng với `idempotent=True`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | --: | --: | --: | --- |
| `retrieval_hit_rate` | 1.0 | 0.8 | 1.0 | Metric nhạy nhất với corruption |
| `mean_token_f1` | 1.0 | 0.9 | 1.0 | Bỏ sót eval_004 vì câu trả lời đúng "nhờ may mắn" |
| `judge_accuracy` | 1.0 | 0.9 | 1.0 | Heuristic fallback, bám theo token F1 |
| `mean_judge_score` | 5.0 | 4.6 | 5.0 | Heuristic fallback |
| Quality checks | 6/6 PASS | 4/6 PASS | 6/6 PASS | FAIL: unique `paper_id` (6), `summary` length (3) |
| Freshness status | Fresh 4.17% | Stale 40.91% | Fresh 4.17% | Bắt được `stale_date` mà expectation không bắt |

### Kết luận từ số liệu

1. `stale_date` (7 dòng) + `duplicate_rows` → freshness 40.91% > 25% và `unique(paper_id)` FAIL → gate FAIL; nhưng metric agent của các câu hỏi trên những paper này không đổi (eval_005, eval_009 hỏi summary). Observability phát hiện lỗi mà agent metric không thấy.
2. Repair rebuild từ `data/raw/crossref_records.json` → gate 6/6 PASS, freshness 4.17% → hit rate và token F1 trở về 1.0 (phục hồi 100%).

Corruption ảnh hưởng rõ nhất đến agent là `truncate_title`: `qa.py` ưu tiên tra exact title, title bị cắt còn 7 ký tự làm lookup thất bại, semantic search trả về paper khác nên eval_003 trả lời sai ngày (F1 = 0). Đáng chú ý là gate hiện tại không có expectation nào bắt lỗi này.

Kết quả khác kỳ vọng: (1) eval_004 retrieval miss (paper bị `drop_latest_records`) nhưng token F1 = 1.0, vì một paper khác có cùng categories. Tôi kiểm tra bằng cách đối chiếu `retrieved_doc_ids` trong `corrupted_answers.json` với `corruption_log.json`. Điều này cho thấy chỉ nhìn F1 có thể che mất lỗi retrieval. (2) `inject_noise` và `blank_summary` không làm giảm metric agent vì các paper bị chọn không trùng với câu hỏi `summary` nào; mức giảm tổng (0.8) nhỏ hơn nhiều so với mức hỏng dữ liệu (21/24 paper).

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Pipeline cần một raw snapshot bất biến làm lineage anchor: nó vừa là nguồn để repair, vừa giữ kết quả đánh giá tái lập được khi API thay đổi.
2. Quality checks và freshness bổ sung cho nhau: có lỗi chỉ expectation bắt được (trùng, summary rỗng), có lỗi chỉ freshness bắt được (ngày cũ), và có lỗi cả hai đều không bắt (title bị cắt, nhiễu trong summary).
3. Metric của agent không phải thước đo đầy đủ cho chất lượng dữ liệu: dữ liệu hỏng 21/24 paper nhưng hit rate chỉ giảm 20%, và token F1 có thể đúng dù retrieval sai.

### Nếu có thêm thời gian

Thêm 2 expectation: `title` dài tối thiểu 15 ký tự và `summary` không khớp regex ký tự rác (`#{3,}|@{3,}|<[^>]+>|�`). Cách đo: chạy lại `run_corruption_flow.py`, kỳ vọng corrupted gate FAIL thêm 2 check (truncate_title 3 dòng, inject_noise 3 dòng) trong khi baseline vẫn PASS.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Đinh Minh Nhật
**Ngày xác nhận:** 2026-09-26
