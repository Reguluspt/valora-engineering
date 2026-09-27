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

- Valora shell + Fluent 2 light, desktop-first;
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

## E. Historical next-task note / current routing disposition

At the time TM04 was approved, the next design task was labeled `S17 — Hoàn tất hồ sơ`. That sequencing note is **historical only**.

Current routing is governed by the newer Final Result authority:

```text
Hoàn tất từng báo giá NCC
→ Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
```

The approved S17 Iteration 3 baseline remains valid only as the child screen `Hoàn tất một báo giá NCC`. Do not create or revive a standalone whole-case `S17 — Hoàn tất hồ sơ` readiness dashboard/checkpoint between NCC Selection and Final Result. If a future whole-case completion action is needed for state/audit, it must preserve the locked routing and requires explicit newer authority.
