# VALORA TM04 — Preview / Test fill dữ liệu Word — Iteration 1

**Trạng thái:** `ITERATION — CHƯA CHỐT BASELINE / KHÔNG PHẢI DESIGN AUTHORITY`

Mockup working visual hiện tại của TM04 dùng cùng Valora shell + Fluent 2 với TM01/TM03 và tuân thủ rule template báo giá NCC chỉ dùng Word `.docx`.

## Cấu trúc iteration

- Header: `Preview / Test fill dữ liệu Word`.
- Step rail trái thể hiện 4 bước đã đi qua: `Upload file → Mapping bảng danh mục → Mapping thông tin chung → Preview / Test fill`.
- Khu vực trái cho chọn bộ dữ liệu test, số dòng danh mục và tùy chọn hiển thị/highlight mapping.
- Khu vực giữa hiển thị dữ liệu test sẽ được fill, có tab `Thông tin chung` và `Bảng danh mục`.
- Khu vực phải preview trực tiếp tài liệu Word đã fill, có zoom/page navigation/full-screen.
- Footer hiển thị tiến độ setup, trạng thái preview và các CTA.

## Hành vi test fill

TM04 phải hỗ trợ:

- dữ liệu test mặc định hoặc bộ dữ liệu kiểm thử phù hợp;
- điền thử placeholder/text field;
- điền thử bảng danh mục lặp theo row template Word;
- kiểm tra text dài/tràn ô;
- kiểm tra format tiền/ngày;
- kiểm tra bảng lặp, footer và ngắt trang;
- highlight vùng dữ liệu vừa được fill khi người dùng bật tùy chọn;
- chạy lại test fill sau khi dữ liệu test hoặc mapping thay đổi.

## CTA iteration

- `Quay lại chỉnh mapping`;
- `Lưu template` / `Lưu bản nháp` theo trạng thái;
- `Lưu và đặt sẵn sàng sử dụng` chỉ khi không còn lỗi blocking.

## Guardrail

- Dữ liệu test chỉ dùng để kiểm tra template, không trở thành dữ liệu hồ sơ chính thức.
- Preview hợp lệ không tự động đổi template sang trạng thái sẵn sàng nếu chưa có thao tác người dùng.
- Lỗi blocking phải ngăn `Sẵn sàng sử dụng`; warning/info không tự thay mapping.
- Không dùng semantics Excel như sheet/cell/range trong TM04.

Mockup này chỉ là working iteration. Chỉ khi người dùng nói `chốt baseline` hoặc `nâng TM04 thành authority` thì mới được nâng thành design authority và cập nhật vào danh sách baseline v2.3.
