# TM01 — Danh sách mẫu báo giá nhà cung cấp — Visual Baseline v2.3

**Trạng thái:** BASELINE ĐÃ DUYỆT / DESIGN AUTHORITY
**Mockup:** TM01 Iteration 1
**Phong cách:** VALORA shell + Fluent 2 light, desktop-first
**Phạm vi:** Visual/interaction baseline cho màn hình `Cấu hình → Mẫu báo giá NCC → Danh sách mẫu`

Tài liệu này ghi lại visual baseline của mockup TM01 Iteration 1 đã được người dùng duyệt. Dữ liệu hiển thị trong mockup chỉ là dữ liệu minh họa; không phải dữ liệu khách hàng/NCC/hồ sơ thật.

## 1. Cấu trúc màn hình authority

- Dùng cùng sidebar trái và top app bar với các baseline VALORA hiện hành.
- Breadcrumb: `Cấu hình → Mẫu báo giá nhà cung cấp → Danh sách mẫu`.
- Header chính: `Danh sách mẫu báo giá nhà cung cấp`.
- Primary CTA đặt góc phải header: `Tạo mẫu mới`.
- Bề mặt chính là **bảng danh sách template**, không dùng card-heavy dashboard làm trọng tâm.

## 2. Filter / search baseline

Toolbar đầu màn hình gồm tối thiểu:

- `Nhà cung cấp`;
- `Loại template`;
- `Định dạng file`;
- `Trạng thái`;
- search theo tên mẫu / mã mẫu;
- `Bộ lọc`;
- `Đặt lại`.

## 3. Summary compact

Ngay trên bảng có summary compact theo 4 trạng thái chính:

- `Tổng số mẫu`;
- `Đang sử dụng`;
- `Bản nháp`;
- `Ngừng sử dụng`.

Summary chỉ hỗ trợ scan nhanh, không được lấn át bảng danh sách.

## 4. Bảng danh sách baseline

Các cột authority của Iteration 1:

```text
STT
| Mã mẫu
| Tên mẫu
| Nhà cung cấp
| Loại template
| Định dạng
| Phiên bản
| Cập nhật gần nhất
| Trạng thái
| Thao tác
```

Quy tắc:

- Historical TM01 sample vocabulary: `XLSX` / `DOCX` showed their file icons. Current supplier quotation template authority is Word `.docx` only under [TM04 addendum §A](../VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md#a-quyết-định-04-được-cập-nhật) and [Template Management §C](../VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md#c-quy-tắc-định-dạng). The historical Excel TM03 examples remain history; they grant no current supplier-template authority.
- `Phiên bản` hiển thị compact như `v1.0`, `v2.1`.
- Trạng thái dùng badge semantic: `Đang sử dụng`, `Bản nháp`, `Ngừng sử dụng`.
- Mỗi dòng có CTA `Xem chi tiết` và overflow menu cho thao tác phụ.
- Bảng hỗ trợ pagination và lựa chọn số dòng/trang.

## 5. Panel phải baseline

Panel phải gồm 3 khối hỗ trợ:

1. `Hướng dẫn`;
2. `Thao tác nhanh`;
3. `Gợi ý`.

`Thao tác nhanh` có thể deep-link tới:

- `Tạo mẫu mới`;
- `Upload & Mapping`;
- `Preview / Test fill`;
- `Lịch sử phiên bản`.

Panel phải là vùng hỗ trợ; không được làm bảng chính bị thu hẹp quá mức. Nếu cần tối ưu viewport ở iteration sau, có thể cho phép thu gọn panel nhưng không thay đổi IA đã duyệt.

## 6. Guardrail visual

- Fluent 2 light, nền sáng, border nhẹ, radius và spacing đồng bộ NCCQ/S11–S13.
- Vietnamese-first.
- Một primary CTA nổi bật: `Tạo mẫu mới`.
- Không tự suy diễn template là `Đang sử dụng` nếu chưa đạt điều kiện readiness theo Handoff.
- Không silent overwrite version/template cũ.
- TM01 chỉ quản lý danh sách/template metadata; mapping chi tiết thuộc TM03, test fill thuộc TM04, version history chi tiết thuộc TM05.

## 7. Quan hệ với Handoff

Khi có mâu thuẫn visual giữa mockup/iteration TM01 cũ và baseline này, **TM01 Iteration 1 + §11 của `VALORA_UIUX_HANDOFF_v2.3.md` là nguồn quyết định**.

The former “TM03 và TM04 vẫn chưa có baseline authority” statement was superseded by the approved [TM04 addendum §§A–D](../VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md): TM01, TM03 Word-only Upload & Mapping and [TM04 Word Preview/Test fill baseline](VALORA_TM04_BASELINE_v2.3.md) are approved. This is visual/design authority, not runtime-completion evidence.
