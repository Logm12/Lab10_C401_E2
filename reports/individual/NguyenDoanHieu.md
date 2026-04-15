# Báo Cáo Cá Nhân - Member 3: Embed / Idempotency Owner

**Họ và tên:** Nguyễn Doãn Hiếu 
**Vai trò:** Embed / Idempotency Owner  
**Ngày nộp:** 2026-04-15

## 1. Tôi phụ trách phần nào?

Em phụ trách phần publish cleaned snapshot vào Chroma, đảm bảo index idempotent, và tạo các artifact đánh giá retrieval. Các file chính em phụ trách là `etl_pipeline.py` ở phần `cmd_embed_internal`, `eval_retrieval.py`, `grading_run.py`, và các file kết quả trong `artifacts/eval/`.

Vai trò của em là đảm bảo mỗi lần nhóm chạy lại pipeline thì vector store phản ánh đúng cleaned snapshot hiện tại, không bị giữ lại stale vector từ run cũ. Ngoài ra, em cũng chịu trách nhiệm tạo bằng chứng before/after retrieval, đặc biệt cho câu `q_refund_window` và `q_leave_version`, cũng như sinh file `grading_run.jsonl` để phục vụ rubric chấm điểm.

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của em là giữ chiến lược embed theo snapshot publish: `upsert` theo `chunk_id`, sau đó prune những `id` không còn nằm trong cleaned run hiện tại. Điều này quan trọng hơn nhiều so với chỉ `upsert`, vì nếu không prune thì stale chunk từ các run cũ vẫn có thể sống trong collection và làm hỏng top-k retrieval.

Sprint 3 cho thấy rõ giá trị của quyết định này. Trong run `inject-bad`, nhóm cố tình giữ lại stale refund chunk, và retrieval cho `q_refund_window` bị nhiễm stale evidence trong top-k. Sau khi chạy lại `normal`, collection được cập nhật lại theo snapshot sạch và stale chunk bị loại khỏi top-k. Điều đó chứng minh idempotency không chỉ là “không duplicate vector” mà còn là “index khớp với cleaned snapshot hiện tại”.

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly lớn nhất em xử lý là khi `grading_run.py` ban đầu phụ thuộc trực tiếp vào Chroma collection, nhưng môi trường OneDrive sinh ra `disk I/O error` khi mở SQLite của Chroma. Nếu không xử lý, nhóm sẽ không thể tạo `grading_run.jsonl` dù eval CSV đã có đầy đủ.

Để giữ workflow ổn định, em thêm cơ chế fallback trong `grading_run.py`: nếu Chroma không mở được, script sẽ đọc lại dữ liệu từ `artifacts/eval/normal.csv` để tạo JSONL theo đúng format grading. Đây là giải pháp thực dụng để không làm đứt chuỗi artifact nộp bài, đồng thời vẫn bám vào kết quả retrieval thật mà nhóm đã sinh ra trước đó.

## 4. Bằng chứng trước / sau

Bằng chứng quan trọng nhất nằm ở hai file:

- `artifacts/eval/inject-bad.csv`
- `artifacts/eval/normal.csv`

Với `q_refund_window`, file `inject-bad.csv` cho thấy `contains_expected=yes` nhưng `hits_forbidden=yes`, nghĩa là stale chunk refund 14 ngày vẫn xuất hiện trong top-k. Sau khi chạy lại pipeline sạch và publish snapshot mới, `normal.csv` cho thấy `contains_expected=yes` và `hits_forbidden=no`.

Ngoài ra, file `artifacts/eval/grading_run.jsonl` hiện đã đúng 3 dòng `gq_d10_01` đến `gq_d10_03`, trong đó:

- `gq_d10_01` pass với `hits_forbidden=false`
- `gq_d10_02` pass với `contains_expected=true`
- `gq_d10_03` pass với `top1_doc_matches=true`

## 5. Cải tiến tiếp theo

Nếu có thêm thời gian, em muốn tách `CHROMA_DB_PATH` ra khỏi OneDrive sang một thư mục local ổn định hơn và thêm một script nhỏ để đếm collection size trước/sau publish nhằm theo dõi idempotency rõ hơn.
