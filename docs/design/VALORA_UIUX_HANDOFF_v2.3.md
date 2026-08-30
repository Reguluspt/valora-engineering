# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Fluent 2, desktop-first, data-heavy workflow  
**Trạng thái:** Canonical master handoff — **Consolidation v2.3 lần 2 + AI-TPL-4 + 03_Hợp đồng + Managed Regions Baseline**; không đồng nghĩa product code đã implement  
**Cập nhật:** 30/08/2026

> Master này đã consolidate toàn bộ authority v2.3 hiện hành, bao gồm Price & Evidence, Kết quả thẩm định giá, Microsoft 365 Document Workspace, Generic Template Management, Generic Word Mapping/Review, AI-assisted Template Setup cho Word + Bảng tính, visual baseline dùng chung Bước 4 — Kiểm tra & hoàn tất, baseline `03_Hợp đồng — Danh sách & tạo tài liệu` và baseline `Managed Regions — Báo cáo thẩm định giá — Iteration 1`. Các addendum vẫn được giữ để truy vết quyết định/visual authority. Khi có xung đột, quyết định explicit mới hơn thắng trong đúng scope.

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
- Đồng bộ Managed Regions luôn là thao tác explicit; nếu có khác biệt hoặc người dùng đã sửa trong vùng, UI phải cho người dùng xem và chọn cách xử lý trước khi ghi dữ liệu.

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
   → tạo/quản lý Word
   → Mở trong Word
   → Đồng bộ dữ liệu
   → versioning
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

Nguồn giá/chứng cứ được ưu tiên theo thứ tự nghiệp vụ:

1. **Giá khảo sát từ Internet**.
2. **Thuyết minh đơn giá**.
3. **Giá trong phần Kết quả thẩm định giá của hồ sơ cũ**.

`Tổng hợp căn cứ` là bề mặt tổng hợp, không phải nguồn thứ tư.

`Kho tri thức` là cơ chế hỗ trợ tìm/gợi ý candidate và dữ liệu tham chiếu; không phải một nguồn giá ưu tiên độc lập ngang hàng với ba nguồn trên.

### 5.2 Nguồn Internet

Tối thiểu lưu: URL/định danh, giá tham khảo, ngày thu thập/cập nhật, trạng thái truy cập, snapshot/tài liệu, trạng thái rà soát. Nguồn mất truy cập vẫn giữ URL/snapshot/history nếu đã dùng.

### 5.3 Thuyết minh đơn giá

- Cho phép lập/chỉnh theo tài sản.
- Có version/history.
- Có thể là căn cứ duy nhất nếu người dùng chấp nhận và rule nghiệp vụ cho phép.
- Không tự sinh quyết định giá.

### 5.4 Hồ sơ cũ / Giá lịch sử

Trong phạm vi xác định giá thẩm định, giá hồ sơ cũ được hiểu là **giá trong phần Kết quả thẩm định giá của hồ sơ cũ**, không mặc định là giá NCC trong báo giá cũ.

Hồ sơ cũ là first-class evidence, tối thiểu phải truy vết:

```text
Tài sản hiện tại
→ Hồ sơ cũ
→ Tài sản cũ
→ Hãng/Model
→ Thời điểm thẩm định
→ Giá trong phần Kết quả
→ Mức tương đồng
→ Tài liệu nguồn
```

Chọn hồ sơ cũ làm căn cứ tạo lineage nhưng không tự copy giá cũ thành Đơn giá hiện hành.

### 5.5 Quyết định giá

Người dùng là người quyết định Đơn giá hiện hành và Đơn giá trong Kết quả thẩm định giá. Nguồn/chứng cứ chỉ hỗ trợ quyết định và giải trình.

## 6. S09–S13

### S09 — Chuyển sang thẩm định chính thức

Điều kiện vào: Pre-case đã có file kết quả sơ bộ và người dùng chủ động chuyển.

Tạo hồ sơ mới nhưng giữ lineage tới Pre-case, file nguồn, file kết quả, mapping snapshot, giá sơ bộ và chứng cứ đã dùng. Giá hiện hành Pre-case trở thành giá khởi tạo; không tạo checkpoint xác nhận lại giá.

### S10 — Tổng quan hồ sơ

S10 là dashboard điều phối, không phải form nhập liệu dài. S10 chỉ tổng hợp readiness; issue cụ thể hiển thị tại nơi phát sinh và có CTA `Đi tới`.

**Không khóa số lượng checkpoint bằng một con số cố định**; dashboard phản ánh workflow hiện hành trong §2.

### S11 — Xác nhận & điều chỉnh danh mục triển khai

S11 chốt phạm vi tài sản, không chốt giá. Cho phép giữ nguyên, thêm mới, loại bớt, khôi phục; giữ lineage. STT gốc không bị renumber.

### S12 — Workbench tài sản

