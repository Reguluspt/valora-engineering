# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX đã duyệt + các business rule mới đã khóa  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Valora shell bám sát Fluent 2, desktop-first

> v2.3 kế thừa baseline v2.2, chốt S13 — `Asset Context Drawer / Ngữ cảnh tài sản`, loại S14 khỏi workflow hiện tại, khóa cơ chế `Đơn giá hiện hành` có thể được người dùng sửa trong quá trình xử lý hồ sơ, chốt baseline `Nguồn giá & Chứng cứ`, **chốt baseline authority cho checkpoint `Tạo & quản lý báo giá nhà cung cấp` (NCCQ) theo Iteration 6, cho `TM01 — Danh sách mẫu báo giá NCC` theo Iteration 1 và cho `TM03 — Upload & Mapping template` theo Iteration 1 Word-only**. IA/flow TM01–TM05 tiếp tục giữ nguyên; TM04 chưa được coi là baseline cuối cho tới khi người dùng duyệt.

## 0. Quyết định v2.3 đã duyệt / đã khóa

### 0.1 S09–S13 và giá hiện hành

- Toàn bộ quyết định S09–S12 của v2.2 tiếp tục giữ nguyên, ngoại trừ nội dung yêu cầu phải có một màn hình riêng để xác nhận lại `Giá thẩm định chính thức`.
- S13 — `Asset Context Drawer / Ngữ cảnh tài sản` đã được duyệt baseline; đây là drawer trong S12, không phải route/menu độc lập.
- Khi mở S13, S12 giữ nguyên filter, sort, search, pagination, selection và vị trí scroll.
- `Dữ liệu gốc (Excel)` luôn truy vết được và không bị ghi đè bởi dữ liệu chuẩn hóa.
- Kho tri thức/AI chỉ gợi ý; không auto-accept candidate, không tự xác nhận identity, không tự ấn định hoặc tự sửa giá.
- **Không dùng S14 — So sánh & Xác nhận giá thẩm định chính thức trong workflow hiện tại.**
- Đơn giá người dùng ấn định ở Pre-case là giá khởi tạo/kế thừa khi chuyển sang hồ sơ chính thức, nhưng không bị khóa cứng.
- Người dùng có thể sửa đơn giá trong quá trình xử lý hồ sơ tại các context được phép. Mỗi lần sửa trở thành `Đơn giá hiện hành` mới và phải giữ lịch sử/lineage/audit.
- Không yêu cầu người dùng xác nhận lại cùng một mức giá tại một checkpoint riêng chỉ vì chuyển từ Pre-case sang hồ sơ chính thức.
- Nếu tài sản mới được bổ sung hoặc identity/thông số quan trọng thay đổi, hệ thống cảnh báo về độ phù hợp của giá/căn cứ hiện hành; người dùng quyết định giữ, sửa hoặc phân tích lại.
- Validation chạy tại field/dòng/context phát sinh theo `Blocking`, `Warning`, `Info`; không có màn hình Kiểm tra riêng.

### 0.2 Nguồn giá & Chứng cứ

- Checkpoint `Nguồn giá & Chứng cứ` đã được duyệt baseline trong v2.3.
- Ba nhóm căn cứ ngang hàng:
  1. `Nguồn Internet`;
  2. `Hồ sơ cũ / Giá lịch sử`;
  3. `Thuyết minh đơn giá`.
- `Tổng hợp căn cứ` là bề mặt tổng hợp, không phải loại căn cứ thứ tư.
- `Hồ sơ cũ / Giá lịch sử` không bị ẩn trong Kho tri thức; người dùng phải biết hồ sơ cũ cụ thể nào đang được tham khảo.
- Giá từ mọi nguồn chỉ là căn cứ tham khảo/giải trình; `Đơn giá hiện hành` vẫn do người dùng quyết định và có thể sửa.

### 0.3 Tạo & quản lý báo giá nhà cung cấp — business rule + visual baseline đã khóa

- Sau `Nguồn giá & Chứng cứ`, workflow có checkpoint **`Tạo & quản lý báo giá nhà cung cấp`** trước `Hoàn tất hồ sơ`.
- Mẫu hồ sơ nghiệp vụ người dùng cung cấp xác nhận pattern cuối cùng gồm **03 đơn vị báo giá và bảng so sánh 03 cột giá**. Tài liệu repository không chứa tên NCC/hồ sơ thật.
- Hệ thống **tạo báo giá nháp trước**; sau đó người dùng quyết định gộp/tách/chuyển nhóm thiết bị vào các báo giá phù hợp.
- Hệ thống không tự quyết định cấu trúc báo giá cuối cùng.
- Lineage phải giữ ở **cấp dòng báo giá**, vì một báo giá mới có thể chứa thiết bị đến từ nhiều hồ sơ lịch sử khác nhau.
- Với thiết bị đã từng được thẩm định và có dữ liệu báo giá lịch sử phù hợp, hệ thống lấy **đủ đơn giá của 03 nhà cung cấp cũ** gắn với tài sản/hồ sơ lịch sử đó.
- **Nếu nhiều thiết bị cùng dẫn về một nhà cung cấp, hệ thống phải tổng hợp chúng vào báo giá nháp/hiện tại phù hợp của chính NCC đó; không tạo thêm báo giá trùng NCC nếu đã tồn tại một báo giá phù hợp của NCC đó.**
- Khi thiết bị từ nhiều hồ sơ cũ khác nhau cùng dẫn về một NCC, chúng có thể được tổng hợp vào cùng báo giá NCC hiện tại, nhưng lineage từng dòng bắt buộc giữ theo chuỗi `Tài sản hiện tại → Hồ sơ cũ → Báo giá cũ → NCC → Giá lịch sử → Báo giá hiện tại`.
- Một hồ sơ chỉ phát sinh thêm báo giá nháp khi thực sự cần một quan hệ NCC/báo giá khác; số báo giá nháp không được tăng chỉ vì các dòng đến từ hồ sơ lịch sử khác nhau nhưng cùng một NCC.
- Mỗi đơn giá NCC lịch sử được so sánh với **Giá sơ bộ từ Pre-case**. Chỉ cần khác giá sơ bộ là UI phải có cảnh báo; không cần ngưỡng % tối thiểu.
- Cảnh báo nêu rõ ít nhất: giá sơ bộ, giá NCC lịch sử, chênh lệch tiền và % chênh lệch. Cảnh báo không tự sửa giá và không tự loại nguồn.
- Với thiết bị chỉ có căn cứ Internet và **không có lịch sử báo giá**, người dùng chọn một báo giá để điền `Đơn giá hiện hành` làm **giá đề nghị để NCC xác nhận**.
- Hai báo giá còn lại trong cùng bộ có thể được hệ thống sinh **giá đề nghị** trong khoảng:

```text
Đơn giá hiện hành <= Giá đề nghị <= Đơn giá hiện hành × 115%
```

- Hai mức giá hệ thống sinh chỉ là **giá đề nghị để NCC xác nhận**, không được coi là `Đơn giá NCC đã xác nhận` trước khi NCC phản hồi/ký/đóng dấu.
- NCC có thể giữ nguyên hoặc sửa mức giá trên file trước khi xác nhận; sau khi nhận lại file ký/đóng dấu, mức giá thực tế trở thành `Đơn giá NCC đã xác nhận`.
- Cơ sở xác định `Đơn giá hiện hành` của tài sản vẫn có thể là Nguồn Internet; workflow báo giá NCC là lớp chứng từ/bằng chứng bổ trợ và không tự thay `Đơn giá hiện hành`.
- Sau khi nhận các báo giá đã xác nhận, có CTA **`Chọn nhà cung cấp đã xác nhận giá`** để người dùng chọn các NCC/báo giá dùng trong hồ sơ.
- Việc chọn được lưu theo `NCC → báo giá cụ thể → các dòng thiết bị → đơn giá NCC đã xác nhận → file ký/đóng dấu`, không chỉ lưu tên NCC.
- **`STT` của thiết bị là thứ tự/lineage bất biến của danh mục gốc.** Gộp thiết bị, tách báo giá, chuyển báo giá, nhóm theo NCC, nhóm theo hồ sơ cũ hoặc sort theo giá không được đánh lại hay thay đổi STT gốc.
- Các thao tác báo giá chỉ thay quan hệ `Tài sản → Báo giá`; chúng không thay lineage/order của danh mục ban đầu. UI có thể thay thứ tự hiển thị khi sort/filter, nhưng số `STT` hiển thị cho từng tài sản vẫn giữ nguyên giá trị gốc.
- **Mockup NCCQ Iteration 6 đã được người dùng duyệt và nâng thành baseline authority.** Các iteration NCCQ trước đó chỉ còn giá trị lịch sử/tham khảo và không được dùng để override baseline này.

### 0.4 Mẫu báo giá nhà cung cấp — Word-only; TM01 và TM03 visual baseline đã duyệt

- Người dùng sẽ đưa mẫu báo giá riêng của từng NCC vào hệ thống.
- **Template báo giá NCC chỉ dùng Microsoft Word `.docx`. Không dùng Excel/PDF làm template báo giá NCC.**
- Phần mềm phải có khả năng tự fill dữ liệu hồ sơ/danh mục vào đúng template Word của NCC.
- Luồng thiết kế đã thống nhất ở mức IA/UX:

