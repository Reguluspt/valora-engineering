# VALORA UI/UX v2.3 — Đồng bộ dữ liệu hàng loạt — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Đồng bộ dữ liệu hàng loạt — Iteration 1` được nâng thành Baseline / Design Authority. Đây là child-flow của `Tạo & Xem lại bộ tài liệu hồ sơ` và `Đồng bộ dữ liệu & Quản lý phiên bản`, không phải lifecycle song song.

## 2. Mental flow
```text
Chọn nguồn dữ liệu mới
→ Xem thay đổi & phạm vi cập nhật
→ Xem trước kết quả
→ Xác nhận & Đồng bộ
```

Không silent sync. User luôn chọn phạm vi trước khi ghi.

## 3. Layout authority — bước Xem thay đổi & phạm vi cập nhật
- Header + stepper 4 bước.
- Summary: nguồn dữ liệu mới, số tài liệu bị ảnh hưởng, số vùng thay đổi, Warning, Blocking.
- Trái: phạm vi đồng bộ + bộ lọc nhanh.
- Giữa: bảng `Danh sách tài liệu bị ảnh hưởng`, hỗ trợ chọn tài liệu, loại tài liệu, mức độ ảnh hưởng, số vùng thay đổi, trạng thái hiện tại, phiên bản hiện tại.
- Phải: `Chi tiết thay đổi` của tài liệu đang chọn, top vùng thay đổi, current value → new value, Warning và thông tin phiên bản mới dự kiến.
- Footer: Hủy, quay lại, và một primary CTA `Xem trước kết quả`.

## 4. Selection authority
User có thể chọn:
- đồng bộ tất cả tài liệu bị ảnh hưởng;
- chỉ tài liệu được chọn;
- theo nhóm tài liệu.

Tài liệu `Không thay đổi` không cần tạo revision mới chỉ vì nằm trong bộ hồ sơ. Chỉ tài liệu/vùng user chọn và đủ điều kiện mới được cập nhật.

## 5. Change & validation semantics
- Mỗi tài liệu hiển thị mức ảnh hưởng `Cao / Trung bình / Thấp / Không thay đổi` như tín hiệu review, không phải approval state.
- `Blocking > 0` ngăn đồng bộ phần bị Blocking cho tới khi xử lý.
- Warning cho phép đi tiếp khi rule hiện hành cho phép nhưng phải hiển thị rõ.
- User phải xem được giá trị hiện tại và giá trị mới theo Managed Region.
- Conflict do user chỉnh trong Word/Managed Region phải được đưa vào diff/conflict resolution authority hiện hành trước khi ghi.

## 6. Version semantics
Sau sync thành công, **mỗi tài liệu được cập nhật tạo Document Revision mới** và ghi nhận Microsoft 365 file/version tương ứng theo authority hiện hành. Published revision/release không mutate.

Không được hiểu số version minh họa trên mockup là schema bắt buộc.

## 7. Data-source semantics
`Nguồn dữ liệu mới` trong mockup là minh họa cho Data Snapshot/source revision mới của hồ sơ. Canonical business data vẫn là Workbench/database. Không khóa hệ thống vào việc chỉ nhận `.xlsx` làm nguồn sync tài liệu.

## 8. Guardrails
- Single-user.
- Không silent sync/overwrite.
- Không fake Word editor.
- Không tạo revision mới cho tài liệu không thay đổi.
- Không ghi ngoài Managed Regions.
- Một primary CTA mỗi context.
- Document Revision != Microsoft 365 file version.

## 9. ADR
Nếu implementation thay đổi multi-document transaction boundary, partial success/rollback, idempotency, Data Snapshot binding, conflict resolution, hoặc version creation semantics thì phải đánh giá ADR riêng trước khi sửa product code.
