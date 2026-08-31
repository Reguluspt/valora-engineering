# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master handoff — **Consolidated v2.3 + Spreadsheet Fill Engine Baseline + NCC Price Warning Authority**; không đồng nghĩa product code đã implement  
**Cập nhật:** 31/08/2026

> Master này consolidate authority v2.3 hiện hành. Addendum được giữ để truy vết quyết định/visual authority. Khi có xung đột, quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành

Các baseline/authority đã khóa:

- S09 — Chuyển sang thẩm định chính thức.
- S10 — Tổng quan hồ sơ.
- S11 — Xác nhận & điều chỉnh danh mục triển khai.
- S12 — Workbench tài sản.
- S13 — Asset Context Drawer; drawer trong S12, không phải route độc lập.
- Nguồn giá & Chứng cứ.
- NCCQ — Tạo & quản lý báo giá NCC — Iteration 6.
- TM01 — Danh sách mẫu báo giá NCC — Iteration 1.
- TM03 — Upload & Mapping template NCC — Iteration 1 Word-only.
- TM04 — Preview / Test fill template NCC — Iteration 1.
- NCCQ child — Hoàn tất 01 báo giá NCC — Iteration 3, scope 01 báo giá / 01 NCC.
- Kết quả thẩm định giá — Iteration 1, 03 bảng biểu mẫu công ty immutable.
- Microsoft 365 Document Workspace / Bộ tài liệu phát hành — baseline authority.
- 03_Hợp đồng — Danh sách & tạo tài liệu — Iteration 1 Baseline / Design Authority.
- Managed Regions — Báo cáo thẩm định giá — Iteration 1 Baseline / Design Authority.
- Managed Regions — Chứng thư thẩm định giá — Iteration 1 Baseline / Design Authority.
- Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1 Baseline / Design Authority.
- Phát hành bộ tài liệu — Iteration 1 Baseline / Design Authority.
- Quản lý mẫu tài liệu generic — Iteration 1.
- Mapping Template tài liệu generic Word — Iteration 2.
- Kiểm tra & hoàn tất template Word generic — Iteration 1.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 3: Rà soát & chỉnh sửa — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 4: Kiểm tra & hoàn tất Word + Bảng tính — Iteration 1 Baseline / Design Authority.
- **Bảng tính Fill Engine — Implementation Contract v1 — Iteration 1 Baseline / Design Authority.**

Current business-rule authority mới nhất:

- **Không có màn `Kiểm tra quy tắc đối chiếu giá`.** Mockup màn này discarded, không phải baseline.
- Cảnh báo `Giá NCC ↔ Đơn giá hiện hành` xuất hiện ngay tại NCCQ theo từng dòng; Warning, không Blocking.

Supersession/guardrail:

- Không dùng S14 — So sánh & Xác nhận giá thẩm định chính thức.
- Không có màn Kiểm tra hồ sơ riêng.
- Không có workflow KSCL/phê duyệt nhiều cấp riêng trong single-user v2.3.
- Không có NCCQ aggregate trung gian sau `Chọn nhà cung cấp đã xác nhận giá`.
- AI/Kho tri thức chỉ gợi ý; user quyết định nghiệp vụ chính thức.
- `Bảng tính` là terminology nghiệp vụ chính thức cho template Excel.
- `03_Hợp đồng` quản lý working documents; signed scan thuộc `05_Pháp lý`.
- Managed Regions chỉ cập nhật vùng do VALORA quản lý; narrative ngoài vùng không bị silent overwrite.
- Sync luôn explicit; user xem thay đổi và chọn nội dung trước khi ghi vào Word.
- Document Revision và Microsoft 365 file version là hai lớp lineage liên kết nhưng không đồng nhất.
- Revision/release đã phát hành không được silent mutate.
- Publishing không silent publish/lock và không tự thêm/bỏ tài liệu khỏi release package.
- Fill Engine không overwrite template, không staticize formula và không silent drop workbook feature.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị; phương pháp so sánh.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Excel/Word/PDF là artifact input/output theo context; không có nghĩa mọi module hỗ trợ mọi định dạng.
- Template báo giá NCC chỉ Word `.docx`.
- Template generic có thể Word `.docx` và Bảng tính `.xlsx/.xlsm` theo authority từng loại.
- Microsoft 365 quản lý file/file version/Word; VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status và release manifest.
- Không xây fake Word editor hoặc fake Excel editor.
- Không đưa dữ liệu nhận diện khách hàng/NCC/hồ sơ thật vào public repository.

