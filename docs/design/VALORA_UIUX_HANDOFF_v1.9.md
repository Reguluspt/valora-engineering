# VALORA — UI/UX Handoff v1.9

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh

> Phiên bản v1.9 kế thừa toàn bộ baseline v1.8 và bổ sung/chốt chi tiết S08 — **Rà soát giá đề xuất**. Các màn hình S02–S07 đã duyệt không bị thiết kế lại.

## 0. Cập nhật v1.9

Các quyết định mới đã được người dùng duyệt:

- Chốt S08 — `Rà soát giá đề xuất` là checkpoint toàn danh mục sau S05–S07.
- **Không cho phép hoàn tất toàn danh mục nếu còn bất kỳ dòng nào chưa xác định được giá.**
- `Thuyết minh đơn giá` (`USER_PRICE_JUSTIFICATION`) **có thể là căn cứ duy nhất** để một dòng hoàn tất, miễn đáp ứng đầy đủ các điều kiện xác định giá và được người dùng xác nhận.
- S08 hiển thị `Thành tiền đề xuất = SL × Đơn giá đề xuất` theo từng dòng.
- S08 dùng **một trang danh mục có thanh cuộn dọc**, không phân trang theo kiểu chia page trong vùng dữ liệu chính.
- Khu vực KPI/header/ghi chú phải tiết kiệm chiều cao để ưu tiên không gian hiển thị bảng.
- Menu S08 nằm trong cùng cụm điều hướng nghiệp vụ của **Yêu cầu sơ bộ / Phân tích yêu cầu sơ bộ**, không tách thành một module độc lập.
- Mockup S08 đã được duyệt sau vòng chỉnh sửa về menu, mật độ KPI, scrolling và footer/ghi chú.

## 1. Product baseline đã chốt

Valora ở giai đoạn hiện tại được thiết kế cho **01 người dùng nghiệp vụ xử lý toàn bộ vòng đời công việc**. Không xây workflow chuyển việc giữa nhiều tài khoản, không có inbox chờ người khác duyệt và không có SLA theo role ở phiên bản hiện tại.

Phần mềm **chỉ phục vụ thẩm định giá máy móc thiết bị bằng phương pháp so sánh**. Nguồn chứng cứ chủ yếu là thông tin giá bán trên Internet. **Không thiết kế quy trình khảo sát hiện trạng**. Nếu cần tình trạng/đặc điểm tài sản thì sử dụng thông tin khách hàng cung cấp và dữ liệu thu thập từ nguồn Internet.

AI/Kho tri thức chỉ đóng vai trò **gợi ý**. Người dùng luôn là người xác nhận thiết bị, nguồn giá và đơn giá cuối cùng.

## 2. North-star user flow

```text
Trang chủ
  → Quản lý yêu cầu sơ bộ
  → Tạo yêu cầu sơ bộ
  → Upload & Mapping Excel
  → Phân tích danh mục
      → Đối chiếu Kho tri thức
      → Thiết bị chưa có dữ liệu phù hợp: tìm nguồn giá Internet
      → Xác định giá thị trường tham khảo
      → Cộng tỷ lệ vận chuyển (%)
      → Xác nhận đơn giá đề xuất
  → Rà soát giá đề xuất
  → Hoàn tất phân tích danh mục
  → Gửi/ghi nhận mức giá đề xuất với khách hàng
  → Chờ khách hàng phản hồi
  → Khách hàng chấp thuận
  → Chuyển thành hồ sơ chính thức
  → Hoàn thiện thông tin/chứng cứ
  → Xác nhận giá thẩm định chính thức
  → Kiểm tra nội bộ
  → KSCL self-check
  → Hoàn tất
  → Báo cáo / Chứng thư
  → Phát hành
  → Lưu trữ và hình thành tri thức
```

## 3. Khái niệm Yêu cầu sơ bộ / Pre-case

Yêu cầu sơ bộ tồn tại **trước hồ sơ thẩm định giá chính thức**.

Trong thực tế, khách hàng thường chỉ gửi một file Excel danh mục thiết bị. Ở thời điểm này chưa nhất thiết có tên pháp nhân, MST, địa chỉ, người đại diện, hợp đồng hoặc các thông tin khách hàng khác.

