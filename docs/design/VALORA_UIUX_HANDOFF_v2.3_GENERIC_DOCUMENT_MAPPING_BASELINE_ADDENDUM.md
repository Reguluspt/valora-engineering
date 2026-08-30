# VALORA UI/UX Handoff v2.3 — Generic Document Template Mapping Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Baseline:** `Mapping Template tài liệu generic — Iteration 2`  
**Scope chính:** `Microsoft 365 Document Workspace / 03_Hợp đồng`  
**Ngày chốt:** 30/08/2026

Addendum này ghi nhận quyết định explicit mới nhất của người dùng: **mockup Iteration 2 — Mapping Template tài liệu generic, tối ưu cho người nghiệp vụ không rành IT — được nâng thành Baseline / Design Authority**.

Khi có mâu thuẫn trong đúng scope Mapping Template tài liệu generic, addendum này supersede các working iteration/mô tả trước đó, bao gồm Iteration 1 thiên về giao diện kỹ thuật/admin.

## A. Mục tiêu UX

Màn hình Mapping Template tài liệu phải cho phép người dùng nghiệp vụ cấu hình template Word mà **không cần hiểu thuật ngữ kỹ thuật** như `Region ID`, `field path`, `source collection`, `repeating region`, `mapping definition` hoặc `sync policy`.

Mental model authority:

```text
Chọn dữ liệu bên trái
→ Click vị trí cần điền trong Word
→ VALORA tạo mapping phía sau
→ Kiểm tra thử
```

UI phải ưu tiên ngôn ngữ nghiệp vụ tiếng Việt; cấu trúc kỹ thuật chỉ tồn tại ở lớp engine/configuration phía sau hoặc chế độ nâng cao nếu sau này thực sự cần.

## B. Flow baseline — 03 bước

```text
1. Chọn mẫu Word
→ 2. Đánh dấu vị trí
→ 3. Kiểm tra & hoàn tất
```

Không dùng wizard dài hoặc bắt người dùng khai báo mapping bằng form kỹ thuật trước khi tương tác với tài liệu.

Primary interaction tại bước 2 là **preview Word trực tiếp + chọn dữ liệu nghiệp vụ**.

## C. Bố cục visual authority — Iteration 2

Desktop-first, Fluent 2, cùng Valora shell với Microsoft 365 Document Workspace.

Bố cục chính:

```text
┌ Nguồn dữ liệu nghiệp vụ ┐ ┌ Preview Word / vị trí mapping ┐ ┌ Vị trí đang chọn ┐
│ Hồ sơ                   │ │                               │ │ Dữ liệu sẽ điền │
│ Khách hàng              │ │        Template Word          │ │ Cách cập nhật   │
│ Hợp đồng                │ │        trực quan              │ │ Giá trị thử      │
│ Danh mục tài sản        │ │                               │ │ Trạng thái       │
└─────────────────────────┘ └───────────────────────────────┘ └──────────────────┘
```

Các thành phần authority:

- thanh bước 3 bước phía trên;
- hướng dẫn ngắn: `Chọn dữ liệu bên trái → Click vào vị trí cần điền trong Word`;
- panel trái nhóm dữ liệu theo nghiệp vụ, có search;
- preview Word là bề mặt trung tâm lớn nhất;
- các vị trí đã/đang mapping được highlight trực tiếp trên Word;
- panel phải chỉ mô tả vị trí hiện tại bằng ngôn ngữ nghiệp vụ;
- footer/summary có tiến độ mapping và trạng thái `Đã mapping / Chưa mapping / Vùng người dùng`;
- có `Lưu nháp`, `Xem trước kết quả`, `Tiếp tục bước 3`;
- có Undo/Redo/Xóa mapping/Bỏ chọn vùng như thao tác hỗ trợ.

## D. Ngôn ngữ hiển thị cho người dùng

Không hiển thị mặc định:

- `Region ID`;
- `Source path`;
- `assets[]`;
- `MANAGED / INITIAL_ONLY / USER_OWNED`;
- `RepeatingRegion`;
- JSON/path/schema hoặc identifier kỹ thuật tương đương.

Thay bằng ngôn ngữ nghiệp vụ:

```text
Tự cập nhật khi dữ liệu thay đổi
Chỉ điền lần đầu
Người dùng tự chỉnh trong Word
Danh sách nhiều dòng
Giá trị tính toán
```

Ví dụ panel khi người dùng chọn vị trí `Ngày hợp đồng`:

```text
Bạn muốn điền dữ liệu gì vào đây?
[ Ngày hợp đồng ▼ ]

Khi dữ liệu thay đổi:
● Tự cập nhật khi dữ liệu thay đổi
○ Chỉ điền lần đầu

Giá trị thử:
30/08/2026
```

## E. Nguồn dữ liệu nghiệp vụ

Panel trái nhóm tối thiểu:

- `Thông tin hồ sơ`;
- `Khách hàng`;
- `Hợp đồng`;
- `Danh mục tài sản`;
- `Giá trị / phí` khi phù hợp;
- `Giá trị tính toán / dẫn xuất` khi phù hợp.

Người dùng chọn theo label nghiệp vụ; stable Field ID và Document Data Model được engine quản lý phía sau.

## F. Mapping field đơn

Interaction authority:

1. người dùng chọn dữ liệu nghiệp vụ hoặc click vị trí trong Word;
2. chọn dữ liệu cần điền;
3. chọn cách cập nhật bằng ngôn ngữ đơn giản;
4. xem giá trị thử;
5. mapping được ghi nhận ngay và highlight trên preview.

VALORA không yêu cầu người dùng nhập identifier kỹ thuật để hoàn tất mapping.

