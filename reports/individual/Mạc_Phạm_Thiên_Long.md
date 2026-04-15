# Báo cáo cá nhân - Lab Day 10

**Họ và tên:** Mạc Phạm Thiên Long
**Nhóm:** C401_E2
**Vai trò:** Monitoring / Docs Owner
**Ngày nộp:** `2026-04-15`

## 1. Tôi phụ trách phần nào?

Em phụ trách Freshness của dữ liệu (freshness monitoring), sổ tay vận hành (runbook), kiến trúc pipeline (pipeline architecture), và tổng hợp báo cáo nhóm. Các file em chịu trách nhiệm (ownership) là `monitoring/freshness_check.py`, `docs/runbook.md`, `docs/quality_report.md`, `README.md`, và `reports/group_report.md`.

Mục tiêu của em là biến các sản phẩm kỹ thuật (artifacts) thành bằng chứng để nộp bài: có sơ đồ pipeline, cách đọc các trạng thái PASS/WARN/FAIL, và liên kết rõ ràng giữa logs, manifests, eval CSV, cùng chất lượng báo cáo.

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng là theo dõi freshness dựa trên `latest_exported_at` trong manifest, không chỉ dựa trên `run_timestamp`. Nếu chỉ nhìn `run_timestamp`, pipeline có thể trông có vẻ mới dù dữ liệu nguồn đã cũ. Cách đo hiện tại giúp nhóm phát hiện bộ dữ liệu mẫu vẫn bị cũ (stale) theo SLA 24h dù pipeline đã xuất bản thành công.

## 3. Một lỗi hoặc bất thường (anomaly) đã xử lý

Bất thường lớn nhất trong giám sát là `freshness_check=FAIL` trong các lần chạy `sprint2`, `normal`, và `inject-bad`. Đây không phải lỗi mã nguồn mà là dấu hiệu dữ liệu mẫu có `latest_exported_at = 2026-04-10T08:00:00Z`, cũ hơn SLA 24h. Em đã đưa kết quả này vào runbook để giải thích rằng đây là data staleness, không phải do pipeline bị lỗi.

## 4. Bằng chứng trước / sau

Bằng chứng em sử dụng là kết quả lệnh:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py freshness --manifest artifacts/manifests/manifest_normal.json
```

Kết quả:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.516, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Em kết hợp bằng chứng này với `normal.csv` và `inject-bad.csv` để giải thích: chất lượng dữ liệu có thể tốt lên sau khi làm sạch, nhưng freshness vẫn cần được theo dõi độc lập.

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, em sẽ thêm một boundary freshness ở giai đoạn nạp (ingest stage) và lưu cả `raw_seen_at` để phân biệt giữa dữ liệu nguồn cũ và pipeline chạy chậm.
