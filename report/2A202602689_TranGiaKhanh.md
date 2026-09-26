# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Gia Khánh |
| MSSV | 2A202602689 |
| Khóa/Lớp | K4 — L3B |
| Tên nhóm | Manngusidan |
| Vai trò chính | Data Foundation & Recovery |
| Repository | https://github.com/thong0609/K4-L3B-DAY10-Manngusidan-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Data Ingestion & Lineage** | `src/ingestion/crossref.py`<br>- `fetch_source_records()`<br>- `parse_crossref_payload()` | Cấu hình `Settings`, Crossref REST API `/works` hoặc offline snapshot `data/raw/crossref_response.json` | - `data/raw/crossref_response.json`<br>- `data/raw/crossref_records.json` (24 đối tượng `PaperRecord` chuẩn hóa) | Hoàn thành |
| **Data Cleaning & Modeling** | `src/ingestion/cleaning.py`<br>- `build_clean_dataframe()`<br>- `_build_embedding_text()` | Danh sách `PaperRecord` thô, `run_date` (UTC timestamp) | - `data/clean/papers_clean.csv`<br>- `data/clean/papers_clean.json` (24 bản ghi sạch, có `age_days` & `text_for_embedding`) | Hoàn thành |
| **Data Recovery (Idempotent Repair)** | `src/ingestion/cleaning.py`<br>phối hợp cùng `src/pipelines/corruption_flow.py` | Snapshot thô bất biến `data/raw/crossref_records.json` | - `data/clean/papers_clean_repaired.csv`<br>- `data/clean/papers_clean_repaired.json`<br>- Dữ liệu sạch phục hồi 100% qua Quality Gate | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| :--- | :--- | :--- |
| **Khớp nối Contract cho RAG & Vector Index** | Đinh Văn Bình (`src/retrieval/index.py`, `embeddings.py`) | Chuẩn hóa schema metadata và định dạng trường `text_for_embedding` 5 phần, đảm bảo ChromaDB lập chỉ mục chính xác và QA Router truy xuất đúng trường thông tin (`title`, `authors`, `published`, `categories`, `summary`). |
| **Hỗ trợ thiết lập Observability & Test Set** | Ngô Đinh Minh Nhật (`src/observability/quality.py`, `evaluation/testset.py`) | Cung cấp đúng định dạng dữ liệu đầu vào cho Great Expectations 1.x (không có null, unique `paper_id`), đồng bộ cấu trúc trường để bộ test 10 câu hỏi trích xuất chính xác `ground_truth_doc_ids`. |
| **Tích hợp luồng thực thi Pipeline** | Tô Huy Thông (`src/pipelines/phase1.py`, `corruption_flow.py`) | Tích hợp hàm `build_clean_dataframe` và logic khôi phục dữ liệu từ snapshot thô vào hai pipeline chính; bảo đảm tính lặp lại an toàn (Idempotent) giữa các chu trình chạy. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| Xây dựng module Ingestion Crossref API có cơ chế Retry & Offline Fallback | `src/ingestion/crossref.py` — `fetch_source_records` | Thu thập 24 bản ghi từ API với cơ chế retry 3 lần, exponential backoff (2s, 4s) cho mã 429/5xx, tự động fallback sang snapshot local khi mất mạng/hết quota. | Chạy lệnh ingestion test; console in ra tải thành công 24 bài báo; lưu trữ đầy đủ 2 file raw. |
| Xử lý bóc tách payload phức tạp (JATS XML, Dates, Authors) | `src/ingestion/crossref.py` — `parse_crossref_payload` | Loại bỏ 100% thẻ `<jats:p>`, unescape HTML entities, chuyển mảng `date-parts` đa cấp thành ISO `YYYY-MM-DD`, chuẩn hóa tên tác giả "given family". | `data/raw/crossref_records.json` chứa 24 `PaperRecord` sạch cú pháp XML, không còn thẻ `<jats`. |
| Xây dựng quy trình làm sạch & mô hình hóa tiền Vector hóa (Pre-embed Modeling) | `src/ingestion/cleaning.py` — `build_clean_dataframe` | Tính toán `age_days = (run_date - published).days`, tạo cột `text_for_embedding` 5 phần giàu ngữ cảnh, khử trùng lặp theo `paper_id`. | Xuất `data/clean/papers_clean.csv` và `.json` (đúng 24 dòng sạch); GX Quality Gate đạt 100% PASS. |
| Hiện thực hóa cơ chế Phục hồi Dữ liệu Tự động (Idempotent Self-Healing Repair) | `src/ingestion/cleaning.py` (tái xử lý từ `crossref_records.json`) | Khôi phục toàn bộ dữ liệu bị tiêm lỗi về trạng thái sạch ban đầu mà không cần gọi lại API bên ngoài; chứng minh tính bất biến qua 2 lần chạy liên tiếp. | `papers_clean_repaired.csv` khôi phục đúng 24 dòng; GX Gate khôi phục từ FAIL lên PASS; RAG Hit Rate từ 0.8 lên lại 1.0. |

