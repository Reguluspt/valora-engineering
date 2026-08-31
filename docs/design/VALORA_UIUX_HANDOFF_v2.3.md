# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước, `Đồng bộ dữ liệu hàng loạt — Iteration 1` và **`Xem trước kết quả đồng bộ — Iteration 1`**. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
         → Xử lý xung đột nếu có
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
Tài liệu có mẫu sẵn sinh hàng loạt và review chung. Preview lớn là vùng review chính. Lineage: `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version`.

### 5.2 Đồng bộ dữ liệu hàng loạt — Baseline Iteration 1
`Chọn nguồn dữ liệu mới → Xem thay đổi & phạm vi cập nhật → Xem trước kết quả → Xác nhận & Đồng bộ`. Không silent sync; user chọn phạm vi. Tài liệu không thay đổi không tạo revision mới.

### 5.3 Xem trước kết quả đồng bộ — Baseline Iteration 1
Đây là bước 3/4 và là **read-only simulation / zero-write**. Chưa cập nhật Word, chưa tạo Document Revision, chưa tạo Microsoft 365 version.

Layout Fluent 2: header/stepper; `Thông tin phiên xem trước`; summary `Sẽ được cập nhật / Không thay đổi / Warning / Blocking`; bảng tài liệu gồm loại, mức ảnh hưởng, vùng thay đổi, thay đổi dữ liệu, thay đổi Word, kết quả và revision dự kiến; panel phải hiển thị tài liệu đang chọn, revision hiện tại/dự kiến, current value → value sau sync, Warning/Blocking. Footer có quay lại, `Xử lý xung đột (nếu có)` và primary `Tiếp tục: Xác nhận & Đồng bộ`.

Semantics:
- `Sẽ cập nhật` chỉ là kết quả mô phỏng.
- `Revision dự kiến` chưa tồn tại và không được reserve như revision thực chỉ vì preview.
- `Không thay đổi` không tạo revision.
- User xem được current→new ở Managed Region.
- Blocking >0 không cho thực thi đồng bộ; Warning không tự Blocking.
- Preview không silent sửa dữ liệu/mapping/content để pass.

Nếu Word và VALORA cùng thay đổi một Managed Region, user phải đi qua conflict resolution. Không auto chọn VALORA thắng hoặc Word thắng.

Tên `.xlsx` trong mockup chỉ minh họa source/Data Snapshot; canonical business data vẫn Workbench/database.

### 5.4 Custom template — Baseline
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. Case-only default; library reuse explicit; AI advisory.

### 5.5 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.6 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Preview sync zero-write.
- Không fake Word/Excel editor.
- Không silent mapping/save/sync/overwrite/conflict resolution/publish.
- Không revision/version mới trong preview.
- Không tạo revision cho tài liệu không thay đổi.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 / NCCQ / Result | P0 baseline |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| Đồng bộ dữ liệu hàng loạt | P0 baseline Iteration 1 |
| **Xem trước kết quả đồng bộ** | **P0 baseline Iteration 1** |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Sync/Version / Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md`.
- Các addendum hiện hành khác tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Nếu implementation persist preview simulation, reserve revision number, cache diff, hoặc thay đổi conflict/validation/multi-document transaction boundary thì phải đánh giá ADR riêng trước khi sửa product code.