Desktop-first, data grid lớn; raw Excel và dữ liệu chuẩn hóa đặt cạnh nhau. Raw read-only và luôn truy vết được. Grid có thông số, trạng thái, Kho tri thức, nguồn giá, Đơn giá hiện hành và thao tác mở ngữ cảnh.

### S13 — Asset Context Drawer

Drawer bên phải mở từ S12; không có route/menu độc lập. Mở/đóng không làm mất filter, sort, pagination, selection hoặc scroll của S12.

Tabs: `Tổng quan`, `Thông số kỹ thuật`, `Nguồn giá & Chứng cứ`, `Lịch sử`.

Nguồn giá trong S13 chỉ là summary/deep-link; không nhân bản full checkpoint Nguồn giá & Chứng cứ.

## 7. NCCQ — Tạo & quản lý báo giá nhà cung cấp

### 7.1 Vai trò

Giá của các nhà cung cấp **không phải nguồn chính để xác định Đơn giá thẩm định cuối cùng**.

Giá NCC phục vụ:

1. tạo/tái tạo báo giá NCC;
2. theo dõi phản hồi/xác nhận;
3. làm dữ liệu đối chiếu cho Kết quả thẩm định giá;
4. lưu evidence/lineage.

NCCQ không tự thay Đơn giá hiện hành.

### 7.2 Baseline bảng

```text
STT | Tên tài sản | ĐVT | Số lượng |
NCC1 | NCC2 | NCC3 |
Đơn giá chọn | Thành tiền | Đơn giá hiện hành
```

Các cột NCC hiển thị số tiền trực tiếp.

Semantic giá:

- `Giá lịch sử`;
- `Giá đề nghị — chờ NCC xác nhận`;
- `Đơn giá NCC đã xác nhận`.

### 7.3 Sinh báo giá nháp và dedupe

- Hệ thống sinh cấu trúc nháp trước; người dùng quyết định gộp/tách/chuyển.
- Cùng một NCC phải consolidate vào cùng báo giá hiện tại phù hợp.
- Không tạo duplicate quote chỉ vì thiết bị đến từ hồ sơ lịch sử khác.
- Lineage giữ ở cấp dòng.
- STT immutable theo danh mục gốc; sort/group/gộp/tách/chuyển không renumber.

### 7.4 Tài sản có lịch sử

- Lấy đủ 03 giá NCC lịch sử để phục vụ tái tạo báo giá.
- Nếu giá NCC lịch sử khác Giá sơ bộ Pre-case dù rất nhỏ, UI warning; hiển thị giá sơ bộ, giá NCC, chênh tiền, chênh %.
- Không auto-change Đơn giá hiện hành.

### 7.5 Internet-only

Người dùng chọn 01 báo giá dùng Đơn giá hiện hành làm giá đề nghị. Hai báo giá còn lại có thể sinh:

```text
Đơn giá hiện hành <= Giá đề nghị <= Đơn giá hiện hành × 115%
```

Giá này chỉ là `Giá đề nghị — chờ NCC xác nhận`; không phải giá xác nhận.

### 7.6 Child flow — Hoàn tất 01 báo giá NCC

Scope: 01 báo giá / 01 NCC.

```text
Tạo báo giá nháp
→ Tạo file theo mẫu NCC
→ Gửi NCC xác nhận
→ Nhận phản hồi / file ký
→ Hoàn tất báo giá
```

Readiness chỉ của báo giá hiện tại; không hiển thị readiness 3/3 NCC hay toàn hồ sơ.

`Hoàn tất báo giá` không tự sửa Đơn giá hiện hành, không tự chọn NCC và không tự hoàn tất hồ sơ.

### 7.7 Chọn nhà cung cấp đã xác nhận giá

Selection lưu theo:

```text
NCC
→ Báo giá
→ Dòng thiết bị
→ Đơn giá NCC đã xác nhận
→ File evidence ký/đóng dấu
```

Việc chọn NCC **không có nghĩa** lấy giá NCC làm Đơn giá thẩm định cuối cùng.

Sau CTA này chuyển trực tiếp sang Kết quả thẩm định giá; không có NCCQ aggregate trung gian.

## 8. Template báo giá NCC — Word-only specialized authority

Flow:

```text
Cấu hình
→ Mẫu báo giá NCC
→ Tạo mẫu
→ Upload Word (.docx)
→ Mapping
→ Preview / Test fill
→ Lưu template
→ Sẵn sàng sử dụng
```

### TM01 — Danh sách mẫu

Baseline Iteration 1. Quản lý template theo NCC, trạng thái, version, mặc định; table-first.

### TM02 — Metadata

IA/capability: NCC, mã NCC, tên mẫu, mô tả, ngày hiệu lực, trạng thái, mẫu mặc định, file Word gốc.

### TM03 — Upload & Mapping

