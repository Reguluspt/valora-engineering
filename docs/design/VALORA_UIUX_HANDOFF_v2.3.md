# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **`Kết quả đồng bộ hàng loạt — Iteration 1`**, phiên bản **không có luồng xuất PDF**. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
            → Xem & quản lý revision / Quay lại workspace
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

### 5.5 Xác nhận & Đồng bộ hàng loạt — Baseline
Đây là write boundary. CTA chỉ enabled khi Blocking=0, conflict bắt buộc đã xử lý và sync plan chưa stale. Chỉ Managed Regions trong final plan được ghi; giữ Word/bỏ qua/không thay đổi không bị overwrite. Chỉ tài liệu cập nhật thành công mới tạo Document Revision + Microsoft 365 version.

### 5.6 Kết quả đồng bộ hàng loạt — Baseline Iteration 1
Đây là màn **post-execution**, không ghi thêm dữ liệu chỉ vì user mở màn kết quả.

Layout Fluent 2 baseline: header/breadcrumb + stepper hoàn tất; summary cards `Đã đồng bộ thành công / Không có thay đổi / Bỏ qua (theo quyết định) / Lỗi (thất bại) / Tổng tài liệu`; bảng `Chi tiết kết quả theo tài liệu` với vùng thay đổi, kết quả, Revision mới (VALORA), phiên bản M365 và thời gian xử lý; panel phải là tổng quan phiên đồng bộ + breakdown kết quả; ghi chú dưới bảng; primary CTA `Xem & quản lý revision`.

Result semantics:
- `Đã đồng bộ`: Managed Regions trong sync plan đã ghi thành công; tạo Document Revision mới và ghi nhận Microsoft 365 file/version.
- `Không thay đổi`: không ghi; không tạo revision mới.
- `Bỏ qua`: không ghi lần này; không revision mới; không coi là đã đồng bộ.
- `Lỗi`: chưa hoàn tất; không giả định thay đổi đã ghi thành công; user xem chi tiết và retry sau khi xử lý.

Không dùng một success chung để che partial failure. Retry phải revalidate Data Snapshot/Word hiện tại và không replay sync plan cũ nếu stale.

**Export authority:** không có luồng xuất file PDF tại màn Kết quả đồng bộ hàng loạt. Phiên bản mockup trước còn `Báo cáo tóm tắt (PDF)` bị supersede. Nếu sau này cần báo cáo đối soát, phải thiết kế capability riêng. Publishing authority hiện hành cũng tiếp tục **không có `Xuất PDF`**.

### 5.7 Custom template — Baseline
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. Case-only default; library reuse explicit; AI advisory.

### 5.8 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.9 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Preview/conflict zero-write; Confirm & Sync là write boundary; Result là post-execution view.
- Không silent mapping/save/sync/overwrite/conflict resolution/retry/publish.
- Không fake Word/Excel editor.
- Không revision cho unchanged/skipped/failed nếu chưa cập nhật thành công.
- Không export PDF trong Bulk Sync Result/Publishing baseline.
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
| Xác nhận & Đồng bộ hàng loạt | P0 baseline Iteration 1 |
| **Kết quả đồng bộ hàng loạt** | **P0 baseline Iteration 1 — no PDF export** |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Sync/Version / Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_RESULT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_CONFIRM_EXECUTE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md`.
- Các addendum hiện hành khác tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Nếu implementation thay đổi partial-success model, retry/idempotency, recovery semantics, stale-plan revalidation, result persistence, multi-document transaction boundary hoặc revision/version creation thì phải đánh giá ADR riêng trước khi sửa product code.
