# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `AI nhận diện & thiết lập mẫu từ tài liệu tải lên — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_AI_CUSTOM_TEMPLATE_RECOGNITION_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `AI nhận diện & thiết lập mẫu từ tài liệu tải lên — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md` — Baseline `Tạo & Xem lại bộ tài liệu hồ sơ — Iteration 1`.
4. `VALORA_UIUX_HANDOFF_v2.3_CERTIFICATE_GENERATION_SYNC_BASELINE_ADDENDUM.md` — Baseline Sinh & Đồng bộ Chứng thư.
5. `VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md` — Baseline Sinh & Đồng bộ Báo cáo.
6. `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md` — Baseline Fill Engine.
7. `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md` — NCC warning authority.
8. Các addendum Managed Regions / Sync-Version / Publishing / Template / Result / NCCQ hiện hành trong scope tương ứng.
9. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Tạo hàng loạt từ mẫu có sẵn
      → Review tài liệu trong preview lớn
      → Đồng bộ dữ liệu khi hồ sơ thay đổi
      → Tải lên mẫu tùy biến của hồ sơ
         → Tải file & phân tích
         → Đề xuất mapping
         → Test fill (xem trước)
         → Xác nhận & Lưu template
      → Báo cáo / Chứng thư mở child-flow chuyên sâu khi cần
   → Phát hành bộ tài liệu
```

## 3. AI custom-template baseline
AI đối chiếu nội dung `.docx` với dữ liệu hồ sơ hiện tại và chỉ **đề xuất** field/mapping/Managed Regions/Repeating Regions. User xác nhận trước khi mapping trở thành cấu hình Template Version.

Layout: data-source fields bên trái; preview Word lớn với highlight trung tâm; mapping/setup panel bên phải; primary CTA `Tiếp tục: Test fill (xem trước)`.

Mental flow:
```text
Tải file & phân tích → Đề xuất mapping → Test fill (xem trước) → Xác nhận & Lưu template
```

User có thể xác nhận, đổi field, đổi loại vùng, bỏ mapping, đánh dấu nội dung cố định/không quản lý, hoặc tạo custom field. Custom field không tự promote thành canonical field.

Template scope: mặc định chỉ hồ sơ hiện tại; chỉ explicit `Lưu vào thư viện mẫu` mới mở rộng phạm vi tái sử dụng.

## 4. Document Set baseline
```text
Template Version(s) → Data Snapshot → Batch generation → Review → Sync on change → Publishing
```
Preview tài liệu lớn là vùng review chính. `Đồng bộ dữ liệu` explicit; không silent overwrite; published revision immutable.

## 5. Existing Document Workspace authority
Managed Regions status: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`.

Báo cáo và Chứng thư giữ shared generation contract:
```text
Chọn template & phạm vi → Data Snapshot → Preview & Review vùng → Tạo Document Revision → Đồng bộ Microsoft 365 → Kết quả đồng bộ
```
Document Set workspace orchestration không thay thế child-flow chuyên sâu này.

## 6. Price & Evidence authority
Ưu tiên: `Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính xác định đơn giá cuối cùng. NCC warning là Warning tại dòng, không Blocking, không màn rule-check riêng.

## 7. Spreadsheet authority
`Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine không overwrite template, không staticize formula, không silent drop workbook feature.

## 8. Guardrails
- Single-user; AI advisory.
- Không S14, Kiểm tra hồ sơ riêng, KSCL workflow riêng, NCC rule-check screen.
- Không fake Word/Excel editor.
- Không silent accept/mapping/sync/overwrite/publish.
- Không auto-promote custom field hoặc mẫu hồ sơ thành global authority.
- Document Revision != Microsoft 365 file version.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 9. ADR
AI custom-template recognition baseline là UI/UX/domain interaction authority. Nếu implementation thay đổi AI-to-mapping persistence, Managed Region creation semantics, custom-field persistence, template-scope promotion hoặc test-fill transaction boundary thì đánh giá ADR riêng.