Baseline Iteration 1 Word-only. Hỗ trợ text/content control/placeholder, table, repeating row, cell/column. Có mapping nhanh gợi ý nhưng người dùng xác nhận; mapping thủ công được hỗ trợ.

Không dùng semantics Excel sheet/cell/range cho template Word.

### TM04 — Preview / Test fill

Baseline Iteration 1. Kiểm tra dữ liệu test, preview Word đã fill và validation:

- field chưa map;
- repeating table;
- text overflow;
- format tiền/ngày;
- page break;
- footer;
- Blocking/Warning.

Chỉ `Sẵn sàng sử dụng` khi không còn Blocking và người dùng thực hiện thao tác explicit.

### TM05 — Lịch sử phiên bản

IA/capability: version, hiệu lực, mặc định; xem/nhân bản/khôi phục theo lifecycle.

Template gốc/version đã dùng không silent overwrite.

## 9. Quản lý mẫu tài liệu generic — Template Management Authority

### 9.1 IA

```text
Cấu hình
→ Mẫu tài liệu
→ Quản lý mẫu tài liệu
```

`03_Hợp đồng` chỉ là contextual entry/filter cho `Hợp đồng & hồ sơ liên quan`, không sở hữu toàn bộ template system.

### 9.2 Nhóm template

```text
Tất cả
Hợp đồng & hồ sơ liên quan
Báo cáo thẩm định giá
Chứng thư thẩm định giá
Bảng tính
Báo giá nhà cung cấp
```

`Bảng tính` là terminology chính thức cho nhóm Excel trong UI.

Các subcategory hợp đồng tối thiểu: Phiếu/Giấy yêu cầu, Danh mục, Thương thảo, Dự thảo HĐ, Hợp đồng, Phụ lục hợp đồng, Nghiệm thu, Thanh lý, Tài liệu HĐ khác.

### 9.3 Danh sách quản lý

Desktop-first, Fluent 2, table-first. Cột chính:

```text
Loại tài liệu | Tên mẫu | Định dạng | Phiên bản | Mặc định |
Trạng thái | Cập nhật gần nhất | Người cập nhật | Thao tác
```

Action: xem; chỉnh thiết lập/mapping; tạo phiên bản mới; nhân bản; đặt mặc định; ngưng sử dụng; lịch sử phiên bản.

Word `.docx` và Bảng tính `.xlsx/.xlsm` có thể cùng được quản lý metadata/lifecycle. Báo giá NCC vẫn `.docx` only.

## 10. Thiết lập mẫu tài liệu — AI Template Assistant Authority

### 10.1 Mental model và flow

User-facing term ưu tiên: **Thiết lập mẫu tài liệu**.

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

Áp dụng cho Word generic và Bảng tính, nhưng analyzer/renderer/fill semantics tách theo format.

### 10.2 AI được phép làm

AI có thể:

- phân tích cấu trúc template;
- nhận diện field/vùng/bảng/dòng lặp/section/formula/evidence;
- đề xuất dữ liệu VALORA tương ứng;
- giải thích `Vì sao AI đề xuất?`;
- highlight vị trí trong preview;
- phát hiện vùng chưa thiết lập;
- chạy test fill/validation;
- phát hiện lỗi/rủi ro layout/công thức;
- đề xuất cách sửa.

Confidence hiển thị bằng ngôn ngữ nghiệp vụ:

```text
Tin cậy cao
Cần xác nhận
Chưa xác định
```

Không dùng raw score kỹ thuật như mental model chính.

### 10.3 AI guardrails

AI không được tự:

- đổi cấu trúc biểu mẫu công ty;
- thêm/bớt/đổi thứ tự cột chính thức;
- xóa merge;
- đổi template formula;
- thay template formula bằng business rule khác;
- sửa narrative Word thành quyết định chính thức;
- publish template;
- silent accept mapping;
- overwrite Template Version đang được sử dụng;
- silently promote custom field thành canonical domain field.

## 11. Bước 3 — Rà soát & chỉnh sửa — Baseline Iteration 1

Bước 3 là checkpoint **user-controlled** cho mapping.

### 11.1 Layout

Preview tài liệu/Bảng tính là vùng lớn nhất. Panel mapping bên phải có summary, search/filter, grouping và focus/highlight vị trí. Inspector vùng đang chọn hiển thị loại vùng, nội dung/công thức, dữ liệu đang gán, trạng thái, giải thích AI và thao tác.

### 11.2 Mapping status

```text
Đã mapping
Cần xác nhận
Chưa mapping
Đã bỏ qua
```

- `Đã mapping`: AI tin cậy cao hoặc user đã xác nhận/gán.
- `Cần xác nhận`: AI có đề xuất nhưng user cần kiểm tra.
- `Chưa mapping`: vùng có khả năng cần dữ liệu nhưng chưa có mapping.
- `Đã bỏ qua`: user explicit xác nhận không dùng mapping; không do AI tự bỏ qua.

### 11.3 Action vùng đang chọn

