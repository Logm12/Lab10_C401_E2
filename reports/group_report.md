# Bao Cao Nhom - Lab Day 10: Data Pipeline & Data Observability

**Ten nhom:** ___________
**Thanh vien:**
| Ten | Vai tro (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngay nop:** `2026-04-15`
**Repo:** ___________

## 1. Pipeline tong quan

Nguon raw chinh la `data/raw/policy_export_dirty.csv` va bo mo rong `data/raw/policy_export_dirty_extended.csv`. Luong ETL cua nhom la ingest CSV -> clean -> validation quarantine -> embed Chroma -> ghi manifest/log -> freshness check. `run_id` duoc truyen tu CLI va xuat ra trong `artifacts/logs/run_<run_id>.log` cung `artifacts/manifests/manifest_<run_id>.json`.

Lenh chay mot dong:

```powershell
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe etl_pipeline.py run --run-id final --raw data/raw/policy_export_dirty_extended.csv
```

## 2. Cleaning & expectation

Baseline cua nhom giu cac buoc clean can thiet: allowlist `doc_id`, normalize `effective_date`, dedupe, fix refund 14->7 ngay, quarantine stale HR effective date. Sprint 2 mo rong them cac rule co tac dong do duoc va them validation quarantine de record xau khong di thang vao embed.

### Bang metric_impact

| Rule / Expectation moi | Truoc (so lieu) | Sau (so lieu) | Chung cu |
|------------------------|-----------------|---------------|----------|
| `rule_normalize_exported_at` | 14 record co `exported_at` chua dung UTC-ISO | 14 record duoc chuan hoa thanh `YYYY-MM-DDTHH:MM:SSZ` | `artifacts/logs/run_sprint2.log`, `artifacts/manifests/manifest_sprint2.json` |
| `rule_normalize_contact_tokens` | 1 chunk co email in hoa va hotline co dau gach | 1 chunk duoc chuan hoa thanh `it-help@vinuni.edu`, `0901234567` | `artifacts/cleaned/cleaned_sprint2.csv` |
| `rule_normalize_currency_vnd` | 1 chunk co `700000 vnd` | 1 chunk duoc chuan hoa thanh `700,000 VND` | `artifacts/cleaned/cleaned_sprint2.csv` |
| `rule_html_unescape` + `rule_compact_whitespace` | 1 chunk co `&nbsp;` va spacing lon xon | 1 chunk duoc unescape va compact whitespace | `artifacts/cleaned/cleaned_sprint2.csv` |
| `rule_fix_hr_leave_version` | 1 chunk HR 2026 van con `10 ngay phep nam` | 1 chunk duoc fix thanh `12 ngay phep nam` | `artifacts/logs/run_sprint2.log`, `artifacts/cleaned/cleaned_sprint2.csv` |
| `exported_at_iso_utc` (halt) | Truoc clean co 14 record sai dinh dang target | Sau validate `invalid_exported_at=0` | `artifacts/logs/run_sprint2.log` |
| `unique_doc_id_chunk_text` (halt) | Raw co 2 duplicate chunk | Sau clean/validate `duplicate_pairs=0` | `artifacts/logs/run_sprint2.log`, `artifacts/quarantine/quarantine_sprint2.csv` |
| `validation_chunk_too_short` | 1 chunk ngan `Reset?` vuot qua ingest | 1 chunk bi dua vao validation quarantine | `artifacts/quarantine/quarantine_sprint2.csv` |

Expectation moi khai bao `halt`:

- `exported_at_iso_utc`
- `unique_doc_id_chunk_text`

## 3. Before / after anh huong retrieval hoac agent

Kich ban `normal` duoc chay voi clean + validate day du, sau do eval luu tai `artifacts/eval/normal.csv`. Kich ban `inject-bad` duoc chay voi `--no-refund-fix --skip-validate`, sau do eval luu tai `artifacts/eval/inject-bad.csv`. Ca hai cung dung `top-k=5` de quet stale chunk tren toan bo top-k.

Bang chung dinh luong noi bat:

- `q_refund_window`: `normal` co `contains_expected=yes`, `hits_forbidden=no`; `inject-bad` co `contains_expected=yes`, `hits_forbidden=yes`.
- `q_leave_version`: ca hai kich ban deu `contains_expected=yes`, `top1_doc_expected=yes`, cho thay rule fix HR version on dinh.
- `q_p1_sla`: giu on dinh o ca hai kich ban, dung de doi chieu voi cau refund bi corruption.

Y nghia chinh la retrieval co the nhin dung o top-1 nhung van xau di o top-k do stale context. Day la bang chung pipeline clean/publish da cai thien data stability, khong chi cai thien mot dong text.

## 4. Freshness & monitoring

Manifest `normal` va `inject-bad` deu bao `freshness_check=FAIL` vi `latest_exported_at = 2026-04-10T08:00:00Z`, cu hon SLA 24h. Theo quy uoc cua nhom:

- `PASS`: timestamp nam trong SLA
- `WARN`: manifest thieu/khong parse duoc timestamp
- `FAIL`: timestamp hop le nhung da vuot SLA

Lenh kiem tra:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py freshness --manifest artifacts/manifests/manifest_normal.json
```

Ket qua thuc te:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.516, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

## 5. Lien he Day 09

Collection `day10_kb` la corpus da clean/validate de cap lai retrieval cho bai Day 09. Nhom tach collection nay khoi collection cu de tranh stale vector va de chung minh index idempotency doc lap.

## 6. Rui ro con lai & viec chua lam

- Bo du lieu mau van stale theo SLA 24h nen freshness luon `FAIL`.
- Eval hien tai la keyword-based retrieval, chua cham full generation answer.
- Cac thanh vien con lai can tao file rieng trong `reports/individual/`.

## 7. Peer Review Q&A

1. Tai sao nhom khong chi do top-1 retrieval?
Vi top-1 co the van dung trong khi top-k da chua stale chunk. `q_refund_window` trong `inject-bad` la vi du ro nhat.

2. Quarantine mang lai gia tri gi so voi viec sua moi record?
Quarantine giu boundary giua record co the sua an toan va record khong nen publish, giup tranh dua chunk ngan, unknown source, hoac stale version vao embed.

3. Neu freshness fail nhung expectation pass, co nen embed khong?
Trong bai lab, nhom van embed de tao bang chung monitoring. Trong he thong that, day se la dieu kien canh bao hoac tam dung publish tuy SLA.
