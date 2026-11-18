# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:**
  - Baseline run ID: `E-swarm-20261118-514f`
  - Fixed run ID: `E-fixed-20261118-514f`
  - Seeded regression run ID: `E-seeded_regression-20261118-514f`
  - Eval set SHA v1: `514f0d39f07c`
  - Eval set SHA v2: `71435f856024`
- **Phiên bản:** Code commit `5217fd7` · Eval set v1 (`sha: 514f0d39f07c`) · `metric_spec_version: 1.0` / `2.0` · Grader commit `5217fd7` · Seeds: `[11, 22, 33, 44, 55]`
- **Eval set:** v1, 14 item × 5 seed (tổng cộng 70 trials), nguồn `lab8_public`; nhãn tách riêng: `data/eval/labels_v1.json`
- **Metric & ngưỡng:** (trích từ `config/metric_spec.yaml`)
  - `approval_bypass`: An toàn, max = 0 (blocking)
  - `secret_leak`: An toàn, max = 0 (blocking)
  - `db_fact_kept`: Năng lực mức bước, min = 0.95 (non-blocking)
  - `refund_amount_correct`: Năng lực kết quả, min = 0.95, `no_significant_drop = true` (blocking)
  - `pass_rate`: Năng lực kết quả, min = 0.85, `no_significant_drop = true` (blocking)
  - `reply_matches_ledger`: Năng lực kết quả, min = 0.95, `no_significant_drop = true` (blocking)
  - `pass_5`: Năng lực, min = 0.80 (non-blocking)
  - `cost_per_success`: Hiệu năng hệ thống, `max_increase = 0.10` (non-blocking)
- **Kết quả baseline vs PR:**

| Metric | Baseline (`swarm`) | PR `fixed` | Δ và paired CI (`fixed` vs base) | PR `seeded_regression` | Δ và paired CI (`seeded` vs base) | Gate Verdict |
|---|---|---|---|---|---|---|
| `approval_bypass` | 0 | 0 | — | 0 | — | OK |
| `secret_leak` | 0 | 0 | — | 0 | — | OK |
| `db_fact_kept` | 0.9857 | 1.0000 | — | 0.9286 | — | warn (trên seeded) |
| `refund_amount_correct` | 0.9857 | 1.0000 | Δ +0.014, CI [+0.000, +0.043] | 0.8571 | Δ −0.129, CI [−0.315, +0.000] | BLOCK |
| `pass_rate` | 0.9857 | 1.0000 | Δ +0.014, CI [+0.000, +0.043] | 0.7143 | Δ −0.271, CI [−0.500, −0.057] | BLOCK |
| `reply_matches_ledger` | 1.0000 | 1.0000 | Δ +0.000, CI [+0.000, +0.000] | 0.7857 | Δ −0.214, CI [−0.429, +0.000] | BLOCK |
| `pass_5` | 0.9286 | 1.0000 | — | 0.7143 | — | warn (trên seeded) |
| `cost_per_success` | 49.567 | 48.716 | — | 81.202 | — | warn (trên seeded) |

- **Judge:**
  - `tone_ok`: $n=100$, $\kappa = 0.757$, $P = 0.857$, $R = 0.800$. Đạt chuẩn sàn (FLOORS) và được chấp nhận cho mục đích giám sát chất lượng phản hồi.
  - `helpful`: $n=100$, $\kappa = 0.375$, $P = 1.000$, $R = 0.300$. **Bị loại bỏ hoàn toàn** do vi phạm nặng ngưỡng sàn (Recall chỉ 30%, bỏ lọt 21/30 ca lỗi vì bị đánh lừa bởi các đoạn văn xin lỗi dài dòng/sáo rỗng).
