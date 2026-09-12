# VALORA — Bước cuối Kết quả thẩm định giá — Iteration 1

**Trạng thái:** `PROMOTED → BASELINE AUTHORITY`

Iteration 1 đã được người dùng duyệt và **chốt baseline**.

Authority hiện hành:

- [`VALORA_FINAL_RESULT_BASELINE_v2.3.md`](./VALORA_FINAL_RESULT_BASELINE_v2.3.md)
- `../VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md`

## Quyết định được chốt

- Sau `Chọn nhà cung cấp đã xác nhận giá`, hệ thống đi thẳng sang bước cuối `Kết quả thẩm định giá`; không có màn `NCCQ tổng hợp` riêng.
- 03 bảng nghiệp vụ là **biểu mẫu công ty ban hành — immutable layout**.
- Fluent Design 2 chỉ áp dụng cho shell và các control/context surface xung quanh bảng.
- Bảng 1 giữ đúng `STT | Tên tài sản | Đặc điểm kinh tế - kỹ thuật | ĐVT | SL`; toàn bộ thông tin kỹ thuật của một tài sản nằm trong một ô KTKT.
- Bảng 2 giữ đúng 03 cột **đơn giá NCC** và `Tổ TĐG đánh giá: Đơn giá | Thành tiền`; không có `Thành tiền NCC` hay cột phân tích bổ sung.
- Bảng 3 giữ đúng `STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền`, kèm `Tổng cộng / Làm tròn` và dòng bằng chữ theo mẫu.

Tài liệu iteration này chỉ còn vai trò lịch sử/promoted pointer. Mọi chi tiết authority phải đọc từ baseline file nêu trên.