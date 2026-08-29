# VALORA UI/UX Handoff v2.3 — Addendum Baseline Bước cuối Kết quả thẩm định giá

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Áp dụng từ:** sau khi người dùng chốt `Bước cuối — Kết quả thẩm định giá — Iteration 1` làm baseline.

Authority chi tiết: [`assets/VALORA_FINAL_RESULT_BASELINE_v2.3.md`](./assets/VALORA_FINAL_RESULT_BASELINE_v2.3.md).

Addendum này **supersede** mọi mô tả/iteration trước mâu thuẫn với các quyết định dưới đây.

## A. Routing sau báo giá NCC

Flow mới nhất được khóa:

```text
Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC riêng lẻ
→ Chọn nhà cung cấp đã xác nhận giá
→ BƯỚC CUỐI: Kết quả thẩm định giá
   1. Dựng lại Bảng Đặc điểm kinh tế - kỹ thuật
   2. Dựng lại Bảng Tổng hợp giá các nhà cung cấp
   3. Dựng lại Bảng Kết quả thẩm định giá
→ Output phục vụ Báo cáo & Chứng thư
```

**Không có màn `NCCQ tổng hợp` riêng** sau CTA `Chọn nhà cung cấp đã xác nhận giá`.

Mọi iteration NCCQ tổng hợp được dựng sau khi các báo giá riêng lẻ hoàn tất nhưng trước bước chọn/dựng bảng kết quả không còn authority.

## B. Quan hệ với S17 / Hoàn tất hồ sơ

Quyết định mới nhất của người dùng xác định bước dựng 03 bảng kết quả là **bước cuối sau khi chọn NCC đã xác nhận giá**.

Vì vậy, các mô tả cũ suy diễn rằng người dùng phải đi qua một dashboard readiness `S17 — Hoàn tất hồ sơ` riêng **giữa** `Chọn nhà cung cấp đã xác nhận giá` và `Kết quả thẩm định giá` bị superseded.

Baseline `Hoàn tất một báo giá của một NCC` đã chốt trước đó vẫn hợp lệ vì đó là child flow của NCCQ cho **01 báo giá / 01 NCC**, không phải dashboard toàn hồ sơ.

Nếu sau này cần một hành động `Hoàn tất hồ sơ` về mặt trạng thái hệ thống/audit, action đó phải được thiết kế không làm thay đổi routing đã khóa ở trên, trừ khi người dùng duyệt business rule mới.

## C. Company form = immutable layout

03 bảng tại bước cuối là **biểu mẫu do công ty ban hành**. Layout/schema của chúng là authority nghiệp vụ và không được redesign theo Fluent 2.

Fluent 2 chỉ áp dụng cho shell/context xung quanh.

### C1. Bảng Đặc điểm kinh tế - kỹ thuật

Bắt buộc:

```text
STT | Tên tài sản | Đặc điểm kinh tế - kỹ thuật | ĐVT | SL
```

Toàn bộ đặc điểm của một tài sản nằm trong **một ô `Đặc điểm kinh tế - kỹ thuật`**. Không tách thương hiệu/model/xuất xứ/công suất/kích thước/năm SX/tình trạng thành các cột riêng.

### C2. Bảng Tổng hợp giá các nhà cung cấp

Bắt buộc:

```text
STT | Tên tài sản | ĐVT | SL
| Đơn giá tham khảo: NCC1 | NCC2 | NCC3
| Tổ TĐG đánh giá: Đơn giá | Thành tiền
```

- mỗi NCC chỉ có **đơn giá**;
- **không có Thành tiền NCC**;
- không thêm cột `Giá thấp nhất`, `% chênh lệch`, `Cao nhất - thấp nhất` hoặc analytics khác vào bảng chính.

### C3. Bảng Kết quả thẩm định giá

Bắt buộc:

```text
STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền
```

Giữ `Tổng cộng`, `Làm tròn`, tổng giá trị bằng số và bằng chữ theo mẫu công ty.

## D. STT / lineage

`STT` tiếp tục là lineage/order bất biến của danh mục gốc trên cả 03 bảng.

Việc chọn NCC, dựng lại bảng hay xuất báo cáo không được đánh lại STT.

Giá trong Bảng Tổng hợp NCC phải truy vết được tới:

`NCC → Báo giá → Dòng tài sản → Đơn giá NCC đã xác nhận → File ký/đóng dấu`.

Thông tin KTKT và giá Tổ TĐG đánh giá phải giữ lineage tới dữ liệu làm việc tương ứng; hệ thống không được làm mất dữ liệu gốc/nguồn.

## E. Fluent 2 visual authority

Được phép dùng Fluent 2 cho:

- sidebar/navigation;
- breadcrumb/header;
- command bar/button/menu;
- progress indicator;
- panel hồ sơ/NCC/chứng cứ/lịch sử;
- warning/status/drawer/tooltip;
- spacing/elevation/surface bên ngoài bảng.

Không được:

- card hóa 03 biểu mẫu;
- đổi border/header hierarchy của bảng theo cách khác mẫu;
- thêm visual analytics vào trong schema bảng;
- đổi cột để tối ưu viewport.

Nếu cần thêm context, dùng panel/drawer/tooltip hoặc horizontal/vertical scroll phù hợp thay vì thay schema biểu mẫu.

## F. Screen inventory authority bổ sung

| Scope | Authority v2.3 |
|---|---|
| NCCQ tổng hợp quản lý báo giá | Baseline NCCQ Iteration 6 |
| NCCQ child — Hoàn tất 01 báo giá NCC | Baseline Iteration 3 đã duyệt |
| NCCQ post-completion aggregate trước chọn NCC | **Không dùng / superseded** |
| Bước cuối — Kết quả thẩm định giá | **Baseline Iteration 1 — authority addendum này** |

## G. Superseded visuals

Các mockup bước cuối trước baseline này không còn authority nếu có một trong các lỗi:

- tách KTKT thành nhiều cột;
- thêm Thành tiền cho từng NCC;
- thêm cột phân tích không có trong mẫu;
- thay bảng Kết quả thẩm định bằng schema dashboard khác;
- tự điều chỉnh bố cục biểu mẫu để bám Fluent 2.

## H. Nhiệm vụ tiếp theo

Sau khi baseline này được chốt, UI/UX nên chuyển sang **cách tạo/preview Báo cáo thẩm định giá & Chứng thư từ dữ liệu đã khóa**, hoặc module/output tiếp theo mà người dùng yêu cầu; không quay lại chèn thêm một màn NCCQ aggregate trung gian nếu chưa có business rule mới.