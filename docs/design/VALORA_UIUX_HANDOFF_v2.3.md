# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **`Chuẩn bị bộ phát hành — Iteration 1`** với Publishing flow rút gọn. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
   → Publishing đơn giản hóa
      → Chuẩn bị bộ phát hành
      → Xem lại & xử lý ngoại lệ
      → Xác nhận phát hành
      → hệ thống tạo Release Manifest + khóa revision đã phát hành
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
Preview/conflict không ghi Word/revision; Confirm & Sync là write boundary. Result theo từng tài liệu: `Đã đồng bộ / Không thay đổi / Bỏ qua / Lỗi`. Không dùng success chung để che partial failure. Không export PDF.

### 5.3 Custom template — Baseline
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. AI chỉ đề xuất; case-only default; `Lưu vào thư viện mẫu` là explicit opt-in.

### 5.4 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.5 Publishing — Simplified Baseline
**Flow 5 bước cũ bị supersede**:
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản`.

Authority mới:
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành
→ Release Manifest + khóa revision đã phát hành [system consequence]
```

Không còn màn `Khóa phiên bản` riêng. Không có `Xuất PDF`.

#### 5.5.1 Chuẩn bị bộ phát hành — Baseline Iteration 1
Mục tiêu: **giảm thao tác, exception-first**.

VALORA tự động chọn revision mới nhất đủ điều kiện phát hành. User không phải tick từng tài liệu bình thường; user chủ yếu xem `Cần xem lại / Có lỗi` và có thể bỏ chọn tài liệu nếu không muốn đưa vào release.

Layout Fluent 2 baseline:
- summary cards `Sẵn sàng phát hành (auto-selected) / Cần xem lại / Có lỗi / Không thay đổi / Tổng tài liệu`;
- banner `Cách hệ thống chọn tài liệu`;
- bảng `Danh sách tài liệu sẽ phát hành` với tên, loại, revision, trạng thái, lần đồng bộ gần nhất, chọn để phát hành;
- preview nhanh view-only + `Mở trong Word`;
- panel phải: Release dự kiến, ngày dự kiến, breakdown trạng thái, điểm cần chú ý;
- một primary CTA theo context.

Auto-selection rules:
- revision `Sẵn sàng` → auto-select;
- Blocking/error → không auto-select;
- `Cần xem lại` → exception cần user review;
- `Không thay đổi` có thể dùng revision hiện hành nếu revision đó vẫn đạt readiness;
- user có thể bỏ chọn;
- auto-select **không** đồng nghĩa auto-publish.

Mockup `Chọn tài liệu để phát hành — Iteration 1` trước đó chỉ là Design Proposal và bị supersede bởi baseline này.

### 5.6 Release semantics
Release bind chính xác các Document Revision đã chọn vào Release Manifest. Sau phát hành thành công, revision nằm trong release được khóa/immutable. `Khóa revision` là hậu quả hệ thống của phát hành, không phải bước thao tác riêng.

## 6. Guardrails
- Single-user; AI advisory.
- Exception-first UX để giảm thao tác.
- Auto-select nhưng không auto-publish.
- Không silent mapping/save/sync/overwrite/conflict resolution/publish.
- Không fake Word/Excel editor.
- Không export PDF trong Bulk Sync Result hoặc Publishing.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 / NCCQ / Result | P0 baseline |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| Bulk Sync loop | P0 baseline Iteration 1 |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| **Chuẩn bị bộ phát hành** | **P0 baseline Iteration 1** |
| Publishing simplified flow | P0 authority |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md`.
- Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành tiếp tục có hiệu lực.

## 9. ADR
Nếu implementation thay đổi release-readiness computation, auto-selection persistence, Release Manifest binding, locking transaction, partial-publish semantics, hoặc các persistence/transaction semantics đã nêu trong authority Bulk Sync/Template thì phải đánh giá ADR riêng trước khi sửa product code.
