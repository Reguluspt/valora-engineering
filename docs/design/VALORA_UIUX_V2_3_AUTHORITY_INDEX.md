# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Xem trước kết quả đồng bộ — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_BULK_SYNC_PREVIEW_BASELINE_ADDENDUM.md` — **Baseline `Xem trước kết quả đồng bộ — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md` — Baseline Đồng bộ dữ liệu hàng loạt.
4. `VALORA_UIUX_HANDOFF_v2.3_CUSTOM_TEMPLATE_CONFIRM_SAVE_BASELINE_ADDENDUM.md` — Baseline Xác nhận & Lưu template tùy biến.
5. `VALORA_UIUX_HANDOFF_v2.3_AI_CUSTOM_TEMPLATE_RECOGNITION_BASELINE_ADDENDUM.md` — Baseline AI nhận diện & thiết lập mẫu.
6. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md` — Baseline Tạo & Xem lại bộ tài liệu hồ sơ.
7. Các addendum Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Template/AI, Result/NCCQ hiện hành.
8. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Đồng bộ dữ liệu hàng loạt
→ Chọn nguồn dữ liệu mới
→ Xem thay đổi & phạm vi cập nhật
→ Xem trước kết quả [read-only, zero-write]
→ Xử lý xung đột nếu có
→ Xác nhận & Đồng bộ
→ Document Revision mới chỉ cho tài liệu sync thành công
```

## 3. Bulk Sync Preview baseline
Bước 3/4. Layout: session/source info + preview summary; bảng tài liệu với affected regions/data/Word changes/result/revision dự kiến; panel phải current→after sync; Warning/Blocking; footer quay lại/conflict/primary `Tiếp tục: Xác nhận & Đồng bộ`.

Preview semantics: `Sẽ cập nhật` là dự kiến, không phải đã ghi. Revision dự kiến chưa tồn tại. `Không thay đổi` không tạo revision.

Conflict: nếu Word và VALORA cùng thay đổi Managed Region, user phải xử lý conflict; không auto-win VALORA hoặc Word.

Validation: Blocking >0 không được thực thi; Warning không tự Blocking. Preview không silent fix.

Data source `.xlsx` trên mockup chỉ minh họa source/Data Snapshot; canonical business data vẫn Workbench/database.

## 4. Bulk Data Sync authority
`Chọn nguồn dữ liệu mới → Xem thay đổi & phạm vi cập nhật → Xem trước kết quả → Xác nhận & Đồng bộ`. Không silent sync; user chọn scope; tài liệu không đổi không revision.

## 5. Document/Template authority
Document Set: `Template Version(s) → Data Snapshot → Batch generation → Review → Sync on change → Publishing`. Custom template flow giữ authority hiện hành; AI advisory, case-only default, library reuse explicit.

## 6. Guardrails
- Single-user; AI advisory.
- Preview zero-write.
- Không fake Word/Excel editor.
- Không silent mapping/save/sync/overwrite/conflict resolution/publish.
- Không revision/version mới ở preview.
- Document Revision != Microsoft 365 file version.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 7. ADR
Preview persistence, revision reservation, diff cache, conflict/validation transaction boundary cần ADR nếu implementation thay đổi persistence/architecture.