## 2. North-star user flow v2.3

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
   → Kho tri thức
   → Nguồn Internet
   → Hồ sơ cũ / Giá lịch sử
   → Thuyết minh đơn giá
   → Người dùng ấn định / điều chỉnh giá
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục triển khai
→ Workbench tài sản
→ Asset Context Drawer
→ Nguồn giá & Chứng cứ
→ Tạo & quản lý báo giá NCC
   → Hoàn tất từng báo giá NCC
   → Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
   → Bảng Đặc điểm kinh tế - kỹ thuật
   → Bảng Tổng hợp giá nhà cung cấp
   → Bảng Kết quả thẩm định giá
→ Microsoft 365 Document Workspace / Bộ tài liệu phát hành
   → 03_Hợp đồng — Danh sách & tạo tài liệu
   → Báo cáo thẩm định giá → Managed Regions — Báo cáo
   → Chứng thư thẩm định giá → Managed Regions — Chứng thư
   → Đồng bộ dữ liệu & Quản lý phiên bản tài liệu
   → Phát hành bộ tài liệu
      → Chọn tài liệu
      → Kiểm tra tình trạng
      → Xem bộ tài liệu
      → Xác nhận phát hành
      → Khóa phiên bản đã phát hành
```

Không có checkpoint riêng: `Khai báo thông tin thực hiện`, `Xác nhận giá thẩm định chính thức`, `Kiểm tra hồ sơ`, `KSCL`, `Kiểm tra quy tắc đối chiếu giá`.

Supporting configuration:

```text
Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu
→ Tạo/chọn mẫu → AI phân tích & đề xuất
→ Rà soát & chỉnh sửa → Kiểm tra & hoàn tất
→ Bảng tính Fill Engine: Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version
```

## 3. Pre-case

### 3.1 Quản lý yêu cầu sơ bộ

Trạng thái: `Mới tạo`, `Mới nhận danh mục`, `Đang phân tích`, `Sẵn sàng tạo kết quả sơ bộ`, `Đã tạo kết quả sơ bộ`, `Không tiếp tục`, `Đã chuyển thành hồ sơ`.

S08 không có màn riêng; rà soát và tạo file kết quả sơ bộ tích hợp S02. File kết quả sơ bộ là bản sao Excel khách hàng, giữ cấu trúc tối đa và bổ sung đúng:

```text
Đơn giá đề xuất | Thành tiền
```

Output có version/lineage; file nguồn không bị ghi đè.

### 3.2 Giá Pre-case

```text
Đơn giá KH dự kiến → Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo → Vận chuyển (%)
→ Đơn giá đề xuất → Người dùng ấn định / sửa giá
```

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

Không tạo file kết quả sơ bộ nếu dòng cần định giá chưa có mức giá do user ấn định. Giá tại thời điểm tạo file được kế thừa làm giá khởi tạo khi chuyển chính thức.

## 4. Đơn giá hiện hành

Mỗi tài sản có một `Đơn giá hiện hành` tại từng thời điểm. Giá ban đầu có thể kế thừa Pre-case; user có thể sửa tại context được phép. AI/Kho tri thức/rule engine/Internet/hồ sơ cũ/báo giá NCC không tự ghi đè. Mọi thay đổi giữ history/lineage/audit.

## 5. Nguồn giá & Chứng cứ — Price & Evidence Authority

Thứ tự ưu tiên:

```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```

`Kho tri thức` là cơ chế hỗ trợ tìm/gợi ý, không phải nguồn giá thứ tư. Giá NCC không phải nguồn chính xác định Đơn giá thẩm định cuối cùng; phục vụ tạo/tái tạo báo giá, evidence/lineage và đối chiếu.

Nguồn Internet tối thiểu lưu URL/định danh, giá, ngày thu thập, trạng thái truy cập, snapshot/tài liệu, trạng thái rà soát. Thuyết minh đơn giá có version/history. Hồ sơ cũ phải truy vết tài sản hiện tại → hồ sơ/tài sản cũ → hãng/model → thời điểm → giá Kết quả → mức tương đồng → tài liệu nguồn. Chọn nguồn không tự copy thành Đơn giá hiện hành.

## 6. S09–S13

- **S09:** chuyển chính thức từ Pre-case, giữ lineage; không tạo checkpoint xác nhận giá lại.
- **S10:** dashboard điều phối readiness; issue ở nơi phát sinh, có CTA `Đi tới`.
- **S11:** chốt phạm vi tài sản, không chốt giá; STT gốc immutable.
- **S12:** desktop-first data grid, raw Excel read-only cạnh normalized data.
- **S13:** Asset Context Drawer trong S12; tabs Tổng quan / Thông số KT / Nguồn giá & Chứng cứ / Lịch sử; không mất state S12 khi mở/đóng.

## 7. NCCQ — Tạo & quản lý báo giá NCC

Baseline bảng:

```text
STT | Tên tài sản | ĐVT | Số lượng |
NCC1 | NCC2 | NCC3 |
Đơn giá chọn | Thành tiền | Đơn giá hiện hành
```

Các cột NCC hiển thị tiền trực tiếp. Semantic giá: `Giá lịch sử`, `Giá đề nghị — chờ NCC xác nhận`, `Đơn giá NCC đã xác nhận`.

Cùng NCC consolidate vào báo giá phù hợp; không duplicate chỉ vì nguồn lịch sử khác. Lineage giữ cấp dòng; STT immutable.

Thiết bị Internet-only có thể sinh giá đề nghị trong khoảng:

```text
Đơn giá hiện hành <= Giá đề nghị <= Đơn giá hiện hành × 115%
```

Đây không phải giá xác nhận. Child flow `Hoàn tất 01 báo giá NCC` chỉ scope 01 báo giá/01 NCC và không tự sửa giá, tự chọn NCC hay tự hoàn tất hồ sơ.

CTA `Chọn nhà cung cấp đã xác nhận giá` lưu NCC → báo giá → dòng → giá xác nhận → evidence và chuyển trực tiếp sang Kết quả thẩm định giá.

### 7.1 Cảnh báo giá NCC — authority mới nhất

Không dựng màn/checkpoint `Kiểm tra quy tắc đối chiếu giá`. Cảnh báo hiển thị ngay tại NCCQ theo từng dòng.

```text
A. Giá NCC < Đơn giá hiện hành
→ luôn Warning, kể cả chênh lệch <= 15%

