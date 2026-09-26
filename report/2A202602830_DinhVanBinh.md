# Báo cáo cá nhân — Thành viên 3: RAG & Vector Index

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đinh Văn Bình |
| MSSV | 2A202602830 |
| Khóa/Lớp | K4-L3B — Day 10 |
| Tên nhóm | Manngusidan |
| Vai trò chính | Thành viên 3 — RAG, Vector Database & Embedding, theo docs/TEAM.md |
| Repository | https://github.com/thong0609/K4-L3B-DAY10-Manngusidan-DataPipelineDataObservability |
| Ngày cập nhật | 2026-09-26 |
| Trạng thái | Đã đối chiếu code và artifact của nhóm sau khi cập nhật từ main; chưa chạy lại pipeline trong lần rà soát này |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Tôi phụ trách RAG & Vector Index theo phân công trong `docs/TEAM.md`. Bảng dưới mô tả phạm vi được giao và trạng thái implementation hiện có, không khẳng định toàn bộ code trong các file này do tôi viết mới. Phần triển khai trực tiếp cần đối chiếu với commit cá nhân trước khi nộp.

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding | `src/retrieval/embeddings.py`, `MiniLMEmbeddings` | Văn bản tài liệu và câu hỏi | Vector đã chuẩn hóa | Code dùng cùng model MiniLM cho tài liệu và câu hỏi; manifest ghi nhận model tương ứng |
| Vector index | `src/retrieval/index.py`, `LocalEmbeddingIndex` | DataFrame sạch và Settings | ChromaDB collection, manifest và kết quả tìm kiếm | Đã có ba manifest baseline/corrupted/repaired với 24/22/24 document |
| QA và Agent | `src/retrieval/qa.py`, `src/retrieval/agent.py` | Câu hỏi và index | Câu trả lời và tài liệu truy xuất | Có answers và metrics của luồng QA; chưa chạy lại LLM Agent trong lần rà soát này |
| Vị trí database | `data/chroma/` | Database đã có | Database ở đúng đường dẫn cấu hình | Đã chuyển và xác minh vị trí file |

Thành viên 2 cung cấp dữ liệu sạch và `text_for_embedding`. Thành viên 1 tích hợp index vào pipeline. Thành viên 4 dùng đầu ra retrieval/QA để đánh giá trên cùng test set.

### Việc hỗ trợ ngoài phạm vi chính

Chưa ghi nhận đóng góp ngoài phạm vi RAG & Vector Index có bằng chứng cụ thể. Cleaning, quality gate và orchestration được mô tả bên dưới để giải thích phụ thuộc, không nhận là phần đã trực tiếp thực hiện.

## 3. Kết quả theo vai trò

| Nội dung đã rà soát hoặc thực hiện | Bằng chứng | Kết luận |
| --- | --- | --- |
| Rà soát embedding | `embed_documents()` và `embed_query()` dùng `normalize_embeddings=True` | Có logic dùng cùng model cho tài liệu và câu hỏi |
| Rà soát phân tách trạng thái | `_derive_collection_name()` và ba manifest trong `data/embeddings/` | Tên collection trong manifest khớp baseline/corrupted/repaired |
| Chuyển database về đường dẫn chung | `data/chroma/chroma.sqlite3` và các thư mục vector hiện có | Đã khớp đường dẫn cấu hình |
| Kiểm tra artifact bàn giao | Ba manifest và `data/results/*_metrics.json` | Đã có dữ liệu bàn giao và kết quả đánh giá của nhóm |

Database hiện nằm tại `data/chroma/`. Các manifest `papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json` lần lượt ghi nhận collection `papers-baseline`, `papers-corrupted`, `papers-repaired` với 24, 22, 24 document. Đây là số đếm từ manifest, chưa phải phép đếm trực tiếp collection qua ChromaDB trong lần rà soát này. Các kết quả đánh giá ở mục 8 là artifact tích hợp của nhóm.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Chuyển nội dung bài báo thành vector để tìm tài liệu liên quan đến câu hỏi, đồng thời tách index của dữ liệu sạch, dữ liệu lỗi và dữ liệu phục hồi để so sánh khách quan.

### Cách triển khai

