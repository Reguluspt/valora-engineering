# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX đã duyệt  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Valora shell bám sát Fluent 2, desktop-first

> v2.3 kế thừa toàn bộ baseline v2.2 và bổ sung/chốt S13 — `Asset Context Drawer / Ngữ cảnh tài sản`. S13 không phải màn hình độc lập trong navigation; đây là drawer mở trực tiếp từ một dòng đang chọn trong S12 Workbench để xử lý sâu một tài sản mà không làm mất context bảng.

## 0. Quyết định v2.3 đã duyệt

- Toàn bộ quyết định S09–S12 của v2.2 tiếp tục giữ nguyên.
- S13 — `Asset Context Drawer / Ngữ cảnh tài sản` đã được người dùng duyệt làm baseline tiếp theo.
- S13 luôn mở trong context của S12; không tạo menu riêng và không biến thành một full-screen độc lập.
- Khi mở S13, S12 vẫn được giữ ở nền với nguyên filter, sort, search, pagination, selection và vị trí scroll hiện tại.
- S13 phục vụ hoàn thiện sâu một tài sản: đối chiếu dữ liệu gốc với dữ liệu chuẩn hóa, xử lý nhận diện/thông số, xem candidate Kho tri thức và context nguồn giá kế thừa.
- `Dữ liệu gốc (Excel)` phải luôn truy vết được và không bị ghi đè bởi dữ liệu chuẩn hóa.
- Kho tri thức/AI chỉ gợi ý; không auto-accept candidate, không tự xác nhận identity, không tự xác nhận giá.
- S13 chỉ hiển thị summary nguồn giá/Thuyết minh/giá sơ bộ và CTA chuyển tiếp đúng tài sản; không nhân bản toàn bộ màn hình Nguồn giá.
- S13 không phải màn hình `So sánh & Xác nhận giá thẩm định chính thức`; việc chốt giá chính thức vẫn ở bước riêng sau Nguồn giá & chứng cứ.
- Validation tiếp tục chạy tại field/dòng đang phát sinh, theo `Blocking`, `Warning`, `Info`; không có màn hình Kiểm tra riêng.
- Các thay đổi identity quan trọng hoặc thao tác có thể làm mất dữ liệu đã xác nhận phải có confirm rõ ảnh hưởng.
- S13 phải duy trì lineage: `raw source → normalized asset → candidate KB/source/price → human decision`.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị.
- Chỉ dùng phương pháp so sánh.
- Công việc chính: Kho tri thức + nguồn giá Internet + Thuyết minh đơn giá.
- Không thiết kế khảo sát hiện trạng.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word/PDF là input/output; Workbench + database là nguồn dữ liệu làm việc chính thức.
- Không thiết kế workflow giao việc/chờ xác nhận giữa nhiều tài khoản ở giai đoạn này.

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
→ Quay lại Quản lý yêu cầu sơ bộ
    → Rà soát tích hợp
    → Tạo file kết quả sơ bộ
→ S09 Chuyển sang thẩm định chính thức
→ S10 Tổng quan hồ sơ
→ S11 Xác nhận & điều chỉnh danh mục triển khai
→ S12 Workbench tài sản
    → S13 Asset Context Drawer / Ngữ cảnh tài sản
