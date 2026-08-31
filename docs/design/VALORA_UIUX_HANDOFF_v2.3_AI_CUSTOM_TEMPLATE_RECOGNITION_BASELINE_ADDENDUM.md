# VALORA UI/UX v2.3 — AI nhận diện & thiết lập mẫu từ tài liệu tải lên — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Scope:** Microsoft 365 Document Workspace → Bộ tài liệu hồ sơ → Mẫu tùy biến của hồ sơ → AI nhận diện & thiết lập mẫu từ tài liệu tải lên.  
**Visual language:** Microsoft Fluent 2, desktop-first, Vietnamese-first.

## 1. Quyết định baseline
Mockup `AI nhận diện & thiết lập mẫu từ tài liệu tải lên — Iteration 1` được nâng thành **Baseline / Design Authority**.

Baseline này khóa child-flow biến một tài liệu Word tùy biến của khách hàng thành Template Version có thể fill dữ liệu có kiểm soát. AI chỉ phân tích và đề xuất; user phải rà soát/xác nhận trước khi tạo Managed Regions/mapping chính thức hoặc lưu template.

## 2. Mental flow
```text
Tải file & phân tích
→ Đề xuất mapping
→ Test fill (xem trước)
→ Xác nhận & Lưu template
```

## 3. Layout authority — Fluent 2
- Header/breadcrumb trong context hồ sơ → Tài liệu & Workspace → Bộ tài liệu hồ sơ → Tải lên mẫu tùy biến.
- Stepper 4 bước theo mental flow.
- Cột trái: `Trường dữ liệu hồ sơ (Data Source)` với search/filter, nhóm `Tất cả / AI đề xuất / Chưa map`, confidence và giá trị hiện tại.
- Trung tâm là **preview Word lớn** có highlight trực tiếp các vùng AI nhận diện, vùng đề xuất, repeating region và nội dung cố định/không quản lý.
- Cột phải: `Mapping & thiết lập vùng dữ liệu` để xem/chỉnh field đang chọn, vị trí trong tài liệu, loại vùng, giá trị xem trước, ghi chú và hành động `Xóa mapping / Bỏ qua trường này`.
- Footer: `Hủy / Quay lại` và đúng một primary CTA `Tiếp tục: Test fill (xem trước)` ở bước đề xuất mapping.
- Preview chỉ dùng để rà soát; không fake Word editor.

## 4. AI recognition semantics
VALORA đối chiếu nội dung file upload với dữ liệu của hồ sơ đang thao tác để tìm các đoạn có khả năng tương ứng.

AI có thể đề xuất:
- trường dữ liệu đơn (text/date/number);
- vùng dữ liệu/Managed Region;
- bảng/vùng lặp (Repeating Region);
- nội dung cố định;
- nội dung không do VALORA quản lý.

Confidence là tín hiệu hỗ trợ, không phải quyết định nghiệp vụ. AI không được tự động tạo mapping chính thức chỉ vì confidence cao.

## 5. User-controlled mapping
User có thể:
- xác nhận đề xuất;
- đổi field nguồn;
- đổi loại vùng dữ liệu;
- bỏ mapping;
- đánh dấu nội dung cố định;
- đánh dấu không quản lý bằng VALORA;
- thêm trường tùy chỉnh khi cần.

Nếu không có field chuẩn phù hợp, custom field không tự được promote thành canonical/global field.

## 6. Managed Region creation boundary
Chỉ mapping/vùng user đã xác nhận mới được chuyển thành cấu hình Template Version/Managed Regions.

Không silent:
- chấp nhận mapping;
- biến text thành Managed Region;
- ghi đè nội dung Word;
- lưu/publish template;
- promote field/template ra phạm vi dùng chung.

## 7. Test fill
Bước `Test fill (xem trước)` sử dụng dữ liệu hồ sơ hiện tại để mô phỏng kết quả điền.

Validator tối thiểu:
- `Blocking`: mapping bắt buộc thiếu/không hợp lệ, repeating region không đủ cấu hình hoặc template không thể fill an toàn;
- `Warning`: confidence thấp, nhiều vị trí cạnh tranh, overflow/format/page-break risk;
- `Info`: trạng thái đã nhận diện/đã xác nhận.

User phải nhìn được kết quả preview trước khi lưu Template Version.

## 8. Template scope
Sau khi user xác nhận và test fill đạt điều kiện:
- mặc định lưu thành **Template Version chỉ dùng cho hồ sơ hiện tại**;
- chỉ khi user explicit chọn `Lưu vào thư viện mẫu` mới mở rộng phạm vi tái sử dụng cho hồ sơ khác.

Upload tài liệu khách hàng không tự động trở thành template dùng chung/global.

## 9. Relationship với Document Set baseline
Flow này là child-flow của `Tạo & Xem lại bộ tài liệu hồ sơ — Iteration 1` tại capability `Tải lên mẫu tùy biến`.

Sau khi lưu Template Version, template có thể tham gia batch generation/review/sync theo authority Document Set hiện hành. Báo cáo/Chứng thư vẫn giữ Managed Regions/Generation-Sync authority riêng khi cần.

## 10. Guardrails
- Single-user.
- AI advisory; user quyết định mapping/template chính thức.
- Không fake Word editor.
- Không phơi Region ID/internal technical terms ở bề mặt chính.
- Không hard-code field từ mockup.
- Không silent accept/mapping/fill/save/publish.
- Một primary CTA mỗi context.
- Không auto-promote template hồ sơ thành template dùng chung.

## 11. ADR
Promotion này là UI/UX/domain interaction authority. Nếu implementation làm thay đổi AI-to-mapping persistence, Managed Region creation semantics, custom-field persistence, template-scope promotion hoặc test-fill transaction boundary thì phải đánh giá ADR riêng trước khi sửa product code.
