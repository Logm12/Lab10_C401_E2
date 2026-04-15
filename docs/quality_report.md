# Báo cáo chất lượng - Lab Day 10

**run_id:** `normal`, `inject-bad`
**Ngày:** `2026-04-15`

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (`inject-bad`) | Sau (`normal`) | Ghi chú |
|--------|----------------------|----------------|---------|
| raw_records | 16 | 16 | Cùng một bộ raw mở rộng để so sánh công bằng |
| cleaned_records | 11 | 10 | `inject-bad` bỏ qua kiểm định (validate) nên giữ lại thêm 1 hàng ngắn và các đoạn hoàn tiền cũ |
| quarantine_records | 5 | 6 | `normal` có thêm `validation_chunk_too_short=1` |
| Expectation halt? | Có | Không | `inject-bad` thất bại `refund_no_stale_14d_window`; `normal` vượt qua toàn bộ |

---

## 2. Truy xuất trước / sau (Before / after retrieval)

Chúng tôi đánh giá việc truy xuất bằng `eval_retrieval.py` với `top-k=5` trên cùng bộ câu hỏi chuẩn (golden questions). Hai file bằng chứng là `artifacts/eval/normal.csv` và `artifacts/eval/inject-bad.csv`.

**Câu hỏi then chốt:** `q_refund_window`

- Trước (`inject-bad`): `contains_expected=yes` nhưng `hits_forbidden=yes`. Điều này cho thấy top-k vẫn chứa các đoạn cũ "14 ngày làm việc", nên nếu chỉ nhìn top-1 sẽ tưởng truy xuất ổn nhưng thực tế ngữ cảnh đã bị nhiễm.
- Sau (`normal`): `contains_expected=yes` và `hits_forbidden=no`. Sau khi bật lại quy tắc sửa refund 14->7 và kiểm định đầy đủ, các đoạn cũ biến mất khỏi top-k.

**Đánh giá:** `q_leave_version`

- Trước (`inject-bad`): `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.
- Sau (`normal`): `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.

Điều này cho thấy quy tắc sửa phiên bản HR của Sprint 2 đã ổn định ở cả hai kịch bản; lỗi đưa vào (corruption) có chủ đích ở Sprint 3 tập trung vào thời hạn hoàn tiền và bộ kiểm định.

**Câu thứ ba để đối chiếu:** `q_p1_sla`

- Trước (`inject-bad`): `contains_expected=yes`, `hits_forbidden=no`.
- Sau (`normal`): `contains_expected=yes`, `hits_forbidden=no`.

Nhận xét tổng hợp: truy xuất không xấu đi ở mọi câu hỏi, nhưng chất lượng quan sát đã xấu đi rõ rệt ở `q_refund_window`. Đây là bằng chứng quan trọng vì top-1 vẫn đúng, nhưng top-k đã bị nhiễm các bằng chứng cũ (stale evidence). Theo tinh thần Day 10, đó là một sự thụt lùi (regression) thực sự ở lớp dữ liệu.

---

## 3. Độ tươi & giám sát (Freshness & monitor)

Cả hai lần chạy đều cho kết quả `freshness_check=FAIL` vì `latest_exported_at = 2026-04-10T08:00:00Z`, cũ hơn SLA 24h. Đây là cảnh báo độ tươi của bộ dữ liệu mẫu, không phải lỗi logic của pipeline. Manifest vẫn hữu ích để chỉ ra rằng dữ liệu đã xuất bản thành công nhưng không còn mới.

---

## 4. Đưa lỗi vào (Corruption inject - Sprint 3)

Kịch bản đưa lỗi vào được chạy bằng:

```powershell
python etl_pipeline.py run --run-id inject-bad --raw data/raw/policy_export_dirty_extended.csv --no-refund-fix --skip-validate
```

Hai thay đổi có chủ đích:

- Tắt việc sửa `refund` để văn bản cũ `14 ngay lam viec` được giữ lại trong bản xuất đã làm sạch (cleaned publish).
- Bỏ qua việc dừng kiểm định (validation halt) để các bản ghi lỗi vẫn được đưa vào Chroma.

Bằng chứng:

- `artifacts/logs/run_inject-bad.log`: `refund_no_stale_14d_window FAIL (halt) :: violations=1`
- `artifacts/cleaned/cleaned_inject-bad.csv`: còn đoạn refund cũ `14 ngay lam viec`
- `artifacts/eval/inject-bad.csv`: `q_refund_window` có `hits_forbidden=yes`

---

## 5. Hạn chế & việc chưa làm

- Việc đánh giá hiện tại là truy xuất dựa trên từ khóa (keyword-based), chưa chấm điểm tạo câu trả lời đầy đủ (full answer generation).
- Độ tươi của bộ dữ liệu mẫu vẫn thất bại theo SLA 24h.
- Cần bổ sung thêm phần diễn giải trong `runbook.md` và tổng hợp vào `reports/group_report.md`.
