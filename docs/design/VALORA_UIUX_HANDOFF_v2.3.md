# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX đã duyệt  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Valora shell bám sát Fluent 2, desktop-first

> v2.3 kế thừa baseline v2.2, bổ sung/chốt S13 — `Asset Context Drawer / Ngữ cảnh tài sản`, loại S14 khỏi workflow hiện tại và khóa lại cơ chế giá: **đơn giá do người dùng ấn định được kế thừa từ Pre-case nhưng vẫn có thể được người dùng sửa trong suốt quá trình xử lý hồ sơ tại các context được phép chỉnh sửa. Không có checkpoint xác nhận giá lần thứ hai.**

## 0. Quyết định v2.3 đã duyệt

- Toàn bộ quyết định S09–S12 của v2.2 tiếp tục giữ nguyên, ngoại trừ nội dung yêu cầu phải có một màn hình riêng để xác nhận lại `Giá thẩm định chính thức`.
- S13 — `Asset Context Drawer / Ngữ cảnh tài sản` đã được duyệt làm baseline tiếp theo.
- S13 luôn mở trong context của S12; không tạo menu riêng và không biến thành full-screen độc lập.
- Khi mở S13, S12 vẫn được giữ ở nền với nguyên filter, sort, search, pagination, selection và vị trí scroll hiện tại.
- `Dữ liệu gốc (Excel)` luôn truy vết được và không bị ghi đè bởi dữ liệu chuẩn hóa.
- Kho tri thức/AI chỉ gợi ý; không auto-accept candidate, không tự xác nhận identity, không tự ấn định hoặc tự sửa giá.
- **Không dùng S14 — So sánh & Xác nhận giá thẩm định chính thức trong workflow hiện tại.**
- **Đơn giá đã được người dùng ấn định ở Pre-case là giá khởi tạo/kế thừa khi chuyển sang hồ sơ chính thức, nhưng không bị khóa cứng.**
- **Người dùng có thể sửa đơn giá trong suốt quá trình xử lý hồ sơ ở các context được phép chỉnh sửa giá. Mỗi lần sửa trở thành mức giá hiện hành mới và phải giữ lineage/audit.**
- Không yêu cầu người dùng xác nhận lại cùng một mức giá ở một checkpoint riêng chỉ vì chuyển từ Pre-case sang hồ sơ chính thức.
- Nếu tài sản mới được bổ sung hoặc identity/thông số quan trọng thay đổi, hệ thống phải cảnh báo về độ phù hợp của giá hiện hành; người dùng có thể giữ, sửa hoặc phân tích lại giá bằng quyết định explicit.
- Validation chạy tại field/dòng/context phát sinh theo `Blocking`, `Warning`, `Info`; không có màn hình Kiểm tra riêng.
- Các thay đổi identity quan trọng hoặc thao tác có thể làm mất dữ liệu đã xác nhận phải có confirm rõ ảnh hưởng.
- S13 duy trì lineage: `raw source → normalized asset → candidate KB/source/price → human decision`.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị.
- Chỉ dùng phương pháp so sánh.
- Công việc chính: Kho tri thức + nguồn giá Internet + Thuyết minh đơn giá.
- Không thiết kế khảo sát hiện trạng.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word/PDF là input/output; Workbench + database là nguồn dữ liệu làm việc chính thức.
- Không thiết kế workflow giao việc/chờ xác nhận giữa nhiều tài khoản ở giai đoạn này.
- Giá dùng trong kết quả thẩm định luôn là mức giá do người dùng nghiệp vụ ấn định hoặc sửa; hệ thống không tự sinh quyết định giá.

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
→ Nguồn giá & chứng cứ
→ S17 Hoàn tất hồ sơ
→ S18 Báo cáo & Chứng thư
→ S19 Phát hành
→ S20 Lưu trữ & hình thành tri thức
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
- Khi chuyển thành hồ sơ chính thức, mức giá này được kế thừa làm **giá khởi tạo của kết quả thẩm định**, nhưng người dùng vẫn có thể sửa tiếp trong quá trình xử lý hồ sơ.

### 3.2 Quy tắc giá hiện hành

Một tài sản có **một mức giá hiện hành** dùng cho kết quả thẩm định tại từng thời điểm.

