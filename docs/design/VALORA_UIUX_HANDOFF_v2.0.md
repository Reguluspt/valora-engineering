# VALORA — UI/UX Handoff v2.0

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh

> v2.0 kế thừa baseline v1.9 nhưng **supersede cách tổ chức S08**: `Rà soát giá đề xuất` không còn là một màn hình độc lập. Chức năng rà soát được tích hợp vào `S02 — Quản lý yêu cầu sơ bộ`, đồng thời bổ sung bước **Tạo file kết quả sơ bộ** từ file Excel khách hàng.

## 0. Cập nhật v2.0 đã được duyệt

- **Không có màn hình S08 độc lập.**
- Rà soát giá đề xuất là checkpoint tích hợp trong `Quản lý yêu cầu sơ bộ`.
- Tại một Pre-case đủ điều kiện, CTA `Rà soát & tạo file` mở panel/drawer bên phải ngay trên S02.
- Danh sách Yêu cầu sơ bộ vẫn là context chính; người dùng không bị điều hướng sang một shell/page khác.
- Không cho tạo kết quả sơ bộ nếu còn bất kỳ dòng nào chưa xác định được giá hoặc chưa xác nhận.
- `Thuyết minh đơn giá` (`USER_PRICE_JUSTIFICATION`) có thể là căn cứ duy nhất của một dòng nếu người dùng đã lưu/xác nhận căn cứ và đã xác định đầy đủ giá cơ sở, vận chuyển %, đơn giá đề xuất.
- `Thành tiền = SL × Đơn giá đề xuất`.
- Sau khi rà soát đạt, Valora cho phép **Tạo file kết quả sơ bộ**.
- File kết quả sơ bộ là **bản sao của chính file Excel khách hàng đã cung cấp**, không phải template Excel mới của Valora.
- File kết quả bổ sung đúng 02 cột nghiệp vụ: `Đơn giá đề xuất` và `Thành tiền` tại vùng bảng danh mục đã mapping.
- File nguồn khách hàng không bị ghi đè.
- File kết quả phải có version/lineage tới Pre-case, version file nguồn, mapping snapshot và snapshot giá dùng để xuất.
- Mockup 08 đã duyệt là trạng thái mở rộng của S02: bảng work queue ở trái + panel `Rà soát & tạo file kết quả sơ bộ` ở phải.

## 1. Product baseline đã chốt

- Valora hiện tại dành cho **01 người dùng nghiệp vụ xử lý toàn bộ vòng đời công việc**.
- Chỉ phục vụ **thẩm định giá máy móc thiết bị**.
- Phương pháp nghiệp vụ cố định: **phương pháp so sánh**.
- Công việc chính: đối chiếu Kho tri thức và thu thập thông tin giá bán trên Internet.
- **Không thiết kế khảo sát hiện trạng** ở phiên bản hiện tại.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word là input/output; Workbench + database mới là nguồn dữ liệu làm việc chính thức.

