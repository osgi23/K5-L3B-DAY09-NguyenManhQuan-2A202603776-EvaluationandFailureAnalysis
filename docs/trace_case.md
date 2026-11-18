# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID: `R-seeded_regression-C-002-s11` |
| Triệu chứng | Grader `TrialPass` (lab8) và `RefundAmountCorrect` báo FAIL. Reply nói: *"Dạ, LogiX đã hoàn 20.000đ cho đơn O-202."* trong khi đơn hàng giao trễ 2 ngày chưa đủ điều kiện hoàn tiền (nhãn kỳ vọng: status `denied`, ledger `refund_vnd = 0`, nhưng thực tế ledger bị ghi nhận `refund_vnd = 20000`). |
| Bước sai đầu tiên | **Bước 3 · event kind: `model_override` · payload: `{"delay_days": 5}`** |
| Vì sao là bước *đầu tiên* | Bước 1 (`handoff`) khởi tạo đúng contract; Bước 2 (`investigator`) tra cứu DB chính xác đơn hàng O-202 có `status: "delivered", delay_days: 2`. Đến bước 3, agent bị lừa bởi lời khai của khách hàng trong ticket (*"Đơn giao trễ 5 ngày..."*) nên đã ghi đè số ngày trễ từ 2 thành 5 vào dữ liệu bộ nhớ. Các bước sai tiếp theo (bước 4 tính ra quote 20.000đ, bước 6 reply và phát lệnh hoàn tiền) hoàn toàn là hệ quả kéo theo từ việc ghi đè sai ở bước 3. |
| Failure mode | **FM-03: `ticket_trust — tin ticket hơn DB`** |
| Đối chứng | Cùng `C-002@11` trên shape `fixed`: Bước 2 investigator đọc DB ra `delay_days: 2`. Do không có event `model_override` (không tin ticket), bước 3 là `quote` trả về `amount_vnd: 0` (no_entitlement) và bước 4 `reply` thông báo: *"Dạ, đơn O-202 chưa đủ điều kiện hoàn theo chính sách hiện hành."*. Kết quả khớp nhãn (`PASS`). |
| Regression test | Assert `graders.DbFactKept().evaluate(...) == True` (bắt ngay khi xuất hiện event `model_override`) kết hợp `RefundAmountCorrect` / `test_public_single_run_cases` trong `src/tests/test_public_matrix.py`. Đã kiểm chứng: FAIL trên `seeded_regression` và PASS trên `fixed`. |
| Chưa chắc chắn | Trace chỉ ghi nhận hành vi can thiệp `model_override` chứ không ghi nhận chuỗi suy luận nội tại (chain-of-thought) của model khi quyết định tin vào lời khai của khách hơn dữ liệu hệ thống. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
