# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 01/09/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa `Audit / Lineage Entry-point Consistency Contract v1` + visual baseline `Audit & Lineage Entry-point Pattern Board — Iteration 1`, `Microsoft 365 Return / Revalidation Contract v1` + visual baseline `M365 Return & Revalidation — Iteration 1`, `Cross-product Empty / Loading / Error / Retry Contract v1` + `Cross-product State Pattern Board — Iteration 1`, Publishing simplified flow, `Đã phát hành — Iteration 1`, `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`, `Chọn NCC đã xác nhận giá — Iteration 1`, `Quản lý Kho tri thức — Iteration 1`, `Cần rà soát tri thức — Iteration 1`, `Hồ sơ cũ — Iteration 1` và `Lịch sử & nguồn gốc — Iteration 1`. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian, màn rule-check giá riêng, màn Tiến độ hồ sơ riêng hoặc màn Audit toàn hệ thống.

## 1. North-star flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ [orchestration hub]
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản [Asset Context Drawer theo ngữ cảnh]
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Batch generation → Review
      → Mở trong Word ↔ Return / Revalidation [integration state, không checkpoint]
      → khi dữ liệu thay đổi: Bulk Sync loop
      → Tải lên mẫu tùy biến → AI mapping → Test fill → Xác nhận & Lưu template
   → Báo cáo / Chứng thư: child-flow chuyên sâu khi cần
   → Publishing
      → Chuẩn bị bộ phát hành
      → Xem lại & xử lý ngoại lệ
      → Xác nhận phát hành [commit boundary]
      → Release Manifest + khóa revision + audit [system consequence]
      → Đã phát hành [success/read-only result]

Horizontal traceability pattern, không phải checkpoint:
Audit / Lineage Entry-points
  → Xem lịch sử thay đổi | Xem nguồn gốc | Xem quyết định | Xem phiên bản | Xem Release Manifest
  → deep-link đúng domain surface và giữ business context / return target

Supporting module, không phải checkpoint bắt buộc:
Quản lý Kho tri thức
  → Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc
  ↔ Workbench tra cứu Kho tri thức