Người dùng cần xem danh mục, kiểm tra thiết bị, đối chiếu Kho tri thức và tìm giá cho các thiết bị mới để đưa ra **đơn giá thẩm định sơ bộ**. Chỉ khi khách hàng chấp thuận mức giá đề xuất mới yêu cầu thông tin khách hàng và chuyển Pre-case thành hồ sơ chính thức.

### Trạng thái Pre-case đề xuất

- `Mới tạo`
- `Mới nhận danh mục`
- `Đang đối chiếu tri thức`
- `Cần tìm giá`
- `Đang phân tích giá`
- `Sẵn sàng gửi giá đề xuất`
- `Chờ khách hàng phản hồi`
- `Đã chấp thuận giá đề xuất`
- `Không tiếp tục`
- `Đã chuyển thành hồ sơ`

## 4. S02 — Quản lý yêu cầu sơ bộ

### Mục tiêu

Cho người dùng nhìn thấy và tiếp tục toàn bộ Pre-case trước khi hình thành hồ sơ chính thức.

### Thành phần chính

- KPI/card: Tổng yêu cầu, Mới tạo, Đang phân tích, Chờ phản hồi, Đã chuyển thành hồ sơ.
- Search theo mã yêu cầu, tên yêu cầu, tên file.
- Filter theo trạng thái/ngày.
- CTA chính: **`+ Tạo yêu cầu sơ bộ`**.
- Bảng danh sách gồm tối thiểu:
  - Mã yêu cầu.
  - Tên yêu cầu sơ bộ.
  - Tệp nguồn.
  - Ngày nhận.
  - Số thiết bị.
  - Tiến độ phân tích.
  - Tổng giá trị đề xuất.
  - Trạng thái.
  - Cập nhật cuối.
  - Thao tác `Tiếp tục` / `Xem`.

### Quy tắc UX

- Không hiển thị Customer/MST/Hợp đồng như trường bắt buộc.
- Row action ưu tiên `Tiếp tục` để mở đúng bước người dùng đang làm dở.
- Không dùng nhãn kỹ thuật như Project/Job/Created/Pending trên UI.

## 5. S03 — Tạo yêu cầu sơ bộ

### Mục tiêu

Tạo Pre-case tối giản khi chưa biết đầy đủ thông tin khách hàng.

### Dữ liệu đầu vào

- Mã yêu cầu: hệ thống tự sinh.
- Tên yêu cầu sơ bộ: bắt buộc; có thể tự gợi ý từ tên file và cho phép sửa.
- Ngày nhận: mặc định ngày hiện tại, cho phép sửa.
- Ghi chú: không bắt buộc.
- File danh mục: `.xls` / `.xlsx`.

### Hành vi

- Có vùng drag & drop file Excel.
- Sau upload có thể hiển thị nhanh: số sheet, số dòng ước tính, phát hiện có cột Đơn giá hay không.
- Có tùy chọn `Tự gợi ý tên yêu cầu từ tên file`.
- Có tùy chọn kiểm tra Pre-case tương tự/trùng gần đây.
- Nếu phát hiện khả năng trùng, chỉ cảnh báo và cho người dùng quyết định.
- Cho phép `Lưu yêu cầu` ngay cả khi chưa upload file.
- CTA chính khi có file hợp lệ: **`Tạo & tiếp tục Mapping`**.

### Không yêu cầu ở bước này

- Tên khách hàng.
- MST.
- Địa chỉ.
- Người đại diện.
- Hợp đồng.
- Phương pháp thẩm định.
- Thông tin khảo sát hiện trạng.

## 6. S04 — Upload & Mapping Excel

Luồng chuẩn gồm 3 bước:

1. **Tải tệp Excel**.
2. **Chọn sheet & vùng dữ liệu**.
3. **Mapping cột**.

Màn hình phải dùng đúng shell Valora đã chốt, có preview dữ liệu và panel `Thiết lập nhập liệu / Kiểm tra mapping` bên phải.

### Các field quan trọng khi mapping