### Output cụ thể tạo ra và giúp xác minh:
- **`data/raw/crossref_records.json`**: Bản lưu trữ thô chuẩn hóa (Raw Snapshot) gồm 24 đối tượng `PaperRecord`. Đây là chiếc "mỏ neo dữ liệu" (Data Lineage Anchor) bảo toàn tính bất biến của hệ thống, giúp toàn bộ thực nghiệm có thể tái lập chính xác bất kể biến động từ API Crossref bên ngoài.
- **`data/clean/papers_clean.csv` & `papers_clean.json`**: Tập dữ liệu sạch 24 dòng với cấu trúc chuẩn 16 cột. Cột `text_for_embedding` ghép 5 tầng thông tin giúp mô hình embedding bao quát được cả metadata bài báo, trực tiếp quyết định việc hệ thống RAG đạt **100% Retrieval Hit Rate** ở Baseline.
- **`data/clean/papers_clean_repaired.csv` & `papers_clean_repaired.json`**: Artifact đầu ra của quá trình Repair, minh chứng dữ liệu sau khi khôi phục từ snapshot thô hoàn toàn trùng khớp với Baseline ban đầu cả về số dòng (24), chất lượng schema và điểm kiểm định chất lượng.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Dữ liệu thô từ học thuật rất phức tạp và thiếu ổn định:** Crossref API trả về payload JSON lồng nhau sâu, chứa các thẻ XML học thuật (JATS XML như `<jats:p>`, `<jats:italic>`), các thực thể HTML mã hóa (`&amp;`, `&lt;`), và cấu trúc ngày tháng dạng mảng bất quy tắc `date-parts: [[2026, 7, 22]]` có thể khuyết tháng/ngày. Ngoài ra, API Crossref công cộng thường xuyên trả về mã lỗi `429 Too Many Requests` hoặc thiếu trường `subject`.
2. **Nguy cơ mất mát nguồn gốc dữ liệu (Data Lineage Loss):** Nếu pipeline làm sạch trực tiếp trên luồng truyền dữ liệu (in-flight) mà không lưu lại snapshot thô nguyên bản, khi dữ liệu bị lỗi hoặc tiêm bẩn (Data Corruption), hệ thống sẽ không có căn cứ đối chứng và không thể tự phục hồi nếu không gọi lại API từ đầu.
3. **Mô hình hóa dữ liệu cho RAG (Data Modeling for Embedding):** Vector retriever cần thông tin không chỉ ở phần Abstract mà còn ở Tiêu đề, Tác giả, Ngày tháng và Danh mục để trả lời các câu hỏi nghiệp vụ khác nhau. Cần thiết kế một lược đồ trường nhúng (`text_for_embedding`) chuẩn mực và tính toán chính xác độ trôi thời gian (`age_days`) phục vụ giám sát Freshness SLA.

### Cách triển khai

