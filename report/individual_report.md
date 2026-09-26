# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                       |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| Họ và tên          | [Điền Họ và tên của bạn - ví dụ: Nguyễn Văn Khánh / khanh205]                                   |
| MSSV               | [Điền MSSV của bạn]                                                                            |
| Khóa/Lớp           | K4 / L3B                                                                                       |
| Tên nhóm           | Manngusidan                                                                                    |
| Vai trò chính      | Phụ trách Data Observability & Benchmark Evaluation (Observability & Evaluation Engineer)       |
| Repository         | https://github.com/thong0609/K4-L3B-DAY10-Manngusidan-DataPipelineDataObservability           |
| Ngày hoàn thành    | 2026-09-26                                                                                     |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Data Quality Gate & Freshness SLA** | `src/observability/quality.py`<br>- `run_data_quality_checks()`<br>- `build_freshness_report()` | Cleaned `pd.DataFrame`, `Settings` (ngưỡng SLA 180 ngày) | `data/quality/baseline_quality_report.json`<br>`data/quality/corrupted_quality_report.json`<br>`data/quality/freshness_report.json`<br>`data/quality/corrupted_freshness_report.json` | Hoàn thành |
| **Evaluation Benchmark Test Set** | `src/evaluation/testset.py`<br>- `build_test_set()` | Cleaned `pd.DataFrame`, đường dẫn lưu file | `data/eval/test_set.json` (10 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ kèm ground truth & doc IDs) | Hoàn thành |
| **Synthetic Data Corruption Suite** | `src/ingestion/corruption.py`<br>- `corrupt_clean_dataframe()` | Cleaned `pd.DataFrame`, đường dẫn log | DataFrame bị tiêm 6 lỗi dữ liệu, `data/results/corruption_log.json` | Hoàn thành |
| **Observability Reporting** | `src/observability/reporting.py`<br>- `generate_phase1_report()`<br>- `generate_corruption_report()` | Source summary, metrics RAG, kết quả GX, báo cáo Freshness | `data/reports/phase1_report.md`<br>`data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Rà soát & kiểm định Ingestion & Data Cleaning** | Đinh Văn Bình (`src/ingestion/crossref.py`, `cleaning.py`) | Kiểm tra tính nhất quán giữa cấu trúc raw `PaperRecord` và schema sạch (`text_for_embedding`, `age_days`), đảm bảo 24 bản ghi sạch đạt tiêu chuẩn trước khi đưa vào kiểm định chất lượng và embedding. |
| **Phối hợp tích hợp Pipeline End-to-End** | Tô Huy Thông (`src/pipelines/phase1.py`, `corruption_flow.py`) | Tích hợp các hàm kiểm tra GX 1.x, Freshness SLA và xuất báo cáo markdown tự động vào luồng chạy chính; thống nhất việc chia tách 3 collection riêng biệt trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`). |
| **Xử lý tương thích Terminal Windows/PowerShell** | Toàn nhóm | Đảm bảo các định dạng chuỗi log và ký tự báo cáo chạy an toàn trên Windows PowerShell (tránh các lỗi mã hóa ký tự Unicode cp1258). |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Thiết lập Data Quality Gate chuẩn **Great Expectations 1.x** (Ephemeral Context) | `src/observability/quality.py` — `run_data_quality_checks` | Chốt chặn 5 expectations: kiểm tra số lượng dòng [15, 30], non-null `paper_id` & `title`, unique `paper_id`, và độ dài summary >= 20 ký tự. | Chạy kiểm tra độc lập và kiểm tra qua file `data/quality/baseline_quality_report.json` (`success: true`, 5/5 pass). |
| Xây dựng hệ thống giám sát Freshness SLA | `src/observability/quality.py` — `build_freshness_report` | Tự động tính toán `age_days`, xác định ngày mới/cũ nhất, phát hiện vi phạm SLA nếu tỷ lệ bài quá hạn (>180 ngày) vượt quá 25%. | Xuất `data/quality/freshness_report.json` (`is_fresh: true`, 0% quá hạn ở baseline vs 30.43% vi phạm ở corrupted). |
| Xây dựng Benchmark Test Set 10 câu hỏi chuẩn hóa | `src/evaluation/testset.py` — `build_test_set` | Bộ test cố định gồm 10 câu hỏi phủ đủ 4 nhóm: `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) có `ground_truth_doc_ids`. | Sinh ra `data/eval/test_set.json`, được sử dụng làm thước đo bất biến xuyên suốt 3 trạng thái. |
| Giả lập 6 kịch bản Data Corruption & Logging | `src/ingestion/corruption.py` — `corrupt_clean_dataframe` | Mô phỏng thực tế 6 dạng lỗi dữ liệu: drop 20% bài mới, xóa trắng summary, chèn noise, cắt ngắn title, lùi date về 2010, nhân bản duplicate rows. | `data/results/corruption_log.json` ghi nhận đầy đủ 6 hành động tiêm lỗi; GX Quality Gate báo FAIL và Freshness SLA báo STALE. |
| Lập báo cáo đối chiếu định lượng 3 trạng thái | `src/observability/reporting.py` — `generate_corruption_report` | Bảng so sánh trực quan định lượng giữa Baseline vs Corrupted vs Repaired, chỉ rõ hiện tượng Silent Failure và năng lực tự phục hồi. | Xuất file `data/reports/corruption_report.md` đầy đủ số liệu đối chiếu. |

### Output cụ thể tạo ra và giúp xác minh:
- **`data/quality/baseline_quality_report.json` & `data/quality/corrupted_quality_report.json`**: Minh chứng rõ ràng Data Quality Gate hoạt động chính xác — đạt 100% (5/5 pass) ở baseline và bắt đúng 2 lỗi nghiêm trọng ở corrupted (`expect_column_values_to_be_unique` phát hiện 6 bản ghi trùng lặp 26.09%, `expect_column_value_lengths_to_be_between` phát hiện 2 bản ghi summary bị xóa trắng).
- **`data/results/corruption_log.json`**: Lưu vết chi tiết từng loại lỗi tiêm vào dữ liệu, danh sách `paper_id` bị tác động, phục vụ truy vết nguồn gốc (Data Lineage).
- **`data/reports/corruption_report.md`**: Bảng tổng kết 3 trạng thái phản ánh sự sụt giảm của Retrieval Hit Rate từ 100% xuống 60%, Token F1 từ 80% xuống 40.7% khi bị tiêm lỗi, và sự phục hồi hoàn toàn 100% sau Idempotent Repair.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong các hệ thống RAG Agent phục vụ sản xuất, sự cố dữ liệu thường không gây sập chương trình (crash) mà gây ra hiện tượng **Silent Failure (suy giảm ngầm)**:
- Pipeline ingestion vẫn nạp dữ liệu, vector index vẫn sinh embedding và LLM vẫn trả lời người dùng, nhưng nội dung trả lời bị sai lệch, ảo giác hoặc trích xuất không đúng tài liệu do dữ liệu bị bẩn (mất tài liệu mới, text bị cắt ngắn, trùng lặp hoặc thông tin đã quá cũ).
- Nếu không có lớp **Data Observability**, đội ngũ kỹ thuật hoàn toàn mù mờ trước sự suy giảm chất lượng cho đến khi người dùng khiếu nại.
- Nhiệm vụ của tôi là xây dựng "mắt thần quan sát dữ liệu": chốt chặn kiểm định chất lượng dữ liệu tĩnh (Data Quality Gate) và giám sát biến động độ trôi thời gian (Freshness SLA), đồng thời xây dựng bộ công cụ đo lường thực nghiệm (Corruption Suite & Benchmark Testset) để định lượng hóa chính xác mức độ ảnh hưởng của dữ liệu bẩn lên AI Agent.

### Cách triển khai

1. **Data Quality Gate với Great Expectations 1.x (GX 1.x):**
   - Sử dụng mô hình **Ephemeral Context** (`gx.get_context(mode="ephemeral")`) để không phụ thuộc vào thư mục cấu hình YAML cồng kềnh, tối ưu cho môi trường CI/CD và pipeline Python tự động.
   - Kết nối dữ liệu in-memory qua Fluent Data Sources: `context.data_sources.add_pandas()`, tạo DataFrame Asset và Batch Definition dạng `add_batch_definition_whole_dataframe()`.
   - Thiết lập `ExpectationSuite` với 5 quy tắc cốt lõi:
     - `ExpectTableRowCountToBeBetween(min_value=15, max_value=30)`: Chặn lỗi rỗng dữ liệu hoặc thu thập vượt ngưỡng bất thường.
     - `ExpectColumnValuesToNotBeNull(column="paper_id")`: Đảm bảo định danh tài liệu luôn tồn tại.
     - `ExpectColumnValuesToNotBeNull(column="title")`: Đảm bảo tiêu đề bắt buộc phải có để hiển thị và trích xuất.
     - `ExpectColumnValuesToBeUnique(column="paper_id")`: Khử trùng lặp khóa chính, ngăn ngừa vector index bị phình to vô ích.
     - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20)`: Đảm bảo tóm tắt bài báo có độ dài tối thiểu, đủ ngữ cảnh cho mô hình embedding.
   - Chạy kiểm định thông qua `gx.ValidationDefinition` và trích xuất kết quả ra file JSON chi tiết (thống kê số lượng vi phạm, tỷ lệ vi phạm, danh sách giá trị vi phạm cụ thể).