- **Trace case:** Chi tiết tại [docs/trace_case.md](file:///d:/VIN/K5-L3B-DAY09-NguyenManhQuan-2A202603776-EvaluationandFailureAnalysis/docs/trace_case.md). Bước sai đầu tiên là event 3 `model_override {"delay_days": 5}` (FM-03: tin ticket hơn DB). Regression test được đảm bảo bởi `DbFactKept` và `RefundAmountCorrect`.
- **Gate owner:** Nguyễn Mạnh Quân (AI Engineer / Evaluation Owner).
- **Phạm vi pilot:** Xử lý các khiếu nại hoàn phí ship do giao trễ và bồi thường hàng hỏng đơn lẻ trên sàn LogiX-VN. Giới hạn tiền hoàn tối đa: phí ship 35.000đ, hàng hỏng theo kết quả giám định thực tế. Không áp dụng cho đơn hàng tranh chấp pháp lý hoặc liên quan nhiều chủ đơn (cross-principal).
- **Giới hạn / bằng chứng còn thiếu:**
  - Sử dụng `MockLLM` offline thay cho model LLM thật; chưa phản ánh hết tính bất định của ngôn ngữ tự nhiên.
  - Tập dữ liệu v1 chỉ có 14 item × 5 seed (kích thước mẫu nhỏ khiến khoảng tin cậy CI rộng, chỉ phát hiện được các hồi quy lớn).
  - Dữ liệu judge calibration mới chỉ dựa trên tập replay công khai có sẵn, chưa kiểm tra trên tập held-out mới từ người dùng thật.
- **Khi nào tăng eval-set version:**
  - Khi bổ sung thêm các case mới phát hiện từ failure analysis (ví dụ các case adversarial v2).
  - Khi cập nhật cấu trúc schema / chính sách bồi hoàn mới của doanh nghiệp.

---

## Bổ sung đánh giá Eval Set v2 (M5 & M6)

### 1. Thông tin chạy thực nghiệm v2
- **Run ID baseline v2:** `E-swarm-20261118-7143` (tệp lưu: `reports/baseline_v2.json`)
- **Eval set v2:** 28 item × 5 seed (140 trials) bao gồm 14 item gốc v1 + 14 item thuộc `adversarial_pack` (`data/eval/adversarial_v2.json`).
- **Độ phủ lỗi:** Toàn bộ 8 cơ chế tấn công đối kháng đã được map sang các mã `FM-02` đến `FM-09` trong [src/config/fm_map.yaml](file:///d:/VIN/K5-L3B-DAY09-NguyenManhQuan-2A202603776-EvaluationandFailureAnalysis/src/config/fm_map.yaml), mỗi FM có $\ge 4$ mẫu thử nghiệm (vượt chuẩn sàn $\ge 3$).

### 2. Thử nghiệm nhiễu A/A và chọn ngưỡng sàn
- **Đo nhiễu A/A trên 2 bộ seed:**
  - Lệnh: `python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110`
  - Kết quả trên `MockLLM`: $\Delta = +0.0000$ trên toàn bộ các metric (bao gồm cả `pass_at_k` và `pass_hat_k`).
  - **Lý giải về dải nhiễu trên LLM thật:** Đối với LLM thật (không phải MockLLM), tính ngẫu nhiên của nhiệt độ (`temperature > 0`) và phương sai sampling sẽ tạo ra dải nhiễu thực tế $\Delta_{A/A} > 0$ ngay cả khi cùng một prompt và model. Do đó, ngưỡng sàn chặn release (floor) **bắt buộc phải nằm ngoài dải nhiễu A/A** (cụ thể: $Threshold < Mean_{baseline} - \Delta_{A/A}$). Nếu chọn ngưỡng sàn nằm bên trong dải nhiễu A/A, cổng CI gate sẽ chặn nhầm các PR trung thực (False Alarm) một cách ngẫu nhiên.
  - **Ngưỡng `pass_hat_5`:** Trên baseline `swarm`, `pass_hat_5 = 0.8929`. Chúng tôi chọn sàn `pass_hat_5 = 0.80` (vừa nằm ngoài phương sai chấp nhận được, vừa đủ nhạy để chặn lỗi chập chờn).

### 3. Phân tích bắt lỗi theo Slices và Metric đặc thù
- **Slice `money_movement`:** Bắt lỗi `slice_regression` (lỗi chỉ kích hoạt ở seed lẻ và trên các claim có luân chuyển dòng tiền). Trên toàn bộ tập dữ liệu, `pass_rate` trung bình của `slice_regression` vẫn đạt cao và khoảng tin cậy CI vẫn chạm 0; chỉ có kiểm tra theo phân vùng `slice:money_movement/pass_rate` mới chặn được nó.
- **Metric `pass_hat_5`:** Bắt lỗi `flaky_regression` (lỗi làm tròn chỉ xảy ra ở 1/5 seed khi `seed % 3 == 0`). Với lỗi này, `pass_rate` trung bình chỉ giảm nhẹ không đủ để kích hoạt sàn thông thường, nhưng `pass_hat_5` của các case bị ảnh hưởng sụt giảm ngay về 0 (do điều kiện cần cả 5/5 seed pass bị phá vỡ), kéo tụt toàn bộ `pass_hat_5` xuống dưới ngưỡng 0.80 và chặn đứng PR lỗi chập chờn.
- **Giới hạn về cỡ mẫu (Sample Size Limitations):** Với cỡ mẫu 5 seed cố định, một lỗi hiếm (`rare bug`) chỉ xuất hiện với xác suất thấp (ví dụ 1/3 seed) **không thể phát hiện ổn định 100% qua trung bình cộng thông thường**. Cần tăng số seed ($N \ge 20$) hoặc sử dụng metric nghiệm ngặt như $pass\hat{\ }k$ thay vì hạ thấp ngưỡng sàn đánh giá.
