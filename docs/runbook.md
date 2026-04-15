# Runbook - Lab Day 10

## Symptom

Trieu chung thuong gap:

- Agent tra loi "14 ngay lam viec" thay vi 7 ngay cho refund policy
- Retrieval top-1 dung nhung top-k van chua stale chunk
- Pipeline `run` dung vi expectation `halt`
- Freshness check bao `FAIL`

## Detection

Kiem tra theo thu tu:

- `artifacts/logs/run_<run_id>.log`
- `artifacts/manifests/manifest_<run_id>.json`
- `artifacts/quarantine/quarantine_<run_id>.csv`
- `artifacts/eval/*.csv`

Freshness convention:

- `PASS`: `latest_exported_at` nam trong SLA 24h
- `WARN`: manifest thieu timestamp hoac timestamp khong parse duoc
- `FAIL`: timestamp hop le nhung da vuot SLA

Ket qua thuc te:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py freshness --manifest artifacts/manifests/manifest_normal.json
```

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.516, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

## Diagnosis

| Buoc | Viec lam | Ket qua mong doi |
|------|----------|------------------|
| 1 | Mo manifest cua run hien tai | Thay `run_id`, counts, `latest_exported_at`, `clean_metrics`, `validation_metrics` |
| 2 | Mo quarantine CSV | Biet record loi nam o stage `clean` hay `validate` |
| 3 | Mo cleaned CSV | Kiem tra stale chunk da bi fix/prune chua |
| 4 | Doc run log | Thay expectation fail va metric impact |
| 5 | Chay eval voi `top-k 5` | Kiem tra `hits_forbidden` tren toan bo top-k |

## Mitigation

Normal rerun:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id normal --raw data/raw/policy_export_dirty_extended.csv
.\.venv\Scripts\python.exe eval_retrieval.py --out artifacts/eval/normal.csv --top-k 5
```

Inject corruption de tai hien loi:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id inject-bad --raw data/raw/policy_export_dirty_extended.csv --no-refund-fix --skip-validate
.\.venv\Scripts\python.exe eval_retrieval.py --out artifacts/eval/inject-bad.csv --top-k 5
```

Neu freshness fail nhung expectation pass:

- Khong can rollback code
- Ghi ro du lieu dang stale trong report
- Xin batch export moi hoac cap nhat source

## Prevention

- Giu `refund_no_stale_14d_window` la expectation `halt`
- Giu `unique_doc_id_chunk_text` va `exported_at_iso_utc` la expectation `halt`
- Luon danh gia retrieval voi `top-k >= 5` cho cau hoi versioning
- Ghi `run_id` vao manifest/log de audit
- Khi may khong co mang, bat che do offline cho HF cache

## Peer Review Q&A

1. Tai sao nhom khong chi do top-1 retrieval?
Vi top-1 co the van "dung" trong khi top-k da chua stale chunk. `q_refund_window` trong `inject-bad` la vi du ro nhat.

2. Tai sao can quarantine thay vi sua tat ca record?
Chi sua nhung loi co the sua an toan nhu date/currency/contact. Record mo ho hoac khong du gia tri retrieval can bi tach rieng de tranh embed rac.

3. Neu freshness fail nhung expectation pass, co nen publish khong?
Trong bai lab nhom van publish de co bang chung monitoring. Trong he thong that, day se la dieu kien canh bao hoac tam dung publish tuy SLA.
