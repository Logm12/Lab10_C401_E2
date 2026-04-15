# Báo Cáo Cá Nhân - Member 2: Cleaning / Quality Owner

**Họ và tên:** Bùi Hữu Huấn   

**Vai trò:** Cleaning / Quality Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Tôi phụ trách phần làm sạch dữ liệu và kiểm soát chất lượng trước khi publish vào Chroma. Các file chính tôi chịu trách nhiệm là `transform/cleaning_rules.py`, `quality/expectations.py`, và một phần `docs/quality_report.md`. Mục tiêu của tôi là đảm bảo raw export sau khi đi qua pipeline sẽ không còn duplicate không kiểm soát, không còn stale refund window 14 ngày, không còn stale HR version 10 ngày phép năm, đồng thời các record lỗi sẽ được chuyển vào quarantine thay vì đi thẳng vào vector store.

Trong Sprint 2, tôi bổ sung các rule có tác động đo được như chuẩn hóa `exported_at`, chuẩn hóa contact token, chuẩn hóa currency `VND`, unescape HTML entity, compact whitespace, và fix HR leave version. Tôi cũng thêm expectation mới để kiểm tra `exported_at_iso_utc` và `unique_doc_id_chunk_text`, đồng thời tách validation quarantine ra khỏi clean quarantine để pipeline chuẩn vẫn có thể `exit 0`.

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là tách rõ hai lớp kiểm soát lỗi: `clean quarantine` và `validation quarantine`. Những lỗi có thể xác định ngay ở đầu vào như `unknown_doc_id`, `missing_effective_date`, hoặc stale HR effective date sẽ bị loại ngay ở stage clean. Ngược lại, những lỗi cần đánh giá trên dữ liệu đã được normalize như chunk quá ngắn, stale refund còn sót sau clean, hay duplicate ở mức `doc_id + chunk_text` sẽ được kiểm tra ở stage validate.

Cách tổ chức này có hai lợi ích. Thứ nhất, pipeline chuẩn không bị dừng vì một vài row không đáng để halt toàn bộ batch; thay vào đó, row lỗi được đẩy sang quarantine. Thứ hai, cleaned snapshot dùng để embed sẽ phản ánh đúng dữ liệu có thể publish, còn expectation aggregate vẫn giữ vai trò chặn các failure mode quan trọng. Ví dụ, expectation `refund_no_stale_14d_window` được giữ ở mức `halt` vì stale refund ảnh hưởng trực tiếp đến retrieval quality.

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly rõ nhất tôi xử lý là stale refund chunk. Trong run `inject-bad`, pipeline được chạy với `--no-refund-fix --skip-validate`, nên expectation `refund_no_stale_14d_window` fail với `violations=1`. Điều đáng chú ý là nếu chỉ nhìn top-1 retrieval thì người dùng vẫn có thể tưởng hệ thống trả lời đúng, nhưng khi quét toàn bộ top-k, stale chunk “14 ngày làm việc” vẫn xuất hiện.

Tôi dùng hai lớp bằng chứng để chứng minh lỗi này. Lớp thứ nhất là log trong `artifacts/logs/run_inject-bad.log`, cho thấy expectation fail thật. Lớp thứ hai là `artifacts/eval/inject-bad.csv`, nơi câu `q_refund_window` có `contains_expected=yes` nhưng `hits_forbidden=yes`. Sau khi bật lại clean rule fix refund ở run `normal`, stale chunk biến mất khỏi top-k và `hits_forbidden` quay về `no`.

## 4. Bằng chứng trước / sau

Bằng chứng rõ nhất nằm ở hai file eval:

- `artifacts/eval/inject-bad.csv`: `q_refund_window` có `contains_expected=yes`, `hits_forbidden=yes`
- `artifacts/eval/normal.csv`: `q_refund_window` có `contains_expected=yes`, `hits_forbidden=no`

Ngoài ra, Sprint 2 cũng cho thấy tác động định lượng của các rule tôi thêm:

- `rule_normalize_exported_at=14`
- `rule_fix_hr_leave_version=1`
- `rule_normalize_contact_tokens=1`
- `rule_normalize_currency_vnd=1`
- `validation_chunk_too_short=1`

Các số này đã được ghi lại trong `artifacts/logs/run_sprint2.log` và tổng hợp lại trong `reports/group_report.md`.

## 5. Cải tiến tiếp theo

Nếu có thêm thời gian, tôi muốn bổ sung một lớp schema validation chặt hơn bằng pydantic hoặc Great Expectations để tách biệt rõ lỗi schema, lỗi semantic, và lỗi retrieval-quality. Điều này sẽ giúp quarantine reason chi tiết hơn và report tự động hơn.