1. **Kiến trúc Thu thập Bền bỉ (Resilient Ingestion) trong `src/ingestion/crossref.py`:**
   - Sử dụng cơ chế Retry với Exponential Backoff: khi gặp các lỗi mạng tạm thời hoặc mã trạng thái thuộc tập `{429, 500, 502, 503, 504}`, hệ thống tự động thử lại tối đa 3 lần với khoảng nghỉ tăng dần ($2\text{s} \rightarrow 4\text{s}$).
   - Cơ chế Fallback an toàn: nếu API bị chặn quota hoặc khi cờ `REFRESH_SOURCE` không được bật, hệ thống tự động chuyển sang đọc từ file snapshot thô có sẵn `data/raw/crossref_response.json`, đảm bảo tính khả dụng cao và kết quả tái lập 100% trên mọi máy chấm.
   - Bóc tách payload chi tiết (`parse_crossref_payload`):
     - Dùng Regex `re.compile(r"<[^>]+>")` kết hợp `html.unescape()` và `normalize_whitespace()` để tẩy sạch mọi thẻ JATS XML.
     - Hàm `_date_from_parts()` chuyển mảng ngày tháng linh hoạt sang ISO `YYYY-MM-DD`, tự động bù ngày/tháng bằng 1 nếu thiếu.
     - Tìm kiếm ngày xuất bản ưu tiên theo thứ tự: `published` $\rightarrow$ `published-online` $\rightarrow$ `published-print` $\rightarrow$ `issued` $\rightarrow$ `created`.
     - Lưu kết quả ra 2 file raw artifacts: `crossref_response.json` (nguyên bản API) và `crossref_records.json` (danh sách `PaperRecord` bất biến).

2. **Quy trình Làm sạch & Tạo trường Đặc trưng (Cleaning & Feature Engineering) trong `src/ingestion/cleaning.py`:**
   - Chuẩn hóa văn bản và danh sách: chuẩn hóa khoảng trắng toàn bộ các trường chuỗi, viết thường DOI làm `paper_id` khóa chính (`df["paper_id"].str.lower()`).
   - Tính toán trường thời gian động:
     $$\text{age\_days} = (\text{run\_date} - \text{published}).\text{days}$$
     Toàn bộ thời gian được chuẩn hóa về múi giờ UTC (`datetime.now(timezone.utc)`), đảm bảo tính nhất quán tuyệt đối.
   - Thiết kế mẫu trường nhúng `text_for_embedding` 5 phần:
     ```text
     Title: <title>
     Authors: <authors_joined>
     Published: <published>
     Categories: <categories_joined>
     Summary: <summary>
     ```
   - Lọc bỏ dòng lỗi (Completeness Filtering): loại bỏ các bản ghi thiếu `paper_id`, `title`, `summary`, hoặc không thể ép kiểu ngày xuất bản.
   - Khử trùng lặp khóa chính: gom nhóm theo `paper_id`, giữ lại bản ghi có ngày `updated` mới nhất.

3. **Cơ chế Phục hồi Bất biến (Idempotent Repair):**
   - Quá trình Repair không thực hiện chắp vá từng ô dữ liệu bị hỏng (ad-hoc patching) mà kích hoạt hàm `build_clean_dataframe()` trực tiếp từ snapshot thô `crossref_records.json`.
   - Vì snapshot thô là bất biến (Read-only), việc chạy lại quy trình làm sạch luôn sinh ra cùng một DataFrame sạch 24 dòng giống hệt ban đầu:
     $$f(\text{raw\_snapshot}) = \text{clean\_df}_{\text{repaired}} \equiv \text{clean\_df}_{\text{baseline}}$$
   - Điều này đảm bảo tính Idempotent: chạy bao nhiêu lần cũng không làm phình to dữ liệu hay sai lệch schema.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Crossref API `/works` payload hoặc `data/raw/crossref_response.json` (raw API response); tham số `run_date` kiểu `datetime`. |
