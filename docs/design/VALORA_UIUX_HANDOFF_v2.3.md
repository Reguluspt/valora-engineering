# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master handoff — **Consolidated v2.3 + Spreadsheet Fill Engine + Sinh & Đồng bộ Báo cáo Baseline + NCC Price Warning Authority**; không đồng nghĩa product code đã implement  
**Cập nhật:** 31/08/2026

> Master consolidate authority v2.3 hiện hành. Addendum giữ để truy vết quyết định/visual authority. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành

Baseline/authority đã khóa:

- S09 — Chuyển sang thẩm định chính thức.
- S10 — Tổng quan hồ sơ.
- S11 — Xác nhận & điều chỉnh danh mục triển khai.
- S12 — Workbench tài sản.
- S13 — Asset Context Drawer trong S12.
- Nguồn giá & Chứng cứ.
- NCCQ — Tạo & quản lý báo giá NCC — Iteration 6.
- TM01 — Danh sách mẫu báo giá NCC — Iteration 1.
- TM03 — Upload & Mapping template NCC — Iteration 1 Word-only.
- TM04 — Preview / Test fill template NCC — Iteration 1.
- NCCQ child — Hoàn tất 01 báo giá NCC — Iteration 3.
- Kết quả thẩm định giá — Iteration 1, 03 bảng biểu mẫu công ty immutable.
- Microsoft 365 Document Workspace / Bộ tài liệu phát hành — baseline authority.
- 03_Hợp đồng — Iteration 1 Baseline / Design Authority.
- Managed Regions — Báo cáo — Iteration 1 Baseline / Design Authority.
- Managed Regions — Chứng thư — Iteration 1 Baseline / Design Authority.
- Đồng bộ dữ liệu & Quản lý phiên bản — Iteration 1 Baseline / Design Authority.
- Phát hành bộ tài liệu — Iteration 1 Baseline / Design Authority.
- Quản lý mẫu tài liệu generic — Iteration 1.
- Mapping Template tài liệu generic Word — Iteration 2.
- Kiểm tra & hoàn tất template Word generic — Iteration 1.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 3 — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 4 Word + Bảng tính — Iteration 1 Baseline / Design Authority.
- Bảng tính Fill Engine — Implementation Contract v1 — Iteration 1 Baseline / Design Authority.
- **Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1 Baseline / Design Authority.**

Current business-rule authority:
- Không có màn `Kiểm tra quy tắc đối chiếu giá`; mockup đó discarded.
- Cảnh báo `Giá NCC ↔ Đơn giá hiện hành` xuất hiện ngay tại NCCQ theo từng dòng; Warning, không Blocking.

Guardrail xuyên suốt: single-user; AI advisory; không S14; không màn Kiểm tra hồ sơ riêng; không KSCL/phê duyệt nhiều cấp; không NCCQ aggregate trung gian; không silent overwrite/sync/publish; không fake Word/Excel editor.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị; phương pháp so sánh.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Template báo giá NCC chỉ Word `.docx`; template generic có thể Word/Bảng tính theo authority.
- Microsoft 365 quản lý file/file version/Word; VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status và release manifest.
- Không đưa dữ liệu nhận diện khách hàng/NCC/hồ sơ thật vào public repository.

## 2. North-star user flow v2.3

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
   → Kho tri thức / Internet / Hồ sơ cũ / Thuyết minh đơn giá
   → Người dùng ấn định / điều chỉnh giá
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục triển khai
→ Workbench tài sản → Asset Context Drawer
→ Nguồn giá & Chứng cứ
→ Tạo & quản lý báo giá NCC
   → Hoàn tất từng báo giá NCC
   → Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace / Bộ tài liệu phát hành
   → 03_Hợp đồng
   → Báo cáo thẩm định giá
      → Sinh & Đồng bộ Báo cáo
         → Chọn template & phạm vi
         → Data Snapshot
         → Preview & Review vùng
         → Tạo Document Revision
         → Đồng bộ Microsoft 365
         → Kết quả đồng bộ
      → Managed Regions — Báo cáo
   → Chứng thư thẩm định giá → Managed Regions — Chứng thư
   → Đồng bộ dữ liệu & Quản lý phiên bản
   → Phát hành bộ tài liệu
