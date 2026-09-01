# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 01/09/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa Publishing simplified flow, `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`, `Chọn NCC đã xác nhận giá — Iteration 1`, `Quản lý Kho tri thức — Iteration 1`, `Cần rà soát tri thức — Iteration 1`, `Hồ sơ cũ — Iteration 1` và `Lịch sử & nguồn gốc — Iteration 1`. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian, màn rule-check giá riêng hoặc màn Tiến độ hồ sơ riêng.

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
      → khi dữ liệu thay đổi: Bulk Sync loop
      → Tải lên mẫu tùy biến → AI mapping → Test fill → Xác nhận & Lưu template
   → Báo cáo / Chứng thư: child-flow chuyên sâu khi cần
   → Publishing
      → Chuẩn bị bộ phát hành
      → Xem lại & xử lý ngoại lệ
      → Xác nhận phát hành [commit boundary]
      → Release Manifest + khóa revision + audit [system consequence]

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

## 6. Publishing
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit boundary] → Release Manifest + locked revisions + audit [system consequence]`.
Không màn khóa riêng, không Export PDF.

## 7. Guardrails
Single-user; Vietnamese-first; Fluent 2; desktop-first; data-heavy/table-first; một primary CTA/context. AI advisory; human explicit commit cho official decisions. Không KSCL/multi-level approval, S14, NCCQ aggregate, separate rule-check, fake Word/Excel editor, silent overwrite/publish/knowledge activation/state transition/stale reconciliation.
