# VALORA — Bước cuối Kết quả thẩm định giá — Iteration 1

**Trạng thái:** `ITERATION — CHƯA CHỐT BASELINE / KHÔNG PHẢI DESIGN AUTHORITY`

Mockup này là working visual mới nhất của bước cuối sau thao tác `Chọn nhà cung cấp đã xác nhận giá`.

## 1. Scope nghiệp vụ

Flow hiện tại:

```text
Hoàn tất các báo giá NCC riêng lẻ
→ Chọn nhà cung cấp đã xác nhận giá
→ Dựng lại các bảng kết quả theo biểu mẫu công ty
→ Xem trước / xuất dữ liệu phục vụ Báo cáo thẩm định giá
```

Không có màn hình NCCQ tổng hợp riêng sau bước chọn NCC.

## 2. Nguyên tắc authority quan trọng

**Ba bảng nghiệp vụ là biểu mẫu do công ty ban hành và có layout bất biến.**

Fluent Design 2 chỉ áp dụng cho:

- application shell;
- sidebar / breadcrumb / header;
- command bar / button;
- panel thông tin, nguồn dữ liệu, lịch sử;
- trạng thái / progress / warning;
- spacing và surface bên ngoài bảng.

Fluent Design 2 **không được** dùng để redesign cấu trúc biểu mẫu công ty.

Không được tự ý:

- đổi thứ tự cột;
- đổi tên heading;
- tách một cột nghiệp vụ thành nhiều cột;
- gộp các cột khác với mẫu;
- thêm cột phân tích vào bảng chính;
- đổi cách trình bày section/header/tổng cộng/làm tròn nếu mẫu quy định;
- thay bảng kết quả bằng dashboard hoặc bảng công thức khác.

Thông tin bổ sung như lineage, warning, chênh lệch, nguồn chứng cứ phải đặt **ngoài biểu mẫu** bằng panel/drawer/tooltip.

## 3. Bảng 1 — Đặc điểm kinh tế - kỹ thuật

Cấu trúc bắt buộc theo mẫu công ty:

```text
STT
| Tên tài sản
| Đặc điểm kinh tế - kỹ thuật
| ĐVT
| SL
```

Toàn bộ thông tin kỹ thuật của một thiết bị phải nằm **trong cùng một ô `Đặc điểm kinh tế - kỹ thuật`**, theo đúng cách trình bày trong báo cáo mẫu, ví dụ các dòng/bullet về:

- Thương hiệu;
- Xuất xứ;
- Mã sản phẩm / Model;
- Kích thước;
- Công suất / năng suất;
- vật liệu / cấu tạo;
- năm sản xuất;
- tình trạng;
- các thông số kỹ thuật khác.

Không tách các thông số này thành nhiều cột riêng trong UI chính.

## 4. Bảng 2 — Tổng hợp giá các nhà cung cấp

Cấu trúc bắt buộc theo mẫu công ty:

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

- mỗi NCC chỉ có **cột đơn giá**;
- **không có cột Thành tiền NCC**;
- không thêm `Giá thấp nhất`, `% chênh lệch`, `Cao nhất - thấp nhất` vào bảng chính nếu mẫu công ty không có;
- `Tổ TĐG đánh giá` giữ đúng `Đơn giá | Thành tiền`;
- hàng `Tổng cộng` giữ đúng pattern mẫu.

## 5. Bảng 3 — Kết quả thẩm định giá

Cấu trúc bắt buộc theo mẫu công ty:

```text
STT
| Tên tài sản
| ĐVT
| SL
| Đơn giá
| Thành tiền
```

Cuối bảng giữ đúng pattern mẫu:

- `Tổng cộng`;
- `Làm tròn`;
- dòng tổng giá trị bằng số;
- dòng bằng chữ khi mẫu yêu cầu.

Không thay bằng bảng `Nội dung | Công thức | Giá trị | Ghi chú` hoặc dạng dashboard khác.

## 6. Visual working iteration

Iteration 1 giữ:

- Valora shell theo Fluent 2, desktop-first;
- breadcrumb theo hồ sơ;
- progress compact: `Chọn NCC đã xác nhận giá → Dựng bảng Đặc điểm KTKT → Dựng bảng tổng hợp giá NCC → Dựng bảng kết quả thẩm định giá`;
- command bar: `Xem trước báo cáo`, `Xuất ra Excel`, `Xuất ra Word`, CTA đi tiếp;
- ba bảng biểu mẫu là vùng trung tâm và không bị card hóa/redesign;
- panel phải chỉ hiển thị thông tin hồ sơ, NCC đã xác nhận, nguồn dữ liệu/chứng cứ và lịch sử hoạt động;
- dữ liệu hiển thị trong mockup là dữ liệu giả lập.

## 7. Trạng thái thiết kế

Mockup này là **working iteration mới nhất** cho bước cuối `Kết quả thẩm định giá`.

Nó **chưa phải baseline authority**. Chỉ khi người dùng nói `chốt baseline` hoặc `nâng bước cuối thành authority` mới được nâng thành baseline và cập nhật Handoff authority.

Các mockup bước cuối trước iteration này bị superseded nếu chúng:

- thay đổi bố cục ba bảng công ty;
- tách thông tin KTKT thành nhiều cột;
- thêm cột Thành tiền NCC;
- dùng bảng kết quả thẩm định không đúng mẫu gốc.
