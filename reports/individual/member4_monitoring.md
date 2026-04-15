# Bao Cao Ca Nhan - Lab Day 10

**Ho va ten:** ___________
**Vai tro:** Monitoring / Docs Owner
**Ngay nop:** `2026-04-15`

## 1. Toi phu trach phan nao?

Toi phu trach freshness monitoring, runbook, pipeline architecture, va tong hop bao cao nhom. Cac file toi can nhan ownership la `monitoring/freshness_check.py`, `docs/pipeline_architecture.md`, `docs/runbook.md`, `docs/quality_report.md`, `README.md`, va `reports/group_report.md`.

Muc tieu cua toi la bien artifact ky thuat thanh bang chung de nop bai: co so do pipeline, cach doc PASS/WARN/FAIL, va lien ket ro giua logs, manifests, eval CSV, va quality report.

## 2. Mot quyet dinh ky thuat

Quyet dinh ky thuat quan trong la theo doi freshness dua tren `latest_exported_at` trong manifest, khong chi dua tren `run_timestamp`. Neu chi nhin `run_timestamp`, pipeline co the trong co ve moi du du lieu nguon da cu. Cach do hien tai giup nhom phat hien bo du lieu mau van stale theo SLA 24h du pipeline da publish thanh cong.

## 3. Mot loi hoac anomaly da xu ly

Anomaly monitoring lon nhat la `freshness_check=FAIL` trong cac run `sprint2`, `normal`, va `inject-bad`. Day khong phai loi code ma la dau hieu du lieu mau co `latest_exported_at = 2026-04-10T08:00:00Z`, cu hon SLA 24h. Toi dua ket qua nay vao runbook de giai thich rang day la data staleness, khong phai pipeline broken.

## 4. Bang chung truoc / sau

Bang chung toi su dung la ket qua lenh:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py freshness --manifest artifacts/manifests/manifest_normal.json
```

Ket qua:

```text
FAIL {"latest_exported_at": "2026-04-10T08:00:00Z", "age_hours": 120.516, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```

Toi ket hop bang chung nay voi `normal.csv` va `inject-bad.csv` de giai thich: data quality co the tot len sau clean, nhung freshness van can theo doi doc lap.

## 5. Cai tien tiep theo

Neu co them 2 gio, toi se them mot boundary freshness o ingest stage va luu ca `raw_seen_at` de phan biet "du lieu nguon cu" va "pipeline chay cham".
