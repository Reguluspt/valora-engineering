# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **`Xem lại & xử lý ngoại lệ — Iteration 1`** trong Publishing flow rút gọn. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
      → khi dữ liệu thay đổi: Bulk Sync loop
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

### 5.1 Document Set / Bulk Sync / Custom Template — Baseline
Các baselines hiện hành tiếp tục có hiệu lực. Bulk Sync preview/conflict zero-write; Confirm & Sync là write boundary; result theo từng tài liệu. Không export PDF.

### 5.2 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.3 Publishing — Simplified Baseline
Flow 5 bước cũ bị supersede. Authority mới:
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành
→ Release Manifest + khóa revision đã phát hành [system consequence]
```
Không còn màn `Khóa phiên bản` riêng. Không có `Xuất PDF`.

#### 5.3.1 Chuẩn bị bộ phát hành — Baseline Iteration 1
Exception-first. VALORA tự động chọn revision mới nhất đủ điều kiện. Ready auto-selected nhưng không auto-publish; Blocking/error không auto-select; `Cần xem lại` thành exception; user có thể bỏ chọn. Preview view-only.

#### 5.3.2 Xem lại & xử lý ngoại lệ — Baseline Iteration 1
Mục tiêu: user **không rà lại toàn bộ tài liệu Sẵn sàng**, chỉ xử lý ngoại lệ.

Layout Fluent 2 baseline:
- header/breadcrumb + stepper 3 bước;
- summary `Cần xem lại / Có lỗi (bắt buộc xử lý) / Cảnh báo (không chặn)` + hướng dẫn;
- trái: `Danh sách ngoại lệ`, filter/tab theo loại, revision + trạng thái; Ready được ẩn khỏi task list;
- giữa: preview tài liệu view-only lớn, highlight vùng/vấn đề, `Mở trong Word` secondary;
- phải: `Chi tiết & lý do ngoại lệ`, vấn đề, sync/revision và action xử lý;
- footer: progress ngoại lệ bắt buộc + primary `Tiếp tục: Xác nhận phát hành`.

Exception semantics:
- `Có lỗi / Blocking`: tài liệu không thể ở lại release trong trạng thái lỗi; user phải sửa rồi revalidate hoặc loại khỏi release.
- `Cần xem lại`: user review và quyết định theo rule.
- `Cảnh báo`: không tự Blocking; user có thể giữ tài liệu sau explicit review nếu rule cho phép.
- `Sẵn sàng`: không phải task ở màn này.

Actions:
- `Mở tài liệu để cập nhật`: mở Microsoft 365/Word; quay lại phải revalidate.
- `Loại khỏi bộ phát hành`: bỏ tài liệu khỏi release plan lần này.
- `Giữ nguyên và phát hành`: chỉ non-Blocking, explicit decision; không silent bypass.

Completion gate: CTA sang `Xác nhận phát hành` chỉ enabled khi mọi Blocking trong release scope đã xử lý hoặc tài liệu tương ứng đã loại; release plan chưa stale; quyết định bắt buộc đã ghi nhận. Nếu document/revision/readiness đổi trong lúc review, phải revalidate.

Màn này chưa publish, chưa tạo Release Manifest final, chưa khóa revision. Quyết định ngoại lệ phải audit được: tài liệu, revision, vấn đề, lựa chọn user, thời điểm.

### 5.4 Release semantics
Release bind chính xác các Document Revision đã chọn vào Release Manifest. Sau phát hành thành công, revision trong release được khóa/immutable. Lock là system consequence, không phải UI step.

## 6. Guardrails
- Single-user; AI advisory.
- Exception-first UX; giảm thao tác bình thường.
- Auto-select nhưng không auto-publish.
- Không silent bypass Blocking/cảnh báo/publish/overwrite.
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
| Chuẩn bị bộ phát hành | P0 baseline Iteration 1 |
| **Xem lại & xử lý ngoại lệ** | **P0 baseline Iteration 1** |
| Publishing simplified flow | P0 authority |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md`.
- Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành tiếp tục có hiệu lực.

## 9. ADR
Nếu implementation thay đổi exception-decision persistence, release-plan stale detection, revalidation after Word edit, exclusion semantics, release-readiness computation, Release Manifest binding/locking transaction hoặc partial-publish semantics thì phải đánh giá ADR riêng trước khi sửa product code.