Tối thiểu:

```text
Giữ nguyên / Xác nhận
Đổi gán dữ liệu
Không dùng vùng này
```

Với vùng công thức, ưu tiên `Giữ công thức từ mẫu`, không ép gán source field.

### 11.4 Bổ sung trường AI bỏ sót — mandatory

Người dùng luôn có thể:

```text
Chọn vị trí trước → Chọn dữ liệu VALORA → Gán
```

hoặc:

```text
Chọn dữ liệu trước → Chọn vị trí → Gán
```

Nếu field chuẩn đã tồn tại trong Document Data Model, user có thể mapping thủ công.

Nếu không có field phù hợp, cho phép `Tạo trường tùy chỉnh` nhưng phải phân biệt:

```text
Trường chuẩn VALORA
Trường tùy chỉnh của template
```

Custom field không tự trở thành canonical business field toàn hệ thống.

### 11.5 Navigation/persistence

```text
Quay lại Bước 2 | Lưu nháp | Tiếp tục: Kiểm tra & hoàn tất
```

Navigation/lưu nháp không làm mất thay đổi mapping. Bước 3 không publish template.

## 12. Generic Word Mapping & Review Authority

### 12.1 Word mapping mental model

```text
Chọn mẫu Word
→ Chọn dữ liệu nghiệp vụ
→ Click vị trí cần điền trong Word
→ VALORA tạo mapping phía sau
→ Kiểm tra & hoàn tất
```

AI-assisted flow có thể pre-analyze trước, nhưng người dùng vẫn có thể map thủ công.

UI không bắt user hiểu Region ID, source path, collection path, `assets[]`, Content Control kỹ thuật hoặc sync-policy enum.

Ngôn ngữ user-facing cho sync policy:

```text
Tự cập nhật khi dữ liệu thay đổi
Chỉ điền lần đầu
Người dùng tự chỉnh trong Word
```

Word preview là preview, không phải Word editor.

### 12.2 Generic Word validation

Bước kiểm tra dùng dữ liệu test, không tạo tài liệu nghiệp vụ chính thức. Severity:

```text
Blocking
Warning
Info
```

Summary tối thiểu: `Đã mapping`, `Chưa mapping`, `Cảnh báo`, `Không tìm thấy vùng`.

Chỉ `Template hợp lệ` khi không còn Blocking.

Vùng chưa thiết lập có action:

```text
Gán dữ liệu
Bỏ qua có chủ đích
Đây là nội dung cố định
```

Back về bước mapping phải giữ thay đổi.

## 13. Bảng tính — Format-specific Authority

### 13.1 Analyzer/fill semantics

Bảng tính không áp Word region semantics máy móc. AI/engine có thể nhận diện:

- workbook/sheet;
- used range;
- header nhiều tầng;
- merged cells;
- section/group row;
- repeating data row;
- cột dữ liệu;
- formula region;
- tổng hợp;
- number/date format;
- ảnh/chứng cứ;
- print/page layout;
- hidden row/column/sheet;
- named range và workbook structure nếu có.

Mapping ưu tiên vùng/cột/dòng mẫu, không bắt user map từng cell lặp nếu cấu trúc có thể suy ra an toàn.

### 13.2 Reference case — `Bang Tinh - HĐ 42.xlsx`

Reference case đã dùng để định hình Iteration 1:

- 01 sheet `Sheet1`;
- used range `A3:T48`;
- bảng nghiệp vụ chính `A:K`;
- header 2 tầng;
- section/group tài sản;
- E:G là ba vị trí giá NCC, tên NCC thực tế là dữ liệu fill chứ không hard-code thành schema;
- H là vùng công thức Đơn giá Tổ TĐG;
- I là vùng công thức Thành tiền;
- J:K là Thông tin khảo sát;
- K có thể chứa URL, text, hồ sơ nguồn và ảnh/chứng cứ;
- template có ảnh/chứng cứ neo theo vùng/dòng;
- style/layout/merge/formula phải được bảo toàn.

### 13.3 Formula authority

Theo quyết định explicit của người dùng:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

`MIN(E:G)` là **template formula authority**.

Engine phải:

- giữ công thức từ mẫu;
- không ghi đè bằng static value;
- không thay bằng business rule khác;
- khi nhân dòng, cập nhật relative references đúng;
- cập nhật an toàn vùng Tổng cộng/Làm tròn khi số dòng thay đổi.

### 13.4 Bảng tính guardrails

Không silent:

- xóa/đổi công thức;
- phá merged cells;
- mất style/border/number format;
- mất ảnh/chứng cứ;
- phá print/page layout;
- làm mất named ranges/data validation/conditional formatting nếu template có;
- làm mất macro trong `.xlsm` nếu format này được hỗ trợ;
- drop workbook feature không hỗ trợ mà không cảnh báo.

Nếu không bảo toàn được thành phần template, validation phải báo trước khi hoàn tất.

