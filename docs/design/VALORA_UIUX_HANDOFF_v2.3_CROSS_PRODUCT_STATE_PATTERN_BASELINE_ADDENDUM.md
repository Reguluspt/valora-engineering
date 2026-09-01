# VALORA UI/UX Handoff v2.3 — Cross-product Empty / Loading / Error / Retry Contract v1

**Status:** Design Authority / Baseline  
**Baseline visual:** `Cross-product State Pattern Board — Iteration 1`  
**Date:** 01/09/2026  
**Scope:** Toàn bộ VALORA — Thẩm định giá, Workbench, Knowledge Management, Microsoft 365 Workspace, NCC Selection, Publishing.

## 1. Purpose
Khóa một contract xuyên suốt cho các trạng thái `Empty / Loading / Error / Retry / Processing / Conflict / Connectivity / Partial Success` để UI không tự phát sinh pattern riêng theo từng màn.

Contract này **không thay thế** `VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md`. Error Registry tiếp tục là message authority (`title | message | nextAction | severity | retryable`). Cross-product State Contract chịu trách nhiệm phân loại state, scope, presentation surface, recovery action và preserve/replace data behavior.

Canonical mental model:

```text
Domain/API/System state
→ Canonical UI State
→ Scope
→ Presentation Surface
→ Vietnamese message
→ Allowed recovery action
→ Preserve / refresh / replace current data
```

## 2. Canonical UI State v1

```text
INITIAL_LOADING
SECTION_LOADING
BACKGROUND_REFRESH
PROCESSING
EMPTY_FIRST_USE
EMPTY_NO_RESULTS
EMPTY_NOT_APPLICABLE
EMPTY_COMPLETED
INLINE_ERROR
SECTION_ERROR
PAGE_ERROR
FATAL_ERROR
STALE_DATA
VERSION_CONFLICT
OFFLINE
RECONNECTING
PARTIAL_SUCCESS
```

## 3. Loading authority
- `INITIAL_LOADING`: capability chính chưa có usable data.
- `SECTION_LOADING`: chỉ panel/drawer/tab/table/detail area đang tải.
- `BACKGROUND_REFRESH`: đã có usable data và đang kiểm tra/lấy bản mới.
- Khi đã có usable data, không xóa content chỉ để hiển thị spinner.
- Background refresh giữ content và dùng indicator nhẹ.
- Table initial load có thể dùng row skeleton/table loading state; pagination/refresh giữ rows hiện có nếu còn hợp lệ.

## 4. Loading ≠ Processing
`PROCESSING` dùng cho long-running domain/system jobs như Upload, Extraction, AI mapping, generation, Bulk Sync, revalidation, historical dossier processing.

Processing status tối thiểu:
`queued | running | retrying | completed | failed | cancelled`.

Nếu có progress thật thì hiển thị; nếu backend không biết phần trăm thực thì dùng indeterminate progress + current step. **Không tạo progress % giả. Không spinner vô hạn cho durable job.**

## 5. Empty semantics
- `EMPTY_FIRST_USE`: capability chưa từng có dữ liệu. Có CTA tạo mới nếu nghiệp vụ cho phép.
- `EMPTY_NO_RESULTS`: dữ liệu tồn tại nhưng filter/search hiện tại không khớp. Recovery là xóa filter/đặt lại tìm kiếm; không biến thành CTA tạo dữ liệu.
- `EMPTY_NOT_APPLICABLE`: capability không áp dụng trong context hiện tại; không phải Error.
- `EMPTY_COMPLETED`: không còn item cần xử lý vì công việc đã hoàn tất; có thể dùng positive state.

Hard invariant: **Empty không che Error.** API/network/permission/timeout failure không được render thành `Chưa có dữ liệu`.

