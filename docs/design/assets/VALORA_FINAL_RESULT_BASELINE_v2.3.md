# VALORA — Bước cuối Kết quả thẩm định giá — Baseline Authority v2.3

**Nguồn duyệt:** `Bước cuối — Kết quả thẩm định giá — Iteration 1`  
**Trạng thái:** `BASELINE ĐÃ DUYỆT / DESIGN AUTHORITY`  
**Phạm vi:** Bước cuối sau thao tác `Chọn nhà cung cấp đã xác nhận giá`, dùng để dựng lại các bảng chính thức phục vụ Báo cáo thẩm định giá.

> Authority rule quan trọng: **03 bảng nghiệp vụ là biểu mẫu do công ty ban hành và có layout bất biến.** Fluent Design 2 chỉ áp dụng cho application shell và các vùng điều khiển xung quanh; không được redesign cấu trúc biểu mẫu.

## 1. Flow đã khóa

```text
Hoàn tất các báo giá NCC riêng lẻ
→ Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
   → Dựng lại Bảng Đặc điểm kinh tế - kỹ thuật
   → Dựng lại Bảng Tổng hợp giá các nhà cung cấp
   → Dựng lại Bảng Kết quả thẩm định giá
→ Xem trước / xuất dữ liệu phục vụ Báo cáo & Chứng thư
```

Không có màn hình `NCCQ tổng hợp` riêng sau CTA `Chọn nhà cung cấp đã xác nhận giá`.

Màn hình này là bước tổng hợp cuối của dữ liệu thẩm định trước output báo cáo; không tạo thêm một dashboard readiness toàn hồ sơ nếu không có business rule mới được người dùng duyệt.

## 2. Nguyên tắc `Company form = immutable layout`

UI/UX không được tự ý:

- đổi thứ tự cột;
- đổi tên heading/caption do biểu mẫu quy định;
- tách một cột nghiệp vụ thành nhiều cột;
- gộp cột khác với mẫu;
- thêm cột phân tích vào bảng chính;
- đổi cách trình bày section/header/subsection;
- đổi pattern `Tổng cộng`, `Làm tròn`, dòng bằng số hoặc bằng chữ;
- thay bảng gốc bằng dashboard/KPI/chart hoặc một bảng có schema khác.

Thông tin bổ sung như lineage, warning, chênh lệch, nguồn chứng cứ, audit chỉ được đặt **ngoài biểu mẫu** bằng Fluent 2 panel/drawer/tooltip/contextual surface.

## 3. Bảng 1 — Đặc điểm kinh tế - kỹ thuật

Cấu trúc bắt buộc:

```text
STT
| Tên tài sản
| Đặc điểm kinh tế - kỹ thuật
| ĐVT
| SL
```

Toàn bộ thông tin kỹ thuật của **một tài sản** phải nằm trong **một ô duy nhất `Đặc điểm kinh tế - kỹ thuật`**, trình bày theo mẫu báo cáo của công ty, ví dụ:

- Thương hiệu;
- Xuất xứ;
- Mã sản phẩm / Model;
- Kích thước;
- Công suất / năng suất;
- vật liệu / cấu tạo;
- năm sản xuất;
- tình trạng;
- các thông số kỹ thuật khác.

Không tách các thuộc tính này thành nhiều cột riêng.

Nếu danh mục gốc có dòng section/hạng mục như `HỆ THỐNG ...`, `I. ...`, `II. ...`, UI phải giữ cách thể hiện tương ứng của biểu mẫu gốc.

`STT` tiếp tục là lineage/order bất biến của danh mục gốc.

## 4. Bảng 2 — Tổng hợp giá các nhà cung cấp

Cấu trúc bắt buộc:

```text
STT
| Tên tài sản
| ĐVT
| SL
| Đơn giá tham khảo
    | NCC 1
    | NCC 2
    | NCC 3
| Tổ TĐG đánh giá
    | Đơn giá
    | Thành tiền
```

Rule khóa:

- mỗi NCC chỉ có **01 cột đơn giá**;
- **không có cột Thành tiền NCC**;
- không thêm `Giá thấp nhất`, `% chênh lệch`, `Cao nhất - thấp nhất` hoặc cột phân tích khác vào biểu mẫu chính;
- `Tổ TĐG đánh giá` giữ đúng 02 cột `Đơn giá | Thành tiền`;
- hàng `Tổng cộng` giữ đúng pattern của mẫu công ty;
- tên NCC hiển thị theo các NCC/báo giá đã được người dùng chọn ở bước trước;
- số tiền phải truy vết được tới `NCC → báo giá → dòng thiết bị → đơn giá NCC đã xác nhận → file ký/đóng dấu`.

Hệ thống có thể gợi ý/điền lại dữ liệu từ các giá đã xác nhận nhưng **không được tự thay quyết định giá của Tổ TĐG** nếu chưa có thao tác của người dùng theo rule hiện hành.

## 5. Bảng 3 — Kết quả thẩm định giá

Cấu trúc bắt buộc:

```text
STT
| Tên tài sản
| ĐVT
| SL
| Đơn giá
| Thành tiền
```

Cuối bảng phải giữ đúng mẫu:

- `Tổng cộng`;
- `Làm tròn`;
- dòng tổng giá trị bằng số;
- dòng bằng chữ khi biểu mẫu yêu cầu.

Không thay bằng schema kiểu `Nội dung | Công thức | Giá trị | Ghi chú` hoặc dashboard tổng hợp khác.

## 6. Fluent Design 2 — phạm vi được phép

Fluent 2 được áp dụng cho:

- Valora application shell;
- sidebar/navigation;
- breadcrumb/header;
- command bar/button/menu;
- progress/step indicator;
- panel thông tin hồ sơ;
- panel NCC đã xác nhận;
- panel nguồn dữ liệu/chứng cứ;
- audit/history;
- warning/status/tooltip/drawer;
- spacing, elevation, neutral surface **bên ngoài** 03 biểu mẫu.

Không `card hóa`, bo góc hoặc styling lại 03 bảng theo cách làm thay đổi hình thức/structure của biểu mẫu công ty.

## 7. Visual baseline — Iteration 1

Visual baseline giữ:

- desktop-first, Fluent 2 shell;
- breadcrumb theo context hồ sơ;
- progress compact: `Chọn NCC đã xác nhận giá → Dựng bảng Đặc điểm KTKT → Dựng bảng tổng hợp giá NCC → Dựng bảng kết quả thẩm định giá`;
- command bar có các thao tác như `Xem trước báo cáo`, `Xuất ra Excel`, `Xuất ra Word` khi capability tương ứng được triển khai;
- 03 bảng công ty chiếm vùng nội dung chính;
- panel phải chỉ dùng cho context/lineage/chứng cứ/lịch sử, không thay đổi schema bảng;
- dữ liệu minh họa trong mockup không phải dữ liệu khách hàng/NCC thật.

## 8. Authority / supersession

`Bước cuối — Kết quả thẩm định giá — Iteration 1` đã được người dùng duyệt và chốt baseline.

Các mockup trước bị **superseded** nếu chúng:

- tách thông tin KTKT thành nhiều cột;
- thêm `Thành tiền` cho từng NCC;
- thêm cột phân tích không có trong mẫu;
- dùng bảng kết quả thẩm định khác schema gốc;
- tự điều chỉnh bố cục 03 bảng để bám Fluent 2.

Authority hiện hành là tài liệu này cùng addendum tương ứng của `VALORA_UIUX_HANDOFF_v2.3`.