2. **Freshness SLA Monitoring:**
   - Dựa trên trường `age_days` đã tính từ cleaning (`age_days = (run_date - published).days`).
   - Tính toán tỷ lệ `stale_ratio = (stale_rows / total_rows)` với điều kiện bài báo quá hạn khi `age_days > 180`.
   - Quy tắc SLA: Nếu `stale_ratio > 0.25` (hơn 25% bài báo cũ hơn 6 tháng), hệ thống lập tức gắn cờ cảnh báo `is_fresh = False`.

3. **Benchmark Test Set Generator:**
   - Hàm `build_test_set()` tự động hóa việc sinh 10 câu hỏi kiểm thử đại diện từ tập dữ liệu sạch ban đầu theo 4 nhóm nghiệp vụ cụ thể:
     - Nhóm `summary`: Hỏi tóm tắt nội dung bài báo, ground truth lấy câu đầu tiên của abstract (`first_sentence(row["summary"])`).
     - Nhóm `authors`: Hỏi danh sách tác giả, ground truth là `authors_joined`.
     - Nhóm `date`: Hỏi ngày công bố, ground truth là chuỗi ISO `published`.
     - Nhóm `categories`: Hỏi phân loại lĩnh vực, ground truth là `categories_joined`.
   - Mỗi câu hỏi được cố định kèm `ground_truth_doc_ids: [paper_id]` để làm cơ sở tính toán Retrieval Hit Rate chuẩn xác.