- Tên thiết bị.
- Thông số / đặc điểm.
- Đơn vị tính (ĐVT).
- Số lượng (SL).
- **Đơn giá KH dự kiến**.
- Ghi chú.
- Cột không cần dùng → `Bỏ qua`.

### Quy tắc đặc biệt với cột `Đơn giá`

Cột `Đơn giá` trong file khách hàng được map thành **`Đơn giá KH dự kiến`**.

Đây là dữ liệu tham khảo do khách hàng cung cấp, **không phải Giá thị trường**, không phải chứng cứ giá và không phải Đơn giá đề xuất của thẩm định viên.

Phải giữ lineage về file/sheet/dòng/cột gốc và không tự ghi đè dữ liệu này.

## 7. S05 — Phân tích danh mục: workspace trung tâm

Đây là màn hình làm việc quan trọng nhất của Valora.

### Layout baseline

- Sidebar Valora bên trái.
- Header/breadcrumb phía trên.
- Các KPI/card tiến độ.
- Toolbar search/filter/trạng thái.
- **Bảng danh mục thiết bị chiếm vùng chính bên trái/trung tâm**.
- **Panel chi tiết bên phải** với 4 tab cố định:
  1. `Tổng quan`
  2. `Kho tri thức`
  3. `Nguồn giá`
  4. `Kết luận giá`

Không điều hướng sang một trang khác mỗi khi xử lý một thiết bị. Khi click dòng mới, panel phải cập nhật trong cùng workspace.

### Cụm cột giá đã chốt

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

**Không có cột Chênh lệch so với khách hàng.**

### Trạng thái dòng đề xuất

- Chưa phân tích.
- Có gợi ý.
- Cần tìm giá.
- Đang xử lý.
- Hoàn tất.

### Spreadsheet efficiency

Workbench cần ưu tiên trải nghiệm giống bảng tính:

- scroll nhanh;
- sticky header/cột thiết yếu;
- resize cột;
- copy/paste phù hợp;
- edit inline cho field được phép;
- phím Enter/↑/↓ hỗ trợ chuyển dòng;
- không reload toàn màn hình sau mỗi save;
- sau khi xác nhận xong một dòng có thể tự chọn dòng chưa hoàn tất tiếp theo.

## 8. Panel Kho tri thức

Kho tri thức là nơi tra cứu **trước khi tìm mới trên Internet**.

### Candidate phải hiển thị

- Tên chuẩn tài sản.
- Thương hiệu.
- Model.
- Thông số quan trọng.
- Mức độ tương đồng.
- Giải thích lý do khớp.
- Giá tham chiếu/lịch sử.
- Ngày cập nhật/lần dùng gần nhất.
- Số nguồn giá liên quan.

### Hành động

- `Sử dụng dữ liệu này`.
- `Không phù hợp`.
- `Xem tất cả trong Kho tri thức`.

### Nguyên tắc

- Không auto-accept candidate.
- Không tự ghi đè tên gốc của khách hàng.
- Giá lịch sử chỉ là tham khảo; không tự trở thành giá hiện tại.
- Dữ liệu cũ cần hiển thị thời điểm để người dùng cân nhắc có phải kiểm tra lại Internet hay không.
- Nếu chưa có dữ liệu đủ phù hợp, khuyến nghị chuyển sang tab `Nguồn giá`.

## 9. Panel Nguồn giá Internet

Mục tiêu là quản lý các nguồn giá bán Internet cho thiết bị đang chọn.

### Danh sách nguồn

Mỗi nguồn nên lưu tối thiểu:

- URL.
- Website/nhà cung cấp.
- Tên sản phẩm.
- Giá quan sát.
- Ngày thu thập.
- Tình trạng/model/thông số đối chiếu khi có.
- Ghi chú.
- Trạng thái xác nhận/cần xem lại.

Không cố định `Nguồn 1 / Nguồn 2 / Nguồn 3`; một thiết bị có thể có N nguồn.

### Không chỉ lưu URL

Website có thể thay đổi hoặc mất. Dữ liệu cần lưu snapshot nghiệp vụ tối thiểu gồm URL, tên website, tên sản phẩm, giá quan sát, thời điểm thu thập và ghi chú đối chiếu. Có thể mở rộng screenshot/HTML snapshot ở giai đoạn sau.

