# VALORA UI/UX v2.3 — Audit / Lineage Entry-point Baseline Addendum

**Contract:** `Audit / Lineage Entry-point Consistency Contract v1`  
**Visual baseline:** `Audit & Lineage Entry-point Pattern Board — Iteration 1`  
**Status:** Design Authority / Baseline  
**Date:** 01/09/2026

## 1. Purpose
Khóa semantics và visual pattern cho các entry point dẫn người dùng từ nghiệp vụ hiện tại đến đúng traceability surface trên toàn VALORA. Pattern này là cross-product navigation/traceability authority, không phải workflow checkpoint và không tạo một màn `Audit toàn hệ thống` mới.

## 2. Context-first rule
Người dùng bắt đầu từ business object/context hiện tại, rồi chọn entry point theo câu hỏi cần trả lời:

- `Xem lịch sử thay đổi` — ai đã làm gì, khi nào, thay đổi gì.
- `Xem nguồn gốc` — dữ liệu/giá trị này đến từ đâu.
- `Xem quyết định` — ai xác nhận/chọn/xử lý và vì sao.
- `Xem phiên bản` / `Xem chuỗi phiên bản` — đây là phiên bản nào và sinh ra từ phiên bản/snapshot nào.
- `Xem Release Manifest` — bản phát hành đã bind chính xác những Document Revision nào.

Không dùng một generic CTA `Xem Audit` đặt khắp sản phẩm.

## 3. Domain boundaries
Các persistence/domain primitives hiện hữu như `AuditEvent`, `UserActionLog`, `KnowledgeLineage`, `IdentityDecisionLog`, `KnowledgeVersion`, `Document Revision`, `Release Manifest` không phải tên menu nghiệp vụ.

UI dùng nhãn nghiệp vụ: `Lịch sử thay đổi | Nguồn gốc | Quyết định | Phiên bản | Release Manifest`.

Không hợp nhất case history, price history, knowledge lineage, document lineage và release history thành một capability duy nhất. Các surface được phép deep-link qua lại khi có quan hệ nhưng không duplicate dữ liệu để giả thành một timeline toàn cục.

## 4. Canonical lineage chains
### 4.1 Document / Release
`Release → Release Manifest → Document Revision → Data Snapshot → Managed Region / business data → source/evidence nếu có`.

### 4.2 Knowledge
`Knowledge Version → review decision → candidate → extracted value → source locator → historical dossier/file`.

### 4.3 NCC Selection
`NCC Selection Revision → selected QuoteLine → Quote revision → Supplier → Evidence/Source → confirmation event`.

Các chain khác dùng cùng semantics: chỉ hiển thị mắt xích có căn cứ; không suy diễn lineage giả.

## 5. Deep-link context contract
Mọi điều hướng đến traceability surface phải giữ đủ context để người dùng hiểu nguồn xuất phát và quay lại đúng nơi. Conceptual payload tối thiểu:

```text
context_type
context_id
project_id?
parent_context?
return_target
anchor?
```

`return_target` phải ưu tiên trở về đúng business context có ý nghĩa, ví dụ đúng asset line, document revision, knowledge item, quote line hoặc release; không mặc định chỉ quay về landing page.

Frontend route có thể khác nhau theo module, nhưng semantic context không được mất khi deep-link.

## 6. Missing / broken link behavior
Nếu một mắt xích không tồn tại hoặc không thể truy cập:
- `Chưa được ghi nhận` khi hệ thống không có provenance/linkage đã lưu.
- `Không khả dụng` khi source không còn khả dụng.
- `Không còn quyền truy cập` khi quyền hiện tại không cho phép mở nguồn.
- Không suy diễn, tự bind, tự tìm source thay thế hoặc che mất mắt xích.

Một traceability surface bị lỗi không được biến thành `Không có dữ liệu` nếu thực tế là read/access failure; áp dụng Cross-product State Contract hiện hành.

## 7. Navigation relationships
Mỗi entry point dẫn đến đúng surface chuyên trách và surface có thể deep-link sang surface liên quan:

`Lịch sử thay đổi ↔ Nguồn gốc ↔ Quyết định ↔ Phiên bản ↔ Release Manifest`

Quan hệ này là navigation graph, không phải một database graph mới và không yêu cầu tất cả entity đều có đủ cả 5 entry point.

Entry point chỉ xuất hiện khi có ý nghĩa nghiệp vụ và target phù hợp.

## 8. UX rules
- Đặt entry point gần dữ liệu/object cần truy vết: header, toolbar, row action, detail drawer hoặc contextual menu phù hợp.
- Không nhồi đồng thời cả 5 entry point khi object không hỗ trợ đủ 5 capability.
- Dùng nhãn chuẩn và icon nhất quán.
- Surface đích phải có title/context để người dùng biết đang xem lịch sử/nguồn gốc của đối tượng nào.
- Loading/error/empty/retry tuân Cross-product State Pattern Baseline.
- Traceability surface mặc định read-oriented; không biến history/lineage thành commit surface trừ khi domain authority riêng đã định nghĩa explicit decision action.
- Một primary recovery CTA mỗi error/revalidation context.

## 9. Security / access
Deep-link không bypass permission/tenant/domain authorization. Nếu user nhìn thấy business object nhưng không có quyền mở source chi tiết, UI hiển thị trạng thái quyền phù hợp thay vì rò rỉ metadata nhạy cảm.

## 10. Approved visual authority
Mockup `Audit & Lineage Entry-point Pattern Board — Iteration 1` được người dùng explicit nâng Baseline ngày 01/09/2026 và là visual authority cho pattern này.

Board baseline gồm tối thiểu:
1. 5 entry point chuẩn và khi nào dùng.
2. Decision tree chọn đúng entry point.
3. Cross-product entry-point map cho Case Workspace, Kho tri thức, Document, Sync & Version và Publishing.
4. Deep-link Context Contract + return target.
5. Document / Knowledge / NCC lineage mental models.
6. Surface relationship & navigation.
7. Missing-link behavior.
8. UX guidelines, access-control guidance và Do/Don't.

Nếu wording minh họa trong visual mâu thuẫn semantic contract này hoặc domain authority cụ thể, semantic/domain authority thắng.

## 11. Implementation / ADR boundary
Baseline này ưu tiên reuse persistence/audit primitives hiện hữu và không yêu cầu audit subsystem mới.

Nếu implementation cần thêm unified traceability projection, generic cross-domain reference persistence, lineage graph persistence hoặc thay đổi semantics của `AuditEvent`, `UserActionLog`, `KnowledgeLineage`, `IdentityDecisionLog`, Document lineage hay Release Manifest thì phải đánh giá ADR trước khi thay đổi persistence/architecture.
