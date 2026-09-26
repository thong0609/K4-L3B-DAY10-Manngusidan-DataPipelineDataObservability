# BÁO CÁO ĐỐI CHIẾU 3 TRẠNG THÁI: BASELINE VS CORRUPTED VS REPAIRED

## 1. Bảng Tổng Hợp So Sánh Định Lượng

| Chỉ số / Tiêu chí đánh giá | Trạng thái Baseline (Sạch) | Trạng thái Corrupted (Bị tiêm lỗi) | Trạng thái Repaired (Tự phục hồi) | Nhận xét xu hướng |
| :--- | :---: | :---: | :---: | :--- |
| **Data Quality Gate (GX 1.x)** | **PASS** | **FAIL** | **PASS** | Gate bắt lỗi thành công khi tiêm data bẩn |
| **Freshness SLA (> 180 ngày)** | **FRESH** | **STALE** | **FRESH** | Phát hiện Stale date khi dữ liệu bị lỗi |
| **Retrieval Hit Rate** | **100.0%** | **60.0%** | **100.0%** | Sụt giảm mạnh khi lỗi, phục hồi 100% sau repair |
| **Mean Token F1** | **80.0%** | **40.7%** | **80.0%** | Khôi phục độ khớp từ vựng chính xác |
| **LLM Judge Accuracy** | **80.0%** | **40.0%** | **80.0%** | Trả lời ngữ nghĩa chuẩn xác sau khôi phục |

## 2. Phân Tích Hiện Tượng "Silent Failure" (Suy Giảm Ngầm)
Khi không có Data Observability:
1. Hệ thống RAG vẫn âm thầm chạy và trả lời người dùng mà không quăng Exception.
2. Tuy nhiên, chất lượng câu trả lời sụt giảm thảm hại (Retrieval Hit Rate rơi từ 100.0% xuống 60.0%, F1 rơi từ 80.0% xuống 40.7%).
3. Nhờ có **Great Expectations 1.x** và **Freshness SLA**, hệ thống đã chủ động cảnh báo vi phạm trước khi tri thức hỏng lây lan vào vector store.

## 3. Năng Lực Tự Phục Hồi An Toàn (Idempotent Repair)
- Quá trình Repair đọc lại từ bản Snapshot Raw bất biến (`crossref_records.json`).
- Pipeline làm sạch, kiểm định lại và tái lập Vector Index một cách an toàn mà không bị trùng lặp dữ liệu (Idempotent).
- Sau khi Repair, toàn bộ chỉ số hiệu năng và kiểm định chất lượng đều trở về trạng thái tối ưu ngang bằng Baseline ban đầu.