→ Nguồn giá & chứng cứ
→ S14 So sánh & Xác nhận giá thẩm định chính thức
→ S17 Hoàn tất hồ sơ
→ S18 Báo cáo & Chứng thư
→ S19 Phát hành
→ S20 Lưu trữ & hình thành tri thức
```

Không có checkpoint riêng `Khai báo thông tin thực hiện`, `Kiểm tra hồ sơ`, `KSCL`.

## 3. Pre-case baseline giữ nguyên từ v2.2

Trạng thái cấp danh sách: `Mới tạo`, `Mới nhận danh mục`, `Đang phân tích`, `Sẵn sàng tạo kết quả sơ bộ`, `Đã tạo kết quả sơ bộ`, `Không tiếp tục`, `Đã chuyển thành hồ sơ`.

Không dùng `Ghi nhận đã gửi`, `Chờ khách hàng phản hồi`, `Ghi nhận phản hồi`, `Đã chấp thuận giá đề xuất`.

S08 vẫn là checkpoint tích hợp trong S02. File kết quả sơ bộ là bản sao file Excel khách hàng và bổ sung đúng 02 cột `Đơn giá đề xuất`, `Thành tiền`; file gốc không bị ghi đè; output có version/lineage.

## 4. S09 — Chuyển sang thẩm định chính thức

Giữ nguyên baseline v2.2:

- Pre-case phải có file kết quả sơ bộ.
- Giá đề xuất sơ bộ không tự trở thành giá thẩm định chính thức.
- Trường hồ sơ chưa điền đủ vẫn có thể tạo hồ sơ nếu chưa tới dependency bắt buộc; hiển thị `Chưa bổ sung`.
- `Chủ đầu tư` là searchable select và dữ liệu được copy thành snapshot hồ sơ.
- `Tên hồ sơ` dẫn xuất từ `Tài sản thẩm định`; không nhập riêng.
- `Ngày bắt đầu dự kiến` = `Ngày hợp đồng`; `Ngày kết thúc dự kiến` = `Ngày chứng thư`.
- `Thẩm định viên`, `Trợ lý`, `Tổ trưởng/Phụ trách` lấy từ `Cấu hình → Thông tin thực hiện mặc định`.
- Primary CTA: `Tạo hồ sơ thẩm định chính thức`.

## 5. S10 — Tổng quan hồ sơ

Giữ nguyên baseline v2.2:

- S10 là dashboard điều phối hồ sơ, không phải form nhập liệu dài.
- Workflow gồm 8 checkpoint: `Thông tin hồ sơ`, `Danh mục triển khai`, `Hoàn thiện tài sản`, `Nguồn giá & chứng cứ`, `Giá thẩm định chính thức`, `Hoàn tất hồ sơ`, `Báo cáo & Chứng thư`, `Phát hành`.
- Ngay sau S09, `Việc cần làm tiếp theo` dẫn vào S11.
- S10 chỉ tổng hợp readiness và validation; mọi vấn đề cụ thể có CTA `Đi tới` đúng nơi sửa.
- Không reintroduce `Thông tin thực hiện`, `Kiểm tra`, `KSCL` thành checkpoint riêng.

## 6. S11 — Xác nhận & điều chỉnh danh mục triển khai

Giữ nguyên baseline v2.2:

- S11 chốt phạm vi tài sản, không chốt giá.
- Cho phép giữ nguyên, thêm mới, loại bớt và khôi phục tài sản trước khi xác nhận.
- Tài sản bị loại không bị xóa khỏi Pre-case; giữ đầy đủ lineage.
- Dòng mới có badge `Mới bổ sung`, không tự sao chép giá từ tài sản khác.
- `Tổng triển khai = Giữ lại + Mới bổ sung`.
- Primary CTA: `Xác nhận danh mục triển khai`.

## 7. S12 — Workbench tài sản

### 7.1 Mục tiêu

S12 là bảng làm việc chính của danh mục đã được chốt tại S11. Người dùng hoàn thiện nhận diện và thông số đủ để so sánh đúng thiết bị, đồng thời giữ nguyên dữ liệu nguồn để truy vết.

### 7.2 Visual baseline đã duyệt

S12 dùng Fluent 2, desktop-first, ưu tiên data grid lớn. Baseline hiện hành thể hiện:

- shell VALORA thống nhất với S09–S11;
- header `S12 Workbench tài sản`;
- card hồ sơ + KPI readiness;
- notice rõ rằng dữ liệu gốc Excel luôn được giữ nguyên;
- toolbar filter/search/tùy chỉnh cột;
- grid lớn với nhóm cột `Thông tin từ Excel (Dữ liệu gốc)` và `Thông tin chuẩn hóa (Bạn đang chỉnh sửa)` đặt cạnh nhau;
- cột `Thông số kỹ thuật chính`, `Trạng thái`, `Kho tri thức`, `Nguồn giá`, `Đơn giá sơ bộ`, `Thao tác`;
- thao tác mỗi dòng `Mở ngữ cảnh` để mở S13.

### 7.3 Trạng thái dòng

Có thể gồm:

- `Đủ thông tin`;
- `Cần bổ sung`;
- `Mới bổ sung`;
- `Cần phân tích giá`.

Trạng thái Kho tri thức tách riêng như `Có / Đã tìm thấy gợi ý`, `Cần xác nhận`, `Chưa có`.

### 7.4 Guardrail S12

- Raw source không bị ghi đè.
- Dòng không đổi có thể tái sử dụng candidate Kho tri thức, nguồn giá và giá sơ bộ từ Pre-case.
- Dòng mới hoặc thay đổi model/thông số quan trọng phải được đánh dấu cần xử lý lại.
- Không tự áp dụng giá cũ cho một identity đã thay đổi đáng kể.
- Primary CTA cuối bước vẫn là `Tiếp tục sang Nguồn giá & chứng cứ` khi readiness phù hợp.

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

Header phải đủ để người dùng luôn biết mình đang chỉnh đúng thiết bị nào.

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
- Field thay đổi identity quan trọng phải cảnh báo nếu làm mất/giảm hiệu lực candidate hoặc nguồn giá kế thừa.

### 8.6 Validation inline

Validation hiển thị tại đúng field hoặc block phát sinh:

- `Blocking`: phải xử lý trước hành động có dependency.
- `Warning`: vẫn được tiếp tục nhưng phải nêu rõ ảnh hưởng.
- `Info`: trạng thái/thông tin không cản workflow.

Mọi validation phải trả lời được:

```text
Vấn đề gì → nằm ở đâu → ảnh hưởng gì → sửa thế nào
```

Nếu thay đổi `Tên thiết bị`, `Hãng`, `Model`, `Xuất xứ` hoặc thông số identity quan trọng làm lệch dữ liệu đã kế thừa, phải confirm trước khi commit thay đổi.

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
- `Đơn giá sơ bộ`.

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
- giá sơ bộ kế thừa;
- trạng thái nguồn: còn truy cập / cần kiểm tra / chỉ còn snapshot lịch sử;
- candidate/source liên quan tới đúng tài sản.

CTA rõ ràng:

- `Mở Nguồn giá` hoặc `Xem Nguồn giá & Chứng cứ`.

CTA phải chuyển đúng context của tài sản hiện tại, không bắt người dùng tìm lại thiết bị.

### 8.10 Lưu thay đổi

Footer drawer baseline:

- secondary: `Hủy thay đổi`;
- primary: `Lưu thông tin`;
- tertiary/utility: `Đóng ngữ cảnh (Esc)`.

Quy tắc:

- Một primary CTA nổi bật.
- Nếu không có thay đổi thì `Lưu thông tin` disabled hoặc chuyển sang trạng thái không nổi bật.
- Nếu có unsaved changes và người dùng đóng drawer, phải cảnh báo rõ `Lưu / Bỏ thay đổi / Tiếp tục chỉnh sửa`.
- Lưu thành công không được reset filter/sort/scroll của S12.

### 8.11 Loading / Empty / Error / Warning states

S13 phải có trạng thái thiết kế cho:

- đang tải dữ liệu asset context;
- chưa có dữ liệu normalized;
- chưa có candidate Kho tri thức;
- chưa có nguồn giá;
- nguồn Internet cũ/mất truy cập nhưng còn snapshot;
- tải candidate/source lỗi;
- stale data / dữ liệu vừa thay đổi ở nơi khác nếu hệ thống phát hiện;
- warning khi identity thay đổi làm candidate/nguồn/giá sơ bộ cần tái kiểm tra.

Thông báo dùng tiếng Việt nghiệp vụ, không hiển thị HTTP/SQL/stack trace/row_version.

### 8.12 Audit / Lineage

Người dùng phải có khả năng truy vết logic dữ liệu:

```text
Raw source / Excel
→ Dữ liệu chuẩn hóa
→ Candidate Kho tri thức / nguồn giá / giá sơ bộ
→ Quyết định người dùng
→ Dữ liệu chính thức tiếp theo
```

Không cần hiển thị thuật ngữ database/API trong UI; có thể thể hiện dưới dạng `Nguồn dữ liệu`, `Lịch sử thay đổi`, `Đã kế thừa từ`, `Đã xác nhận bởi người dùng`.

### 8.13 Ranh giới S13 đã khóa

S13 **được phép**:

- hoàn thiện ngữ cảnh một tài sản;
- chỉnh normalized fields;
- xem raw source;
- xem và quyết định candidate Kho tri thức;
- xem summary nguồn giá/Thuyết minh/giá sơ bộ;
- deep-link sang đúng tài sản ở Nguồn giá & Chứng cứ.

S13 **không được**:

- trở thành màn hình xác nhận giá chính thức;
- tự tính/chốt Appraised Price;
- auto-accept identity candidate;
- auto-apply nguồn giá;
- ghi đè raw source;
- nhân bản full panel Kho tri thức/Nguồn giá;
- biến thành wizard dài nhiều bước;
- tạo menu/navigation độc lập.

## 9. Validation phân tán — không có bước Kiểm tra riêng

Không có màn hình `Kiểm tra hồ sơ` riêng nhưng validation vẫn bắt buộc.

- `Blocking`: phải xử lý trước dependency liên quan.
- `Warning`: vẫn cho tiếp tục nhưng nêu rõ rủi ro/cần kiểm tra.
- `Info`: chỉ cung cấp trạng thái.

S10 chỉ tổng hợp readiness. S12/S13/S14 và các màn hình sau hiển thị issue ngay tại nơi phát sinh và có `Đi tới` đúng chỗ sửa khi cần.

## 10. Cụm giá Pre-case tiếp tục giữ nguyên

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

Không có `Chênh lệch`; không hiển thị `Chi phí vận chuyển` hoặc `Giá sau vận chuyển`.

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

Giá sơ bộ kế thừa vào hồ sơ chính thức chỉ là tham khảo, không phải giá thẩm định chính thức.

## 11. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price hoặc auto-apply.
- File Excel nguồn và raw observation phải truy lại được.
- Không ghi đè dữ liệu gốc khách hàng bằng dữ liệu chuẩn hóa.
- Staging và dữ liệu chính thức phải phân biệt.
- Giá lịch sử Kho tri thức chỉ là tham khảo.
- Nguồn Internet mất truy cập vẫn giữ lịch sử URL/snapshot và đánh dấu cần kiểm tra.
- Vietnamese-first, không hiển thị HTTP/SQL/stack trace/row_version cho người dùng.
- Mỗi màn hình/context có một primary CTA nổi bật.
- Hành động rủi ro cao phải confirm rõ thay đổi và khả năng hoàn tác.
- S09–S13 dùng cùng Valora shell theo Fluent 2, desktop-first cho grid/workbench.
- Final price, hoàn tất, phát hành và các quyết định chính thức đều human-confirmed và có lineage.

## 12. Screen inventory v2.3

| ID | Màn hình | Trạng thái / quyết định v2.3 |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát tích hợp + tạo/quản lý file kết quả + CTA chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | Không có màn hình riêng; tích hợp S02 |
| S09 | Chuyển sang thẩm định chính thức | P0 — mockup/field layout đã duyệt |
| S10 | Tổng quan hồ sơ | P0 — workflow dashboard 8 checkpoint |
| S11 | Xác nhận & điều chỉnh danh mục triển khai | P0 — giữ/thêm/loại + lineage; chốt phạm vi, không chốt giá |
| S12 | Workbench tài sản | P0 — grid desktop-first + raw vs normalized + context entry point |
| S13 | Asset Context Drawer | **P0 — baseline đã duyệt trong v2.3; drawer trong S12, không phải màn hình độc lập** |
| S14 | So sánh & Xác nhận giá | P0 — giá sơ bộ vs giá chính thức + rationale; thiết kế chi tiết là bước tiếp theo |
| S15 | Kiểm tra hồ sơ | **Không dùng trong workflow single-user v2.3; validation phân tán** |
| S16 | KSCL Checklist | **Không dùng trong workflow single-user v2.3** |
| S17 | Hoàn tất hồ sơ | P0 — readiness summary + confirmations + blocking issues tổng hợp |
| S18 | Báo cáo & Chứng thư | P1 — templates, preview, draft versions |
| S19 | Phát hành | P1 — confirm, lock version, export |
| S20 | Lịch sử & Lưu trữ | P1 — timeline, files, sources, prices, provenance, knowledge promotion |

## 13. Mockup baseline v2.3

Baseline mockup đã được duyệt:

- S09 — Chuyển sang thẩm định chính thức, Fluent 2.
- S10 — Tổng quan hồ sơ, workflow rút gọn 8 checkpoint.
- S11 — Xác nhận & điều chỉnh danh mục triển khai, full-screen riêng.
- S12 — Workbench tài sản, data grid lớn với raw vs normalized.
- **S13 — Asset Context Drawer mở từ S12; drawer bên phải + S12 giữ nguyên ở nền.**

S13 baseline cụ thể:

- asset header compact;
- raw vs normalized trong drawer;
- trạng thái và mức hoàn thiện;
- candidate Kho tri thức;
- nguồn giá/giá sơ bộ summary;
- tab `Tổng quan / Thông số kỹ thuật / Nguồn giá & Chứng cứ / Lịch sử`;
- `Hủy thay đổi / Lưu thông tin / Đóng ngữ cảnh`;
- không làm mất context S12.

## 14. Trạng thái triển khai

Đây là **thiết kế mục tiêu đã duyệt**. Không được suy diễn rằng toàn bộ nội dung v2.3 đã được implement trong product code.

Các guardrail kỹ thuật hiện có trong repository vẫn tiếp tục có hiệu lực: tenant isolation fail-closed; staging không phải official; Apply human-confirmed; restricted Workbench fields đi qua human-controlled mutation path; AI advisory-only; source evidence phải có provenance.

## 15. Nhiệm vụ UI/UX tiếp theo sau v2.3

Sau khi S13 đã được chốt, bước thiết kế tiếp theo là **S14 — So sánh & Xác nhận giá thẩm định chính thức**.

S14 cần được thiết kế theo các nguyên tắc đã khóa:

- phân biệt rõ `Giá sơ bộ` và `Giá thẩm định chính thức`;
- dựa trên nguồn giá/chứng cứ đã được rà soát;
- người dùng phải explicit confirm giá chính thức;
- có rationale/ghi chú quyết định;
- không auto-price;
- có validation/readiness rõ trước khi cho chốt;
- giữ lineage từ raw/normalized asset → nguồn/chứng cứ → giá sơ bộ → quyết định giá chính thức.

Không nhảy sang S17/S18 trước khi S14 được người dùng duyệt.