B. |Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15%
→ Warning chênh lệch lớn
```

Suy ra phía cao:

```text
Giá NCC > 115% × Đơn giá hiện hành
→ Warning
```

UI phải cho người dùng truy cập được ngay tại dòng:

```text
Đơn giá hiện hành | Giá NCC | Chênh tiền | Chênh % | Cảnh báo
```

Warning không Blocking. Người dùng vẫn có thể tiếp tục tạo báo giá. VALORA không tự sửa Giá NCC, không tự sửa Đơn giá hiện hành và không tự chọn giá thay user.

Companion authority: `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md`.

## 8. Template báo giá NCC — Word-only

```text
Cấu hình → Mẫu báo giá NCC → Tạo mẫu → Upload Word (.docx)
→ Mapping → Preview/Test fill → Lưu template → Sẵn sàng sử dụng
```

TM03 hỗ trợ text/content control/placeholder, table, repeating row, cell/column; AI chỉ gợi ý mapping. TM04 validation field/repeating/overflow/format/page break/footer với Blocking/Warning. Template/version đã dùng không silent overwrite.

## 9. Quản lý mẫu tài liệu generic

IA: `Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu`.

Nhóm: Tất cả; Hợp đồng & hồ sơ liên quan; Báo cáo thẩm định giá; Chứng thư thẩm định giá; Bảng tính; Báo giá nhà cung cấp.

Danh sách table-first:

```text
Loại tài liệu | Tên mẫu | Định dạng | Phiên bản | Mặc định |
Trạng thái | Cập nhật gần nhất | Người cập nhật | Thao tác
```

## 10. AI Template Assistant

Mental model:

```text
1. Chọn mẫu → 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa → 4. Kiểm tra & hoàn tất
```

Áp dụng Word generic + Bảng tính với analyzer/renderer/fill semantics riêng. Confidence: `Tin cậy cao / Cần xác nhận / Chưa xác định`. AI không silent accept mapping/publish/overwrite Template Version/change immutable form/change formula/promote custom field thành canonical.

## 11. Bước 3 — Rà soát & chỉnh sửa

Checkpoint user-controlled. Preview lớn nhất; panel mapping có summary/search/filter/group/highlight. Status: `Đã mapping | Cần xác nhận | Chưa mapping | Đã bỏ qua`. Action: `Giữ nguyên/Xác nhận`, `Đổi gán dữ liệu`, `Không dùng vùng này`. User luôn có `+ Thêm dữ liệu cần điền`, hỗ trợ cả vị trí→dữ liệu và dữ liệu→vị trí. Nếu không có field chuẩn, cho phép `Tạo trường tùy chỉnh` nhưng không tự promote thành canonical field.

## 12. Generic Word Mapping & Review

Mental model: chọn mẫu → chọn dữ liệu → click vị trí → VALORA tạo mapping phía sau → kiểm tra. UI không bắt user hiểu Region ID/source path/Content Control kỹ thuật. Sync policy user-facing: `Tự cập nhật khi dữ liệu thay đổi / Chỉ điền lần đầu / Người dùng tự chỉnh trong Word`. Preview không phải Word editor. Validation `Blocking / Warning / Info`; chỉ hợp lệ khi Blocking=0.

## 13. Bảng tính — Format-specific Authority

Analyzer nhận diện workbook/sheet/used range/header nhiều tầng/merge/section/repeating row/cột/formula/tổng/format/ảnh/evidence/page layout/hidden/named range. Mapping ưu tiên vùng/cột/dòng mẫu.

Reference `Bang Tinh - HĐ 42.xlsx` khóa:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

Engine giữ formula, không staticize/đổi rule; nhân dòng cập nhật relative refs và tổng/làm tròn. Không silent mất merge/style/border/format/image/evidence/page layout/named range/data validation/conditional formatting/workbook feature; validation phải cảnh báo nếu không bảo toàn.

### 13.1 Bảng tính Fill Engine — Implementation Contract v1 — Baseline Iteration 1

Mental flow:

```text
Chuẩn bị
→ Mapping
→ Preview & Validate
→ Fill & Recalculate
→ Save & Version
```

Logical architecture:

```text
Data Sources
→ Mapping Engine
→ Fill Engine Core
→ Excel Processor
→ Validator
→ Output & Lineage
```

Layout baseline Fluent 2 desktop-first:

- Header + template/version/context + command bar.
- Stepper 5 bước.
- Cột trái: Template & Output, Nguồn dữ liệu, Chế độ điền, Nguyên tắc an toàn.
- Cột giữa: Mapping Panel + Repeating Rows.
- Vùng lớn: Preview Spreadsheet.
- Hàng dưới: Validator + Fill Manifest + Output & Lineage.
- Footer có một primary CTA theo bước.

Preview là bề mặt kiểm tra fill, không phải Excel editor.

Mapping hỗ trợ metadata hồ sơ, tài sản, vùng/cột, repeating rows, vùng tổng hợp và formula-bearing template cells. User có thể thêm/chỉnh mapping thủ công; AI chỉ gợi ý.

Repeating rows phải giữ relative references, structure và STT nghiệp vụ immutable khi STT thuộc lineage gốc.

Formula authority:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

Fill Engine phải giữ formula, không staticize, không đổi business formula; nhân dòng giữ relative refs; cập nhật Tổng cộng/Làm tròn theo cấu trúc template.

Workbook feature preservation tối thiểu: merge, style, border, number format, ảnh/chứng cứ, print/page layout, named range, data validation, conditional formatting và workbook features liên quan. Không silent drop feature; nếu không thể bảo toàn phải Warning/Blocking trước khi output được coi là hợp lệ.

Validator:

```text
Blocking | Warning | Info
```

Blocking cản dependency fill/save; Warning nêu rủi ro nhưng có thể tiếp tục nếu rule cho phép; Info là trạng thái. Issue phải có vị trí + thông báo nghiệp vụ + action xem chi tiết/đi tới.

Fill Manifest tối thiểu ghi Template Version, sheet/vùng đích, nguồn dữ liệu/Data Snapshot hoặc dataset reference, thời điểm chạy, số dòng, số ô/vùng đã điền, formula preservation result, validator result và output identity/checksum phù hợp implementation.

Lineage:

```text
Template Version
→ Fill Run / Manifest
→ Output File
→ Lineage & Audit
```

Safety baseline:

- không ghi đè file mẫu;
- luôn tạo output mới;
- chỉ ghi vào vùng mapping được phép;
- giữ cấu trúc/công thức/định dạng;
- có manifest/audit cho mỗi fill run;
- không silent drop workbook feature.

Boundary:

- UI/UX authority khóa layout, mental model, control, validator semantics và safety communication.
- Domain contract khóa template/mapping/formula/feature-preservation/manifest-lineage semantics.
- Engine implementation không bị khóa technology stack/runtime chỉ bởi visual baseline.

Companion authority: `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md`.

## 14. Bước 4 — Kiểm tra & hoàn tất

Visual baseline dùng chung Word generic + Bảng tính; validator/fill semantics chuyên biệt. Severity `Blocking | Warning | Info`; chỉ hợp lệ khi Blocking=0. Layout: Header + stepper → Preview/Test fill + vùng/section → Kết quả kiểm tra + issue list → công cụ xử lý → footer. Vùng chưa thiết lập: `Gán dữ liệu / Bỏ qua có chủ đích / Đây là nội dung cố định`. Footer: `Quay lại | Lưu nháp | Chạy lại kiểm tra | Hợp lệ & Lưu template`. Không silent publish.

## 15. Kết quả thẩm định giá — immutable company forms

Bảng 1:

```text
STT | Tên tài sản | Đặc điểm kinh tế - kỹ thuật | ĐVT | SL
```

Bảng 2:

```text
STT | Tên tài sản | ĐVT | SL |
Đơn giá tham khảo: NCC1 | NCC2 | NCC3 |
Tổ TĐG đánh giá: Đơn giá | Thành tiền
```

Bảng 3:

```text
STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền
```

Giữ Tổng cộng, Làm tròn, số tiền bằng chữ. Không có Thành tiền NCC. Không đổi tên/thứ tự/split/merge/add analytics/cardize.

Rule hiện hành:

```text
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
→ phù hợp theo rule nghiệp vụ/tiêu chuẩn đang áp dụng trong VALORA
```

Cách xác định tập báo giá bắt buộc chưa được khóa thành min/max/every-quote; không tự suy diễn.

## 16. Microsoft 365 Document Workspace / Bộ tài liệu phát hành

### 16.1 Kiến trúc

VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status và release manifest. Microsoft 365/OneDrive/SharePoint/Word quản lý file/file version/Word. Preview Word cuộn trang liên tục; không fake Word editor.

Command bar: `Mở trong Word`, `Đồng bộ dữ liệu`, `Tạo phiên bản mới`, `So sánh`, `Khóa phiên bản`, `...`, `Phát hành bộ tài liệu`. Không có `Xuất PDF`.

Thư mục: `01_Hồ sơ gốc / 02_Tài liệu thẩm định / 03_Hợp đồng / 04_Báo giá nhà cung cấp / 05_Pháp lý`. Generated working document và signed scan là hai artifact khác nhau; signed scan thuộc `05_Pháp lý`.

### 16.2 03_Hợp đồng — Baseline Iteration 1

Bảng: `STT | Tên tài liệu | Loại tài liệu | Số/Ký hiệu | Trạng thái | Phiên bản | Cập nhật lần cuối | Tác vụ`. Primary CTA `Tạo tài liệu`; preview view-only; chỉnh sửa qua Word. Lifecycle `Bản nháp → Cần đồng bộ → Đã đồng bộ → Sẵn sàng phát hành → Đã phát hành`. Lineage `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version → signed scan 05_Pháp lý (nếu có)`.

### 16.3 Managed Regions — Báo cáo — Baseline Iteration 1

User-facing title: `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`.

```text
1. Xem danh sách vùng → 2. Xem nội dung hiện tại
→ 3. Xem khác biệt → 4. Chọn vùng cần cập nhật → Đồng bộ
```

Trạng thái: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`. Comparison: `Dữ liệu từ VALORA ↔ Nội dung đang có trong Word`. Không silent sync; narrative ngoài vùng giữ nguyên.

