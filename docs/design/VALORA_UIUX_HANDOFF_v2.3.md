# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 01/09/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa `Microsoft 365 Return / Revalidation Contract v1`, `Cross-product Empty / Loading / Error / Retry Contract v1` + `Cross-product State Pattern Board — Iteration 1`, Publishing simplified flow, `Đã phát hành — Iteration 1`, `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`, `Chọn NCC đã xác nhận giá — Iteration 1`, `Quản lý Kho tri thức — Iteration 1`, `Cần rà soát tri thức — Iteration 1`, `Hồ sơ cũ — Iteration 1` và `Lịch sử & nguồn gốc — Iteration 1`. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian, màn rule-check giá riêng hoặc màn Tiến độ hồ sơ riêng.

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

Layout authority:
- `Bộ tài liệu đã được phát hành` + banner `Phát hành thành công!` + badge `ĐÃ PHÁT HÀNH`;
- release summary;
- 3 bước Publishing hoàn thành + result state `Đã phát hành`;
- tính toàn vẹn/warning/ngoại lệ/M365 sync/lịch sử;
- bảng `Tên tài liệu | Loại tài liệu | Document Revision đã phát hành | Trạng thái | Phiên bản M365 | Lần đồng bộ cuối`;
- right rail `Thông tin Release | Tính toàn vẹn bản phát hành | Lịch sử phát hành | Hành động`;
- immutable notice.

Primary CTA: `Về Tổng quan hồ sơ`. Secondary: xem Release Manifest, mở tài liệu, xem lịch sử/lineage. Không edit/unlock/rollback/replace release, không Export PDF.

Sau success: Global Case State canonical stage = `PUBLISHED`, terminal/completed, `next_action = null`. Muốn thay đổi sau phát hành phải tạo revision mới, revalidate/sync và phát hành release mới; release cũ immutable.

## 1.3 Cross-product Empty / Loading / Error / Retry — Baseline Contract v1
Contract này là state-presentation + recovery authority dùng chung cho toàn VALORA và không thay thế Error Registry hiện hành. Error Registry sở hữu Vietnamese-friendly message payload; Cross-product State Contract sở hữu classification, scope, surface, recovery action và preserve/replace behavior.

Canonical states:
`INITIAL_LOADING | SECTION_LOADING | BACKGROUND_REFRESH | PROCESSING | EMPTY_FIRST_USE | EMPTY_NO_RESULTS | EMPTY_NOT_APPLICABLE | EMPTY_COMPLETED | INLINE_ERROR | SECTION_ERROR | PAGE_ERROR | FATAL_ERROR | STALE_DATA | VERSION_CONFLICT | OFFLINE | RECONNECTING | PARTIAL_SUCCESS`.

Loading authority:
- initial load chỉ khi chưa có usable data;
- section load chỉ thay đúng section;
- background refresh giữ usable data;
- Loading khác Processing;
- durable/long-running jobs dùng lifecycle `queued | running | retrying | completed | failed | cancelled`, có current step/progress thật nếu có, không tạo % giả và không spinner vô hạn.

Empty authority:
- First Use = chưa từng có dữ liệu;
- No Results = filter/search không khớp;
- Not Applicable = capability không áp dụng;
- Completed = không còn item cần xử lý vì đã hoàn tất;
- Empty không bao giờ che Error.

Error authority:
- inline/section/page/fatal theo phạm vi thực tế;
- lỗi một section không collapse toàn page nếu phần khác còn dùng được;
- technical detail không là primary user-facing copy.

Retry/concurrency authority:
- retry phải thật và đúng scope;
- read thường có thể retry;
- mutation không blind retry khi commit status chưa xác định;
- `409 → reload/reconcile → review nếu cần → explicit commit lại`, không last-write-wins;
- client timeout của write không đồng nghĩa domain failure.

Preserve/partial/connectivity authority:
- usable old data + refresh failure → giữ old data + stale/error indicator + Retry;
- partial failure giữ phần thành công và retry chỉ phần retryable nếu domain cho phép;
- Offline giữ view/local draft phù hợp nhưng disable official mutations cần server confirmation; không fake success; reconnect phải refresh/revalidate trước khi re-enable commit.

Surface selection:
`field/action nhỏ → inline | section lỗi → section error/inline alert | page notice còn thao tác được → banner | success ngắn hạn → toast | conflict cần quyết định → dialog/drawer | empty → Empty State | capability chính lỗi → Page Error`.

Cross-product hard invariants:
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

Visual baseline `Cross-product State Pattern Board — Iteration 1` là design-system authority dùng chung, không phải workflow checkpoint hay màn nghiệp vụ độc lập.

## 1.4 Microsoft 365 Return / Revalidation — Baseline Contract v1
Contract này khóa hành vi khi user `Mở trong Word` rồi quay lại VALORA. Return/Revalidation là integration/state contract, không phải workflow checkpoint và không phải business commit.

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