```text
Cấu hình → Mẫu báo giá nhà cung cấp
→ Tạo mẫu mới
→ Upload file Word (.docx)
→ Mapping field / vùng lặp
→ Preview / Test fill
→ Lưu template
→ Sẵn sàng sử dụng
```

- Mỗi NCC có thể có template Word riêng và nhiều version.
- Mapping phải hỗ trợ vùng text/placeholder và bảng danh mục lặp: STT, thiết bị, mô tả/thông số, ĐVT, SL, đơn giá, thành tiền, ghi chú.
- Template gốc và version cũ phải giữ để truy vết.
- Module template gồm tối thiểu TM01–TM05: danh sách mẫu, metadata mẫu, Upload & Mapping, Preview/Test fill, lịch sử phiên bản.
- **TM01 — Danh sách mẫu báo giá NCC — Iteration 1 đã được người dùng duyệt và nâng thành baseline authority.**
- **TM03 — Upload & Mapping template — Iteration 1 Word-only đã được người dùng duyệt và nâng thành baseline authority. Bản mockup TM03 dùng Excel trước đó bị superseded và không còn authority.**
- TM04 vẫn ở trạng thái IA/UX đã thiết kế nhưng mockup chưa duyệt baseline cuối.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị.
- Chỉ dùng phương pháp so sánh.
- Công việc chính: Kho tri thức + Nguồn Internet + Hồ sơ cũ/Giá lịch sử + Thuyết minh đơn giá + báo giá NCC.
- Không thiết kế khảo sát hiện trạng.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word/PDF là input/output của toàn hệ thống; riêng **template báo giá NCC chỉ dùng Word `.docx`**.
- Workbench + database là nguồn dữ liệu làm việc chính thức.
- Không thiết kế workflow giao việc/chờ xác nhận giữa nhiều tài khoản ở giai đoạn này.
- Giá dùng trong kết quả thẩm định luôn là mức giá do người dùng nghiệp vụ ấn định hoặc sửa; hệ thống không tự sinh quyết định giá.
- Giá hệ thống sinh để chuẩn bị báo giá NCC chỉ là **giá đề nghị**, không phải quyết định thẩm định và không phải giá NCC xác nhận cho tới khi có phản hồi/xác nhận phù hợp.

## 2. North-star user flow v2.3

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
    → Kho tri thức
    → Nguồn giá Internet / Thuyết minh đơn giá
    → Giá thị trường tham khảo
    → Vận chuyển (%)
    → Đơn giá đề xuất
    → Người dùng ấn định / điều chỉnh giá
→ Quay lại Quản lý yêu cầu sơ bộ
    → Rà soát tích hợp
    → Tạo file kết quả sơ bộ
→ S09 Chuyển sang thẩm định chính thức
→ S10 Tổng quan hồ sơ
→ S11 Xác nhận & điều chỉnh danh mục triển khai
→ S12 Workbench tài sản
    → S13 Asset Context Drawer / Ngữ cảnh tài sản
→ Nguồn giá & Chứng cứ
    → Nguồn Internet
    → Hồ sơ cũ / Giá lịch sử
    → Thuyết minh đơn giá
    → Tổng hợp căn cứ
    → Người dùng có thể sửa Đơn giá hiện hành
→ Tạo & quản lý báo giá nhà cung cấp
    → Hệ thống sinh báo giá nháp theo NCC, tránh trùng NCC
    → Người dùng gộp/tách/chuyển thiết bị giữa các báo giá nhưng giữ nguyên STT gốc
    → Rà soát cảnh báo chênh lệch giá
    → Tạo file theo template Word NCC
    → Gửi NCC xác nhận / ký đóng dấu
    → Nhận file đã xác nhận
    → Chọn nhà cung cấp đã xác nhận giá
→ S17 Hoàn tất hồ sơ
→ S18 Báo cáo & Chứng thư
→ S19 Phát hành
→ S20 Lưu trữ & hình thành tri thức
```

Luồng quản trị template dùng chung:

```text
Cấu hình
→ Mẫu báo giá nhà cung cấp
→ Tạo / chỉnh template Word
→ Upload .docx
→ Mapping
→ Preview / Test fill
→ Lưu version
→ Sẵn sàng sử dụng
```

Không có checkpoint riêng `Khai báo thông tin thực hiện`, `Xác nhận giá thẩm định chính thức`, `Kiểm tra hồ sơ`, `KSCL`.

## 3. Pre-case baseline

Trạng thái cấp danh sách: `Mới tạo`, `Mới nhận danh mục`, `Đang phân tích`, `Sẵn sàng tạo kết quả sơ bộ`, `Đã tạo kết quả sơ bộ`, `Không tiếp tục`, `Đã chuyển thành hồ sơ`.

Không dùng `Ghi nhận đã gửi`, `Chờ khách hàng phản hồi`, `Ghi nhận phản hồi`, `Đã chấp thuận giá đề xuất`.

S08 vẫn là checkpoint tích hợp trong S02. File kết quả sơ bộ là bản sao file Excel khách hàng và bổ sung đúng 02 cột `Đơn giá đề xuất`, `Thành tiền`; file gốc không bị ghi đè; output có version/lineage.

### 3.1 Cụm giá Pre-case

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
→ Người dùng ấn định / sửa giá
```

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

- Không hiển thị `Chênh lệch`, `Chi phí vận chuyển`, `Giá sau vận chuyển`.
- `Thuyết minh đơn giá` có thể là căn cứ duy nhất của một dòng nếu người dùng chấp nhận căn cứ đó.
- Không cho tạo file kết quả sơ bộ nếu còn dòng trong phạm vi cần định giá mà chưa có mức giá do người dùng ấn định.
- Mức giá hiện hành tại thời điểm tạo file được ghi vào cột `Đơn giá đề xuất`.
- Khi chuyển thành hồ sơ chính thức, mức giá này được kế thừa làm giá khởi tạo của kết quả thẩm định, nhưng người dùng vẫn có thể sửa tiếp trong quá trình xử lý hồ sơ.

### 3.2 Quy tắc Đơn giá hiện hành

Một tài sản có **một `Đơn giá hiện hành`** dùng cho kết quả thẩm định tại từng thời điểm.

- Giá hiện hành ban đầu có thể kế thừa từ Pre-case.
- Người dùng có thể sửa giá tại context phù hợp trong S12/S13/Nguồn giá & Chứng cứ hoặc bề mặt chỉnh giá được duyệt sau này.
- Sau khi người dùng lưu/commit thay đổi, mức mới trở thành `Đơn giá hiện hành`; mức cũ vẫn giữ trong lịch sử/lineage.
- `Giá sơ bộ` từ Pre-case vẫn được giữ riêng để đối chiếu/cảnh báo với giá NCC lịch sử.
- Không cần bước `Xác nhận giá chính thức` riêng sau mỗi lần sửa.
- AI, Kho tri thức, rule engine, nguồn Internet, hồ sơ cũ hoặc báo giá NCC không được tự ghi đè `Đơn giá hiện hành`.
- Khi hồ sơ đã khóa/phát hành, khả năng sửa giá tuân theo lifecycle/version/change workflow; v2.3 không thiết kế bypass trạng thái khóa.

## 4. S09 — Chuyển sang thẩm định chính thức

### 4.1 Nguyên tắc

- Pre-case phải có file kết quả sơ bộ.
- Giá hiện hành trong Pre-case được copy vào snapshot hồ sơ chính thức cùng provenance/lineage và trở thành giá khởi tạo của tài sản.
- `Giá sơ bộ từ Pre-case` được giữ như mốc lineage/đối chiếu, kể cả sau khi `Đơn giá hiện hành` đã được người dùng sửa.
- Không tạo bước xác nhận lại giá chỉ để đổi tên từ `giá sơ bộ` sang `giá chính thức`.
- Sau khi tạo hồ sơ, người dùng vẫn có thể chỉnh giá trong quá trình làm việc.
- Trường hồ sơ chưa điền đủ vẫn có thể tạo hồ sơ nếu chưa tới dependency bắt buộc; hiển thị `Chưa bổ sung`.

### 4.2 Chủ đầu tư & liên hệ

`Chủ đầu tư` là searchable select theo tên/MST/số điện thoại. Chọn record hiện có sẽ prefill snapshot hồ sơ: Chủ đầu tư, Mã số thuế, Số ĐT, Địa chỉ, Tài khoản Chủ đầu tư, Người đại diện, Chức vụ, Người liên hệ.

Sửa snapshot trong hồ sơ không tự ghi đè customer master; cập nhật master phải là thao tác riêng.

### 4.3 Thông tin hồ sơ & thẩm định

**2A — Nhận diện hồ sơ**:

```text
[Tài sản thẩm định]
[Mục đích]
[Ghi chú]
```

- `Tên hồ sơ` ẩn và tự sinh từ `Tài sản thẩm định`.
- Biến thể `Tài sản thẩm định (viết thường)` là dữ liệu dẫn xuất, không hiển thị field riêng.

**2B — Mốc hồ sơ / số hiệu văn bản**:

```text
[Ngày hợp đồng]    [Số hợp đồng]    [Số QĐ]
[Ngày chứng thư]   [Số chứng thư]   [Thời điểm TĐ]
[Ngày thương thảo] [Ngày dự thảo]
```

Dữ liệu dẫn xuất/ẩn: ngày hợp đồng dạng chữ; `Ngày báo cáo = Ngày chứng thư`; ngày chứng thư dạng chữ; `Thời điểm TĐ (chân trang)` tự sinh từ `Thời điểm TĐ`.

**2C — Giá trị & phí**:

```text
[Tổng giá trị] [Giá đã bao gồm]
[Phí thẩm định]
```

**Biên bản nghiệm thu & thanh lý**:

```text
[Ngày thanh lý] [Số hóa đơn] [Ngày hóa đơn]
```

Primary CTA: `Tạo hồ sơ thẩm định chính thức`. Tạo thành công → Pre-case `Đã chuyển thành hồ sơ`, hồ sơ mới `Đang xử lý`, mở S10.

## 5. S10 — Tổng quan hồ sơ

### 5.1 Mục tiêu

S10 là dashboard điều phối hồ sơ chính thức, không phải form nhập liệu dài.

### 5.2 Workflow rút gọn

Workflow hiện tại gồm **8 checkpoint**:

1. `Thông tin hồ sơ`;
2. `Danh mục triển khai`;
3. `Hoàn thiện tài sản`;
4. `Nguồn giá & chứng cứ`;
5. `Báo giá nhà cung cấp`;
6. `Hoàn tất hồ sơ`;
7. `Báo cáo & Chứng thư`;
8. `Phát hành`.

Không có checkpoint riêng `Thông tin thực hiện`, `Giá thẩm định chính thức`, `Kiểm tra hồ sơ`, `KSCL`.

### 5.3 Readiness / cột phải

Có thể tổng hợp:

- mức hoàn thiện thông tin hồ sơ;
- số tài sản triển khai;
- tiến độ nhận diện;
- số Nguồn Internet;
- số căn cứ Hồ sơ cũ/Giá lịch sử;
- số Thuyết minh đơn giá;
- số dòng đã có Đơn giá hiện hành;
- số dòng chưa có giá;
- số dòng có warning giá/căn cứ cần rà soát;
- số báo giá nháp;
- số báo giá đã tạo file;
- số báo giá/NCC đã xác nhận;
- số NCC/báo giá đã được chọn dùng trong hồ sơ;
- readiness;
- thông tin cần bổ sung;
- nguồn Pre-case/file/snapshot/lineage;
- người thực hiện lấy từ Cấu hình.

Ngay sau S09, card `Việc cần làm tiếp theo` dẫn vào S11. S10 chỉ tổng hợp validation; mọi vấn đề cụ thể có CTA `Đi tới` đúng nơi sửa.

## 6. S11 — Xác nhận & điều chỉnh danh mục triển khai

- S11 chốt phạm vi tài sản, không phải màn hình chuyên xử lý giá.
- Cho phép giữ nguyên, thêm mới, loại bớt và khôi phục tài sản trước khi xác nhận.
- Tài sản bị loại không bị xóa khỏi Pre-case; giữ đầy đủ lineage.
- Dòng mới có badge `Mới bổ sung`, không tự sao chép giá từ tài sản khác.
- Dòng mới chưa có giá vẫn được phép đi qua S11; khi vào S12 hiển thị trạng thái `Cần phân tích giá` cho tới khi người dùng nhập/ấn định giá.
- `Tổng triển khai = Giữ lại + Mới bổ sung`.
- Primary CTA: `Xác nhận danh mục triển khai`.

## 7. S12 — Workbench tài sản

### 7.1 Mục tiêu

S12 là bảng làm việc chính của danh mục đã chốt tại S11. Người dùng hoàn thiện nhận diện/thông số, rà soát nguồn/candidate và có thể tiếp tục điều chỉnh giá.

### 7.2 Visual baseline đã duyệt

S12 dùng Fluent 2, desktop-first, ưu tiên data grid lớn:

- shell VALORA thống nhất với S09–S11;
- header `S12 Workbench tài sản`;
- card hồ sơ + KPI readiness;
- notice dữ liệu gốc Excel luôn được giữ nguyên;
- toolbar filter/search/tùy chỉnh cột;
- nhóm cột `Thông tin từ Excel (Dữ liệu gốc)` và `Thông tin chuẩn hóa (Bạn đang chỉnh sửa)` đặt cạnh nhau;
- cột `Thông số kỹ thuật chính`, `Trạng thái`, `Kho tri thức`, `Nguồn giá`, `Đơn giá hiện hành`, `Thao tác`;
- mỗi dòng có `Mở ngữ cảnh` để mở S13.

### 7.3 Trạng thái dòng

Có thể gồm `Đủ thông tin`, `Cần bổ sung`, `Mới bổ sung`, `Cần phân tích giá`. Trạng thái Kho tri thức tách riêng như `Có gợi ý`, `Cần xác nhận`, `Chưa có`.

### 7.4 Quy tắc sửa giá trong S12

- Giá kế thừa từ Pre-case là giá khởi tạo, không phải giá bị khóa.
- Người dùng có thể chỉnh giá tại bề mặt được phép hoặc mở context Nguồn giá/S13.
- Mỗi thay đổi giá là thao tác explicit của người dùng và có lịch sử.
- Dòng mới không tự sao chép giá từ tài sản khác.
- Nếu thay đổi identity quan trọng, hệ thống cảnh báo giá/căn cứ hiện hành cần rà soát; không tự xóa hoặc tự thay giá.
- Người dùng quyết định `Giữ giá hiện tại`, `Sửa giá` hoặc tiếp tục phân tích nguồn/căn cứ.
- AI/Kho tri thức không tự thay giá.

### 7.5 Guardrail S12

- Raw source không bị ghi đè.
- Dòng không đổi có thể tái sử dụng candidate Kho tri thức, Nguồn Internet, Hồ sơ cũ/Giá lịch sử, Thuyết minh và giá từ Pre-case.
- Dòng mới hoặc thay đổi identity quan trọng phải được đánh dấu/cảnh báo phù hợp.
- Primary CTA cuối bước: `Tiếp tục sang Nguồn giá & chứng cứ` khi readiness phù hợp.

## 8. S13 — Asset Context Drawer / Ngữ cảnh tài sản

### 8.1 Mục tiêu và hành vi

S13 xử lý sâu một tài sản đang chọn trong S12 mà không rời Workbench. Đây là drawer bên phải, mở từ `Mở ngữ cảnh`.

Khi mở:

- S12 giữ nguyên search/filter/sort/pagination/selection/scroll;
- dòng đang mở được highlight;
- có `Đóng ngữ cảnh (Esc)`;
- lưu/đóng quay đúng vị trí S12 trước đó;
- không tạo route/menu độc lập.

### 8.2 Header và cấu trúc

Header hiển thị tên thiết bị chuẩn hóa, hãng/model, mã tài sản, trạng thái và badge nguồn.

Khuyến nghị 4 tab:

1. `Tổng quan`;
2. `Thông số kỹ thuật`;
3. `Nguồn giá & Chứng cứ`;
4. `Lịch sử`.

Không dùng wizard đa bước.

### 8.3 Raw vs Normalized

```text
Dữ liệu gốc (Excel) | Dữ liệu chuẩn hóa (Đang chỉnh sửa)
```

Tối thiểu: Tên thiết bị, Hãng, Model, Xuất xứ, Năm sản xuất nếu có, Tình trạng nếu có, Vị trí nếu có, Thông số kỹ thuật chính.

Raw read-only; normalized được chỉnh theo guardrail. Thay đổi identity quan trọng phải cảnh báo nếu làm giảm độ phù hợp của candidate, nguồn hoặc giá hiện hành.

### 8.4 Validation inline

- `Blocking`: phải xử lý trước hành động có dependency.
- `Warning`: vẫn tiếp tục nhưng nêu rõ ảnh hưởng.
- `Info`: thông tin trạng thái.

Mọi validation trả lời: `Vấn đề gì → nằm ở đâu → ảnh hưởng gì → sửa thế nào`.

### 8.5 Kho tri thức / candidate

Mỗi candidate tối thiểu có canonical identity, mức tương đồng, điểm giống/khác, model/thông số, giá lịch sử và nguồn/ngày tham chiếu khi có. Hành động `Dùng`, `Không dùng`, `Xem chi tiết`. Không auto-accept.

### 8.6 Summary nguồn/căn cứ

Trong drawer có:

- `Nguồn Internet`;
- `Hồ sơ cũ / Giá lịch sử`;
- `Thuyết minh đơn giá`;
- `Đơn giá hiện hành`;
- trạng thái `Chưa có nguồn`, `Cần xác nhận`, `Đủ thông tin`, `Cần bổ sung`, `Cần phân tích giá`.

CTA `Xem Nguồn giá & Chứng cứ` mở đúng context tài sản.

### 8.7 Lưu / state / lineage

Footer: `Hủy thay đổi`, `Lưu thông tin`, `Đóng ngữ cảnh (Esc)`. Nếu có unsaved changes khi đóng, hỏi `Lưu / Bỏ thay đổi / Tiếp tục chỉnh sửa`.