4. **Synthetic Data Corruption Suite:**
   - Triển khai hàm `corrupt_clean_dataframe()` mô phỏng 6 dạng lỗi dữ liệu bẩn điển hình:
     - *Drop latest records*: Cắt bỏ 20% bài báo mới nhất theo ngày xuất bản để giả lập mất mát dữ liệu thời gian thực.
     - *Blank summary*: Xóa trắng nội dung tóm tắt của 2 bài báo về rỗng `""`.
     - *Inject noise*: Chèn các chuỗi ký tự rác `[CORRUPTED_NOISE_$$$#@!] * 8` vào tóm tắt của 2 bài báo.
     - *Truncate title*: Rút gọn tiêu đề của 2 bài báo xuống còn 3 ký tự (`"Bad"`).
     - *Stale date*: Lùi ngày xuất bản của 35% bản ghi về năm 2010 (`age_days = 5500`) nhằm kích hoạt cảnh báo Freshness SLA.
     - *Duplicate rows*: Nhân bản 3 bản ghi đã có nhằm vi phạm tính duy nhất (`ExpectColumnValuesToBeUnique`).
   - Tái tạo lại trường `text_for_embedding` bằng hàm `_build_embedding_text()` sau khi biến đổi để phản ánh trực tiếp sự méo mó dữ liệu vào không gian vector.
   - Ghi lại toàn bộ lịch sử can thiệp vào `data/results/corruption_log.json`.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Cleaned DataFrame từ `src/ingestion/cleaning.py` (24 dòng, 16 cột), đối tượng `Settings` chứa ngưỡng cấu hình đường dẫn và SLA (180 ngày). |
