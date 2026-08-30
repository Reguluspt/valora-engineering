# VALORA v2.3 — User Flow Mindmap

**Trạng thái:** `DESIGN SUPPORT / FLOW MAP`  
**Authority:** Bám theo handoff v2.3 + các addendum mới nhất. Nếu mâu thuẫn, business/design authority mới nhất thắng.

```mermaid
mindmap
  root((VALORA\nSingle-user Workflow))
    Pre-case
      Trang chủ
      Quản lý yêu cầu sơ bộ
      Tạo yêu cầu sơ bộ
      Upload & Mapping Excel
      Phân tích danh mục
        Kho tri thức
          Gợi ý candidate
          Không phải nguồn giá ưu tiên độc lập
        Nguồn giá/chứng cứ ưu tiên
          1. Giá khảo sát Internet
          2. Thuyết minh đơn giá
          3. Giá Kết quả hồ sơ cũ
        Người dùng ấn định / điều chỉnh giá
      Rà soát tích hợp
      Tạo file kết quả sơ bộ
      Chuyển sang thẩm định chính thức
    Hồ sơ chính thức
      Tổng quan hồ sơ
      Xác nhận & điều chỉnh danh mục triển khai
      Workbench tài sản
        Asset Context Drawer
          Raw vs Normalized
          Thông số kỹ thuật
          Nguồn giá & Chứng cứ
          Lịch sử
      Nguồn giá & Chứng cứ
        1. Giá khảo sát Internet
        2. Thuyết minh đơn giá
        3. Giá trong Kết quả hồ sơ cũ
        Tổng hợp căn cứ
        Người dùng chỉnh Đơn giá hiện hành
    NCCQ
      Hệ thống sinh báo giá nháp
      Dedupe theo NCC
      Gộp / Tách / Chuyển thiết bị
      STT bất biến
      Giá NCC lịch sử
        Chỉ phục vụ tái tạo báo giá
      Internet-only
        1 báo giá dùng Đơn giá hiện hành làm giá đề nghị
        2 báo giá còn lại 100%-115%
      Hoàn tất từng báo giá NCC
        Tạo báo giá nháp
        Tạo file theo mẫu NCC
        Gửi NCC xác nhận
        Nhận phản hồi / file ký
        Hoàn tất báo giá
      Chọn nhà cung cấp đã xác nhận giá
        Không tự biến giá NCC thành giá thẩm định
        Lưu NCC → Báo giá → Dòng → Giá xác nhận → File evidence
    Kết quả thẩm định giá
      Rule đối chiếu
        Đơn giá Kết quả <= Đơn giá báo giá NCC
        Không đạt thì validation
        Không auto sửa giá
      Bảng 1
        Đặc điểm kinh tế - kỹ thuật
        Immutable layout
      Bảng 2
        Tổng hợp 03 giá NCC
        Không có Thành tiền NCC
      Bảng 3
        Kết quả thẩm định giá
        Đơn giá do người dùng quyết định
        Tổng cộng / Làm tròn / Bằng chữ
    Bộ tài liệu phát hành
      Microsoft 365 Document Workspace
      Tạo / quản lý Word
      Mở trong Word
      Đồng bộ dữ liệu
      Tạo phiên bản mới
      So sánh
      Khóa phiên bản
      Phát hành bộ tài liệu
      Không có Xuất PDF trong baseline
      Cấu trúc thư mục
        01_Hồ sơ gốc
        02_Tài liệu thẩm định
        03_Hợp đồng
        04_Báo giá nhà cung cấp
        05_Pháp lý
```

## Semantic giá

```text
Nguồn ưu tiên xác định giá:
Giá khảo sát Internet
→ Thuyết minh đơn giá
→ Giá trong phần Kết quả của hồ sơ cũ
→ Người dùng quyết định Đơn giá hiện hành / Đơn giá Kết quả

Luồng báo giá NCC:
Đơn giá hiện hành
→ Giá đề nghị
→ NCC xác nhận
→ Đơn giá NCC đã xác nhận
→ Dùng làm báo giá/evidence đối chiếu

Rule kết quả:
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
```

## Guardrail

- `Kho tri thức` chỉ gợi ý; không tự ra quyết định giá.
- Giá NCC không phải nguồn chính để xác định Đơn giá thẩm định cuối cùng.
- Giá NCC lịch sử phục vụ tái tạo báo giá và lineage.
- Người dùng kiểm soát `Đơn giá hiện hành`; mọi thay đổi có history/lineage/audit.
- Không có S14 xác nhận lại giá, màn Kiểm tra hồ sơ riêng hoặc workflow KSCL riêng.
- Không có NCCQ aggregate trung gian sau khi chọn NCC đã xác nhận giá.
- Ba bảng Kết quả thẩm định giá là immutable layout.
- Microsoft 365 quản lý file/version/Word; VALORA quản lý structured business data, snapshot, lineage và audit.