# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 01/09/2026 — `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_CASE_OVERVIEW_ORCHESTRATION_BASELINE_ADDENDUM.md` — **Baseline `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`**.
3. `VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md` — Baseline `Chọn NCC đã xác nhận giá — Iteration 1`.
4. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_LINEAGE_HISTORY_BASELINE_ADDENDUM.md` — Baseline `Lịch sử & nguồn gốc — Iteration 1`.
5. `VALORA_UIUX_HANDOFF_v2.3_HISTORICAL_DOSSIER_BASELINE_ADDENDUM.md` — Baseline `Hồ sơ cũ — Iteration 1`.
6. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_REVIEW_BASELINE_ADDENDUM.md` — Baseline `Cần rà soát tri thức — Iteration 1`.
7. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md` — Baseline `Quản lý Kho tri thức — Iteration 1`.
8. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — Baseline Xác nhận phát hành.
9. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
10. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
11. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
12. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Tổng quan hồ sơ / orchestration authority
`Tổng quan hồ sơ` là project-level orchestration hub. Không tạo màn `Tiến độ hồ sơ` riêng.

Global Case State projection tổng hợp Project + WorkflowInstance + domain completion facts + ValidationIssue + document/release state + last meaningful context. `Project.status` hoặc `WorkflowInstance.current_state` không tự động là UI route authority.

Canonical Case Stage v1 gồm 16 stage từ preliminary request đến published; UI dùng nhãn nghiệp vụ tiếng Việt. Completion derive từ mandatory business facts, không từ màn đã mở. Supporting Knowledge Management không phải mandatory completion step.

Một hồ sơ có một primary next-action. Precedence: Blocking → stale cần review → công việc đang dở hợp lệ → bước bắt buộc chưa hoàn tất gần nhất → bước tiếp theo north-star → Published/no action. Next-action là system-derived projection, không phải AI decision. AI chỉ giải thích.

Resume Target ưu tiên last meaningful context còn hợp lệ, nhưng blocker/stale mới có thể thắng. Resume không phải business commit, không bypass blocker và last visited route không mặc định là resume authority.

Layout baseline: trạng thái hồ sơ + completion/health; 16-step mandatory progress; group progress; blockers; warnings; information/statistics; right rail `Hành động tiếp theo | Ngữ cảnh hồ sơ (Resume Target) | Hoạt động gần đây`; một primary CTA trong next-action context.

## 3. NCC Selection authority
### 3.1 Chọn NCC đã xác nhận giá — Baseline Iteration 1
`Chọn NCC đã xác nhận giá` là checkpoint sau `Hoàn tất từng báo giá NCC` và trước `Kết quả thẩm định giá`.

Selection scope: `1 Project + 1 ProjectAssetLine + 1 confirmed QuoteLine = 1 current NCC Selection`.
Selection là project-line context. Đổi NCC tạo revision mới và giữ lịch sử. Quote revision mới không auto-rebind; selection chuyển `Cần xem lại` cho đến khi user explicit xác nhận lại.

Warning contract: `Đơn giá hiện hành | Giá NCC | Chênh lệch | Chênh lệch % | Warning`.
- NCC thấp hơn đơn giá hiện hành → luôn Warning.
- `abs(diff)/current > 15%` → Warning.
- NCC >115% đơn giá hiện hành → Warning.
- Warning không Blocking.

Primary commit CTA: `Xác nhận NCC đã chọn`. AI không auto-select. Selection không tự tạo/sửa `AppraisedPriceDecision`, không ghi đè đơn giá thẩm định và không đổi price-source priority.

## 4. Knowledge Management authority
`Quản lý Kho tri thức` là supporting workspace độc lập với panel tra cứu trong Workbench.
IA: `Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`.
Structured KTKT là business data; report presentation thuộc template công ty/Microsoft 365. Historical knowledge không override price-source authority.

### 4.1 Lịch sử & nguồn gốc
Read-oriented knowledge-governance traceability surface trên `IdentityDecisionLog`, `KnowledgeVersion`, `KnowledgeLineage`; không tạo audit/version subsystem mới. Không commit CTA/edit/delete/restore/rollback/approve/activate knowledge.

### 4.2 Hồ sơ cũ
Historical candidate pipeline: nhập hồ sơ → phân loại → trích xuất → ghép khớp → rà soát → tạo candidate → Cần rà soát tri thức → human decision → official/versioned knowledge. Không direct-inject active knowledge.

### 4.3 Cần rà soát tri thức
Human review queue. `Xác nhận | Chỉnh sửa rồi xác nhận | Không phù hợp | Để xử lý sau`; confidence không auto-approve; provenance/history luôn giữ.

## 5. Publishing routing authority — complete
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit boundary] → Release Manifest + khóa revision + audit [system consequence]`.
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

## 6. Guardrails
- Single-user.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- AI advisory; human-confirmed official decisions.
- Không silent bypass/publish/overwrite/knowledge activation/state transition/stale reconciliation.
- Không revive KSCL/QC/multi-level approval từ legacy workflow commands.
- NCC Selection không auto-select/rebind và không override appraisal price.
- Không fake Word/Excel editor; không export PDF.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 7. ADR
Global Case State projection/resume persistence nếu implementation thay đổi persistence/architecture; NCC-selection persistence/revision/stale semantics; DossierBundle/source-role; extraction/table-role; row-alignment; candidate transaction/jobs; knowledge activation/versioning/lineage; Managed Region merge; Release Manifest transaction semantics cần ADR phù hợp.
