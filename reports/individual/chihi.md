# Bao Cao Ca Nhan - Lab Day 10

**Ho va ten:** Chihi
**Vai tro:** Cleaning / Quality + Monitoring / Docs
**Ngay nop:** `2026-04-15`

## 1. Toi phu trach phan nao?

Toi phu trach mo rong cleaning rules, expectation suite, va tong hop bang chung monitoring/doc cho bai lab. Cac file chinh toi lam la `transform/cleaning_rules.py`, `quality/expectations.py`, `docs/quality_report.md`, `docs/runbook.md`, va `reports/group_report.md`. Toi phoi hop voi phan embed de dam bao output sau clean van phu hop voi Chroma idempotency, va phoi hop voi phan ingestion de metric trong manifest/log co the dung lai cho report nhom.

## 2. Mot quyet dinh ky thuat

Quyet dinh quan trong nhat cua toi la tach `validation quarantine` khoi `clean quarantine`. Cac loi co the sua an toan nhu normalize date/currency/contact se duoc xu ly som; con cac record khong nen publish nhu chunk ngan hoac stale refund con sot lai se duoc tach rieng truoc embed. Cach lam nay giup pipeline normal van `exit 0` ma khong de rac di vao vector store.

## 3. Mot loi hoac anomaly da xu ly

Anomaly quan trong nhat toi xu ly la stale refund chunk. Trieu chung la trong run `inject-bad`, expectation `refund_no_stale_14d_window` fail voi `violations=1`. Top-1 retrieval van co the nhin dung, nhung top-k van chua stale chunk 14 ngay va lam `hits_forbidden=yes` cho cau `q_refund_window`. Fix la bat lai rule refund trong normal run va publish lai collection.

## 4. Bang chung truoc / sau

Voi `run_id=inject-bad`, dong `q_refund_window` trong `artifacts/eval/inject-bad.csv` cho thay `contains_expected=yes` nhung `hits_forbidden=yes`. Voi `run_id=normal`, cung cau hoi do trong `artifacts/eval/normal.csv` cho thay `contains_expected=yes` va `hits_forbidden=no`. Dieu nay chung minh pipeline cai thien retrieval o muc context, khong chi top-1.

## 5. Cai tien tiep theo

Neu co them 2 gio, toi se them mot script tong hop eval co cot `scenario` va thong ke tong so cau hoi `hits_forbidden=yes` / `contains_expected=no` cho tung run de bao cao tu dong hon.
