# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Xác nhận phát hành — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — **Baseline `Xác nhận phát hành — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
4. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
5. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
6. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Publishing routing authority — complete
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ Release Manifest + khóa revision + audit [system consequence]
```
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

## 3. Release Confirmation baseline
Màn cuối hiển thị thông tin phát hành dự kiến, tóm tắt tài liệu/revision/cảnh báo/loại khỏi release, danh sách tài liệu, ngoại lệ đã xử lý, integrity/readiness checks và hệ quả sau phát hành.

Commit gate: Blocking=0; ngoại lệ bắt buộc đã xử lý; revision hợp lệ; release plan không stale; không unresolved version conflict; tài liệu giữ trong release đạt readiness. Thay đổi sau review phải revalidate.

CTA `Xác nhận phát hành` là explicit commit. Thành công → tạo Release Manifest final bind đúng Document Revisions, khóa revision trong release, ghi audit/lineage. Tài liệu bị loại không thuộc manifest và không bị khóa.

Release ID trước commit là dự kiến/reserved; ID trên mockup không phải schema cứng. Không được báo thành công nếu manifest chưa commit hợp lệ.

## 4. Release Exception Review baseline
Exception-first; Blocking phải sửa/revalidate hoặc loại; Warning không tự Blocking; màn này chưa publish.

## 5. Release Preparation baseline
Auto-select ready revision; không auto-publish.

## 6. Guardrails
- Single-user.
- Explicit final confirmation; không auto-publish.
- Không silent bypass/publish.
- Không fake Word editor.
- Không export PDF.
- Lock revision là system consequence.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 7. ADR
Release Manifest transaction boundary, Release ID reservation, locking atomicity, retry/idempotency, failure recovery, audit commit semantics và các release-plan persistence semantics cần ADR nếu implementation thay đổi persistence/architecture.