## 10. Thêm nguồn giá — 2 cách nhập

Khi bấm **`+ Thêm nguồn giá`**, UI hỗ trợ **một hoặc cả hai** cách trong cùng design system, không mở một sản phẩm/shell khác.

### Cách 1 — Thuyết minh đơn giá

Mở khung soạn thảo rich text để người dùng ghi:

- căn cứ;
- nguồn thông tin;
- điều kiện;
- nhận xét;
- cách xác định mức giá;
- ghi chú chuyên môn.

Có thể đính kèm file hỗ trợ.

### Cách 2 — Dán link trang web

Người dùng paste URL; hệ thống có thể hỗ trợ đọc/gợi ý:

- tên website;
- tên sản phẩm;
- giá;
- tình trạng;
- ngày cập nhật/thu thập.

Người dùng phải kiểm tra lại trước khi lưu.

### Phân biệt loại nguồn

Backend/domain cần phân biệt tối thiểu:

- `USER_PRICE_JUSTIFICATION`
- `INTERNET_MARKET_SOURCE`

Không đồng nhất thuyết minh của người dùng với chứng cứ website.

## 11. Logic giá thị trường → vận chuyển → đơn giá đề xuất

```text
Giá thị trường → Vận chuyển (%) → Đơn giá đề xuất
```

Công thức nghiệp vụ:

```text
Đơn giá đề xuất = Giá thị trường cơ sở × (1 + Tỷ lệ vận chuyển / 100)
```

### Không hiển thị trên UI

- Không tạo field `Chi phí vận chuyển`.
- Không tạo field `Giá sau vận chuyển`.

Giá thị trường gốc vẫn phải được giữ để truy vết.

### Tùy chỉnh tỷ lệ vận chuyển

- Có thể có tỷ lệ mặc định cho cả danh mục.
- Có thể áp dụng cho nhóm nhiều dòng.
- Có thể override từng thiết bị.
- Khi đổi %, hệ thống tính lại Đơn giá đề xuất ngay.
- Người dùng vẫn có thể chỉnh Đơn giá đề xuất thủ công nếu nghiệp vụ yêu cầu; nếu chỉnh tay phải giữ audit/nguồn gốc giá.

## 12. Điều kiện hoàn tất một thiết bị — v1.9

Một dòng chỉ được xem là `Hoàn tất` khi đồng thời:

1. Thiết bị được nhận diện đủ để so sánh.
2. Có **ít nhất một căn cứ giá được người dùng chấp nhận**.
3. Có Giá thị trường tham khảo / giá cơ sở được người dùng xác nhận.
4. Có Vận chuyển (%) hợp lệ; `0%` là hợp lệ.
5. Có Đơn giá đề xuất.
6. Người dùng đã xác nhận dòng.

### Căn cứ giá hợp lệ

Một dòng có thể hoàn tất với một hoặc nhiều loại căn cứ sau:

- Kho tri thức đã được người dùng chọn/xác nhận.
- Nguồn Internet đã được người dùng chấp nhận.
- **Thuyết minh đơn giá** đã được người dùng lưu và xác nhận; thuyết minh được phép là **căn cứ duy nhất** của dòng.

Không yêu cầu cứng số lượng nguồn Internet tối thiểu.

Nếu dùng Kho tri thức cần lưu version/candidate đã dùng. Nếu dùng nguồn Internet cần lưu evidence/URL và giá quan sát. Nếu dùng Thuyết minh đơn giá cần lưu nội dung, file đính kèm nếu có, người xác nhận và thời điểm xác nhận.

**Không còn ngoại lệ “có lý do chưa xác định giá nhưng vẫn xem là hoàn tất”.** Dòng chưa xác định được giá luôn là dòng `Cần xử lý`.

## 13. S08 — Rà soát giá đề xuất

### 13.1 Mục tiêu người dùng

S08 là checkpoint toàn danh mục, không phải màn hình phân tích lại từng thiết bị. Người dùng cần trả lời nhanh:

