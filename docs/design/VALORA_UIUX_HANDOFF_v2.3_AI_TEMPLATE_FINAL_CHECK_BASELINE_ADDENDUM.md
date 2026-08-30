# VALORA UI/UX v2.3 — Thiết lập mẫu tài liệu — Bước 4: Kiểm tra & hoàn tất

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Scope:** Dùng chung cho Word generic và Bảng tính; validation chuyên biệt theo format  
**Approved:** 30/08/2026

## 1. Authority

Bước 4 `Kiểm tra & hoàn tất` là checkpoint cuối của flow:

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

Baseline này không thay đổi authority của Bước 2/Bước 3, Generic Word Mapping/Review, Spreadsheet semantics hoặc specialized NCC template.

## 2. Mental model

Validation dùng ba mức:

```text
Blocking
Warning
Info
```

Template chỉ được coi là `Hợp lệ` khi không còn `Blocking`.

Không có silent publish. Việc hoàn tất/lưu template là thao tác explicit của người dùng.

## 3. Layout Baseline — Iteration 1

Desktop-first, Fluent 2, data/document-first.

- Header giữ context `Thiết lập mẫu tài liệu` và stepper 4 bước; Bước 4 là trạng thái hiện hành.
- Preview/Test fill là vùng lớn nhất của màn hình.
- Cột trái trong vùng làm việc là danh sách vùng dữ liệu/section, hỗ trợ trạng thái và focus/highlight.
- Khu vực trung tâm là preview Word hoặc Bảng tính theo đúng renderer/semantics của format.
- Panel phải là `Kết quả kiểm tra`, hiển thị summary Blocking / Warning / Info / số mục đã gán và danh sách issue.
- Chọn issue phải focus/highlight đúng vị trí trong preview.
- Có thao tác chạy lại kiểm tra sau khi sửa.
- Footer giữ `Quay lại`, `Lưu nháp`, `Chạy lại kiểm tra` và primary CTA hoàn tất khi đủ điều kiện.

## 4. Vùng chưa thiết lập

Vùng chưa thiết lập phải cho người dùng explicit chọn một trong các hướng:

```text
Gán dữ liệu
Bỏ qua có chủ đích
Đây là nội dung cố định
```

AI không được tự silent skip.

## 5. Validation dùng chung

Bước 4 phải kiểm tra tối thiểu:

- test fill;
- mapping/vùng dữ liệu;
- vùng chưa thiết lập;
- layout;
- format;
- repeating regions;
- nội dung tràn/không phù hợp vùng;
- khả năng định vị/focus issue;
- các thành phần template mà fill engine không bảo toàn được.

`Blocking` cản hoàn tất. `Warning` cho phép tiếp tục nhưng phải nêu rủi ro. `Info` chỉ cung cấp trạng thái/thông tin.

## 6. Word-specific validation

Với Word generic, kiểm tra theo Word semantics, tối thiểu gồm:

- field/region mapping;
- repeating table/row;
- text overflow;
- page break;
- footer/header và layout trang khi kiểm tra được;
- format tiền/ngày/số;
- vùng không còn tồn tại hoặc không định vị được;
- managed-region behavior theo authority Word hiện hành.

Preview Word là preview, không phải Word editor.

## 7. Bảng tính-specific validation

Bảng tính dùng validator riêng, không áp Word region semantics máy móc. Tối thiểu kiểm tra:

- workbook/sheet/range structure;
- header nhiều tầng, merged cells, section/group, repeating row;
- formula regions;
- relative references khi nhân dòng;
- Tổng cộng/Làm tròn;
- style, border, number/date format;
- ảnh/chứng cứ;
- print/page layout;
- workbook features có nguy cơ không được bảo toàn.

Formula authority phải được giữ. Với reference semantics đã khóa:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

AI/fill engine không được thay formula bằng static value hoặc business rule khác. Nếu engine không bảo toàn được feature nào, validation phải báo trước khi người dùng hoàn tất.

## 8. Primary completion rule

Primary CTA chỉ thể hiện trạng thái hoàn tất hợp lệ khi `Blocking = 0`.

Thao tác hoàn tất:

- ghi nhận mapping/configuration của Template Version;
- ghi nhận kết quả validation tương ứng;
- không silent publish;
- không silent overwrite Template Version đang được sử dụng.

## 9. Visual Authority

Mockup `Thiết lập mẫu tài liệu — Bước 4: Kiểm tra & hoàn tất — Iteration 1` được người dùng explicit nâng thành Baseline ngày 30/08/2026.

Mockup thể hiện cấu trúc visual chính thức: preview lớn + danh sách vùng + panel Kết quả kiểm tra + tools xử lý vùng chưa thiết lập + footer completion actions. Nội dung ví dụ trong mockup chỉ là dữ liệu minh họa, không khóa thành dữ liệu nghiệp vụ hay template cụ thể.

## 10. Guardrails

- Không silent accept mapping.
- Không silent skip vùng.
- Không silent publish.
- Không silent overwrite Template Version.
- Không đổi immutable company form.
- Không tự đổi template formula.
- Không biến custom field thành canonical field.
- Word và Bảng tính dùng chung shell/mental model nhưng validation/fill semantics chuyên biệt theo format.
- Design Authority không đồng nghĩa product code đã implement.
