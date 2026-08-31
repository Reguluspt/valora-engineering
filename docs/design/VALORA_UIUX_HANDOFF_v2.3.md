# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master handoff — **Consolidated v2.3 + Document Generation/Sync Baselines + Spreadsheet Fill Engine + NCC Price Warning Authority**  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Baseline/authority đã khóa gồm S09–S13, Nguồn giá & Chứng cứ, NCCQ Iteration 6, TM01/TM03/TM04, NCCQ child, Kết quả thẩm định giá 03 bảng immutable, Microsoft 365 Document Workspace, 03_Hợp đồng, Managed Regions Báo cáo/Chứng thư, Sync/Version, Publishing, Template/AI flows, Fill Engine, **Sinh & Đồng bộ Báo cáo — Iteration 1**, và **Sinh & Đồng bộ Chứng thư — Iteration 1**.

Không có S14, màn Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn Kiểm tra quy tắc đối chiếu giá. AI advisory; không silent overwrite/sync/publish; không fake Word/Excel editor.

## 1. North-star user flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản → Asset Context Drawer
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → 03_Hợp đồng
   → Báo cáo thẩm định giá
      → Sinh & Đồng bộ Báo cáo
      → Managed Regions — Báo cáo
   → Chứng thư thẩm định giá
      → Sinh & Đồng bộ Chứng thư
      → Managed Regions — Chứng thư
   → Đồng bộ dữ liệu & Quản lý phiên bản
   → Phát hành bộ tài liệu
```

## 2. Price & Evidence authority
Ưu tiên: `Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Kho tri thức chỉ hỗ trợ; giá NCC không phải nguồn chính xác định đơn giá cuối cùng.

Cảnh báo NCC tại dòng: `Giá NCC < Đơn giá hiện hành` luôn Warning; `|Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15%` là Warning chênh lệch lớn. Warning không Blocking; VALORA không tự sửa/chọn giá.

## 3. Kết quả thẩm định giá
Ba bảng biểu mẫu công ty immutable. Không đổi tên/thứ tự cột, split/merge/add analytics/cardize. Giữ Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Template / AI / Bảng tính
AI flow: `Chọn mẫu → AI phân tích & đề xuất → Rà soát & chỉnh sửa → Kiểm tra & hoàn tất`; AI không silent accept/publish/overwrite/change formula.

Bảng tính authority: `Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine: `Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version`; không overwrite template, không staticize formula, không silent drop workbook feature; có Fill Manifest + audit.

## 5. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, release manifest. Microsoft 365 quản lý Word/file/file version. Document Revision != Microsoft 365 file version.

Managed Regions status: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`. Chỉ vùng user chọn được ghi; narrative ngoài vùng giữ nguyên; conflict trong managed region phải xem/xử lý trước khi ghi.

### 5.1 Shared Document Generation/Sync Contract — Báo cáo + Chứng thư
```text
Chọn template & phạm vi
→ Data Snapshot
→ Preview & Review vùng
→ Tạo Document Revision
→ Đồng bộ Microsoft 365
→ Kết quả đồng bộ
```

Layout Fluent 2 baseline: breadcrumb/header + stepper 6 bước; trái là Template/Phạm vi + Data Snapshot + kiểm tra Managed Regions; giữa là Word preview view-only lớn nhất có overlay vùng; phải là mapping/status + thông tin đồng bộ dự kiến + validation; footer có một primary CTA theo bước.

`Tạo Document Revision` là explicit user action. Template Version + Data Snapshot được bind/truy vết khi tạo revision; không silent đổi nguồn sau đó.

Lineage:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```

Readiness trước sinh có thể hiển thị `Đã mapping / Cần xem / Chưa mapping`; sau khi Word tồn tại dùng trạng thái Managed Regions chuẩn. Region code/field trên mockup chỉ minh họa, không hard-code schema và không bắt user hiểu ID kỹ thuật.

Validation phân tán: Blocking ngăn tạo revision/sync; Warning cho tiếp tục nếu rule cho phép; Info là trạng thái. Không tạo màn kiểm tra hồ sơ mới.

### 5.2 Sinh & Đồng bộ Báo cáo — Baseline Iteration 1
Child flow của Báo cáo dùng shared contract trên và nối vào `Managed Regions — Báo cáo`, Sync/Version, Publishing. Không tạo lifecycle song song.

### 5.3 Sinh & Đồng bộ Chứng thư — Baseline Iteration 1
Mockup Fluent 2 đã khóa: context `Chứng thư thẩm định giá`; template/snapshot/Managed Regions ở cột trái; preview Chứng thư view-only ở trung tâm; mapping/status + sync info/validation ở phải; primary CTA `Tiếp tục: Tạo Document Revision` ở bước review.

Các nhóm/vùng như số chứng thư, căn cứ pháp lý, khách hàng, mục đích, tài sản, kết quả, bảng chữ, ký tên chỉ là nội dung minh họa của Template Version + mapping, **không phải hard-coded schema**.

Sau khi revision/file Word tồn tại, child flow nối vào `Managed Regions — Chứng thư` hiện hành. Nội dung user tự chỉnh ngoài vùng được quản lý giữ nguyên; nếu user chỉnh trong Managed Region phải phát hiện khác biệt và xử lý trước khi ghi.

### 5.4 Sync/version
`Xem thay đổi → Xem khác biệt → Chọn nội dung → Cập nhật vào Word & tạo/ghi nhận phiên bản`.

### 5.5 Publishing
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Release manifest immutable; không có `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Không silent accept/sync/overwrite/publish.
- Không fake Word/Excel editor.
- STT immutable; raw source truy vết được.
- Document Revision != Microsoft 365 file version.
- Revision/release đã phát hành immutable.
- Vietnamese-first; không phơi technical internals.
- Một primary CTA mỗi context.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 | P0 baseline |
| NCCQ | P0 baseline Iteration 6 |
| Result | P0 baseline Iteration 1; 03 bảng immutable |
| Microsoft 365 Document Workspace | P0 baseline |
| Managed Regions — Báo cáo | P0 baseline Iteration 1 |
| Managed Regions — Chứng thư | P0 baseline Iteration 1 |
| Sync/Version | P0 baseline Iteration 1 |
| Publishing | P0 baseline Iteration 1 |
| Spreadsheet Fill Engine | P0 baseline Iteration 1 |
| Sinh & Đồng bộ Báo cáo | P0 baseline Iteration 1 |
| **Sinh & Đồng bộ Chứng thư** | **P0 baseline Iteration 1** |

## 8. Companion authority documents
- `VALORA_UIUX_HANDOFF_v2.3_CERTIFICATE_GENERATION_SYNC_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md`.
- Các addendum Managed Regions/Sync-Version/Publishing/Template/Result/NCCQ hiện hành tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Promotion `Sinh & Đồng bộ Chứng thư thẩm định giá — Iteration 1` là UI/UX authority update. Nếu implementation thay đổi Data Snapshot/Document Revision persistence, transaction boundary, conflict detection, managed-region write policy hoặc Microsoft 365 version binding thì phải đánh giá ADR riêng trước khi sửa product code.
