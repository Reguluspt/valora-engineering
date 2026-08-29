# VALORA UI/UX Handoff v2.3 — TM04 Baseline Authority Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`

**Áp dụng từ:** sau khi người dùng chốt `TM04 — Preview / Test fill dữ liệu Word — Iteration 1` làm baseline.

Tài liệu này là addendum của `VALORA_UIUX_HANDOFF_v2.3.md` và **supersede mọi câu trong bản Handoff hiện tại còn ghi TM04 là `mockup chưa duyệt baseline`, `working iteration` hoặc nhiệm vụ thiết kế tiếp theo cần chốt**.

Authority chi tiết của TM04: [`assets/VALORA_TM04_BASELINE_v2.3.md`](./assets/VALORA_TM04_BASELINE_v2.3.md).

## A. Quyết định 0.4 được cập nhật

Module `Mẫu báo giá nhà cung cấp` là Word-only và hiện có ba visual baseline đã duyệt:

- `TM01 — Danh sách mẫu báo giá NCC — Iteration 1`;
- `TM03 — Upload & Mapping template — Iteration 1 Word-only`;
- **`TM04 — Preview / Test fill dữ liệu Word — Iteration 1`.**

TM03 Excel trước rule Word-only vẫn là lịch sử và không có authority.

## B. Screen Inventory — trạng thái TM04

| ID | Màn hình | Trạng thái / quyết định v2.3 |
|---|---|---|
| TM04 | Preview / Test fill dữ liệu | **P0 — baseline authority đã duyệt; Word-only Preview/Test fill; Iteration 1** |

## C. Baseline v2.3 bổ sung

**TM04 — Preview / Test fill dữ liệu Word — Iteration 1: baseline authority đã duyệt.**

Authority visual/interaction:

- Valora shell + Fluent 2, desktop-first;
- step rail 4 bước của setup template;
- chọn bộ dữ liệu test;
- vùng dữ liệu test với `Thông tin chung` / `Bảng danh mục`;
- preview Word đã fill ở vùng phải;
- zoom/page navigation/full-screen;
- validation placeholder, text dài/tràn ô, format tiền/ngày, bảng lặp, footer, ngắt trang;
- `Blocking` phải xử lý trước `Sẵn sàng sử dụng`;
- `Lưu và đặt sẵn sàng sử dụng` chỉ bằng thao tác explicit của người dùng;
- dữ liệu test không trở thành dữ liệu hồ sơ chính thức;
- không dùng semantics Excel trong TM04.

## D. Trạng thái module template sau baseline TM04

Chuỗi baseline đã đủ để xác định flow tạo template/output:

```text
TM01 Danh sách mẫu
→ TM03 Upload & Mapping Word
→ TM04 Preview / Test fill Word
→ Người dùng lưu và đặt Sẵn sàng sử dụng
→ Template có thể được dùng để tạo file báo giá NCC
```

TM02/TM05 tiếp tục giữ IA/capability đã mô tả; chưa tự suy diễn visual baseline riêng.

## E. Nhiệm vụ UI/UX tiếp theo

Sau khi TM04 được chốt baseline, **nhiệm vụ thiết kế tiếp theo chuyển sang `S17 — Hoàn tất hồ sơ`**.

S17 cần tổng hợp readiness/blocking/warning từ các bước trước, đặc biệt:

- tài sản/Đơn giá hiện hành;
- nguồn giá & chứng cứ;
- trạng thái báo giá NCC;
- coverage NCC đã xác nhận;
- file ký/đóng dấu và selection NCC/báo giá dùng trong hồ sơ;
- khả năng tạo file báo giá theo template Word đã sẵn sàng;
- thay đổi chưa lưu/commit và dependency bắt buộc khác.

Không tạo checkpoint Kiểm tra hồ sơ hoặc KSCL riêng; validation tiếp tục phân tán và S17 chỉ tổng hợp readiness để người dùng quyết định hoàn tất.