Three-way Managed Region semantics với `Old = snapshot/lần sync đã bind`, `V = VALORA hiện tại`, `W = Word hiện tại`:
- `V=Old, W=Old` → không đổi;
- `V=Old, W!=Old` → Word-only edit, bảo toàn Word, không silent overwrite;
- `V!=Old, W=Old` → VALORA-only change, `Cần cập nhật`, không conflict;
- `V!=Old, W!=Old` và V/W khác semantic value → conflict cần explicit decision;
- V/W hội tụ cùng semantic value có thể non-conflict nếu implementation giữ audit/lineage đầy đủ.

Hard rules:
- quay lại VALORA không đồng nghĩa Word đã đổi;
- revalidation có usable data dùng `BACKGROUND_REFRESH`, không blank page;
- M365 version mới không tự tạo Document Revision;
- thay đổi ngoài Managed Region không mặc định conflict;
- user edit trong Managed Region không silent overwrite;
- không tự bind file thay thế chỉ theo filename;
- không fake `Đã đồng bộ`/`Sẵn sàng phát hành` khi freshness chưa xác minh;
- reconnect phải revalidate trước official mutation phụ thuộc freshness;
- published revision/release immutable.

Sync/Publishing phải dùng freshness đủ theo policy. Revalidation result feed vào document/release readiness và Global Case State `stale/blocking/next_action`; frontend không dựng workflow truth riêng. Visual M365 Return/Revalidation chưa được chốt; mockup tiếp theo mặc định Design Proposal / Iteration.

## 2. Price & Evidence
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính. NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% Warning; không Blocking. Dữ liệu trong Kho tri thức chỉ là hỗ trợ/tra cứu và không override price-source authority này.

### 2.1 Chọn NCC đã xác nhận giá — Baseline Iteration 1
`Chọn NCC đã xác nhận giá` là checkpoint sau `Hoàn tất từng báo giá NCC` và trước `Kết quả thẩm định giá`.

Selection scope: `1 Project + 1 ProjectAssetLine + 1 confirmed QuoteLine = 1 current NCC Selection`.
Selection là project-line context. Đổi NCC tạo revision mới và giữ lịch sử. Quote revision/source thay đổi không auto-rebind; selection chuyển `Cần xem lại` đến khi user explicit xác nhận lại.

Eligibility: đúng dòng tài sản; NCC xác định; đơn giá hợp lệ; báo giá hoàn tất/xác nhận; evidence/source truy xuất được. Warning không Blocking; quote chưa hoàn tất/evidence lỗi không eligible.

Warning surface: `Đơn giá hiện hành | Giá NCC | Chênh lệch | Chênh lệch % | Warning`.
- Giá NCC < current → luôn Warning.
- `abs(diff)/current > 15%` → Warning.
- Giá NCC >115% current → Warning.
- Current bằng 0/chưa có: không tính phần trăm giả.

Layout: KPI + filter/search + table-first + drawer `Danh sách báo giá đủ điều kiện | Thông tin chọn hiện tại | Lịch sử chọn`; evidence + comparison + warning. Primary commit CTA `Xác nhận NCC đã chọn`. AI không auto-select. Selection không tự tạo/sửa `AppraisedPriceDecision`, không ghi đè giá Kết quả thẩm định, không đổi price-source priority.

## 3. Kết quả thẩm định giá
Ba bảng công ty là immutable về cấu trúc:
1. `STT | Tên tài sản | Đặc điểm KTKT | ĐVT | SL`
2. `STT | Tên tài sản | ĐVT | SL | NCC1 | NCC2 | NCC3 | Tổ TĐG đánh giá: Đơn giá | Thành tiền`
3. `STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền`
Giữ Tổng cộng/Làm tròn/Số tiền bằng chữ; không rename/reorder/cardize.

## 4. Knowledge Management
Supporting workspace: `Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`. Structured KTKT là business data; template/Microsoft 365 sở hữu presentation. Historical dossier là candidate pipeline, không direct-inject active knowledge. Knowledge review cần explicit human decision. History/lineage read-oriented, không edit/delete/rollback/activate knowledge.

## 5. Microsoft 365 / Documents
VALORA sở hữu structured data, Data Snapshot, lineage, audit, sync status, Document Revision, Release Manifest. Microsoft 365 sở hữu Word file/OneDrive-SharePoint file/version. Document Revision != M365 file version. Managed Region không silent overwrite; conflict phải explicit resolve. Published revision/release immutable.

Return/Revalidation authority: external Word return phải revalidate M365 state trước mutation phụ thuộc freshness; M365 version mới không tự tạo Document Revision; Managed Region changes dùng three-way semantics và explicit conflict handling khi cần.

## 6. Publishing
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit boundary] → Release Manifest + locked revisions + audit [system consequence] → Đã phát hành [success/read-only result]`.
`Đã phát hành` không phải step thao tác mới. Không màn khóa riêng, không Export PDF.

## 7. Guardrails
Single-user; Vietnamese-first; Fluent 2; desktop-first; data-heavy/table-first; AI advisory; human-confirmed official decisions; không silent bypass/publish/overwrite/state transition/stale reconciliation; không fake Word/Excel editor; không Export PDF; published revision/release immutable; một primary CTA/recovery CTA mỗi context.
