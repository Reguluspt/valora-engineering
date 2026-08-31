# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Đồng bộ dữ liệu hàng loạt — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_BULK_DATA_SYNC_BASELINE_ADDENDUM.md` — **Baseline `Đồng bộ dữ liệu hàng loạt — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_CUSTOM_TEMPLATE_CONFIRM_SAVE_BASELINE_ADDENDUM.md` — Baseline Xác nhận & Lưu template tùy biến.
4. `VALORA_UIUX_HANDOFF_v2.3_AI_CUSTOM_TEMPLATE_RECOGNITION_BASELINE_ADDENDUM.md` — Baseline AI nhận diện & thiết lập mẫu.
5. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md` — Baseline Tạo & Xem lại bộ tài liệu hồ sơ.
6. Các addendum Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Template/AI, Result/NCCQ hiện hành.
7. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Tạo & Xem lại bộ tài liệu hồ sơ
→ khi dữ liệu hồ sơ thay đổi: Đồng bộ dữ liệu hàng loạt
   → Chọn nguồn dữ liệu mới
   → Xem thay đổi & phạm vi cập nhật
   → Xem trước kết quả
   → Xác nhận & Đồng bộ
→ mỗi tài liệu thực sự cập nhật tạo Document Revision mới
→ tiếp tục Review / Publishing
```

## 3. Bulk Data Sync baseline
Layout bước 2: summary nguồn + affected docs/regions/Warning/Blocking; trái scope/filter; giữa bảng tài liệu bị ảnh hưởng; phải diff chi tiết current→new + warning + revision dự kiến; primary `Xem trước kết quả`.

Scope: tất cả tài liệu bị ảnh hưởng / chỉ tài liệu được chọn / theo nhóm tài liệu. `Không thay đổi` không tạo revision mới.

Validation: Blocking ngăn phần tương ứng; Warning không tự Blocking; conflict Managed Region phải resolve theo authority hiện hành trước khi ghi.

Version: mỗi tài liệu được sync thành công tạo Document Revision mới và ghi nhận Microsoft 365 version; published revision/release immutable.

Nguồn mới trên mockup chỉ minh họa Data Snapshot/source revision mới; canonical business data vẫn Workbench/database, không khóa sync vào `.xlsx`.

## 4. Custom-template authority
Flow: `Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`. AI advisory; case-only default; library reuse explicit.

## 5. Document Set authority
`Template Version(s) → Data Snapshot → Batch generation → Review → Sync on change → Publishing`. Preview lớn; không silent overwrite.

## 6. Guardrails
- Single-user; AI advisory.
- Không fake Word/Excel editor.
- Không silent accept/mapping/save/sync/overwrite/publish.
- Không revision mới cho tài liệu không thay đổi.
- Không auto-promote custom field/case template.
- Document Revision != Microsoft 365 file version.
- Vietnamese-first; một primary CTA mỗi context.

## 7. ADR
Multi-document transaction boundary, partial success/rollback, idempotency, snapshot binding, conflict resolution và version creation semantics cần ADR nếu implementation thay đổi persistence/architecture.