- Giá hiện hành ban đầu có thể kế thừa từ Pre-case.
- Người dùng có thể sửa giá tại context phù hợp trong S12/S13/Nguồn giá & Chứng cứ hoặc bề mặt chỉnh giá được thiết kế sau này.
- Sau khi người dùng lưu/commit thay đổi, mức mới thay thế mức trước thành `Giá hiện hành`; mức cũ vẫn giữ trong lịch sử/lineage, không bị xóa khỏi audit trail.
- Không cần một bước `Xác nhận giá chính thức` riêng sau mỗi lần sửa.
- AI, Kho tri thức, rule engine hoặc nguồn Internet không được tự ghi đè giá hiện hành.
- Khi hồ sơ ở trạng thái đã khóa/phát hành, khả năng sửa giá phải tuân theo cơ chế khóa/version/change workflow của giai đoạn đó; v2.3 không thiết kế bypass cho trạng thái đã khóa.

## 4. S09 — Chuyển sang thẩm định chính thức

### 4.1 Nguyên tắc

- Pre-case phải có file kết quả sơ bộ.
- Giá hiện hành trong Pre-case được copy vào snapshot hồ sơ chính thức cùng provenance/lineage và trở thành giá khởi tạo của tài sản.
- Không tạo bước xác nhận lại giá chỉ để đổi tên từ `giá sơ bộ` sang `giá chính thức`.
- Sau khi tạo hồ sơ, người dùng vẫn có thể chỉnh giá trong quá trình làm việc.
- Trường hồ sơ chưa điền đủ vẫn có thể tạo hồ sơ nếu chưa tới dependency bắt buộc; hiển thị `Chưa bổ sung`.
- Chỉ validate format/logic khi người dùng có nhập; field trống chỉ trở thành blocking khi bước sau thực sự cần dữ liệu đó.

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

Workflow hiện tại gồm **7 checkpoint**:

1. `Thông tin hồ sơ`;
2. `Danh mục triển khai`;
3. `Hoàn thiện tài sản`;
4. `Nguồn giá & chứng cứ`;
5. `Hoàn tất hồ sơ`;
6. `Báo cáo & Chứng thư`;
7. `Phát hành`.

Không có checkpoint riêng `Thông tin thực hiện`, `Giá thẩm định chính thức`, `Kiểm tra hồ sơ`, `KSCL`.

### 5.3 Readiness / cột phải

Có thể tổng hợp:

- mức hoàn thiện thông tin hồ sơ;
- số tài sản triển khai;
- tiến độ nhận diện;
- số nguồn giá/Thuyết minh;
- số dòng đã có giá hiện hành;
- số dòng chưa có giá;
- số dòng có warning giá/căn cứ cần rà soát;
- readiness;
- thông tin cần bổ sung;
- nguồn Pre-case/file/snapshot/lineage;
- người thực hiện lấy từ Cấu hình.

Ngay sau S09, card `Việc cần làm tiếp theo` dẫn vào S11.

S10 chỉ tổng hợp validation; mọi vấn đề cụ thể có CTA `Đi tới` đúng nơi sửa.

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

S12 là bảng làm việc chính của danh mục đã được chốt tại S11. Người dùng hoàn thiện nhận diện/thông số, rà soát nguồn/candidate và có thể tiếp tục điều chỉnh giá của tài sản trong quá trình làm việc.

### 7.2 Visual baseline đã duyệt

S12 dùng Fluent 2, desktop-first, ưu tiên data grid lớn. Baseline hiện hành thể hiện:

- shell VALORA thống nhất với S09–S11;
- header `S12 Workbench tài sản`;
- card hồ sơ + KPI readiness;
- notice rõ rằng dữ liệu gốc Excel luôn được giữ nguyên;
- toolbar filter/search/tùy chỉnh cột;
- grid lớn với nhóm cột `Thông tin từ Excel (Dữ liệu gốc)` và `Thông tin chuẩn hóa (Bạn đang chỉnh sửa)` đặt cạnh nhau;
- cột `Thông số kỹ thuật chính`, `Trạng thái`, `Kho tri thức`, `Nguồn giá`, `Đơn giá hiện hành`, `Thao tác`;
- thao tác mỗi dòng `Mở ngữ cảnh` để mở S13.

Trong UI có thể dùng nhãn `Đơn giá TĐ` hoặc `Đơn giá hiện hành` tùy không gian, nhưng không tạo cột giá thứ hai chỉ để xác nhận lại cùng một mức giá.

### 7.3 Trạng thái dòng

Có thể gồm:

- `Đủ thông tin`;
- `Cần bổ sung`;
- `Mới bổ sung`;
- `Cần phân tích giá`.

Trạng thái Kho tri thức tách riêng như `Có / Đã tìm thấy gợi ý`, `Cần xác nhận`, `Chưa có`.

