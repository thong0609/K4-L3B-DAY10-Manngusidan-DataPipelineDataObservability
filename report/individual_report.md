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
| Trạng thái | Đã rà soát code và đường dẫn database; chưa nghiệm thu chạy tích hợp |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Tôi phụ trách RAG & Vector Index theo phân công trong `docs/TEAM.md`. Bảng dưới mô tả phạm vi được giao và trạng thái implementation hiện có, không khẳng định toàn bộ code trong các file này do tôi viết mới. Phần triển khai trực tiếp cần đối chiếu với commit cá nhân trước khi nộp.

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding | `src/retrieval/embeddings.py`, `MiniLMEmbeddings` | Văn bản tài liệu và câu hỏi | Vector đã chuẩn hóa | Có implementation; chưa kiểm chứng runtime trong lần rà soát này |
| Vector index | `src/retrieval/index.py`, `LocalEmbeddingIndex` | DataFrame sạch và Settings | ChromaDB collection, manifest và kết quả tìm kiếm | Có build/load/search/lookup; thiếu manifest để kiểm tra load |
| QA và Agent | `src/retrieval/qa.py`, `src/retrieval/agent.py` | Câu hỏi và index | Câu trả lời và tài liệu truy xuất | Có implementation; chưa kiểm chứng câu trả lời thực tế |
| Vị trí database | `data/chroma/` | Database đã có | Database ở đúng đường dẫn cấu hình | Đã chuyển và xác minh vị trí file |

Thành viên 2 cung cấp dữ liệu sạch và `text_for_embedding`. Thành viên 1 tích hợp index vào pipeline. Thành viên 4 dùng đầu ra retrieval/QA để đánh giá trên cùng test set.

### Việc hỗ trợ ngoài phạm vi chính

Chưa ghi nhận đóng góp ngoài phạm vi RAG & Vector Index có bằng chứng cụ thể. Cleaning, quality gate và orchestration được mô tả bên dưới để giải thích phụ thuộc, không nhận là phần đã trực tiếp thực hiện.

## 3. Kết quả theo vai trò

| Nội dung đã rà soát hoặc thực hiện | Bằng chứng | Kết luận |
| --- | --- | --- |
| Rà soát embedding | `embed_documents()` và `embed_query()` dùng `normalize_embeddings=True` | Có logic dùng cùng model cho tài liệu và câu hỏi |
| Rà soát phân tách trạng thái | `_derive_collection_name()` ánh xạ ba đường dẫn manifest sang ba collection | Có logic phân tách; chưa xác minh dữ liệu từng collection |
| Chuyển database về đường dẫn chung | `data/chroma/chroma.sqlite3` và các thư mục vector hiện có | Đã khớp đường dẫn cấu hình |
| Kiểm tra điều kiện load | `data/embeddings/` chỉ có `.gitkeep` | Chưa có manifest để hàm load đọc |

Output đã xác minh là database nằm tại `data/chroma/`. Sự tồn tại của database chưa chứng minh collection đủ tài liệu hoặc truy vấn thành công.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Chuyển nội dung bài báo thành vector để tìm tài liệu liên quan đến câu hỏi, đồng thời tách index của dữ liệu sạch, dữ liệu lỗi và dữ liệu phục hồi để so sánh khách quan.

### Cách triển khai

1. `MiniLMEmbeddings` tải model `sentence-transformers/all-MiniLM-L6-v2`. Hàm tải dùng `lru_cache(maxsize=4)` để tái sử dụng model trong cùng tiến trình.
2. Mỗi dòng DataFrame trở thành document gồm `text_for_embedding` và metadata. `record_id` ghép `paper_id` với vị trí dòng, cho phép biểu diễn cả các dòng trùng paper khi mô phỏng corruption.
3. `build()` chọn collection theo đường dẫn manifest, tạo lại collection đích, tính vector và nạp ChromaDB với khoảng cách cosine.
4. Manifest lưu tên model, đường dẫn database, tên collection và documents. `load()` cần manifest để mở lại index; chỉ có database chưa đủ cho giao diện này.
5. `search()` embedding câu hỏi rồi truy vấn top-k; `lookup()` tìm chính xác theo paper ID hoặc tiêu đề.
6. `qa.py` ưu tiên exact-title lookup khi câu hỏi chứa tiêu đề trong dấu nháy đơn, rồi trích câu trả lời từ metadata. `agent.py` cung cấp semantic search và lookup làm công cụ cho LLM. Đây là hai luồng khác nhau.

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

