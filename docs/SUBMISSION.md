# Nội Quy, Hướng Dẫn Nộp Bài & Checklist Nghiệm Thu

> ⚠️ **QUY ĐỊNH BẮT BUỘC:**  
> Dù bài lab làm theo nhóm, **MỖI CÁ NHÂN ĐỀU PHẢI TỰ NỘP ĐƯỜNG LINK REPO LÊN VLEARN LMS** từ tài khoản cá nhân.  
> Thành viên nào không nộp link → hệ thống ghi nhận **0 điểm**.

---

## 1. Deadline & Chính Sách Trễ Hạn

- **Hạn nộp mặc định:** `23:59:59` ngày diễn ra bài lab (GMT+7).
- **Trễ 0–2 giờ:** Trừ 10% tổng điểm.
- **Trễ 2–12 giờ:** Trừ 25% tổng điểm.
- **Trễ > 12 giờ:** 0 điểm (trừ bất khả kháng được Giảng viên phê duyệt trước hạn chót).

---

## 2. Quy Tắc Đặt Tên Repo Bài Nộp

Theo **Quy ước chung Khóa 4**:
- **Công thức:** `K4-L3B-DAY10-TenNhom-DataPipelineDataObservability`
- **Ví dụ:** `K4-L3B-DAY10-AlphaTeam-DataPipelineDataObservability`

---

## 3. Bảo Mật API Key

- **Tuyệt đối cấm** commit `.env`, `GOOGLE_API_KEY`, `OPENAI_API_KEY` hoặc bất kỳ Secret/Token nào vào Git.
- Luôn dùng `.env.example` với placeholder (`your_api_key_here`).
- **Vi phạm:** Trừ 20 điểm + yêu cầu revoke key. Nếu gây rò rỉ chi phí trên public repo: 0 điểm toàn bài.

---

## 4. Chính Sách Sử Dụng AI

- **Được phép:** Dùng Gemini, Claude, ChatGPT, Copilot, Cursor để tra cú pháp, giải thích thư viện, gợi ý code.
- **Bắt buộc:** Mọi dòng code commit phải do nhóm hiểu rõ logic và có khả năng giải thích trước Giảng viên/Mentor.
- **Cấm:** Copy-paste mù quáng từ AI mà không kiểm chứng luồng dữ liệu.

---

## 5. Liêm Chính Học Thuật

- Mỗi nhóm tự thiết kế, lập trình và chạy pipeline. Cấm clone/tráo artifact giữa các nhóm.
- Các file báo cáo (`phase1_report.md`, `corruption_report.md`) và kết quả (`*_metrics.json`) phải được sinh từ pipeline thực tế. Cấm bịa/sửa tay số liệu.
- **Vi phạm:** 0 điểm toàn bài + kỷ luật học thuật theo quy chế VinUni.

---

## 6. Đóng Góp Nhóm & Minh Bạch Phân Công

- Điền đầy đủ `TEAM.md`: danh sách, MSSV, vai trò, phân công từng CP.
- Điểm cá nhân đối chiếu giữa `TEAM.md` và lịch sử commit Git. Không commit = 0 điểm cá nhân.

---

## 7. Cấu Trúc Repo Phải Nộp (Deliverables)

```text
K4-L3B-DAY10-TenNhom-DataPipelineDataObservability/
├── data/
│   ├── raw/              ← crossref_response.json, crossref_records.json
│   ├── clean/            ← papers_clean.csv, papers_clean.json
│   ├── chroma/           ← ChromaDB vector collections
│   ├── eval/             ← test_set.json (10 câu benchmark)
│   ├── quality/          ← baseline/corrupted/freshness quality reports (GX 1.x)
│   ├── results/          ← baseline/corrupted/repaired_metrics.json, corruption_log.json
│   └── reports/          ← phase1_report.md, corruption_report.md
├── script/               ← run_phase1.py, run_corruption_flow.py
├── src/                  ← Code hoàn thiện: core/, ingestion/, retrieval/, evaluation/, observability/
├── report/               ← group_report.md + <MSSV>_HoTen.md (báo cáo cá nhân)
├── docs/                 ← CHECKPOINTS.md, RUBRIC.md, SUBMISSION.md, TEAM.md
├── README.md
└── .env.example
```

---

## 8. Checklist Trước Khi Nộp Link Lên VLearn

- [x] `python script/run_phase1.py` chạy exit code 0
- [x] `python script/run_corruption_flow.py` chạy exit code 0
- [x] `data/reports/corruption_report.md` có bảng đối chiếu Baseline vs Corrupted vs Repaired
- [x] Có đủ `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`
- [x] `TEAM.md` điền đầy đủ họ tên, MSSV, phần tự khai cá nhân
- [x] Không commit `.env` lên GitHub
- [x] Tab **Insights → Contributors** trên GitHub: 100% thành viên có commit trên `main`
- [x] Mỗi cá nhân nộp link repo lên VLearn LMS trước 23:59:59
