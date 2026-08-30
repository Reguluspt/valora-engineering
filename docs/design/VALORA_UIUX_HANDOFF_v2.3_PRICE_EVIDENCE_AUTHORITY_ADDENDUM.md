# VALORA UI/UX Handoff v2.3 — Price & Evidence Authority Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Phạm vi:** Nguồn giá & Chứng cứ → NCCQ → Kết quả thẩm định giá  
**Nguyên tắc supersession:** Addendum này ưu tiên áp dụng nếu mâu thuẫn với mô tả cũ trong master handoff hoặc iteration trước.

## A. Thứ tự ưu tiên nguồn giá & chứng cứ

Thứ tự nghiệp vụ được khóa:

1. **Giá khảo sát từ Internet**.
2. **Thuyết minh đơn giá**.
3. **Giá trong phần Kết quả thẩm định giá của hồ sơ cũ**.

`Tổng hợp căn cứ` chỉ là bề mặt tổng hợp, không phải loại căn cứ thứ tư.

`Kho tri thức` là cơ chế hỗ trợ tìm/gợi ý candidate và thông tin tham chiếu; không phải một nguồn giá ưu tiên độc lập ngang hàng với ba nguồn trên.

Người dùng là người quyết định `Đơn giá hiện hành` và `Đơn giá` trong Kết quả thẩm định giá. AI/Kho tri thức/rule engine/nguồn ngoài không tự ghi đè quyết định giá.

## B. Hồ sơ cũ / Giá lịch sử

Trong phạm vi xác định giá thẩm định, giá hồ sơ cũ được hiểu là **giá trong phần Kết quả thẩm định giá của hồ sơ cũ**, không phải mặc định là giá của các nhà cung cấp trong báo giá cũ.

Hồ sơ cũ vẫn là first-class evidence và phải giữ lineage tối thiểu tới:

```text
Tài sản hiện tại
→ Hồ sơ cũ
→ Tài sản cũ
→ Thời điểm thẩm định
→ Giá trong phần Kết quả
→ Tài liệu nguồn
```

Việc dùng hồ sơ cũ làm căn cứ không tự copy giá cũ thành `Đơn giá hiện hành`.

## C. Vai trò của giá nhà cung cấp

Giá của các nhà cung cấp, bao gồm giá NCC lịch sử và giá NCC đã xác nhận trong báo giá hiện tại, **không phải nguồn chính để xác định Đơn giá thẩm định cuối cùng**.

Giá NCC phục vụ hai mục đích chính:

1. **Tạo/tái tạo báo giá NCC** trong NCCQ.
2. **Đối chiếu tính phù hợp của Đơn giá Kết quả định giá**.

NCCQ tiếp tục giữ semantic riêng:

- `Giá lịch sử`;
- `Giá đề nghị — chờ NCC xác nhận`;
- `Đơn giá NCC đã xác nhận`.

Các mức giá NCC không tự thay `Đơn giá hiện hành`.

## D. Rule kiểm tra Kết quả thẩm định giá

Rule nghiệp vụ được khóa:

```text
Đơn giá Kết quả định giá <= Đơn giá trong báo giá NCC dùng để đối chiếu
→ Phù hợp
```

Nếu Đơn giá Kết quả định giá **không cao hơn** đơn giá trong các báo giá NCC thuộc tập đối chiếu áp dụng cho dòng tài sản đó thì được coi là phù hợp theo rule/tiêu chuẩn thẩm định giá đang áp dụng trong VALORA.

Nếu:

```text
Đơn giá Kết quả định giá > Đơn giá báo giá NCC thuộc tập đối chiếu bắt buộc
```

UI phải hiển thị validation phù hợp tại nơi phát sinh. Hệ thống **không tự sửa giá**.

Mức severity cụ thể (`Blocking` hay `Warning`) và cách xác định chính xác tập báo giá bắt buộc dùng để đối chiếu cần được đặc tả tại dependency triển khai; không tự suy diễn ngoài authority đã khóa.

## E. Semantic của CTA Chọn nhà cung cấp đã xác nhận giá

`Chọn nhà cung cấp đã xác nhận giá` **không có nghĩa** là lấy giá NCC làm Đơn giá thẩm định cuối cùng.

Selection giữ lineage:

```text
NCC
→ Báo giá
→ Dòng thiết bị
→ Đơn giá NCC đã xác nhận
→ File ký/đóng dấu
```

Selection này cung cấp lớp báo giá/evidence NCC cho bước Kết quả thẩm định giá và rule đối chiếu giá.

## F. Routing giữ nguyên

```text
Nguồn giá & Chứng cứ
→ Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC
→ Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace / Bộ tài liệu phát hành
```

Không có màn NCCQ aggregate trung gian.

## G. Quan hệ với 03 bảng Kết quả thẩm định giá

### Bảng 1 — Đặc điểm kinh tế - kỹ thuật

Không thay đổi authority immutable layout.

### Bảng 2 — Tổng hợp giá nhà cung cấp

03 cột NCC là dữ liệu báo giá phục vụ đối chiếu/evidence. Không có cột Thành tiền NCC.

### Bảng 3 — Kết quả thẩm định giá

`Đơn giá` là quyết định nghiệp vụ cuối của người dùng dựa trên nguồn giá/chứng cứ ưu tiên và phải thỏa rule đối chiếu NCC nêu tại §D.

Ba bảng vẫn là biểu mẫu công ty có layout bất biến.

## H. Superseded semantics

Các mô tả cũ bị supersede nếu hiểu rằng:

- ba nhóm `Nguồn Internet / Hồ sơ cũ / Thuyết minh` là ngang hàng không có thứ tự ưu tiên;
- giá NCC lịch sử là nguồn chính để xác định đơn giá thẩm định;
- chọn NCC đã xác nhận giá đồng nghĩa lấy giá NCC làm giá thẩm định;
- giá NCC có thể tự ghi đè `Đơn giá hiện hành`;
- giá trong hồ sơ cũ dùng làm căn cứ mặc định là giá NCC thay vì giá ở phần Kết quả thẩm định giá của hồ sơ cũ.

## I. Guardrail

- Human decision remains authoritative.
- Mọi thay đổi `Đơn giá hiện hành` có history/lineage/audit.
- Giá NCC và giá thẩm định là hai semantic khác nhau.
- Không đưa dữ liệu khách hàng/NCC/hồ sơ thật vào public repository.
- Addendum này là authority nghiệp vụ; không suy diễn rằng product code đã implement.