### 16.4 Managed Regions — Chứng thư — Baseline Iteration 1

User-facing title: `Quản lý nội dung do VALORA quản lý (Chứng thư thẩm định giá)`.

Mental model:

```text
1. Xem các nội dung VALORA quản lý
→ 2. Xem khác biệt
→ 3. Chọn nội dung cần cập nhật
→ 4. Đồng bộ vào Word
```

Chỉ managed regions user chọn mới được ghi. `Lưu lựa chọn` không đồng nghĩa sync. Narrative ngoài vùng giữ nguyên. Nếu user sửa trong managed region, hệ thống phải phát hiện khác biệt và cho xem/xử lý trước khi ghi; không silent overwrite.

### 16.5 Đồng bộ dữ liệu & Quản lý phiên bản — Baseline Iteration 1

```text
1. Xem những gì đã thay đổi → 2. Xem chi tiết khác biệt
→ 3. Chọn nội dung muốn cập nhật → 4. Cập nhật vào Word & tạo/ghi nhận phiên bản
```

Lineage giữ `Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version`. Revision đã phát hành không silent mutate.

### 16.6 Phát hành bộ tài liệu — Baseline Iteration 1

```text
1. Chọn tài liệu → 2. Kiểm tra tình trạng → 3. Xem bộ tài liệu
→ 4. Xác nhận phát hành → Khóa phiên bản đã phát hành
```

