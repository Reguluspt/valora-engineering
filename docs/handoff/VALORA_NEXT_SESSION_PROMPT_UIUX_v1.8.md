# Prompt bàn giao phiên làm việc tiếp theo — VALORA UI/UX v1.8

Bạn đang tiếp tục thiết kế sản phẩm **Valora** trong repository `Reguluspt/valora-engineering`.

## 1. Tài liệu cần đọc trước

Đọc theo thứ tự:

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. `docs/design/VALORA_UIUX_HANDOFF_v1.8.md`
6. `docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md`
7. `docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md`
8. `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
9. `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`

Tài liệu `VALORA_UIUX_HANDOFF_v1.8.md` là baseline nghiệp vụ/UI mới nhất cho luồng single-user.

## 2. Phạm vi sản phẩm đã chốt

- Valora hiện tại dành cho **01 người dùng xử lý toàn bộ quy trình**.
- Chỉ phục vụ **thẩm định giá máy móc thiết bị**.
- Phương pháp nghiệp vụ cố định: **phương pháp so sánh**.
- Công việc chính: đối chiếu Kho tri thức và tìm thông tin giá bán trên Internet.
- **Không thiết kế khảo sát hiện trạng**.
- AI/Kho tri thức chỉ gợi ý; người dùng xác nhận mọi quyết định chính thức.

## 3. Luồng đầu vào đã chốt

```text
Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
→ Kho tri thức / Nguồn giá Internet
→ Giá thị trường
→ Vận chuyển (%)
→ Đơn giá đề xuất
→ Hoàn tất phân tích danh mục
→ Chờ khách hàng phản hồi
→ Khách hàng chấp thuận
→ Chuyển thành hồ sơ chính thức
```

Khách hàng thường chỉ gửi file Excel danh mục trước. Chưa bắt buộc thông tin khách hàng, hợp đồng, MST, địa chỉ ở giai đoạn Pre-case.

## 4. Các màn hình/mockup đã chốt

Baseline đã duyệt gồm:

1. Quản lý yêu cầu sơ bộ.
2. Tạo yêu cầu sơ bộ.
3. Upload & Mapping Excel.
4. Phân tích danh mục.
5. Panel Kho tri thức.
6. Panel Nguồn giá Internet.
7. Thêm nguồn giá.

Khi thiết kế màn hình mới, phải giữ cùng shell/component language: sidebar, breadcrumb/header, KPI cards, table/grid, right panel, tabs, badge trạng thái, button hierarchy, typography và spacing.

## 5. Quy tắc quan trọng của màn hình Phân tích danh mục

Cụm cột giá trung tâm phải theo thứ tự:

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

Không có cột chênh lệch so với khách hàng.

Công thức:

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

Không hiển thị field `Chi phí vận chuyển` và `Giá sau vận chuyển`.

## 6. Nguồn giá

`+ Thêm nguồn giá` hỗ trợ hai cách:

1. **Thuyết minh đơn giá** — rich text để ghi căn cứ/diễn giải chuyên môn.
2. **Dán link trang web** — nhập URL và lưu dữ liệu nguồn Internet.

Có thể dùng một hoặc cả hai.

Phân biệt domain semantics:

- `USER_PRICE_JUSTIFICATION`
- `INTERNET_MARKET_SOURCE`

Không đồng nhất thuyết minh của người dùng với chứng cứ Internet.

## 7. Kho tri thức

Mỗi candidate cần hiển thị:

- tên chuẩn;
- thương hiệu/model;
- thông số;
- mức độ tương đồng;
- lý do khớp;
- giá/lịch sử;
- ngày cập nhật;
- nguồn liên quan.

Không auto-accept. Giá lịch sử chỉ là tham khảo.

## 8. Pre-case

Pre-case là entity trước hồ sơ chính thức.

Trạng thái nghiệp vụ đề xuất:

- Mới tạo
- Mới nhận danh mục
- Đang đối chiếu tri thức
- Cần tìm giá
- Đang phân tích giá
- Sẵn sàng gửi giá đề xuất
- Chờ khách hàng phản hồi
- Đã chấp thuận giá đề xuất
- Không tiếp tục
- Đã chuyển thành hồ sơ

Khi khách hàng chấp thuận, dữ liệu đã phân tích phải được tái sử dụng trong hồ sơ chính thức; không bắt upload/làm lại từ đầu.

## 9. Guardrail kỹ thuật không được phá

- Tenant isolation fail-closed.
- Excel upload/validate chỉ tạo staging, không tự thành official data.
- Apply phải do người dùng xác nhận.
- Restricted Workbench fields đi qua draft/commit và audit atomically.
- Raw/source evidence phải giữ provenance.
- AI không auto-approve, auto-apply, auto-price hoặc auto-publish.

## 10. Nhiệm vụ ưu tiên cho phiên tiếp theo

Tiếp tục từ baseline v1.8, ưu tiên **thiết kế sâu màn hình tiếp theo chưa chốt** thay vì sửa lại các màn hình đã duyệt.

Đề xuất thứ tự:

1. **S08 — Rà soát giá đề xuất**
   - tổng hợp toàn danh mục sau khi từng dòng đã hoàn tất;
   - thống kê thiết bị dùng Kho tri thức / nguồn Internet;
   - tổng giá trị đề xuất;
   - thiết bị còn thiếu nguồn/chưa xác nhận;
   - thao tác quay lại dòng lỗi;
   - CTA `Hoàn tất phân tích danh mục`.

2. Sau khi S08 chốt, thiết kế **trạng thái Chờ khách hàng phản hồi / ghi nhận kết quả phản hồi**.

3. Tiếp theo thiết kế **S09 — Chuyển thành hồ sơ chính thức**.

Mỗi lần chốt một màn hình:

- mô tả user goal;
- inputs;
- layout;
- states;
- primary/secondary CTA;
- validations;
- error/empty/loading;
- dữ liệu được lưu;
- điều kiện chuyển bước;
- dựng mockup bám design system đã chốt;
- sau khi người dùng duyệt, cập nhật `VALORA_UIUX_HANDOFF` lên version tiếp theo.

## 11. Cách làm việc với người dùng

- Trao đổi bằng tiếng Việt.
- Xưng `em`, gọi người dùng là `anh`.
- Không tự suy diễn nghiệp vụ nếu chưa chắc; đưa phương án ngắn gọn để anh xác nhận.
- Ưu tiên mockup thực dụng, desktop-first, tối ưu cho danh mục nhiều dòng.
- Mỗi thay đổi đã được anh chốt phải cập nhật vào tài liệu Handoff.

## 12. Điểm bắt đầu ngay

Hãy bắt đầu bằng việc đọc `docs/design/VALORA_UIUX_HANDOFF_v1.8.md`, sau đó trình bày thiết kế chi tiết cho **S08 — Rà soát giá đề xuất** và dựng mockup đầu tiên theo đúng design system Valora đã chốt.
