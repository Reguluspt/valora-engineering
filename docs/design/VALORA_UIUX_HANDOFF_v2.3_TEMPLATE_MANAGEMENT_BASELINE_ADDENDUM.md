# VALORA UI/UX Handoff v2.3 — Quản lý mẫu tài liệu Generic Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Baseline:** `Quản lý mẫu tài liệu generic — Iteration 1`  
**Scope:** Cấu hình mẫu tài liệu dùng chung toàn VALORA  
**Ngày chốt:** 30/08/2026

Addendum này ghi nhận quyết định explicit mới nhất của người dùng: mockup **Quản lý mẫu tài liệu generic** được nâng thành **Baseline / Design Authority**.

Authority này supersede hướng IA hẹp trước đó coi danh sách template chỉ thuộc `03_Hợp đồng`. `03_Hợp đồng` là một category/filter nghiệp vụ của hệ thống quản lý template dùng chung, không phải nơi sở hữu toàn bộ template của VALORA.

## A. Mục tiêu IA

VALORA có một khu vực quản lý mẫu tài liệu cấp hệ thống:

```text
Cấu hình
→ Mẫu tài liệu
→ Quản lý mẫu tài liệu
```

Khu vực này quản lý template phục vụ nhiều loại tài liệu phát hành, trong khi từng module nghiệp vụ có thể mở cùng dữ liệu đã filter theo context.

## B. Nhóm template authority

Các nhóm tối thiểu:

```text
Tất cả
Hợp đồng & hồ sơ liên quan
Báo cáo thẩm định giá
Chứng thư thẩm định giá
Phụ lục / Bảng tính Excel
Báo giá nhà cung cấp
```

`Hợp đồng & hồ sơ liên quan` có thể phân nhóm con:

- Phiếu/Giấy yêu cầu;
- Danh mục;
- Thương thảo;
- Dự thảo hợp đồng;
- Hợp đồng;
- Phụ lục hợp đồng;
- Nghiệm thu;
- Thanh lý;
- tài liệu hợp đồng khác.

## C. Quy tắc định dạng

Generic Template Management quản lý metadata/lifecycle chung nhưng phải tôn trọng authority định dạng theo từng loại:

- tài liệu Word dùng `.docx`;
- Phụ lục/Bảng tính Excel dùng `.xlsx` hoặc `.xlsm` khi nghiệp vụ/template yêu cầu;
- template Báo giá NCC **chỉ Word `.docx`**, giữ nguyên TM03/TM04 authority;
- generic module không được dùng Excel/PDF làm template Báo giá NCC;
- không suy diễn rằng mọi loại template đều dùng cùng một fill engine hoặc mapping interaction nếu format khác nhau.

Word Generic Document Mapping Iteration 2 là authority cho UX mapping Word generic trong scope phù hợp. Excel template mapping cần authority riêng trước khi implementation.

## D. Bố cục visual authority

Desktop-first, Fluent 2, table-first.

Header:

- breadcrumb `Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu`;
- title `Quản lý mẫu tài liệu`;
- mô tả ngắn về quản lý template dùng để tạo/phát hành tài liệu;
- action `Nhập template`;
- action `Thiết lập chung`;
- primary CTA `Tạo mẫu mới`.

Bên dưới là category tabs cho các nhóm authority ở mục B.

Vùng nội dung gồm:

```text
┌ Danh mục loại tài liệu ┐ ┌ Bộ lọc + bảng template ┐
│ category tree/filter   │ │ search                 │
│ rule định dạng         │ │ filters                │
│                        │ │ data grid              │
└────────────────────────┘ └────────────────────────┘
```

## E. Bảng template

Các cột authority tối thiểu:

```text
Loại tài liệu
Tên mẫu
Định dạng
Phiên bản
Mặc định
Trạng thái
Cập nhật gần nhất
Người cập nhật
Thao tác
```

Có search và filter theo tối thiểu:

- định dạng;
- trạng thái;
- người tạo/cập nhật;
- thời điểm cập nhật;
- loại tài liệu.

Không cardize từng template nếu làm giảm mật độ thông tin; ưu tiên data grid.

## F. Lifecycle và thao tác

Template hỗ trợ các thao tác phù hợp với quyền/context:

- Xem;
- Chỉnh mapping/cấu hình;
- Tạo phiên bản mới;
- Nhân bản;
- Đặt làm mặc định;
- Ngừng sử dụng;
- Xem lịch sử phiên bản.

Template/version đã từng được dùng để sinh tài liệu phải giữ lineage và không silent overwrite.

Một category có thể có nhiều template/version, nhưng khái niệm `Mặc định` phải xác định trong đúng scope loại tài liệu/context, không phải một default duy nhất cho toàn hệ thống.

## G. Quan hệ với các authority khác

### Generic Word Mapping

Với Word generic phù hợp:

```text
Quản lý mẫu tài liệu
→ Tạo/Nhập mẫu
→ Chọn mẫu Word
→ Đánh dấu vị trí
→ Kiểm tra & hoàn tất
→ Sẵn sàng sử dụng
```

Bước Mapping và Review tuân `GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM` và `GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM`.

### Báo giá NCC

TM03/TM04 vẫn là authority chuyên biệt cho template Báo giá NCC. Generic Template Management chỉ cung cấp entry/list/version/lifecycle chung và không override Word-only/mapping/test-fill rules đã khóa.

### Excel

Phụ lục/Bảng tính Excel được quản lý trong cùng danh mục template nhưng **Excel mapping/fill behavior chưa được baseline trong addendum này**. Không áp Word region semantics một cách máy móc cho workbook/sheet/cell.

## H. Contextual entry

Từ `03_Hợp đồng`, người dùng có thể mở Quản lý mẫu tài liệu với filter `Hợp đồng & hồ sơ liên quan`.

Từ khu vực Báo cáo/Chứng thư/Phụ lục, có thể mở cùng module với category tương ứng.

Do đó không tạo các hệ quản lý template độc lập trùng lặp cho từng folder nghiệp vụ nếu không có lý do domain rõ ràng.

## I. Guardrails

- Generic management không làm mất specialized authority của từng document type.
- Báo giá NCC template luôn Word `.docx`.
- Báo cáo/Chứng thư/Excel template được quản lý chung nhưng mapping/fill phải tuân authority riêng khi được chốt.
- Template/version đã dùng không silent overwrite.
- Không đưa dữ liệu khách hàng/NCC/hồ sơ thật vào public repo.
- Design authority không đồng nghĩa product code đã implement.
- Không khóa implementation technology ở baseline này.
