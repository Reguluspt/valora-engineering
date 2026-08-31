# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **`Xử lý xung đột khi đồng bộ — Iteration 1`**. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
         → Xử lý xung đột nếu có [zero-write, user decision]
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

### 5.2 Bulk Sync — Baseline
`Chọn nguồn dữ liệu mới → Xem thay đổi & phạm vi cập nhật → Xem trước kết quả → [Xử lý xung đột nếu có] → Xác nhận & Đồng bộ`. User chọn scope; không silent sync; tài liệu không đổi không revision.

### 5.3 Xem trước kết quả — Baseline
Read-only simulation / zero-write. Revision dự kiến chưa tồn tại. Blocking >0 ngăn execution; Warning không tự Blocking. Current→new phải xem được theo Managed Region.

### 5.4 Xử lý xung đột khi đồng bộ — Baseline Iteration 1
Đây là **conditional step**, chỉ xuất hiện nếu cùng một Managed Region vừa thay đổi trong dữ liệu VALORA mới vừa được user chỉnh trong Word kể từ snapshot/lần đồng bộ trước. Nếu không có conflict thì bỏ qua.

Mental flow:
```text
Phát hiện conflict → Chọn tài liệu/vùng → So sánh 3 giá trị → User quyết định từng vùng
→ Hoàn tất conflict bắt buộc → Cập nhật sync plan → Quay lại Xác nhận & Đồng bộ
```

Layout Fluent 2: banner giải thích; trái là danh sách conflict theo tài liệu/vùng; giữa là preview Word view-only lớn highlight đúng vùng; phải so sánh `Giá trị lần đồng bộ trước (Snapshot cũ)` / `Dữ liệu VALORA mới` / `Nội dung hiện tại trong Word`, sau đó user chọn cách xử lý. Footer có progress và primary `Áp dụng quyết định & quay lại xác nhận đồng bộ`.

Resolution choices:
- `Dùng dữ liệu VALORA mới`.
- `Giữ nguyên nội dung trong Word`.
- `Bỏ qua vùng này trong lần đồng bộ này` — defer, không coi là đã đồng bộ.

Không bên nào auto-win. Mọi conflict bắt buộc trong scope phải có explicit decision trước khi hoàn tất bước. Màn conflict chỉ cập nhật **sync plan**, chưa ghi Word, chưa tạo Document Revision/Microsoft 365 version.

Mỗi quyết định phải audit được: tài liệu/vùng, ba giá trị so sánh, lựa chọn user, thời điểm. Revision/version chỉ tạo sau `Xác nhận & Đồng bộ` execution thành công. Published revision/release immutable.

### 5.5 Custom template — Baseline
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. Case-only default; library reuse explicit; AI advisory.

### 5.6 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.7 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Preview/conflict resolution zero-write đối với Word/revision.
- Không auto-win VALORA/Word.
- Không fake Word/Excel editor.
- Không silent mapping/save/sync/overwrite/conflict resolution/publish.
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
| Xem trước kết quả đồng bộ | P0 baseline Iteration 1 |
| **Xử lý xung đột khi đồng bộ** | **P0 baseline Iteration 1** |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Sync/Version / Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md`.
- Các addendum hiện hành khác tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Nếu implementation persist conflict decisions, thay đổi sync-plan transaction boundary, defer semantics, stale-conflict detection, audit storage hoặc multi-document execution semantics thì phải đánh giá ADR riêng trước khi sửa product code.
