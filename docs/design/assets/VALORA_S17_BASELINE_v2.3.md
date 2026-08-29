# VALORA — Hoàn tất một báo giá nhà cung cấp — Baseline Authority v2.3

**Nguồn duyệt:** `S17 — Iteration 3`  
**Trạng thái:** `BASELINE ĐÃ DUYỆT / DESIGN AUTHORITY`  
**Phạm vi nghiệp vụ:** **01 báo giá cụ thể của 01 nhà cung cấp (NCC)** trong checkpoint `Tạo & quản lý báo giá nhà cung cấp`.

> Quyết định authority quan trọng: Iteration 3 được duyệt về visual + interaction, nhưng scope nghiệp vụ được khóa là **hoàn tất một báo giá của một NCC**, không phải readiness/hoàn tất toàn bộ hồ sơ thẩm định. Badge `S17` xuất hiện trên mockup được giữ như nhãn iteration lịch sử; khi triển khai/chuẩn hóa screen ID, màn hình này phải được phân loại là child screen của NCCQ. `S17 — Hoàn tất hồ sơ` ở cấp hồ sơ là một scope riêng và không được suy diễn từ baseline này.

## 1. Mục tiêu

Cho phép người dùng rà soát trạng thái của **một báo giá hiện tại**, xem phản hồi NCC, giá NCC đã xác nhận, file ký/đóng dấu, chênh lệch so với giá đã gửi và lineage/evidence trước khi explicit bấm `Hoàn tất báo giá`.

Màn hình không tổng hợp coverage 3 NCC và không đánh giá readiness toàn bộ hồ sơ.

## 2. Visual baseline — Iteration 3

- Valora shell + Fluent 2, desktop-first.
- Breadcrumb theo context hồ sơ và báo giá, ví dụ: `Hồ sơ thẩm định → [Hồ sơ] → Báo giá nhà cung cấp → [NCC / Mã báo giá]`.
- Header `Hoàn tất báo giá nhà cung cấp`.
- Primary CTA: `Hoàn tất báo giá`.
- Secondary action: `Lưu nháp`.
- Left rail thể hiện lifecycle của **báo giá hiện tại**, không phải lifecycle template:
  1. `Tạo báo giá nháp`;
  2. `Tạo file theo mẫu NCC`;
  3. `Gửi NCC xác nhận`;
  4. `Nhận phản hồi / file ký`;
  5. `Hoàn tất báo giá`.
- Vùng giữa là readiness/status của báo giá hiện tại + danh sách warning/blocking còn lại.
- Vùng phải gồm `Thông tin báo giá hiện tại`, preview nhanh file báo giá đã xác nhận và `Checklist hoàn tất báo giá`.

![Baseline — Hoàn tất một báo giá NCC — Iteration 3](./VALORA_S17_ITERATION_3_BASELINE_v2.3.jpg)

## 3. Readiness của một báo giá

Các hạng mục baseline:

1. `Nhà cung cấp` — đúng NCC gắn với báo giá hiện tại.
2. `Danh mục trong báo giá` — số dòng thiết bị thuộc **báo giá này**; không dùng tổng danh mục hồ sơ nếu báo giá chỉ chứa subset.
3. `Đơn giá gửi NCC` — coverage các dòng đã có giá đề nghị/giá gửi đi.
4. `File báo giá` — file Word đã tạo theo template Word của NCC.
5. `Phản hồi NCC` — trạng thái gửi/nhận phản hồi và ngày nhận nếu có.
6. `Giá NCC đã xác nhận` — coverage các dòng đã có giá thực tế NCC xác nhận.
7. `File ký & đóng dấu` — file phản hồi/ký/đóng dấu tương ứng khi lifecycle yêu cầu.
8. `Chênh lệch so với giá gửi đi` — số dòng NCC đã sửa giá, có CTA xem chi tiết.
9. `Lineage & chứng cứ` — truy vết nguồn lịch sử/Internet → báo giá hiện tại → file gửi → giá xác nhận → file phản hồi.

**Không có** readiness `Đã chọn 3/3 NCC`, `12/12 dòng có nguồn giá`, `mapping 100%` hoặc các KPI template trong màn hình này.

