# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Cần rà soát tri thức — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_REVIEW_BASELINE_ADDENDUM.md` — **Baseline `Cần rà soát tri thức — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md` — Baseline `Quản lý Kho tri thức — Iteration 1`.
4. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — Baseline Xác nhận phát hành.
5. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
6. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
7. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
8. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Knowledge Management authority
`Quản lý Kho tri thức` là supporting workspace độc lập với panel tra cứu trong Workbench.

IA:
```text
Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc
```

Structured KTKT là business data; report presentation thuộc template công ty/Microsoft 365. Historical knowledge không override price-source authority.

### 2.1 Cần rà soát tri thức — Baseline Iteration 1
`Cần rà soát` là human-review queue cho identity/contextual-alias/KTKT/knowledge candidates. Candidate không trở thành official knowledge nếu chưa có explicit human decision.

Layout: candidate list bên trái; candidate/structured comparison ở giữa; report preview view-only + note/history bên phải; decision bar phía dưới.

Decision semantics:
`Xác nhận | Chỉnh sửa rồi xác nhận | Không phù hợp | Để xử lý sau`.

- Confidence/độ ưu tiên chỉ hỗ trợ review, không auto-approve.
- Confirm là explicit human commit.
- Edit+confirm giữ source/candidate lineage và giá trị cuối đã xác nhận.
- Reject không xóa evidence/provenance.
- Defer không được coi là official knowledge.
- Khi tri thức hiện hữu có liên quan, user phải có surface so sánh; không silent overwrite.
- Decision phải có history/lineage/audit.
- AI/system không impersonate human confirmation.

Preview KTKT tiếp tục theo authority Báo cáo công ty, view-only, không fake Word editor.

## 3. Publishing routing authority — complete
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ Release Manifest + khóa revision + audit [system consequence]
```
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

## 4. Guardrails
- Single-user.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- AI advisory; human-confirmed official decisions.
- Không silent bypass/publish/overwrite/knowledge activation.
- Không auto-approve knowledge candidate.
- Không fake Word editor.
- Không export PDF.
- Historical knowledge không override v2.3 price-source authority.
- Structured KTKT = business data; report formatting = company template authority.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 5. ADR
Knowledge review queue/candidate lifecycle/decision log/activation/versioning, attribute persistence, lineage, presentation mapping, Managed Region merge semantics và Release Manifest transaction semantics cần ADR nếu implementation thay đổi persistence/architecture.
