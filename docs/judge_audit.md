# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | ĐẠT (0.757 ≥ 0.6, 0.857 ≥ 0.8, 0.800 ≥ 0.7) | DÙNG |
| helpful | 100 | 0.375 | 1.000 | 0.300 | KHÔNG ĐẠT (κ=0.375 < 0.6, Recall=0.300 < 0.7) | LOẠI |

## ≥5 case audit thủ công

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & Hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 (`data/eval/judge_tone_public.csv`) | PASS | FAIL | Người đúng | Phản hồi *"Em đã hoàn tiền cho anh rồi nha, anh check giúp em"* quá suồng sã, xưng hô "Em - anh" và từ đệm "nha", "check" không phù hợp văn phong CSKH chuyên nghiệp. **Sửa rubric:** Bổ sung tiêu chí cấm xưng hô gia đình/thân mật ("anh", "em") và từ ngữ chat thông tục ("nha", "check"). |
| 2 | H-017 (`data/eval/judge_tone_public.csv`) | PASS | FAIL | Người đúng | Câu *"Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha"* dùng cách gọi "bạn ơi" và đuôi "rồi nha" thiếu tính trang trọng trong giao dịch tài chính. **Sửa rubric:** Định nghĩa rõ đại từ chuẩn mực ("LogiX - Quý khách" hoặc "anh/chị"), loại trừ lối gọi chào suồng sã. |
| 3 | H-029 (`data/eval/judge_tone_public.csv`) | PASS | FAIL | Người đúng | Lời nhắn *"Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm"* mang giọng điệu cộc cằn, gạt phắt khách hàng ("không cần nhắn thêm"). **Sửa rubric:** Thêm quy định cấm các câu phủ định mang tính xua đuổi, yêu cầu đổi thành câu hướng dẫn tích cực (*"LogiX sẽ chủ động thông báo ngay khi có kết quả"*). |
| 4 | H-042 (`data/eval/judge_tone_public.csv`) | FAIL | PASS | Người đúng | Câu trả lời *"Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ"* hoàn toàn lịch sự, nhã nhặn và có thông tin hữu ích. Judge báo FAIL nhầm (False Positive). **Sửa rubric:** Cung cấp few-shot ví dụ khẳng định câu thông báo ngắn gọn có dạ/ạ và nêu rõ mốc thời gian là đạt chuẩn, không phải cộc cằn. |
| 5 | H-051 (`data/eval/judge_tone_public.csv`) | FAIL | PASS | Người đúng | Câu *"Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ"* bị judge phạt vì dùng từ chêm tiếng Anh "refund". Tuy nhiên ngữ cảnh hoàn toàn tôn trọng khách. **Sửa rubric:** Nới lỏng tiêu chí ngôn ngữ, chấp nhận các thuật ngữ thương mại điện tử phổ biến như "refund/ship" khi thái độ chung vẫn lịch sự. |
| 6 | HL-016 (`data/eval/judge_helpful_public.csv`) | PASS | FAIL | Người đúng | Lời xin lỗi lặp lại nguyên xi 2 lần: *"LogiX thành thật xin lỗi... Một lần nữa LogiX xin lỗi..."*. Lời nói sáo rỗng (boilerplate apology) nhưng judge bị đánh lừa bởi độ dài và câu từ lịch sự nên chấm PASS. **Sửa rubric:** Bổ sung tiêu chí phạt các câu lặp cấu trúc xin lỗi vô nghĩa không kèm hành động thực tế. |
| 7 | HL-028 (`data/eval/judge_helpful_public.csv`) | PASS | FAIL | Người đúng | Đoạn phản hồi copy lặp lại 2 lần một câu xin lỗi y hệt nhau. Judge vẫn cho PASS. Điều này cho thấy judge `helpful` bị ảo giác bởi độ dài. **Sửa rubric:** Bắt buộc kiểm tra trùng lặp câu (deduplication) và đánh giá độ hữu ích dựa trên thông tin hành động (actionable info). |

## Kết luận
- **Tiêu chí bị loại và lý do:**
  - Tiêu chí `helpful` bị **loại bỏ hoàn toàn** khỏi cổng CI gate.
  - Ma trận nhầm lẫn của `helpful`: `{"tp": 9, "fp": 0, "fn": 21, "tn": 70}`.
  - Tỷ lệ bỏ sót lỗi nghiêm trọng: Có tới **21 ca False Negative** trên tổng số 30 ca lỗi (Recall chỉ đạt **30%**, cách rất xa ngưỡng sàn 70%).
  - Hệ số tương quan $\kappa = 0.375$ (thấp hơn nhiều so với ngưỡng tối thiểu 0.60), cho thấy judge đồng thuận với con người ở mức rất yếu, chủ yếu phán đoán thiên lệch về PASS do bị đánh lừa bởi các phản hồi xin lỗi dài dòng hoặc câu từ khách sáo mà không chứa giải pháp thực tế. Nếu dùng làm gate, các câu trả lời vô ích hoặc lặp lỗi sẽ lọt qua dễ dàng.
- **Tiêu chí được giữ lại:**
  - Tiêu chí `tone_ok` đạt chuẩn để sử dụng (κ = 0.757 ≥ 0.6, Precision = 0.857 ≥ 0.8, Recall = 0.800 ≥ 0.7). Tỷ lệ lỗi quan sát là 0.28, qua hiệu chỉnh Rogan-Gladen phản ánh đúng tỷ lệ lỗi thực tế 0.30.
- **Rủi ro còn lại:**
  - Judge chỉ mới được kiểm tra trên dữ liệu replay đã công khai (`judge_tone_public.csv`).
  - Cần liên tục thu thập nhãn từ người dùng thật (human-in-the-loop) để xây dựng tập held-out mới, tránh hiện tượng overfitting rubric vào tập dữ liệu thử nghiệm có sẵn.