## 4. Warning / Blocking theo lifecycle

- `Blocking`: ngăn `Hoàn tất báo giá` khi dependency bắt buộc của báo giá hiện tại chưa đạt.
- `Warning`: cho phép hoàn tất nếu rule nghiệp vụ cho phép, nhưng phải nêu rõ rủi ro và có CTA xử lý/xem chi tiết.
- `Info`: trạng thái tham khảo.

`File ký & đóng dấu` **không tự động là Warning từ đầu lifecycle**. Chỉ cảnh báo/Blocking khi báo giá đã tới giai đoạn cần phản hồi/xác nhận mà file/evidence tương ứng còn thiếu theo rule nghiệp vụ.

Ví dụ warning baseline trong Iteration 3:

- NCC điều chỉnh một số dòng so với giá đề nghị đã gửi;
- file scan ký/đóng dấu đã nhận nhưng chất lượng cần rà soát/thay bản rõ hơn.

## 5. Thông tin báo giá hiện tại

Panel phải hiển thị tối thiểu:

- Nhà cung cấp;
- Mã báo giá;
- Trạng thái lifecycle;
- Số dòng thiết bị;
- Tổng giá trị xác nhận;
- Ngày gửi NCC;
- Ngày nhận phản hồi;
- file gửi NCC;
- file phản hồi/ký/đóng dấu.

Tên NCC, mã báo giá, giá trị và ngày trong mockup là dữ liệu giả lập, không phải dữ liệu hồ sơ/NCC thật.

## 6. Preview file đã xác nhận

- Preview Word/PDF-render của file báo giá đã nhận/xác nhận để người dùng rà nhanh chứng từ.
- Bảng preview giữ `STT` gốc của tài sản trong danh mục ban đầu; báo giá subset không được renumber STT.
- Preview không thay thế file evidence gốc; file gốc/version/lineage vẫn phải truy vết được.

## 7. CTA `Hoàn tất báo giá`

CTA chỉ active khi không còn Blocking của báo giá hiện tại.

Khi người dùng hoàn tất:

- trạng thái báo giá được chuyển sang semantic `Đã hoàn tất` / trạng thái tương đương được implementation khóa sau;
- lưu snapshot giá NCC đã xác nhận và evidence liên quan;
- giữ toàn bộ lịch sử giá gửi đi, thay đổi của NCC và lineage;
- ghi audit actor/time.

CTA **không được**:

- tự thay `Đơn giá hiện hành`;
- tự chọn NCC thay người dùng;
- tự hoàn tất toàn bộ hồ sơ thẩm định;
- tự coi báo giá này là một trong 3 NCC được chọn dùng trong hồ sơ nếu người dùng chưa thực hiện CTA `Chọn nhà cung cấp đã xác nhận giá` ở NCCQ.

## 8. Quan hệ với NCCQ

Luồng authority:

```text
NCCQ — Tạo & quản lý báo giá NCC
→ mở một báo giá/NCC cụ thể
→ Tạo báo giá nháp
→ Tạo file Word theo mẫu NCC
→ Gửi NCC
→ Nhận phản hồi / file ký
→ Hoàn tất báo giá hiện tại
→ quay về NCCQ tổng hợp
→ Chọn nhà cung cấp đã xác nhận giá
```

Coverage `1/2/3 NCC`, `3/3 NCC` và lựa chọn các NCC dùng trong hồ sơ thuộc **NCCQ tổng hợp**, không thuộc màn hình baseline này.

## 9. Superseded iterations

- `S17 Iteration 1`: superseded vì còn template-centric và giả định readiness toàn hồ sơ.
- `S17 Iteration 2`: superseded vì trộn readiness toàn hồ sơ/coverage nhiều NCC vào flow của một báo giá.
- **Iteration 3** là authority trực quan và nghiệp vụ cho scope **một báo giá / một NCC**.

Khi có mâu thuẫn giữa hình mockup và rule trong tài liệu này, **scope/rule ở companion baseline này + business rule NCCQ trong Handoff v2.3 là nguồn quyết định**.