| **Output** | - Các file JSON kiểm định: `baseline_quality_report.json`, `corrupted_quality_report.json`, `freshness_report.json`, `corrupted_freshness_report.json`.<br>- File JSON benchmark: `data/eval/test_set.json`.<br>- DataFrame bị làm bẩn và file `data/results/corruption_log.json`.<br>- File báo cáo Markdown: `data/reports/phase1_report.md` và `data/reports/corruption_report.md`. |
| **Module phụ thuộc** | `core.config.Settings`, `core.utils` (`write_json`, `ensure_parent`, `first_sentence`), `ingestion.cleaning._build_embedding_text`. |
| **Module sử dụng output** | `src/pipelines/phase1.py` dùng kết quả GX và Freshness để xuất báo cáo Pha 1; `src/pipelines/corruption_flow.py` nạp testset và DataFrame bị corrupt để đánh giá suy giảm và so sánh đối chiếu 3 trạng thái. |
| **Điều kiện lỗi cần xử lý** | - Xử lý an toàn khi DataFrame rỗng (`len(df) < 10` trong testset ném ngoại lệ rõ ràng thay vì crash ngầm).<br>- Tương thích các kiểu dữ liệu ngày tháng khi DataFrame bị khuyết trường `age_days` hoặc `published`.<br>- GX 1.x Ephemeral context tránh tạo xung đột tên (data source/asset name) bằng cách gắn hậu tố `report_name` (`papers_source_baseline`, `papers_source_corrupted`). |

### Cách xác minh

Kiểm tra trực tiếp module Quality & Observability:
```powershell
.venv\Scripts\python.exe -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Quality check status = {res[\"success\"]}')"
```

Kiểm tra trực tiếp module Test Set:
```powershell
.venv\Scripts\python.exe -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Test questions generated: {len(ts)}')"
```

Chạy toàn bộ quy trình kiểm chứng 3 trạng thái:
```powershell
.venv\Scripts\python.exe script/run_corruption_flow.py
```

- **Kết quả mong đợi:**
  - Quality check trên dữ liệu clean: `success = True`, Freshness SLA: `is_fresh = True`.
  - Sinh đủ 10 câu hỏi test với đầy đủ 4 nhóm câu hỏi và ground truth.
  - Trên dữ liệu corrupted: Quality check chuyển sang `success = False` (bắt được 2 vi phạm), Freshness chuyển sang `is_fresh = False` (tỷ lệ bài cũ 30.43% > 25%).
  - Console và file báo cáo `data/reports/corruption_report.md` in ra bảng đối chiếu 3 trạng thái với đầy đủ các chỉ số định lượng.
- **Kết quả thực tế:**
  - Hoàn toàn chính xác theo thiết kế. Console in ra bảng so sánh rõ ràng, file `data/reports/corruption_report.md` và `data/results/corruption_log.json` được tạo đầy đủ.
- **Artifacts:**
  - `data/quality/baseline_quality_report.json`
  - `data/quality/corrupted_quality_report.json`
  - `data/quality/freshness_report.json`
  - `data/quality/corrupted_freshness_report.json`
  - `data/eval/test_set.json`
  - `data/results/corruption_log.json`
  - `data/reports/corruption_report.md`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thiết kế module kiểm định dữ liệu với Great Expectations 1.x, nhóm cần chọn giữa việc khởi tạo cấu hình lưu trên ổ đĩa (File-based Context với thư mục `great_expectations/` chứa các file YAML) hay sử dụng mô hình hoàn toàn lập trình trong bộ nhớ (In-memory Ephemeral Context).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (File-based Context):* Dùng CLI của Great Expectations sinh thư mục cấu hình `great_expectations/` với các file YAML truyền thống.
  2. *Phương án 2 (Ephemeral In-memory Context):* Khởi tạo context động qua code bằng `gx.get_context(mode="ephemeral")`, định nghĩa Data Sources, Data Assets, Batch Definitions và Expectation Suites trực tiếp trong bộ nhớ lúc runtime.