S13 có loading/empty/error/warning cho normalized data, candidate, nguồn, hồ sơ cũ, stale data và identity change.

Lineage:

```text
Raw source / Excel
→ Dữ liệu chuẩn hóa
→ Candidate Kho tri thức
→ Nguồn Internet / Hồ sơ cũ-Giá lịch sử / Thuyết minh
→ Giá do người dùng ấn định
→ Các lần người dùng chỉnh giá
→ Đơn giá hiện hành
```

## 9. Nguồn giá & Chứng cứ — baseline đã duyệt

### 9.1 Mục tiêu

Checkpoint sau S12/S13 để người dùng xem, bổ sung, rà soát và truy vết căn cứ giá của từng tài sản, đồng thời có thể sửa `Đơn giá hiện hành`. Không phải checkpoint xác nhận giá lần thứ hai.

### 9.2 Visual baseline

- Cùng VALORA shell, Fluent 2, desktop-first.
- Asset header: tên/mã tài sản, hãng/model/xuất xứ, trạng thái, `Đơn giá hiện hành`, `Giá khởi tạo từ Pre-case`, lần cập nhật gần nhất, summary từng nhóm căn cứ.
- CTA `Chỉnh sửa đơn giá`.
- Vùng tab + bảng + panel chi tiết bên phải.
- Timeline `Lịch sử thay đổi đơn giá hiện hành`.

### 9.3 Bề mặt chính

```text
Nguồn Internet
| Hồ sơ cũ / Giá lịch sử
| Thuyết minh đơn giá
| Tổng hợp căn cứ
```

Ba nhóm đầu là ba loại căn cứ ngang hàng.

### 9.4 Nguồn Internet

Tối thiểu: loại nguồn, tiêu đề/mô tả, URL/định danh, giá tham khảo, ngày thu thập/cập nhật, trạng thái truy cập, độ phù hợp nếu có, snapshot/tài liệu, trạng thái rà soát. Nguồn mất truy cập vẫn giữ URL/snapshot/lịch sử nếu đã dùng.

### 9.5 Hồ sơ cũ / Giá lịch sử

Danh sách tối thiểu:

- Mã hồ sơ cũ;
- Tên tài sản cũ;
- Hãng/Model;
- Thời điểm thẩm định;
- Đơn giá đã dùng;
- Mức tương đồng;
- Trạng thái;
- thao tác xem chi tiết.

Cách tính mức tương đồng chi tiết chưa khóa; UI không tự suy diễn công thức scoring.

### 9.6 Panel chi tiết hồ sơ cũ

Hiển thị mã hồ sơ, tài sản cũ, hãng/model, thời điểm TĐ, đơn giá đã dùng, mức tương đồng, người thực hiện/đơn vị nếu có, điểm khác biệt, tài liệu liên quan. Có `Xem hồ sơ gốc` / `Xem tài liệu` khi quyền cho phép.

### 9.7 Dùng hồ sơ cũ làm căn cứ

- Ghi lineage tài sản hiện tại ↔ hồ sơ cũ.
- Không tự copy giá cũ thành `Đơn giá hiện hành`.
- Người dùng quyết định giữ/sửa giá hiện hành.
- UI phân biệt `Đang dùng làm căn cứ` và `Chỉ tham khảo`.
- Nếu model/thông số khác quan trọng, hiển thị cảnh báo thay vì coi giá cũ tương đương tuyệt đối.

### 9.8 Thuyết minh đơn giá

Cho phép lập/chỉnh nội dung thuyết minh theo tài sản; có thể là căn cứ duy nhất nếu người dùng chấp nhận và rule nghiệp vụ cho phép; giữ version/lịch sử; không tự sinh quyết định giá.

### 9.9 Tổng hợp căn cứ

Hiển thị Nguồn Internet, Hồ sơ cũ/Giá lịch sử, Thuyết minh đang dùng và chỉ tham khảo; trạng thái rà soát; Giá khởi tạo từ Pre-case; Đơn giá hiện hành; warning identity/căn cứ thay đổi.

### 9.10 Chỉnh sửa Đơn giá hiện hành

- Người dùng nhập/ấn định giá mới.
- Có thể yêu cầu lý do/ghi chú theo UX phù hợp.
- Sau lưu/commit, mức mới trở thành `Đơn giá hiện hành`.
- Giá cũ, actor, time và căn cứ tại thời điểm đổi giá vẫn truy vết được.
- Không cần S14.

### 9.11 Guardrail checkpoint

Được phép: xem/thêm/rà soát Internet, Hồ sơ cũ, Thuyết minh; tổng hợp căn cứ; sửa Đơn giá hiện hành bằng quyết định explicit; xem lịch sử/lineage.

Không được: auto-price; tự copy giá hồ sơ cũ; auto-accept căn cứ; xóa im lặng evidence/history; biến giá lịch sử thành giá hiện hành không có thao tác người dùng.

## 10. Tạo & quản lý báo giá nhà cung cấp — baseline authority đã duyệt

### 10.1 Mục tiêu

Checkpoint này biến dữ liệu giá/căn cứ đã có thành các **báo giá nháp theo NCC**, cho phép người dùng tổ chức lại danh mục, tạo file theo mẫu NCC, theo dõi xác nhận/ký đóng dấu và chọn NCC đã xác nhận giá dùng trong hồ sơ.

Không dùng checkpoint này để tự thay `Đơn giá hiện hành`.

### 10.2 Bố cục baseline

Baseline dùng **Fluent 2, desktop-first, table-first**, bám visual language của S11/S12/S13 và cấu trúc Excel nghiệp vụ. Bảng là bề mặt làm việc chính; hạn chế tối đa card giải thích cố định chiếm viewport.

Cấu trúc tham chiếu chính:

```text
STT
| Tên tài sản
| ĐVT
| Số lượng
| Đơn giá nhà cung cấp
    | NCC 1
    | NCC 2
    | NCC 3
| Đơn giá thẩm định
    | Đơn giá chọn
    | Thành tiền
| Đơn giá hiện hành
```

- Các cột NCC hiển thị **số tiền trực tiếp**, không chỉ badge trạng thái.
- Semantic giá hiển thị ngay dưới/đi kèm số tiền bằng badge nhỏ: `Giá lịch sử`, `Giá đề nghị — chờ NCC xác nhận`, `Giá NCC đã xác nhận`.
- Các nhóm/hạng mục như `HỆ THỐNG ...`, `I. ...`, `II. ...` hiển thị dạng section/header row tương tự Excel thực tế.
- `STT` và `Tên tài sản` nằm ở vùng trái dễ đối chiếu; `STT` có affordance thể hiện bất biến.
- Lineage, hồ sơ cũ nguồn, báo giá cũ và cảnh báo chi tiết ưu tiên đưa vào **drawer phải theo dòng đang chọn** thay vì mở rộng bảng chính quá mức.
- Toolbar phía trên bảng ưu tiên search/filter, nhóm theo NCC, batch actions và `Thiết lập cột`.
- Primary CTA của checkpoint là **`Chọn nhà cung cấp đã xác nhận giá`** khi điều kiện cho phép; các action `Xuất Excel`, `Tạo file theo template` là secondary actions.
- Baseline không đặt các card giải thích dài phía dưới bảng; khu vực cuối bảng chỉ giữ tổng tiền, legend trạng thái và pagination cần thiết.

### 10.3 Hệ thống sinh báo giá nháp trước

- Hệ thống tạo cấu trúc báo giá nháp từ dữ liệu lịch sử/Internet hiện có.
- Sau khi sinh, người dùng mới gộp/tách/chuyển thiết bị giữa các báo giá.
- **Báo giá nháp được dedupe theo NCC phù hợp:** nếu đã có một báo giá nháp/hiện tại của NCC đó trong context tương thích, thiết bị mới cùng NCC phải được đưa vào báo giá hiện có thay vì sinh thêm báo giá trùng NCC.
- Thiết bị từ nhiều hồ sơ lịch sử khác nhau có thể cùng nằm trong một báo giá hiện tại của cùng NCC; provenance được giữ ở cấp dòng.
- Một hồ sơ có thể phát sinh nhiều hơn 03 báo giá nháp nếu thực sự có nhiều NCC/báo giá khác nhau sau khi áp dụng rule dedupe theo NCC; không tăng số báo giá chỉ vì khác hồ sơ cũ.
- Hệ thống không ép người dùng giữ nguyên cấu trúc nháp.

### 10.4 Thiết bị có 03 giá NCC lịch sử

Với tài sản có hồ sơ lịch sử phù hợp:

- lấy đủ 03 đơn giá NCC cũ;
- giữ nguồn theo từng dòng: hồ sơ cũ → báo giá cũ → NCC → đơn giá lịch sử;
- nếu nhiều dòng cùng NCC thì đưa vào cùng báo giá hiện tại phù hợp của NCC đó;
- so sánh từng giá NCC cũ với `Giá sơ bộ từ Pre-case`;
- nếu khác, hiển thị warning ngay dòng/cell;
- warning hiển thị giá sơ bộ, giá lịch sử, chênh lệch tiền và %;
- không tự sửa `Đơn giá hiện hành`.

