# Prompt bàn giao phiên làm việc tiếp theo — VALORA UI/UX v2.2

Tiếp tục dự án `Reguluspt/valora-engineering` trên nhánh thiết kế hiện hành `docs/uiux-handoff-v2.2`.

## 1. Đọc trước theo thứ tự

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. `docs/design/VALORA_UIUX_HANDOFF_v2.2.md`
6. `docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md`
7. `docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md`
8. `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
9. `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`

`VALORA_UIUX_HANDOFF_v2.2.md` là baseline UI/UX mới nhất đã được người dùng duyệt cho S09–S12. Không quay lại baseline v2.1/v2.0 khi có xung đột.

## 2. Phạm vi sản phẩm đã khóa

- Single-user: 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời hồ sơ.
- Chỉ thẩm định giá máy móc thiết bị.
- Chỉ dùng phương pháp so sánh.
- Không thiết kế khảo sát hiện trạng.
- Kho tri thức/AI chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word/PDF là input/output; Workbench + database là nguồn dữ liệu làm việc chính thức.
- Không đưa workflow giao việc/chờ xác nhận đa người dùng vào giai đoạn hiện tại.
- Visual baseline S09–S12: Valora shell bám sát Fluent Design 2, desktop-first, bảng dữ liệu lớn thao tác nhanh, một primary CTA nổi bật mỗi màn hình.
- Không sửa code sản phẩm nếu người dùng chưa yêu cầu. Luôn phân biệt rõ target design và trạng thái đã implement.

## 3. Luồng người dùng hiện hành

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
→ Xác nhận giá thẩm định chính thức
→ Hoàn tất hồ sơ
→ Báo cáo & Chứng thư
→ Phát hành
→ Lưu trữ & hình thành tri thức
```

Không có checkpoint riêng `Kiểm tra hồ sơ` hoặc `KSCL` trong workflow single-user hiện tại.

## 4. Quy tắc validation mới đã khóa

**Không bỏ validation dữ liệu, nhưng không có màn hình Kiểm tra riêng.**

Validation chạy tại đúng field/dòng/màn hình phát sinh và chia 3 mức:

- `Blocking`: phải xử lý trước hành động nghiệp vụ có phụ thuộc.
- `Warning`: vẫn cho tiếp tục nhưng phải cảnh báo rõ.
- `Info`: chỉ cung cấp trạng thái/thông tin.

Nguyên tắc UX cho mọi vấn đề:

```text
Vấn đề gì → nằm ở đâu → ảnh hưởng gì → sửa thế nào → Đi tới đúng chỗ sửa
```

S10 chỉ tổng hợp readiness; không bắt người dùng chạy lại một màn hình kiểm tra.

## 5. S09 — Chuyển sang thẩm định chính thức: baseline đã duyệt

Mục tiêu: tạo hồ sơ chính thức từ Pre-case đã có file kết quả sơ bộ và tái sử dụng tối đa dữ liệu đã phân tích.

### 5.1 Thông tin Chủ đầu tư & liên hệ

`Chủ đầu tư` nên là search/select theo tên, MST, điện thoại; nếu chọn bản ghi có sẵn thì prefill:

- Mã số thuế;
- Số ĐT;
- Địa chỉ;
- Tài khoản Chủ đầu tư;
- Người đại diện;
- Chức vụ;
- Người liên hệ.

Dữ liệu được copy thành snapshot của hồ sơ; sửa snapshot hồ sơ không được âm thầm cập nhật master Chủ đầu tư. Nếu cần sửa master phải là hành động explicit.

### 5.2 Thông tin hồ sơ & thẩm định

**2A. Nhận diện hồ sơ** — thứ tự đã duyệt:

```text
Tài sản thẩm định
Mục đích
Ghi chú
```

- `Tên hồ sơ` ẩn và tự sinh từ `Tài sản thẩm định`.
- Bản `Tài sản thẩm định (viết thường)` tự sinh và ẩn.

**2B. Mốc hồ sơ / số hiệu văn bản**:

```text
Ngày hợp đồng | Số hợp đồng | Số QĐ
Ngày chứng thư | Số chứng thư | Thời điểm TĐ
Ngày thương thảo | Ngày dự thảo
```

Dẫn xuất/ẩn:

- Ngày hợp đồng dạng chữ tự sinh.
- Ngày báo cáo = Ngày chứng thư.
- Ngày chứng thư dạng chữ tự sinh.
- Thời điểm TĐ chân trang tự sinh từ Thời điểm TĐ.

**2C. Giá trị & phí**:

```text
Tổng giá trị | Giá đã bao gồm
Phí thẩm định
```

**3. Biên bản nghiệm thu & thanh lý**:

```text
Ngày thanh lý | Số hóa đơn | Ngày hóa đơn
```