- **Phương án đã chọn:** Phương án 2 — Ephemeral In-memory Context.
- **Lý do:**
  - *Tính độc lập và di động (Portability):* File-based context tạo ra rất nhiều file YAML cấu hình phức tạp, dễ bị lỗi đường dẫn tuyệt đối khi clone code sang máy khác hoặc chạy trên GitHub Actions. Ephemeral Context loại bỏ hoàn toàn các phụ thuộc này.
  - *Tốc độ và sự linh hoạt (Speed & Lifecycle):* Trong luồng `corruption_flow.py`, dữ liệu liên tục thay đổi qua 3 trạng thái (Baseline, Corrupted, Repaired). Ephemeral Context cho phép tạo nhanh các suite kiểm định độc lập (`papers_suite_baseline`, `papers_suite_corrupted`, `papers_suite_repaired`) mà không lo đè dữ liệu hay xung đột tài nguyên lock file.
- **Bằng chứng quyết định phù hợp:** Toàn bộ quá trình chạy kiểm định dữ liệu trong pipeline diễn ra gần như tức thì (<0.8 giây), không sinh ra file rác cấu hình trong Git, và xuất ra các file JSON báo cáo có cấu trúc chuẩn mực tại `data/quality/`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  AttributeError: 'DataContext' object has no attribute 'add_expectation_suite'
  hoặc:
  UserWarning: Great Expectations v0.x Checkpoint/BatchRequest syntax is deprecated and will fail in GX 1.0+
  ```
- **Lệnh hoặc bước tái hiện:** Chạy thử nghiệm ban đầu của `quality.py` khi sử dụng code mẫu dựa trên cú pháp cũ của Great Expectations (v0.18 trở về trước).
- **Nguyên nhân gốc:** Great Expectations 1.x đã tái cấu trúc toàn diện kiến trúc (Core API Redesign). Các khái niệm cũ như `RuntimeDataConnector`, `BatchRequest`, `add_expectation_suite()` trực tiếp từ context đã bị thay thế hoàn toàn bởi kiến trúc Fluent Data Sources: `context.data_sources.add_pandas()` -> `add_dataframe_asset()` -> `add_batch_definition_whole_dataframe()` -> `gx.ValidationDefinition`.
- **Cách xử lý:** Tôi đã nghiên cứu tài liệu chính thức của GX 1.x và tái cấu trúc lại toàn bộ hàm `run_data_quality_checks()`:
  - Khởi tạo context: `context = gx.get_context(mode="ephemeral")`.
  - Tạo source & asset: `data_source = context.data_sources.add_pandas(name=...)`, `data_asset = data_source.add_dataframe_asset(...)`.
  - Tạo batch definition: `batch_def = data_asset.add_batch_definition_whole_dataframe(...)`.
  - Tạo suite mới qua `suite = gx.ExpectationSuite(name=...)` và thêm các expectation chuẩn mới từ namespace `great_expectations.expectations` (`gxe`).
  - Đóng gói kiểm tra qua `gx.ValidationDefinition(name=..., data=batch_def, suite=suite)` và kích hoạt chạy với tham số `batch_parameters={"dataframe": df}`.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra độc lập `run_data_quality_checks()` trên PowerShell, kết quả trả về mã trạng thái sạch, không còn bất kỳ cảnh báo deprecation nào, file `baseline_quality_report.json` lưu đúng định dạng cấu trúc kết quả chi tiết.
- **Điều học được:** Khi làm việc với các thư viện mã nguồn mở có bước nhảy vọt phiên bản lớn (major release như v0.x -> v1.x), tuyệt đối không copy code cũ mà phải bám sát kiến trúc API chuẩn mới nhất để tránh nợ kỹ thuật (technical debt) và lỗi sập pipeline trong tương lai.

---

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
- *Thu thập (Ingestion):* Dữ liệu bắt đầu từ Crossref REST API (hoặc fallback từ `data/raw/crossref_response.json`). Hàm `parse_crossref_payload()` loại bỏ các thẻ JATS XML (`<jats:p>`), chuyển cấu trúc mảng `date-parts` thành chuỗi ngày ISO `YYYY-MM-DD`, chuẩn hóa danh sách tác giả và lưu thành danh sách `PaperRecord` tại `data/raw/crossref_records.json` (bản snapshot gốc bất biến).
- *Làm sạch & Mô hình hóa (Cleaning & Modeling):* `build_clean_dataframe()` loại bỏ trùng lặp theo `paper_id`, tính toán trường `age_days = (run_date - published).days` và ghép trường dữ liệu giàu ngữ cảnh `text_for_embedding` (bao gồm Title, Authors, Published, Categories, Summary) rồi lưu ra `papers_clean.csv` / `papers_clean.json`.
- *Vector Indexing:* Module `LocalEmbeddingIndex` nạp DataFrame sạch, chuyển từng bản ghi thành Document có metadata, sử dụng mô hình Sentence-Transformers `all-MiniLM-L6-v2` để sinh vector 384 chiều và lưu trữ lâu dài vào ChromaDB (collection `papers-baseline` qua `PersistentClient`).

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
- `build_test_set()` tạo ra 10 câu hỏi bao quát 4 nhóm nghiệp vụ với câu trả lời chuẩn (`ground_truth`) và mã định danh bài báo gốc chuẩn (`ground_truth_doc_ids: [paper_id]`).
- Khi đánh giá, câu hỏi được mã hóa vector và tìm kiếm trên ChromaDB để lấy danh sách `retrieved_doc_ids` (top-k).
- Chỉ số `retrieval_hit_rate` được tính bằng tỷ lệ số câu hỏi mà `ground_truth_doc_ids` xuất hiện trong `retrieved_doc_ids`.
- Sau đó, ngữ cảnh của tài liệu tìm được được gửi vào QA Agent để sinh câu trả lời dự đoán. Chất lượng câu trả lời được đo lường bằng:
  - `mean_token_f1`: Đo độ trùng khớp từ vựng (precision & recall ở cấp độ token) giữa câu trả lời dự đoán và `ground_truth`.
  - `judge_accuracy` & `mean_judge_score`: Sử dụng LLM Judge (hoặc Mock Judge) đối chiếu ngữ nghĩa để đánh giá xem câu trả lời có chính xác và trung thực với câu hỏi hay không.

**3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
- *Quality checks (Great Expectations 1.x):* Giám sát **tính toàn vẹn về cấu trúc và ràng buộc tĩnh (Structural & Semantic Constraints)** của bảng dữ liệu — ví dụ: số lượng dòng có nằm trong khoảng cho phép không, các cột khóa có bị rỗng hay trùng lặp không, độ dài văn bản có bị suy thoái không.
- *Freshness monitoring:* Giám sát **tính kịp thời và độ trôi theo thời gian (Temporal Validity / Data Drift)** — kiểm tra xem dữ liệu trong kho tri thức có đang phản ánh thông tin cập nhật hay đang chứa quá nhiều dữ liệu lỗi thời dựa trên ngưỡng SLA (180 ngày).
- *Ý nghĩa kết hợp:* Một tập dữ liệu có thể hoàn toàn thỏa mãn Quality Checks (không null, không trùng, schema chuẩn) nhưng vẫn vi phạm Freshness SLA (ví dụ: toàn bộ bài báo từ 15 năm trước khiến RAG Agent đưa ra câu trả lời lỗi thời). Cả hai cơ chế tạo nên tấm lá chắn toàn diện hai lớp.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
- Đây là nguyên tắc cốt lõi của **thực nghiệm khoa học có đối chứng (Controlled Experiment)**: Nhằm đánh giá chính xác tác động của chất lượng dữ liệu lên chất lượng của RAG Agent, biến số duy nhất được phép thay đổi là **dữ liệu trong cơ sở tri thức**.
- Nếu thay đổi bộ test set giữa các lần chạy, sự thay đổi của các chỉ số (Hit Rate, F1, Judge Score) có thể bắt nguồn từ độ khó/dễ khác nhau của câu hỏi mới chứ không phản ánh đúng tác động của dữ liệu bị tiêm lỗi hay đã được phục hồi.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
- Về mặt Data Observability:
  - `data/quality/repaired_freshness_report.json` đạt `is_fresh = True` (0 bản ghi quá hạn, tỷ lệ stale = 0.0%).
  - `data/quality/quality_suite_repaired.json` đạt `success = True` (100% expectations vượt qua, không còn lỗi trùng lặp hay rỗng summary).
  - `data/clean/papers_clean_repaired.csv` khôi phục đúng 24 bản ghi sạch chuẩn như baseline ban đầu.
- Về mặt RAG Agent Benchmark:
  - File `data/results/repaired_metrics.json` ghi nhận sự phục hồi toàn diện ngang bằng với `baseline_metrics.json`:
    - `retrieval_hit_rate`: Khôi phục từ **60.0%** trở lại **100.0%**.
    - `mean_token_f1`: Khôi phục từ **40.68%** trở lại **80.0%**.
    - `judge_accuracy`: Khôi phục từ **40.0%** trở lại **80.0%**.
    - `mean_judge_score`: Khôi phục từ **2.6 / 5.0** trở lại **4.2 / 5.0**.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline (Sạch) | Corrupted (Tiêm lỗi) | Repaired (Phục hồi) | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **100.0%** (1.0) | **60.0%** (0.6) | **100.0%** (1.0) | Giảm mạnh 40% khi bị drop tài liệu và hỏng tiêu đề; phục hồi hoàn hảo sau khi repair. |
| **`mean_token_f1`** | **80.0%** (0.8) | **40.7%** (0.4068) | **80.0%** (0.8) | Giảm gần một nửa (~39.3 pp) do summary bị xóa trắng và chèn noise; trở về chính xác mốc baseline sau repair. |
| **`judge_accuracy`** | **80.0%** (0.8) | **40.0%** (0.4) | **80.0%** (0.8) | Đánh giá ngữ nghĩa giảm 40 pp khi dữ liệu bẩn; phục hồi trọn vẹn sau sửa chữa. |
| **`mean_judge_score`** | **4.20 / 5.0** | **2.60 / 5.0** | **4.20 / 5.0** | Điểm trung bình chất lượng câu trả lời rớt 1.6 điểm; sau phục hồi đạt lại mức điểm cao 4.2. |
| **Quality checks (GX 1.x)** | **PASS** (5/5 pass) | **FAIL** (3/5 pass, 2 fail) | **PASS** (5/5 pass) | GX bắt chính xác 2 vi phạm: 6 dòng trùng lặp (26.09%) và 2 dòng summary rỗng. |
| **Freshness status** | **FRESH** (0.0% stale) | **STALE** (30.43% stale) | **FRESH** (0.0% stale) | Phát hiện chính xác 7/23 bài bị lùi về năm 2010 vượt ngưỡng cảnh báo 25%. |

### Kết luận từ số liệu

**Hai chuỗi nguyên nhân – bằng chứng:**
1. **[Data Corruption] → [Quality/Freshness Signal Vi Phạm] → [Agent Metric Suy Giảm Nghiêm Trọng]:**
   Khi tiêm 6 kịch bản lỗi vào dữ liệu sạch, GX Quality Gate lập tức chuyển từ `PASS` sang `FAIL` (phát hiện 6 bản ghi trùng lặp và 2 bản ghi summary rỗng), Freshness SLA chuyển từ `FRESH` sang `STALE` (tỷ lệ bài quá hạn tăng vọt từ 0.0% lên 30.43%). Hệ quả trực tiếp phản ánh lên RAG Agent: Retrieval Hit Rate sụp đổ từ 100% xuống 60%, Mean Token F1 tụt từ 80.0% xuống 40.7%, và Judge Accuracy rơi từ 80% xuống 40%. Đây là bằng chứng thực nghiệm rõ nét nhất về hiện tượng **Silent Failure** — AI vẫn trả lời nhưng câu trả lời đã bị thoái hóa chất lượng nghiêm trọng.

2. **[Idempotent Repair] → [Quality/Freshness Signal Phục Hồi] → [Agent Metric Lấy Lại Phong Độ]:**
   Khi kích hoạt cơ chế Idempotent Repair bằng cách tái xử lý từ bản Raw Snapshot bất biến (`crossref_records.json`), tập dữ liệu được làm sạch chuẩn hóa lại, GX Quality Gate khôi phục trạng thái `PASS` (100% 5/5 expectations đạt), Freshness SLA trở về `FRESH` (0% vi phạm). Sau khi tái lập Vector Index (`papers-repaired`), toàn bộ chỉ số của RAG Agent phục hồi hoàn toàn ngang bằng với trạng thái Baseline ban đầu (Hit Rate 100%, Token F1 80%, Judge Accuracy 80%).

**Dạng corruption ảnh hưởng rõ rệt nhất:**
- **`drop_latest_records` (cắt bỏ 20% bài báo mới)** và **`blank_summary` (xóa trắng tóm tắt)** gây ảnh hưởng nghiêm trọng nhất:
  - Khi bài báo bị drop khỏi cơ sở dữ liệu, vector retriever hoàn toàn không thể tìm thấy tài liệu liên quan cho các câu hỏi nhắm vào bài đó, trực tiếp kéo tụt Retrieval Hit Rate xuống 60%.
  - Khi summary bị xóa trắng hoặc thay bằng noise, dù retriever có thể lấy được tiêu đề tương tự nhưng context đưa vào LLM hoàn toàn rỗng hoặc vô nghĩa, khiến mô hình bị ảo giác và Token F1 sụp đổ xuống mức 40.7%.

**Kết quả khác với kỳ vọng ban đầu và cách lý giải:**
- *Kỳ vọng ban đầu:* Tôi từng dự đoán khi bị tiêm ký tự rác (`inject_noise`), vector retriever sẽ bị đánh lừa hoàn toàn và không thể retrieve được tài liệu liên quan.
- *Thực tế quan sát được:* Mô hình embedding `all-MiniLM-L6-v2` vẫn thể hiện tính kháng nhiễu tốt trên tiêu đề bài báo, vẫn retrieve được bài đó nếu tiêu đề còn nguyên vẹn. Tuy nhiên, phần text context chứa đầy ký tự rác làm câu trả lời sinh ra bị loãng ngữ nghĩa, ảnh hưởng nặng đến Token F1 và điểm số của LLM Judge. Điều này chứng minh rằng kiểm soát chất lượng dữ liệu ở cấp độ nội dung chi tiết (nội dung abstract/summary) cũng quan trọng không kém gì việc kiểm soát tiêu đề hay khóa định danh.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline (Tính Idempotency & Data Lineage):**
   Một data pipeline chuyên nghiệp phục vụ AI bắt buộc phải đảm bảo tính Idempotent (chạy lại nhiều lần với cùng input phải cho ra cùng output) và phải bảo toàn tuyệt đối bản lưu trữ thô bất biến (Raw Snapshot). Khả năng tự phục hồi (Self-healing) thực chất phụ thuộc hoàn toàn vào việc bạn có giữ được bản gốc sạch và quy trình làm sạch có thể tái lập 100% hay không.

2. **Về Data Observability (Phát hiện sớm Silent Failure):**
   Trong kiến trúc AI/LLM hiện đại, kiểm thử unit test hay kiểm tra cú pháp code là chưa đủ. Dữ liệu là "code mới". Việc tích hợp các chốt chặn tự động như Great Expectations 1.x kết hợp với Freshness SLA giúp đội ngũ kỹ thuật phát hiện và ngăn chặn dữ liệu bẩn ngay tại "cửa ngõ" trước khi chúng được nhúng thành vector và đi vào serving layer.

3. **Về mối quan hệ giữa Data Quality và RAG Agent:**
   Chất lượng của mô hình AI luôn bị giới hạn trên bởi chất lượng của dữ liệu đầu vào ("Garbage in, garbage out"). Việc chỉ số Agent sụt giảm hơn 50% chỉ vì 15–20% dữ liệu bị hỏng cho thấy nỗ lực tối ưu hóa Prompt hay tinh chỉnh LLM sẽ trở nên vô nghĩa nếu nền tảng dữ liệu bên dưới không được giám sát và bảo đảm chất lượng.

### Nếu có thêm thời gian

Tôi muốn xây dựng một **Automated Circuit Breaker & Self-Healing Webhook**:
- *Mô tả:* Khi hàm `run_data_quality_checks()` phát hiện `success == False` hoặc `build_freshness_report()` phát hiện `is_fresh == False`, pipeline sẽ tự động kích hoạt chốt ngắt mạch (Circuit Breaker) — lập tức dừng việc nạp dữ liệu bẩn vào Vector Database đang phục vụ production, tự động bắn thông báo cảnh báo qua Telegram/Slack Bot, và kích hoạt luồng khôi phục dữ liệu tự động từ snapshot trước đó.
- *Cách đo lường:* Giả lập tiêm lỗi tự động qua GitHub Actions và đo thời gian từ lúc phát hiện lỗi đến khi hoàn tất rollback/repair (<60 giây) mà dịch vụ RAG không bị gián đoạn hay trả lời sai lệch cho người dùng.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Điền Họ và tên của bạn]  
**Ngày xác nhận:** 2026-09-26
