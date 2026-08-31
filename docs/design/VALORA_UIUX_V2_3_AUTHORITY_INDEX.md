# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Tạo & Xem lại bộ tài liệu hồ sơ — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Tạo & Xem lại bộ tài liệu hồ sơ — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_CERTIFICATE_GENERATION_SYNC_BASELINE_ADDENDUM.md` — Baseline Sinh & Đồng bộ Chứng thư.
4. `VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md` — Baseline Sinh & Đồng bộ Báo cáo.
5. `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md` — Baseline Fill Engine.
6. `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md` — NCC warning authority.
7. Các addendum Managed Regions / Sync-Version / Publishing / Template / Result / NCCQ hiện hành trong scope tương ứng.
8. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Chọn/bộ mẫu có sẵn
      → Data Snapshot
      → Tạo bộ tài liệu hàng loạt
      → Review tài liệu trong preview lớn
      → Đồng bộ dữ liệu khi hồ sơ thay đổi
      → Tải lên mẫu tùy biến của hồ sơ (khi cần)
         → AI nhận diện trường → user xác nhận → test fill → Template Version
      → Báo cáo / Chứng thư mở child-flow chuyên sâu khi cần
   → Phát hành bộ tài liệu
```

Các tài liệu mẫu cố định như Quyết định/Kế hoạch/Phiếu KSCL không cần workflow riêng; sinh hàng loạt + review chung.

## 3. Document Set baseline
Mental model:
```text
Template Version(s) → Data Snapshot → Batch generation → Review → Sync on change → Publishing
```

Layout: summary phía trên; danh sách tài liệu trái; **preview tài liệu lớn trung tâm**; metadata/mapping/history phải; zoom/page/full-screen/Open in Word. Preview nhỏ của iteration trước bị supersede.

Batch dùng chung snapshot nhưng từng tài liệu có `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version` riêng.

`Đồng bộ dữ liệu` explicit: xem thay đổi → chọn tài liệu/vùng → sync. Không silent overwrite; conflict managed region phải xử lý; published revision immutable.

Mẫu tùy biến: upload `.docx` → AI đối chiếu dữ liệu hồ sơ → gợi ý/ highlight mapping/Managed Regions → user xác nhận → test fill → lưu Template Version. Mặc định scope hồ sơ; chỉ explicit `Lưu vào thư viện mẫu` mới tái sử dụng rộng hơn.

## 4. Existing Document Workspace authority
Managed Regions status: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`.

Báo cáo và Chứng thư giữ shared generation contract:
```text
Chọn template & phạm vi → Data Snapshot → Preview & Review vùng → Tạo Document Revision → Đồng bộ Microsoft 365 → Kết quả đồng bộ
```
Document Set workspace orchestration không thay thế child-flow chuyên sâu này.

## 5. Price & Evidence authority
Ưu tiên: `Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính xác định đơn giá cuối cùng.

NCC warning: giá NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% là Warning; không Blocking; không màn rule-check riêng.

## 6. Spreadsheet authority
`Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine không overwrite template, không staticize formula, không silent drop workbook feature.

## 7. Guardrails
- Single-user; AI advisory.
- Không S14, Kiểm tra hồ sơ riêng, KSCL workflow riêng, NCC rule-check screen.
- Không fake Word/Excel editor.
- Không silent accept/mapping/sync/overwrite/publish.
- Không auto-promote mẫu hồ sơ thành global template.
- Document Revision != Microsoft 365 file version.
- Published revision/release immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 8. ADR
Baseline Document Set là UI/UX/domain interaction authority. Batch transaction semantics, template scope persistence, AI-to-managed-region conversion, conflict detection hoặc multi-document sync persistence cần đánh giá ADR riêng khi implement nếu thay đổi kiến trúc/persistence.
