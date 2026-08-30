# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Fluent 2, desktop-first, data-heavy workflow  
**Trạng thái:** Canonical master handoff — **Consolidation v2.3 lần 2 + AI-TPL-4 + 03_Hợp đồng + Managed Regions + Sync/Version Baseline**; không đồng nghĩa product code đã implement  
**Cập nhật:** 30/08/2026

> Master này consolidate authority v2.3 hiện hành, bao gồm Price & Evidence, Kết quả thẩm định giá, Microsoft 365 Document Workspace, Generic Template Management, Generic Word Mapping/Review, AI-assisted Template Setup cho Word + Bảng tính, baseline `03_Hợp đồng`, `Managed Regions — Báo cáo thẩm định giá` và `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1`. Addendum được giữ để truy vết. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành

Các baseline/authority đã khóa:

- S09 — Chuyển sang thẩm định chính thức.
- S10 — Tổng quan hồ sơ.
- S11 — Xác nhận & điều chỉnh danh mục triển khai.
- S12 — Workbench tài sản.
- S13 — Asset Context Drawer, drawer trong S12; không phải route/menu độc lập.
- Nguồn giá & Chứng cứ.
- NCCQ — Tạo & quản lý báo giá NCC — **Iteration 6**.
- TM01 — Danh sách mẫu báo giá NCC — **Iteration 1**.
- TM03 — Upload & Mapping template NCC — **Iteration 1 Word-only**.
- TM04 — Preview / Test fill template NCC — **Iteration 1**.
- NCCQ child — Hoàn tất 01 báo giá NCC — **Iteration 3**, scope 01 báo giá / 01 NCC.
- Kết quả thẩm định giá — **Iteration 1**, 03 bảng biểu mẫu công ty immutable.
- Microsoft 365 Document Workspace / Bộ tài liệu phát hành — baseline authority.
- **03_Hợp đồng — Danh sách & tạo tài liệu — Iteration 1 Baseline / Design Authority.**
- **Managed Regions — Báo cáo thẩm định giá — Iteration 1 Baseline / Design Authority.**
- **Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1 Baseline / Design Authority.**
- Quản lý mẫu tài liệu generic — **Iteration 1**.
- Mapping Template tài liệu generic Word — **Iteration 2**.
- Kiểm tra & hoàn tất template Word generic — **Iteration 1**.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — **Iteration 1**.
- Thiết lập mẫu tài liệu — Bước 3: Rà soát & chỉnh sửa — **Iteration 1**.
- Thiết lập mẫu tài liệu — Bước 4: Kiểm tra & hoàn tất dùng chung Word + Bảng tính — **Iteration 1 Baseline / Design Authority**.

Các rule supersession quan trọng:

- Không dùng S14 — So sánh & Xác nhận giá thẩm định chính thức.
- Không có màn hình Kiểm tra hồ sơ riêng.
- Không có workflow KSCL riêng trong single-user v2.3.
- Không có NCCQ aggregate trung gian sau `Chọn nhà cung cấp đã xác nhận giá`.
- `Hoàn tất 01 báo giá NCC` là child flow của NCCQ, không phải readiness toàn hồ sơ.
- `Bảng tính` là terminology nghiệp vụ chính thức cho template Excel; không dùng `Phụ lục Excel` làm domain term chính.
- `Thiết lập mẫu tài liệu` là mental model user-facing; Mapping vẫn tồn tại trong domain/engineering/audit.
- AI-assisted setup bổ sung Generic Word Mapping/Review, không override specialized authority của template Báo giá NCC.
- Bước 3 Rà soát & chỉnh sửa là checkpoint user-controlled; AI proposal không tự trở thành mapping chính thức.
- Bước 4 dùng shell/mental model chung nhưng validator/fill semantics chuyên biệt theo Word và Bảng tính.
- `03_Hợp đồng` quản lý working documents; signed scan thuộc `05_Pháp lý` và giữ lineage về tài liệu gốc.
- Managed Regions chỉ cập nhật các vùng do VALORA quản lý; nội dung ngoài vùng do người dùng biên tập trong Word không bị silent overwrite.
- Đồng bộ luôn explicit; người dùng xem thay đổi và chọn nội dung cần cập nhật trước khi ghi vào Word.
- Document Revision và Microsoft 365 file version là hai lớp lineage liên kết nhưng không đồng nhất.
- Revision đã phát hành không được silent mutate.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị; phương pháp so sánh.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định nghiệp vụ chính thức do người dùng.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Excel/Word/PDF có thể là artifact input/output tùy context; điều này không có nghĩa mọi module hỗ trợ cả ba định dạng.
- Template báo giá NCC chỉ dùng Microsoft Word `.docx`.
- Template generic có thể gồm Word `.docx` và Bảng tính `.xlsx/.xlsm` theo authority từng loại.
- Microsoft 365 quản lý file/version/Word ở bước tài liệu; VALORA quản lý structured business data, Data Snapshot, lineage, audit và sync status.
- Không xây fake Word editor trong VALORA.
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
   → Hoàn tất từng báo giá NCC (child flow)
   → Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
   → Bảng Đặc điểm kinh tế - kỹ thuật
   → Bảng Tổng hợp giá nhà cung cấp
   → Bảng Kết quả thẩm định giá