- Đã xử lý hết danh mục chưa?
- Mỗi đơn giá đề xuất dựa trên căn cứ nào?
- Còn dòng nào chưa đủ điều kiện/chưa xác nhận?
- Tổng giá trị đề xuất của toàn danh mục là bao nhiêu?
- Có thể quay lại đúng dòng cần sửa mà không mất context hay không?

### 13.2 Điều kiện vào

Pre-case đã có danh mục từ S04 và đã thực hiện phân tích ở S05–S07. S08 có thể mở ngay cả khi còn dòng chưa hoàn tất để người dùng rà soát lỗi/chỗ thiếu; tuy nhiên CTA hoàn tất sẽ bị khóa.

### 13.3 Dữ liệu đầu vào

Mỗi dòng lấy từ kết quả phân tích hiện tại và lineage tương ứng:

- STT/dòng nguồn.
- Tên thiết bị và mô tả/thông số ngắn.
- SL, ĐVT.
- Đơn giá KH dự kiến.
- Giá tham chiếu Kho tri thức.
- Giá thị trường tham khảo.
- Vận chuyển (%).
- Đơn giá đề xuất.
- Căn cứ đã dùng: Kho tri thức / Internet / Thuyết minh.
- Trạng thái xác nhận.
- Nguồn/file/sheet/dòng/cột/candidate/version liên quan.

### 13.4 Bố cục màn hình

S08 dùng đúng Valora shell/component language đã chốt.

**Sidebar:** S08 nằm trong cùng cụm điều hướng `Yêu cầu sơ bộ / Phân tích yêu cầu sơ bộ`, cùng Upload & Mapping, Phân tích danh mục, Kho tri thức và Nguồn giá; không tách thành menu/module độc lập.

**Header:**

- Breadcrumb: `Yêu cầu sơ bộ / {mã YC} / Rà soát giá đề xuất`.
- Tên Pre-case + file nguồn/version ngắn gọn.
- CTA phụ: `Quay lại Phân tích danh mục`.
- CTA chính: `Hoàn tất phân tích danh mục`.

Header và metadata phải **compact**, không chiếm chiều cao không cần thiết.

### 13.5 KPI toàn danh mục

Hiển thị dạng compact card:

- `Tổng thiết bị`.
- `Đã xác nhận`.
- `Có dùng Kho tri thức`.
- `Có nguồn Internet mới`.
- `Cần xử lý`.
- `Tổng giá trị đề xuất`.

`Có dùng Kho tri thức` và `Có nguồn Internet mới` là hai tập có thể giao nhau; không được thiết kế như hai nhóm loại trừ nhau.

Người dùng có thể click KPI/filter tương ứng để lọc nhanh bảng.

### 13.6 Banner readiness

Nếu toàn bộ danh mục đạt điều kiện:

> `Tất cả {N} thiết bị đã đủ điều kiện và được xác nhận.`

Nếu còn blocking rows:

> `Còn {N} thiết bị cần xử lý trước khi có thể hoàn tất phân tích danh mục.`

Banner phải chỉ rõ nhóm nguyên nhân và có CTA `Đi tới dòng đầu tiên cần xử lý`.

### 13.7 Bộ lọc

Các filter nhanh:

- `Tất cả`.
- `Cần xử lý`.
- `Kho tri thức`.
- `Internet mới`.
- `Thuyết minh`.
- `Đã xác nhận`.

Có search thiết bị và bộ lọc mở rộng khi cần.

### 13.8 Bảng rà soát

Thứ tự cột ưu tiên:

1. STT.
2. Thiết bị.
3. SL / ĐVT.
4. Đơn giá KH dự kiến.
5. Giá tham chiếu Kho tri thức.
6. Giá thị trường tham khảo.
7. Vận chuyển (%).
8. Đơn giá đề xuất.
9. **Thành tiền đề xuất.**
10. Căn cứ.
11. Trạng thái.
12. Thao tác.

Công thức:

```text
Thành tiền đề xuất = SL × Đơn giá đề xuất
```

