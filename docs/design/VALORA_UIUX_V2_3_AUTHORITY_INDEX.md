# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Xác nhận & Đồng bộ hàng loạt — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_CONFIRM_EXECUTE_BASELINE_ADDENDUM.md` — **Baseline `Xác nhận & Đồng bộ hàng loạt — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md` — Baseline Xử lý xung đột khi đồng bộ.
4. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md` — Baseline Xem trước kết quả đồng bộ.
5. `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md` — Baseline Đồng bộ dữ liệu hàng loạt.
6. Các addendum Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Result/NCCQ hiện hành.
7. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Xem trước kết quả [zero-write]
→ Xử lý xung đột nếu có [zero-write]
→ Xác nhận & Đồng bộ [WRITE BOUNDARY]
→ Kết quả đồng bộ hàng loạt
```

## 3. Confirm & Execute baseline
Đây là execution gate. Layout: summary final scope; bảng phạm vi cuối cùng; panel Blocking/Warning/conflict/readiness + snapshot info; warning banner; footer với primary `Xác nhận & Đồng bộ`.

CTA chỉ enabled khi Blocking=0, conflict bắt buộc đã xử lý, sync plan chưa stale. Nếu Word/Data Snapshot đổi sau preview thì phải review lại.

Execution chỉ ghi Managed Regions theo final sync plan. `Giữ Word` không overwrite; `Bỏ qua` không ghi và không coi đã đồng bộ; `Không thay đổi` không revision. Mỗi tài liệu cập nhật thành công tạo Document Revision mới + Microsoft 365 version tương ứng. Published revision/release immutable.

Batch result phải theo từng tài liệu; không dùng một success chung nếu có partial failure.

## 4. Conflict / Preview authority
Conflict so sánh Snapshot cũ / VALORA mới / Word hiện tại; user quyết định explicit. Preview và conflict screen đều zero-write.

## 5. Guardrails
- Single-user; AI advisory.
- Không silent overwrite/sync/conflict resolution.
- Không fake Word editor.
- Không revision cho unchanged/skipped docs.
- Document Revision != Microsoft 365 file version.
- Vietnamese-first; một primary CTA mỗi context.

## 6. ADR
Multi-document transaction, partial success/rollback, retry/idempotency, stale-plan/concurrency, revision creation và audit/lineage cần ADR nếu implementation thay đổi persistence/architecture.
