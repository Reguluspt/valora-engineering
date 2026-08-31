# VALORA UI/UX v2.3 — Sinh & Đồng bộ Chứng thư thẩm định giá — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Scope:** Microsoft 365 Document Workspace → Chứng thư thẩm định giá → sinh tài liệu từ template Word, Data Snapshot, Managed Regions, Document Revision và đồng bộ Microsoft 365.  
**Visual language:** Microsoft Fluent 2, desktop-first, Vietnamese-first.

## 1. Quyết định baseline
Mockup `Sinh & Đồng bộ Chứng thư thẩm định giá — Iteration 1` được nâng thành **Baseline / Design Authority**.

Baseline này khóa interaction model và visual contract của child flow sinh Chứng thư. Nó dùng chung Document Generation/Sync Contract với Báo cáo nhưng giữ authority Managed Regions riêng của Chứng thư. Đây không đồng nghĩa product code đã implement.

## 2. Mental flow
```text
Chọn template & phạm vi
→ Data Snapshot
→ Preview & Review vùng
→ Tạo Document Revision
→ Đồng bộ Microsoft 365
→ Kết quả đồng bộ
```

## 3. Layout authority — Fluent 2
- Breadcrumb trong context hồ sơ → Tài liệu & Workspace → Microsoft 365 Document Workspace → Chứng thư thẩm định giá.
- Stepper 6 bước theo mental flow.
- Cột trái: `Template & Phạm vi sinh tài liệu`, `Data Snapshot`, `Kiểm tra Managed Regions`.
- Trung tâm: preview Word view-only lớn nhất, có overlay/nhãn vùng được quản lý.
- Cột phải: `Mapping vùng dữ liệu`, `Thông tin đồng bộ (dự kiến)`, kiểm tra trước khi tạo.
- Footer: `Quay lại` + đúng một primary CTA theo bước, ví dụ `Tiếp tục: Tạo Document Revision`.
- `Mở trong Word` là external editing action; VALORA không xây Word editor giả.

## 4. Template + Data Snapshot
User chọn Template Version và phạm vi dữ liệu. Data Snapshot là ảnh chụp dữ liệu nghiệp vụ dùng để tạo revision, không đồng nhất với Document Revision hay Microsoft 365 file version. Template Version + Data Snapshot phải được truy vết và không silent đổi sau khi user tạo revision.

## 5. Managed Regions — Chứng thư
Các vùng thực tế đến từ Template Version + mapping đã cấu hình; các mã/nhóm hiển thị trên mockup chỉ là minh họa, **không hard-code schema** và không bắt user hiểu Region ID kỹ thuật.

Readiness trước khi sinh có thể dùng `Đã mapping / Cần xem / Chưa mapping`. Khi file Word đã tồn tại, trạng thái Managed Regions chuẩn tiếp tục là:
```text
Đã đồng bộ
Cần cập nhật
Bạn tự chỉnh trong Word
Lỗi
```

Chỉ vùng có mapping hợp lệ mới được fill tự động. Nội dung ngoài Managed Regions giữ nguyên. Nếu user đã sửa bên trong vùng được quản lý, hệ thống phải phát hiện khác biệt và cho xem/xử lý trước khi ghi; không silent overwrite.

## 6. Document Revision
`Tạo Document Revision` là hành động explicit. Revision bind tối thiểu:
```text
Template Version
→ Data Snapshot
→ Managed Region mapping/version
→ Document Revision
```
Tạo revision không đồng nghĩa phát hành. Revision đã phát hành immutable; sinh lại từ dữ liệu/template mới phải tạo revision mới theo authority versioning.

## 7. Microsoft 365 sync
Lineage chuẩn:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```
Document Revision != Microsoft 365 file version. Không silent sync, không silent overwrite, không silent publish. Conflict trong Managed Region phải được xử lý trước khi ghi. Sync result phải có trạng thái/audit truy vết được.

## 8. Validation
Validation phân tán, không tạo màn `Kiểm tra hồ sơ` riêng.
- `Blocking`: dependency bắt buộc chưa hợp lệ thì không cho tạo revision/sync.
- `Warning`: nêu rủi ro nhưng cho tiếp tục khi rule cho phép.
- `Info`: trạng thái/thông tin hỗ trợ.

Kiểm tra tối thiểu: template/version hợp lệ; Data Snapshot đã chọn; Managed Regions bắt buộc có mapping; conflict chưa xử lý; phạm vi dữ liệu phù hợp; lineage dự kiến truy vết được.

## 9. Relationship với authority hiện hành
Baseline này không thay thế `Managed Regions — Chứng thư`, `Đồng bộ dữ liệu & Quản lý phiên bản` hay `Phát hành bộ tài liệu`. Đây là child flow sinh revision trước khi nối vào các authority đó; không tạo lifecycle song song.

## 10. Guardrails
- Không fake Word editor.
- Không silent accept mapping/sync/overwrite/publish.
- Không hard-code field từ mockup.
- Không phơi internal ID/HTTP/SQL/stack trace.
- Một primary CTA mỗi context/bước.
- Data Snapshot, Document Revision và Microsoft 365 file/version là các lớp lineage khác nhau.
- Release/revision đã phát hành immutable theo Publishing authority.

## 11. ADR
Promotion này là cập nhật UI/UX authority. Nếu implementation thay đổi Data Snapshot/Document Revision persistence, transaction boundary, conflict detection, managed-region write policy hoặc Microsoft 365 version binding thì phải đánh giá ADR riêng trước khi sửa product code.
