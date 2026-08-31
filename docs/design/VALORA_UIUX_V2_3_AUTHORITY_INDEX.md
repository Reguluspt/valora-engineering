# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Xem lại & xử lý ngoại lệ — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — **Baseline `Xem lại & xử lý ngoại lệ — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
4. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_RESULT_BASELINE_ADDENDUM.md` — Baseline Kết quả đồng bộ hàng loạt.
5. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
6. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Publishing routing authority — simplified
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành
→ hệ thống tạo Release Manifest + khóa các revision đã phát hành
```
Flow 5 bước cũ bị supersede. Không còn UI riêng `Khóa phiên bản`. Không `Xuất PDF`.

## 3. Release Exception Review baseline
Exception-first: tài liệu `Sẵn sàng` không nằm trong task list; user chỉ tập trung `Cần xem lại / Có lỗi / Cảnh báo`.

Layout: summary ngoại lệ; trái danh sách/filter; giữa preview view-only lớn + highlight + Open in Word; phải chi tiết nguyên nhân, sync/revision và action; footer progress + primary `Tiếp tục: Xác nhận phát hành`.

Semantics:
- Blocking/error → phải sửa/revalidate hoặc loại khỏi release; không silent bypass.
- Cần xem lại → user review/decision theo rule.
- Warning → không tự Blocking; có thể giữ sau explicit review.
- Ready → không phải task tại màn này.

Actions: `Mở tài liệu để cập nhật` / `Loại khỏi bộ phát hành` / `Giữ nguyên và phát hành` (chỉ non-Blocking). Sau Word edit phải revalidate.

Completion gate: mọi Blocking trong release scope đã xử lý hoặc tài liệu đã loại; release plan không stale; quyết định bắt buộc đã ghi nhận. Màn này chưa publish/lock/finalize Release Manifest.

## 4. Release Preparation baseline
VALORA auto-select revision mới nhất đủ điều kiện; user chủ yếu review ngoại lệ. Auto-select không đồng nghĩa auto-publish.

## 5. Guardrails
- Single-user; AI advisory.
- Exception-first UX.
- Không silent bypass/publish/overwrite.
- Không fake Word editor.
- Không export PDF.
- Release Manifest bind đúng Document Revisions đã chọn.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 6. ADR
Exception-decision persistence, release-plan stale detection, revalidation after Word edit, exclusion semantics, Release Manifest binding/locking transaction cần ADR nếu implementation thay đổi persistence/architecture.
