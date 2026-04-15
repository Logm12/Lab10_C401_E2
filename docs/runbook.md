# Runbook - Lab Day 10

## Triệu chứng (Symptom)

Triệu chứng thường gặp:

- Agent trả lời "14 ngày làm việc" thay vì 7 ngày cho chính sách hoàn tiền (refund policy).
- Truy xuất top-1 đúng nhưng top-k vẫn chứa các đoạn cũ (stale chunk).
- Pipeline `run` dừng vì kiểm tra mong đợi (expectation) bị `halt`.
- Kiểm tra độ tươi (Freshness check) báo `FAIL`.

## Phát hiện (Detection)

Kiểm tra theo thứ tự:

- `artifacts/logs/run_<run_id>.log`
- `artifacts/manifests/manifest_<run_id>.json`
- `artifacts/quarantine/quarantine_<run_id>.csv`
- `artifacts/eval/*.csv`

Quy ước độ tươi (Freshness convention):

- `PASS`: `latest_exported_at` nằm trong SLA 24h.
- `WARN`: manifest thiếu timestamp hoặc timestamp không phân tích (parse) được.
- `FAIL`: timestamp hợp lệ nhưng đã vượt SLA.

Kết quả thực tế:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py freshness --manifest artifacts/manifests/manifest_normal.json
```

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.516, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

## Chẩn đoán (Diagnosis)

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở manifest của lần chạy hiện tại | Thấy `run_id`, số lượng bản ghi, `latest_exported_at`, `clean_metrics`, `validation_metrics` |
| 2 | Mở file quarantine CSV | Biết bản ghi lỗi nằm ở giai đoạn `clean` hay `validate` |
| 3 | Mở file cleaned CSV | Kiểm tra xem các đoạn cũ đã được sửa/loại bỏ (fix/prune) chưa |
| 4 | Đọc bản ghi chạy hệ thống (run log) | Thấy các mong đợi thất bại và tác động lên metric |
| 5 | Chạy đánh giá với `top-k 5` | Kiểm tra `hits_forbidden` trên toàn bộ top-k |

## Xử lý & Giảm thiểu (Mitigation)

Chạy lại bình thường (Normal rerun):

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id normal --raw data/raw/policy_export_dirty_extended.csv
.\.venv\Scripts\python.exe eval_retrieval.py --out artifacts/eval/normal.csv --top-k 5
```

Đưa lỗi vào để tái hiện (Inject corruption):

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id inject-bad --raw data/raw/policy_export_dirty_extended.csv --no-refund-fix --skip-validate
.\.venv\Scripts\python.exe eval_retrieval.py --out artifacts/eval/inject-bad.csv --top-k 5
```

Nếu độ tươi thất bại nhưng các mong đợi đều vượt qua:

- Không cần khôi phục mã nguồn (rollback code).
- Ghi rõ dữ liệu đang bị cũ trong báo cáo.
- Yêu cầu xuất dữ liệu mới hoặc cập nhật nguồn.

## Phòng ngừa (Prevention)

- Giữ `refund_no_stale_14d_window` là một mong đợi ở mức `halt`.
- Giữ `unique_doc_id_chunk_text` và `exported_at_iso_utc` là các mong đợi ở mức `halt`.
- Luôn đánh giá truy xuất với `top-k >= 5` cho các câu hỏi về phiên bản.
- Ghi `run_id` vào manifest/log để phục vụ kiểm toán (audit).
- Khi máy không có mạng, bật chế độ ngoại tuyến cho HF cache.

## Câu hỏi & Trả lời Review (Peer Review Q&A)

1. Tại sao nhóm không chỉ đo top-1 retrieval?
Vì top-1 có thể vẫn "đúng" trong khi top-k đã chứa các đoạn cũ. `q_refund_window` trong `inject-bad` là ví dụ rõ nhất.

2. Tại sao cần quarantine thay vì sửa tất cả bản ghi?
Chỉ sửa những lỗi có thể sửa an toàn như ngày tháng/tiền tệ/liên hệ. Các bản ghi mơ hồ hoặc không đủ giá trị truy xuất cần bị tách riêng để tránh đưa rác vào hệ thống (embed rác).

3. Nếu độ tươi thất bại nhưng các mong đợi đều vượt qua, có nên xuất bản (publish) không?
Trong bài lab này, nhóm vẫn xuất bản để có bằng chứng giám sát. Trong hệ thống thực, đây sẽ là điều kiện cảnh báo hoặc tạm dừng xuất bản tùy thuộc vào SLA.