### 10.5 Thiết bị không có lịch sử báo giá

Với tài sản chỉ có căn cứ Internet:

1. người dùng chọn một báo giá trong bộ để điền `Đơn giá hiện hành` làm **giá đề nghị để NCC xác nhận**;
2. hai báo giá còn lại có thể được hệ thống sinh giá đề nghị trong biên 100%–115% của Đơn giá hiện hành;
3. hệ thống nên tránh sinh hai giá giống nhau khi có thể, nhưng thuật toán ngẫu nhiên/rounding chi tiết chưa khóa ở tài liệu này;
4. mọi giá hệ thống sinh được đánh dấu semantic `Giá đề nghị — chờ NCC xác nhận`;
5. chỉ sau khi NCC phản hồi/ký/đóng dấu mới chuyển thành `Đơn giá NCC đã xác nhận`.

### 10.6 Gộp / tách / chuyển thiết bị

Người dùng được phép:

- chọn nhiều dòng;
- `Đưa vào báo giá`;
- `Chuyển sang báo giá khác`;
- `Tách thành báo giá mới`;
- `Bỏ khỏi báo giá` khi phù hợp;
- tạo báo giá mới.

Rule thao tác:

- một báo giá mới có thể chứa thiết bị đến từ nhiều hồ sơ lịch sử; provenance của từng dòng không được mất;
- nếu thao tác chuyển/gộp làm các dòng cùng về một NCC đã có báo giá phù hợp, hệ thống phải **hợp nhất vào báo giá NCC hiện có**, không tạo duplicate quote chỉ vì khác nguồn lịch sử;
- tách báo giá là thay đổi quan hệ `Tài sản → Báo giá`, không phải tái tạo tài sản hay đánh lại thứ tự;
- **mọi thao tác gộp/tách/chuyển/nhóm không được thay `STT` gốc.**

### 10.7 Bảng làm việc baseline

```text
Checkbox
| STT
| Tên tài sản
| ĐVT
| Số lượng
| Đơn giá nhà cung cấp
    | NCC 1
    | NCC 2
    | NCC 3
| Đơn giá thẩm định
    | Đơn giá chọn
    | Thành tiền
| Đơn giá hiện hành
| Thao tác
```

Quy tắc hiển thị:

- `STT` là giá trị immutable từ danh mục gốc; nên pin/freeze gần mép trái cùng `Tên tài sản` để người dùng đối chiếu nhanh.
- Sort theo giá/NCC/trạng thái chỉ thay thứ tự hàng trên màn hình, **không renumber STT**.
- Mỗi cột NCC hiển thị số tiền trực tiếp; dưới số tiền có badge semantic nhỏ khi cần.
- Warning chênh lệch có icon/badge ngay cell giá NCC; hover/click hoặc chọn dòng mở chi tiết `Giá sơ bộ → Giá NCC lịch sử → Chênh lệch tiền → %` trong context/drawer.
- Dòng tài sản có thể mở `Lineage & tổng hợp` để xem `Hồ sơ cũ nguồn → Báo giá cũ → NCC → Giá lịch sử → Báo giá hiện tại`, giá trị đối chiếu, trạng thái dòng và file evidence.
- Dòng section/header không có giá, không bị đánh STT mới và giữ đúng cấu trúc hạng mục từ danh mục gốc.
- Toolbar phía trên bảng chứa thao tác batch `Đưa vào báo giá`, `Chuyển báo giá`, `Tách báo giá`; thông tin hướng dẫn dài không đặt thành card cố định dưới bảng.
- Hàng tổng cuối bảng hiển thị tối thiểu `Tổng tiền (Đơn giá chọn)` và `Tổng tiền (Hiện hành)`; chênh lệch tổng có thể hiển thị khi hữu ích.
- Legend trạng thái ở cuối bảng giải nghĩa compact: `Đã xác nhận`, `Chờ xác nhận`, `Đề nghị`, `Chưa có`.

### 10.8 Cảnh báo chênh lệch

Rule hiện tại:

```text
Giá NCC lịch sử != Giá sơ bộ từ Pre-case
→ Warning
```

Không tự đặt ngưỡng %. Warning là thông tin để người dùng biết, không phải auto-reject.

### 10.9 Tạo file báo giá theo template NCC

Khi cấu trúc báo giá đã sẵn sàng:

- người dùng bấm `Tạo file báo giá` / `Tạo file theo template`;
- hệ thống dùng **template Word `.docx` của NCC** nếu đã cấu hình;
- preview tối thiểu: NCC, danh sách thiết bị, SL/ĐVT, đơn giá, thành tiền, tổng cộng;
- thứ tự/STT trong file output phải giữ STT gốc của danh mục, kể cả khi báo giá chỉ chứa một subset tài sản;
- nếu còn warning chênh lệch, hệ thống hiển thị rõ trước khi tạo file nhưng không mặc định biến warning thành blocking;
- file tạo ra có version/lineage.

### 10.10 Lifecycle báo giá

Đề xuất trạng thái:

```text
Nháp
→ Sẵn sàng tạo file
→ Đã tạo file
→ Chờ NCC xác nhận
→ Đã nhận bản ký
→ Đã xác nhận giá
→ Được chọn dùng trong hồ sơ
```

Tên trạng thái có thể tinh chỉnh i18n nhưng semantic phải giữ.

### 10.11 NCC sửa giá khi xác nhận

- Giá lúc gửi đi và giá NCC xác nhận phải phân biệt.
- Nếu NCC sửa giá, mức trả về trở thành `Đơn giá NCC đã xác nhận`.
- Giá trước khi gửi vẫn giữ trong lịch sử.
- Thay đổi của NCC không tự sửa `Đơn giá hiện hành` của tài sản.

### 10.12 Chọn nhà cung cấp đã xác nhận giá

CTA sau giai đoạn nhận báo giá:

**`Chọn nhà cung cấp đã xác nhận giá`**

- CTA active khi có ít nhất một báo giá/NCC ở trạng thái phù hợp để chọn.
- Drawer/modal chọn hiển thị tối thiểu: NCC, mã báo giá, số thiết bị đã xác nhận, tổng giá trị, file ký/đóng dấu, ngày xác nhận, số dòng giá thay đổi và trạng thái.
- Người dùng tick các NCC/báo giá muốn sử dụng trong hồ sơ.
- Lưu selection ở mức báo giá + NCC + dòng thiết bị + giá xác nhận + file evidence.
- Nếu coverage chưa đủ theo nhu cầu nghiệp vụ, UI phải chỉ rõ thiết bị nào mới có 1/2/3 NCC xác nhận; không tự bổ sung NCC.

### 10.13 Lineage báo giá

Mỗi dòng báo giá phải truy vết được:

```text
Tài sản hiện tại
→ Hồ sơ cũ
→ Báo giá cũ
→ NCC
→ Giá lịch sử
→ Báo giá hiện tại
→ File gửi NCC
→ Giá NCC đã xác nhận
→ File ký/đóng dấu
→ NCC/báo giá được chọn dùng trong hồ sơ
```

Với dòng Internet-only, đoạn `Hồ sơ cũ → Báo giá cũ → NCC → Giá lịch sử` được thay bằng `Nguồn Internet → Giá đề nghị hệ thống/người dùng chuẩn bị → NCC/báo giá hiện tại`.

Nếu nhiều dòng từ nhiều hồ sơ cũ cùng về một NCC, chúng có thể dùng chung `Báo giá hiện tại`, nhưng phần lineage trước nút này vẫn độc lập theo từng dòng.

### 10.14 Guardrail

Checkpoint được phép:

- sinh báo giá nháp;
- tái sử dụng/hợp nhất vào báo giá hiện tại của cùng NCC khi phù hợp;
- sinh giá đề nghị trong biên đã khóa cho thiết bị không có lịch sử;
- cho người dùng gộp/tách/chuyển dòng;
- tạo file theo template;
- ghi nhận giá NCC phản hồi/xác nhận;
- chọn NCC đã xác nhận dùng trong hồ sơ.

Checkpoint không được:

- tự thay Đơn giá hiện hành;
- coi giá đề nghị hệ thống sinh là giá NCC đã xác nhận trước phản hồi/xác nhận;
- tạo báo giá trùng NCC khi đã có báo giá phù hợp của NCC đó chỉ vì dòng đến từ hồ sơ cũ khác;
- xóa lineage nguồn lịch sử khi người dùng gộp báo giá;
- đánh lại/đổi `STT` gốc khi gộp, tách, chuyển, group hoặc sort;
- tự chọn NCC thay người dùng.

### 10.15 Visual baseline authority — NCCQ Iteration 6

**Trạng thái:** `BASELINE ĐÃ DUYỆT / DESIGN AUTHORITY`.

Baseline trực quan chính thức của NCCQ là mockup Iteration 6, dùng cùng Valora shell/Fluent 2 với S11–S13:

- sidebar trái và top app bar thống nhất với các màn hình đã duyệt;
- header gọn, không dùng dashboard-card-heavy layout;
- step indicator compact cho chu trình `Tạo báo giá nháp → Gửi báo giá cho NCC → Chọn NCC đã xác nhận giá`;
- bảng chiếm phần lớn viewport;
- drawer `Lineage & tổng hợp` mở bên phải theo dòng đang chọn và không thay thế bảng chính;
- drawer hiển thị lineage hồ sơ cũ/báo giá cũ/NCC/báo giá hiện tại, giá sơ bộ, giá lịch sử, chênh lệch, trạng thái dòng và file ký/đóng dấu;
- các giá trị/số hiệu trong mockup là dữ liệu giả lập phục vụ minh họa, không phải dữ liệu khách hàng/NCC/hồ sơ thật.

![NCCQ — Baseline Authority v2.3](./assets/VALORA_NCCQ_BASELINE_v2.3.jpg)

Các iteration NCCQ trước Iteration 6 trong phụ lục/lịch sử thiết kế **không còn là authority**. Khi có mâu thuẫn visual, Iteration 6 + business rule §10 là nguồn quyết định.

## 11. Quản lý mẫu báo giá nhà cung cấp — Word-only; TM01 và TM03 baseline authority đã duyệt

### 11.1 Mục tiêu

Mỗi NCC có thể có bố cục báo giá khác nhau. Hệ thống lưu **template Word `.docx` + mapping + version** để khi tạo báo giá trong hồ sơ, VALORA có thể tự fill dữ liệu vào đúng mẫu của từng NCC.

Module nằm ở:

```text
Cấu hình → Mẫu báo giá nhà cung cấp
```

Từ checkpoint `Tạo & quản lý báo giá nhà cung cấp` có thể có shortcut `Chọn mẫu NCC`, `Tạo mẫu mới`, `Quản lý mẫu báo giá`.

### 11.2 Screen inventory module template

#### TM01 — Danh sách mẫu báo giá nhà cung cấp — baseline authority đã duyệt

Mục tiêu: quản lý toàn bộ template theo NCC.

**Visual baseline — Iteration 1:**

- dùng cùng Valora shell + Fluent 2 với NCCQ/S11–S13;
- breadcrumb `Cấu hình → Mẫu báo giá nhà cung cấp → Danh sách mẫu`;
- header `Danh sách mẫu báo giá nhà cung cấp`;
- primary CTA `Tạo mẫu mới` ở góc phải header;
- toolbar gồm filter theo NCC/trạng thái, search tên/mã mẫu, `Bộ lọc`, `Đặt lại`;
- summary compact `Tổng số mẫu / Đang sử dụng / Bản nháp / Ngừng sử dụng` đặt trên bảng;
- bảng là bề mặt làm việc chính, không dùng card-heavy dashboard;
- panel phải `Hướng dẫn / Thao tác nhanh / Gợi ý` là vùng hỗ trợ và không được lấn át bảng chính.

Bảng baseline:

```text
STT
| Mã mẫu
| Tên mẫu
| Nhà cung cấp
| Định dạng
| Phiên bản
| Cập nhật gần nhất
| Trạng thái
| Thao tác
```

Quy tắc hiển thị:

- định dạng template luôn là `DOCX`, hiển thị icon Word + định dạng trực tiếp;
- version hiển thị compact như `v1.0`, `v2.1`;
- trạng thái dùng badge semantic `Đang sử dụng`, `Bản nháp`, `Ngừng sử dụng`;
- mỗi dòng có `Xem chi tiết` + overflow menu cho thao tác phụ;
- có pagination và lựa chọn số dòng/trang;
- `Thao tác nhanh` có thể deep-link `Tạo mẫu mới`, `Upload & Mapping`, `Preview / Test fill`, `Lịch sử phiên bản`.

Guardrail TM01:

- không silent overwrite version/template cũ;
- không coi template là `Đang sử dụng` nếu chưa đạt điều kiện readiness;
- không cho upload/khởi tạo template báo giá NCC bằng XLSX/PDF;
- TM01 chỉ quản lý danh sách/metadata; mapping chi tiết thuộc TM03, test fill thuộc TM04, lịch sử phiên bản chi tiết thuộc TM05.

Visual authority companion: [`VALORA_TM01_BASELINE_v2.3.md`](./assets/VALORA_TM01_BASELINE_v2.3.md).

#### TM02 — Tạo / chỉnh sửa thông tin mẫu

Metadata tối thiểu:

- Nhà cung cấp;
- Mã NCC;
- Tên mẫu báo giá;
- Loại file: **Word `.docx` duy nhất**;
- Mô tả;
- Ngày hiệu lực;
- trạng thái;
- tùy chọn `Đặt làm mẫu mặc định của NCC`.

Khu vực file hiển thị file mẫu gốc, tên file, dung lượng, định dạng DOCX, ngày upload.

CTA: `Tiếp tục sang Mapping`, `Lưu nháp`, `Hủy`.

#### TM03 — Upload & Mapping template — baseline authority đã duyệt

Đây là màn hình làm việc chính của module template.

**Visual baseline — Iteration 1 Word-only:**

- cùng Valora shell + Fluent 2 với TM01/NCCQ;
- header `Upload & Mapping template` với secondary actions `Xem hướng dẫn`, `Lưu nháp` và primary CTA `Tiếp theo: Preview / Test fill`;
- step rail compact ở vùng trái: `Upload file → Mapping bảng danh mục → Mapping thông tin chung → Kiểm tra mapping`;
- chỉ nhận file Word `.docx`; file hiện hành hiển thị icon Word, tên file, dung lượng và `Thay đổi file`;
- vùng trái hiển thị metadata file và các thiết lập mapping cơ bản;
- vùng giữa là bảng mapping field của VALORA ↔ vị trí trong template Word;
- vùng phải là **preview trực tiếp tài liệu Word**, highlight các vùng dữ liệu sẽ được điền;
- footer hiển thị tiến độ mapping, validation status và CTA đi tiếp.

Bảng mapping baseline có thể gồm:

```text
Trường dữ liệu VALORA
| Kiểu dữ liệu
| Vị trí trong template Word
| Nội dung mẫu / gợi ý
| Trạng thái
```

Mapping Word sử dụng các đối tượng nghiệp vụ:

```text
Trang / vùng văn bản
→ Placeholder / đoạn text
→ Bảng
→ Dòng mẫu lặp
→ Ô / cột trong bảng
```

Không sử dụng các khái niệm Excel như `Sheet`, `Cell`, `Range`, `A8:J100`, `Cột A/B/C` theo nghĩa tọa độ spreadsheet.

Bản mockup TM03 dùng Excel trước khi rule Word-only được khóa **bị superseded** và không được dùng làm authority.

![TM03 — Baseline Authority Word-only v2.3](./assets/VALORA_TM03_BASELINE_v2.3.jpg)

#### TM04 — Preview / Test fill dữ liệu

Cho phép test bằng:

- `Dữ liệu mẫu mặc định`;
- hoặc một hồ sơ phù hợp được người dùng chọn để kiểm thử.

Hiển thị preview file Word đã fill + panel kết quả kiểm tra.

#### TM05 — Lịch sử phiên bản template

Quản lý version, hiệu lực và template mặc định; cho phép xem/nhân bản/đặt mặc định hoặc khôi phục theo lifecycle được triển khai sau.

### 11.3 Luồng chuẩn

```text
TM01 Danh sách mẫu
→ Tạo mẫu mới
→ TM02 Nhập metadata + Upload Word (.docx)
→ TM03 Mapping Word
→ Chạy kiểm tra
→ TM04 Preview / Test fill
→ Lưu template
→ Sẵn sàng sử dụng
```

Luồng khi NCC đổi mẫu:

```text
Mẫu hiện hành
→ Tạo phiên bản mới
→ Upload file Word mới hoặc chỉnh mapping
→ Preview / Test fill
→ Lưu version mới
→ Đặt làm mặc định nếu người dùng chọn
```

Không silent overwrite version đang được dùng trong hồ sơ cũ.

### 11.4 Danh sách field mapping

Cột mapping TM03 chia field theo nhóm để người dùng dễ tìm.

**A. Thông tin báo giá**

- Số báo giá;
- Ngày báo giá;
- Hiệu lực báo giá;
- Người nhận báo giá;
- Tên khách hàng / đơn vị nhận;
- Địa chỉ;
- Liên hệ.

**B. Thông tin nhà cung cấp**

- Tên NCC;
- Địa chỉ NCC;
- Mã số thuế;
- Điện thoại;
- Email;
- Người đại diện.

**C. Thông tin hồ sơ**

- Mã hồ sơ;
- Tên hồ sơ;
- Mục đích thẩm định;
- Tài sản thẩm định khi template cần.

**D. Bảng danh mục lặp**

- STT;
- Tên thiết bị;
- Mô tả / thông số;
- ĐVT;
- Số lượng;
- Đơn giá;
- Thành tiền;
- Ghi chú dòng.

**E. Tổng hợp**

- Tổng cộng;
- Thuế VAT nếu template có;
- Tổng thanh toán;
- Bằng chữ;
- Ghi chú chung.

Field cụ thể có thể mở rộng theo template thực tế nhưng không được hard-code một layout NCC duy nhất.

### 11.5 Preview file Word trong TM03