### 7.4 Quy tắc sửa giá trong S12

- Giá kế thừa từ Pre-case là giá khởi tạo, không phải giá bị khóa.
- Người dùng có thể chỉnh giá trực tiếp tại bề mặt được phép hoặc mở đúng context Nguồn giá/S13 để sửa.
- Mỗi thay đổi giá phải là thao tác explicit của người dùng và có lịch sử thay đổi.
- Dòng mới không tự sao chép giá từ tài sản khác.
- Nếu thay đổi model/thông số identity quan trọng, hệ thống cảnh báo rằng giá/căn cứ hiện hành cần rà soát; không tự xóa hoặc tự thay giá của người dùng.
- Người dùng quyết định `Giữ giá hiện tại`, `Sửa giá` hoặc tiếp tục phân tích nguồn/căn cứ.
- AI/Kho tri thức không tự thay giá.

### 7.5 Guardrail S12

- Raw source không bị ghi đè.
- Dòng không đổi có thể tái sử dụng candidate Kho tri thức, nguồn giá và giá từ Pre-case.
- Dòng mới hoặc thay đổi identity quan trọng phải được đánh dấu/cảnh báo phù hợp để người dùng rà soát.
- Primary CTA cuối bước: `Tiếp tục sang Nguồn giá & chứng cứ` khi readiness phù hợp.

## 8. S13 — Asset Context Drawer / Ngữ cảnh tài sản

### 8.1 Mục tiêu

S13 cho phép xử lý sâu một tài sản đang chọn trong S12 mà không rời Workbench và không mất context bảng hiện tại.

S13 là **drawer bên phải**, mở từ CTA `Mở ngữ cảnh` trên dòng tài sản trong S12.

### 8.2 Hành vi mở/đóng drawer

Khi mở S13:

- S12 vẫn nằm ở nền và tiếp tục cho người dùng nhận biết dòng đang chọn.
- Giữ nguyên `search`, `filter`, `sort`, pagination, selection và vị trí scroll.
- Dòng đang mở context được highlight rõ.
- Drawer có nút `Đóng ngữ cảnh (Esc)` và nút đóng ở header.
- Sau khi lưu/đóng, người dùng quay đúng vị trí S12 trước đó.

Không tạo route/menu độc lập cho S13 trong navigation chính.

### 8.3 Header tài sản

Header drawer hiển thị compact:

- tên thiết bị chuẩn hóa;
- hãng + model;
- mã tài sản;
- trạng thái hiện tại;
- badge nguồn như `Từ Excel`, `Mới bổ sung`, `Đang chuẩn hóa` khi phù hợp.

### 8.4 Cấu trúc drawer baseline

Khuyến nghị 4 tab trong cùng drawer:

1. `Tổng quan`;
2. `Thông số kỹ thuật`;
3. `Nguồn giá & Chứng cứ`;
4. `Lịch sử`.

Không dùng wizard đa bước.

### 8.5 Tab Tổng quan — Raw vs Normalized

Khối trung tâm của S13 là bảng/field pair đặt cạnh nhau:

```text
Dữ liệu gốc (Excel) | Dữ liệu chuẩn hóa (Đang chỉnh sửa)
```

Các field tối thiểu:

- Tên thiết bị;
- Hãng;
- Model;
- Xuất xứ;
- Năm sản xuất nếu có;
- Tình trạng nếu có;
- Vị trí nếu có;
- Thông số kỹ thuật chính.

Quy tắc:

- Cột raw là read-only.
- Cột normalized cho phép chỉnh theo đúng guardrail dữ liệu.
- Không âm thầm cập nhật raw source.
- Field thay đổi identity quan trọng phải cảnh báo nếu làm giảm độ phù hợp của candidate, nguồn giá hoặc mức giá hiện hành.

### 8.6 Validation inline

Validation hiển thị tại đúng field hoặc block phát sinh:

- `Blocking`: phải xử lý trước hành động có dependency.
- `Warning`: vẫn được tiếp tục nhưng phải nêu rõ ảnh hưởng.
- `Info`: trạng thái/thông tin không cản workflow.

Mọi validation phải trả lời được:

```text
Vấn đề gì → nằm ở đâu → ảnh hưởng gì → sửa thế nào
```

Nếu thay đổi `Tên thiết bị`, `Hãng`, `Model`, `Xuất xứ` hoặc thông số identity quan trọng làm lệch dữ liệu đã kế thừa, phải cảnh báo rằng giá/căn cứ hiện hành cần được rà soát; quyết định giữ hay sửa giá vẫn thuộc người dùng.