→ Microsoft 365 Document Workspace / Bộ tài liệu phát hành
   → 03_Hợp đồng — Danh sách & tạo tài liệu
   → Báo cáo/Chứng thư
      → Managed Regions
      → Đồng bộ dữ liệu & Quản lý phiên bản tài liệu
   → Mở trong Word
   → Khóa phiên bản
   → Phát hành
```

Không có checkpoint riêng: `Khai báo thông tin thực hiện`, `Xác nhận giá thẩm định chính thức`, `Kiểm tra hồ sơ`, `KSCL`.

Supporting configuration flow:

```text
Cấu hình
→ Mẫu tài liệu
→ Quản lý mẫu tài liệu
   → Tạo/chọn mẫu
   → AI phân tích & đề xuất
   → Rà soát & chỉnh sửa
   → Kiểm tra & hoàn tất
```

## 3. Pre-case

### 3.1 Quản lý yêu cầu sơ bộ

Trạng thái: `Mới tạo`, `Mới nhận danh mục`, `Đang phân tích`, `Sẵn sàng tạo kết quả sơ bộ`, `Đã tạo kết quả sơ bộ`, `Không tiếp tục`, `Đã chuyển thành hồ sơ`.

Không dùng: `Ghi nhận đã gửi`, `Chờ khách hàng phản hồi`, `Ghi nhận phản hồi`, `Đã chấp thuận giá đề xuất`.

S08 không có màn hình riêng; rà soát và tạo file kết quả sơ bộ tích hợp trong Quản lý yêu cầu sơ bộ.

File kết quả sơ bộ là bản sao Excel khách hàng, giữ cấu trúc nguồn tối đa và bổ sung đúng 02 cột:

```text
Đơn giá đề xuất | Thành tiền
```

Output có version/lineage; file nguồn không bị ghi đè.

### 3.2 Giá Pre-case

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

Không tạo file kết quả sơ bộ nếu còn dòng cần định giá mà chưa có mức giá do người dùng ấn định.

Mức giá tại thời điểm tạo file được ghi vào `Đơn giá đề xuất` và kế thừa làm giá khởi tạo khi chuyển chính thức.

## 4. Đơn giá hiện hành

Mỗi tài sản có một `Đơn giá hiện hành` tại từng thời điểm.

- Giá ban đầu có thể kế thừa từ Pre-case.
- Người dùng có thể sửa tại context được phép trong S12/S13/Nguồn giá & Chứng cứ hoặc bề mặt đã duyệt.
- Sau commit, giá mới trở thành Đơn giá hiện hành; giá cũ vẫn giữ history/lineage/audit.
- AI/Kho tri thức/rule engine/nguồn Internet/hồ sơ cũ/báo giá NCC không tự ghi đè.
- Giá sơ bộ Pre-case giữ riêng để truy vết/đối chiếu.
- Khi hồ sơ đã khóa/phát hành, quyền sửa tuân lifecycle/version; không có bypass trong v2.3.

## 5. Nguồn giá & Chứng cứ — Price & Evidence Authority

### 5.1 Thứ tự ưu tiên

1. **Giá khảo sát từ Internet**.
2. **Thuyết minh đơn giá**.
3. **Giá trong phần Kết quả thẩm định giá của hồ sơ cũ**.

`Tổng hợp căn cứ` là bề mặt tổng hợp, không phải nguồn thứ tư. `Kho tri thức` là cơ chế hỗ trợ tìm/gợi ý candidate và dữ liệu tham chiếu; không phải một nguồn giá ưu tiên độc lập ngang hàng với ba nguồn trên.

### 5.2 Nguồn Internet

Tối thiểu lưu: URL/định danh, giá tham khảo, ngày thu thập/cập nhật, trạng thái truy cập, snapshot/tài liệu, trạng thái rà soát. Nguồn mất truy cập vẫn giữ URL/snapshot/history nếu đã dùng.

### 5.3 Thuyết minh đơn giá

- Cho phép lập/chỉnh theo tài sản.
- Có version/history.
- Có thể là căn cứ duy nhất nếu người dùng chấp nhận và rule nghiệp vụ cho phép.
- Không tự sinh quyết định giá.

### 5.4 Hồ sơ cũ / Giá lịch sử

Trong phạm vi xác định giá thẩm định, giá hồ sơ cũ là **giá trong phần Kết quả thẩm định giá của hồ sơ cũ**, không mặc định là giá NCC trong báo giá cũ.

Hồ sơ cũ là first-class evidence, tối thiểu truy vết:

```text
Tài sản hiện tại → Hồ sơ cũ → Tài sản cũ → Hãng/Model
→ Thời điểm thẩm định → Giá trong phần Kết quả → Mức tương đồng → Tài liệu nguồn
```

Chọn hồ sơ cũ làm căn cứ tạo lineage nhưng không tự copy giá cũ thành Đơn giá hiện hành.

### 5.5 Quyết định giá

Người dùng quyết định Đơn giá hiện hành và Đơn giá trong Kết quả thẩm định giá. Nguồn/chứng cứ chỉ hỗ trợ quyết định và giải trình.

## 6. S09–S13

### S09 — Chuyển sang thẩm định chính thức

Điều kiện vào: Pre-case đã có file kết quả sơ bộ và người dùng chủ động chuyển. Tạo hồ sơ mới nhưng giữ lineage tới Pre-case, file nguồn, file kết quả, mapping snapshot, giá sơ bộ và chứng cứ đã dùng. Giá hiện hành Pre-case trở thành giá khởi tạo; không tạo checkpoint xác nhận lại giá.

### S10 — Tổng quan hồ sơ

S10 là dashboard điều phối, không phải form nhập liệu dài. S10 chỉ tổng hợp readiness; issue cụ thể hiển thị tại nơi phát sinh và có CTA `Đi tới`. Không khóa số lượng checkpoint bằng một con số cố định.

### S11 — Xác nhận & điều chỉnh danh mục triển khai

S11 chốt phạm vi tài sản, không chốt giá. Cho phép giữ nguyên, thêm mới, loại bớt, khôi phục; giữ lineage. STT gốc không bị renumber.

### S12 — Workbench tài sản

Desktop-first, data grid lớn; raw Excel và dữ liệu chuẩn hóa đặt cạnh nhau. Raw read-only và luôn truy vết được. Grid có thông số, trạng thái, Kho tri thức, nguồn giá, Đơn giá hiện hành và thao tác mở ngữ cảnh.

### S13 — Asset Context Drawer

Drawer bên phải mở từ S12; không có route/menu độc lập. Mở/đóng không làm mất filter, sort, pagination, selection hoặc scroll của S12. Tabs: `Tổng quan`, `Thông số kỹ thuật`, `Nguồn giá & Chứng cứ`, `Lịch sử`. Nguồn giá trong S13 chỉ là summary/deep-link.

## 7. NCCQ — Tạo & quản lý báo giá nhà cung cấp

### 7.1 Vai trò

Giá NCC **không phải nguồn chính để xác định Đơn giá thẩm định cuối cùng**. Giá NCC phục vụ tạo/tái tạo báo giá, theo dõi phản hồi/xác nhận, đối chiếu Kết quả thẩm định giá và evidence/lineage. NCCQ không tự thay Đơn giá hiện hành.

### 7.2 Baseline bảng

```text
STT | Tên tài sản | ĐVT | Số lượng |
NCC1 | NCC2 | NCC3 |
Đơn giá chọn | Thành tiền | Đơn giá hiện hành
```

Các cột NCC hiển thị số tiền trực tiếp. Semantic giá: `Giá lịch sử`; `Giá đề nghị — chờ NCC xác nhận`; `Đơn giá NCC đã xác nhận`.

### 7.3 Sinh báo giá nháp và dedupe

- Hệ thống sinh cấu trúc nháp trước; người dùng quyết định gộp/tách/chuyển.
- Cùng một NCC consolidate vào cùng báo giá hiện tại phù hợp.
- Không duplicate quote chỉ vì thiết bị đến từ hồ sơ lịch sử khác.
- Lineage giữ ở cấp dòng.
- STT immutable theo danh mục gốc.

### 7.4 Tài sản có lịch sử

Lấy đủ 03 giá NCC lịch sử để phục vụ tái tạo báo giá. Nếu giá NCC lịch sử khác Giá sơ bộ Pre-case, UI warning và hiển thị chênh lệch; không auto-change Đơn giá hiện hành.

### 7.5 Internet-only

Người dùng chọn 01 báo giá dùng Đơn giá hiện hành làm giá đề nghị. Hai báo giá còn lại có thể sinh:

```text
Đơn giá hiện hành <= Giá đề nghị <= Đơn giá hiện hành × 115%
```

Đây chỉ là `Giá đề nghị — chờ NCC xác nhận`.

### 7.6 Child flow — Hoàn tất 01 báo giá NCC

```text
Tạo báo giá nháp → Tạo file theo mẫu NCC → Gửi NCC xác nhận
→ Nhận phản hồi / file ký → Hoàn tất báo giá
```

Scope 01 báo giá / 01 NCC. `Hoàn tất báo giá` không tự sửa Đơn giá hiện hành, không tự chọn NCC và không tự hoàn tất hồ sơ.

### 7.7 Chọn nhà cung cấp đã xác nhận giá

Selection lưu theo `NCC → Báo giá → Dòng thiết bị → Đơn giá NCC đã xác nhận → File evidence ký/đóng dấu`. Việc chọn NCC không có nghĩa lấy giá NCC làm Đơn giá thẩm định cuối cùng. Sau CTA chuyển trực tiếp sang Kết quả thẩm định giá.

## 8. Template báo giá NCC — Word-only specialized authority

Flow:

```text
Cấu hình → Mẫu báo giá NCC → Tạo mẫu → Upload Word (.docx)
→ Mapping → Preview / Test fill → Lưu template → Sẵn sàng sử dụng
```

### TM01 — Danh sách mẫu
Baseline Iteration 1. Quản lý template theo NCC, trạng thái, version, mặc định; table-first.

### TM02 — Metadata
NCC, mã NCC, tên mẫu, mô tả, ngày hiệu lực, trạng thái, mẫu mặc định, file Word gốc.

### TM03 — Upload & Mapping
Baseline Iteration 1 Word-only. Hỗ trợ text/content control/placeholder, table, repeating row, cell/column. Mapping AI chỉ gợi ý; user xác nhận.

### TM04 — Preview / Test fill
Baseline Iteration 1. Kiểm tra field chưa map, repeating table, text overflow, format tiền/ngày, page break, footer, Blocking/Warning. Chỉ `Sẵn sàng sử dụng` khi không còn Blocking và user explicit hoàn tất.

### TM05 — Lịch sử phiên bản
Version, hiệu lực, mặc định; xem/nhân bản/khôi phục. Template/version đã dùng không silent overwrite.

## 9. Quản lý mẫu tài liệu generic — Template Management Authority

IA: `Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu`. `03_Hợp đồng` chỉ là contextual entry/filter.

Nhóm template:

```text
Tất cả
Hợp đồng & hồ sơ liên quan
Báo cáo thẩm định giá
Chứng thư thẩm định giá
Bảng tính
Báo giá nhà cung cấp
```

`Bảng tính` là terminology chính thức. Danh sách quản lý table-first:

```text
Loại tài liệu | Tên mẫu | Định dạng | Phiên bản | Mặc định |
Trạng thái | Cập nhật gần nhất | Người cập nhật | Thao tác
```

Word `.docx` và Bảng tính `.xlsx/.xlsm` có thể cùng quản lý metadata/lifecycle. Báo giá NCC vẫn `.docx` only.

## 10. Thiết lập mẫu tài liệu — AI Template Assistant Authority

User-facing term: **Thiết lập mẫu tài liệu**.

```text
1. Chọn mẫu → 2. AI phân tích & đề xuất → 3. Rà soát & chỉnh sửa → 4. Kiểm tra & hoàn tất
```

Áp dụng Word generic và Bảng tính, analyzer/renderer/fill semantics tách theo format. AI có thể phân tích cấu trúc, nhận diện field/vùng/bảng/dòng lặp/section/formula/evidence, đề xuất mapping, giải thích, highlight, test fill, phát hiện lỗi và đề xuất sửa. Confidence: `Tin cậy cao / Cần xác nhận / Chưa xác định`.

AI không tự đổi cấu trúc biểu mẫu công ty, cột chính thức, merge, formula; không publish, silent accept mapping, overwrite Template Version hoặc promote custom field thành canonical field.

## 11. Bước 3 — Rà soát & chỉnh sửa — Baseline Iteration 1

Bước 3 là checkpoint user-controlled. Preview là vùng lớn nhất; panel mapping có summary/search/filter/group/focus. Trạng thái:

```text
Đã mapping | Cần xác nhận | Chưa mapping | Đã bỏ qua
```

Action: `Giữ nguyên / Xác nhận`, `Đổi gán dữ liệu`, `Không dùng vùng này`. Với formula ưu tiên giữ công thức từ mẫu.

Người dùng luôn có thể bổ sung field AI bỏ sót theo cả hai hướng `vị trí → dữ liệu → gán` hoặc `dữ liệu → vị trí → gán`. Nếu không có field chuẩn, cho phép `Tạo trường tùy chỉnh`; custom field không tự thành canonical business field.

Navigation: `Quay lại Bước 2 | Lưu nháp | Tiếp tục: Kiểm tra & hoàn tất`.

## 12. Generic Word Mapping & Review Authority

Mental model:

```text
Chọn mẫu Word → Chọn dữ liệu nghiệp vụ → Click vị trí cần điền trong Word
→ VALORA tạo mapping phía sau → Kiểm tra & hoàn tất
```

UI không bắt user hiểu Region ID/source path/collection path/Content Control kỹ thuật. Sync policy user-facing: `Tự cập nhật khi dữ liệu thay đổi / Chỉ điền lần đầu / Người dùng tự chỉnh trong Word`. Preview không phải Word editor.

Validation dùng `Blocking / Warning / Info`; vùng chưa thiết lập có `Gán dữ liệu / Bỏ qua có chủ đích / Đây là nội dung cố định`. Chỉ hợp lệ khi không còn Blocking.

## 13. Bảng tính — Format-specific Authority

Bảng tính không áp Word region semantics máy móc. Analyzer nhận diện workbook/sheet/used range/header nhiều tầng/merge/section/repeating row/cột/formula/tổng/format/ảnh/evidence/page layout/hidden/named range. Mapping ưu tiên vùng/cột/dòng mẫu.

Reference `Bang Tinh - HĐ 42.xlsx` khóa:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

Engine giữ formula, không staticize/đổi rule; khi nhân dòng cập nhật relative refs và tổng/làm tròn. Không silent mất merge/style/border/number format/image/evidence/page layout/named range/data validation/conditional formatting/macro; validation phải cảnh báo nếu không bảo toàn.

## 14. Bước 4 — Kiểm tra & hoàn tất — Baseline Iteration 1

Visual baseline dùng chung Word generic + Bảng tính; validator/fill semantics chuyên biệt theo format. Severity `Blocking | Warning | Info`; chỉ hợp lệ khi Blocking = 0.

Layout:

```text
Header + stepper 4 bước
→ Preview/Test fill + danh sách vùng/section
→ Kết quả kiểm tra + issue list
→ Công cụ xử lý issue
→ Footer actions
```

Vùng chưa thiết lập: `Gán dữ liệu / Bỏ qua có chủ đích / Đây là nội dung cố định`. Word validation kiểm tra mapping/region, repeating row, overflow, page break, header/footer, format. Spreadsheet validation kiểm tra workbook/sheet/range, header/merge/repeating row, formula/relative refs, tổng/làm tròn, style/format, evidence/image, print/page layout và workbook features.

Footer: `Quay lại | Lưu nháp | Chạy lại kiểm tra | Hợp lệ & Lưu template`. Không silent publish.

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

Không có cột Thành tiền NCC.

Bảng 3:

```text
STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền
```

Giữ `Tổng cộng`, `Làm tròn`, số tiền bằng chữ.

Rule:

```text
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
→ phù hợp theo rule nghiệp vụ/tiêu chuẩn đang áp dụng trong VALORA
```

Cách xác định tập báo giá bắt buộc dùng để đối chiếu chưa được khóa thành min/max/every-quote; không tự suy diễn. Ba bảng là immutable layout; Fluent 2 chỉ áp dụng ngoài biểu mẫu.

## 16. Microsoft 365 Document Workspace / Bộ tài liệu phát hành

### 16.1 Kiến trúc

VALORA quản lý structured business data, Data Snapshot, lineage, audit và sync status. Microsoft 365/OneDrive/SharePoint/Word quản lý file và file version. Không xây Word editor giả. Preview Word cuộn trang liên tục.

### 16.2 Command bar

`Mở trong Word`; `Đồng bộ dữ liệu`; `Tạo phiên bản mới`; `So sánh`; `Khóa phiên bản`; `...`; `Phát hành bộ tài liệu`. **Không có `Xuất PDF` trong baseline.**

### 16.3 Cấu trúc thư mục

```text
01_Hồ sơ gốc
02_Tài liệu thẩm định
03_Hợp đồng
04_Báo giá nhà cung cấp
05_Pháp lý
```

File Word generated và signed scan là hai artifact khác nhau. Signed scan/chứng từ ký thuộc `05_Pháp lý`.

### 16.4 03_Hợp đồng — Danh sách & tạo tài liệu — Baseline Iteration 1

Workspace quản lý working documents vòng đời hợp đồng; không thay Generic Template Management và không phải Word editor. Bảng:

```text
STT | Tên tài liệu | Loại tài liệu | Số / Ký hiệu |
Trạng thái | Phiên bản | Cập nhật lần cuối | Tác vụ
```

Primary CTA `Tạo tài liệu`. Preview view-only; chỉnh sửa qua `Mở trong Word`.

Lineage:

```text
Template Version → Data Snapshot → Document Revision
→ Microsoft 365 file / file version → Bản scan ký 05_Pháp lý (nếu có)
```

Lifecycle:

```text
Bản nháp → Cần đồng bộ → Đã đồng bộ → Sẵn sàng phát hành → Đã phát hành
```

`Chưa tạo` chỉ là planning state trước artifact. Không silent overwrite Template Version đã dùng hoặc mutate revision đã phát hành.

### 16.5 File scan / pháp lý

Người dùng tự drag/drop, upload hoặc move file vào `05_Pháp lý`. Không có checkpoint bắt buộc `Xác nhận đã ký/Ghi nhận pháp lý/Đã nhận bản ký`.

### 16.6 Sync/version domain boundary

Phân biệt `VALORA Data Snapshot`, `Document Revision`, `Microsoft 365 DriveItem/file version`. Khi dữ liệu VALORA thay đổi, document chuyển `Cần đồng bộ`, cho xem thay đổi, chỉ update managed regions và không overwrite narrative. Khi phát hành: freeze Revision + Snapshot + artifact/version state.

### 16.7 Managed Regions — Báo cáo thẩm định giá — Baseline Iteration 1

Managed Regions là lớp đồng bộ structured data từ VALORA vào vùng hệ thống quản lý trong Báo cáo thẩm định giá. User-facing title ưu tiên `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`.

Flow:

```text
1. Xem danh sách vùng
→ 2. Xem nội dung hiện tại
→ 3. Xem khác biệt (nếu có)
→ 4. Chọn vùng cần cập nhật
→ Đồng bộ
```

Layout: danh sách vùng bên trái → preview Word ở giữa → comparison bên phải → footer status/action. Trạng thái: `Đã đồng bộ / Cần đồng bộ / Bạn tự chỉnh trong Word / Lỗi`.

Comparison: `Dữ liệu từ VALORA ↔ Dữ liệu đang có trong Word`. Action: `Cập nhật vào Word / Giữ nguyên trong Word / Bỏ qua vùng này lần này`. Không silent sync. Baseline áp dụng trực tiếp cho Báo cáo; Chứng thư chưa tự thành visual baseline riêng.

### 16.8 Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Baseline Iteration 1

Baseline này đặc tả UX khi dữ liệu VALORA đã thay đổi sau khi tài liệu Word tồn tại. Mental model user-facing tránh thuật ngữ IT; ưu tiên `Dữ liệu mới`, `Nội dung hiện tại`, `Phiên bản tài liệu`, `Cần cập nhật`, `Cập nhật vào Word`.

Flow baseline:

```text
1. Xem những gì đã thay đổi
→ 2. Xem chi tiết khác biệt
→ 3. Chọn nội dung muốn cập nhật
→ 4. Cập nhật vào Word & tạo/ghi nhận phiên bản
```

Màn hình gồm header/trạng thái tài liệu, quy trình 4 bước, danh sách vùng thay đổi, preview Word, panel tóm tắt khác biệt, dữ liệu VALORA mới nhất, lịch sử phiên bản và footer actions.

Tài liệu hiển thị `Cần cập nhật` khi dữ liệu VALORA mới hơn dữ liệu đã đồng bộ và có khác biệt có thể truy vết. Mỗi vùng có thể dùng mức thay đổi:

```text
Thay đổi nhiều
Thay đổi một phần
Thay đổi nhỏ
Không thay đổi
```

Người dùng chọn từng vùng hoặc tất cả vùng cần cập nhật và có thể xem chi tiết trước khi quyết định. Chỉ managed regions được chọn mới được ghi. Nội dung ngoài vùng và narrative do user chỉnh trong Word giữ nguyên.

Nếu user đã sửa bên trong managed region, hệ thống phải phát hiện khác biệt và đưa vào bước xem/xử lý xung đột; không silent overwrite.

Lineage tiếp tục:

```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```

User-facing có thể hiển thị phiên bản như `rev0`, `rev1`, `rev2`; lịch sử tối thiểu có phiên bản, thời điểm, người thao tác, trạng thái đồng bộ. Trong domain, Document Revision không đồng nhất Microsoft 365 file version.

Khi sync thành công phải ghi nhận Data Snapshot dùng cho lần sync, Document Revision và Microsoft 365 file/version liên quan. Revision đã phát hành không silent mutate.

Action baseline: `Mở trong Word`, `Cập nhật vào Word`, `Xem chi tiết`, `Chọn tất cả/Bỏ chọn tất cả`, `Lưu nháp lựa chọn`, `Tiếp tục`, `Xem tất cả phiên bản`. Mỗi bước chỉ có một primary CTA nổi bật.

Companion authority: `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SYNC_VERSION_BASELINE_ADDENDUM.md`.

## 17. Validation phân tán

Không có màn Kiểm tra hồ sơ riêng. `Blocking` phải xử lý trước dependency; `Warning` nêu rủi ro nhưng có thể tiếp tục; `Info` là trạng thái. S10 chỉ tổng hợp readiness. Blocking đặt tại dependency thực tế như thiếu giá, thiếu dữ liệu bắt buộc, template còn Blocking, báo giá chưa đủ điều kiện, managed regions chưa đồng bộ hoặc sync/version conflict chưa xử lý.

## 18. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price, auto-apply.
- AI Template Assistant không silent accept mapping, publish hoặc overwrite template/version.
- User luôn có quyền bổ sung field AI bỏ sót, sửa/xóa mapping AI.
- Raw Excel/source luôn truy vết được.
- Giá/chứng cứ không silent overwrite Đơn giá hiện hành.
- Mỗi thay đổi giá giữ history/lineage/audit.
- STT immutable trong business dataset.
- Template báo giá chỉ `.docx`.
- Formula template không biến thành static mapping; AI không đổi `MIN(E:G)`.
- 03 bảng Kết quả thẩm định giá immutable.
- Generated Word và signed scan là hai artifact khác nhau.
- Managed Regions không silent sync, không overwrite narrative ngoài vùng và phải cho xem khác biệt trước khi ghi đè dữ liệu trong vùng.
- Sync/version không bắt user hiểu Snapshot/Revision/DriveItem ID.
- Document Revision và Microsoft 365 file version không bị đồng nhất trong domain.
- Không silent mutate revision đã phát hành.
- Vietnamese-first; không phơi HTTP/SQL/stack trace/row_version.
- Mỗi context có một primary CTA.

## 19. Screen / capability inventory v2.3

| ID / Capability | Màn hình / Chức năng | Trạng thái v2.3 |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát tích hợp + tạo file kết quả + CTA chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | Không có màn riêng; tích hợp S02 |
| S09 | Chuyển sang thẩm định chính thức | P0 — baseline |
| S10 | Tổng quan hồ sơ | P0 — dashboard điều phối |
| S11 | Xác nhận & điều chỉnh danh mục triển khai | P0 — baseline |
| S12 | Workbench tài sản | P0 — baseline |
| S13 | Asset Context Drawer | P0 — baseline; drawer trong S12 |
| NGC | Nguồn giá & Chứng cứ | P0 — baseline |
| NCCQ | Tạo & quản lý báo giá NCC | P0 — baseline Iteration 6 |
| TM01 | Danh sách mẫu báo giá NCC | P0 — baseline Iteration 1 |
| TM02 | Tạo/chỉnh metadata mẫu NCC | P0 — IA/capability |
| TM03 | Upload & Mapping NCC | P0 — baseline Iteration 1 Word-only |
| TM04 | Preview / Test fill NCC | P0 — baseline Iteration 1 |
| TM05 | Lịch sử phiên bản template NCC | P0 — IA/capability |
| S14 | So sánh & Xác nhận giá | Không dùng |
| S15 | Kiểm tra hồ sơ | Không dùng; validation phân tán |
| S16 | KSCL Checklist | Không dùng trong workflow single-user v2.3 |
| NCCQ-child | Hoàn tất 01 báo giá NCC | P0 — baseline Iteration 3; scope 01 báo giá / 01 NCC |
| Result | Kết quả thẩm định giá | P0 — baseline Iteration 1; 03 bảng immutable |
| M365 | Bộ tài liệu phát hành | P0 — baseline; sync/version/lock/publish; không Xuất PDF |
| M365-03HĐ | 03_Hợp đồng — Danh sách & tạo tài liệu | P0 — baseline Iteration 1 |
| M365-MR-REPORT | Managed Regions — Báo cáo thẩm định giá | P0 — baseline Iteration 1; user-friendly compare + explicit sync |
| M365-SYNC-VERSION | Đồng bộ dữ liệu & Quản lý phiên bản tài liệu | P0 — baseline Iteration 1; change review + selective sync + version history |
| GTM | Quản lý mẫu tài liệu generic | P0 — baseline Iteration 1 |
| GWM | Mapping tài liệu Word generic | P0 — baseline Iteration 2 |
| GWR | Kiểm tra & hoàn tất template Word generic | P0 — baseline Iteration 1 |
| AI-TPL-2 | AI phân tích & đề xuất | P0 — baseline Iteration 1 |
| AI-TPL-3 | Rà soát & chỉnh sửa | P0 — baseline Iteration 1 |
| Spreadsheet | Bảng tính template semantics | Design Authority — format-specific mapping/fill guardrails |
| AI-TPL-4 | Kiểm tra & hoàn tất Word + Bảng tính | P0 — baseline Iteration 1 |

## 20. Companion authority documents

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
- `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow support, không override master.