Trạng thái: `Sẵn sàng / Cần cập nhật / Chưa hoàn tất / Không áp dụng / Đã phát hành`. Chỉ tài liệu đủ điều kiện mới được chọn; package có Blocking thì primary publish CTA không khả dụng. Trước xác nhận cuối, user xem chính xác danh sách tài liệu + phiên bản. Freeze release manifest; release cũ immutable; sửa sau phát hành tạo revision/version và package mới. Không có `Xuất PDF`.

## 17. Validation phân tán

Không có màn Kiểm tra hồ sơ riêng. `Blocking` phải xử lý trước dependency; `Warning` nêu rủi ro nhưng có thể tiếp tục nếu rule cho phép; `Info` là trạng thái. S10 tổng hợp readiness; các issue hiển thị tại nơi phát sinh và có deep-link/Đi tới.

## 18. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept/auto-price/auto-apply.
- AI Template Assistant không silent accept/publish/overwrite.
- Raw source luôn truy vết được.
- Giá/chứng cứ không silent overwrite Đơn giá hiện hành.
- Cảnh báo giá NCC là Warning tại NCCQ; không tạo checkpoint riêng.
- STT immutable trong business dataset.
- Template báo giá chỉ `.docx`.
- Formula template không staticize; không đổi `MIN(E:G)`.
- Fill Engine luôn output file mới; không silent drop workbook feature.
- 03 bảng Kết quả thẩm định giá immutable.
- Generated Word và signed scan là hai artifact khác nhau.
- Managed Regions không silent sync/overwrite narrative ngoài vùng.
- Sync/version không bắt user hiểu ID kỹ thuật.
- Document Revision != Microsoft 365 file version trong domain.
- Không silent mutate revision/release đã phát hành.
- Publishing không silent publish/lock/mutate release hoặc tự thêm/bỏ tài liệu khỏi package.
- Vietnamese-first; không phơi HTTP/SQL/stack trace/row_version.
- Mỗi context/bước có một primary CTA.

