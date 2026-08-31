# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa: S09–S13; Nguồn giá & Chứng cứ; NCCQ Iteration 6; Kết quả thẩm định giá; Microsoft 365 Document Workspace; Managed Regions Báo cáo/Chứng thư; Sync/Version; Publishing; Template/AI; Fill Engine; Sinh & Đồng bộ Báo cáo/Chứng thư; Tạo & Xem lại bộ tài liệu hồ sơ; AI nhận diện & thiết lập mẫu; và **Xác nhận & Lưu template tùy biến — Iteration 1**.

Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

## 1. North-star flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản → Asset Context Drawer
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Batch generation từ mẫu có sẵn → Review → Sync khi dữ liệu thay đổi
      → Tải lên mẫu tùy biến
         → Tải file & phân tích → Đề xuất mapping → Test fill → Xác nhận & Lưu template
            → Chỉ hồ sơ này [default] / Lưu vào thư viện mẫu [explicit]
      → template đã lưu quay về workspace để dùng trong batch
   → Báo cáo / Chứng thư: child-flow chuyên sâu khi cần
   → Đồng bộ dữ liệu & Quản lý phiên bản → Phát hành bộ tài liệu
```

## 2. Price & Evidence
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính. NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% Warning; không Blocking.

## 3. Kết quả thẩm định giá
03 bảng công ty immutable; giữ tên/thứ tự cột, Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Template / AI / Spreadsheet
AI advisory; user xác nhận mapping/template. Không silent accept/publish/overwrite/change formula. Custom field không tự promote canonical.

Bảng tính: `Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine không overwrite template/staticize formula/silent drop workbook feature.

## 5. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, release manifest. Microsoft 365 quản lý Word/file/file version. `Document Revision != Microsoft 365 file version`.

### 5.1 Tạo & Xem lại bộ tài liệu hồ sơ — Baseline Iteration 1
Tài liệu có mẫu sẵn được sinh hàng loạt và review trong workspace chung. Preview lớn là vùng review chính. `Đồng bộ dữ liệu` explicit khi hồ sơ thay đổi. Từng tài liệu có lineage `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version`.

### 5.2 AI nhận diện & thiết lập mẫu — Baseline Iteration 1
`Tải file & phân tích → Đề xuất mapping → Test fill (xem trước) → Xác nhận & Lưu template`.
AI đối chiếu `.docx` với dữ liệu hồ sơ và chỉ đề xuất field/mapping/Managed/Repeating Regions. User xác nhận trước khi thành cấu hình. Preview Word lớn; không fake editor.

### 5.3 Xác nhận & Lưu template tùy biến — Baseline Iteration 1
Đây là bước 4/4 sau Test fill.

Layout Fluent 2 baseline: trái là thông tin Template Version dự kiến + thống kê vùng + trạng thái Test fill; giữa là **preview Word view-only lớn** của kết quả test; phải là validation `Blocking / Warning / Info` + chi tiết vấn đề + `Phạm vi sử dụng template`; footer `Hủy`, `Quay lại: Test fill`, primary CTA `Xác nhận & Lưu template`.

Validation gate:
- `Blocking > 0` → không lưu.
- `Blocking = 0` → cho phép lưu; Warning vẫn hiển thị nhưng không tự Blocking.
- Info là thông tin.
- Không silent sửa mapping, repeating region, fixed content hoặc source data để pass validation.

Scope authority:
- `Chỉ sử dụng cho hồ sơ này` — mặc định.
- `Lưu vào thư viện mẫu để tái sử dụng` — explicit opt-in.
Không auto-promote template hồ sơ thành library/global template.

Khi user xác nhận: lưu Template Version từ mapping/Managed Regions đã xác nhận và ghi nhận provenance Test fill/validation; giữ file nguồn/narrative ngoài vùng; **không tự tạo hoặc publish Document Revision**. Sau save, template quay về `Tạo & Xem lại bộ tài liệu hồ sơ` và sẵn sàng dùng trong batch generation.

### 5.4 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer.

### 5.5 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Không fake Word/Excel editor.
- Không silent mapping/save/sync/overwrite/publish.
- Không auto-promote custom field/template scope.
- Preview review-first.
- Một primary CTA mỗi context.
- Published revision/release immutable.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 | P0 baseline |
| NCCQ | P0 baseline Iteration 6 |
| Result | P0 baseline; 03 bảng immutable |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| AI nhận diện & thiết lập mẫu | P0 baseline Iteration 1 |
| **Xác nhận & Lưu template tùy biến** | **P0 baseline Iteration 1** |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Sync/Version | P0 baseline |
| Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_CUSTOM_TEMPLATE_CONFIRM_SAVE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_AI_CUSTOM_TEMPLATE_RECOGNITION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md`.
- Các addendum hiện hành khác tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Nếu implementation thay đổi Template Version save transaction, Test-fill provenance, scope promotion, rollback/idempotency, AI-to-mapping persistence hoặc multi-document sync persistence thì phải đánh giá ADR riêng trước khi sửa product code.
