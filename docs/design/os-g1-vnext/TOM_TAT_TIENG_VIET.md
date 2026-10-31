# VALORA — Tóm tắt quyết định OS-G1 vNext và ranh giới triển khai

**Ngày:** 31/10/2026  
**Trạng thái:** Ghi nhận quyết định UX của Product Owner; **chưa phê duyệt triển khai**.  
**Phạm vi:** Chỉ thay đổi định hướng UX yêu cầu sơ bộ OS-G1, thiết kế đối chiếu Kho tri thức và chuẩn Fluent 2. Không thay đổi runtime, API, schema, CI hoặc UAT #203.

## 1. Hành trình chính đã thống nhất

**Khởi tạo yêu cầu sơ bộ → Upload/Mapping Excel → VALORA tự tìm nguồn giá/chứng cứ đủ tin cậy → Nhân viên rà soát từng dòng theo thứ tự gốc → Xử lý tài sản thiếu nguồn hoặc thông số sai → Tổng kết cảnh báo → Xác nhận một lần và xuất Excel → Tiếp tục chỉnh sửa để xuất phiên bản mới hoặc chuyển OS-G2.**

- Không bắt buộc thông tin khách hàng khi tạo yêu cầu sơ bộ. Khi chuyển hồ sơ chính thức phải có khách hàng hợp lệ.
- Kho tri thức tự điền dữ liệu khi **nhận dạng tài sản** và **nguồn giá/chứng cứ** cùng đạt điều kiện tin cậy. Tài sản tương tự nhưng chưa đủ tin cậy chỉ được gợi ý.
- Nhân viên là người quyết định **Đơn giá đề xuất**; công thức từ giá khảo sát + vận chuyển là gợi ý, không ràng buộc. Hệ thống không tự ghi đè giá nhân viên đã sửa.
- Rà soát tuần tự không cần bấm xác nhận từng tài sản. Chuyển sang dòng khác ghi nhận “đã xem”; màn tổng kết cảnh báo những dòng chưa xem, không ngầm coi chúng đã rà soát.
- Nguồn giá và chứng cứ được quản lý cùng thẻ. Dán văn bản, URL và ảnh trực tiếp; sau khi lưu thành công bảng phải cập nhật nguồn/chứng cứ.
- Sửa hãng/model/công suất/thông số trọng yếu: hỏi ngay trong panel **cập nhật tri thức hiện có / tạo tài sản hoặc biến thể mới / chỉ sửa hồ sơ này**. Sửa giá đơn thuần không kích hoạt câu hỏi.
- Nhân viên đề xuất thay đổi Kho tri thức từ dữ liệu đã nhập một lần; người có quyền phê duyệt mới được công bố tri thức dùng chung. Việc chờ duyệt không cản việc xử lý yêu cầu sơ bộ.
- Chênh lệch giá bất thường chỉ cảnh báo trong lúc rà soát; không phát sinh thêm bước phê duyệt giá riêng.
- Tổng kết/xuất Excel một bảng, có giá/nguồn/link/ảnh, bảo toàn dòng chưa có giá mà không cộng phần chưa xác định; mỗi lần xuất tạo phiên bản không đổi.
- Chuyển OS-G2 kế thừa dữ liệu như bản đang làm việc và chuyển OS-G1 sang chỉ đọc; quyết định **“Chấp nhận làm cơ sở thẩm định”** chỉ thuộc khâu hoàn thành hồ sơ chính thức theo phân quyền.

## 2. Giao diện hướng tới

- Microsoft Fluent 2 Light **thực chất**, ưu tiên dùng \`@fluentui/react-components\` v9.
- Workbench bảng dày với cột STT/tên tài sản cố định, thanh cuộn ngang trên/dưới đồng bộ, chuột cuộn tự nhiên, nội dung dài xuống dòng.
- Cột **ĐVT → SL nguồn** được sửa trực tiếp; giữ số lượng Excel gốc và giải trình khi đổi.
- Có Đơn giá/Thành tiền khách hàng khi có đầu vào; Đơn giá/Thành tiền đề xuất; cảnh báo trường còn trống.
- Panel bên phải mở/đóng linh hoạt, có nguồn + chứng cứ, tài sản tương tự, lịch sử/nguồn gốc; sidebar thu gọn vẫn hiển thị icon và tooltip.
- Màn hình tìm nguồn hàng loạt là tính năng hỗ trợ khi cần, không phải một bước bắt buộc.
- Mockup UX-G1.15 v01 chỉ là HTML minh họa, **không phải** React Fluent 2 thật và chưa được duyệt làm baseline. v02 cần kiểm tra thành phần Microsoft, trạng thái tương tác, keyboard/focus/accessibility.

## 3. Những điểm phải hòa giải trước khi giao Codex

| Mục | Vướng mắc | Hướng xử lý |
|---|---|---|
| Xác nhận từng dòng | Mockup 26/10 và hợp đồng Preliminary Analysis hiện tại có xác nhận từng dòng, manifest nghiêm ngặt | Quyết định UX mới là xác nhận tổng thể; **phải sửa hợp đồng domain/API và test bằng task độc lập**, không sửa ngầm |
| Thiếu giá/chứng cứ | Hợp đồng hiện hành có những điều kiện dữ liệu chặt hơn phương án xuất sơ bộ chưa hoàn chỉnh | Thẩm định lại snapshot, generator Excel, lineage và thống kê tổng |
| Người duyệt tri thức | Baseline v2.3 Knowledge Review là single-user và “Cần rà soát” nội bộ | Phê duyệt UX-G1.14 B phải có phân quyền được xác lập; không tự dựng workflow đa người |
| Loại nguồn giá | Kho tri thức chỉ là nơi truy xuất/gợi ý, không phải căn cứ giá thứ tư | Giữ thứ tự Internet → Thuyết minh đơn giá → Giá kết quả thẩm định hồ sơ cũ |
| Mockup đã duyệt | Issue #222 đã lưu mockup 26/10 và còn HOLD sau UAT | Bảo toàn nguyên bản như lịch sử; v02 là ứng viên mới, cần PO duyệt |
| Fluent 2 | Có sử dụng Fluent UI thật nhưng không đồng nhất; còn nhiều component thủ công | Lập mapping component/thiết kế và audit tương tác trước khi triển khai |

## 4. Cổng phê duyệt

**Tài liệu trên nhánh/Draft PR là để review, không phải product design approved hay runtime approved.**

Trước khi sửa code cần: (1) PO chốt bản thiết kế tổng hợp, (2) rà soát authority/domain/ADR/RBAC/ảnh/chứng cứ, (3) duyệt mockup Fluent UI React v02, (4) chia micro-task Codex nhỏ có test và review riêng, (5) kiểm tra môi trường phù hợp và gate triển khai độc lập.

**Không merge PR tài liệu nếu chưa có quyết định review; không chạy lại UAT #203 và không ghi/chỉnh sửa Kho tri thức thật từ phạm vi này.**

## 5. Tài liệu chi tiết

- [Nhật ký quyết định](DECISION_REGISTER.md).
- [Đặc tả Workflow và Workbench](WORKFLOW_AND_WORKBENCH.md).
- [Đối chiếu tài sản và quản trị tri thức](KNOWLEDGE_MATCHING_AND_GOVERNANCE.md).
- [Hòa giải authority và yêu cầu gate](AUTHORITY_RECONCILIATION.md).
- [Mapping Fluent 2 và chuẩn mockup v02](FLUENT2_COMPONENT_MAPPING.md).
- [Báo cáo kiểm kê Fluent 2](../../audits/VALORA_FLUENT2_UIUX_STATIC_AUDIT_2026-10-31.md).