```

Không có checkpoint riêng: `Khai báo thông tin thực hiện`, `Xác nhận giá thẩm định chính thức`, `Kiểm tra hồ sơ`, `KSCL`, `Kiểm tra quy tắc đối chiếu giá`.

## 3. Price & Evidence

Ưu tiên nguồn giá:
```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```
Kho tri thức chỉ hỗ trợ; giá NCC không phải nguồn chính xác định đơn giá thẩm định cuối cùng.

Cảnh báo NCC:
```text
Giá NCC < Đơn giá hiện hành → luôn Warning
|Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15% → Warning chênh lệch lớn
```
Warning không Blocking; không tự sửa/chọn giá.

## 4. NCCQ

Bảng baseline:
```text
STT | Tên tài sản | ĐVT | Số lượng | NCC1 | NCC2 | NCC3 | Đơn giá chọn | Thành tiền | Đơn giá hiện hành
```
STT immutable; cùng NCC consolidate; lineage cấp dòng. CTA `Chọn nhà cung cấp đã xác nhận giá` lưu evidence và chuyển trực tiếp sang Kết quả thẩm định giá.

## 5. Kết quả thẩm định giá

Ba bảng immutable:
```text
STT | Tên tài sản | Đặc điểm kinh tế - kỹ thuật | ĐVT | SL
STT | Tên tài sản | ĐVT | SL | NCC1 | NCC2 | NCC3 | Tổ TĐG đánh giá: Đơn giá | Thành tiền
STT | Tên tài sản | ĐVT | SL | Đơn giá | Thành tiền
```
Giữ Tổng cộng, Làm tròn, số tiền bằng chữ; không cardize/đổi cột.

## 6. Template / AI

```text
Chọn mẫu → AI phân tích & đề xuất → Rà soát & chỉnh sửa → Kiểm tra & hoàn tất
```
AI không silent accept/publish/overwrite/change formula/promote custom field.

## 7. Bảng tính authority

Reference `Bang Tinh - HĐ 42.xlsx`:
```text
Hn = MIN(En:Gn)
In = Dn*Hn
```
Engine giữ formula, relative refs, tổng/làm tròn, merge/style/border/number format/images/evidence/page layout/named range/data validation/conditional formatting/workbook features; phải cảnh báo trước nếu không bảo toàn.

Fill Engine baseline:
```text
Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version
```
Không overwrite template; output mới; mapped regions only; Fill Manifest + audit; validator Blocking/Warning/Info.

## 8. Microsoft 365 Document Workspace

VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, release manifest. Microsoft 365 quản lý Word/file/file version. Không fake Word editor. Document Revision != Microsoft 365 file version.

Managed Regions status:
```text
Đã đồng bộ
Cần cập nhật
Bạn tự chỉnh trong Word
Lỗi
```
Mental model:
```text
Dữ liệu từ VALORA ↔ Nội dung hiện tại trong Word → user chọn vùng → Đồng bộ
```
Không silent overwrite narrative ngoài vùng; conflict trong managed region phải được xem/xử lý.

### 8.1 Sinh & Đồng bộ Báo cáo thẩm định giá — Baseline Iteration 1

Mental flow:
```text
Chọn template & phạm vi
→ Data Snapshot
→ Preview & Review vùng
→ Tạo Document Revision
→ Đồng bộ Microsoft 365
→ Kết quả đồng bộ
```

Layout Fluent 2: header/breadcrumb + stepper 6 bước; trái là Template/Phạm vi + Data Snapshot + kiểm tra Managed Regions; giữa là preview Word view-only lớn nhất có overlay vùng; phải là mapping/status + thông tin đồng bộ dự kiến + validation; footer có một primary CTA theo bước.

`Tạo Document Revision` là explicit user action. Template Version và Data Snapshot phải được khóa/truy vết khi tạo revision; không silent đổi nguồn sau đó.

Lineage:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```

Ở giai đoạn chuẩn bị sinh mới, readiness vùng có thể hiển thị `Đã mapping / Cần xem / Chưa mapping`; sau khi Word tồn tại, trạng thái vùng quay về authority Managed Regions chuẩn. Các region code/field trong mockup chỉ minh họa, không hard-code schema và không bắt user hiểu ID kỹ thuật.

Validation phân tán: Blocking ngăn tạo revision/sync; Warning cho tiếp tục nếu rule cho phép; Info là trạng thái. Không tạo màn kiểm tra hồ sơ mới.

Baseline này là child flow, không thay thế Managed Regions — Báo cáo, Sync/Version hoặc Publishing; không tạo lifecycle song song.

### 8.2 Sync/version
```text
Xem những gì đã thay đổi → Xem chi tiết khác biệt → Chọn nội dung muốn cập nhật → Cập nhật vào Word & tạo/ghi nhận phiên bản
```

### 8.3 Publishing
```text
Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành
```
Release manifest freeze artifact + Document Revision + Data Snapshot nếu có + Microsoft 365 file/version + thời điểm + người thao tác. Release cũ immutable. Không có `Xuất PDF` trong baseline.

## 9. Validation / UX guardrails

- Blocking xử lý trước dependency; Warning nêu rủi ro; Info là trạng thái.
- Không màn Kiểm tra hồ sơ riêng.
- Raw source truy vết được; STT immutable.
- Vietnamese-first; không phơi HTTP/SQL/stack trace/internal IDs.
- Mỗi context có một primary CTA.
- Không silent mutate revision/release đã phát hành.

## 10. Screen / capability inventory

| Capability | Trạng thái |
|---|---|
| Pre-case S02–S09 | P0 theo authority hiện hành |
| S10–S13 | P0 baseline |
| Nguồn giá & Chứng cứ | P0 baseline |
| NCCQ | P0 baseline Iteration 6 |
| Result | P0 baseline Iteration 1; 03 bảng immutable |
| Microsoft 365 Document Workspace | P0 baseline |
| 03_Hợp đồng | P0 baseline Iteration 1 |
| Managed Regions — Báo cáo | P0 baseline Iteration 1 |
| Managed Regions — Chứng thư | P0 baseline Iteration 1 |
| Sync/Version | P0 baseline Iteration 1 |
| Publishing | P0 baseline Iteration 1 |
| Spreadsheet Fill Engine | P0 baseline Iteration 1 |
| **Sinh & Đồng bộ Báo cáo** | **P0 baseline Iteration 1** |

## 11. Companion authority documents

- `VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md`.
- Các addendum Managed Regions / Sync-Version / Publishing / Template / Result / NCCQ hiện hành tiếp tục có hiệu lực trong scope tương ứng.
- `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 12. ADR

Nâng `Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1` thành visual/design baseline là UI/UX authority update. Nếu implementation thay đổi Data Snapshot/Document Revision persistence, transaction boundary khi tạo file, conflict detection, managed-region write policy hoặc Microsoft 365 version binding thì phải đánh giá ADR riêng trước khi sửa product code.