## 19. Screen / capability inventory v2.3

| ID / Capability | Màn hình / Chức năng | Trạng thái v2.3 |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát + tạo file + chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | Tích hợp S02; không có màn riêng |
| S09 | Chuyển sang thẩm định chính thức | P0 — baseline |
| S10 | Tổng quan hồ sơ | P0 — dashboard điều phối |
| S11 | Xác nhận & điều chỉnh danh mục | P0 — baseline |
| S12 | Workbench tài sản | P0 — baseline |
| S13 | Asset Context Drawer | P0 — baseline; drawer trong S12 |
| NGC | Nguồn giá & Chứng cứ | P0 — baseline |
| NCCQ | Tạo & quản lý báo giá NCC | P0 — baseline Iteration 6 + inline price warnings |
| TM01 | Danh sách mẫu báo giá NCC | P0 — baseline Iteration 1 |
| TM03 | Upload & Mapping NCC | P0 — baseline Iteration 1 Word-only |
| TM04 | Preview/Test fill NCC | P0 — baseline Iteration 1 |
| NCCQ-child | Hoàn tất 01 báo giá NCC | P0 — baseline Iteration 3 |
| Result | Kết quả thẩm định giá | P0 — baseline Iteration 1; 03 bảng immutable |
| M365 | Bộ tài liệu phát hành | P0 — baseline; sync/version/lock/publish; không Xuất PDF |
| M365-03HĐ | 03_Hợp đồng — Danh sách & tạo tài liệu | P0 — baseline Iteration 1 |
| M365-MR-REPORT | Managed Regions — Báo cáo | P0 — baseline Iteration 1 |
| M365-MR-CERT | Managed Regions — Chứng thư | P0 — baseline Iteration 1 |
| M365-SYNC-VERSION | Đồng bộ dữ liệu & Quản lý phiên bản | P0 — baseline Iteration 1 |
| M365-PUBLISH | Phát hành bộ tài liệu | P0 — baseline Iteration 1; immutable release manifest |
| GTM | Quản lý mẫu tài liệu generic | P0 — baseline Iteration 1 |
| GWM | Mapping tài liệu Word generic | P0 — baseline Iteration 2 |
| GWR | Kiểm tra & hoàn tất Word generic | P0 — baseline Iteration 1 |
| AI-TPL-2 | AI phân tích & đề xuất | P0 — baseline Iteration 1 |
| AI-TPL-3 | Rà soát & chỉnh sửa | P0 — baseline Iteration 1 |
| Spreadsheet | Bảng tính template semantics | Design Authority |
| AI-TPL-4 | Kiểm tra & hoàn tất Word + Bảng tính | P0 — baseline Iteration 1 |
| XLS-FILL | Bảng tính Fill Engine — Implementation Contract v1 | **P0 — Baseline / Design Authority Iteration 1** |