## G. Mapping bảng danh mục nhiều dòng

Đối với bảng Word có danh mục động, UI dùng mental model:

```text
Đây là dòng mẫu danh mục
→ Cột 1: STT
→ Cột 2: Tên tài sản
→ Cột 3: Đơn vị tính
→ Cột 4: Số lượng
→ ...
```

Người dùng không phải cấu hình `collection path`, `row template ID` hoặc `cell mapping path` bằng tay.

Engine phía sau vẫn phải giữ semantics repeating row/region và lineage STT gốc.

`STT` trong output lấy từ STT gốc của tài sản; sort/filter/mapping không được tự renumber.

## H. Các semantic mapping phía sau UI

Iteration 2 **không loại bỏ** contract kỹ thuật; nó chỉ ẩn complexity khỏi người dùng nghiệp vụ.

Engine có thể tiếp tục phân biệt các semantic logic:

- field đơn;
- derived field;
- repeating region;
- conditional region;
- user-owned/narrative region.

Về sync ownership, engine tiếp tục cần tương đương:

```text
Managed       → có thể cập nhật khi người dùng bấm Đồng bộ dữ liệu
Initial only  → fill lần đầu, sau đó không tự cập nhật
User owned    → VALORA không overwrite nội dung người dùng quản lý trong Word
```

Nhưng UI authority hiển thị các semantic này bằng câu nghiệp vụ trong §D.

## I. Fill / Sync guardrail

Template Word giữ layout: font, paragraph, bảng, border, header/footer, page setup, numbering và static wording.

VALORA fill/sync theo các vùng được mapping; không dùng cơ chế tìm-replace text mù toàn tài liệu.

Khi dữ liệu VALORA thay đổi:

```text
Đã đồng bộ
→ Cần đồng bộ
→ Xem thay đổi
→ Người dùng bấm Đồng bộ dữ liệu
→ Chỉ cập nhật vùng VALORA quản lý
→ Giữ nguyên narrative người dùng chỉnh trong Word
```

Không regenerate toàn bộ Word theo cách làm mất nội dung người dùng đã chỉnh.

Tài liệu `Đã phát hành` không được silent mutate; cần tạo revision/version mới theo lifecycle Document Workspace.

## J. Data / version boundary

Baseline UX này tương thích với kiến trúc đã khóa:

```text
VALORA Domain Data
→ Document Data Model
→ Data Snapshot
→ Template Version + Mapping Definition
→ Fill / Sync
→ Document Revision
→ Microsoft 365 Word file/version
```

Một Document Revision phải truy vết được template/version, snapshot và file/version đã dùng.

## K. Scope `03_Hợp đồng`

Baseline generic này áp dụng trước hết cho các tài liệu Word do VALORA sinh trong `03_Hợp đồng`, gồm khi nghiệp vụ phát sinh:

- Phiếu/Giấy yêu cầu;
- Danh mục;
- Thương thảo;
- Dự thảo hợp đồng;
- Hợp đồng thẩm định giá;
- Phụ lục;
- Nghiệm thu;
- Thanh lý;
- tài liệu hợp đồng khác.

Mỗi loại tài liệu có template/schema riêng nhưng **không tạo một Mapping Engine riêng cho từng loại tài liệu**.

## L. Generic engine principle

Design authority định hướng **một VALORA Document Template Engine dùng chung**.

`03_Hợp đồng`, báo giá NCC, Báo cáo và Chứng thư có thể tái sử dụng cùng core concepts fill/mapping/version/sync, nhưng mỗi document type vẫn có schema, validation và template authority riêng.

Điều này không tự động thay đổi baseline TM03/TM04 của báo giá NCC; khi reuse, UX nghiệp vụ cụ thể của module vẫn phải tôn trọng authority của module đó.

## M. Validation

Người dùng cuối tiếp tục thấy `Blocking / Warning / Info`, nhưng thông báo phải trả lời:

```text
Vấn đề gì
→ nằm ở vị trí nào trong tài liệu
→ ảnh hưởng gì
→ cần làm gì
```

Không phơi exception, JSON, schema path, HTTP/SQL hoặc lỗi kỹ thuật thô.

Các tình huống như thiếu dữ liệu bắt buộc, chưa gán vị trí bắt buộc, bảng danh mục chưa đủ cột cần thiết hoặc mapping xung đột có thể là Blocking theo dependency.

## N. Không khóa implementation technology

Baseline này khóa **UX, mental model và domain boundary**, không khóa công nghệ triển khai cụ thể.

Chưa được suy diễn từ authority này rằng engineering bắt buộc phải dùng:

- một loại Word Content Control cụ thể;
- Open XML SDK cụ thể;
- Microsoft Graph endpoint cụ thể;
- placeholder syntax cụ thể;
- một serialization/schema format cụ thể.

Các quyết định công nghệ/data contract chi tiết cần engineering review và ADR nếu thay đổi domain/version/sync boundary hiện có.

## O. Supersession

- **Iteration 2 là visual/interaction Design Authority hiện hành cho `Mapping Template tài liệu generic`.**
- Iteration 1 generic thiên về bảng kỹ thuật/admin chỉ còn giá trị lịch sử/tham khảo.
- Khi có mâu thuẫn giữa hai iteration generic, Iteration 2 thắng.
- `Đã duyệt mockup` ở phiên trước nay được nâng explicit thành `Baseline / Design Authority` theo yêu cầu người dùng ngày 30/08/2026.

## P. Trạng thái triển khai

Đây là design authority, **không đồng nghĩa product code đã implement**.

Không có thay đổi product code trong commit tạo authority này.