| **Output** | - `data/raw/crossref_records.json`: 24 đối tượng `PaperRecord`.<br>- `data/clean/papers_clean.csv` & `.json`: DataFrame 24 dòng, 16 cột.<br>- `data/clean/papers_clean_repaired.csv` & `.json`: Dữ liệu phục hồi sau repair. |
| **Module phụ thuộc** | `core.config.Settings`, `core.utils` (`normalize_whitespace`, `read_json`, `write_json`). |
| **Module sử dụng output** | `src/retrieval/index.py` (đọc cột `text_for_embedding` và metadata để index vào ChromaDB); `src/observability/quality.py` (đọc DataFrame để chạy Great Expectations và tính Freshness SLA); `src/evaluation/testset.py` (đọc DataFrame để sinh bộ câu hỏi benchmark). |
| **Điều kiện lỗi cần xử lý** | - Lỗi mạng / HTTP 429: kích hoạt exponential backoff và fallback sang file snapshot.<br>- Dữ liệu ngày tháng khuyết thiếu: hàm `_date_from_parts` tự động bù `[year, 1, 1]` an toàn.<br>- Dữ liệu rác/thiếu trường bắt buộc: bộ lọc loại bỏ trước khi xuất ra clean dataframe. |

### Cách xác minh

Kiểm tra Ingestion và lưu trữ raw records:
```powershell
.venv\Scripts\python.exe -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Ingestion thành công: Đã tải {len(r)} bài báo')"
```

Kiểm tra Cleaning và tạo clean dataframe:
```powershell
.venv\Scripts\python.exe -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean thành công: {len(df)} dòng, có text_for_embedding: {\"text_for_embedding\" in df.columns}')"
```

Chạy toàn bộ luồng tích hợp Phase 1:
```powershell
.venv\Scripts\python.exe script/run_phase1.py
```

- **Kết quả mong đợi:** Tải/đọc đủ 24 bài báo; làm sạch thành công 24 dòng; sinh đầy đủ các cột helper và `text_for_embedding`; GX Quality Gate báo `success = True`.
- **Kết quả thực tế:** Hoàn thành chính xác 100%. Console in ra `PHASE 1 COMPLETE!`; các file `data/raw/` và `data/clean/` được tạo đầy đủ, chuẩn xác.
- **Artifacts:**
  - `data/raw/crossref_response.json` (kích thước ~320 KB)
  - `data/raw/crossref_records.json` (24 items)
  - `data/clean/papers_clean.csv` (24 rows)
  - `data/clean/papers_clean.json` (24 items)

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi xây dựng quy trình làm sạch dữ liệu để nạp vào ChromaDB Vector Store, nhóm cần quyết định cách cấu trúc dữ liệu đưa vào mô hình Embedding: chỉ đưa trường `summary` (Abstract) thuần túy hay đóng gói toàn bộ metadata vào một chuỗi văn bản tổng hợp đa trường (`text_for_embedding`).
- **Các phương án đã cân nhắc:**
  1. *Phương án 1 (Chỉ embed summary):* Chỉ đưa nội dung tóm tắt bài báo vào vector model. Các trường tác giả, ngày tháng, danh mục chỉ lưu ở dạng metadata filter của vector database.
  2. *Phương án 2 (Đóng gói văn bản tổng hợp đa trường - Composite Text Embedding):* Ghép 5 trường cốt lõi theo cấu trúc tường minh:
     `Title: ... \n Authors: ... \n Published: ... \n Categories: ... \n Summary: ...`
     đồng thời vẫn lưu đầy đủ các trường riêng biệt vào metadata của ChromaDB.
- **Phương án đã chọn:** Phương án 2 — Composite Text Embedding kết hợp Metadata đồng bộ.
- **Lý do:**
  - Bộ benchmark đánh giá của RAG Agent không chỉ hỏi về nội dung bài báo mà phủ khắp 4 nhóm nghiệp vụ: hỏi về tác giả (`authors`), hỏi về thời gian xuất bản (`date`), hỏi về danh mục (`categories`) và tóm tắt (`summary`).
  - Nếu chỉ embed `summary`, vector retriever sẽ hoàn toàn bị "mù" khi người dùng truy vấn theo tên tác giả hoặc năm xuất bản vì thông tin đó không nằm trong không gian vector ngữ nghĩa.
  - Việc đưa cả Title và Authors vào embedding text giúp mô hình `all-MiniLM-L6-v2` nắm bắt được sự tương đồng ngữ nghĩa của tên nhà khoa học và từ khóa chủ đề, giúp Retrieval Hit Rate đạt mức tối đa 100% trên cả 10 câu hỏi test set.