## 21. Trạng thái triển khai và hướng tiếp theo

Đây là thiết kế mục tiêu. Không suy diễn design authority = chức năng đã implement.

Authority đã khóa xuyên suốt:

```text
Pre-case
→ Official appraisal workflow
→ Price/Evidence
→ NCC quotation evidence
→ Final Result
→ Document Workspace
   → 03_Hợp đồng
   → Managed Regions — Báo cáo thẩm định giá
   → Đồng bộ dữ liệu & Quản lý phiên bản tài liệu
→ Generic Template Management
→ AI-assisted Template Setup
```

Hướng thiết kế tiếp theo ưu tiên:

1. Phát hành bộ tài liệu;
2. áp dụng/thiết kế interaction model Managed Regions cho Chứng thư thẩm định giá;
3. đặc tả dependency/rule engine cho đối chiếu `Đơn giá Kết quả <= Đơn giá báo giá NCC` mà không tự suy diễn tập báo giá bắt buộc;
4. implementation contract riêng cho Excel/Bảng tính Fill Engine nếu bắt đầu triển khai.

## 22. ADR

Việc nâng `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1` thành visual/design baseline là cập nhật UI/UX authority, **không phát sinh ADR kỹ thuật mới**.

Nếu triển khai làm thay đổi domain contract, Document Data Model, version/sync boundary, Data Snapshot persistence, Document Revision semantics, Microsoft 365 file-version mapping, conflict detection, managed-region sync hoặc immutable published revision, cần đánh giá ADR riêng trước khi sửa product code.
