# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 01/09/2026 — `Đã phát hành — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_POST_PUBLISH_SUCCESS_BASELINE_ADDENDUM.md` — **Baseline `Đã phát hành — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_CASE_OVERVIEW_ORCHESTRATION_BASELINE_ADDENDUM.md` — Baseline `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`.
4. `VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md` — Baseline `Chọn NCC đã xác nhận giá — Iteration 1`.
5. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_LINEAGE_HISTORY_BASELINE_ADDENDUM.md` — Baseline `Lịch sử & nguồn gốc — Iteration 1`.
6. `VALORA_UIUX_HANDOFF_v2.3_HISTORICAL_DOSSIER_BASELINE_ADDENDUM.md` — Baseline `Hồ sơ cũ — Iteration 1`.
7. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_REVIEW_BASELINE_ADDENDUM.md` — Baseline `Cần rà soát tri thức — Iteration 1`.
8. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md` — Baseline `Quản lý Kho tri thức — Iteration 1`.
9. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — Baseline Xác nhận phát hành.
10. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
11. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
12. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
13. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Post-Publish Success authority
`Đã phát hành` là success/read-only result state sau `Xác nhận phát hành` commit thành công. Đây không phải bước thứ 4 của Publishing và không phải workflow checkpoint mới.

Flow:
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit] → Release Manifest + khóa revision + audit [system consequence] → Đã phát hành [read-only result]`.

UI chỉ hiển thị `Đã phát hành` khi Release Manifest final commit hợp lệ. Success surface phải phản ánh Release ID thật, thời điểm/người phát hành, manifest items, locked Document Revisions, M365 version references nếu có, retained warnings và audit/lineage.

Layout baseline: success banner + release summary + completed publishing progress + integrity/warning summary + table `Tên tài liệu | Loại tài liệu | Document Revision đã phát hành | Trạng thái | Phiên bản M365 | Lần đồng bộ cuối` + right rail `Thông tin Release | Tính toàn vẹn | Lịch sử phát hành | Hành động`.

Primary CTA: `Về Tổng quan hồ sơ`. Secondary: xem Release Manifest, mở tài liệu, lịch sử/lineage. Không edit/unlock/rollback/replace release, không Export PDF.

Global Case State sau thành công: canonical stage `PUBLISHED`, terminal/completed, `next_action = null`; published release/revisions immutable. Muốn thay đổi phải tạo revision mới và release mới.

## 3. Tổng quan hồ sơ / orchestration authority
`Tổng quan hồ sơ` là project-level orchestration hub. Không tạo màn `Tiến độ hồ sơ` riêng.

Global Case State projection tổng hợp Project + WorkflowInstance + domain completion facts + ValidationIssue + document/release state + last meaningful context. `Project.status` hoặc `WorkflowInstance.current_state` không tự động là UI route authority.

Canonical Case Stage v1 gồm 16 stage từ preliminary request đến published; UI dùng nhãn nghiệp vụ tiếng Việt. Completion derive từ mandatory business facts, không từ màn đã mở. Supporting Knowledge Management không phải mandatory completion step.

Một hồ sơ có một primary next-action. Precedence: Blocking → stale cần review → công việc đang dở hợp lệ → bước bắt buộc chưa hoàn tất gần nhất → bước tiếp theo north-star → Published/no action. Next-action là system-derived projection, không phải AI decision. AI chỉ giải thích.

Resume Target ưu tiên last meaningful context còn hợp lệ, nhưng blocker/stale mới có thể thắng. Resume không phải business commit, không bypass blocker và last visited route không mặc định là resume authority.

## 4. NCC Selection authority
`Chọn NCC đã xác nhận giá` là checkpoint sau `Hoàn tất từng báo giá NCC` và trước `Kết quả thẩm định giá`. Selection là project-line context; đổi NCC tạo revision mới; quote revision mới không auto-rebind. Warning không Blocking. Primary commit CTA `Xác nhận NCC đã chọn`; selection không override appraisal price.

## 5. Knowledge Management authority
Supporting workspace: `Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`. Structured KTKT là business data; report presentation thuộc template công ty/Microsoft 365. Historical knowledge không override price-source authority. Không direct-inject active knowledge; knowledge review cần explicit human decision; history/lineage read-only.

## 6. Publishing routing authority — complete
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit boundary] → Release Manifest + khóa revision + audit [system consequence] → Đã phát hành [success/read-only result]`.
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

## 7. Guardrails
- Single-user.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- AI advisory; human-confirmed official decisions.
- Không silent bypass/publish/overwrite/knowledge activation/state transition/stale reconciliation.
- Không revive KSCL/QC/multi-level approval từ legacy workflow commands.
- Không fake Word/Excel editor; không export PDF.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 8. ADR
Global Case State projection/resume persistence; post-publish published-state projection; Release Manifest transaction/locking/idempotency/recovery; NCC-selection persistence/revision/stale; DossierBundle/extraction/row-alignment; knowledge activation/versioning/lineage; Managed Region merge semantics cần ADR nếu implementation thay đổi persistence/architecture.
