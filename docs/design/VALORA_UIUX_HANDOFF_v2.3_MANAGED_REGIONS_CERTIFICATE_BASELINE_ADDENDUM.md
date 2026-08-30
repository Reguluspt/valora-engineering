# VALORA UI/UX v2.3 — Managed Regions — Chứng thư thẩm định giá — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Scope:** Microsoft 365 Document Workspace → Chứng thư thẩm định giá → Quản lý nội dung do VALORA quản lý.

## 1. Quyết định baseline

Mockup `Managed Regions — Chứng thư thẩm định giá — Iteration 1` được nâng thành visual/design authority. Thiết kế ưu tiên người dùng nghiệp vụ không rành IT và dùng cùng mental model với Managed Regions của Báo cáo, nhưng bề mặt Chứng thư được tối giản theo đặc thù tài liệu ngắn và dữ liệu có cấu trúc cao.

## 2. Mental model user-facing

```text
1. Xem các nội dung VALORA quản lý
→ 2. Xem khác biệt
→ 3. Chọn nội dung cần cập nhật
→ 4. Đồng bộ vào Word
```

User-facing title ưu tiên: `Quản lý nội dung do VALORA quản lý (Chứng thư thẩm định giá)`; không bắt người dùng hiểu Region ID, source path, Data Snapshot ID, Document Revision ID hoặc Microsoft 365 file-version ID.

## 3. Layout authority

Desktop-first Fluent 2:

- Header/breadcrumb + `Mở trong Word` + một primary CTA `Đồng bộ vào Word (n vùng)`.
- Stepper 4 bước.
- Cột trái: danh sách các vùng/nội dung do VALORA quản lý, trang, trạng thái, `Xem chi tiết`.
- Vùng trung tâm: so sánh `Dữ liệu từ VALORA ↔ Nội dung đang có trong Word`, nêu chênh lệch rõ ràng.
- Vùng chọn cập nhật: checkbox theo vùng; chỉ vùng user chọn mới được ghi.
- Panel phải: tình trạng file Word, tóm tắt trạng thái vùng, lịch sử đồng bộ, mẹo sử dụng.
- Footer: `Quay lại`, `Lưu lựa chọn`, một primary CTA `Đồng bộ vào Word (n vùng)`.

## 4. Trạng thái

```text
Đã đồng bộ
Cần cập nhật
Bạn tự chỉnh trong Word
Lỗi
```

`Bạn tự chỉnh trong Word` là trạng thái có chủ đích: VALORA không tự ghi đè vùng đó. Nếu cần chuyển lại thành managed sync, user phải explicit xử lý mapping/policy hoặc chọn hành động phù hợp theo authority hiện hành.

## 5. Nhóm nội dung

Mockup minh họa các nhóm nghiệp vụ thường gặp: thông tin hồ sơ, thông tin khách hàng, đối tượng thẩm định, mục đích thẩm định, thời điểm thẩm định, kết quả thẩm định giá, thông tin phát hành. Đây **không phải danh sách field hard-code**. Vùng thực tế được xác định bởi Template Version + mapping đã cấu hình và dữ liệu hồ sơ hiện hành.

## 6. Sync semantics

- Comparison là `Dữ liệu từ VALORA ↔ Nội dung đang có trong Word`.
- Chỉ managed regions được user chọn mới được cập nhật.
- Nội dung ngoài managed regions giữ nguyên.
- Nếu user đã sửa bên trong managed region, phải phát hiện khác biệt và cho user xem/xử lý trước khi ghi; không silent overwrite.
- Có thể `Lưu lựa chọn` mà chưa đồng bộ; lưu lựa chọn không đồng nghĩa đã cập nhật Word.
- Đồng bộ thành công phải ghi lineage theo authority: `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version`.
- Sau sync, tài liệu tiếp tục dùng baseline `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu` và `Phát hành bộ tài liệu`; baseline này không tạo lifecycle song song.

## 7. Guardrails

- Không fake Word editor.
- Không silent sync, silent overwrite, silent accept conflict hoặc silent publish.
- Không hard-code field chỉ vì xuất hiện trong mockup.
- Không tự đổi narrative ngoài vùng.
- Không đồng nhất Document Revision với Microsoft 365 file version.
- Revision/release đã phát hành không silent mutate.
- Mỗi context/bước chỉ có một primary CTA nổi bật.

## 8. Relationship với Managed Regions — Báo cáo

Hai baseline chia sẻ interaction model và trạng thái, nhưng là hai visual authorities riêng theo loại tài liệu. Baseline Chứng thư không override cấu trúc/nội dung biểu mẫu Chứng thư và không làm thay đổi authority của Managed Regions — Báo cáo.

## 9. ADR

Đây là UI/UX authority update; chưa phát sinh ADR kỹ thuật mới. Nếu implementation làm thay đổi managed-region persistence, conflict detection, sync policy, Document Revision/Data Snapshot semantics hoặc Microsoft 365 version binding thì đánh giá ADR riêng trước khi sửa product code.