- Preview theo trang Word và table/paragraph/placeholder có thể map.
- Người dùng click vào vùng/ô trong preview để liên kết field hoặc xem mapping hiện tại.
- Vùng đã map có affordance/highlight rõ và cho phép xem field đang liên kết.
- Nếu file có nhiều bảng/trang, cho phép chọn đúng bảng/vùng trước khi mapping.
- Preview không giả lập spreadsheet grid khi file nguồn là Word.

### 11.6 Panel / cấu hình Mapping

Khi chọn một vùng Word, UI hiển thị tối thiểu:

- field đang map;
- loại field: text, số, ngày, bảng lặp, derived/formula;
- vị trí theo `trang / paragraph / table / row / cell` hoặc identifier tương đương do hệ thống quản lý;
- format tiền;
- số thập phân;
- format ngày;
- wrap text / xuống dòng nếu phù hợp;
- sample value;
- required/optional.

Không phơi bày thuật ngữ kỹ thuật không cần thiết cho người dùng cuối nếu có thể biểu diễn bằng ngôn ngữ nghiệp vụ.

### 11.7 Mapping bảng danh mục lặp — first-class feature

Vì báo giá có số dòng thiết bị thay đổi theo hồ sơ, mapping vùng lặp là requirement cốt lõi.

Với Word phải xác định được ít nhất:

- table chứa danh mục;
- row template dùng để nhân dòng;
- ô/cột STT;
- ô/cột tên hàng;
- ô/cột mô tả nếu có;
- ô/cột ĐVT;
- ô/cột số lượng;
- ô/cột đơn giá;
- ô/cột thành tiền;
- ô/cột ghi chú nếu có;
- vùng tổng cộng/footer để tránh bị ghi đè khi danh mục dài.

Hệ thống nhân dòng theo **row template của bảng Word**, không dùng cơ chế row/cell range của Excel.

### 11.8 Mapping nhanh và Mapping thủ công

Module hỗ trợ hai chế độ:

**Mapping nhanh**

- hệ thống nhận diện/gợi ý các vùng Word có thể map;
- người dùng xác nhận hoặc sửa;
- gợi ý không được tự trở thành cấu hình chính thức nếu chưa có thao tác người dùng.

**Mapping thủ công**

- người dùng chọn vùng/placeholder/ô bảng Word;
- chọn field;
- cấu hình format/rule;
- lưu mapping.

### 11.9 TM04 — Preview / Test fill

Mục tiêu là kiểm tra kết quả trước khi template được dùng thật.

Panel kết quả kiểm tra nên cho biết:

- số field đã map;
- số field bắt buộc chưa map;
- lỗi format;
- text quá dài / tràn ô;
- bảng lặp có nguy cơ đè footer;
- vùng tổng cộng chưa được map;
- dữ liệu tiền/ngày hiển thị không phù hợp;
- bảng/dòng lặp bị vỡ layout hoặc ngắt trang không phù hợp;
- công thức/tổng hợp không hợp lệ nếu hệ thống có thể kiểm tra.

CTA:

- `Quay lại chỉnh mapping`;
- `Lưu template`;
- `Lưu và đặt sẵn sàng sử dụng`.

### 11.10 Trạng thái template

Đề xuất lifecycle:

```text
Nháp
→ Đã upload file
→ Đang mapping
→ Đã mapping
→ Preview lỗi
→ Sẵn sàng sử dụng
→ Ngưng sử dụng
```

Tên trạng thái có thể tinh chỉnh i18n nhưng semantic phải rõ.

### 11.11 Điều kiện Sẵn sàng sử dụng

Tối thiểu:

- có metadata bắt buộc;
- có file Word `.docx` hợp lệ;
- các field bắt buộc đã mapping;
- vùng danh mục lặp đã cấu hình nếu template có danh mục;
- Preview/Test fill không còn lỗi blocking.

Template chưa đạt điều kiện vẫn có thể `Lưu nháp` nhưng không được coi là template sẵn sàng dùng để tạo output chính thức.

### 11.12 Versioning / lineage

- Không ghi đè file template gốc.
- Mỗi lần NCC đổi mẫu tạo version mới.
- Mapping thuộc version cụ thể.
- Hồ sơ/báo giá đã tạo phải truy vết được template version đã dùng.
- Có thể đặt một version làm mẫu mặc định của NCC.
- Việc đổi mẫu mặc định không làm thay đổi các file báo giá đã tạo trước đó.

### 11.13 Guardrail module template

Module được phép:

- upload template Word `.docx`;
- mapping field/vùng lặp;
- test fill;
- lưu nhiều version;
- đặt template mặc định;
- dùng template để sinh báo giá.

Module không được:

- nhận XLSX/PDF làm template báo giá NCC;
- silent overwrite template/version đã dùng;
- tự xác nhận mapping gợi ý thành mapping chính thức mà không có thao tác người dùng;
- làm mất file template gốc;
- hard-code toàn bộ hệ thống theo một mẫu NCC duy nhất;
- hiển thị hoặc lưu mapping Word dưới semantics sheet/cell/range của Excel.

### 11.14 Trạng thái thiết kế

- IA/flow TM01–TM05 và nguyên tắc mapping/versioning đã được đưa vào v2.3.
- **TM01 — Danh sách mẫu báo giá NCC — Iteration 1 là baseline authority đã duyệt.**
- **TM03 — Upload & Mapping template — Iteration 1 Word-only là baseline authority đã duyệt.**
- Bản TM03 Excel trước đó là iteration lịch sử và không còn authority.
- Mockup trực quan tiếp theo ưu tiên `TM04 — Preview / Test fill dữ liệu`.
- TM04 chỉ được nâng thành baseline khi người dùng duyệt rõ.

## 12. Validation phân tán — không có bước Kiểm tra riêng

Không có màn hình `Kiểm tra hồ sơ` riêng nhưng validation vẫn bắt buộc.

- `Blocking`: phải xử lý trước dependency liên quan.
- `Warning`: vẫn cho tiếp tục nhưng nêu rõ rủi ro/cần kiểm tra.
- `Info`: chỉ cung cấp trạng thái.

S10 chỉ tổng hợp readiness. S12/S13, Nguồn giá & Chứng cứ, Báo giá NCC và các màn hình sau hiển thị issue ngay tại nơi phát sinh và có `Đi tới` đúng chỗ sửa.

Ví dụ blocking trước `Hoàn tất hồ sơ` có thể gồm:

- tài sản trong phạm vi kết quả chưa có Đơn giá hiện hành;
- dữ liệu bắt buộc để sinh Báo cáo/Chứng thư còn thiếu;
- thay đổi chưa được lưu/commit;
- thiếu đầu ra báo giá/NCC đã xác nhận nếu rule hoàn tất hồ sơ sau này quy định đây là dependency bắt buộc.

Rule blocking chi tiết của S17 sẽ được khóa khi thiết kế S17; không tự suy diễn từ warning giá NCC.

## 13. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price hoặc auto-apply.
- File Excel nguồn và raw observation phải truy lại được.
- Không ghi đè dữ liệu gốc khách hàng bằng dữ liệu chuẩn hóa.
- Staging và dữ liệu chính thức phải phân biệt.
- Giá lịch sử Kho tri thức và giá hồ sơ cũ chỉ là căn cứ/tham khảo; không tự trở thành Đơn giá hiện hành.
- Giá hiện hành phải do người dùng ấn định/sửa và có lineage.
- Người dùng được phép sửa đơn giá trong quá trình xử lý tại context được phép.
- Mỗi thay đổi giá giữ lịch sử giá trước, actor và thời điểm; không silent overwrite audit trail.
- Không buộc người dùng xác nhận lại một mức giá tại checkpoint riêng.
- Nguồn Internet mất truy cập vẫn giữ URL/snapshot lịch sử và đánh dấu cần kiểm tra.
- Hồ sơ cũ/Giá lịch sử truy vết về hồ sơ/tài liệu nguồn cụ thể.
- Giá đề nghị hệ thống sinh cho báo giá NCC phải phân biệt rõ với `Đơn giá NCC đã xác nhận`.
- Báo giá NCC phải dedupe/hợp nhất theo NCC phù hợp; không tạo thêm báo giá trùng NCC chỉ vì các dòng đến từ hồ sơ cũ khác nhau.
- `STT` tài sản là immutable lineage/order từ danh mục gốc; sort/group/gộp/tách/chuyển báo giá không được renumber.
- File báo giá gửi/nhận, template và version phải có lineage phù hợp.
- **Template báo giá NCC chỉ dùng Word `.docx`; XLSX/PDF không phải template báo giá NCC.**
- Template báo giá gốc và mapping/version đã dùng không được silent overwrite.
- Vietnamese-first; không hiển thị HTTP/SQL/stack trace/row_version cho người dùng cuối.
- Mỗi màn hình/context có một primary CTA nổi bật.
- Hành động rủi ro cao phải confirm rõ thay đổi và khả năng hoàn tác.
- S09–S13, Nguồn giá & Chứng cứ, Báo giá NCC và module Template dùng cùng Valora shell theo Fluent 2, desktop-first.
- Hoàn tất, phát hành và các quyết định chính thức đều human-confirmed và có lineage.
- Quyền sửa giá sau khi hồ sơ đã khóa/phát hành phải tuân theo lifecycle/version guardrail của bước phát hành.
- Không đưa dữ liệu nhận diện khách hàng/NCC thật hoặc file hồ sơ thật vào public repository.