- **Bằng chứng quyết định phù hợp:** Trong bài đo Baseline, Retrieval Hit Rate đạt **1.0 (10/10 câu)** trên cả 4 dạng câu hỏi; Token F1 đạt **1.0**, chứng minh bộ trích xuất vector lấy đúng chính xác văn bản cần tìm cho RAG Agent.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  Khi chạy lại ingestion từ API Crossref live, trường 'categories' (chứa Crossref subject) của toàn bộ các bài báo mới bị rỗng: []
  Hệ quả: Cột 'categories_joined' bị rỗng -> test set không sinh được câu hỏi dạng categories hoặc QA Agent trả về rỗng.
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh `python script/run_phase1.py` với cờ `REFRESH_SOURCE=1` để gọi trực tiếp tới endpoint Crossref live.
- **Nguyên nhân gốc:**
  - API công cộng của Crossref đối với các bài báo khoa học xuất bản gần đây (đặc biệt là các bài từ 2026/online first) thường chưa kịp gắn thẻ `subject` (chỉ có metadata cơ bản về DOI, title, author).
  - Khi script Ingestion vô tình ghi đè snapshot thô bằng kết quả trả về từ API live này, tập dữ liệu bị mất trường danh mục, phá vỡ hợp đồng dữ liệu (data contract) mà module Evaluation và Cleaning kỳ vọng.
- **Cách xử lý:**
  1. Tôi đã thiết lập cơ chế **Lineage Anchor**: mặc định hàm `fetch_source_records()` sẽ ưu tiên đọc từ snapshot thô bất biến `data/raw/crossref_response.json` (bản snapshot chuẩn đã có đầy đủ `subject`). Chỉ khi nào nhà phát triển chủ động truyền cờ `REFRESH_SOURCE=1` thì mới gọi API.
  2. Bổ sung cơ chế Fallback phòng thủ trong `build_clean_dataframe()`: nếu trường `primary_category` bị rỗng thì tự động trích xuất phần tử đầu tiên của `categories`, nếu cả hai đều rỗng thì gán nhãn mặc định an toàn thay vì để `None` hoặc crash.
  3. Phối hợp với bạn phụ trách Evaluation để cập nhật bộ test set có cơ chế cảnh báo và fallback mềm khi phát hiện trường danh mục thiếu.
- **Cách xác minh sau khi sửa:** Chạy lại toàn bộ luồng Ingestion và Cleaning. File `data/clean/papers_clean.json` luôn có đầy đủ danh mục, bộ test set sinh ra đủ 10 câu hỏi phủ đủ 4 dạng (`summary` 3, `authors` 3, `date` 2, `categories` 2), và chỉ số F1 đạt 1.0.
- **Điều học được:** Khi phụ thuộc vào dữ liệu từ bên thứ ba (Third-party API), dữ liệu thực tế luôn có tính phi tất định (non-deterministic). Việc lưu giữ một bản **Raw Snapshot bất biến** làm gốc và xây dựng cơ chế xử lý lỗi phòng thủ (defensive handling) là bắt buộc để đảm bảo tính tái lập (reproducibility) trong kỹ thuật dữ liệu.

