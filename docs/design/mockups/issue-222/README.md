# VALORA — Phân tích danh mục: mockup UI/UX đã chốt

**Product Owner chốt thiết kế:** 26/10/2026 (Asia/Ho_Chi_Minh)  
**Trạng thái:** `PO_DESIGN_APPROVED / POST_UAT_IMPLEMENTATION_HOLD`  
**Backlog:** [Issue #222](https://github.com/Reguluspt/valora-engineering/issues/222), liên kết [UAT #203](https://github.com/Reguluspt/valora-engineering/issues/203).

## Tệp mở độc lập

[`VALORA_Preliminary_Analysis_Mockup_Approved_2026-10-26.html`](VALORA_Preliminary_Analysis_Mockup_Approved_2026-10-26.html)

- Một tệp HTML duy nhất, đã nhúng CSS/JavaScript, mở offline bằng trình duyệt để kiểm tra thiết kế.
- Dữ liệu bên trong **đã được thay bằng 9 tài sản giả lập, tên dự án ẩn danh và giá minh họa** vì repository là public. Không lưu file Excel khách hàng, tên công trình hoặc giá thật trong repository.
- Giữ nguyên cấu trúc, luồng thao tác và cách tính của mockup được PO duyệt; thay đổi dữ liệu chỉ phục vụ an toàn khi lưu trữ công khai.
- Mockup không kết nối VALORA, không lưu server/database, không có đăng nhập, không tải lên tài liệu, không tự ghi sang staging/danh mục chính thức. Dữ liệu nhập thử mất khi tải lại trang.

## Quyết định UI/UX đã chốt

1. **Đầu vào Excel khách hàng:** có STT, tên tài sản/đặc điểm, ĐVT, số lượng, đơn giá KH và thành tiền KH. **Không có sẵn** đơn giá thẩm định/đơn giá đề xuất và nguồn thông tin tham khảo; các cột làm việc trên giao diện khởi tạo rỗng.
2. **Bảng nhập liệu dày:** cố định STT và tên tài sản; text chuyên môn có xuống dòng; hai thanh cuộn ngang phía trên và phía dưới bảng đồng bộ; hỗ trợ tra cứu, lọc và nhập nhanh.
3. **Số lượng:** chỉ còn một cột `SL nguồn` có thể sửa trực tiếp, đặt cạnh ĐVT. Bản gốc từ Excel được giữ riêng để đối chiếu; khi thay đổi số lượng, yêu cầu giải trình trước khi xác nhận.
4. **Giá:** dùng thuật ngữ `Đơn giá đề xuất` và `Thành tiền đề xuất`; chỉ tính thành tiền và tổng tạm tính của các dòng đã có giá. Không coi ô trống là 0 đồng.
5. **Chứng cứ:** một tab `Chứng cứ` cạnh `Lịch sử` trong chi tiết tài sản; không có tab `Phân tích giá`. Ô `Diễn giải cơ sở đề xuất` nhận văn bản, URL và hình ảnh clipboard qua Ctrl+V, tự nhận diện link/ảnh, không dùng nút `Thêm liên kết` hoặc `Thêm ảnh chụp`.
6. **Cột Chứng cứ:** tự phản ánh ngay số liên kết/ảnh mới dán cho từng tài sản; mở panel bên phải để xem và sửa.
7. **Khảo sát và vận chuyển:** thẩm định viên nhập đơn giá khảo sát, tỷ lệ vận chuyển (% trên giá khảo sát); giá tính = giá khảo sát + chi phí vận chuyển. Có quyền sửa giá đề xuất thủ công, không bắt buộc liên kết công thức.
8. **Điều kiện nguồn:** VAT và điều kiện vận chuyển có thể sửa bằng ô nhập.
9. **Kiểm soát:** mỗi dòng cần có giá đề xuất, diễn giải cơ sở và chứng cứ trước khi xác nhận; mockup không tạo quyền nghiệp vụ hay hiệu lực thẩm định chính thức.

## Ranh giới chưa triển khai

- Đây là **baseline thiết kế**, không phải phê duyệt sửa frontend/backend/domain/API hiện tại.
- Không mở PR triển khai, merge, deploy, migration, AI provider, hoặc thao tác vào môi trường UAT #203 từ bản lưu này.
- Điều hướng trực tiếp từ Upload & Mapping Excel, hợp đồng lưu chứng cứ giàu nội dung, lịch sử/audit/lineage, xử lý hình/PDF và nghiệp vụ xác nhận thực tế vẫn cần task/authority và kiểm thử riêng sau UAT theo Issue #222.
- Khi tiếp tục phiên làm việc sau, đọc Issue #222, #203, CODEX.md và ranh giới hiện hành; kiểm tra live main/CI trước khi mở task triển khai. Không suy diễn mockup thành sản phẩm đã được chứng nhận.
