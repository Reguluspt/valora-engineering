# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Chuẩn bị bộ phát hành — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — **Baseline `Chuẩn bị bộ phát hành — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_RESULT_BASELINE_ADDENDUM.md` — Baseline Kết quả đồng bộ hàng loạt.
4. Các addendum Bulk Sync Confirm/Conflict/Preview/Data Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
5. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Publishing routing authority — simplified
Flow 5 bước cũ bị supersede.

Authority mới:
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành
→ hệ thống tạo Release Manifest + khóa các revision đã phát hành
```

Không còn bước UI riêng `Khóa phiên bản`. Không có `Xuất PDF`.

## 3. Release Preparation baseline
VALORA tự chọn revision mới nhất đủ điều kiện; user chủ yếu review ngoại lệ.

Layout: summary `Sẵn sàng phát hành (auto-selected) / Cần xem lại / Có lỗi / Không thay đổi / Tổng tài liệu`; banner giải thích selection; bảng tài liệu + revision/status/last sync/select; preview nhanh view-only; panel Release dự kiến + breakdown + chú ý; primary CTA sang review ngoại lệ.

Auto-selection rules:
- ready revision → auto-select;
- Blocking/error → không auto-select;
- `Cần xem lại` → exception;
- `Không thay đổi` có thể dùng revision hiện hành nếu vẫn hợp lệ;
- user có thể bỏ chọn tài liệu;
- auto-select không đồng nghĩa auto-publish.

`Chọn tài liệu để phát hành — Iteration 1` trước đó chỉ là proposal và bị supersede.

## 4. Bulk Sync Result authority
Post-execution result theo từng tài liệu; `Đã đồng bộ / Không thay đổi / Bỏ qua / Lỗi`; không export PDF; revision/version chỉ cho tài liệu update thành công.

## 5. Guardrails
- Single-user; AI advisory.
- Exception-first UX; giảm thao tác bình thường.
- Không silent publish/overwrite.
- Không fake Word editor.
- Không export PDF.
- Release Manifest bind đúng Document Revisions đã chọn.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 6. ADR
Release-readiness computation, auto-selection persistence, Release Manifest binding, locking transaction và partial-publish semantics cần ADR nếu implementation thay đổi persistence/architecture.