## 14. Bước 4 — Kiểm tra & hoàn tất — Baseline Iteration 1

### 14.1 Phạm vi và mental model

Đây là visual baseline dùng chung cho Word generic và Bảng tính. Shell, hierarchy và severity dùng chung; validator, renderer và fill semantics vẫn chuyên biệt theo format.

```text
Blocking | Warning | Info
```

Template chỉ được coi là `Hợp lệ` khi `Blocking = 0`. Không có silent publish, silent accept hoặc silent overwrite Template Version đang được sử dụng.

### 14.2 Layout authority

Desktop-first, Fluent 2, data-heavy. Preview/Test fill là vùng lớn nhất của màn hình.

Cấu trúc chính:

```text
Header + stepper 4 bước
→ Preview/Test fill + danh sách vùng/section
→ Kết quả kiểm tra + danh sách issue
→ Công cụ xử lý issue
→ Footer actions
```

Panel Kết quả kiểm tra phải cho biết số Blocking/Warning/Info và mức độ hoàn tất. Chọn issue phải focus/highlight đúng vị trí trong preview.

### 14.3 Vùng chưa thiết lập

Mọi vùng chưa thiết lập phải có ba lựa chọn explicit:

```text
Gán dữ liệu
Bỏ qua có chủ đích
Đây là nội dung cố định
```

`Bỏ qua có chủ đích` là user intent; AI không được tự silent skip. `Đây là nội dung cố định` phân biệt rõ nội dung template cố định với vùng dữ liệu cần mapping.

### 14.4 Validation Word

Tối thiểu kiểm tra:

- mapping/region chưa thiết lập hoặc không còn định vị được;
- repeating table/row;
- text overflow;
- page break;
- header/footer;
- format tiền/ngày/số;
- layout sau test fill.

Preview Word vẫn là preview, không phải Word editor.

### 14.5 Validation Bảng tính

Tối thiểu kiểm tra:

- workbook/sheet/used range và vùng mapping;
- header nhiều tầng, merged cells và repeating row;
- formula region và relative references khi nhân dòng;
- Tổng cộng/Làm tròn;
- style/border/number format;
- ảnh/chứng cứ;
- print/page layout;
- named range/data validation/conditional formatting/macro hoặc workbook feature có nguy cơ không được bảo toàn.

Formula authority tiếp tục giữ nguyên:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

AI/fill engine không được thay formula bằng static value hoặc business rule khác.

### 14.6 Completion actions

Footer tối thiểu hỗ trợ:

```text
Quay lại | Lưu nháp | Chạy lại kiểm tra | Hợp lệ & Lưu template
```

Primary completion chỉ khả dụng khi không còn Blocking. Thao tác hoàn tất là explicit user action; không tự publish template. Quay lại bước trước hoặc lưu nháp không làm mất mapping/decision đã xác nhận.

### 14.7 Visual authority

Mockup được người dùng explicit nâng thành Baseline ngày 30/08/2026. Companion visual/domain authority:

`VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_FINAL_CHECK_BASELINE_ADDENDUM.md`.

## 15. Kết quả thẩm định giá — immutable company forms

Ngay sau `Chọn nhà cung cấp đã xác nhận giá`, chuyển trực tiếp sang Kết quả thẩm định giá.

### Bảng 1 — Đặc điểm kinh tế - kỹ thuật

```text
STT | Tên tài sản | Đặc điểm kinh tế - kỹ thuật | ĐVT | SL
```

Toàn bộ thông số một tài sản nằm trong **một ô KTKT**.

### Bảng 2 — Tổng hợp giá nhà cung cấp

```text
STT | Tên tài sản | ĐVT | SL |
Đơn giá tham khảo: NCC1 | NCC2 | NCC3 |
Tổ TĐG đánh giá: Đơn giá | Thành tiền
```

Không có cột Thành tiền NCC.

### Bảng 3 — Kết quả thẩm định giá

```text
STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền
```

Giữ `Tổng cộng`, `Làm tròn`, số tiền bằng chữ theo đúng biểu mẫu công ty.

### Rule đối chiếu giá

```text
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
→ được coi là phù hợp theo rule nghiệp vụ/tiêu chuẩn thẩm định giá đang áp dụng trong VALORA
```

Nếu Đơn giá Kết quả lớn hơn một mức giá thuộc tập báo giá đối chiếu bắt buộc, UI phải nêu issue theo dependency được đặc tả; hệ thống không tự sửa giá.

**Limitation:** cách xác định tập báo giá bắt buộc dùng để đối chiếu theo từng dòng/NCC chưa được user khóa thành công thức cụ thể; master không tự suy diễn min/max/every-quote algorithm.

### Immutable layout

Không được tự đổi bố cục, tên cột, thứ tự, split/merge, thêm analytics column hoặc cardize các bảng. Fluent 2 chỉ áp dụng cho shell, navigation, command bar, panel, drawer, status, tooltip và spacing bên ngoài biểu mẫu.