- **Kết quả mong đợi:** Database nằm đúng vị trí được cấu hình; xác định artifact nào còn thiếu.
- **Kết quả thực tế:** Có `data/chroma/chroma.sqlite3`; cấu hình trỏ tới `data/chroma/`; chưa có manifest hoặc metrics trong các thư mục tương ứng.
- **Giới hạn:** Chỉ kiểm tra tĩnh và vị trí file; chưa chạy build/load/search, LLM Agent hoặc pipeline end-to-end.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần giữ riêng ba phiên bản dữ liệu để đánh giá.
- **Các phương án để đối chiếu:** Dùng một collection và thay dữ liệu mỗi lượt; hoặc dùng ba collection riêng trong cùng database.
- **Phương án hiện có trong code:** `papers-baseline`, `papers-corrupted`, `papers-repaired`, chọn thông qua đường dẫn manifest.
- **Lý do:** Rebuild corrupted không ghi đè baseline, dễ kiểm tra từng trạng thái. Đổi lại cần thêm dung lượng và quản lý đúng các manifest.
- **Bằng chứng:** Có ánh xạ ba collection trong `_derive_collection_name()`. Chưa có phép đo runtime chứng minh ba collection đã nạp thành công.

## 6. Một lỗi hoặc blocker đã xử lý

### Đường dẫn database không khớp

- **Hiện tượng:** Database ban đầu ở `chroma/` tại gốc repository, trong khi cấu hình dùng `data/chroma/`. Đây là lệch đường dẫn quan sát được; chưa ghi nhận stack trace runtime.
- **Cách xác định:** Đối chiếu vị trí `chroma.sqlite3` với `settings.paths.chroma_dir` và nơi tạo `PersistentClient`.
- **Nguyên nhân:** Vị trí lưu database thực tế khác vị trí được cấu hình chung.
- **Cách xử lý:** Tôi đã chuyển database vào `data/chroma/`.
- **Xác minh:** Database và thư mục vector có mặt ở vị trí mới; thư mục `chroma/` ở gốc không còn.
- **Điều rút ra:** Bàn giao index phải thống nhất cả database, manifest và đường dẫn trong manifest.

### Blocker còn lại

`data/embeddings/` chưa có `papers_embeddings.json` và manifest cho corrupted/repaired. Hàm load đọc manifest trước nên việc chuyển database chưa đủ để hoàn thành luồng load. `cleaning.py`, `phase1.py` và `corruption_flow.py` còn `NotImplementedError` tại thời điểm rà soát.

Bước tiếp theo: nhận dữ liệu sạch đúng schema, phối hợp hoàn thiện pipeline, build từng index để sinh manifest rồi xác minh load/search. Kiểm tra số document baseline theo dữ liệu đầu vào (mục tiêu lab: 24); số document corrupted/repaired phải khớp DataFrame tương ứng.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref đến index:** Lưu raw snapshot, parse records, làm sạch/khử trùng lặp, tính `age_days`, tạo `text_for_embedding`, embedding và nạp ChromaDB. Raw snapshot là nguồn dùng để repair.
2. **Evaluation:** So ID truy xuất với `ground_truth_doc_ids`; code tính một hit nếu có ít nhất một ID đúng. So câu trả lời với ground truth qua token F1 và judge. Judge có fallback heuristic khi LLM evaluator không dùng được.
3. **Quality và freshness:** Quality kiểm tra tính hợp lệ như null, trùng ID và độ dài; freshness kiểm tra tuổi dữ liệu. Dữ liệu đúng schema vẫn có thể cũ. Theo yêu cầu lab, cảnh báo khi tỷ lệ bài có `age_days > 180` vượt 25%.
4. **Cùng test set:** Giữ nguyên câu hỏi và ground truth để so ảnh hưởng của corruption/repair, tránh thay đổi độ khó đánh giá giữa các lượt.
5. **Xác nhận repair:** Dựng lại dữ liệu từ raw, rebuild repaired index, đánh giá lại quality/freshness và metrics trên cùng test set. So với baseline để xác định mức phục hồi; không chỉ dựa vào lệnh chạy không lỗi. Khi kiểm tra tính lặp lại cần giữ nhất quán mốc thời gian tính tuổi dữ liệu.