---

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
- *Ingestion:* Dữ liệu thô từ Crossref API (hoặc snapshot `crossref_response.json`) được tải về. Hàm `parse_crossref_payload()` loại bỏ JATS XML tags, unescape ký tự, parse mảng ngày tháng linh hoạt và chuẩn hóa thành các đối tượng `PaperRecord`, lưu vào `crossref_records.json` (bảo toàn raw snapshot).
- *Cleaning:* `build_clean_dataframe()` đọc danh sách `PaperRecord`, chuẩn hóa text, khử trùng lặp theo `paper_id` (giữ bản ghi mới nhất), tính toán `age_days` so với ngày chạy UTC, và đóng gói chuỗi đa tầng `text_for_embedding` (Title/Authors/Published/Categories/Summary), lưu ra `papers_clean.csv` và `.json`.
- *Vector Indexing:* DataFrame sạch được nạp vào module `LocalEmbeddingIndex`. Mô hình `sentence-transformers/all-MiniLM-L6-v2` mã hóa chuỗi `text_for_embedding` thành vector embedding 384 chiều và nạp kèm metadata vào ChromaDB collection (`papers-baseline`) lưu trên ổ đĩa qua `PersistentClient`.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
- Module `build_test_set()` sinh ra 10 câu hỏi chuẩn hóa đại diện từ corpus sạch phủ đủ 4 nhóm nghiệp vụ (`summary`, `authors`, `date`, `categories`). Mỗi câu hỏi được gán cố định `ground_truth_doc_ids` chứa chính xác DOI của bài báo nguồn tạo ra câu hỏi đó.
- Khi đánh giá:
  - *Retrieval Quality:* Câu hỏi được tìm kiếm trên ChromaDB để lấy danh sách top-k (`retrieved_doc_ids`). Nếu `ground_truth_doc_ids` nằm trong danh sách trả về thì được tính là 1 Hit. Tỷ lệ này trên toàn bộ câu hỏi chính là `retrieval_hit_rate`.
  - *Answer Quality:* Dữ liệu context của tài liệu tìm được được chuyển qua QA Agent để trích xuất câu trả lời. Chỉ số `mean_token_f1` đo độ trùng khớp từ vựng giữa câu trả lời sinh ra và `ground_truth`. Điểm số `judge_accuracy` / `mean_judge_score` đánh giá tính đúng đắn ngữ nghĩa của câu trả lời.

**3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
- *Quality checks (Great Expectations 1.x):* Giám sát **tính toàn vẹn về cấu trúc và giá trị tĩnh** của bảng dữ liệu (Structural & Data Contract Constraints) — như kiểm tra số lượng bản ghi nằm trong ngưỡng [15, 30], không có bản ghi nào bị null ở khóa chính hay tiêu đề, tính duy nhất của `paper_id`, và độ dài tối thiểu của tóm tắt.
- *Freshness monitoring:* Giám sát **tính hợp thời và độ trôi theo trục thời gian** (Temporal Freshness / Data Drift) — dựa trên trường `age_days` tính từ ngày xuất bản thực tế đến ngày chạy pipeline. Nếu tỷ lệ bài quá hạn (>180 ngày) vượt quá 25%, hệ thống sẽ cảnh báo `is_fresh = False`.
- *Sự khác biệt cốt lõi:* Một bảng dữ liệu có thể hoàn toàn sạch sẽ, không hề có dòng null hay trùng lặp (GX Gate PASS), nhưng toàn bộ bài báo đã được xuất bản từ 10 năm trước khiến tri thức của RAG Agent bị lỗi thời nghiêm trọng (Freshness SLA FAIL). Do đó, hai cơ chế này bổ trợ song hành cho nhau.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
- Đây là nguyên tắc cơ bản của **thực nghiệm khoa học có đối chứng (Controlled Experiment)**: Mục tiêu của bài lab là cô lập và đo lường định lượng chính xác tác động của **chất lượng dữ liệu** lên hiệu năng của RAG Agent.
- Nếu thay đổi bộ test set giữa các trạng thái, sự tăng giảm của các chỉ số (Hit Rate, Token F1) có thể do sự khác biệt về độ khó/dễ của câu hỏi mới, làm mất đi tính khách quan. Việc giữ nguyên cùng một file `data/eval/test_set.json` đảm bảo biến số duy nhất thay đổi xuyên suốt thực nghiệm chính là **tình trạng dữ liệu trong Vector Index**.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
- *Về mặt Data Artifacts:*
  - File `data/clean/papers_clean_repaired.csv` khôi phục chính xác 24 dòng sạch, không còn dòng rác hay dòng trùng lặp.
  - Kết quả kiểm định Great Expectations tại `data/quality/quality_suite_repaired.json` đạt `success = True` (100% 6/6 checks pass).
  - Báo cáo Freshness tại `data/quality/repaired_freshness_report.json` đạt `is_fresh = True` (tỷ lệ stale giảm từ 40.91% về lại 4.17%).
