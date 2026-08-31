# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa: S09–S13; Nguồn giá & Chứng cứ; NCCQ Iteration 6; Kết quả thẩm định giá; Microsoft 365 Document Workspace; Managed Regions Báo cáo/Chứng thư; Sync/Version; Publishing; Template/AI; Fill Engine; Sinh & Đồng bộ Báo cáo; Sinh & Đồng bộ Chứng thư; Tạo & Xem lại bộ tài liệu hồ sơ; và **AI nhận diện & thiết lập mẫu từ tài liệu tải lên — Iteration 1**.

Không có S14, màn Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn Kiểm tra quy tắc đối chiếu giá.

## 1. North-star flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản → Asset Context Drawer
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Tạo hàng loạt từ mẫu có sẵn
      → Review từng tài liệu trong preview lớn
      → Đồng bộ dữ liệu khi hồ sơ thay đổi
      → Tải lên mẫu tùy biến của hồ sơ
         → AI nhận diện & thiết lập mẫu
            → Tải file & phân tích
            → Đề xuất mapping
            → Test fill (xem trước)
            → Xác nhận & Lưu template
   → Báo cáo / Chứng thư: child-flow Managed Regions/Generation-Sync chuyên sâu khi cần
   → Đồng bộ dữ liệu & Quản lý phiên bản
   → Phát hành bộ tài liệu
```

## 2. Price & Evidence
Ưu tiên: `Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính xác định đơn giá cuối cùng. Giá NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% là Warning; Warning không Blocking.

## 3. Kết quả thẩm định giá
03 bảng biểu mẫu công ty immutable; không đổi tên/thứ tự cột, split/merge/cardize; giữ Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Template / AI / Spreadsheet
AI chỉ phân tích/gợi ý/test; user xác nhận mapping/template. Không silent accept/publish/overwrite/change formula.

Bảng tính: `Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine: `Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version`; không overwrite template/staticize formula/silent drop workbook feature.

## 5. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, release manifest. Microsoft 365 quản lý Word/file/file version. Document Revision != Microsoft 365 file version.

### 5.1 Tạo & Xem lại bộ tài liệu hồ sơ — Baseline Iteration 1
Các tài liệu có mẫu sẵn được sinh hàng loạt và review trong một workspace chung. Preview tài liệu lớn là vùng review chính; `Đồng bộ dữ liệu` là explicit action khi hồ sơ thay đổi. Batch có thể dùng chung Data Snapshot nhưng từng tài liệu có lineage riêng:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```

Mẫu tùy biến mặc định chỉ thuộc hồ sơ; chỉ explicit `Lưu vào thư viện mẫu` mới mở rộng phạm vi tái sử dụng.

### 5.2 AI nhận diện & thiết lập mẫu từ tài liệu tải lên — Baseline Iteration 1
Mental flow:
```text
Tải file & phân tích
→ Đề xuất mapping
→ Test fill (xem trước)
→ Xác nhận & Lưu template
```

Layout Fluent 2: cột trái là `Trường dữ liệu hồ sơ (Data Source)` có search/filter/confidence; trung tâm là **preview Word lớn** với highlight vùng AI nhận diện/đề xuất/repeating/fixed; cột phải là `Mapping & thiết lập vùng dữ liệu` cho phép user xem/chỉnh field, vị trí, loại vùng, preview value, ghi chú và bỏ mapping; footer có một primary CTA `Tiếp tục: Test fill (xem trước)`.

AI đối chiếu nội dung `.docx` với dữ liệu hồ sơ hiện tại để **đề xuất** text field, Managed Region, Repeating Region hoặc nội dung cố định/không quản lý. Confidence chỉ là tín hiệu hỗ trợ, không tự chốt mapping.

User có thể xác nhận đề xuất, đổi field nguồn, đổi loại vùng, bỏ mapping, đánh dấu nội dung cố định/không quản lý hoặc thêm custom field. Custom field không tự promote thành canonical/global field.

Chỉ mapping/vùng user đã xác nhận mới trở thành cấu hình Template Version/Managed Regions. Không silent accept mapping, tạo Managed Region, fill, save/publish template hoặc promote scope.

`Test fill (xem trước)` phải cho user nhìn thấy kết quả trước khi lưu. Validator dùng `Blocking / Warning / Info`; Blocking ngăn lưu khi mapping bắt buộc/repeating region không hợp lệ hoặc không thể fill an toàn.

Sau khi xác nhận, template mặc định được lưu **chỉ cho hồ sơ hiện tại**. Chỉ khi user explicit chọn `Lưu vào thư viện mẫu` mới trở thành template tái sử dụng ngoài hồ sơ.

### 5.3 Báo cáo & Chứng thư
Hai loại này giữ Generation/Sync + Managed Regions baselines riêng. Workspace bộ tài liệu là orchestration layer, không thay thế child-flow chuyên sâu.

### 5.4 Publishing
Tiếp tục authority: `Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không có `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Không fake Word/Excel editor.
- Không silent mapping/sync/overwrite/publish.
- Không auto-promote custom field hoặc mẫu riêng của hồ sơ.
- Preview review-first, chiếm diện tích chính.
- Một primary CTA mỗi context.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Published revision/release immutable.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 | P0 baseline |
| NCCQ | P0 baseline Iteration 6 |
| Result | P0 baseline; 03 bảng immutable |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| **AI nhận diện & thiết lập mẫu từ tài liệu tải lên** | **P0 baseline Iteration 1** |
| Managed Regions — Báo cáo | P0 baseline |
| Managed Regions — Chứng thư | P0 baseline |
| Sinh & Đồng bộ Báo cáo | P0 baseline |
| Sinh & Đồng bộ Chứng thư | P0 baseline |
| Sync/Version | P0 baseline |
| Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_AI_CUSTOM_TEMPLATE_RECOGNITION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md`.
- Các addendum Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Template/AI, Result/NCCQ hiện hành tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Baseline AI custom-template recognition khóa UI/UX + domain interaction. Nếu implementation thay đổi AI-to-mapping persistence, Managed Region creation semantics, custom-field persistence, template-scope promotion hoặc test-fill transaction boundary thì phải đánh giá ADR riêng trước khi sửa product code.
