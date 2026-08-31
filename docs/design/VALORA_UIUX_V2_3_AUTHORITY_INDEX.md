# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Xử lý xung đột khi đồng bộ — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_SYNC_CONFLICT_RESOLUTION_BASELINE_ADDENDUM.md` — **Baseline `Xử lý xung đột khi đồng bộ — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md` — Baseline Xem trước kết quả đồng bộ.
4. `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md` — Baseline Đồng bộ dữ liệu hàng loạt.
5. Các addendum Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Result/NCCQ hiện hành.
6. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Xem trước kết quả [zero-write]
→ nếu có conflict: Xử lý xung đột
   → chọn tài liệu/vùng
   → so sánh Snapshot cũ / VALORA mới / Word hiện tại
   → user quyết định từng vùng
   → cập nhật sync plan [vẫn zero-write]
→ Xác nhận & Đồng bộ
```
Nếu không có conflict thì bỏ qua bước Xử lý xung đột.

## 3. Conflict Resolution baseline
Conflict = cùng Managed Region vừa thay đổi ở dữ liệu VALORA vừa được user chỉnh trong Word kể từ snapshot/lần sync trước. Không bên nào auto-win.

Layout: trái conflict list; giữa preview Word lớn highlight vùng; phải so sánh ba giá trị và lựa chọn; footer progress + primary `Áp dụng quyết định & quay lại xác nhận đồng bộ`.

Lựa chọn từng vùng: `Dùng dữ liệu VALORA mới` / `Giữ nguyên nội dung trong Word` / `Bỏ qua vùng này trong lần đồng bộ này`. Skip/defer không được đánh dấu là đã đồng bộ.

Completion gate: mọi conflict bắt buộc trong scope phải có explicit decision. Màn này chỉ cập nhật sync plan; chưa ghi Word, chưa tạo Document Revision/version.

Audit: lưu được tài liệu/vùng, ba giá trị, quyết định user, thời điểm. Revision/version chỉ tạo sau execution thành công.

## 4. Bulk Sync Preview authority
Preview read-only/zero-write; revision dự kiến chưa tồn tại; Blocking ngăn execution; Warning không tự Blocking.

## 5. Guardrails
- Single-user; AI advisory.
- Không auto-win VALORA/Word.
- Không silent mapping/save/sync/overwrite/conflict resolution/publish.
- Không fake Word editor.
- Document Revision != Microsoft 365 file version.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 6. ADR
Conflict-decision persistence, sync-plan transaction boundary, defer semantics, stale-conflict detection và audit storage cần ADR nếu implementation thay đổi persistence/architecture.
