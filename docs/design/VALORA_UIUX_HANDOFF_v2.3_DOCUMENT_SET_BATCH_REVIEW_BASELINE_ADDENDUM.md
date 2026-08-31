# VALORA UI/UX v2.3 — Tạo & Xem lại bộ tài liệu hồ sơ — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Visual language:** Microsoft Fluent 2, desktop-first, Vietnamese-first.

## 1. Quyết định baseline
Mockup `Tạo & Xem lại bộ tài liệu hồ sơ — Iteration 1`, phiên bản có **khu vực review tài liệu mở rộng**, được nâng thành Baseline / Design Authority.

Baseline này supersede hướng thiết kế tạo workflow riêng cho từng tài liệu mẫu cố định như Quyết định/Kế hoạch/Phiếu KSCL. Các tài liệu có mẫu sẵn được sinh hàng loạt và review trong một workspace chung.

## 2. Mental model
```text
Bộ mẫu áp dụng cho hồ sơ
→ Data Snapshot
→ Tạo bộ tài liệu hàng loạt
→ Xem lại từng tài liệu trong workspace
→ Khi dữ liệu hồ sơ thay đổi: xem thay đổi → chọn tài liệu/vùng → Đồng bộ dữ liệu
→ Hoàn tất bộ tài liệu
→ Phát hành bộ tài liệu
```

Báo cáo và Chứng thư vẫn giữ các baseline Managed Regions / Generation-Sync riêng đã khóa; màn bộ tài liệu là orchestration workspace, không xóa các child-flow chuyên sâu đó.

## 3. Layout authority
- Header/breadcrumb trong `Tài liệu & Workspace → Microsoft 365 Document Workspace → Bộ tài liệu hồ sơ`.
- Summary phía trên: hồ sơ đang thao tác, Data Snapshot hiện tại, tổng quan tài liệu, thao tác nhanh.
- Main workspace ưu tiên review: danh sách tài liệu bên trái, **preview tài liệu lớn ở trung tâm**, metadata/mapping/sync history bên phải.
- Preview phải đủ lớn để đọc nội dung; phiên bản mockup review nhỏ trước đó bị supersede.
- Có zoom, chuyển trang, full-screen và `Mở trong Word`; preview VALORA là view-only, không fake Word editor.
- Một primary CTA theo context; `Đồng bộ dữ liệu` là action rõ ràng khi snapshot hồ sơ thay đổi.

## 4. Batch generation
- User tạo nhiều tài liệu từ các Template Version đã cấu hình sẵn trong một lần.
- Một Data Snapshot được ghi nhận làm nguồn cho batch; từng tài liệu vẫn có Document Revision và Microsoft 365 file/version riêng.
- Lỗi một tài liệu phải được hiển thị theo tài liệu; không silent bỏ qua.
- Không bắt user đi qua workflow mapping/sinh 6 bước cho từng tài liệu mẫu cố định.

## 5. Review workspace
Bảng tài liệu tối thiểu thể hiện: `Tài liệu | Mẫu sử dụng | Phiên bản | Trạng thái | Cập nhật lần cuối | Tác vụ`.

Chọn một tài liệu cập nhật preview lớn và panel thông tin. Panel phải hỗ trợ xem Template Version, Document Revision, Microsoft 365 file, mapping/Managed Regions và lịch sử đồng bộ khi có.

## 6. Đồng bộ khi hồ sơ thay đổi
Khi dữ liệu nghiệp vụ thay đổi sau lần sinh gần nhất, VALORA xác định tài liệu/vùng đang dựa trên snapshot cũ và hiển thị `Cần cập nhật`.

`Đồng bộ dữ liệu` là explicit user action:
```text
Snapshot mới
→ Xác định tài liệu/vùng thay đổi
→ Xem chi tiết khác biệt
→ User chọn tài liệu/vùng
→ Đồng bộ
→ Tạo/ghi nhận revision + Microsoft 365 version theo authority
```

Không silent overwrite. Narrative ngoài Managed Regions giữ nguyên. Conflict trong Managed Region phải xem/xử lý trước khi ghi. Revision/release đã phát hành không mutate; cập nhật phải tạo revision mới.

## 7. Mẫu tùy biến riêng cho hồ sơ
Workspace có `Tải lên mẫu tùy biến`.

Flow:
```text
Tải .docx
→ AI phân tích nội dung
→ Đối chiếu với dữ liệu hồ sơ hiện tại
→ Nhận diện/gợi ý các trường tương ứng
→ Highlight vị trí và đề xuất Managed Regions/mapping
→ User rà soát & xác nhận
→ Test fill
→ Lưu Template Version
```

AI chỉ đề xuất, không tự chốt mapping. Không hard-code field từ mockup.

Template mới mặc định có scope `Mẫu riêng của hồ sơ`. Chỉ khi user explicit chọn `Lưu vào thư viện mẫu` mới trở thành mẫu tái sử dụng ngoài hồ sơ hiện tại. Upload tài liệu khách hàng không tự động biến thành global/shared template.

## 8. Lineage
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```
Batch có thể chia sẻ Data Snapshot nhưng từng tài liệu có lineage riêng. Document Revision != Microsoft 365 file version.

## 9. Trạng thái
Tái sử dụng vocabulary hiện hành khi phù hợp: `Sẵn sàng`, `Cần cập nhật`, `Chưa hoàn tất`, `Lỗi`; với Managed Regions sau khi file tồn tại tiếp tục dùng `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`.

## 10. Guardrails
- Single-user.
- Không workflow phê duyệt/KSCL riêng.
- Không fake Word editor.
- Không silent mapping/sync/overwrite/publish.
- Không auto-promote mẫu riêng thành mẫu dùng chung.
- Preview là review-first và chiếm diện tích chính.
- Một primary CTA mỗi context.
- Phát hành tiếp tục dùng Publishing authority hiện hành.

## 11. ADR
Promotion này khóa UI/UX + domain interaction contract. Khi implement, nếu batch transaction semantics, template scope persistence, AI-to-managed-region conversion, conflict detection hoặc multi-document sync semantics làm thay đổi persistence/transaction boundary thì phải đánh giá ADR riêng trước khi sửa product code.