- *Về mặt RAG Agent Metrics (trong `data/results/repaired_metrics.json`):*
  - `retrieval_hit_rate`: Phục hồi 100% từ **0.8** trở lại mốc hoàn hảo **1.0**.
  - `mean_token_f1`: Phục hồi 100% từ **0.9** trở lại **1.0**.
  - `judge_accuracy`: Phục hồi 100% từ **0.9** trở lại **1.0**.
  - `mean_judge_score`: Phục hồi từ **4.6** trở lại **5.0**.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline (Sạch) | Corrupted (Tiêm lỗi) | Repaired (Phục hồi) | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0** (100%) | **0.8** (80%) | **1.0** (100%) | Giảm 0.2 (2 câu bị trượt: eval_003 bị cắt title và eval_004 bị drop bài); phục hồi hoàn toàn 1.0 sau khi repair từ raw. |
| **`mean_token_f1`** | **1.0** (100%) | **0.9** (90%) | **1.0** (100%) | Giảm 0.1 do câu eval_003 trả lời sai ngày (F1=0); phục hồi tuyệt đối 1.0 sau repair. |
| **`judge_accuracy`** | **1.0** | **0.9** | **1.0** | Heuristic fallback bám theo token F1 do API Gemini bị 429; giảm 0.1 và phục hồi trọn vẹn. |
| **`mean_judge_score`** | **5.0** | **4.6** | **5.0** | Điểm số trung bình phục hồi về mức tuyệt đối 5.0. |
| **Quality checks (GX 1.x)** | **6/6 PASS** | **4/6 PASS** (2 FAIL) | **6/6 PASS** | GX bắt chính xác 2 lỗi: `unique(paper_id)` FAIL do 6 dòng trùng lặp và `summary` length FAIL do 3 dòng bị xóa trắng. |
| **Freshness status** | **FRESH** (4.17%) | **STALE** (40.91%) | **FRESH** (4.17%) | Tỷ lệ bài quá hạn tăng vọt từ 4.17% lên 40.91% (> 25%), kích hoạt cảnh báo SLA kịp thời. |

### Kết luận từ số liệu

**Hai chuỗi nguyên nhân – bằng chứng:**
1. **[Data Corruption] $\rightarrow$ [Quality/Freshness Signal Vi Phạm] $\rightarrow$ [Agent Metric Bị Kéo Tụt (Silent Failure)]:**
   - Kịch bản `truncate_title` cắt ngắn tiêu đề bài báo xuống 7 ký tự $\rightarrow$ không có expectation về độ dài tiêu đề nên lọt qua Quality Gate $\rightarrow$ QA Router không thể tìm thấy exact title, semantic search trả về sai tài liệu $\rightarrow$ câu hỏi eval_003 (date) bị trượt Hit Rate và Token F1 rớt về 0.
   - Kịch bản `drop_latest_records` loại bỏ 5 bài báo mới nhất $\rightarrow$ câu hỏi eval_004 mất tài liệu ground truth $\rightarrow$ Hit Rate bị đánh trượt (giảm từ 1.0 xuống 0.8).
   - Đáng chú ý, pipeline trên dữ liệu bẩn **vẫn chạy thành công và không quăng bất kỳ Exception nào**, chứng minh hiện tượng **Silent Failure** nguy hiểm nếu không có Data Observability.
2. **[Idempotent Repair] $\rightarrow$ [Data Schema & Quality Phục Hồi] $\rightarrow$ [Agent Metric Lấy Lại Phong Độ Tuyệt Đối]:**
   - Kích hoạt cơ chế Repair đọc lại từ snapshot thô nguyên bản `data/raw/crossref_records.json` $\rightarrow$ loại bỏ hoàn toàn các dòng bị corrupt và duplicate $\rightarrow$ tái lập DataFrame sạch 24 dòng với schema và `text_for_embedding` toàn vẹn $\rightarrow$ GX Gate đạt 6/6 PASS, Freshness trở lại 4.17% $\rightarrow$ Vector Index mới phục hồi 100% Hit Rate (1.0) và Token F1 (1.0).

