# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| policy_export_dirty.csv | Batch export từ Document DB | Duplicate chunks, sai ngày tháng (01/02/2026), missing effective_date, stale policy version (refund 14 vs 7 ngày) | Alert nếu `raw_records` < threshold hoặc `quarantine_records` > 5% |
| Docs folder (docs/) | Manual upload / static files | Version mismatch (file chứa ngành kế tiếp), canonical không đồng bộ | Daily freshness check: manifest `exported_at` không quá 24h |
| HR Policy DB | Async export | Version conflict (10 vs 12 ngày phép), missing `effective_date` | `expectation_hr_version` check tại cleaned stage |
| IT Helpdesk FAQ | Wiki crawl | Duplicate sections, HTML escape chars, truncation | Quarantine nếu `chunk_text` < 8 ký tự hoặc regex fail |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Khóa ổn định (hash hoặc doc_id + seq), generate lại mỗi ingest nếu content thay đổi |
| doc_id | string | Có | Khóa logic: policy_refund_v4, hr_leave_policy, it_helpdesk_faq, sla_p1_2026; phải trong allowlist |
| chunk_text | string | Có | Min 8 ký tự; trim space; không chứa ký tự encode escape (vd &nbsp;); tiếng Việt UTF-8 |
| effective_date | date | Có | ISO format (YYYY-MM-DD); không nullable; phải ≥ 2025-01-01 cho HR, ≥ 2026-01-01 cho mới |
| exported_at | datetime | Có | Timestamp khi export từ nguồn; ISO format; timezone UTC |

---

## 3. Quy tắc quarantine vs drop

| Tình huống | Hành động | Ai review | Ghi chú |
|-----------|----------|-----------|---------|
| Duplicate `chunk_text` + `doc_id` | Quarantine (lần 2+) | Data owner | Keep first occurrence, flag update |
| `effective_date` không ISO hoặc null | Quarantine | Data owner | Expectation `no_invalid_date` halt nếu >1% |
| `doc_id` không trong allowlist | Quarantine | Data owner | Chờ whitelist mở rộng + reprocess |
| `chunk_text` < 8 ký tự | Quarantine | Data owner | Thường là dòng trống hoặc header |
### Source of truth (canonical)

| Tài liệu | Nghĩa | Version canonical | Review frequency |
|---------|-------|-------------------|------------------|
| `data/docs/policy_refund_v4.txt` | Refund policy effective 2026-02 | v4 (7 ngày) | Monthly |
| `data/docs/hr_leave_policy.txt` | Leave entitlement per experience | 2026 (12 ngày) | Yearly (Jan) |
| `data/docs/it_helpdesk_faq.txt` | Self-service procedures | Current crawl | Weekly |
| `data/docs/sla_p1_2026.txt` | P1 ticket SLA (4h resolution) | 2026 baseline | Q4 review |

### Reconciliation

- **Khôi phục**: Nếu export chứa stale version (vd refund 14 ngày từ policy-v3), cleaning rule `fix_refund_window` sẽ thay thế text → quarantine + mark "fixed"
- **Embed**: Upsert theo `chunk_id` + `doc_id` + `effective_date` tuple (tránh collision) Domain + cleanup | Fix dòng text → merge lại vào cleaned |

---

## 4. Phiên bản & canonical

| Domain | Source of truth | Canonical rule | Dấu hiệu lỗi cần chặn |
|--------|-----------------|----------------|------------------------|
| Refund policy | `data/docs/policy_refund_v4.txt` | Refund window phải là `7 days`; effective date theo bản v4 | Còn text `14 days` hoặc version cũ xuất hiện trong `chunk_text` |
| HR leave policy | `data/docs/hr_leave_policy.txt` | Annual leave mặc định năm 2026 là `12 days` | Còn entitlement `10 days` sau clean |
| SLA P1 | `data/docs/sla_p1_2026.txt` | P1 resolution target là `4 hours` | Export cũ hoặc doc khác giá trị canonical |
| IT helpdesk FAQ | `data/docs/it_helpdesk_faq.txt` | Nội dung theo crawl mới nhất, không duplicate section | Chunk ngắn, lỗi escape, hoặc lặp section |

---

## 5. Metric theo dõi Sprint 1

| Metric | Ý nghĩa | Mục tiêu / SLA | Nguồn đo |
|--------|---------|----------------|----------|
| `raw_records` | Số record ingest từ raw CSV | Không bằng 0; cảnh báo nếu thấp hơn baseline batch | `artifacts/logs/run_<run_id>.log` |
| `cleaned_records` | Số record còn lại sau clean | Phải lớn hơn 0 | Log + `artifacts/cleaned/*.csv` |
| `quarantine_records` | Số record bị cách ly | <= 5% khi vận hành ổn định; lab có thể cao hơn do dữ liệu bẩn | Log + `artifacts/quarantine/*.csv` |
| `run_timestamp` | Dấu mốc run để audit | Luôn có trong manifest | `artifacts/manifests/manifest_<run_id>.json` |
| `latest_exported_at` | Mốc freshness của dữ liệu sạch | Không quá 24h so với thời điểm publish | Manifest + lệnh `freshness` |

## 6. Sprint 1 acceptance snapshot

- Raw source hiện tại: `data/raw/policy_export_dirty.csv`
- Manifest bắt buộc có: `run_id`, `run_timestamp`, `raw_records`, `cleaned_records`, `quarantine_records`
- Log bắt buộc có: `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`
- Khi chạy `python etl_pipeline.py run --run-id sprint1`, pipeline phải thoát `exit 0` và ghi đủ artifacts log, cleaned CSV, quarantine CSV, manifest JSON