`Thành tiền đề xuất` chỉ là giá trị dẫn xuất phục vụ rà soát/tổng hợp, không thay đổi cụm giá nghiệp vụ đã chốt trong S05.

### 13.9 Scrolling và mật độ bảng

- S08 dùng **một trang danh mục có thanh cuộn dọc**.
- Không chia bảng thành nhiều page khiến người dùng phải chuyển trang để rà soát toàn danh mục.
- Header bảng có thể sticky.
- Có thể virtualize danh sách dài để đảm bảo hiệu năng nhưng UX vẫn là một danh sách cuộn liên tục.
- Khu vực KPI, banner và ghi chú phải tiết kiệm chiều cao để ưu tiên viewport cho bảng.
- Không tạo footer lớn; ghi chú/tổng hợp cuối màn hình ở dạng compact.

### 13.10 Trạng thái dòng

S08 dùng hai trạng thái cấp cao:

- `Đã xác nhận`.
- `Cần xử lý`.

`Cần xử lý` phải chỉ rõ reason như:

- Thiếu căn cứ giá.
- Chưa có Giá thị trường tham khảo.
- Chưa có Đơn giá đề xuất.
- Chưa xác nhận.
- Căn cứ cần kiểm tra lại.

### 13.11 Quay lại đúng dòng cần sửa

Bấm `Sửa` / `Đi tới` phải mở S05 đúng thiết bị và đúng tab phù hợp:

| Vấn đề | Context mở |
|---|---|
| Thiếu/thay nguồn | `Nguồn giá` |
| Kho tri thức chưa xử lý | `Kho tri thức` |
| Chưa xác nhận giá | `Kết luận giá` |
| Vấn đề chung | `Tổng quan` |

Khi quay lại S08, hệ thống khôi phục search/filter/vị trí cuộn trước đó.

### 13.12 Điều kiện bật CTA `Hoàn tất phân tích danh mục`

CTA chỉ enabled khi **mọi dòng trong phạm vi danh mục** đều đáp ứng điều kiện hoàn tất dòng ở §12.

Các trường hợp sau luôn chặn hoàn tất:

- Còn dòng chưa xác định được giá.
- Thiếu căn cứ giá hợp lệ.
- Thiếu Giá thị trường tham khảo / giá cơ sở cần thiết cho quyết định.
- Thiếu Đơn giá đề xuất.
- Chưa xác nhận dòng.
- Có blocking validation/error state.

Không dùng quy tắc “có lý do chưa xác định” để vượt qua gate.

### 13.13 Confirm dialog

Khi bấm `Hoàn tất phân tích danh mục`, hiển thị confirm dialog tóm tắt:

- Tổng thiết bị.
- Số đã xác nhận.
- Số có dùng Kho tri thức.
- Số có nguồn Internet mới.
- Tổng giá trị đề xuất.

Thông điệp cần nêu rõ hệ thống sẽ lưu snapshot kết quả hiện tại và chuyển Pre-case sang `Sẵn sàng gửi giá đề xuất`.

CTA:

- `Hủy`.
- `Xác nhận hoàn tất`.

Không tự chuyển sang `Chờ khách hàng phản hồi` và không tự tạo hồ sơ chính thức.

### 13.14 Snapshot khi hoàn tất

Snapshot `Đã phân tích` tối thiểu lưu:

- Mã/tên Pre-case.
- Version file danh mục và mapping/source lineage.
- Thứ tự danh mục và raw device data cần truy vết.
- Đơn giá KH dự kiến nguyên gốc.
- Candidate/version Kho tri thức đã dùng.
- Nguồn Internet đã chấp nhận + metadata snapshot.
- Thuyết minh đơn giá đã dùng.
- Giá thị trường tham khảo.
- Vận chuyển (%).
- Đơn giá đề xuất.
- Thành tiền đề xuất.
- Trạng thái xác nhận từng dòng.
- KPI aggregate và Tổng giá trị đề xuất.
- Người hoàn tất, thời điểm, snapshot version.

Snapshot cũ không bị sửa. Nếu dữ liệu phân tích thay đổi sau khi đã hoàn tất, UI đánh dấu `Dữ liệu đã thay đổi — cần rà soát lại`; lần hoàn tất tiếp theo tạo snapshot version mới.

