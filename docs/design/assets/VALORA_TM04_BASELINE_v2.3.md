# VALORA TM04 — Preview / Test fill dữ liệu Word — Baseline Authority v2.3

**Trạng thái:** `BASELINE ĐÃ DUYỆT / DESIGN AUTHORITY`

**Nguồn visual:** TM04 — Iteration 1 đã được người dùng duyệt và chốt baseline.

TM04 là màn hình kiểm thử cuối của luồng cấu hình template báo giá NCC Word `.docx`, dùng cùng Valora shell + Fluent 2 với TM01/TM03.

> Authority rule: tài liệu này nâng TM04 Iteration 1 thành design authority. Mọi mô tả cũ ghi TM04 là `mockup chưa duyệt baseline` hoặc `working iteration` bị superseded kể từ baseline này.

## 1. Mục tiêu

Cho phép người dùng điền thử dữ liệu vào template Word trước khi cho phép template trở thành `Sẵn sàng sử dụng`, nhằm kiểm tra mapping, bố cục và hành vi bảng danh mục lặp trong điều kiện gần với output thực tế.

Dữ liệu test chỉ phục vụ kiểm thử template; không trở thành dữ liệu hồ sơ chính thức.

## 2. Visual baseline — Iteration 1

- Valora shell + Fluent 2, desktop-first.
- Breadcrumb: `Cấu hình → Mẫu báo giá nhà cung cấp → Preview / Test fill`.
- Header: `Preview / Test fill dữ liệu Word`.
- Step rail bên trái thể hiện 4 bước: `Upload file → Mapping bảng danh mục → Mapping thông tin chung → Preview / Test fill`.
- Khu vực trái cho chọn bộ dữ liệu test, số dòng danh mục và các tùy chọn highlight/hướng dẫn mapping.
- Khu vực giữa hiển thị dữ liệu test sẽ được fill, có ít nhất hai ngữ cảnh `Thông tin chung` và `Bảng danh mục`.
- Khu vực phải là preview trực tiếp tài liệu Word đã fill, có điều khiển zoom, chuyển trang và toàn màn hình.
- Footer hiển thị tiến độ setup template, trạng thái preview và CTA hoàn tất.

## 3. Nguồn dữ liệu test

TM04 hỗ trợ:

- `Dữ liệu mẫu mặc định` do hệ thống cung cấp để test nhanh;
- hoặc một bộ dữ liệu/hồ sơ phù hợp do người dùng chọn để kiểm thử khi capability này được triển khai.

UI phải nêu rõ đây là dữ liệu minh họa/test, không phải dữ liệu sẽ ghi vào hồ sơ hoặc trở thành báo giá chính thức.

## 4. Preview Word đã fill

Preview phải phản ánh file Word thực tế sau khi điền dữ liệu:

- placeholder/text field đã được thay giá trị;
- bảng danh mục được nhân dòng từ row template;
- STT, tên thiết bị, ĐVT, số lượng, đơn giá, thành tiền và các field được mapping hiển thị theo template;
- header/footer, phần ký tên, ghi chú và các vùng tĩnh của Word được giữ đúng bố cục;
- có page navigation khi tài liệu dài hơn một trang;
- có zoom/full-screen để kiểm tra bố cục.

TM04 không dùng semantics Excel như `sheet`, `cell`, `range`, `A8:J100`.

## 5. Validation / Test fill

Kết quả kiểm tra phải phát hiện và trình bày rõ tối thiểu:

- field bắt buộc chưa mapping;
- placeholder không được fill;
- format tiền/ngày không đúng;
- text quá dài hoặc tràn vùng;
- bảng lặp bị vỡ layout;
- dòng lặp/row template không nhân đúng;
- bảng lặp có nguy cơ đè footer hoặc vùng ký;
- ngắt trang không phù hợp;
- vùng tổng cộng/footer chưa được map khi template yêu cầu;
- dữ liệu tổng hợp/công thức không hợp lệ nếu hệ thống có thể kiểm tra.

Semantic validation:

- `Blocking`: phải xử lý trước khi template được đặt `Sẵn sàng sử dụng`;
- `Warning`: cho phép lưu/tiếp tục nhưng phải hiển thị rủi ro;
- `Info`: thông tin trạng thái.

## 6. Highlight / kiểm tra trực quan

Người dùng có thể bật/tắt hỗ trợ kiểm tra trực quan như:

- highlight vùng dữ liệu vừa được fill;
- hiển thị chú thích mapping;
- chỉ dẫn vùng lặp/bảng danh mục.

Các affordance kiểm tra không được trở thành nội dung của file output cuối.

## 7. CTA baseline

Các action chính:

- `Quay lại chỉnh mapping` — quay về TM03 và giữ context template/version;
- `Lưu template` / `Lưu bản nháp` — lưu trạng thái hiện tại;
- `Lưu và đặt sẵn sàng sử dụng` — primary CTA khi không còn lỗi blocking.

Preview hợp lệ **không tự động** chuyển trạng thái template. Việc đặt `Sẵn sàng sử dụng` luôn là thao tác explicit của người dùng.

## 8. Readiness

Template chỉ được đặt `Sẵn sàng sử dụng` khi tối thiểu:

- metadata bắt buộc đã có;
- file Word `.docx` hợp lệ;
- các field bắt buộc đã mapping;
- row template/vùng danh mục lặp đã cấu hình nếu template có danh mục;
- Test fill không còn lỗi blocking.

## 9. Guardrail

TM04 không được:

- tự sửa mapping để làm test pass;
- tự đổi template sang `Sẵn sàng sử dụng`;
- ghi dữ liệu test vào hồ sơ chính thức;
- silent overwrite template/version đã dùng;
- dùng XLSX/PDF làm template báo giá NCC;
- hiển thị mapping Word bằng semantics spreadsheet.

## 10. Quan hệ authority

Chuỗi baseline module template tại thời điểm này:

`TM01 Danh sách mẫu — baseline` → `TM03 Upload & Mapping Word — baseline` → `TM04 Preview / Test fill Word — baseline`.

TM02 và TM05 hiện giữ IA/capability đã mô tả trong Handoff v2.3; không tự suy diễn visual baseline chi tiết nếu chưa có mockup được duyệt.

Sau khi TM04 được chốt, nhiệm vụ UI/UX tiếp theo là `S17 — Hoàn tất hồ sơ`, dùng readiness từ checkpoint báo giá NCC + template/output để tổng hợp blocking/warning trước khi hoàn tất hồ sơ.