Các field hồ sơ ở bước chuyển chính thức **không bắt buộc phải điền hết ngay**. Trường trống hiển thị `Chưa bổ sung`; chỉ validate format nếu người dùng đã nhập. Sau khi tạo hồ sơ phải có CTA `Bổ sung thông tin hồ sơ`.

`Ngày bắt đầu dự kiến` và `Ngày kết thúc dự kiến` không có field nhập riêng; dẫn xuất tương ứng từ `Ngày hợp đồng` và `Ngày chứng thư`.

`Thẩm định viên`, `Trợ lý`, `Tổ trưởng/Phụ trách` không nhập theo từng hồ sơ; chuyển vào `Cấu hình → Thông tin thực hiện mặc định` và hồ sơ kế thừa giá trị này.

## 6. S10 — Tổng quan hồ sơ: baseline đã duyệt

S10 là dashboard điều phối hồ sơ, không phải form nhập liệu dài.

Workflow hiển thị 8 checkpoint:

1. Thông tin hồ sơ.
2. Xác nhận & điều chỉnh danh mục.
3. Workbench tài sản / Hoàn thiện tài sản.
4. Nguồn giá & chứng cứ.
5. Giá thẩm định chính thức.
6. Hoàn tất hồ sơ.
7. Báo cáo & Chứng thư.
8. Phát hành.

Ngay sau S09, card `Việc cần làm tiếp theo` phải dẫn vào **S11 — Xác nhận & điều chỉnh danh mục triển khai**.

Cột summary/right rail có thể tổng hợp:

- mức hoàn thiện thông tin hồ sơ;
- số tài sản triển khai;
- tiến độ nhận diện;
- số nguồn giá/Thuyết minh;
- số giá sơ bộ;
- số giá chính thức;
- readiness;
- thông tin cần bổ sung;
- nguồn Pre-case/file/snapshot/lineage;
- người thực hiện lấy từ Cấu hình.

Không reintroduce checkpoint `Thông tin thực hiện`, `Kiểm tra`, `KSCL`.

## 7. S11 — Xác nhận & điều chỉnh danh mục triển khai: baseline đã duyệt

S11 **chốt phạm vi tài sản, không chốt giá**.

Người dùng được phép:

- giữ nguyên tài sản từ Pre-case;
- bỏ bớt tài sản khỏi phạm vi hồ sơ chính thức;
- thêm mới tài sản;
- chọn nhiều dòng để loại khỏi hồ sơ;
- khôi phục tài sản đã loại trước khi xác nhận danh mục.

Quy tắc dữ liệu:

- Tài sản bị loại **không bị xóa khỏi Pre-case**; đánh dấu `Không đưa vào hồ sơ chính thức`, giữ toàn bộ lịch sử/lineage.
- Tài sản thêm mới có badge `Mới bổ sung`.
- Dòng mới chưa có giá vẫn được phép đi qua S11, nhưng vào S12 ở trạng thái cần hoàn thiện/phân tích tương ứng.
- Không tự sao chép giá từ tài sản khác cho dòng mới.
- Danh mục Pre-case gốc và snapshot phân tích sơ bộ là bất biến; danh mục triển khai chính thức được hình thành tại S11.

Ví dụ KPI mockup đã duyệt:

```text
Danh mục từ Pre-case: 147
Giữ lại: 142
Mới bổ sung: 3
Loại khỏi hồ sơ: 5
Tổng triển khai: 145
```

`Tổng triển khai = Giữ lại + Mới bổ sung`.

Primary CTA: `Xác nhận danh mục triển khai`.

## 8. S12 — Workbench tài sản: baseline đã duyệt

S12 là bảng làm việc chính của 145 tài sản đã được chốt tại S11.

Mục tiêu: hoàn thiện định danh và thông số đủ để so sánh đúng thiết bị, đồng thời giữ dữ liệu gốc để truy vết.

Nguyên tắc UI/UX:

- Ưu tiên grid lớn, filter, search, inline edit cho trường ngắn.
- Drawer cho thông tin dài/ngữ cảnh chi tiết.
- Luôn phân biệt `Dữ liệu gốc` và `Dữ liệu chuẩn hóa`.
- Không ghi đè raw source khách hàng.
- Có trạng thái dòng như `Đủ thông tin`, `Cần bổ sung`, `Mới bổ sung`, `Cần phân tích giá` theo nghiệp vụ.
- Hiển thị tình trạng Kho tri thức, số nguồn giá và giá sơ bộ kế thừa nếu có.
- Dòng không đổi được tái sử dụng candidate Kho tri thức, nguồn giá và giá đề xuất sơ bộ từ Pre-case.
- Dòng mới/đổi model/thông số quan trọng phải được đánh dấu cần xử lý; không tự áp dụng giá cũ.
- AI/Kho tri thức chỉ đưa gợi ý; người dùng quyết định Dùng/Không dùng/Sửa.

