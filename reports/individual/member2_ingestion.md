# Bao Cao Ca Nhan - Lab Day 10

**Ho va ten:** ___________
**Vai tro:** Ingestion / Raw Owner
**Ngay nop:** `2026-04-15`

## 1. Toi phu trach phan nao?

Toi phu trach raw source va luong ingest dau vao. Cac file can nhan ownership la `etl_pipeline.py`, `data/raw/policy_export_dirty.csv`, `data/raw/policy_export_dirty_extended.csv`, `contracts/data_contract.yaml`, va phan source map trong `docs/data_contract.md`. Muc tieu cua toi la dam bao pipeline doc dung raw file, ghi `run_id`, `raw_records`, va tao manifest/log on dinh cho moi lan chay.

Bang chung can dan:

- `artifacts/logs/run_sprint1.log`
- `artifacts/manifests/manifest_sprint1.json`
- `artifacts/manifests/manifest_sprint2.json`

## 2. Mot quyet dinh ky thuat

Toi chon giu `run_id` la tham so truyen tu CLI thay vi hard-code trong code. Cach nay giup moi thanh vien co the chay cac kich ban `sprint1`, `sprint2`, `normal`, `inject-bad` ma van doi chieu duoc log, manifest, cleaned CSV, va quarantine CSV theo cung mot ten run.

Ngoai ra, manifest duoc ghi sau khi pipeline publish thanh cong de gom du `raw_records`, `cleaned_records`, `quarantine_records`, `latest_exported_at`, va `clean_metrics`.

## 3. Mot loi hoac anomaly da xu ly

Mot anomaly de gap la raw path bi truyen dang tuong doi, khien manifest co the fail khi co gang `relative_to(ROOT)`. Cach fix la chuyen `raw_path` sang `.resolve()` va dung helper hien thi path an toan trong `etl_pipeline.py`. Sau fix, run voi `--raw data/raw/policy_export_dirty_extended.csv` ghi manifest binh thuong.

## 4. Bang chung truoc / sau

Truoc khi dung bo raw mo rong, `sprint1` co `raw_records=10`. Sau khi them file `policy_export_dirty_extended.csv`, `sprint2` va `normal` co `raw_records=16`. Dieu nay tao khong gian de do tac dong cua cleaning rule va expectation moi.

## 5. Cai tien tiep theo

Neu co them 2 gio, toi se them metadata source-level vao manifest, vi du checksum cua raw CSV va source_version, de viec audit ingest ro rang hon.