### 8.7 Kho tri thức / Asset Identity candidate

S13 hiển thị summary/candidate Kho tri thức gắn với đúng tài sản hiện tại.

Mỗi candidate cần thể hiện tối thiểu:

- tên/canonical identity;
- mức tương đồng;
- điểm giống;
- điểm khác;
- model/thông số liên quan;
- giá lịch sử và nguồn/ngày tham chiếu khi có.

Hành động mỗi candidate:

- `Dùng`;
- `Không dùng`;
- `Xem chi tiết`.

Không auto-accept. Chỉ thao tác human-confirmed mới trở thành quyết định chính thức/reusable feedback.

### 8.8 Trạng thái & chỉ số tài sản

Trong drawer có block summary như:

- `Trạng thái hiện tại`;
- `Mức độ hoàn thiện`;
- `Kho tri thức (Candidate)`;
- `Nguồn giá đã có`;
- `Đơn giá hiện hành`.

Trạng thái nghiệp vụ hỗ trợ:

- `Chưa có nguồn`;
- `Cần xác nhận`;
- `Đủ thông tin`;
- `Cần bổ sung`;
- `Cần phân tích giá`.

### 8.9 Nguồn giá & Chứng cứ trong S13

S13 chỉ hiển thị **summary**, không nhân bản toàn bộ màn hình Nguồn giá.

Hiển thị tối thiểu:

- số nguồn Internet hiện có;
- số Thuyết minh đơn giá;
- `Đơn giá hiện hành`;
- trạng thái nguồn: còn truy cập / cần kiểm tra / chỉ còn snapshot lịch sử;
- candidate/source liên quan tới đúng tài sản.

CTA:

- `Mở Nguồn giá` hoặc `Xem Nguồn giá & Chứng cứ`.

CTA phải chuyển đúng context của tài sản hiện tại.

Nếu S13 có field chỉnh giá thì phải thể hiện rõ đây là **giá hiện hành do người dùng sửa**, không phải giá do hệ thống đề xuất tự động.

### 8.10 Lưu thay đổi

Footer drawer baseline:

- secondary: `Hủy thay đổi`;
- primary: `Lưu thông tin`;
- tertiary/utility: `Đóng ngữ cảnh (Esc)`.

Quy tắc:

- Một primary CTA nổi bật.
- Nếu không có thay đổi thì `Lưu thông tin` disabled hoặc chuyển sang trạng thái không nổi bật.
- Nếu có unsaved changes và người dùng đóng drawer, cảnh báo `Lưu / Bỏ thay đổi / Tiếp tục chỉnh sửa`.
- Lưu thành công không reset filter/sort/scroll của S12.
- Nếu gói thay đổi bao gồm đơn giá, phải lưu kèm provenance/actor/time theo guardrail kỹ thuật; lịch sử giá trước đó vẫn truy vết được.

### 8.11 Loading / Empty / Error / Warning states

S13 có state cho:

- đang tải asset context;
- chưa có normalized data;
- chưa có candidate Kho tri thức;
- chưa có nguồn giá;
- nguồn Internet cũ/mất truy cập nhưng còn snapshot;
- tải candidate/source lỗi;
- stale data nếu hệ thống phát hiện;
- warning khi identity thay đổi làm candidate/nguồn/giá hiện hành cần rà soát.

Thông báo dùng tiếng Việt nghiệp vụ, không hiển thị HTTP/SQL/stack trace/row_version.

### 8.12 Audit / Lineage

```text
Raw source / Excel
→ Dữ liệu chuẩn hóa
→ Candidate Kho tri thức / nguồn giá
→ Giá do người dùng ấn định
→ Các lần người dùng chỉnh giá
→ Giá hiện hành
→ Báo cáo / Chứng thư
```

Không cần hiển thị thuật ngữ database/API trong UI; có thể thể hiện dưới dạng `Nguồn dữ liệu`, `Lịch sử thay đổi`, `Đã kế thừa từ`, `Người dùng đã điều chỉnh`.

### 8.13 Ranh giới S13 đã khóa

S13 **được phép**:

- hoàn thiện ngữ cảnh một tài sản;
- chỉnh normalized fields;
- xem raw source;
- xem và quyết định candidate Kho tri thức;
- xem summary nguồn giá/Thuyết minh/giá hiện hành;
- cho phép người dùng chỉnh giá nếu bề mặt S13 được dùng làm context chỉnh giá;
- deep-link sang đúng tài sản ở Nguồn giá & Chứng cứ.

