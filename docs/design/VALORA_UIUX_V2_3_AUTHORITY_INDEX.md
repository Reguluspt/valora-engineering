# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 01/09/2026 — `M365 Return & Revalidation — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_VISUAL_BASELINE_ADDENDUM.md` — **Baseline visual `M365 Return & Revalidation — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_M365_RETURN_REVALIDATION_CONTRACT_ADDENDUM.md` — **Baseline `Microsoft 365 Return / Revalidation Contract v1`**; semantic authority thắng nếu visual wording minh họa khác contract.
4. `VALORA_UIUX_HANDOFF_v2.3_CROSS_PRODUCT_STATE_PATTERN_BASELINE_ADDENDUM.md` — Baseline `Cross-product Empty / Loading / Error / Retry Contract v1` + `Cross-product State Pattern Board — Iteration 1`.
5. `VALORA_UIUX_HANDOFF_v2.3_POST_PUBLISH_SUCCESS_BASELINE_ADDENDUM.md` — Baseline `Đã phát hành — Iteration 1`.
6. `VALORA_UIUX_HANDOFF_v2.3_CASE_OVERVIEW_ORCHESTRATION_BASELINE_ADDENDUM.md` — Baseline `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`.
7. `VALORA_UIUX_HANDOFF_v2.3_NCC_SELECTION_BASELINE_ADDENDUM.md` — Baseline `Chọn NCC đã xác nhận giá — Iteration 1`.
8. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_LINEAGE_HISTORY_BASELINE_ADDENDUM.md` — Baseline `Lịch sử & nguồn gốc — Iteration 1`.
9. `VALORA_UIUX_HANDOFF_v2.3_HISTORICAL_DOSSIER_BASELINE_ADDENDUM.md` — Baseline `Hồ sơ cũ — Iteration 1`.
10. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_REVIEW_BASELINE_ADDENDUM.md` — Baseline `Cần rà soát tri thức — Iteration 1`.
11. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md` — Baseline `Quản lý Kho tri thức — Iteration 1`.
12. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — Baseline Xác nhận phát hành.
13. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
14. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
15. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
16. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Microsoft 365 Return / Revalidation authority
Semantic contract + visual baseline hiện đã khóa.

Canonical flow:
`Mở trong Word → ghi nhận handoff context → return/focus/explicit refresh/action cần freshness → BACKGROUND_REFRESH → revalidate M365 state → classify → derive sync/readiness → continue/review/conflict/recovery`.

Canonical classifications:
`NO_CHANGE | EXTERNAL_CHANGE_OUTSIDE_MANAGED | EXTERNAL_CHANGE_IN_MANAGED | FILE_REPLACED_OR_MOVED | ACCESS_UNAVAILABLE`.

Visual baseline `M365 Return & Revalidation — Iteration 1` gồm high-level return flow, 5 outcome cards, state UI examples, three-way comparison, conflict decision surface, background revalidation indicator và mandatory principles. Đây là integration/state pattern, không phải workflow checkpoint.

Hard semantics: quay lại không đồng nghĩa Word đã đổi; M365 version mới không tự tạo Document Revision; ngoài Managed Region không mặc định conflict; user edit trong Managed Region không silent overwrite; conflict dùng three-way semantics `Old snapshot | VALORA current | Word current`; không fake sync/publish readiness khi freshness chưa xác minh; published revision/release immutable; reconnect phải revalidate trước mutation phụ thuộc freshness.

Revalidation feed vào document/release readiness và Global Case State stale/blocking/next-action. Frontend không dựng workflow truth riêng. Nếu wording minh họa của visual mâu thuẫn semantic contract, contract thắng.

## 3. Cross-product state authority
`Cross-product Empty / Loading / Error / Retry Contract v1` là state-presentation và recovery authority dùng chung toàn VALORA. Nó không thay Error Registry; Error Registry vẫn là message authority, còn State Contract phân loại state, scope, surface, recovery action và preserve/replace behavior.

Canonical states:
`INITIAL_LOADING | SECTION_LOADING | BACKGROUND_REFRESH | PROCESSING | EMPTY_FIRST_USE | EMPTY_NO_RESULTS | EMPTY_NOT_APPLICABLE | EMPTY_COMPLETED | INLINE_ERROR | SECTION_ERROR | PAGE_ERROR | FATAL_ERROR | STALE_DATA | VERSION_CONFLICT | OFFLINE | RECONNECTING | PARTIAL_SUCCESS`.

Hard invariants: Empty không che Error; Loading khác Processing; usable data không blank khi refresh; retry phải thật/đúng scope; mutation không blind retry khi commit chưa xác định; 409 không last-write-wins; partial failure giữ phần thành công; Warning không tự thành Blocking; Offline không fake success; local draft không đồng nghĩa persisted; technical detail không phải primary copy; search error không là No Results; không spinner vô hạn cho durable job; frontend không dựng fallback business state machine khi API/projection authority lỗi; một primary recovery CTA/context.

## 4. Post-Publish Success authority
`Đã phát hành` là success/read-only result state sau `Xác nhận phát hành` commit thành công, không phải bước thứ 4 của Publishing. UI chỉ hiển thị khi Release Manifest final commit hợp lệ. Published release/revisions immutable; muốn thay đổi phải tạo revision/release mới.

## 5. Tổng quan hồ sơ / orchestration authority
`Tổng quan hồ sơ` là project-level orchestration hub. Global Case State derive từ business facts; completion không từ màn đã mở; một primary next-action; resume target không bypass blocker/stale; frontend không tự dựng workflow state machine.

## 6. NCC Selection authority
`Chọn NCC đã xác nhận giá` là checkpoint sau hoàn tất báo giá NCC và trước Kết quả thẩm định giá. Selection là project-line context; đổi NCC tạo revision mới; Warning không Blocking; selection không override appraisal price.

## 7. Knowledge Management authority
Supporting workspace: `Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`. Structured KTKT là business data; historical dossier là candidate pipeline; knowledge review cần explicit human decision; history/lineage read-only.

## 8. Publishing routing authority — complete
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành [commit boundary] → Release Manifest + khóa revision + audit [system consequence] → Đã phát hành [success/read-only result]`.
Không UI khóa riêng. Không Export PDF.

## 9. Guardrails
- Single-user.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- AI advisory; human-confirmed official decisions.
- Không silent bypass/publish/overwrite/knowledge activation/state transition/stale reconciliation.
- Không silent retry mutation khi commit status chưa xác định.
- Không revive KSCL/QC/multi-level approval từ legacy workflow commands.
- Không fake Word/Excel editor; không export PDF.
- Published revision/release immutable.
- Một primary CTA/recovery CTA mỗi context.

## 10. ADR
Global Case State projection/resume persistence; cross-product durable processing/job identity; post-publish projection; Release Manifest transaction/locking/idempotency/recovery; NCC-selection persistence/revision/stale; DossierBundle/extraction/row-alignment; knowledge activation/versioning/lineage; Managed Region merge semantics; M365 file identity/version binding, webhook/change notification, managed-region fingerprint/diff, freshness policy và revalidation audit persistence cần ADR nếu implementation thay đổi persistence/architecture.
