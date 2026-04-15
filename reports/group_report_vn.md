# Báo Cáo Nhóm - Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** C401-E2
**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/Logm12/Lab10_C401_E2

## 1. Pipeline tổng quan

Nhóm xây dựng một ETL pipeline cho bài toán hỗ trợ IT Helpdesk với luồng xử lý `ingest -> clean -> validate -> embed -> monitor`. Nguồn raw ban đầu là `data/raw/policy_export_dirty.csv`, sau đó nhóm mở rộng thêm `data/raw/policy_export_dirty_extended.csv` để có đủ các failure mode phục vụ Sprint 2 và Sprint 3. Pipeline đọc raw CSV, chuẩn hóa dữ liệu, chuyển các record không an toàn sang quarantine, publish cleaned snapshot vào Chroma, rồi ghi manifest và log theo `run_id`.

Các lần chạy chính của nhóm gồm:

- `sprint1` cho ingest + schema + manifest
- `sprint2` cho clean + validate + embed
- `normal` cho retrieval baseline sạch
- `inject-bad` cho kịch bản corruption có chủ đích

README của nhóm đã có “một lệnh chạy cả pipeline”, và toàn bộ artifact được lưu trong `artifacts/logs/`, `artifacts/manifests/`, `artifacts/quarantine/`, `artifacts/cleaned/`, `artifacts/eval/`.

## 2. Cleaning & expectation

Baseline nhóm giữ các rule xử lý dữ liệu bẩn như: allowlist `doc_id`, chuẩn hóa `effective_date`, quarantine stale HR effective date, fix refund 14 -> 7 ngày, và dedupe chunk. Trên nền đó, Sprint 2 bổ sung thêm các rule có tác động đo được và 2 expectation mới ở mức `halt`.

### Bảng metric_impact

| Rule / Expectation mới | Trước | Sau | Chứng cứ |
|------------------------|-------|-----|----------|
| `rule_normalize_exported_at` | 14 record có `exported_at` chưa chuẩn UTC-ISO | 14 record được chuẩn hóa thành `YYYY-MM-DDTHH:MM:SSZ` | `run_sprint2.log`, `manifest_sprint2.json` |
| `rule_normalize_contact_tokens` | 1 chunk có email in hoa và hotline có dấu gạch | 1 chunk được chuẩn hóa thành `it-help@vinuni.edu`, `0901234567` | `cleaned_sprint2.csv` |
| `rule_normalize_currency_vnd` | 1 chunk có `700000 vnd` | 1 chunk được chuẩn hóa thành `700,000 VND` | `cleaned_sprint2.csv` |
| `rule_html_unescape` + `rule_compact_whitespace` | 1 chunk có `&nbsp;` và spacing lộn xộn | 1 chunk được unescape và compact whitespace | `cleaned_sprint2.csv` |
| `rule_fix_hr_leave_version` | 1 chunk HR 2026 vẫn còn “10 ngày phép năm” | 1 chunk được fix thành “12 ngày phép năm” | `run_sprint2.log`, `cleaned_sprint2.csv` |
| `exported_at_iso_utc` (halt) | Trước clean có 14 record sai định dạng target | Sau validate `invalid_exported_at=0` | `run_sprint2.log` |
| `unique_doc_id_chunk_text` (halt) | Raw có 2 duplicate chunk | Sau clean/validate `duplicate_pairs=0` | `run_sprint2.log`, `quarantine_sprint2.csv` |
| `validation_chunk_too_short` | 1 chunk “Reset?” vượt qua ingest | 1 chunk bị chuyển vào validation quarantine | `quarantine_sprint2.csv` |

Hai expectation mới nhóm giữ ở mức `halt` là:

- `exported_at_iso_utc`
- `unique_doc_id_chunk_text`

Kết quả run `sprint2` cho thấy pipeline chuẩn `exit 0`, `cleaned_records=10`, `quarantine_records=6`, và `PIPELINE_OK`.

## 3. Before / after ảnh hưởng retrieval

Sprint 3 được thực hiện bằng hai kịch bản:

- `normal`: clean + validate đầy đủ, sau đó eval lưu tại `artifacts/eval/normal.csv`
- `inject-bad`: chạy với `--no-refund-fix --skip-validate`, sau đó eval lưu tại `artifacts/eval/inject-bad.csv`

Nhóm dùng `top-k=5` để quét stale evidence trên toàn bộ top-k, không chỉ nhìn top-1.

### Kết quả chính

- `q_refund_window`
  - `normal`: `contains_expected=yes`, `hits_forbidden=no`
  - `inject-bad`: `contains_expected=yes`, `hits_forbidden=yes`
- `q_leave_version`
  - cả hai kịch bản đều `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`
- `q_p1_sla`
  - cả hai kịch bản đều `contains_expected=yes`, `hits_forbidden=no`

Ý nghĩa quan trọng nhất là `q_refund_window` cho thấy retrieval có thể nhìn “đúng” ở top-1 nhưng vẫn sai ở tầng context khi top-k còn stale chunk. Đây chính là bằng chứng nhóm dùng để chứng minh pipeline clean/publish giúp dữ liệu ổn định hơn.

## 4. Freshness & monitoring

Nhóm chạy freshness check trên manifest thật:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py freshness --manifest artifacts/manifests/manifest_normal.json
```

Kết quả:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.516, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Nhóm quy ước:

- `PASS`: timestamp nằm trong SLA
- `WARN`: manifest thiếu timestamp hoặc timestamp không parse được
- `FAIL`: timestamp hợp lệ nhưng đã quá SLA

Điều quan trọng là freshness fail ở đây phản ánh dữ liệu mẫu cũ, không phải pipeline code lỗi. Nhóm ghi rõ cách diễn giải này trong `docs/runbook.md`.

## 5. Liên hệ Day 09

Collection `day10_kb` là corpus đã qua clean và validate để phục vụ lại retrieval cho bài Day 09. Nhóm tách collection này khỏi collection cũ để tránh stale vector, đồng thời chứng minh tính idempotent của publish boundary. Sau khi rerun từ `inject-bad` về `normal`, stale chunk refund biến mất khỏi top-k retrieval.

## 6. Peer Review Q&A

**1. Tại sao nhóm không chỉ đo top-1 retrieval?**  
Vì top-1 có thể vẫn nhìn đúng trong khi top-k đã chứa stale context. `q_refund_window` là ví dụ rõ nhất: ở `inject-bad`, top-1 vẫn là `policy_refund_v4` nhưng `hits_forbidden=yes`.

**2. Tại sao cần quarantine thay vì cố sửa mọi record?**  
Nhóm chỉ sửa những lỗi có thể sửa an toàn như normalize date, contact token, currency, hoặc fix canonical text rõ ràng. Những record không đủ chất lượng publish như chunk quá ngắn hoặc source lạ sẽ bị cách ly để tránh đưa rác vào vector store.

**3. Nếu freshness fail nhưng expectation pass, có nên publish không?**  
Trong bài lab, nhóm vẫn publish để tạo bằng chứng monitoring và before/after. Trong hệ thống thực tế, đây có thể là điều kiện cảnh báo mạnh hoặc dừng publish tùy SLA.

## 7. Rủi ro còn lại & việc chưa làm

- Bộ dữ liệu mẫu vẫn stale theo SLA 24h nên freshness luôn `FAIL`
- Eval hiện tại là retrieval keyword-based, chưa chấm full answer generation
- Bốn thành viên cần điền tên thật và thông tin cá nhân vào các file `reports/individual/*.md`