## 2. North-star user flow v2.0

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
→ Ghi nhận đã gửi/trao đổi với khách hàng
→ Chờ khách hàng phản hồi
→ Khách hàng chấp thuận
→ Chuyển thành hồ sơ chính thức
→ Các bước nghiệp vụ tiếp theo
```

Không tự chuyển sang `Chờ khách hàng phản hồi` chỉ vì đã tạo file kết quả sơ bộ.

## 3. Khái niệm Yêu cầu sơ bộ / Pre-case

Pre-case tồn tại trước hồ sơ thẩm định giá chính thức. Thực tế đầu vào thường chỉ có file Excel danh mục máy móc thiết bị.

Ở giai đoạn này **không bắt buộc**:

- tên khách hàng;
- MST;
- địa chỉ;
- người đại diện;
- hợp đồng.

Thông tin pháp nhân/hợp đồng chỉ được yêu cầu khi khách hàng đồng ý triển khai và người dùng chuyển Pre-case thành hồ sơ chính thức.

### Trạng thái Pre-case

Các trạng thái cấp danh sách có thể gồm:

- `Mới tạo`;
- `Mới nhận danh mục`;
- `Đang phân tích`;
- `Sẵn sàng tạo kết quả sơ bộ`;
- `Đã tạo kết quả sơ bộ`;
- `Chờ khách hàng phản hồi`;
- `Đã chấp thuận giá đề xuất`;
- `Không tiếp tục`;
- `Đã chuyển thành hồ sơ`.

Các trạng thái chi tiết của mapping/thiết bị là progress bên trong, không cần biến thành quá nhiều status cấp danh sách.

## 4. S02 — Quản lý yêu cầu sơ bộ

### 4.1 Mục tiêu

S02 là work queue trung tâm của toàn bộ giai đoạn Pre-case và là nơi người dùng quay về sau khi phân tích danh mục.

### 4.2 Thành phần chính

- KPI/card cấp work queue: Tổng yêu cầu, Đang phân tích, Sẵn sàng tạo kết quả sơ bộ, Chờ phản hồi, Đã chấp thuận.
- Search theo mã yêu cầu, tên yêu cầu, tên file.
- Filter trạng thái/ngày.
- CTA `+ Tạo yêu cầu sơ bộ`.
- Bảng danh sách tối thiểu:
  - Mã yêu cầu;
  - Tên yêu cầu sơ bộ;
  - File nguồn;
  - Ngày nhận;
  - Số thiết bị;
  - Tiến độ phân tích;
  - Tổng giá trị đề xuất;
  - Trạng thái;
  - Cập nhật cuối;
  - Thao tác.

### 4.3 Row action theo trạng thái

- Đang phân tích → `Tiếp tục phân tích`.
- Đã phân tích đủ điều kiện → `Rà soát & tạo file`.
- Đã tạo file kết quả sơ bộ → `Xem file / Ghi nhận đã gửi`.
- Chờ khách hàng phản hồi → `Ghi nhận phản hồi`.
- Đã chấp thuận → `Chuyển thành hồ sơ`.

### 4.4 Rà soát tích hợp trong S02

Khi bấm `Rà soát & tạo file`, mở **panel/drawer bên phải** ngay trên S02.

Panel hiển thị tối thiểu:

- mã/tên Pre-case;
- file nguồn + sheet + version;
- Tổng thiết bị;
- Đã xác nhận;
- Có dùng Kho tri thức;
- Có nguồn Internet mới;
- Có Thuyết minh;
- Cần xử lý;
- Tổng giá trị đề xuất;
- preview một số dòng danh mục;
- CTA quay lại Phân tích danh mục;
- CTA `Tạo file kết quả sơ bộ`;
- liên kết `Xem lịch sử file đã tạo` khi đã có output trước đó.

KPI `Kho tri thức`, `Internet mới`, `Thuyết minh` có thể giao nhau; không được hiểu là các nhóm loại trừ nhau.

### 4.5 Preview danh mục trong panel

Preview tối thiểu:

- Thiết bị;
- SL / ĐVT;
- Đơn giá KH dự kiến;
- Đơn giá đề xuất;
- Thành tiền;
- Trạng thái.

Không cần nhồi toàn bộ cột S05 vào panel; mục đích là rà soát nhanh readiness và giá chuẩn bị xuất.

### 4.6 Quay lại đúng dòng cần sửa

Nếu còn blocking row, `Đi tới dòng`/`Quay lại Phân tích danh mục` phải mở đúng thiết bị trong S05 và đúng context phù hợp:

- thiếu/thay nguồn → `Nguồn giá`;
- candidate tri thức chưa xử lý → `Kho tri thức`;
- chưa xác nhận giá → `Kết luận giá`;
- vấn đề chung → `Tổng quan`.

Khi quay lại S02, hệ thống giữ đúng Pre-case và context rà soát.

## 5. S03 — Tạo yêu cầu sơ bộ

Giữ baseline đã duyệt:

- mã yêu cầu tự sinh;
- tên nội bộ bắt buộc;
- ngày nhận;
- ghi chú không bắt buộc;
- file `.xls` / `.xlsx`;
- cảnh báo trùng chỉ là advisory;
- không bắt nhập khách hàng/MST/hợp đồng;
- CTA có file hợp lệ: `Tạo & tiếp tục Mapping`.

## 6. S04 — Upload & Mapping Excel

Luồng chuẩn:

1. Tải file Excel.
2. Chọn sheet & vùng dữ liệu.
3. Mapping cột.

Các field nghiệp vụ quan trọng:

- Tên thiết bị;
- Thông số / đặc điểm;
- ĐVT;
- SL;
- `Đơn giá KH dự kiến`;
- Ghi chú;
- Bỏ qua.

Cột `Đơn giá` của khách hàng được map thành `Đơn giá KH dự kiến`; không được hiểu là giá thị trường hay đơn giá thẩm định.

Phải giữ lineage file/sheet/dòng/cột nguồn.

## 7. S05 — Phân tích danh mục

Đây là workspace trung tâm để xử lý từng thiết bị.

### Cụm giá đã chốt

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

Không có cột `Chênh lệch`.

Không hiển thị:

- `Chi phí vận chuyển`;
- `Giá sau vận chuyển`.

Công thức:

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

S05 giữ trải nghiệm spreadsheet-first: scroll nhanh, sticky header/cột thiết yếu, edit inline cho field được phép, không reload toàn màn hình sau mỗi save và phải giữ context dòng đang xử lý.

## 8. Panel Kho tri thức

Candidate hiển thị tối thiểu:

- tên chuẩn;
- thương hiệu/model;
- thông số;
- mức độ tương đồng;
- lý do khớp;
- giá/lịch sử;
- ngày cập nhật;
- nguồn liên quan.

Hành động:

- `Sử dụng dữ liệu này`;
- `Không phù hợp`;
- `Xem tất cả trong Kho tri thức`.

Không auto-accept. Giá lịch sử chỉ là tham khảo.

## 9. Panel Nguồn giá / Thêm nguồn giá

`+ Thêm nguồn giá` hỗ trợ hai cách, có thể dùng một hoặc cả hai:

1. `Thuyết minh đơn giá` — `USER_PRICE_JUSTIFICATION`.
2. `Dán link trang web` — `INTERNET_MARKET_SOURCE`.

Nguồn Internet cần lưu tối thiểu URL, website/nhà cung cấp, tên sản phẩm, giá quan sát, ngày thu thập và ghi chú đối chiếu.

Website có thể mất hoặc thay đổi; không xóa lịch sử nguồn cũ chỉ vì URL không còn truy cập được.

## 10. Điều kiện hoàn tất một dòng

Một dòng đạt điều kiện khi đồng thời:

1. thiết bị được nhận diện đủ để so sánh;
2. có ít nhất một căn cứ giá người dùng chấp nhận;
3. có Giá thị trường tham khảo / giá cơ sở được xác nhận;
4. Vận chuyển (%) hợp lệ, `0%` được phép;
5. có Đơn giá đề xuất;
6. người dùng đã xác nhận dòng.

`Thuyết minh đơn giá` có thể là căn cứ duy nhất.

Không yêu cầu cứng số lượng nguồn Internet tối thiểu.

**Không có ngoại lệ “có lý do chưa xác định giá nhưng vẫn hoàn tất”.**

## 11. Checkpoint rà soát tích hợp — điều kiện tạo file

CTA `Tạo file kết quả sơ bộ` chỉ enabled khi:

- `Cần xử lý = 0`;
- tất cả dòng thuộc phạm vi đã có giá;
- tất cả dòng bắt buộc đã được xác nhận;
- không còn lỗi blocking dữ liệu.

Nếu chưa đạt, panel hiển thị warning rõ nguyên nhân và CTA quay về đúng dòng cần xử lý.

### Thành tiền

```text
Thành tiền = SL × Đơn giá đề xuất
```

Tổng giá trị đề xuất = tổng Thành tiền của danh mục.

## 12. Tạo file kết quả sơ bộ

### 12.1 Mục tiêu

Tạo file Excel để người dùng gửi/trao đổi kết quả giá sơ bộ với khách hàng mà vẫn giữ quen thuộc với chính file khách hàng đã cung cấp.

### 12.2 Nguyên tắc nguồn

- File Excel khách hàng là nguồn bất biến; không ghi đè.
- Tạo một **file đầu ra mới** từ đúng version file nguồn đang dùng cho Pre-case.
- Không dùng một template Excel Valora hoàn toàn khác.
- Cố gắng giữ nguyên workbook, sheet, cấu trúc, nội dung và định dạng của file khách hàng.

### 12.3 Hai cột bổ sung

Tại vùng bảng danh mục đã mapping, bổ sung đúng:

- `Đơn giá đề xuất`;
- `Thành tiền`.

Dữ liệu lấy từ snapshot rà soát đã xác nhận.

### 12.4 Lineage / version

Mỗi file kết quả phải liên kết tới:

- Pre-case;
- version file Excel nguồn;
- sheet/vùng dữ liệu đã mapping;
- mapping snapshot;
- snapshot giá đã dùng;
- thời điểm tạo;
- actor tạo;
- version file kết quả.

Nếu người dùng quay lại sửa giá/danh mục rồi tạo lại, sinh **version kết quả mới**; không ghi đè file cũ.

### 12.5 Sau khi tạo file

- Hiển thị file vừa tạo trong Pre-case.
- Có `Xem lịch sử file đã tạo`.
- Tạo file **không tự đồng nghĩa đã gửi khách hàng**.
- Tạo file **không tự chuyển** Pre-case sang `Chờ khách hàng phản hồi`.

## 13. Ghi nhận gửi/trao đổi và phản hồi khách hàng — bước tiếp theo cần thiết kế sâu

Sau khi có file kết quả sơ bộ:

```text
Đã tạo kết quả sơ bộ
→ Ghi nhận đã gửi/trao đổi
→ Chờ khách hàng phản hồi
→ Ghi nhận phản hồi
```

Khi khách hàng chấp thuận, mới vào `S09 — Chuyển thành hồ sơ`.

Nếu khách hàng không tiếp tục, đóng Pre-case nhưng giữ toàn bộ file nguồn, kết quả phân tích, file kết quả sơ bộ, nguồn giá và lịch sử quyết định.

Nếu khách hàng yêu cầu chỉnh danh mục/giá, giữ version cũ và quay lại đúng bước phân tích cần sửa; file kết quả mới phải hình thành version mới.

## 14. S09 — Chuyển thành hồ sơ chính thức

Chỉ mở khi khách hàng đã đồng ý mức giá đề xuất/đề nghị triển khai.

Lúc này mới yêu cầu dữ liệu pháp nhân/hợp đồng cần thiết.

Phải reuse:

- danh mục đã phân tích;
- kết quả Kho tri thức;
- nguồn Internet;
- Thuyết minh;
- snapshot giá sơ bộ;
- file nguồn;
- file kết quả sơ bộ;
- lineage Pre-case.

Không bắt người dùng upload và làm lại từ đầu.

## 15. Design system / UX guardrails

- Vietnamese-first.
- Astryx/Valora component language.
- Không hiển thị HTTP status, SQL, ORM, `row_version`, session id hay stack trace cho người dùng cuối.
- Sidebar/header/breadcrumb/KPI/table/panel/drawer/button hierarchy phải nhất quán.
- Không tạo modal/shell khác visual language cho tác vụ con.
- AI/Kho tri thức không auto-confirm mapping/identity/price/Apply/publish.
- Dữ liệu nguồn bất biến; normalized representation không ghi đè raw wording.
- Chứng cứ và quyết định phải truy vết được.

## 16. Screen inventory cập nhật

| ID | Màn hình / capability | Ghi chú |
|---|---|---|
| S01 | Trang chủ | P0 |
| S02 | Quản lý yêu cầu sơ bộ | P0; bao gồm panel rà soát & tạo file kết quả sơ bộ |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | **Capability tích hợp trong S02; không có màn hình riêng** |
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

Giữ ID S08 để không phá tham chiếu lịch sử tài liệu, nhưng mọi tài liệu mới phải ghi rõ S08 là capability/state trong S02.

## 17. Baseline mockup đã duyệt

Baseline hiện có 08 mockup:

1. Quản lý yêu cầu sơ bộ.
2. Tạo yêu cầu sơ bộ.
3. Upload & Mapping Excel.
4. Phân tích danh mục.
5. Panel Kho tri thức.
6. Panel Nguồn giá Internet.
7. Thêm nguồn giá.
8. **Quản lý yêu cầu sơ bộ — trạng thái `Rà soát & tạo file kết quả sơ bộ`.**

Mockup 08 supersede mockup S08 standalone của v1.9.

## 18. Loading / empty / error / warning cần giữ

- Loading: skeleton trong đúng shell/panel.
- Empty: giải thích rõ bước tiếp theo.
- Error: tiếng Việt, có CTA xử lý; không lộ lỗi kỹ thuật.
- Warning còn dòng thiếu giá/chưa xác nhận: chặn tạo file, chỉ rõ số lượng và cho đi tới dòng.
- Nguồn Internet không còn truy cập: giữ lịch sử URL và đánh dấu cần kiểm tra.
- Lỗi tạo file: không làm mất snapshot đã rà soát hoặc file nguồn.
- File kết quả cũ: không ghi đè khi tạo version mới.

## 19. Phân biệt “đã implement” và “thiết kế mục tiêu”

Các quyết định trong tài liệu này là **baseline thiết kế sản phẩm/UI/UX đã duyệt**. Không được suy diễn rằng toàn bộ flow Pre-case, panel rà soát hoặc chức năng tạo file kết quả sơ bộ đã được implement trong runtime hiện tại.

Engineering chỉ triển khai khi có task/assignment riêng và phải tuân theo CODEX, guardrails, ADR/contracts và task gate của repository.

## 20. Tài liệu authority cần đối chiếu khi implement

Đọc theo thứ tự repository authority, tối thiểu:

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. `docs/design/VALORA_UIUX_HANDOFF_v2.0.md`
6. `docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md`
7. `docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md`
8. `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
9. `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`

Guardrails kỹ thuật vẫn giữ nguyên: tenant isolation fail-closed; staging không tự thành official data; Apply cần human confirmation; restricted Workbench fields đi qua draft/commit; AI advisory-only; historical/source evidence phải có provenance.