1. `MiniLMEmbeddings` tải model `sentence-transformers/all-MiniLM-L6-v2`. Hàm tải dùng `lru_cache(maxsize=4)` để tái sử dụng model trong cùng tiến trình.
2. Mỗi dòng DataFrame trở thành document gồm `text_for_embedding` và metadata. `record_id` ghép `paper_id` với vị trí dòng, cho phép biểu diễn cả các dòng trùng paper khi mô phỏng corruption.
3. `build()` chọn collection theo đường dẫn manifest, tạo lại collection đích, tính vector và nạp ChromaDB với khoảng cách cosine.
4. Manifest lưu tên model, đường dẫn database, tên collection và documents. `load()` cần manifest để mở lại index; chỉ có database chưa đủ cho giao diện này.
5. `search()` embedding câu hỏi rồi truy vấn top-k; `lookup()` tìm chính xác theo paper ID hoặc tiêu đề.
6. `qa.py` thực hiện semantic search và đưa kết quả exact-title lookup lên đầu nếu tìm thấy tiêu đề trong dấu nháy đơn; sau đó trích câu trả lời từ metadata. `agent.py` cung cấp semantic search và lookup làm công cụ cho LLM. Metrics ở mục 8 đánh giá luồng QA, không chứng minh chất lượng sinh câu trả lời của LLM Agent.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input DataFrame | `paper_id`, `title`, `text_for_embedding`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url` |
| Ràng buộc | ID/văn bản hợp lệ; metadata có kiểu được ChromaDB chấp nhận; model truy vấn tương thích với model build |
| Output index | Database trong `data/chroma/` và manifest tương ứng trong `data/embeddings/` |
| Output tìm kiếm | `SearchResult` gồm paper ID, title, score, content, metadata |
| Phụ thuộc | Dữ liệu sạch từ ingestion; Settings và Paths từ `core/config.py` |
| Module sử dụng | QA, Agent, evaluation và pipeline tích hợp |
| Điều kiện cần kiểm tra | Thiếu cột, metadata không hợp lệ, dữ liệu rỗng, thiếu manifest/collection, model không tải được |

### Cách xác minh

Các lệnh đọc file và đối chiếu đường dẫn đã được chạy trong quá trình rà soát với trợ lý:

```powershell
Get-Content -Encoding utf8 src/retrieval/embeddings.py
Get-ChildItem data/embeddings,data/results,data/chroma -ErrorAction SilentlyContinue | Select-Object DirectoryName,Name
rg -n 'chroma_dir|data_dir|PersistentClient|persist_path' src/core/config.py src/retrieval/index.py
rg -n 'NotImplementedError' src/ingestion/cleaning.py src/pipelines
```

- **Kết quả mong đợi:** Database, manifest và metrics có đủ, thống nhất tên collection và số liệu với báo cáo nhóm.
- **Kết quả thực tế:** Có `data/chroma/chroma.sqlite3`, ba manifest và ba file metrics. Không còn tìm thấy `NotImplementedError` trong `cleaning.py`, `phase1.py`, `corruption_flow.py`. Số liệu đã đối chiếu được trình bày ở mục 8.
- **Giới hạn:** Lần cập nhật này kiểm tra tĩnh code và đọc artifact đã có; không chạy lại build/load/search, LLM Agent hoặc pipeline end-to-end. Báo cáo nhóm ghi nhận các lần chạy pipeline thành công; đó là kết quả chung của nhóm.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần giữ riêng ba phiên bản dữ liệu để đánh giá.
- **Các phương án để đối chiếu:** Dùng một collection và thay dữ liệu mỗi lượt; hoặc dùng ba collection riêng trong cùng database.
- **Phương án hiện có trong code:** `papers-baseline`, `papers-corrupted`, `papers-repaired`, chọn thông qua đường dẫn manifest.
- **Lý do:** Rebuild corrupted không ghi đè baseline, dễ kiểm tra từng trạng thái. Đổi lại cần thêm dung lượng và quản lý đúng các manifest.
- **Bằng chứng:** Ánh xạ trong `_derive_collection_name()` khớp tên collection của ba manifest; số document tương ứng là 24/22/24. Nhóm đã lưu answers và metrics riêng cho từng trạng thái. Việc mở lại collection trên máy hiện tại cần kiểm tra thêm đường dẫn `persist_path` trong manifest.

## 6. Một lỗi hoặc blocker đã xử lý

### Đường dẫn database không khớp

- **Hiện tượng:** Database ban đầu ở `chroma/` tại gốc repository, trong khi cấu hình dùng `data/chroma/`. Đây là lệch đường dẫn quan sát được; chưa ghi nhận stack trace runtime.
- **Cách xác định:** Đối chiếu vị trí `chroma.sqlite3` với `settings.paths.chroma_dir` và nơi tạo `PersistentClient`.
- **Nguyên nhân:** Vị trí lưu database thực tế khác vị trí được cấu hình chung.
- **Cách xử lý:** Tôi đã chuyển database vào `data/chroma/`.
- **Xác minh:** Database và thư mục vector có mặt ở vị trí mới; thư mục `chroma/` ở gốc không còn.
- **Điều rút ra:** Bàn giao index phải thống nhất cả database, manifest và đường dẫn trong manifest.

### Trạng thái sau khi đồng bộ main

Các thiếu sót ghi nhận ở bản báo cáo trước đã được cập nhật: repository hiện có đủ manifest cho baseline/corrupted/repaired và các file metrics; ba module `cleaning.py`, `phase1.py`, `corruption_flow.py` không còn `NotImplementedError`.

Điểm cần kiểm tra khi tái hiện trên máy khác là `load()` đọc trực tiếp `persist_path` từ manifest và dùng model trong Settings. Vì vậy cần bảo đảm đường dẫn tồn tại và model truy vấn khớp model đã build. Việc có đủ artifact không thay thế kiểm tra load/search tại môi trường chạy mới.

Cụ thể, cả ba manifest hiện lưu đường dẫn bắt đầu bằng `D:\VinAI\`, trong khi checkout đang rà soát nằm dưới `D:\AiInAction\Lap10\`. Do đó, database đã nằm đúng thư mục tương đối `data/chroma/` nhưng đường dẫn tuyệt đối trong manifest chưa khớp checkout này. Khi tái hiện cần rebuild để sinh manifest theo cấu hình máy hiện tại hoặc xử lý đường dẫn khi load; lần cập nhật báo cáo này chưa thay đổi manifest hay chạy lại index.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref đến index:** Lưu raw snapshot, parse records, làm sạch/khử trùng lặp, tính `age_days`, tạo `text_for_embedding`, embedding và nạp ChromaDB. Raw snapshot là nguồn dùng để repair.
2. **Evaluation:** So ID truy xuất với `ground_truth_doc_ids`; code tính một hit nếu có ít nhất một ID đúng. So câu trả lời với ground truth qua token F1 và judge. Judge có fallback heuristic khi LLM evaluator không dùng được.
3. **Quality và freshness:** Quality kiểm tra tính hợp lệ như null, trùng ID và độ dài; freshness kiểm tra tuổi dữ liệu. Dữ liệu đúng schema vẫn có thể cũ. Theo yêu cầu lab, cảnh báo khi tỷ lệ bài có `age_days > 180` vượt 25%.
4. **Cùng test set:** Giữ nguyên câu hỏi và ground truth để so ảnh hưởng của corruption/repair, tránh thay đổi độ khó đánh giá giữa các lượt.
5. **Xác nhận repair:** Dựng lại dữ liệu từ raw, rebuild repaired index, đánh giá lại quality/freshness và metrics trên cùng test set. So với baseline để xác định mức phục hồi; không chỉ dựa vào lệnh chạy không lỗi. Khi kiểm tra tính lặp lại cần giữ nhất quán mốc thời gian tính tuổi dữ liệu.

## 8. Phân tích kết quả

### Metrics chính

Số liệu dưới đây được đọc từ `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` và đối chiếu với `report/group_report.md`. Đây là kết quả pipeline của nhóm đã lưu trong repository, không phải kết quả một lần chạy mới của cá nhân.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | --- | --- | --- | --- |
| `retrieval_hit_rate` | 1.0 | 0.8 | 1.0 | Corruption làm 2/10 câu không truy xuất đúng ground-truth ID |
| `mean_token_f1` | 1.0 | 0.9 | 1.0 | Chất lượng câu trả lời giảm rồi phục hồi về baseline |
| `judge_accuracy` | 1.0 | 0.9 | 1.0 | Theo báo cáo nhóm, judge dùng heuristic fallback dựa trên token F1 |
| `mean_judge_score` | 5.0 | 4.6 | 5.0 | Không diễn giải như điểm của LLM judge độc lập |
| Quality checks | 6/6 PASS | 4/6 PASS | 6/6 PASS | Corrupted thất bại kiểm tra trùng ID và độ dài summary |
| Freshness status | Fresh (4.17%) | Stale (40.91%) | Fresh (4.17%) | Ngưỡng stale tối đa 25%, tuổi bài vượt 180 ngày |

Quality được đối chiếu với `data/quality/baseline_quality_report.json`, `corrupted_quality_report.json`, `repaired_quality_report.json`; freshness từ `freshness_report.json`, `corrupted_freshness_report.json`, `repaired_freshness_report.json` trong cùng thư mục. Bộ đánh giá có 10 câu, dùng chung `data/eval/test_set.json` và `top_k=4`. Cả ba file metrics ghi Ragas bị bỏ qua (`skipped`), nên không có điểm Ragas để kết luận.

### Phân tích từ góc nhìn retrieval và QA

1. **Title là đầu vào quan trọng của lookup:** Theo phân tích trong báo cáo nhóm, `truncate_title` làm hỏng exact-title lookup ở `eval_003`; kết quả semantic search không chứa tài liệu đúng, dẫn đến trả lời sai ngày. Hit rate và token F1 cùng phát hiện lỗi này.
2. **Câu trả lời đúng chưa bảo đảm retrieval đúng:** Ở `eval_004`, paper ground truth bị loại bởi `drop_latest_records`, nhưng một paper khác có cùng categories nên câu trả lời vẫn khớp. Vì vậy corrupted có hit rate 0.8 trong khi token F1 vẫn 0.9. Đây là lý do cần theo dõi cả hai metric.
3. **Observability bổ sung cho bộ câu hỏi:** Corrupted có 6 dòng vi phạm uniqueness, 3 summary rỗng và 9/22 bài stale. Không phải mọi trường bị hỏng đều được hỏi trong test set, nên metrics QA không phản ánh đầy đủ mức hỏng dữ liệu.
4. **Repair phục hồi trên bộ đo hiện có:** Sau khi nhóm dựng lại dữ liệu từ raw và rebuild repaired index, bốn metrics trở về baseline, quality đạt 6/6 và stale còn 1/24. Kết quả này áp dụng cho snapshot và test set đang dùng, chưa chứng minh mọi câu hỏi mới đều được xử lý đúng.

Baseline đạt 1.0 cần được hiểu trong bối cảnh QA ưu tiên exact-title lookup và trích metadata khớp cách tạo ground truth. Kết quả không phải phép đo riêng semantic search hay khả năng sinh câu trả lời của LLM. Điểm đáng chú ý là trả lời đúng vẫn có thể che giấu việc truy xuất sai tài liệu, như trường hợp `eval_004`.

## 9. Điều rút ra và hướng cải thiện

1. Bàn giao vector index cần thống nhất schema, model, collection và đường dẫn artifact; chỉ có database chưa đủ cho luồng load của dự án.
2. Chất lượng dữ liệu và độ mới dữ liệu là hai khía cạnh riêng, cần quan sát cả hai trước khi kết luận phục hồi.
3. Tìm đúng tài liệu chưa đảm bảo trả lời đúng nếu metadata/nội dung bị hỏng; phải đánh giá cả retrieval và câu trả lời.

Nếu có thêm thời gian, bổ sung kiểm tra build → load → search cho từng trạng thái, đối chiếu số document với DataFrame và theo dõi một nhóm câu hỏi cố định. So sánh semantic-only retrieval với QA có exact-title lookup để giải thích nguồn gốc hit rate.

## 10. Cam kết của thành viên

Tôi đã đọc lại và xác nhận các nội dung sau trước khi nộp:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đinh Văn Bình

**Ngày xác nhận:** 2026-09-26
