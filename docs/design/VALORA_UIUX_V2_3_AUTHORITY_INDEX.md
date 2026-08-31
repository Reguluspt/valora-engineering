# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.  
**Consolidation:** v2.3 — cập nhật authority `Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1` ngày 31/08/2026.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master; điểm đọc chính sau consolidation.
2. `VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Bảng tính Fill Engine — Implementation Contract v1 — Iteration 1`**.
4. `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md` — **Current Business Rule Authority** cho cảnh báo `Giá NCC ↔ Đơn giá hiện hành` ngay tại NCCQ; supersede màn `Kiểm tra quy tắc đối chiếu giá` đã bị bỏ.
5. `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_CERTIFICATE_BASELINE_ADDENDUM.md` — Baseline Managed Regions — Chứng thư.
6. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_PUBLISH_BASELINE_ADDENDUM.md` — Baseline Phát hành bộ tài liệu.
7. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SYNC_VERSION_BASELINE_ADDENDUM.md` — Baseline Đồng bộ dữ liệu & Quản lý phiên bản.
8. `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md` — Baseline Managed Regions — Báo cáo.
9. `VALORA_UIUX_HANDOFF_v2.3_CONTRACT_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — Baseline 03_Hợp đồng.
10. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_FINAL_CHECK_BASELINE_ADDENDUM.md` — Baseline Bước 4 Word + Bảng tính.
11. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM.md`.
12. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_REVIEW_EDIT_BASELINE_ADDENDUM.md`.
13. `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md`.
14. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md`.
15. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md`.
16. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md`.
17. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md`.
18. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md`.
19. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md`.
20. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md`.
21. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

Master là điểm đọc chính sau consolidation. Quyết định explicit mới hơn master thắng trong đúng scope cho tới lần consolidation tiếp theo.

## 2. Routing authority

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục triển khai
→ Workbench tài sản / Asset Context Drawer
→ Nguồn giá & Chứng cứ
→ Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC
→ Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace / Bộ tài liệu phát hành
   → 03_Hợp đồng
   → Báo cáo thẩm định giá
      → Sinh & Đồng bộ Báo cáo: Template → Data Snapshot → Preview/Review Managed Regions → Document Revision → Microsoft 365 → Kết quả đồng bộ
      → Managed Regions — Báo cáo
   → Chứng thư thẩm định giá → Managed Regions — Chứng thư
   → Đồng bộ dữ liệu & Quản lý phiên bản
   → Phát hành bộ tài liệu
```

Supporting configuration:

```text
Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu
→ Chọn/Tạo mẫu → AI phân tích & đề xuất
→ Rà soát & chỉnh sửa → Kiểm tra & hoàn tất
→ Bảng tính Fill Engine: Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version
```

## 3. Price & Evidence authority

```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```

Giá NCC không phải nguồn chính xác định Đơn giá thẩm định cuối cùng; phục vụ tạo/tái tạo báo giá, evidence/lineage và đối chiếu.

Cảnh báo NCC hiện hành:

```text
Giá NCC < Đơn giá hiện hành → luôn Warning
|Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15% → Warning chênh lệch lớn
```

Warning không Blocking; không tạo màn rule-check riêng; VALORA không tự sửa hoặc tự chọn giá thay user.

## 4. Baseline visual authority

- NCCQ — Iteration 6.
- TM01 — Iteration 1.
- TM03 — Iteration 1 Word-only.
- TM04 — Iteration 1.
- Hoàn tất 01 báo giá NCC — Iteration 3.
- Kết quả thẩm định giá — Iteration 1.
- Microsoft 365 Document Workspace — baseline authority.
- 03_Hợp đồng — Baseline Iteration 1.
- Managed Regions — Báo cáo — Baseline Iteration 1.
- Managed Regions — Chứng thư — Baseline Iteration 1.
- Đồng bộ dữ liệu & Quản lý phiên bản — Baseline Iteration 1.
- Phát hành bộ tài liệu — Baseline Iteration 1.
- Mapping Template tài liệu generic Word — Iteration 2.
- Kiểm tra & hoàn tất template Word generic — Iteration 1.
- Quản lý mẫu tài liệu generic — Iteration 1.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 3 — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 4 Word + Bảng tính — Baseline Iteration 1.
- Bảng tính Fill Engine — Implementation Contract v1 — Baseline Iteration 1; Fluent 2 desktop-first.
- **Sinh & Đồng bộ Báo cáo thẩm định giá — Baseline Iteration 1; Fluent 2 desktop-first.**

## 5. Document Workspace authority

Managed Regions user-facing titles:
- Báo cáo: `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`.
- Chứng thư: `Quản lý nội dung do VALORA quản lý (Chứng thư thẩm định giá)`.

Managed Regions mental model:
```text
Xem nội dung VALORA quản lý → Xem khác biệt → Chọn nội dung cần cập nhật → Đồng bộ vào Word
```

Trạng thái: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`. Chỉ vùng user chọn mới được ghi; narrative ngoài vùng giữ nguyên; conflict trong managed region phải được xem/xử lý trước khi ghi.

### 5.1 Sinh & Đồng bộ Báo cáo — baseline

```text
Chọn template & phạm vi
→ Data Snapshot
→ Preview & Review vùng
→ Tạo Document Revision
→ Đồng bộ Microsoft 365
→ Kết quả đồng bộ
```

Đây là child flow của Document Workspace, không thay thế Managed Regions/Sync-Version/Publishing và không tạo lifecycle song song. Preview là view-only, không fake Word editor. `Tạo Document Revision` là explicit user action.

Lineage:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```

Data Snapshot, Document Revision và Microsoft 365 file version là ba lớp khác nhau. Không silent đổi template/snapshot, không silent overwrite nội dung Word, không silent sync/publish. Revision đã phát hành immutable.

Sync/version flow:
```text
Xem những gì đã thay đổi → Xem chi tiết khác biệt → Chọn nội dung muốn cập nhật → Cập nhật vào Word & tạo/ghi nhận phiên bản
```

Publishing flow:
```text
Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành
```

## 6. Template Management / AI authority

IA: `Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu`. AI-assisted flow: `Chọn mẫu → AI phân tích & đề xuất → Rà soát & chỉnh sửa → Kiểm tra & hoàn tất`. AI chỉ đề xuất/phân tích/test; user xác nhận mapping/template chính thức.

## 7. Bảng tính authority

Reference `Bang Tinh - HĐ 42.xlsx` khóa:
```text
Hn = MIN(En:Gn)
In = Dn*Hn
```
AI/engine không tự thay formula.

Fill Engine:
```text
Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version
```
Không overwrite template; không staticize formula; không silent drop workbook feature; có Fill Manifest + audit.

## 8. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI chỉ gợi ý; user quyết định nghiệp vụ/mapping chính thức.
- Không silent accept/publish/overwrite/sync.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Không có S14, màn Kiểm tra hồ sơ, workflow KSCL riêng hoặc màn Kiểm tra quy tắc đối chiếu giá.
- 03 bảng Kết quả thẩm định giá immutable.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- Generated file và signed scan là hai artifact khác nhau.
- Document Revision != Microsoft 365 file version.
- Không silent mutate revision/release đã phát hành.
- Vietnamese-first; không phơi technical internals cho user nghiệp vụ.
- Mỗi context/bước có một primary CTA.

## 9. ADR

Nâng `Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1` thành visual/design baseline là UI/UX authority update. Nếu implementation thay đổi Data Snapshot/Document Revision persistence, transaction boundary, conflict detection, managed-region write policy hoặc Microsoft 365 version binding thì đánh giá ADR riêng.