## 14. Screen inventory v2.3

| ID | Màn hình | Trạng thái / quyết định v2.3 |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát tích hợp + tạo/quản lý file kết quả + CTA chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 — người dùng phân tích, ấn định và có thể chỉnh giá |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | Không có màn hình riêng; tích hợp S02 |
| S09 | Chuyển sang thẩm định chính thức | P0 — baseline đã duyệt; kế thừa giá từ Pre-case làm giá khởi tạo |
| S10 | Tổng quan hồ sơ | P0 — dashboard 8 checkpoint |
| S11 | Xác nhận & điều chỉnh danh mục triển khai | P0 — giữ/thêm/loại + lineage; chốt phạm vi |
| S12 | Workbench tài sản | P0 — grid desktop-first + raw vs normalized + Đơn giá hiện hành |
| S13 | Asset Context Drawer | **P0 — baseline đã duyệt; drawer trong S12** |
| NGC | Nguồn giá & Chứng cứ | **P0 — baseline đã duyệt** |
| NCCQ | Tạo & quản lý báo giá nhà cung cấp | **P0 — baseline authority đã duyệt; Fluent 2 table-first + drawer Lineage & tổng hợp; Iteration 6** |
| TM01 | Danh sách mẫu báo giá NCC | **P0 — baseline authority đã duyệt; Fluent 2 list/table-first; Word-only; Iteration 1** |
| TM02 | Tạo/chỉnh thông tin mẫu báo giá | **P0 — IA/field structure đã thiết kế; Word `.docx` only** |
| TM03 | Upload & Mapping template | **P0 — baseline authority đã duyệt; Word-only mapping + Word preview; Iteration 1** |
| TM04 | Preview / Test fill dữ liệu | **P0 — IA/UX đã thiết kế; mockup chưa duyệt baseline** |
| TM05 | Lịch sử phiên bản template | **P0 — capability/versioning đã thiết kế** |
| S14 | So sánh & Xác nhận giá | **Không dùng trong giai đoạn hiện tại** |
| S15 | Kiểm tra hồ sơ | **Không dùng; validation phân tán** |
| S16 | KSCL Checklist | **Không dùng trong workflow single-user v2.3** |
| S17 | Hoàn tất hồ sơ | P0 — readiness summary + confirmations + blocking issues tổng hợp |
| S18 | Báo cáo & Chứng thư | P1 — templates, preview, draft versions |
| S19 | Phát hành | P1 — confirm, lock version, export |
| S20 | Lịch sử & Lưu trữ | P1 — timeline, files, sources, prices, provenance, knowledge promotion |

> `NGC`, `NCCQ`, `TM01–TM05` là ký hiệu tài liệu, không nhất thiết là route/ID implementation.

## 15. Mockup baseline v2.3

Baseline đã duyệt:

- S09 — Chuyển sang thẩm định chính thức, Fluent 2.
- S10 — Tổng quan hồ sơ.
- S11 — Xác nhận & điều chỉnh danh mục triển khai.
- S12 — Workbench tài sản, data grid lớn với raw vs normalized.
- S13 — Asset Context Drawer mở từ S12; drawer phải + S12 giữ context.
- Nguồn giá & Chứng cứ — full-screen theo asset context, ba nhóm căn cứ ngang hàng và panel Hồ sơ cũ/Giá lịch sử.
- **NCCQ — Tạo & quản lý báo giá nhà cung cấp — Iteration 6: baseline authority đã duyệt.**
- **TM01 — Danh sách mẫu báo giá NCC — Iteration 1: baseline authority đã duyệt.**
- **TM03 — Upload & Mapping template — Iteration 1 Word-only: baseline authority đã duyệt.**

### 15.1 NCCQ — authority visual đã chốt

Mockup NCCQ Iteration 6 là authority trực quan cho checkpoint báo giá nhà cung cấp:

- **table-first**, bảng gần Excel nghiệp vụ;
- 03 cột NCC hiển thị số tiền trực tiếp và semantic trạng thái compact;
- section/header row giữ cấu trúc danh mục;
- dedupe/tổng hợp cùng NCC;
- `STT` bất biến theo danh mục gốc;
- drawer phải `Lineage & tổng hợp` cho context dòng, warning, provenance và file evidence;
- primary CTA `Chọn nhà cung cấp đã xác nhận giá`;
- cùng Fluent 2 / Valora shell với các baseline S11–S13;
- không dùng card giải thích dài phía dưới làm giảm diện tích bảng.

![NCCQ — Baseline Authority v2.3](./assets/VALORA_NCCQ_BASELINE_v2.3.jpg)

Các mockup NCCQ iteration 1–5 và các iteration trung gian trước đó được giữ **chỉ để truy vết lịch sử thiết kế**. Chúng không được dùng làm authority nếu mâu thuẫn với Iteration 6 hoặc business rule §10.

### 15.2 TM01 — authority visual đã chốt

Mockup TM01 Iteration 1 là authority trực quan cho màn hình danh sách mẫu báo giá NCC:

- Valora shell + Fluent 2, desktop-first;
- header gọn với primary CTA `Tạo mẫu mới`;
- filter/search phía trên;
- summary compact 4 trạng thái;
- bảng danh sách template là bề mặt chính;
- trạng thái/version/định dạng DOCX hiển thị trực tiếp trong bảng;
- `Xem chi tiết` + overflow menu ở mỗi dòng;
- panel phải `Hướng dẫn / Thao tác nhanh / Gợi ý` là vùng hỗ trợ;
- pagination ở cuối bảng;
- TM03/TM04/TM05 chỉ được deep-link từ TM01, không nhồi toàn bộ mapping/test/version detail vào bảng chính.

Visual authority companion: [`VALORA_TM01_BASELINE_v2.3.md`](./assets/VALORA_TM01_BASELINE_v2.3.md).

Khi có mâu thuẫn visual giữa các iteration TM01 khác và baseline này, **TM01 Iteration 1 + §11.2 là nguồn quyết định**.

### 15.3 TM03 — authority visual đã chốt

Mockup TM03 Iteration 1 Word-only là authority trực quan cho Upload & Mapping template:

- chỉ nhận template `.docx`;
- left rail thể hiện tiến trình Upload/Mapping/Kiểm tra;
- vùng giữa dùng bảng mapping field VALORA ↔ vị trí trong Word;
- vùng phải preview trực tiếp tài liệu Word và highlight vùng dữ liệu;
- mapping bảng danh mục dựa trên `table → row template → cell/column`;
- có `Tự động dò tìm` nhưng mọi mapping chính thức vẫn human-confirmed;
- validation/progress nằm ngay trong màn hình;
- primary CTA cuối bước là `Tiếp theo: Preview / Test fill`;
- các semantics Excel `sheet/cell/range/A8:J100` bị loại khỏi TM03.

![TM03 — Baseline Authority Word-only v2.3](./assets/VALORA_TM03_BASELINE_v2.3.jpg)

Bản mockup TM03 Excel trước rule Word-only chỉ còn giá trị lịch sử và **không được dùng làm authority**. Khi có mâu thuẫn, **TM03 Iteration 1 Word-only + §11.2/§11.5–§11.8 là nguồn quyết định**.

Đối với phần còn lại của `Quản lý mẫu báo giá nhà cung cấp`:

- TM01 và TM03 đã chốt baseline authority;
- TM04 là mockup tiếp theo cần thiết kế/duyệt;
- TM02/TM05 giữ IA/capability đã mô tả trong §11 cho tới khi cần mockup chi tiết.

Mockup S14 đã thử nghiệm trước quyết định nghiệp vụ mới **không phải baseline**.

## 16. Trạng thái triển khai và nhiệm vụ UI/UX tiếp theo

Đây là **thiết kế mục tiêu**, không được suy diễn rằng toàn bộ nội dung v2.3 đã được implement trong product code.

Các guardrail kỹ thuật hiện có trong repository vẫn có hiệu lực: tenant isolation fail-closed; staging không phải official; Apply human-confirmed; restricted Workbench fields đi qua human-controlled mutation path; AI advisory-only; source evidence có provenance.

### Nhiệm vụ thiết kế tiếp theo

1. **NCCQ, TM01 và TM03 đã chốt baseline authority. Tiếp tục `TM04 — Preview / Test fill dữ liệu` theo template Word.**
2. TM04 phải kiểm thử layout Word thực tế: placeholder, text dài, bảng lặp, tổng cộng/footer, ngắt trang và format tiền/ngày; chỉ nâng thành baseline khi người dùng duyệt rõ.
3. Sau khi TM04 đủ rõ, thiết kế **S17 — Hoàn tất hồ sơ** với readiness summary, bao gồm trạng thái báo giá/NCC đã xác nhận nếu đây là dependency bắt buộc.
4. Tiếp theo là S18 — `Báo cáo & Chứng thư`, S19 — `Phát hành`, S20 — `Lịch sử & Lưu trữ`.

Không nhảy sang S17 trước khi TM04 đủ rõ để xác định chính xác dependency template Word → tạo file → nhận/chọn báo giá ở bước hoàn tất hồ sơ.