## 20. Companion authority documents

- `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_CERTIFICATE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_PUBLISH_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SYNC_VERSION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_CONTRACT_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_REVIEW_EDIT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_FINAL_CHECK_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md`.
- `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 21. Trạng thái triển khai và hướng tiếp theo

Đây là thiết kế mục tiêu; design authority không đồng nghĩa đã implement.

Bảng tính authority hiện khóa xuyên suốt:

```text
Template semantics
→ AI-assisted mapping/review
→ Kiểm tra & hoàn tất
→ Fill Engine
→ Output + Manifest + Lineage
```

Hướng kỹ thuật tiếp theo nếu bắt đầu implementation: tách rõ UI/UX authority, domain contract và engine implementation; đánh giá ADR nếu thay đổi persistence/fill semantics, recalculation strategy, overwrite policy, workbook feature preservation hoặc version binding.

## 22. ADR

Việc nâng `Bảng tính Fill Engine — Implementation Contract v1 — Iteration 1` thành visual/design baseline là cập nhật UI/UX + domain contract authority, **không tự phát sinh ADR kỹ thuật mới**.

Nếu implementation làm thay đổi persistence, transaction boundary, formula/fill semantics, workbook feature preservation, output/version binding, Data Snapshot/Document Revision semantics hoặc immutable published revision/release thì cần đánh giá ADR riêng trước khi sửa product code.