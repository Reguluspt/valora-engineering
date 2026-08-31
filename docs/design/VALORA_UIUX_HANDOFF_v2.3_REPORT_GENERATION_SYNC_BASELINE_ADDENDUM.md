# VALORA UI/UX v2.3 — Sinh & Đồng bộ Báo cáo thẩm định giá — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Scope:** Microsoft 365 Document Workspace → Báo cáo thẩm định giá → sinh tài liệu từ template Word, Data Snapshot, Managed Regions, Document Revision và đồng bộ Microsoft 365.  
**Visual language:** Microsoft Fluent 2, desktop-first, Vietnamese-first.

## 1. Quyết định baseline

Mockup `Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1` được nâng thành **Baseline / Design Authority**.

Baseline này khóa interaction model cho quá trình sinh một Báo cáo thẩm định giá từ Template Version + Data Snapshot, rà soát Managed Regions, tạo Document Revision và đồng bộ file Word lên Microsoft 365. Đây không đồng nghĩa product code đã implement.

## 2. Mental flow

```text
Chọn template & phạm vi
→ Data Snapshot
→ Preview & Review vùng
→ Tạo Document Revision
→ Đồng bộ Microsoft 365
→ Kết quả đồng bộ
```

Không tạo workflow phê duyệt/KSCL mới. Đây là child flow của Microsoft 365 Document Workspace và phải tiếp tục dùng authority Sync/Version + Publishing hiện hành.

## 3. Layout authority — Fluent 2

- Header/breadcrumb đặt trong context hồ sơ → Tài liệu & Workspace → Microsoft 365 Document Workspace → Báo cáo thẩm định giá.
- Stepper 6 bước theo mental flow.
- Cột trái: `Template & Phạm vi sinh tài liệu`, `Data Snapshot`, `Kiểm tra Managed Regions`.
- Vùng trung tâm lớn nhất: preview tài liệu Word dạng view-only với overlay/nhãn vùng được quản lý.
- Cột phải: danh sách `Mapping vùng dữ liệu`, trạng thái từng vùng, `Thông tin đồng bộ (dự kiến)` và kiểm tra trước khi tạo.
- Footer có `Quay lại` và đúng một primary CTA theo bước hiện hành, ví dụ `Tiếp tục: Tạo Document Revision`.
- `Mở trong Word` là external editing action; preview VALORA không phải Word editor giả.

## 4. Template + Data Snapshot contract

- User chọn Template Version và phạm vi dữ liệu dùng để sinh tài liệu.
- Data Snapshot là ảnh chụp dữ liệu nghiệp vụ tại thời điểm sinh revision; không đồng nhất với file Word hoặc Microsoft 365 file version.
- Tạo revision phải ghi rõ Template Version + Data Snapshot được sử dụng.
- Không silent đổi template/version hoặc snapshot sau khi user đã bước sang tạo revision.

## 5. Managed Regions review

Preview phải cho user thấy các vùng do VALORA quản lý và trạng thái mapping của từng vùng.

Trạng thái user-facing tiếp tục theo authority Managed Regions hiện hành:

```text
Đã đồng bộ
Cần cập nhật
Bạn tự chỉnh trong Word
Lỗi
```

Ở giai đoạn sinh tài liệu mới, UI có thể biểu diễn readiness mapping như `Đã mapping / Cần xem / Chưa mapping`, nhưng đây là trạng thái chuẩn bị sinh tài liệu, không thay thế lifecycle trạng thái Managed Regions sau khi file Word tồn tại.

Chỉ vùng có mapping hợp lệ mới được fill tự động. Vùng chưa đủ mapping phải được user xem/xử lý theo validator; không silent đoán hoặc silent fill.

Các mã/nhãn vùng trong mockup chỉ để minh họa khả năng truy vết; UI production không bắt người dùng nghiệp vụ hiểu Region ID kỹ thuật.

## 6. Document Revision semantics

`Tạo Document Revision` là hành động explicit của user.

Revision phải bind tối thiểu:

```text
Template Version
→ Data Snapshot
→ Managed Region mapping/version
→ Document Revision
```

Tạo revision không đồng nghĩa phát hành. Revision đã phát hành không được silent mutate. Nếu sinh lại từ dữ liệu/template mới phải tạo revision mới theo versioning authority.

## 7. Microsoft 365 sync semantics

Sau khi revision được tạo, VALORA mới thực hiện bước đồng bộ/ghi nhận file Microsoft 365 theo authority hiện hành.

Lineage chuẩn:

```text
Template Version
→ Data Snapshot
→ Document Revision
→ Microsoft 365 file/version
```

- Không đồng nhất Document Revision với Microsoft 365 file version.
- Không silent overwrite nội dung user đã chỉnh trong Managed Region.
- Narrative ngoài Managed Regions giữ nguyên khi đồng bộ revision vào file đang tồn tại.
- Nếu có conflict trong Managed Region, user phải xem/xử lý trước khi ghi.
- Sync thành công/thất bại phải có trạng thái và audit truy vết được.

## 8. Validation

Validation là phân tán trong child flow, không tạo màn `Kiểm tra hồ sơ` riêng.

- `Blocking`: không cho tạo revision/sync nếu dependency bắt buộc chưa hợp lệ.
- `Warning`: nêu rủi ro nhưng cho phép tiếp tục khi rule cho phép.
- `Info`: trạng thái/thông tin hỗ trợ.

Kiểm tra tối thiểu trước tạo revision:

- template/version tồn tại và hợp lệ;
- Data Snapshot đã được chọn;
- Managed Regions bắt buộc có mapping;
- không có conflict dữ liệu chưa xử lý;
- phạm vi dữ liệu phù hợp với tài liệu;
- có thể truy vết lineage dự kiến.

## 9. Relationship với baseline hiện hành

Baseline này **không thay thế**:

- `Managed Regions — Báo cáo thẩm định giá — Iteration 1`;
- `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1`;
- `Phát hành bộ tài liệu — Iteration 1`.

Nó khóa child flow trước và trong quá trình sinh revision, sau đó nối vào các authority trên. Không tạo lifecycle song song.

## 10. Guardrails

- Không fake Word editor.
- Không silent accept mapping, silent sync, silent overwrite hoặc silent publish.
- Không hard-code các field chỉ vì xuất hiện trong mockup.
- Không phơi internal ID/HTTP/SQL/stack trace cho user nghiệp vụ.
- Một primary CTA cho mỗi context/bước.
- Data Snapshot, Document Revision và Microsoft 365 file/version là các lớp lineage khác nhau.
- Release đã phát hành immutable theo Publishing authority.
- Design authority không đồng nghĩa implementation đã hoàn tất.

## 11. ADR

Việc nâng mockup này thành baseline là cập nhật UI/UX authority và interaction/domain contract ở mức thiết kế, chưa tự động phát sinh ADR kỹ thuật.

Nếu implementation thay đổi persistence của Data Snapshot/Document Revision, transaction boundary khi tạo file, conflict detection, managed-region write policy hoặc Microsoft 365 version binding thì phải đánh giá ADR riêng trước khi sửa product code.
