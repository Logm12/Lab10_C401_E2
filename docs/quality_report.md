# Quality report - Lab Day 10

**run_id:** `normal`, `inject-bad`
**Ngay:** `2026-04-15`

---

## 1. Tom tat so lieu

| Chi so | Truoc (`inject-bad`) | Sau (`normal`) | Ghi chu |
|--------|----------------------|----------------|---------|
| raw_records | 16 | 16 | Cung mot bo raw mo rong de so sanh cong bang |
| cleaned_records | 11 | 10 | `inject-bad` bo qua validate nen giu lai them 1 row ngan va stale refund chunk |
| quarantine_records | 5 | 6 | `normal` co them `validation_chunk_too_short=1` |
| Expectation halt? | Co | Khong | `inject-bad` fail `refund_no_stale_14d_window`; `normal` pass toan bo |

---

## 2. Before / after retrieval

Chung toi danh gia retrieval bang `eval_retrieval.py` voi `top-k=5` tren cung bo cau hoi golden. Hai file chung cu la `artifacts/eval/normal.csv` va `artifacts/eval/inject-bad.csv`.

**Cau hoi then chot:** `q_refund_window`

- Truoc (`inject-bad`): `contains_expected=yes` nhung `hits_forbidden=yes`. Dieu nay cho thay top-k van chua stale chunk "14 ngay lam viec", nen neu chi nhin top-1 se tuong retrieval on nhung thuc te context da bi nhiem.
- Sau (`normal`): `contains_expected=yes` va `hits_forbidden=no`. Sau khi bat lai rule fix refund 14->7 va validation day du, stale chunk bien mat khoi top-k.

**Merit:** `q_leave_version`

- Truoc (`inject-bad`): `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.
- Sau (`normal`): `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.

Dieu nay cho thay rule fix HR version cua Sprint 2 da on dinh o ca hai kich ban; corruption chu dich o Sprint 3 tap trung vao refund window va bo validate.

**Cau thu ba de doi chieu:** `q_p1_sla`

- Truoc (`inject-bad`): `contains_expected=yes`, `hits_forbidden=no`.
- Sau (`normal`): `contains_expected=yes`, `hits_forbidden=no`.

Nhan xet tong hop: retrieval khong xau di o moi cau hoi, nhung chat luong quan sat da xau di ro o `q_refund_window`. Day la bang chung quan trong vi top-1 van dung, nhung top-k da bi nhiem stale evidence. Theo tinh than Day 10, do la mot regression that su o data layer.

---

## 3. Freshness & monitor

Ca hai run deu cho `freshness_check=FAIL` vi `latest_exported_at = 2026-04-10T08:00:00Z`, cu hon SLA 24h. Day la canh bao freshness cua bo du lieu mau, khong phai loi logic pipeline. Manifest van huu ich de chi ra rang du lieu da publish thanh cong nhung khong con moi.

---

## 4. Corruption inject (Sprint 3)

Kich ban inject duoc chay bang:

```powershell
python etl_pipeline.py run --run-id inject-bad --raw data/raw/policy_export_dirty_extended.csv --no-refund-fix --skip-validate
```

Hai thay doi co chu dich:

- Tat `refund` fix de stale text `14 ngay lam viec` duoc giu lai trong cleaned publish.
- Bo qua validation halt de record loi van duoc embed vao Chroma.

Bang chung:

- `artifacts/logs/run_inject-bad.log`: `refund_no_stale_14d_window FAIL (halt) :: violations=1`
- `artifacts/cleaned/cleaned_inject-bad.csv`: con chunk refund stale `14 ngay lam viec`
- `artifacts/eval/inject-bad.csv`: `q_refund_window` co `hits_forbidden=yes`

---

## 5. Han che & viec chua lam

- Eval hien tai la retrieval keyword-based, chua cham full answer generation.
- Freshness cua bo du lieu mau van fail theo SLA 24h.
- Can bo sung them phan dien giai trong `runbook.md` va tong hop vao `reports/group_report.md`.
