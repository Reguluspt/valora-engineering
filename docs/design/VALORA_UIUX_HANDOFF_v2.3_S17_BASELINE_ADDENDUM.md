# VALORA UI/UX Handoff v2.3 — Addendum Baseline Hoàn tất một báo giá NCC

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`

**Áp dụng từ:** sau khi người dùng chốt `S17 — Iteration 3` làm baseline.

Authority chi tiết: [`assets/VALORA_S17_BASELINE_v2.3.md`](./assets/VALORA_S17_BASELINE_v2.3.md).

## A. Quyết định scope mới nhất

Người dùng đã làm rõ rằng flow đang thiết kế tại Iteration 3 là **xử lý/hoàn tất một báo giá cụ thể của một nhà cung cấp**, không phải readiness/hoàn tất toàn bộ hồ sơ thẩm định.

Vì vậy:

- Iteration 3 được nâng thành baseline authority cho **child screen của NCCQ — Hoàn tất báo giá nhà cung cấp**;
- các Iteration 1–2 bị superseded;
- badge `S17` trong mockup được xem là nhãn iteration lịch sử, không được dùng để suy diễn rằng màn hình này thay thế `S17 — Hoàn tất hồ sơ` cấp toàn hồ sơ;
- `S17 — Hoàn tất hồ sơ` cấp hồ sơ vẫn là một scope riêng cần thiết kế/khóa sau, nếu product workflow vẫn giữ checkpoint đó.

## B. Lifecycle báo giá hiện tại

```text
Tạo báo giá nháp
→ Tạo file theo mẫu NCC
→ Gửi NCC xác nhận
→ Nhận phản hồi / file ký
→ Hoàn tất báo giá
```

Readiness chỉ áp dụng cho báo giá/NCC hiện tại.

## C. Những nội dung được phép xuất hiện trong baseline

- Nhà cung cấp hiện tại;
- danh mục dòng thuộc báo giá hiện tại;
- đơn giá gửi NCC;
- file báo giá Word đã tạo;
- trạng thái gửi/nhận phản hồi;
- giá NCC đã xác nhận;
- file ký/đóng dấu;
- chênh lệch giá so với giá gửi đi;
- lineage/evidence;
- warning/blocking của chính báo giá này;
- preview file báo giá đã xác nhận;
- CTA `Hoàn tất báo giá`.

## D. Những nội dung không thuộc scope màn hình này

Không đưa vào readiness của một báo giá:

- `Đã chọn 3/3 NCC`;
- coverage tổng thể `1/2/3 NCC` của hồ sơ;
- readiness Nguồn giá & Chứng cứ của toàn danh mục;
- `mapping 100%`, sheet/cell/range hoặc trạng thái setup template;
- readiness toàn bộ hồ sơ;
- CTA `Hoàn tất hồ sơ`.

Các nội dung coverage nhiều NCC và selection NCC/báo giá dùng trong hồ sơ thuộc NCCQ tổng hợp và CTA `Chọn nhà cung cấp đã xác nhận giá`.

## E. Warning theo lifecycle

Thiếu file ký/đóng dấu không mặc định là warning ở giai đoạn Nháp/Tạo file. Severity chỉ phát sinh khi lifecycle đã tới dependency tương ứng.

`Hoàn tất báo giá` chỉ active khi không còn Blocking của báo giá hiện tại. Warning có thể cho phép tiếp tục nếu business rule cho phép và phải có CTA xem/xử lý.

## F. Guardrail sau khi hoàn tất báo giá

`Hoàn tất báo giá`:

- lưu trạng thái/snapshot/audit của báo giá hiện tại;
- không tự sửa `Đơn giá hiện hành`;
- không tự chọn NCC;
- không tự hoàn tất toàn bộ hồ sơ;
- không thay thế bước `Chọn nhà cung cấp đã xác nhận giá` ở NCCQ.

## G. Screen inventory authority

Để tránh xung đột ID trong tài liệu hiện tại, cần đọc inventory theo semantic sau:

| Scope | Authority hiện tại |
|---|---|
| NCCQ | Baseline Iteration 6 — màn hình tổng hợp quản lý báo giá NCC |
| NCCQ child — Hoàn tất 1 báo giá NCC | **Baseline Iteration 3 — authority addendum này** |
| S17 — Hoàn tất hồ sơ toàn cục | Chưa được baseline bởi Iteration 3; giữ scope riêng để thiết kế sau |

Addendum này supersede mọi mô tả trước đó coi `S17 Iteration 1/2/3` là readiness toàn hồ sơ khi đang ở flow của một báo giá NCC.