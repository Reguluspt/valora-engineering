# VALORA S17 — Hoàn tất hồ sơ — Iteration 1

**Trạng thái:** `ITERATION — CHƯA CHỐT BASELINE / KHÔNG PHẢI DESIGN AUTHORITY`

Mockup này là working visual ban đầu của S17, dùng cùng Valora shell + Fluent 2 với các baseline trước đó.

> Lưu ý: iteration hiện tại còn một số nội dung/nhãn mang ngữ cảnh `template` từ bước TM04. Các phần đó chỉ là placeholder visual và **không phải business authority của S17**. Khi tinh chỉnh S17 phải chuyển toàn bộ nội dung sang readiness của **hồ sơ thẩm định chính thức**.

## 1. Mục tiêu S17

S17 là readiness summary cuối trước khi người dùng quyết định `Hoàn tất hồ sơ`.

S17 không phải màn hình `Kiểm tra hồ sơ` riêng và không thay thế validation phân tán ở các bước trước.

Primary CTA dự kiến: `Hoàn tất hồ sơ` và chỉ active khi không còn lỗi `Blocking`.

## 2. Working visual — Iteration 1

Các pattern visual được giữ lại từ mockup:

- Valora shell + Fluent 2, desktop-first;
- breadcrumb + header gọn;
- vùng tổng hợp tiến độ/readiness ở phần trên;
- khu vực trung tâm dùng bảng/tóm tắt trạng thái thay vì card-heavy dashboard;
- vùng phải dành cho preview/tóm tắt chứng từ và checklist readiness;
- footer hiển thị tiến độ hoàn tất và CTA chính;
- `Blocking`, `Warning`, `Info` dùng semantic status rõ ràng.

## 3. Nội dung nghiệp vụ cần thay thế trong iteration tiếp theo

Các phần đang ghi `Upload file`, `Mapping`, `Preview / Test fill`, `Lưu template` không phải nội dung cuối của S17.

Iteration tiếp theo phải chuyển chúng thành readiness hồ sơ, tối thiểu gồm:

- `Thông tin hồ sơ`;
- `Danh mục triển khai`;
- `Hoàn thiện tài sản / Đơn giá hiện hành`;
- `Nguồn giá & Chứng cứ`;
- `Báo giá nhà cung cấp`;
- coverage NCC đã xác nhận giá;
- file báo giá ký/đóng dấu;
- NCC/báo giá đã được chọn dùng trong hồ sơ;
- trạng thái template Word/output nếu là dependency của việc tạo file báo giá;
- thay đổi chưa lưu/commit;
- các blocking/warning còn lại từ các checkpoint trước.

## 4. Hành vi readiness

S17 chỉ tổng hợp trạng thái đã phát sinh ở các context trước:

- `Blocking`: ngăn `Hoàn tất hồ sơ`;
- `Warning`: cho phép tiếp tục nếu rule nghiệp vụ cho phép nhưng phải nêu rõ rủi ro;
- `Info`: trạng thái tham khảo.

Mỗi issue nên có CTA `Đi tới` để quay đúng context phát sinh và giữ lineage.

S17 không tự sửa dữ liệu, không tự chọn NCC, không tự thay `Đơn giá hiện hành`, không tự resolve warning/blocking.

## 5. Guardrail

- Không tạo checkpoint `Kiểm tra hồ sơ` riêng từ S17.
- Không tạo KSCL riêng trong workflow single-user hiện tại.
- Không coi preview/template readiness là readiness duy nhất của hồ sơ.
- Không cho hoàn tất khi còn lỗi Blocking.
- `Hoàn tất hồ sơ` là thao tác explicit của người dùng và phải có audit/lineage.
- Mockup Iteration 1 chưa phải authority; chỉ khi người dùng nói `chốt baseline` hoặc `nâng S17 thành authority` mới được nâng thành baseline.

## 6. Trạng thái thiết kế

`S17 — Iteration 1` là working visual ban đầu để tiếp tục tinh chỉnh.

Ưu tiên iteration tiếp theo: thay toàn bộ nội dung template-centric bằng readiness hồ sơ chính thức, giữ layout Fluent 2 và cấu trúc summary + issues + CTA của mockup này.