### 13.15 Loading / empty / error / warning / success

- **Loading:** skeleton KPI + skeleton table; không làm mất shell.
- **Empty:** `Chưa có danh mục để rà soát.` + CTA quay về bước phù hợp.
- **Error:** thông báo tiếng Việt + `Thử lại`; không lộ HTTP/SQL/stack trace.
- **Warning:** banner số dòng cần xử lý + `Đi tới dòng cần xử lý`.
- **Nguồn Internet không còn truy cập:** giữ lịch sử URL, đánh dấu `Cần kiểm tra`, không tự xóa chứng cứ cũ.
- **Success:** banner `Đã hoàn tất phân tích danh mục` + snapshot/version + trạng thái mới.

## 14. Khách hàng phản hồi và chuyển thành hồ sơ chính thức

Khi S08 hoàn tất, Pre-case chuyển sang `Sẵn sàng gửi giá đề xuất`.

Sau khi người dùng ghi nhận đã gửi/trao đổi giá với khách hàng, Pre-case mới chuyển sang `Chờ khách hàng phản hồi`.

Nếu khách hàng không tiếp tục: đóng Pre-case nhưng giữ file nguồn, kết quả phân tích và lịch sử quyết định để tham chiếu.

Nếu khách hàng chấp thuận: lúc này mới yêu cầu/nhập thông tin khách hàng cần thiết và `Chuyển thành hồ sơ`.

Danh mục đã phân tích, kết quả match Kho tri thức, nguồn Internet, Thuyết minh đơn giá và giá sơ bộ phải được tái sử dụng; không bắt người dùng upload và làm lại từ đầu.

Nếu khách hàng gửi file danh mục cập nhật, hệ thống giữ version cũ và cho người dùng xem diff thêm/bớt/thay đổi. Dòng mới/thay đổi quan trọng trở lại trạng thái `Cần phân tích giá`.

## 15. Single-user checkpoint sau khi thành hồ sơ

Các bước sau vẫn do cùng một người dùng thực hiện:

- Khai báo thông tin thực hiện/tổ thẩm định để phục vụ biểu mẫu.
- Hoàn thiện danh mục tài sản.
- Chuẩn hóa tài sản.
- Hoàn thiện chứng cứ/nguồn giá Internet.
- Xác nhận giá thẩm định chính thức bằng phương pháp so sánh.
- Kiểm tra nội bộ.
- KSCL theo hình thức self-check checklist.
- Hoàn tất/phê duyệt nội bộ như một checkpoint, không phải chuyển task.
- Sinh Báo cáo/Chứng thư.
- Phát hành và khóa phiên bản.
- Lưu hồ sơ và hình thành dữ liệu tri thức.

## 16. Quy tắc thiết kế chung

### Vietnamese-first

- UI dùng ngôn ngữ nghiệp vụ tiếng Việt.
- Không hiển thị HTTP status, stack trace, ORM, SQL, session, row_version hay thuật ngữ kỹ thuật cho người dùng cuối.
- CTA dùng động từ rõ.

### Human in the loop

- AI/Kho tri thức chỉ gợi ý.
- Không tự xác nhận mapping.
- Không tự xác nhận identity.
- Không tự Apply dữ liệu chính thức.
- Không tự chốt giá.
- Không tự hoàn tất S08.
- Không tự phát hành.

### Dữ liệu nguồn bất biến

- File Excel khách hàng và raw observation phải truy lại được.
- Không ghi đè tên/đơn giá gốc của khách hàng bằng dữ liệu chuẩn hóa.
- Staging và dữ liệu chính thức phải được phân biệt.
- Snapshot S08 là versioned review snapshot, không được dùng để sửa ngược raw evidence.

### Design system

Các màn hình S02–S08 phải dùng cùng Valora shell/component language:

- sidebar;
- header/breadcrumb;
- card KPI;
- table/grid;
- tabs;
- badge trạng thái;
- button hierarchy;
- form field;
- drawer/panel/overlay;
- confirm dialog.

Không tạo modal/shell khác phong cách cho một thao tác con.

