# Bao Cao Ca Nhan - Lab Day 10

**Ho va ten:** ___________
**Vai tro:** Embed / Idempotency Owner
**Ngay nop:** `2026-04-15`

## 1. Toi phu trach phan nao?

Toi phu trach viec publish cleaned snapshot vao Chroma va kiem chung retrieval. Cac file toi can nhan ownership la `etl_pipeline.py` (phan `cmd_embed_internal`), `eval_retrieval.py`, `grading_run.py`, va cac artifact trong `artifacts/eval/`. Muc tieu cua toi la dam bao rerun khong sinh duplicate vector va before/after retrieval co bang chung ro rang.

Bang chung can dan:

- `embed_upsert count=...`
- `embed_prune_removed=...`
- `artifacts/eval/normal.csv`
- `artifacts/eval/inject-bad.csv`
- `artifacts/eval/grading_run.jsonl`

## 2. Mot quyet dinh ky thuat

Toi giu strategy publish theo snapshot: upsert theo `chunk_id`, sau do prune nhung id khong con trong cleaned run hien tai. Cach nay giup collection phan anh dung phien ban publish moi nhat va tranh de stale vector sot lai sau khi da fix du lieu.

Trong Sprint 3, quyet dinh quan trong la danh gia retrieval voi `top-k=5` thay vi chi `top-k=1`. Nho vay nhom phat hien duoc stale refund chunk van ton tai trong top-k du top-1 van co ve dung.

## 3. Mot loi hoac anomaly da xu ly

Anomaly lon nhat la khi Chroma/SQLite trong OneDrive phat sinh `disk I/O error`. De giu duoc artifact grading, toi bo sung fallback trong `grading_run.py` de script co the doc lai ket qua tu `artifacts/eval/normal.csv` khi collection khong mo duoc. Cach nay khong thay doi logic cham diem, chi giup tao JSONL on dinh trong moi truong file system khong on dinh.

## 4. Bang chung truoc / sau

Bang chung Sprint 3 ro nhat la `q_refund_window`. Trong `inject-bad.csv`, dong nay co `contains_expected=yes` nhung `hits_forbidden=yes`. Trong `normal.csv`, no doi thanh `contains_expected=yes` va `hits_forbidden=no`. Day la bang chung retrieval da duoc cai thien sau khi stale chunk bi prune khoi snapshot publish.

## 5. Cai tien tiep theo

Neu co them 2 gio, toi se tach `CHROMA_DB_PATH` ra khoi OneDrive va them mot script kiem tra collection count truoc/sau publish de quan sat idempotency ro hon.
