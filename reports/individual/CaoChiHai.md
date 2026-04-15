# Báo Cáo Cá Nhân - Member 1: Ingestion / Raw Owner

**Họ và tên:** Cao Chí Hải
**Mã HV**: 2A202600011
**Vai trò:** Ingestion / Raw Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi phụ trách nguồn dữ liệu đầu vào, cách pipeline nhận raw CSV, ghi log theo `run_id`, và tạo manifest để các thành viên khác có thể theo dõi lineage của từng lần chạy. Các file chính tôi chịu trách nhiệm là `etl_pipeline.py`, `data/raw/policy_export_dirty.csv`, `data/raw/policy_export_dirty_extended.csv`, `contracts/data_contract.yaml`, và phần source map trong `docs/data_contract.md`.

Mục tiêu của tôi là đảm bảo pipeline luôn có thể xác định rõ nó đang đọc file nào, đọc được bao nhiêu record, và sau mỗi lần chạy sẽ sinh ra đủ log và manifest để các thành viên còn lại dùng làm bằng chứng. Ví dụ, Sprint 1 đã ghi được `run_id=sprint1`, `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`; còn Sprint 2 với bộ raw mở rộng đã ghi `raw_records=16`, tạo điều kiện cho nhóm đo tác động của các cleaning rule mới.

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là giữ `run_id` làm tham số CLI thay vì hard-code hoặc sinh hoàn toàn tự động. Nhờ vậy, nhóm có thể chạy các kịch bản riêng như `sprint1`, `sprint2`, `normal`, `inject-bad`, `grading-base` rồi đối chiếu trực tiếp giữa log, manifest, cleaned CSV, quarantine CSV và eval CSV.

Tôi cũng chọn cách ghi manifest sau khi pipeline xử lý xong cleaned snapshot và embed, để manifest chứa đầy đủ các trường có giá trị theo dõi: `run_id`, `run_timestamp`, `raw_path`, `raw_records`, `cleaned_records`, `quarantine_records`, `latest_exported_at`, và metric map. Cách làm này giúp monitoring và runbook có đủ thông tin để giải thích pipeline ở mức end-to-end thay vì chỉ ở mức raw ingest.

## 3. Một lỗi hoặc anomaly đã xử lý

Một lỗi thực tế tôi gặp là khi chạy pipeline với `--raw data/raw/policy_export_dirty_extended.csv`, đường dẫn raw ở dạng tương đối có thể gây lỗi khi cố convert sang path tương đối với `ROOT`. Nếu để nguyên cách xử lý cũ, manifest có thể không ghi được `raw_path` đúng cách.

Cách sửa là chuyển `raw_path` sang `.resolve()` và dùng một helper hiển thị path an toàn trước khi ghi vào log/manifest. Sau fix này, pipeline ghi được:

- `raw_path = data\raw\policy_export_dirty_extended.csv`
- `manifest_written = artifacts\manifests\manifest_sprint2.json`

Điều đó đảm bảo đội ingestion và đội monitoring luôn nhìn thấy đúng raw source nào đã được dùng trong từng run.

## 4. Bằng chứng trước / sau

Sự khác biệt trước / sau ở phần ingest thể hiện rõ qua số lượng record:

- `sprint1`: `raw_records=10`
- `sprint2`: `raw_records=16`

Việc mở rộng raw sample từ 10 lên 16 record giúp nhóm có đủ các case thật để chứng minh cleaning và validation không còn là “trivial”. Cụ thể, nhờ bộ raw mở rộng mà Sprint 2 đo được `rule_normalize_exported_at=14`, `rule_fix_hr_leave_version=1`, `validation_chunk_too_short=1`, và Sprint 3 tạo được kịch bản `inject-bad` có stale refund chunk để đánh giá retrieval regression.

## 5. Cải tiến tiếp theo

Nếu có thêm thời gian, tôi muốn bổ sung checksum hoặc source version vào manifest để việc audit raw input đáng tin cậy hơn, đặc biệt khi có nhiều batch export cùng nằm trong thư mục `data/raw/`.