```

## 1.1 Tổng quan hồ sơ — Orchestration Hub Baseline Iteration 2
`Tổng quan hồ sơ` là project-level orchestration hub, không phải approval dashboard và không tạo màn `Tiến độ hồ sơ` riêng.

Global Case State + Resume / Next-action Contract v1:
- projection tổng hợp `Project + WorkflowInstance + domain completion facts + ValidationIssue + document/release state + last meaningful context`;
- không lấy `Project.status` hay `WorkflowInstance.current_state` đơn lẻ làm UI route authority;
- 16 canonical stages: `PRELIMINARY_REQUEST | PRELIMINARY_ANALYSIS | PRELIMINARY_READY | OFFICIAL_INTAKE | ASSET_REVIEW | ASSET_WORKBENCH | PRICE_EVIDENCE | SUPPLIER_QUOTES | SUPPLIER_SELECTION | APPRAISAL_RESULT | DOCUMENT_WORKSPACE | DOCUMENT_SYNC_REVIEW | PUBLISHING_PREPARATION | PUBLISHING_EXCEPTION_REVIEW | PUBLISHING_CONFIRMATION | PUBLISHED`;
- UI dùng nhãn nghiệp vụ tiếng Việt; enum kỹ thuật không phải primary label;
- completion derive từ mandatory business facts, không từ màn đã mở; Knowledge Management là supporting module nên không làm giảm completion;
- một hồ sơ có một primary `next_action`, precedence: Blocking → stale cần review → công việc đang dở hợp lệ → bước bắt buộc chưa hoàn tất gần nhất → bước tiếp theo north-star → Published/no action;
- next-action là system-derived projection, không phải AI decision; AI chỉ giải thích/tóm tắt;
- Warning không Blocking;
- Resume Target ưu tiên last meaningful context còn hợp lệ, nhưng blocker/stale mới có thể thắng; resume không phải business commit và không bypass blocker;
- `current_stage` và `next_action.stage` có thể khác nhau;
- không frontend-only state machine, silent transition hoặc silent stale reconciliation.

Layout baseline: header/thông tin hồ sơ; `Trạng thái hồ sơ` với stage nghiệp vụ + completion + Blocking/Warning/Cần xem lại; progress 16 canonical stages có Document Sync Review và Publishing Exception Review; group progress; blockers; warnings; thông tin/thống kê; right rail `Hành động tiếp theo | Ngữ cảnh hồ sơ (Resume Target) | Hoạt động gần đây`; một primary CTA `Tiếp tục xử lý` hoặc contextual equivalent.

Implementation direction: read projection `GET /api/v1/projects/{project_id}/case-state`; resume persistence `PUT /api/v1/projects/{project_id}/resume-context`; backend trả semantic route key, frontend sở hữu URL mapping; concurrency dùng case/row version phù hợp.

## 1.2 Đã phát hành — Post-Publish Success Baseline Iteration 1
`Đã phát hành` là success/read-only result state sau `Xác nhận phát hành` commit thành công. Không phải bước thứ 4 của Publishing và không phải checkpoint mới.

UI chỉ được hiển thị success khi Release Manifest final đã commit hợp lệ. Success surface phản ánh Release ID thật, thời điểm/người phát hành, số tài liệu trong manifest, Document Revision đã bind/khóa, M365 file/version nếu có, retained warnings và audit/lineage.

Layout authority: success banner + release summary + completed publishing progress + integrity/warning summary + document table + right rail. Primary CTA `Về Tổng quan hồ sơ`. Không edit/unlock/rollback/replace release, không Export PDF. Published release/revisions immutable.

## 1.3 Cross-product Empty / Loading / Error / Retry — Baseline Contract v1
Contract này là state-presentation + recovery authority dùng chung cho toàn VALORA và không thay Error Registry.

Canonical states:
`INITIAL_LOADING | SECTION_LOADING | BACKGROUND_REFRESH | PROCESSING | EMPTY_FIRST_USE | EMPTY_NO_RESULTS | EMPTY_NOT_APPLICABLE | EMPTY_COMPLETED | INLINE_ERROR | SECTION_ERROR | PAGE_ERROR | FATAL_ERROR | STALE_DATA | VERSION_CONFLICT | OFFLINE | RECONNECTING | PARTIAL_SUCCESS`.

Hard invariants: Empty không che Error; Loading khác Processing; có usable data không blank khi refresh; retry thật/đúng scope; mutation không blind retry khi commit chưa xác định; 409 không last-write-wins; partial failure giữ phần thành công; Warning không tự thành Blocking; Offline không fake success; local draft không đồng nghĩa persisted; technical details không là primary copy; search error không là No Results; không spinner vô hạn cho durable job; frontend không tự dựng fallback business state machine; một primary recovery CTA/context.

Visual baseline `Cross-product State Pattern Board — Iteration 1` là design-system authority, không phải workflow checkpoint.

## 1.4 Microsoft 365 Return / Revalidation — Baseline Contract v1 + Visual Iteration 1
Contract khóa hành vi khi user `Mở trong Word` rồi quay lại VALORA. Return/Revalidation là integration/state contract, không phải workflow checkpoint và không phải business commit.

Canonical flow:
```text
Mở trong Word
→ ghi nhận handoff context
→ user quay lại / regain focus / explicit refresh / action cần freshness
→ BACKGROUND_REFRESH
→ revalidate M365 file state
→ so sánh với M365 file/version + Managed Region baseline đã bind vào Document Revision hiện hành
→ classify
→ derive sync/readiness
→ continue / review / conflict / recovery
```

Canonical classifications:
`NO_CHANGE | EXTERNAL_CHANGE_OUTSIDE_MANAGED | EXTERNAL_CHANGE_IN_MANAGED | FILE_REPLACED_OR_MOVED | ACCESS_UNAVAILABLE`.

Three-way semantics với `Old = snapshot/lần sync đã bind`, `V = VALORA hiện tại`, `W = Word hiện tại`:
- `V=Old, W=Old` → không đổi;
- `V=Old, W!=Old` → Word-only edit, bảo toàn Word;
- `V!=Old, W=Old` → VALORA-only change, `Cần cập nhật`, không conflict;
- `V!=Old, W!=Old` và V/W khác semantic value → conflict cần explicit decision;
- V/W hội tụ cùng semantic value có thể non-conflict nếu audit/lineage đủ.

Hard rules: quay lại VALORA không đồng nghĩa Word đã đổi; revalidation có usable data dùng `BACKGROUND_REFRESH`; M365 version mới không tự tạo Document Revision; ngoài Managed Region không mặc định conflict; user edit trong Managed Region không silent overwrite; không auto-bind file thay thế theo filename; không fake `Đã đồng bộ`/`Sẵn sàng phát hành` khi freshness chưa xác minh; reconnect phải revalidate trước mutation phụ thuộc freshness; published revision/release immutable.

**Visual baseline `M365 Return & Revalidation — Iteration 1` đã được explicit chốt ngày 01/09/2026.** Board authority gồm: high-level return flow; 5 semantic outcome cards; state UI patterns; three-way comparison; conflict decision surface; background revalidation indicator; mandatory principles. Nếu wording minh họa mâu thuẫn semantic contract, contract thắng.

## 1.5 Audit / Lineage Entry-point Consistency — Baseline Contract v1 + Visual Iteration 1
Contract này khóa cách người dùng đi từ một business object/context sang đúng traceability surface. Đây là cross-product navigation/traceability pattern, không phải workflow checkpoint, không phải business commit và không tạo một màn `Audit toàn hệ thống`.

5 entry point chuẩn:
- `Xem lịch sử thay đổi` — trả lời ai làm gì, khi nào, thay đổi gì.
- `Xem nguồn gốc` — trả lời dữ liệu/giá trị đến từ đâu.
- `Xem quyết định` — trả lời ai xác nhận/chọn/xử lý và vì sao.
- `Xem phiên bản` / `Xem chuỗi phiên bản` — trả lời đây là version nào và sinh ra từ version/snapshot nào.
- `Xem Release Manifest` — trả lời release đã bind chính xác những Document Revision nào.

Context-first authority:
- entry point đặt gần object/dữ liệu cần truy vết;
- chỉ hiển thị capability có ý nghĩa với object hiện tại, không ép đủ 5 entry point;
- không dùng generic `Xem Audit` xuyên sản phẩm;
- persistence/domain primitives như `AuditEvent`, `UserActionLog`, `KnowledgeLineage`, `IdentityDecisionLog` không phải primary UI label;
- domain histories vẫn độc lập: case/price history, Knowledge lineage, Document lineage, Release history có thể deep-link qua lại nhưng không duplicate thành timeline toàn cục.

Deep-link context conceptual contract:
```text
context_type
context_id
project_id?
parent_context?
return_target
anchor?
```

`return_target` phải đưa user về đúng business context có ý nghĩa như asset line, document revision, knowledge item, quote line hoặc release; không mặc định chỉ về landing page.

Canonical lineage mental models:
- Document/Release: `Release → Release Manifest → Document Revision → Data Snapshot → Managed Region/business data → source/evidence nếu có`.
- Knowledge: `Knowledge Version → review decision → candidate → extracted value → source locator → historical dossier/file`.
- NCC Selection: `NCC Selection Revision → selected QuoteLine → Quote revision → Supplier → Evidence/Source → confirmation event`.

Missing/broken link:
- không có provenance đã lưu → `Chưa được ghi nhận`;
- source không còn khả dụng → `Không khả dụng`;
- user không còn quyền → `Không còn quyền truy cập`;
- không suy diễn lineage, tự bind source thay thế hoặc che read/access failure thành Empty.

Visual baseline `Audit & Lineage Entry-point Pattern Board — Iteration 1` đã được explicit chốt ngày 01/09/2026. Board authority gồm 5 entry points, decision tree, cross-product entry-point map, Deep-link Context Contract, lineage mental models, surface relationships, missing-link behavior, UX/access guidelines và Do/Don't. Nếu wording minh họa mâu thuẫn semantic/domain authority, semantic/domain authority thắng.

Implementation ưu tiên reuse audit/lineage primitives hiện hữu. Nếu cần unified traceability projection, generic cross-domain reference persistence, lineage graph persistence hoặc thay đổi semantics của audit/lineage primitives thì phải đánh giá ADR trước persistence/architecture change.

## 2. Price & Evidence
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính. NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% Warning; không Blocking. Dữ liệu Kho tri thức chỉ hỗ trợ/tra cứu và không override price-source authority.

### 2.1 Chọn NCC đã xác nhận giá — Baseline Iteration 1
`Chọn NCC đã xác nhận giá` là checkpoint sau `Hoàn tất từng báo giá NCC` và trước `Kết quả thẩm định giá`. Selection scope: `1 Project + 1 ProjectAssetLine + 1 confirmed QuoteLine = 1 current NCC Selection`. Đổi NCC tạo revision mới; quote revision/source thay đổi không auto-rebind; Warning không Blocking. Primary commit CTA `Xác nhận NCC đã chọn`. Selection không tự tạo/sửa AppraisedPriceDecision và không ghi đè giá Kết quả thẩm định.

## 3. Kết quả thẩm định giá
Ba bảng công ty immutable về cấu trúc:
1. `STT | Tên tài sản | Đặc điểm KTKT | ĐVT | SL`
2. `STT | Tên tài sản | ĐVT | SL | NCC1 | NCC2 | NCC3 | Tổ TĐG đánh giá: Đơn giá | Thành tiền`
3. `STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền`
Giữ Tổng cộng/Làm tròn/Số tiền bằng chữ; không rename/reorder/cardize.

## 4. Knowledge Management
Supporting workspace: `Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`. Structured KTKT là business data; template/Microsoft 365 sở hữu presentation. Historical dossier là candidate pipeline, không direct-inject active knowledge. Knowledge review cần explicit human decision. History/lineage read-oriented.

Knowledge traceability entry-points tuân Audit/Lineage Contract: `Lịch sử & nguồn gốc` tiếp tục là knowledge-governance surface; có thể deep-link tới hồ sơ cũ, tài sản chuẩn, review decision hoặc source locator nhưng không biến thành case/price audit timeline.

## 5. Microsoft 365 / Documents
VALORA sở hữu structured data, Data Snapshot, lineage, audit, sync status, Document Revision, Release Manifest. Microsoft 365 sở hữu Word file/OneDrive-SharePoint file/version. Document Revision != M365 file version. Managed Region không silent overwrite; conflict phải explicit resolve. Published revision/release immutable.

Return/Revalidation authority: external Word return phải revalidate M365 state trước mutation phụ thuộc freshness; M365 version mới không tự tạo Document Revision; Managed Region changes dùng three-way semantics và explicit conflict handling khi cần.

Document/Release traceability entry-points tuân Audit/Lineage Contract: mở đúng history/source/decision/version/manifest surface theo câu hỏi nghiệp vụ và giữ document/revision/release return context.

## 6. Publishing
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit boundary] → Release Manifest + locked revisions + audit [system consequence] → Đã phát hành [success/read-only result]`.
Không màn khóa riêng, không Export PDF.

Release traceability dùng `Xem Release Manifest` làm entry point chuyên trách; không thay bằng generic Audit timeline.

## 7. Guardrails
Single-user; Vietnamese-first; Fluent 2; desktop-first; data-heavy/table-first; AI advisory; human-confirmed official decisions; không silent bypass/publish/overwrite/state transition/stale reconciliation; không fake Word/Excel editor; không Export PDF; published revision/release immutable; một primary CTA/recovery CTA mỗi context; traceability context-first, giữ return target và không dựng `Audit toàn hệ thống`.