Mockup S11 và S12 đã được tách thành hai màn hình riêng và được người dùng duyệt làm hướng thiết kế tiếp tục.

## 9. Quy tắc giá Pre-case vẫn giữ nguyên

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

Không hiển thị `Chênh lệch`, `Chi phí vận chuyển`, `Giá sau vận chuyển`.

`Thuyết minh đơn giá` có thể là căn cứ duy nhất của một dòng Pre-case. Không cho tạo file kết quả sơ bộ nếu còn dòng chưa xác định được giá.

Khi vào hồ sơ chính thức, giá sơ bộ chỉ là dữ liệu kế thừa/tham khảo; **không được hiểu là giá thẩm định chính thức**. Giá chính thức được người dùng xác nhận ở bước riêng sau khi hoàn thiện tài sản và chứng cứ.

## 10. Nhiệm vụ phiên tiếp theo — S13 Asset Context Drawer / Ngữ cảnh tài sản

Bắt đầu từ S12 và thiết kế **S13 — Asset Context Drawer** trước. Không nhảy sang màn hình giá chính thức khi S13 chưa được duyệt.

### 10.1 Mục tiêu

Cho phép xử lý sâu **một thiết bị đang chọn trong S12** mà không mất context bảng/dòng hiện tại.

### 10.2 Nội dung cần thiết kế

Tối thiểu phải xử lý:

- header thiết bị + trạng thái hiện tại;
- `Dữ liệu gốc (Excel)` cạnh `Dữ liệu chuẩn hóa`;
- Tên thiết bị, Hãng, Model, Xuất xứ, Thông số kỹ thuật chính;
- inline validation tại đúng field;
- gợi ý Kho tri thức với mức tương đồng + điểm giống/khác;
- hành động `Dùng`, `Không dùng`, `Xem chi tiết` cho từng candidate;
- không auto-accept candidate;
- summary nguồn giá/Thuyết minh/giá sơ bộ đã kế thừa;
- CTA mở panel `Nguồn giá` đúng thiết bị hiện tại;
- trạng thái `Chưa có nguồn`, `Cần xác nhận`, `Đủ thông tin`, `Cần bổ sung`, `Cần phân tích giá`;
- lưu thay đổi mà không làm mất vị trí filter/sort/scroll của S12;
- loading/empty/error/warning states;
- confirm khi hành động có thể làm mất dữ liệu đã xác nhận hoặc thay đổi identity quan trọng;
- audit/lineage: raw source → normalized asset → candidate KB/source/price.

### 10.3 Ranh giới S13

- S13 tập trung vào **ngữ cảnh và hoàn thiện một tài sản**.
- Không biến S13 thành màn hình `So sánh & Xác nhận giá chính thức` hoàn chỉnh.
- Không nhân bản toàn bộ panel Kho tri thức/Nguồn giá; chỉ hiển thị summary + deep link/panel chuyển tiếp khi cần.
- Không dùng wizard đa bước nếu drawer/tab trong context S12 xử lý tốt hơn.
- Desktop-first; drawer đủ rộng để đọc Raw vs Normalized nhưng vẫn phải giữ được context bảng S12.

### 10.4 Cách làm việc với người dùng

1. Trình bày cấu trúc/logic S13 ngắn gọn.
2. Dựng mockup S13 bám Fluent 2 và shell S09–S12.
3. Chờ người dùng góp ý/duyệt.
4. Chỉ sau khi S13 được duyệt mới cập nhật Handoff phiên bản tiếp theo (dự kiến v2.3) và prompt bàn giao mới.

## 11. Guardrail quan trọng

- Không sửa product code nếu chưa được yêu cầu.
- Không giả định business rule quan trọng khi chưa đủ dữ liệu; hỏi người dùng nếu ảnh hưởng quyết định nghiệp vụ.
- Không reintroduce workflow phản hồi khách hàng đã loại bỏ khỏi Pre-case.
- Không reintroduce bước Kiểm tra/KSCL riêng ở single-user hiện tại.
- Không tự biến dữ liệu/gợi ý AI thành quyết định chính thức.
- Không ghi đè file Excel nguồn/raw observation.
- Mọi hành động chốt phạm vi, chốt giá, hoàn tất, phát hành phải human-confirmed và có lineage.
- Vietnamese-first; không hiển thị thuật ngữ kỹ thuật API/database cho người dùng cuối.

## 12. Trạng thái repository hiện tại

- Repository: `Reguluspt/valora-engineering`
- Branch UI/UX hiện hành: `docs/uiux-handoff-v2.2`
- Handoff mới nhất: `docs/design/VALORA_UIUX_HANDOFF_v2.2.md`
- Handoff v2.2 đã cập nhật S09–S12 và được dùng làm baseline cho phiên tiếp theo.
- Đây là tài liệu thiết kế mục tiêu; không được suy diễn rằng toàn bộ nội dung đã được implement trong code.