## 6. Error scope
- `INLINE_ERROR`: field hoặc action nhỏ; giữ toàn bộ màn hình.
- `SECTION_ERROR`: một panel/table/tab/drawer lỗi; chỉ thay section lỗi, phần khác vẫn dùng được.
- `PAGE_ERROR`: capability chính không thể tải/tiếp tục; giữ App Shell/navigation khi vẫn hợp lệ.
- `FATAL_ERROR`: chỉ dùng khi không thể tiếp tục an toàn; không dùng fatal chỉ vì một request 500.

User-facing message phải Vietnamese-first, business language, không raw HTTP/API/RBAC/row_version/provider/stack trace.

## 7. Surface-selection authority
- Field/action nhỏ → inline message.
- Section lỗi → section error / inline alert.
- Page-level notice nhưng vẫn thao tác được → banner.
- Action thành công/ngắn hạn → toast.
- Conflict cần explicit decision → dialog/drawer theo context.
- Không có dữ liệu → Empty State.
- Capability chính không dùng được → Page Error.

Không dùng toast cho Blocking issue cần xử lý. Không dùng modal cho lỗi read-only nhỏ ở một section.

## 8. Retry contract
Retry phải là action thật và đúng scope:
- section lỗi → retry section;
- table pagination lỗi → retry page/chunk đó;
- drawer lỗi → retry drawer;
- page capability lỗi → retry page data;
- processing job retryable → retry job theo backend/domain authority.

Không reload cả ứng dụng khi chỉ một section lỗi.

### 8.1 Safe retry boundary
Read operations thường retry được. Mutation không được blind retry khi chưa biết commit đã xảy ra hay chưa.

Hard rule:
`client timeout / uncertain write → resolve current command/result state → chỉ retry khi biết an toàn`.

Áp dụng đặc biệt với NCC Selection confirmation, Apply dữ liệu, Document Sync, Knowledge confirmation và Release Confirmation.

## 9. Stale / Version Conflict
### `STALE_DATA`
Dữ liệu hiển thị không còn mới nhất nhưng vẫn có thể đọc. Giữ dữ liệu hiện tại nếu còn hợp lệ + thông báo đã thay đổi + CTA `Cập nhật dữ liệu`.

### `VERSION_CONFLICT`
Optimistic concurrency/version mismatch, thường tương ứng 409.

Hard rule:
`409 → không last-write-wins → không tự gửi lại mutation → reload/reconcile → user review khi cần → explicit commit lại`.

Conflict scope theo entity/capability; không dùng một full-screen Workbench conflict modal cho mọi 409 toàn sản phẩm.

## 10. Preserve-data principle
`Old usable data + refresh error → giữ old data → đánh dấu có thể đã cũ → Retry`.

Không biến một table đang có usable rows thành blank page chỉ vì refresh thất bại. Chỉ clear data nếu giữ nó có thể làm người dùng hiểu sai hoặc commit sai.

## 11. Partial Success
Batch result phải phân biệt `succeeded | failed | skipped | retryable_failed`.

Partial failure giữ phần thành công; không rollback UI của item thành công chỉ vì item khác thất bại. Retry chỉ phần retryable failed nếu domain cho phép.

Bulk Sync là pattern authority điển hình cho nguyên tắc này.

## 12. Connectivity
### `OFFLINE`
- giữ dữ liệu đang xem;
- disable mutation cần server confirmation;
- giữ local draft nếu capability cho phép;
- hiển thị trạng thái mất kết nối rõ ràng;
- không fake success và không auto-submit official decision.

### `RECONNECTING`
Tự kiểm tra lại kết nối; sau reconnect phải refresh/revalidate state cần thiết trước khi re-enable commit actions.

`local draft != persisted state`. UI phải phân biệt `Đã lưu | Chưa lưu | Đang lưu | Lưu thất bại | Cần cập nhật mới`.

## 13. Permission / authentication
`Không có quyền != Không có dữ liệu`.
Session expired phải có authentication recovery phù hợp. Tenant-hidden/not-found security responses không được lộ raw technical detail.

