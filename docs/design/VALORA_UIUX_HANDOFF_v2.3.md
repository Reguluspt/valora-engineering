# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước và **`Xác nhận phát hành — Iteration 1`**. Publishing simplified flow hiện đã có baseline đầy đủ 3 bước. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

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
   → Publishing
      → Chuẩn bị bộ phát hành
      → Xem lại & xử lý ngoại lệ
      → Xác nhận phát hành [commit boundary]
      → Release Manifest + khóa revision + audit [system consequence]
```

## 2. Price & Evidence
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính. NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% Warning; không Blocking.

## 3. Kết quả thẩm định giá
03 bảng công ty immutable; giữ tên/thứ tự cột, Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Template / AI / Spreadsheet
AI advisory; user xác nhận mapping/template. Không silent accept/publish/overwrite/change formula. Custom field không tự promote canonical. Fill Engine giữ authority hiện hành.

## 5. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, Release Manifest. Microsoft 365 quản lý Word/file/file version. `Document Revision != Microsoft 365 file version`.

### 5.1 Document Set / Bulk Sync / Custom Template — Baseline
Các baselines hiện hành tiếp tục có hiệu lực. Bulk Sync preview/conflict zero-write; Confirm & Sync là write boundary; result theo từng tài liệu. Không export PDF.

### 5.2 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.3 Publishing — Simplified Baseline hoàn chỉnh
Flow authority:
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành
→ Release Manifest + khóa revision + audit [system consequence]
```
Flow 5 bước cũ bị supersede. Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

#### 5.3.1 Chuẩn bị bộ phát hành — Baseline Iteration 1
Exception-first. VALORA auto-select revision mới nhất đủ điều kiện; user chủ yếu xử lý ngoại lệ. Auto-select không auto-publish.

#### 5.3.2 Xem lại & xử lý ngoại lệ — Baseline Iteration 1
Ready không phải task. Blocking phải sửa/revalidate hoặc loại khỏi release. Warning không tự Blocking; giữ và phát hành phải là explicit decision. Màn này chưa publish/finalize/lock.

#### 5.3.3 Xác nhận phát hành — Baseline Iteration 1
Đây là **final commit/write boundary** của Publishing.

Layout Fluent 2 baseline:
- header/breadcrumb + stepper 3 bước, bước 3 active;
- `Thông tin phát hành dự kiến`: Release ID dự kiến, ngày dự kiến, ghi chú tùy chọn, người phát hành;
- summary số tài liệu sẽ phát hành / cảnh báo còn lại / tài liệu bị loại / tổng tài liệu / tổng revision;
- bảng tài liệu sẽ phát hành với loại, Document Revision, trạng thái, lần sync gần nhất;
- `Ngoại lệ đã xử lý`;
- `Tính toàn vẹn & điều kiện phát hành`;
- panel phải `Tóm tắt Release`, `Hệ quả sau khi phát hành`, cảnh báo immutable;
- footer: Hủy, quay lại ngoại lệ, một primary CTA `Xác nhận phát hành`.

Commit gate:
- Blocking = 0 trong release scope;
- mọi ngoại lệ bắt buộc đã xử lý;
- revision được chọn vẫn hợp lệ;
- release plan chưa stale;
- không unresolved version conflict;
- tài liệu giữ trong release đạt readiness.

Nếu trạng thái thay đổi sau review, phải revalidate trước commit.

Khi xác nhận thành công, hệ thống:
1. tạo Release Manifest final bind chính xác các Document Revision đã chọn;
2. khóa/immutable các revision thuộc release;
3. ghi audit event + lineage;
4. ghi trạng thái release thành công.

Tài liệu bị loại không thuộc manifest và không bị khóa bởi release này. Warning non-Blocking còn lại phải được audit theo rule hiện hành.

Release ID trước commit là dự kiến/reserved; ID minh họa trên mockup không phải schema cứng. Không được báo `Đã phát hành` nếu Release Manifest chưa commit hợp lệ.

### 5.4 Release semantics
Published Release và các Document Revision đã bind là immutable. Muốn thay đổi sau phát hành phải tạo release mới; không mutate release cũ.

## 6. Guardrails
- Single-user; AI advisory.
- Exception-first UX.
- Auto-select nhưng không auto-publish.
- Explicit final confirmation.
- Không silent bypass Blocking/Warning/publish/overwrite.
- Không fake Word/Excel editor.
- Không export PDF trong Bulk Sync Result hoặc Publishing.
- Lock revision là system consequence, không phải UI step.
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
| Xem lại & xử lý ngoại lệ | P0 baseline Iteration 1 |
| **Xác nhận phát hành** | **P0 baseline Iteration 1** |
| Publishing simplified flow | **P0 baseline complete** |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md`.
- Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành tiếp tục có hiệu lực.

## 9. ADR
Release Manifest transaction boundary, Release ID reservation, locking atomicity, retry/idempotency, failure recovery, audit commit semantics, partial-publish semantics và các release-plan persistence semantics cần ADR nếu implementation thay đổi persistence/architecture.