## 16. Microsoft 365 Document Workspace / Bộ tài liệu phát hành

### 16.1 Kiến trúc

VALORA quản lý structured business data, Data Snapshot, lineage, audit và sync status. Microsoft 365/OneDrive/SharePoint/Word quản lý file và file version.

Không xây Word editor giả trong VALORA.

Preview Word trong VALORA: **cuộn trang liên tục**.

### 16.2 Command bar

- `Mở trong Word`;
- `Đồng bộ dữ liệu`;
- `Tạo phiên bản mới`;
- `So sánh`;
- `Khóa phiên bản`;
- `...`;
- `Phát hành bộ tài liệu`.

**Không có chức năng `Xuất PDF` trong baseline này.**

### 16.3 Cấu trúc thư mục

```text
01_Hồ sơ gốc
02_Tài liệu thẩm định
03_Hợp đồng
04_Báo giá nhà cung cấp
05_Pháp lý
```

`03_Hợp đồng` chứa file nghiệp vụ do VALORA sinh: Phiếu/Giấy yêu cầu, Danh mục, Thương thảo, Dự thảo, Hợp đồng, Phụ lục, Nghiệm thu, Thanh lý và tài liệu hợp đồng phát sinh.

`04_Báo giá nhà cung cấp` chứa file Word báo giá do VALORA tạo, phiên bản gửi NCC và working document của báo giá.

`05_Pháp lý` chứa scan/chứng từ đã ký/đóng dấu: tài liệu khách hàng ký gửi lại, hợp đồng/biên bản đã ký, pháp lý khách hàng/tài sản, báo giá NCC đã ký/đóng dấu và chứng từ xác nhận liên quan.

File Word hệ thống sinh và file scan đã ký là **hai artifact khác nhau**, giữ lineage khi liên quan cùng nghiệp vụ.

### 16.4 03_Hợp đồng — Danh sách & tạo tài liệu — Baseline Iteration 1

Màn hình `03_Hợp đồng` là workspace quản lý working documents trong vòng đời hợp đồng, không phải nơi thay thế toàn bộ Generic Template Management và không phải Word editor.

Danh mục tối thiểu:

- Phiếu/Giấy yêu cầu thẩm định giá;
- Danh mục;
- Biên bản/Nội dung thương thảo;
- Dự thảo hợp đồng thẩm định giá;
- Hợp đồng thẩm định giá;
- Phụ lục hợp đồng;
- Biên bản nghiệm thu;
- Biên bản thanh lý;
- tài liệu hợp đồng khác.

Bảng baseline:

```text
STT | Tên tài liệu | Loại tài liệu | Số / Ký hiệu |
Trạng thái | Phiên bản | Cập nhật lần cuối | Tác vụ
```

Primary CTA: `Tạo tài liệu`. Có thể tạo từ template đã cấu hình; tạo bản nháp trống khi loại tài liệu cho phép; tải lên tài liệu Word đã có; tạo hàng loạt khi nghiệp vụ cần.

Preview trong VALORA chỉ để xem. Chỉnh sửa dùng `Mở trong Word`.

Lineage authority:

```text
Template Version
→ Data Snapshot
→ Document Revision
→ Microsoft 365 file / file version
→ Bản scan ký ở 05_Pháp lý (nếu có)
```

Lifecycle artifact giữ nguyên:

```text
Bản nháp
→ Cần đồng bộ
→ Đã đồng bộ
→ Sẵn sàng phát hành
→ Đã phát hành
```

`Chưa tạo` có thể dùng làm planning state cho entry chưa sinh artifact; không thay thế lifecycle sau khi artifact đã tồn tại.

Generated working document và signed scan là hai artifact khác nhau. Signed scan thuộc `05_Pháp lý`, không thay thế file working trong `03_Hợp đồng`.

Không silent overwrite Template Version đã dùng; không silent mutate revision đã phát hành. Nếu dữ liệu VALORA thay đổi, document có thể chuyển `Cần đồng bộ`; sync chỉ cập nhật managed regions theo authority liên quan và không overwrite narrative user chỉnh trong Word.

Companion authority: `VALORA_UIUX_HANDOFF_v2.3_CONTRACT_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md`.

### 16.5 File scan / pháp lý

Người dùng tự drag/drop, upload hoặc move file vào `05_Pháp lý`.

Không có modal/checkpoint bắt buộc `Xác nhận đã ký`, `Ghi nhận pháp lý`, `Đã nhận bản ký`.

### 16.6 Sync/version

Phân biệt:

- VALORA Data Snapshot;
- Document Revision;
- Microsoft 365 DriveItem/file version.

Trạng thái:

```text
Bản nháp
→ Cần đồng bộ
→ Đã đồng bộ
→ Sẵn sàng phát hành
→ Đã phát hành
```