## 17. Screen inventory baseline

| ID | Màn hình | Ưu tiên |
|---|---|---|
| S01 | Trang chủ | P0 |
| S02 | Quản lý yêu cầu sơ bộ | P0 |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Nhận danh mục từ Excel / Mapping | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát giá đề xuất | P0 |
| S09 | Chuyển thành hồ sơ | P0 |
| S10 | Tổng quan hồ sơ | P0 |
| S11 | Xác nhận danh mục triển khai | P0 |
| S12 | Workbench tài sản | P0 |
| S13 | Asset Context Drawer | P0 |
| S14 | So sánh & Xác nhận giá | P0 |
| S15 | Kiểm tra hồ sơ | P0 |
| S16 | KSCL Checklist | P0 |
| S17 | Hoàn tất hồ sơ | P0 |
| S18 | Báo cáo & Chứng thư | P1 |
| S19 | Phát hành | P1 |
| S20 | Lịch sử & Lưu trữ | P1 |

## 18. Baseline mockup đã chốt trong v1.9

Baseline chức năng hiện có **08 mockup đã được người dùng duyệt**:

1. **Quản lý yêu cầu sơ bộ**.
2. **Tạo yêu cầu sơ bộ**.
3. **Upload & Mapping Excel**.
4. **Phân tích danh mục**.
5. **Panel Kho tri thức**.
6. **Panel Nguồn giá Internet**.
7. **Thêm nguồn giá**.
8. **Rà soát giá đề xuất (S08)** — full-page review, menu cùng cụm Yêu cầu sơ bộ, KPI/header compact, bảng cuộn dọc liên tục, cột Thành tiền đề xuất, CTA quay lại phân tích và Hoàn tất phân tích danh mục.

Mockup là baseline thị giác. Nếu chi tiết pixel xung đột với nguyên tắc nghiệp vụ/dữ liệu thì **nguyên tắc nghiệp vụ và dữ liệu có ưu tiên cao hơn**.

## 19. Definition of Done cho bộ UI/UX

Bộ thiết kế được xem là đủ để bàn giao Engineering khi:

- Có sitemap và user flow từ Trang chủ đến Phát hành/Lưu trữ.
- Mỗi màn hình P0 có wireframe/hi-fi tương ứng.
- Có loading/empty/error/warning/success/read-only state phù hợp.
- Có confirm dialog cho các hành động rủi ro cao.
- Nhãn tiếng Việt nhất quán.
- Không có workflow đa người dùng ẩn trong UI hiện tại.
- Handoff component/state/token bám design system Astryx/Valora của dự án.
- Truy vết được dữ liệu Excel, candidate Kho tri thức, nguồn Internet, Thuyết minh đơn giá, tỷ lệ vận chuyển và quyết định giá của người dùng.

## 20. Quan hệ với tài liệu kỹ thuật hiện có

Khi hiện thực hóa UI/UX, đọc theo thứ tự authority của repo và đối chiếu tối thiểu:

- `CODEX.md`
- `ENGINEERING_GUARDRAILS.md`
- `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
- `docs/VALORA_PROJECT_HANDOFF.md`
- `docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md`
- `docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md`
- `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
- `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`

Các guardrail kỹ thuật đã tồn tại vẫn có hiệu lực: tenant isolation fail-closed; staging không phải dữ liệu chính thức; Apply là human-confirmed; restricted Workbench fields đi qua draft/commit; AI advisory-only; historical/source evidence phải có provenance.

## 21. Phân biệt trạng thái thiết kế và trạng thái implement

Tài liệu này mô tả **thiết kế mục tiêu UI/UX**. Việc một màn hình được mô tả hoặc mockup được duyệt **không đồng nghĩa màn hình đó đã được implement trong code sản phẩm**.

Tại thời điểm cập nhật v1.9:

- S08 đã được **chốt thiết kế và mockup**.
- Không có thay đổi runtime/code sản phẩm nào được thực hiện từ tài liệu này.
- Engineering chỉ được triển khai khi có task/assignment riêng tuân thủ `CODEX.md`, `ENGINEERING_GUARDRAILS.md` và authority hiện hành.
