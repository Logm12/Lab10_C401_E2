# Kiến trúc pipeline - Lab Day 10

**Nhóm:** C401-E2
**Cập nhật:** `2026-04-15`

## 1. Sơ đồ luồng

<p align="center">
  <img src="Flowchart.png" width="400">
</p>


Cổng chất lượng dữ liệu (Data quality gates):

- Sau ingest/clean: `doc_id` không xác định, thiếu `effective_date`, ngày hiệu lực HR cũ, các đoạn (chunk) trùng lặp sẽ đi vào quarantine.
- Sau validate: chunk ngắn, chính sách hoàn tiền cũ còn sót, timestamp sai định dạng, trùng lặp tài liệu+chunk bị chặn trước khi embed.
- Sau publish: manifest giữ `run_id`, số lượng bản ghi, tác động metric, `latest_exported_at`.

## 2. Ranh giới trách nhiệm

| Thành phần | Đầu vào | Đầu ra | Chủ sở hữu nhóm |
|------------|-------|--------|------------|
| Ingest | Raw CSV | `raw_records`, các hàng dữ liệu thô | Ingestion Owner |
| Transform | Các hàng dữ liệu thô | Các hàng đã làm sạch + metric làm sạch | Cleaning / Quality Owner |
| Quality | Các hàng đã làm sạch | Quarantine kiểm định + kết quả mong đợi | Cleaning / Quality Owner |
| Embed | Cleaned CSV | Chroma collection `day10_kb` | Embed Owner |
| Monitor | Manifest, logs, eval CSV | Trạng thái độ tươi (freshness), bằng chứng báo cáo | Monitoring / Docs Owner |

## 3. Tính không đổi (Idempotency) & chạy lại (rerun)

Pipeline embed theo snapshot publish:

- `chunk_id` được tạo ổn định từ `doc_id + chunk_text + seq`
- Chroma `upsert(ids=chunk_id, ...)` để chạy lại không tạo vector trùng lặp
- Trước khi upsert, pipeline `delete` những `ids` không còn tồn tại trong lần chạy làm sạch hiện tại

Hệ quả:

- Chạy lại cùng một đầu vào không làm phình to kho lưu trữ vector
- Chuyển từ `inject-bad` về `normal` sẽ loại bỏ các đoạn (chunk) cũ khỏi bộ sưu tập (collection)
- `hits_forbidden` có thể được cải thiện sau khi chạy lại mà không cần đặt lại thủ công Chroma

## 4. Liên hệ Day 09

Bộ sưu tập `day10_kb` là kho dữ liệu đã qua làm sạch/kiểm định để cung cấp lại khả năng truy xuất cho bài Day 09. Day 10 không thay đổi quy trình điều phối (orchestration) của Day 09, nhưng giúp agent đọc đúng phiên bản hơn bằng cách loại bỏ chính sách cũ và ghi lại ranh giới xuất bản rõ ràng.

## 5. Rủi ro đã biết

- Độ tươi (Freshness) của bộ dữ liệu mẫu đang vượt quá SLA 24h, nên manifest hiện `FAIL`.
- Khi máy không có mạng, cần đặt `HF_HUB_OFFLINE=1` và `TRANSFORMERS_OFFLINE=1` để dùng cache cục bộ của mô hình embed.
- Top-1 truy xuất có thể vẫn đúng trong khi top-k đã bị nhiễm ngữ cảnh cũ (stale context), nên phải theo dõi `hits_forbidden`.