Nếu dữ liệu VALORA thay đổi: hiển thị `Cần đồng bộ`, cho xem thay đổi, chỉ update managed regions, không overwrite narrative user chỉnh trong Word.

Khi phát hành: freeze Revision + Snapshot + artifact/version state; không silent mutate tài liệu đã phát hành.

### 16.7 Managed Regions — Báo cáo thẩm định giá — Baseline Iteration 1

Managed Regions là lớp đồng bộ dữ liệu có cấu trúc từ VALORA vào các vùng được hệ thống quản lý trong Báo cáo thẩm định giá. VALORA **không chỉnh sửa toàn bộ tài liệu Word** và không được ghi đè nội dung ngoài managed region.

Baseline ưu tiên ngôn ngữ nghiệp vụ dễ hiểu cho người không rành IT. User-facing title có thể dùng `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`; thuật ngữ kỹ thuật `Managed Regions`, `Data Snapshot`, `Document Revision` có thể tồn tại trong domain/audit nhưng không phải mental model chính.

Flow hướng dẫn trên màn hình:

```text
1. Xem danh sách vùng
→ 2. Xem nội dung hiện tại
→ 3. Xem khác biệt (nếu có)
→ 4. Chọn vùng cần cập nhật
→ Đồng bộ
```

Layout authority:

```text
Danh sách vùng dữ liệu bên trái
→ Preview Word ở giữa
→ So sánh dữ liệu vùng đang chọn bên phải
→ Footer tóm tắt trạng thái + hành động đồng bộ
```

Preview là vùng lớn nhất. Chọn một vùng trong danh sách phải focus/highlight đúng vị trí trong preview. Preview chỉ để xem; chỉnh sửa narrative tiếp tục dùng `Mở trong Word`.

Trạng thái user-facing:

```text
Đã đồng bộ
Cần đồng bộ
Bạn tự chỉnh trong Word
Lỗi
```

`Bạn tự chỉnh trong Word` cho biết vùng/nội dung đang được người dùng kiểm soát và không được hệ thống tự ghi đè. Nếu thay đổi Word xảy ra trong một managed region, hệ thống phải phát hiện khác biệt và yêu cầu người dùng chọn cách xử lý trước khi sync; không silent overwrite.

Panel so sánh hiển thị tối thiểu:

```text
Dữ liệu từ VALORA
↔
Dữ liệu đang có trong Word
```

Các giá trị khác nhau phải được highlight trực quan. UI không bắt người dùng hiểu snapshot ID hoặc revision ID mới có thể quyết định.

Với vùng đang chọn, tối thiểu có các lựa chọn explicit:

```text
Cập nhật vào Word
Giữ nguyên trong Word (không cập nhật)
Bỏ qua vùng này lần này
```

Primary CTA có thể là `Đồng bộ các vùng đã chọn (n)` hoặc `Đồng bộ tất cả vùng (n)` tùy context. Không có silent sync. Người dùng luôn biết vùng nào sẽ được cập nhật trước khi thực hiện.

Sync chỉ ghi dữ liệu vào managed regions đã được người dùng chọn. Narrative và nội dung ngoài managed region phải giữ nguyên. Mọi lần đồng bộ cần giữ history/audit đủ để truy vết vùng, Data Snapshot/nguồn dữ liệu, Document Revision/file version và thời điểm thao tác.

Mental model reassurance phải được thể hiện rõ: VALORA chỉ cập nhật những chỗ hệ thống quản lý và không thay đổi phần nội dung người dùng đã tự biên tập ngoài các vùng này.

Baseline hiện tại áp dụng trực tiếp cho **Báo cáo thẩm định giá**. Chứng thư thẩm định giá có thể tái sử dụng cùng interaction model trong iteration tiếp theo nhưng chưa tự động trở thành visual baseline chỉ từ quyết định này.

Companion authority: `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md`.

## 17. Validation phân tán

Không có màn Kiểm tra hồ sơ riêng.

- `Blocking`: phải xử lý trước dependency liên quan.
- `Warning`: vẫn tiếp tục nhưng nêu rõ rủi ro/cần kiểm tra.
- `Info`: trạng thái, không cản workflow.

S10 chỉ tổng hợp readiness; issue hiển thị ngay nơi phát sinh và có `Đi tới`.

Blocking được đặt tại dependency thực tế, ví dụ: thiếu Đơn giá hiện hành, thiếu dữ liệu bắt buộc để tạo file, mapping/template còn Blocking, báo giá NCC chưa đủ điều kiện hoàn tất, managed regions chưa đồng bộ.

