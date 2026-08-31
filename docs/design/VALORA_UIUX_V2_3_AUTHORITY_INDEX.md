# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Kết quả đồng bộ hàng loạt — Iteration 1` (không có luồng xuất PDF).

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_RESULT_BASELINE_ADDENDUM.md` — **Baseline `Kết quả đồng bộ hàng loạt — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_CONFIRM_EXECUTE_BASELINE_ADDENDUM.md` — Baseline Xác nhận & Đồng bộ hàng loạt.
4. `VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md` — Baseline Xử lý xung đột khi đồng bộ.
5. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md` — Baseline Xem trước kết quả đồng bộ.
6. `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md` — Baseline Đồng bộ dữ liệu hàng loạt.
7. Các addendum Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Result/NCCQ hiện hành.
8. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Xem trước kết quả [zero-write]
→ Xử lý xung đột nếu có [zero-write]
→ Xác nhận & Đồng bộ [WRITE BOUNDARY]
→ Kết quả đồng bộ hàng loạt
   → Xem & quản lý revision
   hoặc → Quay lại workspace
```

## 3. Bulk Sync Result baseline
Đây là post-execution result screen. Layout: summary `Đã đồng bộ / Không thay đổi / Bỏ qua / Lỗi / Tổng tài liệu`; bảng kết quả theo từng tài liệu; panel tổng quan phiên; breakdown kết quả; primary `Xem & quản lý revision`.

Semantics:
- `Đã đồng bộ` → tài liệu cập nhật thành công, có Document Revision mới + Microsoft 365 version tương ứng.
- `Không thay đổi` → không ghi, không revision mới.
- `Bỏ qua` → không ghi lần này, không revision mới, không coi là đã đồng bộ.
- `Lỗi` → chưa hoàn tất; phải xem chi tiết/retry sau khi xử lý.

Không dùng success chung để che partial failure. Retry phải revalidate trạng thái hiện tại; không mặc định replay sync plan cũ nếu stale.

**Không có luồng xuất PDF tại màn Kết quả đồng bộ.** Mockup/authority cũ có `Báo cáo tóm tắt (PDF)` bị supersede. Publishing authority cũng tiếp tục không có `Xuất PDF`.

## 4. Confirm / Conflict / Preview authority
Confirm & Sync là write boundary. Preview và conflict zero-write. Conflict so sánh Snapshot cũ / VALORA mới / Word hiện tại; user quyết định explicit.

## 5. Guardrails
- Single-user; AI advisory.
- Không silent overwrite/sync/retry/conflict resolution.
- Không fake Word editor.
- Không revision cho unchanged/skipped/failed nếu chưa cập nhật thành công.
- Không export PDF trong baseline result/publishing.
- Document Revision != Microsoft 365 file version.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 6. ADR
Partial-success model, retry/idempotency, recovery semantics, stale-plan revalidation, result persistence và revision/version creation cần ADR nếu implementation thay đổi persistence/architecture.