S13 **không được**:

- trở thành màn hình xác nhận giá lần thứ hai;
- tự tính/chốt/sửa giá thay người dùng;
- auto-accept identity candidate;
- auto-apply nguồn giá;
- ghi đè raw source;
- nhân bản full panel Kho tri thức/Nguồn giá;
- biến thành wizard dài nhiều bước;
- tạo menu/navigation độc lập.

## 9. Nguồn giá & Chứng cứ

Đây vẫn là checkpoint nghiệp vụ sau S12/S13 để người dùng hoàn thiện, kiểm tra và truy vết căn cứ giá của tài sản.

Mục tiêu **không phải xác nhận giá lần thứ hai**, mà là:

- bổ sung/kiểm tra nguồn Internet;
- bổ sung hoặc rà soát Thuyết minh đơn giá;
- bảo đảm nguồn/chứng cứ gắn đúng tài sản;
- nhận biết nguồn cũ/mất truy cập nhưng còn snapshot;
- xử lý tài sản mới hoặc tài sản có identity thay đổi;
- cho phép người dùng **tiếp tục sửa đơn giá** khi kết quả phân tích/căn cứ thay đổi;
- bảo đảm giá hiện hành có provenance phù hợp trước Hoàn tất hồ sơ.

Khi người dùng sửa giá tại đây:

- mức mới trở thành `Đơn giá hiện hành` sau khi lưu/commit;
- mức cũ vẫn giữ lịch sử;
- không cần qua S14;
- mọi cập nhật giá vẫn human-controlled.

## 10. Validation phân tán — không có bước Kiểm tra riêng

Không có màn hình `Kiểm tra hồ sơ` riêng nhưng validation vẫn bắt buộc.

- `Blocking`: phải xử lý trước dependency liên quan.
- `Warning`: vẫn cho tiếp tục nhưng nêu rõ rủi ro/cần kiểm tra.
- `Info`: chỉ cung cấp trạng thái.

S10 chỉ tổng hợp readiness. S12/S13, Nguồn giá & Chứng cứ và các màn hình sau hiển thị issue ngay tại nơi phát sinh và có `Đi tới` đúng chỗ sửa khi cần.

Ví dụ blocking trước `Hoàn tất hồ sơ`:

- tài sản trong phạm vi kết quả chưa có đơn giá hiện hành;
- dữ liệu bắt buộc để sinh Báo cáo/Chứng thư còn thiếu;
- có thay đổi chưa được lưu/commit.

Identity thay đổi nhưng vẫn đang có giá cũ có thể là `Warning` hoặc `Blocking` tùy dependency/rule được thiết kế chi tiết sau; hệ thống không được tự quyết định thay giá thay người dùng.

## 11. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price hoặc auto-apply.
- File Excel nguồn và raw observation phải truy lại được.
- Không ghi đè dữ liệu gốc khách hàng bằng dữ liệu chuẩn hóa.
- Staging và dữ liệu chính thức phải phân biệt.
- Giá lịch sử Kho tri thức chỉ là tham khảo.
- Giá hiện hành phải do người dùng ấn định/sửa và có lineage.
- **Người dùng được phép sửa đơn giá trong suốt quá trình xử lý hồ sơ tại context được phép chỉnh sửa.**
- Mỗi thay đổi giá phải giữ lịch sử giá trước, actor và thời điểm; không silent overwrite audit trail.
- Không buộc người dùng xác nhận lại một mức giá tại checkpoint riêng.
- Nguồn Internet mất truy cập vẫn giữ lịch sử URL/snapshot và đánh dấu cần kiểm tra.
- Vietnamese-first, không hiển thị HTTP/SQL/stack trace/row_version cho người dùng.
- Mỗi màn hình/context có một primary CTA nổi bật.
- Hành động rủi ro cao phải confirm rõ thay đổi và khả năng hoàn tác.
- S09–S13 dùng cùng Valora shell theo Fluent 2, desktop-first cho grid/workbench.
- Hoàn tất, phát hành và các quyết định chính thức đều human-confirmed và có lineage.
- Quyền sửa giá sau khi hồ sơ đã khóa/phát hành không được suy diễn từ rule trên; phải tuân theo lifecycle/version guardrail của bước phát hành.

## 12. Screen inventory v2.3