## 18. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price, auto-apply.
- AI Template Assistant không silent accept mapping, silent publish hoặc silent overwrite template/version.
- User luôn có quyền bổ sung field AI bỏ sót, sửa/xóa mapping AI.
- `Đã bỏ qua` phải là explicit user intent.
- Raw Excel/source luôn truy vết được; không ghi đè bởi normalized data.
- Staging và dữ liệu chính thức phải phân biệt.
- Giá/chứng cứ không silent overwrite Đơn giá hiện hành.
- Mỗi thay đổi giá giữ giá trước, actor, time, lineage/audit.
- Nguồn Internet mất truy cập vẫn giữ URL/snapshot/history.
- Giá trong Kết quả hồ sơ cũ là nguồn tham chiếu ưu tiên thứ ba.
- Giá NCC lịch sử phục vụ tái tạo báo giá/đối chiếu, không tự trở thành Đơn giá hiện hành.
- Báo giá dedupe/hợp nhất theo NCC phù hợp.
- STT immutable trong business dataset; template-specific display behavior cần explicit mapping/authority.
- Giá đề nghị khác semantic với Đơn giá NCC đã xác nhận.
- Template báo giá chỉ `.docx`; không silent overwrite template/version.
- Formula template không biến thành static data mapping.
- AI/engine không tự đổi `MIN(E:G)` trong Bảng tính reference authority.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- File Word generated và file scan signed là hai artifact khác nhau, giữ lineage.
- `03_Hợp đồng` không giữ signed scan thay working document; signed scan thuộc `05_Pháp lý`.
- Managed Regions không được silent sync, không được overwrite nội dung ngoài vùng quản lý và phải cho người dùng xem khác biệt trước khi ghi đè dữ liệu đang có trong managed region.
- Vietnamese-first; không phơi HTTP/SQL/stack trace/row_version cho người dùng cuối.
- Mỗi màn hình/context có một primary CTA nổi bật.

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
| S10 | Tổng quan hồ sơ | P0 — dashboard điều phối; không khóa số checkpoint |
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
| M365-03HĐ | 03_Hợp đồng — Danh sách & tạo tài liệu | P0 — baseline Iteration 1; table-first + preview + detail + lineage |
| M365-MR-REPORT | Managed Regions — Báo cáo thẩm định giá | P0 — baseline Iteration 1; user-friendly compare + explicit sync |
| GTM | Quản lý mẫu tài liệu generic | P0 — baseline Iteration 1 |
| GWM | Mapping tài liệu Word generic | P0 — baseline Iteration 2 |
| GWR | Kiểm tra & hoàn tất template Word generic | P0 — baseline Iteration 1 |
| AI-TPL-2 | AI phân tích & đề xuất | P0 — baseline Iteration 1 |
| AI-TPL-3 | Rà soát & chỉnh sửa | P0 — baseline Iteration 1 |
| Spreadsheet | Bảng tính template semantics | Design Authority — format-specific mapping/fill guardrails |
| AI-TPL-4 | Kiểm tra & hoàn tất dùng chung Word + Bảng tính | P0 — baseline Iteration 1; validator chuyên biệt theo format |

## 20. Companion authority documents

Các file sau tiếp tục được giữ để truy vết chi tiết/visual authority:

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
- `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — đọc theo semantic child flow; các mô tả về S17 toàn hồ sơ đã bị routing mới supersede.
- `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md`.
- `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow support, không override master.

## 21. Trạng thái triển khai và hướng tiếp theo

Đây là thiết kế mục tiêu. Không suy diễn mockup/design authority = chức năng đã implement.

Authority hiện đã được khóa xuyên suốt:

```text
Pre-case
→ Official appraisal workflow
→ Price/Evidence
→ NCC quotation evidence
→ Final Result
→ Document Workspace
   → 03_Hợp đồng — Danh sách & tạo tài liệu
   → Managed Regions — Báo cáo thẩm định giá
→ Generic Template Management
→ AI-assisted Template Setup
   → AI phân tích & đề xuất
   → Rà soát & chỉnh sửa
   → Kiểm tra & hoàn tất
```

Hướng thiết kế tiếp theo ưu tiên:

1. áp dụng/thiết kế interaction model Managed Regions cho Chứng thư thẩm định giá;
2. version/sync UX chi tiết;
3. phát hành bộ tài liệu;
4. đặc tả dependency/rule engine cho đối chiếu `Đơn giá Kết quả <= Đơn giá báo giá NCC` mà không tự suy diễn tập báo giá bắt buộc;
5. đặc tả implementation contract riêng cho Excel/Bảng tính Fill Engine nếu bắt đầu triển khai.

## 22. ADR

Việc nâng và consolidate `Managed Regions — Báo cáo thẩm định giá — Iteration 1` thành visual/design baseline là cập nhật UI/UX authority, **không phát sinh ADR kỹ thuật mới**.

Nếu triển khai làm thay đổi domain contract, Document Data Model, Excel fill semantics, version/sync boundary, validation semantics, managed-region persistence/sync semantics hoặc template persistence contract hiện có, cần đánh giá ADR riêng trước khi sửa product code.