## 14. Long-running job / timeout semantics
Long job phải có durable identity khi backend hỗ trợ: `job_id | status | progress/current_step | attempt | started_at | last_update | failure | retry availability`.

Rời màn hình rồi quay lại phải đọc current job state thay vì khởi động job mới. Refresh browser không duplicate job.

Frontend timeout không đồng nghĩa domain failure; với write command có trạng thái chưa xác định, phải query result/status trước khi kết luận hoặc retry.

## 15. Search/filter and data-heavy tables
Search state phân biệt `chưa tìm | đang tìm | có kết quả | không có kết quả | search lỗi`. Search error không được hiển thị No Results.

Filter hợp lệ được giữ khi retry.

Cell supplementary data lỗi không fail cả row/table nếu core data vẫn hợp lệ. Missing business value không được giả thành `0`.

## 16. Cross-product integration
### Global Case State
Case-state projection lỗi → Error/Retry theo scope. Frontend không tự dựng fallback business state machine.

### NCC Selection
Candidate section lỗi → `SECTION_ERROR`. Confirm 409 → `VERSION_CONFLICT` → reload selection/quote state → review → explicit confirm lại. Không auto-reselect NCC.

### Knowledge Management
No candidate because filter → `EMPTY_NO_RESULTS`; queue thực sự sạch → `EMPTY_COMPLETED`; chưa nhập historical dossier → `EMPTY_FIRST_USE`; extraction chạy → `PROCESSING`.

### Microsoft 365 / Documents
Return/revalidation có thể là `BACKGROUND_REFRESH` hoặc `PROCESSING` tùy operation. Managed Region conflict → `VERSION_CONFLICT`; không auto-win. Batch sync hỗn hợp → `PARTIAL_SUCCESS`.

### Publishing
Release plan stale → stale/conflict theo server semantics. Release Confirmation timeout không blind retry: kiểm tra Release Manifest thực tế; nếu đã commit hợp lệ route `Đã phát hành`, nếu chưa commit trở về safe confirmation state.

## 17. Accessibility / CTA authority
- State phải có accessible status semantics; không diễn đạt chỉ bằng màu.
- Focus management phù hợp cho error/conflict dialog.
- Recovery actions keyboard accessible.
- Một primary recovery CTA mỗi context.

## 18. Fifteen invariants
1. Empty không che Error.
2. Loading không đồng nghĩa Processing.
3. Có usable data thì không blank page khi background refresh.
4. Retry phải thật và đúng scope.
5. Mutation không blind retry khi commit status chưa xác định.
6. 409 không last-write-wins.
7. Partial failure giữ phần thành công.
8. Warning không tự biến thành Blocking.
9. Offline không fake success.
10. Local draft không đồng nghĩa persisted state.
11. Technical error details không là primary user-facing copy.
12. Search error không hiển thị No Results.
13. Không spinner vô hạn cho durable job.
14. Frontend không tự dựng fallback business state machine khi projection/API authority lỗi.
15. Một primary recovery CTA mỗi context.

## 19. Visual authority — Cross-product State Pattern Board — Iteration 1
Board approved as Design Authority visualizes:
- Loading: Initial / Section / Background Refresh;
- Processing long-running job;
- Empty: First Use / No Results / Not Applicable;
- Error: Inline / Section / Page / Fatal;
- Conflict & Stale: Stale Data / Version Conflict (409);
- Connectivity: Offline / Reconnecting;
- Partial Success;
- 15 invariants;
- surface-selection guide;
- severity/icon guide;
- implementation notes.

The board is a cross-product design-system authority, not a standalone business workflow screen and not a north-star checkpoint.

## 20. Guardrails
Single-user; Vietnamese-first; Fluent 2; desktop-first; data-heavy/table-first. AI advisory only. Không silent retry/overwrite/reconcile/commit. Không fake Word/Excel editor. Không Export PDF. Existing domain-specific stronger authorities continue to win within their scope.