## 8. Phân tích kết quả

### Metrics chính

Chưa có file metrics để điền số liệu thực tế. “Chưa đo” không có nghĩa là 0 hoặc thất bại.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | --- | --- | --- | --- |
| `retrieval_hit_rate` | Chưa đo | Chưa đo | Chưa đo | Đối chiếu ID truy xuất với ground truth |
| `mean_token_f1` | Chưa đo | Chưa đo | Chưa đo | Độ trùng khớp token của câu trả lời |
| `judge_accuracy` | Chưa đo | Chưa đo | Chưa đo | Cần ghi rõ có dùng fallback judge không |
| `mean_judge_score` | Chưa đo | Chưa đo | Chưa đo | Đọc từ artifact đánh giá thực tế |
| Quality checks | Chưa xác minh | Chưa xác minh | Chưa xác minh | Cần báo cáo quality từng trạng thái |
| Freshness status | Chưa xác minh | Chưa xác minh | Chưa xác minh | Cần kết quả tính tuổi dữ liệu |

### Nhận định và giả thuyết cần kiểm chứng

Chưa đủ số liệu để kết luận mức suy giảm/phục hồi. Hai chuỗi dự kiến kiểm chứng:

1. Xóa bài hoặc làm rỗng summary → row count/kiểm tra độ dài có thể báo lỗi → retrieval hit hoặc chất lượng trả lời có thể giảm. Lùi ngày xuất bản → tỷ lệ stale có thể tăng → câu trả lời về ngày có thể sai.
2. Dựng lại dữ liệu từ raw và rebuild repaired → đánh giá lại quality/freshness → so metrics repaired với baseline để xác định mức phục hồi.

Chưa xác định được corruption ảnh hưởng mạnh nhất. `qa.py` ưu tiên exact-title lookup, nên hit rate không chỉ phản ánh semantic search. Summary hỏng có thể làm câu trả lời kém đi dù vẫn tìm đúng paper ID. Đây là giả thuyết từ luồng code, chưa phải kết quả đo.

Chưa có kết quả thực nghiệm để xác định điều gì khác kỳ vọng. Cần bổ sung `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` và báo cáo quality/freshness sau khi chạy tích hợp.

## 9. Điều rút ra và hướng cải thiện

1. Bàn giao vector index cần thống nhất schema, model, collection và đường dẫn artifact; chỉ có database chưa đủ cho luồng load của dự án.
2. Chất lượng dữ liệu và độ mới dữ liệu là hai khía cạnh riêng, cần quan sát cả hai trước khi kết luận phục hồi.
3. Tìm đúng tài liệu chưa đảm bảo trả lời đúng nếu metadata/nội dung bị hỏng; phải đánh giá cả retrieval và câu trả lời.

Nếu có thêm thời gian, bổ sung kiểm tra build → load → search cho từng trạng thái, đối chiếu số document với DataFrame và theo dõi một nhóm câu hỏi cố định. So sánh semantic-only retrieval với QA có exact-title lookup để giải thích nguồn gốc hit rate.

## 10. Cam kết của thành viên

Tôi cần tự đọc lại, điều chỉnh theo đóng góp trực tiếp và đánh dấu trước khi nộp:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đinh Văn Bình

**Ngày xác nhận:** Chưa xác nhận