**Dạng corruption ảnh hưởng rõ rệt nhất:**
- **`truncate_title`** và **`drop_latest_records`** gây ảnh hưởng nghiêm trọng nhất đến RAG Agent:
  - `truncate_title` phá hỏng cơ chế truy vấn tài liệu theo tiêu đề, khiến retriever lấy nhầm văn bản khác và làm câu trả lời sai hoàn toàn (F1 = 0).
  - `drop_latest_records` trực tiếp làm "bốc hơi" tài liệu khỏi không gian vector, khiến cho câu hỏi nhắm vào bài báo đó không thể nào tìm thấy tài liệu gốc.

**Kết quả khác với kỳ vọng ban đầu và cách lý giải:**
- *Quan sát thú vị ở câu hỏi eval_004:* Mặc dù tài liệu gốc của câu hỏi eval_004 bị `drop_latest_records` xóa mất (khiến Retrieval Hit Rate bị đánh trượt), nhưng câu trả lời của Agent về danh mục (`categories`) vẫn đúng "nhờ may mắn" vì một tài liệu khác được retrieve có cùng danh mục chủ đề!
- Điều này chứng minh rằng **chỉ nhìn vào Token F1 của câu trả lời là không đủ để đánh giá hệ thống RAG**, mà bắt buộc phải đo lường song hành cả **Retrieval Hit Rate** và **Data Quality Gates** mới thấy hết được các lỗi tiềm ẩn bên dưới dữ liệu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline (Bảo toàn Data Lineage & Tính Idempotency):**
   Trong kỹ thuật dữ liệu, không bao giờ được biến đổi dữ liệu trực tiếp trên nguồn thô. Việc lưu trữ bản Snapshot Raw bất biến đóng vai trò là "chiếc phao cứu sinh" duy nhất cho phép hệ thống tự phục hồi (Self-healing) một cách an toàn và mang tính Idempotent (chạy lại bao nhiêu lần cũng đảm bảo cùng một kết quả sạch).
2. **Về Data Observability (Tấm khiên chống Silent Failure):**
   Một pipeline chạy không báo lỗi (exit code 0) không có nghĩa là dữ liệu sạch. Việc kết hợp song song giữa chốt chặn cấu trúc tĩnh (Great Expectations 1.x) và chốt chặn độ trôi thời gian động (Freshness SLA) là điều kiện tiên quyết để ngăn chặn dữ liệu hỏng lọt vào Vector Store.
3. **Về Mối quan hệ giữa Data Foundation và AI Agent:**
   Chất lượng của RAG Agent hoàn toàn phụ thuộc vào chất lượng của lớp nền tảng dữ liệu (Data Foundation). Việc trích xuất và thiết kế trường nhúng đa tầng (`text_for_embedding`) có vai trò then chốt giúp mô hình embedding liên kết được ngữ nghĩa giữa câu hỏi người dùng và kho tri thức bài báo.

### Nếu có thêm thời gian

Tôi sẽ xây dựng thêm **Data Contract Schema Validator kết hợp Auto-Rollback**:
- *Mục tiêu:* Bổ sung kỳ vọng kiểm tra độ dài tối thiểu của tiêu đề bài báo (`ExpectColumnValueLengthsToBeBetween(column="title", min_value=10)`) và kiểm tra ký tự rác bằng Regex trong `summary` để chặn đứng triệt để cả hai lỗi `truncate_title` và `inject_noise` ngay tại Quality Gate trước khi dữ liệu kịp đưa vào bước embedding.
- *Cách đo lường:* Chạy lại corruption suite; kỳ vọng toàn bộ 6/6 kịch bản lỗi đều bị Quality Gate bắt được (khiến số checks fail tăng từ 2 lên 4), và pipeline tự động kích hoạt hàm Repair rollback về snapshot trước đó trong thời gian <10 giây.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Gia Khánh  
**Ngày xác nhận:** 2026-09-26
