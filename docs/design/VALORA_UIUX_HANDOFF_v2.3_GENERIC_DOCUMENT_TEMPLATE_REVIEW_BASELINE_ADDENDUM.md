# VALORA UI/UX Handoff v2.3 — Generic Document Template Review Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Baseline:** `Kiểm tra & hoàn tất template — Iteration 1`  
**Flow cha:** `Mapping Template tài liệu generic — Iteration 2`  
**Scope chính:** `Microsoft 365 Document Workspace / 03_Hợp đồng`  
**Ngày chốt:** 30/08/2026

Addendum này ghi nhận quyết định explicit mới nhất của người dùng: mockup màn hình **Bước 3 — Kiểm tra & hoàn tất template** được nâng thành **Baseline / Design Authority**.

Authority này là bước 3 của flow generic đã khóa:

```text
1. Chọn mẫu Word
→ 2. Đánh dấu vị trí
→ 3. Kiểm tra & hoàn tất
```

## A. Mục tiêu

Cho phép người dùng nghiệp vụ kiểm tra kết quả fill bằng dữ liệu mẫu/thử, phát hiện mapping còn thiếu hoặc vấn đề trình bày, điều hướng trực tiếp tới vị trí cần xử lý và chỉ hoàn tất template khi không còn lỗi Blocking.

Màn hình không yêu cầu người dùng hiểu Region ID, field path, source collection, repeating-region hoặc schema kỹ thuật.

## B. Bố cục authority

Desktop-first, Fluent 2, cùng shell với Mapping Template tài liệu generic.

Bố cục ba vùng:

```text
┌ Tổng quan / Kết quả kiểm tra ┐ ┌ Preview Word đã fill ┐ ┌ Dữ liệu test / Issue / Tiếp theo ┐
│ Thông tin template           │ │                      │ │ Nguồn dữ liệu kiểm tra          │
│ Tổng quan mapping            │ │  Word preview lớn    │ │ Đổi hồ sơ/dữ liệu test          │
│ Kết quả kiểm tra             │ │  highlight mapping   │ │ Trường chưa mapping             │
│ Vấn đề cần xử lý             │ │  cuộn/xem tài liệu   │ │ Cảnh báo                         │
└──────────────────────────────┘ └──────────────────────┘ └───────────────────────────────────┘
```

Preview Word là vùng trung tâm lớn nhất.

Header giữ stepper 3 bước và các thao tác:

- `Quay lại bước 2`;
- `Xem trước kết quả`;
- primary CTA `Hoàn tất & lưu template`.

## C. Tổng quan template và mapping

Panel trái hiển thị bằng ngôn ngữ nghiệp vụ:

- Tên template;
- Loại tài liệu;
- Phiên bản template;
- Người tạo;
- Ngày tạo;
- số lượng trường dữ liệu;
- số bảng lặp/danh mục;
- số giá trị tính toán;
- số vùng người dùng tự chỉnh;
- tổng số vị trí mapping.

Không hiển thị identifier kỹ thuật mặc định.

## D. Kết quả kiểm tra

Tối thiểu tổng hợp:

```text
Đã mapping
Chưa mapping
Cảnh báo
Không tìm thấy vùng
```

Severity tuân validation authority chung:

- `Blocking`: phải xử lý trước khi hoàn tất template;
- `Warning`: được phép hoàn tất nhưng phải hiển thị rõ;
- `Info`: thông tin hỗ trợ, không chặn.

Trạng thái `Template hợp lệ` chỉ xuất hiện khi không còn Blocking.

Nếu còn Blocking, primary CTA hoàn tất phải disabled hoặc dẫn người dùng xử lý Blocking thay vì lưu template ở trạng thái sẵn sàng sử dụng.

## E. Preview Word đã fill

Preview sử dụng dữ liệu test và hiển thị kết quả fill trực tiếp trên mẫu Word.

Authority:

- giữ bố cục Word của template;
- highlight các vùng mapping khi bật `Hiển thị vùng mapping`;
- cho phép xem các trang/tài liệu theo preview phù hợp;
- field đã fill phải dễ phân biệt khi kiểm tra nhưng highlight không được trở thành nội dung của file thật;
- bảng danh mục/repeating row phải render nhiều dòng từ dữ liệu test;
- format tiền, ngày, số lượng và giá trị dẫn xuất phải được thể hiện sau fill;
- cảnh báo text dài/page break/footer phải có thể điều hướng tới context liên quan.

Preview trong bước test không phải Word editor; chỉnh narrative/file thật vẫn thuộc Microsoft Word.

## F. Dữ liệu dùng để kiểm tra

Panel phải cho người dùng chọn một bộ dữ liệu/hồ sơ test phù hợp mà không cần cấu hình schema kỹ thuật.

Có thao tác `Đổi hồ sơ khác` hoặc semantic tương đương để kiểm tra template với dữ liệu khác.

Dữ liệu test chỉ phục vụ preview/validation; không biến template thành tài liệu nghiệp vụ chính thức và không tạo quyết định nghiệp vụ.

Không đưa dữ liệu khách hàng/NCC/hồ sơ thật vào public repository hoặc tài liệu design authority.

## G. Trường chưa mapping và issue navigation

Danh sách trường/vùng chưa mapping hiển thị tên nghiệp vụ + vị trí dễ hiểu, ví dụ:

```text
Điều khoản bổ sung (nếu có)
Vị trí: Trang 4 — Mục 5.2
[Đi đến]
```

CTA `Đi đến` phải đưa preview tới đúng context cần xử lý.

Nếu issue cần sửa mapping, người dùng có thể quay lại bước 2 mà không mất mapping đã thực hiện.

## H. Warning UX

Warning phải nói bằng ngôn ngữ người dùng, nêu:

- nội dung/vùng nào có vấn đề;
- ảnh hưởng có thể xảy ra;
- CTA `Xem chi tiết`/`Đi đến` khi có thể.

Ví dụ các nhóm warning được phép:

- nội dung quá dài, có thể xuống dòng hoặc làm thay đổi bố cục;
- page break bất thường;
- footer/header cần kiểm tra;
- format tiền/ngày không như mong đợi;
- bảng lặp có khả năng tràn trang.

Không hiển thị stack trace/exception/JSON cho người dùng cuối.

## I. Hoàn tất & lưu template

Primary CTA: `Hoàn tất & lưu template`.

Khi thực hiện thành công:

- lưu Template Version hiện tại;
- lưu Mapping Definition/version tương ứng;
- lưu validation result cần thiết cho audit;
- template chuyển sang trạng thái sẵn sàng sử dụng theo lifecycle nếu không còn Blocking và người dùng thực hiện thao tác explicit;
- không silent overwrite template/version đã dùng trước đó.

Sau khi lưu, template có thể được dùng để tạo tài liệu mới, chỉnh sửa mapping khi cần theo lifecycle, hoặc tạo phiên bản mới khi template thay đổi.

## J. Quan hệ với Document Template Engine

Bước 3 kiểm chứng contract:

```text
Template Version
+ Mapping Definition
+ Document Data Model / Test Snapshot
→ Fill Engine
→ Validation
→ Preview
→ User explicit completion
```

Authority này khóa UX/mental model/domain boundary, không khóa implementation technology như Open XML SDK, Microsoft Graph, Content Control hay thư viện render Word cụ thể.

## K. Guardrails

- Người dùng nghiệp vụ không phải hiểu cấu trúc mapping kỹ thuật.
- Không tự sửa mapping chỉ để làm validation pass.
- Không tự bỏ qua Blocking.
- Warning không được giả thành Blocking nếu business rule không yêu cầu.
- `Hoàn tất & lưu template` là thao tác explicit của người dùng.
- Preview/test không tạo tài liệu nghiệp vụ chính thức.
- Mapping quay lại bước 2 phải được bảo toàn.
- Template/version đã dùng không silent overwrite.
- Không xây fake Word editor.
- Design authority không đồng nghĩa product code đã implement.
