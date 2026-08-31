# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **`Xác nhận & Đồng bộ hàng loạt — Iteration 1`**. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
         → Xem trước kết quả [zero-write]
         → Xử lý xung đột nếu có [zero-write]
         → Xác nhận & Đồng bộ [write boundary]
         → Kết quả đồng bộ hàng loạt
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
Tài liệu có mẫu sẵn sinh hàng loạt và review chung. Preview lớn là vùng review chính. Lineage: `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version`.

### 5.2 Bulk Sync — Baseline
```text
Chọn nguồn dữ liệu mới → Xem thay đổi & phạm vi cập nhật → Xem trước kết quả [zero-write]
→ Xử lý xung đột nếu có [zero-write] → Xác nhận & Đồng bộ [execution]
→ Kết quả đồng bộ hàng loạt
```

### 5.3 Preview — Baseline
Read-only simulation; revision dự kiến chưa tồn tại. Blocking ngăn execution; Warning không tự Blocking.

### 5.4 Conflict Resolution — Baseline
Conflict = cùng Managed Region thay đổi ở VALORA và Word. So sánh Snapshot cũ / VALORA mới / Word hiện tại. User explicit chọn VALORA / giữ Word / bỏ qua. Chỉ cập nhật sync plan; zero-write.

### 5.5 Xác nhận & Đồng bộ hàng loạt — Baseline Iteration 1
Đây là **write boundary / execution gate**. Các bước trước chưa được ghi Word hoặc tạo revision/version.

Layout Fluent 2: header/stepper; summary sau xử lý conflict (`Tài liệu trong phạm vi / Sẽ cập nhật / Không thay đổi / Bỏ qua / Vùng dữ liệu sẽ cập nhật`); bảng `Phạm vi đồng bộ cuối cùng` với quyết định cuối, revision dự kiến và readiness; panel phải `Kiểm tra trước khi đồng bộ` gồm Blocking, Warning, conflict đã xử lý, unchanged + chi tiết warning + thông tin snapshot/source; banner giải thích hậu quả; footer có Hủy, quay lại conflict và primary `Xác nhận & Đồng bộ`.

Execution gate:
- `Blocking = 0`;
- mọi conflict bắt buộc đã có quyết định;
- sync plan không stale so với Word/Data Snapshot hiện tại.
Nếu Word hoặc dữ liệu đổi sau preview/conflict decision, phải yêu cầu review lại, không silent chạy plan cũ.

Khi thực thi:
- chỉ ghi Managed Regions trong final sync plan;
- `Giữ nội dung Word` không overwrite;
- `Bỏ qua lần này` không ghi và không coi `Đã đồng bộ`;
- `Không thay đổi` không tạo revision;
- mỗi tài liệu thực sự cập nhật thành công tạo Document Revision mới và ghi nhận Microsoft 365 file/version;
- published revision/release immutable.

Warning không tự Blocking nhưng phải hiển thị trước execution. Không silent fix validation.

Kết quả batch phải theo **từng tài liệu**; không hiển thị success chung nếu có partial failure. Màn kế tiếp phải phân biệt `Đã đồng bộ / Không thay đổi / Bỏ qua-Cần cập nhật / Lỗi-Cần xử lý` cùng lineage/version tương ứng.

Tên `.xlsx` trên mockup chỉ minh họa Data Snapshot/source; canonical business data vẫn Workbench/database.

### 5.6 Custom template — Baseline
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. Case-only default; library reuse explicit; AI advisory.

### 5.7 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.8 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Preview/conflict zero-write; Confirm & Sync là write boundary.
- Không silent mapping/save/sync/overwrite/conflict resolution/publish.
- Không fake Word/Excel editor.
- Không revision cho unchanged/skipped docs.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 / NCCQ / Result | P0 baseline |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| Đồng bộ dữ liệu hàng loạt | P0 baseline Iteration 1 |
| Xem trước kết quả đồng bộ | P0 baseline Iteration 1 |
| Xử lý xung đột khi đồng bộ | P0 baseline Iteration 1 |
| **Xác nhận & Đồng bộ hàng loạt** | **P0 baseline Iteration 1** |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Sync/Version / Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_CONFIRM_EXECUTE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md`.
- Các addendum hiện hành khác tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Nếu implementation thay đổi multi-document transaction boundary, partial success/rollback, retry/idempotency, stale-plan/concurrency, revision creation hoặc audit/lineage semantics thì phải đánh giá ADR riêng trước khi sửa product code.
