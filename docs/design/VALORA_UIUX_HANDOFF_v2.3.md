# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **Đồng bộ dữ liệu hàng loạt — Iteration 1**. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

## 1. North-star flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản → Asset Context Drawer
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Batch generation → Review
      → khi dữ liệu thay đổi: Đồng bộ dữ liệu hàng loạt
         → Chọn nguồn dữ liệu mới
         → Xem thay đổi & phạm vi cập nhật
         → Xem trước kết quả
         → Xác nhận & Đồng bộ
      → Tải lên mẫu tùy biến → AI mapping → Test fill → Xác nhận & Lưu template
   → Báo cáo / Chứng thư: child-flow chuyên sâu khi cần
   → Phát hành bộ tài liệu
```

## 2. Price & Evidence
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính. NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% Warning; không Blocking.

## 3. Kết quả thẩm định giá
03 bảng công ty immutable; giữ tên/thứ tự cột, Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Template / AI / Spreadsheet
AI advisory; user xác nhận mapping/template. Không silent accept/publish/overwrite/change formula. Custom field không tự promote canonical. Fill Engine giữ authority hiện hành.

## 5. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, release manifest. Microsoft 365 quản lý Word/file/file version. `Document Revision != Microsoft 365 file version`.

### 5.1 Document Set — Baseline
Tài liệu có mẫu sẵn sinh hàng loạt và review chung. Preview lớn là vùng review chính. Từng tài liệu có lineage `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version`.

### 5.2 Đồng bộ dữ liệu hàng loạt — Baseline Iteration 1
Mental flow:
```text
Chọn nguồn dữ liệu mới → Xem thay đổi & phạm vi cập nhật → Xem trước kết quả → Xác nhận & Đồng bộ
```
Không silent sync; user chọn phạm vi trước khi ghi.

Bước `Xem thay đổi & phạm vi cập nhật` dùng Fluent 2: header/stepper; summary nguồn mới + số tài liệu/vùng ảnh hưởng + Warning/Blocking; trái là phạm vi và filter; giữa là bảng tài liệu bị ảnh hưởng; phải là diff chi tiết current value → new value, warning và revision dự kiến; primary CTA `Xem trước kết quả`.

User có thể đồng bộ tất cả tài liệu bị ảnh hưởng, chỉ tài liệu được chọn hoặc theo nhóm. Tài liệu `Không thay đổi` không tạo revision mới chỉ vì nằm trong bộ hồ sơ.

Mức ảnh hưởng `Cao / Trung bình / Thấp / Không thay đổi` là review signal, không phải approval state. Blocking ngăn phần bị lỗi; Warning không tự Blocking. Conflict do user chỉnh Managed Region trong Word phải đi qua diff/conflict resolution hiện hành trước khi ghi.

Sau sync thành công, **mỗi tài liệu thực sự được cập nhật tạo Document Revision mới** và ghi nhận Microsoft 365 file/version tương ứng. Published revision/release immutable.

`Nguồn dữ liệu mới` dạng `.xlsx` trên mockup là minh họa cho Data Snapshot/source revision mới, không phải ràng buộc kiến trúc. Canonical business data vẫn là Workbench/database.

### 5.3 Custom template — Baseline
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. Case-only default; library reuse explicit; AI advisory.

### 5.4 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.5 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Không fake Word/Excel editor.
- Không silent mapping/save/sync/overwrite/publish.
- Không tạo revision mới cho tài liệu không thay đổi.
- Không auto-promote custom field/template scope.
- Preview review-first; một primary CTA mỗi context.
- Published revision/release immutable.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 / NCCQ / Result | P0 baseline |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| **Đồng bộ dữ liệu hàng loạt** | **P0 baseline Iteration 1** |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Sync/Version / Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md`.
- Các addendum Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Result/NCCQ hiện hành tiếp tục có hiệu lực.

## 9. ADR
Nếu implementation thay đổi multi-document transaction boundary, partial success/rollback, idempotency, Data Snapshot binding, conflict resolution hoặc version creation semantics thì phải đánh giá ADR riêng trước khi sửa product code.
