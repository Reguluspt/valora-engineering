# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Xác nhận & Lưu template tùy biến — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_CUSTOM_TEMPLATE_CONFIRM_SAVE_BASELINE_ADDENDUM.md` — **Baseline `Xác nhận & Lưu template tùy biến — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_AI_CUSTOM_TEMPLATE_RECOGNITION_BASELINE_ADDENDUM.md` — Baseline AI nhận diện & thiết lập mẫu.
4. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md` — Baseline Tạo & Xem lại bộ tài liệu hồ sơ.
5. Các addendum Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Template/AI, Result/NCCQ hiện hành trong scope tương ứng.
6. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Microsoft 365 Document Workspace
→ Tạo & Xem lại bộ tài liệu hồ sơ
   → Tải lên mẫu tùy biến
      → Tải file & phân tích
      → Đề xuất mapping
      → Test fill (xem trước)
      → Xác nhận & Lưu template
         → Chỉ sử dụng cho hồ sơ này [default]
         hoặc → Lưu vào thư viện mẫu để tái sử dụng [explicit]
   → template đã lưu sẵn sàng cho batch generation
→ Phát hành bộ tài liệu
```

## 3. Confirm & Save baseline
Layout: thông tin template + mapping/test-fill summary bên trái; preview Word view-only lớn ở giữa; validation + phạm vi sử dụng bên phải; footer có `Hủy`, `Quay lại: Test fill`, primary `Xác nhận & Lưu template`.

Validation gate: `Blocking > 0` không lưu; `Blocking = 0` có thể lưu. Warning không tự Blocking; Info là thông tin. Không silent sửa dữ liệu/mapping để pass.

Scope: `Chỉ sử dụng cho hồ sơ này` là mặc định; `Lưu vào thư viện mẫu để tái sử dụng` là explicit opt-in. Không auto-promote.

Save tạo/lưu Template Version từ mapping/Managed Regions đã xác nhận và provenance Test fill; không tự tạo/publish Document Revision. Sau save quay lại Document Set workspace để dùng template.

## 4. AI custom-template authority
AI chỉ đề xuất field/mapping/Managed Regions/Repeating Regions; user xác nhận. Custom field không tự promote canonical. Flow đầy đủ:
`Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template`.

## 5. Document Set authority
`Template Version(s) → Data Snapshot → Batch generation → Review → Sync on change → Publishing`. Preview lớn; sync explicit; published revision immutable.

## 6. Guardrails
- Single-user; AI advisory.
- Không fake Word/Excel editor.
- Không silent accept/mapping/save/sync/overwrite/publish.
- Không auto-promote custom field hoặc case template.
- Document Revision != Microsoft 365 file version.
- Vietnamese-first; một primary CTA mỗi context.

## 7. ADR
Template Version save transaction, Test-fill provenance, scope promotion, rollback/idempotency cần ADR nếu implementation thay đổi persistence/architecture.