| ID | Màn hình | Trạng thái / quyết định v2.3 |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát tích hợp + tạo/quản lý file kết quả + CTA chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 — người dùng phân tích, ấn định và có thể chỉnh giá |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | Không có màn hình riêng; tích hợp S02 |
| S09 | Chuyển sang thẩm định chính thức | P0 — mockup/field layout đã duyệt; kế thừa giá hiện hành từ Pre-case làm giá khởi tạo |
| S10 | Tổng quan hồ sơ | P0 — workflow dashboard 7 checkpoint |
| S11 | Xác nhận & điều chỉnh danh mục triển khai | P0 — giữ/thêm/loại + lineage; chốt phạm vi |
| S12 | Workbench tài sản | P0 — grid desktop-first + raw vs normalized + context entry point + giá hiện hành có thể sửa |
| S13 | Asset Context Drawer | **P0 — baseline đã duyệt trong v2.3; drawer trong S12, không phải màn hình độc lập** |
| S14 | So sánh & Xác nhận giá | **Không dùng trong giai đoạn hiện tại; không có checkpoint xác nhận giá lần thứ hai** |
| S15 | Kiểm tra hồ sơ | **Không dùng trong workflow single-user v2.3; validation phân tán** |
| S16 | KSCL Checklist | **Không dùng trong workflow single-user v2.3** |
| S17 | Hoàn tất hồ sơ | P0 — readiness summary + confirmations + blocking issues tổng hợp |
| S18 | Báo cáo & Chứng thư | P1 — templates, preview, draft versions |
| S19 | Phát hành | P1 — confirm, lock version, export |
| S20 | Lịch sử & Lưu trữ | P1 — timeline, files, sources, prices, provenance, knowledge promotion |

## 13. Mockup baseline v2.3

Baseline mockup đã được duyệt:

- S09 — Chuyển sang thẩm định chính thức, Fluent 2.
- S10 — Tổng quan hồ sơ, workflow rút gọn.
- S11 — Xác nhận & điều chỉnh danh mục triển khai, full-screen riêng.
- S12 — Workbench tài sản, data grid lớn với raw vs normalized.
- **S13 — Asset Context Drawer mở từ S12; drawer bên phải + S12 giữ nguyên ở nền.**

S13 baseline cụ thể:

- asset header compact;
- raw vs normalized trong drawer;
- trạng thái và mức hoàn thiện;
- candidate Kho tri thức;
- nguồn giá + `Đơn giá hiện hành` summary;
- tab `Tổng quan / Thông số kỹ thuật / Nguồn giá & Chứng cứ / Lịch sử`;
- `Hủy thay đổi / Lưu thông tin / Đóng ngữ cảnh`;
- không làm mất context S12.

Mockup S14 đã thử nghiệm trước quyết định nghiệp vụ mới **không phải baseline** và không được dùng làm authority cho giai đoạn hiện tại.

## 14. Trạng thái triển khai

Đây là **thiết kế mục tiêu đã duyệt**. Không được suy diễn rằng toàn bộ nội dung v2.3 đã được implement trong product code.

Các guardrail kỹ thuật hiện có trong repository vẫn tiếp tục có hiệu lực: tenant isolation fail-closed; staging không phải official; Apply human-confirmed; restricted Workbench fields đi qua human-controlled mutation path; AI advisory-only; source evidence phải có provenance.

Quyết định UI/UX rằng người dùng có thể sửa đơn giá trong suốt quá trình xử lý **không cấp quyền cho AI/system tự ấn định hoặc tự sửa giá**. Mọi thay đổi giá vẫn là quyết định của người dùng và phải đi qua mutation/audit guardrail kỹ thuật hiện hành.

## 15. Nhiệm vụ UI/UX tiếp theo sau v2.3

**Không thiết kế S14 trong giai đoạn hiện tại.**

Sau S13, ưu tiên thiết kế tiếp:

1. hoàn thiện trải nghiệm checkpoint `Nguồn giá & Chứng cứ`, bao gồm cách người dùng xem căn cứ và sửa `Đơn giá hiện hành`;
2. sau đó thiết kế **S17 — Hoàn tất hồ sơ** với readiness summary và blocking validation;
3. tiếp theo là S18 — `Báo cáo & Chứng thư`.

S17 phải kiểm tra readiness nhưng không biến thành màn hình `Kiểm tra hồ sơ` cũ. Mọi lỗi cụ thể vẫn phát sinh/được sửa tại đúng S09–S13 hoặc Nguồn giá & Chứng cứ, còn S17 chỉ tổng hợp và dẫn `Đi tới`.
