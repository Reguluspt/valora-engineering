# VALORA UI/UX Handoff v2.3 — AI Template Review & Edit Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Baseline:** `Thiết lập mẫu tài liệu — Bước 3: Rà soát & chỉnh sửa — Iteration 1`  
**Scope:** User review/edit of AI-proposed template mappings for Word and Bảng tính  
**Ngày chốt:** 30/08/2026

Addendum này ghi nhận quyết định explicit mới nhất của người dùng: mockup **Bước 3 — Rà soát & chỉnh sửa** được nâng thành **Baseline / Design Authority**.

Authority này là child baseline của `AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM` và khóa interaction sau bước `AI phân tích & đề xuất`.

## A. Flow authority

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

Bước 3 là checkpoint người dùng trực tiếp kiểm soát mapping. AI proposal không được coi là final chỉ vì confidence cao.

## B. Mục tiêu Bước 3

Người dùng phải có thể:

- xem lại toàn bộ mapping AI đề xuất;
- xác nhận mapping đúng;
- sửa/gán lại mapping;
- bổ sung trường AI bỏ sót;
- bỏ qua vùng không cần mapping;
- phân biệt vùng dữ liệu với vùng công thức/nội dung cố định/user-owned;
- xem vị trí tương ứng trực tiếp trong preview;
- lưu nháp và quay lại mà không mất thay đổi;
- chuyển sang Bước 4 sau khi đã rà soát đủ các vấn đề cần xác nhận.

## C. Layout authority

Desktop-first, Fluent 2, data-heavy.

Bố cục chính:

```text
┌─────────────────────────────────────────────────────────────┐
│ Stepper + command actions                                  │
├────────────────────────────────────┬────────────────────────┤
│ Preview tài liệu / Bảng tính       │ Tổng quan mapping      │
│                                    │ + danh sách mapping     │
│ vùng được chọn được highlight      │ + trạng thái            │
├────────────────────────────────────┼────────────────────────┤
│ Chi tiết vùng đang chọn            │                        │
├────────────────────────────────────┴────────────────────────┤
│ Bổ sung trường AI bỏ sót                                    │
└─────────────────────────────────────────────────────────────┘
```

Preview là vùng lớn nhất. Panel mapping bên phải hỗ trợ rà soát nhanh theo nhóm nghiệp vụ.

## D. Mapping status authority

Bước 3 dùng tối thiểu bốn trạng thái:

```text
Đã mapping
Cần xác nhận
Chưa mapping
Đã bỏ qua
```

Ý nghĩa:

- `Đã mapping`: AI confidence cao hoặc user đã xác nhận/gán;
- `Cần xác nhận`: AI có đề xuất nhưng user cần kiểm tra;
- `Chưa mapping`: vùng có khả năng cần dữ liệu nhưng chưa có mapping;
- `Đã bỏ qua`: user đã explicit xác nhận vùng không dùng mapping.

Không coi `Đã bỏ qua` và `Chưa mapping` là cùng một trạng thái.

## E. Right-side mapping panel

Panel phải có:

- tổng quan số lượng theo trạng thái;
- search vùng/dữ liệu;
- filter trạng thái;
- grouping theo ngữ nghĩa tài liệu;
- mỗi mapping hiển thị vị trí/vùng, dữ liệu đang gán, trạng thái;
- action focus/highlight vị trí tương ứng trong preview.

Với Bảng tính có thể group theo:

```text
Thông tin chung bảng
Thông tin tài sản
Tổng cộng
Nhóm tài sản (Section)
Ảnh/Chứng cứ
Khác
```

Grouping có thể thay đổi theo loại template nhưng mental model trên là baseline cho case Bảng tính Iteration 1.

## F. Selected-region inspector

Khi người dùng chọn vùng trong preview hoặc mapping list, panel chi tiết phải cho biết bằng ngôn ngữ nghiệp vụ:

- vùng đang chọn;
- ý nghĩa/loại vùng;
- nội dung hoặc công thức hiện tại;
- dữ liệu đang gán;
- trạng thái;
- giải thích AI nếu mapping do AI đề xuất;
- các action phù hợp.

Action tối thiểu:

```text
Giữ nguyên / Xác nhận
Đổi gán dữ liệu
Không dùng vùng này
```

Với vùng công thức, ưu tiên action `Giữ công thức từ mẫu`; không ép gán source field nếu công thức là presentation/template logic.

## G. Bổ sung trường AI bỏ sót — mandatory

Đây là capability bắt buộc và là một phần trực quan của Bước 3.

Có khu vực `Bổ sung trường AI bỏ sót` với hai mental models tương đương:

```text
Chọn vị trí trước
→ chọn ô/vùng/đoạn trong preview
→ chọn dữ liệu VALORA
→ Gán
```

hoặc:

```text
Chọn dữ liệu trước
→ chọn field VALORA
→ chọn vị trí trong preview
→ Gán
```

UI phải cho phép chuyển cách thêm nếu cần; không khóa user vào workflow AI.

Nếu không tìm thấy field phù hợp, có action `Tạo trường tùy chỉnh` theo guardrail của AI Template Assistant authority.

## H. Bảng tính interaction authority

Với Bảng tính:

- preview có sheet context, grid/column/row semantics;
- user có thể chọn cell/range/column/row mẫu/section;
- mapping ưu tiên vùng/cột/dòng mẫu thay vì map từng cell lặp;
- highlight phải thể hiện vùng mapping trên workbook preview;
- formula region được phân biệt với data region;
- image/evidence region có thể là một mapping category riêng.

Case `Bang Tinh - HĐ 42.xlsx` tiếp tục là reference case cho Iteration 1.

### Formula authority

Cột H của dòng tài sản giữ công thức template:

```text
Hn = MIN(En:Gn)
```

Cột I giữ:

```text
In = Dn*Hn
```

Bước 3 phải cho người dùng thấy đây là `Giữ công thức từ mẫu`, không mô tả sai thành source data mapping.

AI/user review không được vô tình biến formula cell thành static data field.

## I. Word interaction authority

Cùng Bước 3 áp dụng cho Word generic với preview Word thay workbook grid.

User có thể:

- chọn đoạn/vị trí/table/repeating row;
- xem mapping AI;
- xác nhận/sửa/bỏ mapping;
- bổ sung field AI bỏ sót;
- đánh dấu nội dung cố định;
- chọn `Người dùng tự chỉnh trong Word` khi phù hợp.

Không bắt user hiểu Content Control/Region ID/source path.

## J. Navigation & persistence

Bước 3 có tối thiểu:

- `Quay lại Bước 2`;
- `Lưu nháp`;
- `Tiếp tục: Kiểm tra & hoàn tất`.

Quay lại Bước 2 hoặc lưu nháp không làm mất các thay đổi mapping đã thực hiện.

Bước 3 chưa publish template. Publish/hoàn tất chỉ xảy ra theo explicit user action ở bước phù hợp.

## K. Relationship với Bước 4

Bước 3 tập trung vào **mapping correctness và user intent**.

Bước 4 tập trung vào **test fill, validation và khả năng hoàn tất template**.

Các vùng `Chưa mapping` hoặc `Cần xác nhận` có thể được chuyển sang Bước 4 để validation nếu policy cho phép, nhưng Blocking ở Bước 4 phải ngăn trạng thái `Template hợp lệ`.

Không silently coi unresolved mapping là hợp lệ.

## L. Guardrails

- AI proposal không phải quyết định cuối.
- User luôn có quyền bổ sung field AI bỏ sót.
- User luôn có quyền sửa/xóa mapping AI.
- `Đã bỏ qua` phải là explicit user intent, không do AI tự bỏ qua silent.
- Formula template không được biến thành static value mapping.
- Không đổi cấu trúc biểu mẫu công ty.
- Không tự đổi `MIN(E:G)`.
- Không silent overwrite Template Version.
- Không publish ở Bước 3.
- Không đưa dữ liệu khách hàng/NCC/hồ sơ thật vào public repo.
- Design Authority không đồng nghĩa product code đã implement.

## M. Scope boundary

Baseline này khóa UX/interaction/mental model của Bước 3 cho Word generic và Bảng tính. Không khóa implementation technology, AI provider, confidence formula hoặc backend API contract.
